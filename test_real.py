#!/usr/bin/env python3
"""Test script with real BigQuery project."""

import asyncio
import os
from dotenv import load_dotenv
from server import run_query, list_datasets, list_tables

# Load environment variables
load_dotenv()

async def test_real_bigquery():
    """Test with real BigQuery project."""
    project_id = os.getenv("GCP_PROJECT_ID")
    print(f"Testing BigQuery MCP Server with project: {project_id}")
    print("=" * 50)
    
    # 1. List datasets
    print("\n1. Listing datasets:")
    result = await list_datasets.fn()
    if result["success"]:
        print(f"   Found {result['count']} datasets:")
        for dataset in result["datasets"][:5]:  # Show first 5
            print(f"   - {dataset['dataset_id']}")
        if result['count'] > 5:
            print(f"   ... and {result['count'] - 5} more")
    else:
        print(f"   Error: {result['error']}")
    
    # 2. List tables in a dataset (if we found any)
    if result["success"] and result["datasets"]:
        first_dataset = result["datasets"][0]["dataset_id"]
        print(f"\n2. Listing tables in dataset '{first_dataset}':")
        result = await list_tables.fn(dataset_id=first_dataset)
        if result["success"]:
            print(f"   Found {result['count']} tables:")
            for table in result["tables"][:5]:  # Show first 5
                print(f"   - {table['table_id']} ({table['type']})")
            if result['count'] > 5:
                print(f"   ... and {result['count'] - 5} more")
        else:
            print(f"   Error: {result['error']}")
    
    # 3. Run a simple query
    print("\n3. Running a test query:")
    query = "SELECT 1 as test_number, 'Hello BigQuery' as message"
    result = await run_query.fn(query=query)
    if result["success"]:
        print(f"   Query successful!")
        print(f"   Results: {result['rows']}")
        print(f"   Bytes processed: {result['bytes_processed']}")
        print(f"   Bytes billed: {result['bytes_billed']}")
    else:
        print(f"   Error: {result['error']}")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    asyncio.run(test_real_bigquery())