#!/usr/bin/env python3
"""BigQuery MCP Server - Simple and clean interface for BigQuery operations."""

import asyncio
import os
from typing import Optional, Any, Dict, List

from dotenv import load_dotenv
from fastmcp import FastMCP
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

# Load environment variables
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("bigquery-mcp")

# Initialize BigQuery client
def get_bigquery_client(project_id: Optional[str] = None) -> bigquery.Client:
    """Get BigQuery client with optional project override."""
    project = project_id or os.getenv("GCP_PROJECT_ID")
    if not project:
        raise ValueError("GCP_PROJECT_ID environment variable or project_id parameter is required")
    return bigquery.Client(project=project)


@mcp.tool()
async def run_query(
    query: str,
    project_id: Optional[str] = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """Execute a BigQuery SQL query and return results.
    
    Args:
        query: SQL query to execute
        project_id: Optional GCP project ID (defaults to GCP_PROJECT_ID env var)
        max_results: Maximum number of rows to return (default 100)
    
    Returns:
        Dictionary with query results or error information
    """
    try:
        client = get_bigquery_client(project_id)
        
        # Run the query
        query_job = client.query(query)
        
        # Wait for the job to complete
        results = await asyncio.to_thread(query_job.result)
        
        # Convert results to list of dictionaries
        rows = []
        for i, row in enumerate(results):
            if i >= max_results:
                break
            rows.append(dict(row))
        
        return {
            "success": True,
            "rows": rows,
            "total_rows": results.total_rows,
            "rows_returned": len(rows),
            "bytes_processed": query_job.total_bytes_processed,
            "bytes_billed": query_job.total_bytes_billed,
        }
        
    except GoogleCloudError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp.tool()
async def list_datasets(
    project_id: Optional[str] = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """List all datasets in a BigQuery project.
    
    Args:
        project_id: Optional GCP project ID (defaults to GCP_PROJECT_ID env var)
        max_results: Maximum number of datasets to return (default 100)
    
    Returns:
        Dictionary with list of datasets or error information
    """
    try:
        client = get_bigquery_client(project_id)
        
        # List datasets
        datasets_list = await asyncio.to_thread(
            lambda: list(client.list_datasets(max_results=max_results))
        )
        
        # Extract dataset information
        datasets = []
        for dataset in datasets_list:
            datasets.append({
                "dataset_id": dataset.dataset_id,
                "project": dataset.project,
                "full_id": dataset.full_dataset_id,
                "friendly_name": getattr(dataset, 'friendly_name', None),
                "description": getattr(dataset, 'description', None),
                "location": getattr(dataset, 'location', None),
                "created": dataset.created.isoformat() if hasattr(dataset, 'created') and dataset.created else None,
                "modified": dataset.modified.isoformat() if hasattr(dataset, 'modified') and dataset.modified else None,
            })
        
        # Sort by dataset_id
        datasets.sort(key=lambda x: x["dataset_id"])
        
        return {
            "success": True,
            "datasets": datasets,
            "count": len(datasets)
        }
        
    except GoogleCloudError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


@mcp.tool()
async def list_tables(
    dataset_id: str,
    project_id: Optional[str] = None,
    max_results: int = 100
) -> Dict[str, Any]:
    """List all tables in a BigQuery dataset.
    
    Args:
        dataset_id: The dataset ID to list tables from
        project_id: Optional GCP project ID (defaults to GCP_PROJECT_ID env var)
        max_results: Maximum number of tables to return (default 100)
    
    Returns:
        Dictionary with list of tables or error information
    """
    try:
        client = get_bigquery_client(project_id)
        
        # Get dataset reference
        dataset_ref = client.dataset(dataset_id)
        
        # List tables
        tables_list = await asyncio.to_thread(
            lambda: list(client.list_tables(dataset_ref, max_results=max_results))
        )
        
        # Extract table information
        tables = []
        for table in tables_list:
            # Get table details for more information
            table_ref = dataset_ref.table(table.table_id)
            table_obj = await asyncio.to_thread(client.get_table, table_ref)
            
            tables.append({
                "table_id": table.table_id,
                "project": table.project,
                "dataset_id": table.dataset_id,
                "full_id": f"{table.project}.{table.dataset_id}.{table.table_id}",
                "type": table.table_type,
                "friendly_name": table.friendly_name,
                "description": table_obj.description,
                "created": table_obj.created.isoformat() if table_obj.created else None,
                "modified": table_obj.modified.isoformat() if table_obj.modified else None,
                "num_rows": table_obj.num_rows,
                "num_bytes": table_obj.num_bytes,
                "schema": [
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode,
                        "description": field.description
                    }
                    for field in table_obj.schema
                ] if table_obj.schema else []
            })
        
        # Sort by table_id
        tables.sort(key=lambda x: x["table_id"])
        
        return {
            "success": True,
            "tables": tables,
            "count": len(tables),
            "dataset_id": dataset_id
        }
        
    except GoogleCloudError as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }


def main():
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()