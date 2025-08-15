"""BigQuery MCP tools - Optimized interface for AI model data navigation."""

import asyncio
import os

# Handle both module and direct execution imports
import sys
from collections.abc import Callable
from typing import Annotated, Any

from fastmcp import FastMCP
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from pydantic import Field

# Add current directory to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))

try:
    # Try relative imports first (when run as module)
    from .query_safety import is_query_safe
except ImportError:
    # Fall back to absolute imports (when run directly)
    from query_safety import is_query_safe  # type: ignore[import-not-found,no-redef]

# Configuration defaults (can be overridden via CLI args or env vars)
DEFAULT_LIST_MAX_RESULTS = 500  # Basic list operations return limit
DEFAULT_LIST_MAX_RESULTS_DETAILED = 25  # When including descriptions, limit for manageable context
DEFAULT_SAMPLE_ROWS = 3  # Number of sample rows to include in table details
DEFAULT_SAMPLE_ROWS_FOR_STATS = 500  # Number of rows to sample for column statistics
DEFAULT_MAX_RECOMMENDED_RESULTS = 1000  # Maximum recommended results to prevent context overflow

# These can be overridden by environment variables or CLI arguments
_list_max_results = int(os.getenv("BIGQUERY_LIST_MAX_RESULTS", str(DEFAULT_LIST_MAX_RESULTS)))
_list_max_results_detailed = int(
    os.getenv("BIGQUERY_LIST_MAX_RESULTS_DETAILED", str(DEFAULT_LIST_MAX_RESULTS_DETAILED))
)
_sample_rows = int(os.getenv("BIGQUERY_SAMPLE_ROWS", str(DEFAULT_SAMPLE_ROWS)))
_sample_rows_for_stats = int(os.getenv("BIGQUERY_SAMPLE_ROWS_FOR_STATS", str(DEFAULT_SAMPLE_ROWS_FOR_STATS)))
_max_recommended_results = int(os.getenv("BIGQUERY_MAX_RECOMMENDED_RESULTS", str(DEFAULT_MAX_RECOMMENDED_RESULTS)))


def get_list_max_results(include_descriptions: bool = False) -> int:
    """Get appropriate max_results limit based on whether descriptions are included."""
    return _list_max_results_detailed if include_descriptions else _list_max_results


def get_table_stats_sample_size() -> int:
    """Get number of rows to sample for table statistics analysis."""
    return _sample_rows_for_stats


def get_table_sample_data_rows() -> int:
    """Get number of sample rows to include in table details."""
    return _sample_rows


def get_query_max_recommended_results() -> int:
    """Get maximum recommended results for query execution."""
    return _max_recommended_results


def _calculate_search_fetch_limit(max_results: int, search: str) -> int:
    """Calculate appropriate fetch limit when searching to balance thoroughness vs performance."""
    if not search:
        return max_results

    # Use progressive scaling: smaller multiplier for larger max_results
    if max_results <= 10:
        multiplier = 20  # Very small results: search more thoroughly
    elif max_results <= 50:
        multiplier = 10  # Medium results: moderate search expansion
    else:
        multiplier = 5  # Large results: conservative search expansion

    return min(max_results * multiplier, 1000)  # Cap at 1000 to avoid excessive API calls


def _create_success_response(data: Any, total_count: int | None = None, **extra_fields: Any) -> dict[str, Any]:
    response = {"success": True, "data": data}
    if total_count is not None:
        response["total_count"] = total_count
    response.update(extra_fields)
    return response


def _create_error_response(error: Exception) -> dict[str, Any]:
    return {"success": False, "error": str(error), "error_type": type(error).__name__}


def _filter_by_search_term(
    items: list[Any], search_term: str, extract_searchable_text: Callable[[Any], str]
) -> list[Any]:
    if not search_term:
        return items
    search_lower = search_term.lower()
    return [item for item in items if search_lower in extract_searchable_text(item).lower()]


def _get_table_type_with_partitioning(table: Any, partitioning_info: dict[str, Any] | None = None) -> str:
    base_type = table.table_type
    is_partitioned = (
        (hasattr(table, "time_partitioning") and table.time_partitioning)
        or (hasattr(table, "range_partitioning") and table.range_partitioning)
        or (partitioning_info is not None)
    )
    return "PARTITIONED_TABLE" if is_partitioned and base_type == "TABLE" else base_type


def _extract_partition_details(table_obj: Any) -> dict[str, Any] | None:
    if table_obj.time_partitioning:
        return {
            "type": table_obj.time_partitioning.type_,
            "field": table_obj.time_partitioning.field or "_PARTITIONTIME",
            "requires_filter": table_obj.time_partitioning.require_partition_filter,
        }
    elif table_obj.range_partitioning:
        return {
            "type": "RANGE",
            "field": table_obj.range_partitioning.field,
        }
    return None


def _get_primary_key_columns(table_obj: Any) -> list[str] | None:
    if (
        hasattr(table_obj, "table_constraints")
        and table_obj.table_constraints
        and table_obj.table_constraints.primary_key
    ):
        return list(table_obj.table_constraints.primary_key.columns)
    return None


def _calculate_column_fill_rates(
    bigquery_client: bigquery.Client, table_path: str, schema_fields: list[Any], sample_size: int
) -> dict[str, float]:
    """Calculate fill rate (non-null percentage) for each column by sampling rows."""
    if not schema_fields:
        return {}

    # Build query to count non-null values for each column
    column_checks = []
    for field in schema_fields:
        column_name = field.name
        # Use backticks to handle reserved keywords and special characters
        column_checks.append(f"COUNTIF(`{column_name}` IS NOT NULL) AS `{column_name}_non_null`")

    query = f"""
    SELECT
        COUNT(*) as total_rows,
        {", ".join(column_checks)}
    FROM `{table_path}`
    LIMIT {sample_size}
    """  # noqa: S608

    try:
        query_job = bigquery_client.query(query)
        results = list(query_job.result())

        if not results:
            return {}

        row = results[0]
        total_rows = row["total_rows"]

        if total_rows == 0:
            return {}

        fill_rates = {}
        for field in schema_fields:
            non_null_count = row[f"{field.name}_non_null"]
            fill_rates[field.name] = round((non_null_count / total_rows) * 100, 1)

    except Exception:
        # Return empty dict if sampling fails
        return {}
    else:
        return fill_rates


def register_tools(mcp: FastMCP, bigquery_client: bigquery.Client, allowed_datasets: list[str] | None = None) -> None:  # noqa: C901
    # If no allowed_datasets passed, check environment variable
    if allowed_datasets is None:
        env_datasets = os.getenv("BIGQUERY_ALLOWED_DATASETS")
        if env_datasets:
            allowed_datasets = [d.strip() for d in env_datasets.split(",") if d.strip()]

    @mcp.tool(
        description="Execute read-only BigQuery SQL queries with safety validation. Use LIMIT in your query to control result size (recommended: start with LIMIT 20 for exploration)."
    )
    async def run_query(
        query: Annotated[
            str,
            Field(
                description="BigQuery SQL SELECT query to execute (only read-only queries allowed). Use LIMIT clause to control result size."
            ),
        ],
    ) -> dict[str, Any]:
        """Execute read-only BigQuery SQL queries with safety validation.

        Note: Use LIMIT clause in your SQL query to control the number of rows returned.
        For initial exploration, start with a small limit like LIMIT 20.

        Args:
            query: BigQuery SQL SELECT query to execute
        """
        try:
            is_safe, error_msg = is_query_safe(query)
            if not is_safe:
                return _create_error_response(Exception(error_msg))

            query_job = bigquery_client.query(query)
            results = await asyncio.to_thread(query_job.result)

            rows = [dict(row) for row in results]

            return _create_success_response(
                data=rows,
                total_count=len(rows),
                total_rows_in_result=results.total_rows,
                bytes_processed=query_job.total_bytes_processed,
            )

        except (GoogleCloudError, Exception) as e:
            return _create_error_response(e)

    @mcp.tool(description="List all datasets in BigQuery project with optional search and detailed information")
    async def list_datasets_in_project(
        search: Annotated[str, Field(description="Filter datasets by name (case-insensitive)", default="")] = "",
        detailed: Annotated[
            bool, Field(description="Include descriptions and table counts for each dataset", default=False)
        ] = False,
        max_results: Annotated[
            int | None, Field(description="(OPTIONAL INTEGER) Maximum number of datasets to return", default=None)
        ] = None,
    ) -> dict[str, Any]:
        """List all datasets in BigQuery project with optional search and detailed information.

        Args:
            search: Filter datasets by name
            detailed: Include descriptions and table counts
            max_results: (Optional integer) Max datasets to return
        """
        if max_results is None:
            max_results = get_list_max_results(detailed)

        try:
            # Calculate appropriate fetch limit when searching
            fetch_limit = _calculate_search_fetch_limit(max_results, search)

            datasets_list = await asyncio.to_thread(
                lambda: list(bigquery_client.list_datasets(max_results=fetch_limit))
            )

            # Track total available datasets before any filtering
            total_available_datasets = len(datasets_list)

            # Filter by allowed datasets if specified
            if allowed_datasets:
                datasets_list = [d for d in datasets_list if d.dataset_id in allowed_datasets]

            # Apply search filter EARLY (before detailed processing) for both modes
            if search:
                datasets_list = _filter_by_search_term(datasets_list, search, lambda dataset: dataset.dataset_id)

            # Track total matching datasets after search filter
            total_matching_datasets = len(datasets_list)

            # Apply max_results limit after filtering
            datasets_list = datasets_list[:max_results]
            returned_count = len(datasets_list)

            if detailed:
                datasets_with_descriptions = []
                for dataset in datasets_list:
                    # Get table count for this dataset
                    table_count = 0
                    try:
                        dataset_ref = bigquery_client.dataset(dataset.dataset_id)

                        def list_tables_for_dataset(ref: Any = dataset_ref) -> list[Any]:
                            return list(bigquery_client.list_tables(ref, max_results=1000))

                        # Use timeout to prevent hanging on slow dataset operations
                        table_list = await asyncio.wait_for(asyncio.to_thread(list_tables_for_dataset), timeout=10.0)
                        table_count = len(table_list)
                    except TimeoutError:
                        # Log timeout but continue with dataset (table_count = 0)
                        print(f"Warning: Timeout getting table count for dataset {dataset.dataset_id}")
                    except Exception as e:
                        # Log other errors but continue with dataset (table_count = 0)
                        print(f"Warning: Failed to get table count for dataset {dataset.dataset_id}: {e}")

                    dataset_info = {
                        "dataset_id": dataset.dataset_id,
                        "description": getattr(dataset, "description", None),
                        "table_count": table_count,
                    }
                    datasets_with_descriptions.append(dataset_info)

                datasets_with_descriptions.sort(key=lambda x: x["dataset_id"])
                return _create_success_response(
                    data=datasets_with_descriptions,
                    total_available=total_available_datasets,
                    total_matching=total_matching_datasets if search else total_available_datasets,
                    returned_count=returned_count,
                )
            else:
                dataset_names = sorted([dataset.dataset_id for dataset in datasets_list])
                return _create_success_response(
                    data=dataset_names,
                    total_available=total_available_datasets,
                    total_matching=total_matching_datasets if search else total_available_datasets,
                    returned_count=returned_count,
                )

        except (GoogleCloudError, Exception) as e:
            return _create_error_response(e)

    @mcp.tool(description="List tables in dataset with optional search, detailed information, and dataset context")
    async def list_tables_in_dataset(
        dataset_id: Annotated[str, Field(description="Dataset ID to list tables from")],
        search: Annotated[str, Field(description="Filter tables by name (case-insensitive)", default="")] = "",
        detailed: Annotated[
            bool, Field(description="Include table metadata like row count and size", default=False)
        ] = False,
        max_results: Annotated[
            int | None, Field(description="(OPTIONAL INTEGER) Maximum number of tables to return", default=None)
        ] = None,
    ) -> dict[str, Any]:
        """List tables in dataset with optional search, detailed information, and dataset context.

        Args:
            dataset_id: BigQuery dataset ID
            search: Filter tables by name
            detailed: Include schemas and metadata
            max_results: (Optional integer) Max tables to return
        """
        if max_results is None:
            max_results = get_list_max_results(detailed)

        # Check if dataset is allowed
        if allowed_datasets and dataset_id not in allowed_datasets:
            return _create_error_response(Exception(f"Access to dataset '{dataset_id}' is not allowed"))

        try:
            # Get dataset info first for context
            dataset_ref = bigquery_client.dataset(dataset_id)
            dataset_obj = await asyncio.to_thread(bigquery_client.get_dataset, dataset_ref)

            # Calculate appropriate fetch limit when searching
            fetch_limit = _calculate_search_fetch_limit(max_results, search)

            # Get tables list
            tables_list = await asyncio.to_thread(
                lambda: list(bigquery_client.list_tables(dataset_ref, max_results=fetch_limit))
            )

            # Track total available tables before filtering
            total_available_tables = len(tables_list)

            # Apply search filter if provided
            if search:
                tables_list = _filter_by_search_term(tables_list, search, lambda table: table.table_id)

            # Track total matching tables after search filter
            total_matching_tables = len(tables_list)

            # Apply max_results limit after filtering
            tables_list = tables_list[:max_results]
            returned_count = len(tables_list)

            dataset_context = {
                "dataset_id": dataset_id,
                "description": dataset_obj.description,
                "location": dataset_obj.location,
                "total_table_count": total_available_tables,
            }

            if detailed:
                tables_with_descriptions = []
                for table in tables_list:
                    # Get full table object for description
                    table_ref = dataset_ref.table(table.table_id)
                    table_obj = await asyncio.to_thread(bigquery_client.get_table, table_ref)

                    table_info = {
                        "table_id": table.table_id,
                        "type": _get_table_type_with_partitioning(table),
                        "description": table_obj.description,
                        "row_count": table_obj.num_rows,
                        "size_bytes": table_obj.num_bytes,
                    }
                    tables_with_descriptions.append(table_info)

                tables_with_descriptions.sort(key=lambda x: x["table_id"])
                return _create_success_response(
                    data=tables_with_descriptions,
                    total_available=total_available_tables,
                    total_matching=total_matching_tables if search else total_available_tables,
                    returned_count=returned_count,
                    dataset_context=dataset_context,
                )
            else:
                table_names = sorted([table.table_id for table in tables_list])
                return _create_success_response(
                    data=table_names,
                    total_available=total_available_tables,
                    total_matching=total_matching_tables if search else total_available_tables,
                    returned_count=returned_count,
                    dataset_context=dataset_context,
                )

        except (GoogleCloudError, Exception) as e:
            return _create_error_response(e)

    @mcp.tool(description="Get detailed table information with schema and column fill rate analysis")
    async def get_table(
        dataset_id: Annotated[str, Field(description="Dataset ID containing the table")],
        table_id: Annotated[str, Field(description="Table ID to get detailed information for")],
    ) -> dict[str, Any]:
        """Get detailed table information with schema and column fill rate analysis.

        Args:
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
        """
        # Check if dataset is allowed
        if allowed_datasets and dataset_id not in allowed_datasets:
            return _create_error_response(Exception(f"Access to dataset '{dataset_id}' is not allowed"))

        try:
            # Get full table object
            dataset_ref = bigquery_client.dataset(dataset_id)
            table_ref = dataset_ref.table(table_id)
            table_obj = await asyncio.to_thread(bigquery_client.get_table, table_ref)

            table_path = f"{dataset_id}.{table_id}"

            # Get partition details
            partition_details = _extract_partition_details(table_obj)
            primary_key_columns = _get_primary_key_columns(table_obj)

            # Calculate column fill rates
            sample_size = get_table_stats_sample_size()
            column_fill_rates = await asyncio.to_thread(
                _calculate_column_fill_rates, bigquery_client, table_path, table_obj.schema, sample_size
            )

            # Get sample data (configurable number of rows)
            sample_rows_count = get_table_sample_data_rows()
            sample_data = []
            try:
                # Query for latest rows - try to order by a timestamp column if available
                timestamp_columns = [
                    field.name for field in table_obj.schema if field.field_type in ["TIMESTAMP", "DATETIME", "DATE"]
                ]
                order_clause = f"ORDER BY `{timestamp_columns[0]}` DESC" if timestamp_columns else ""

                sample_query = f"SELECT * FROM `{table_path}` {order_clause} LIMIT {sample_rows_count}"  # noqa: S608
                query_job = bigquery_client.query(sample_query)
                results = await asyncio.to_thread(query_job.result)
                sample_data = [dict(row) for row in results]
            except Exception:
                # If sample query fails, continue without sample data
                sample_data = []

            # Build enhanced schema with fill rates
            schema_with_stats = []
            for field in table_obj.schema:
                column_info = {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,
                    "description": field.description,
                    "fill_rate_percent": column_fill_rates.get(field.name, 0.0),
                }
                schema_with_stats.append(column_info)

            table_details = {
                "table_path": table_path,
                "type": _get_table_type_with_partitioning(table_obj, partition_details),
                "description": table_obj.description,
                "total_row_count": table_obj.num_rows,
                "size_bytes": table_obj.num_bytes,
                "created": table_obj.created.isoformat() if table_obj.created else None,
                "modified": table_obj.modified.isoformat() if table_obj.modified else None,
                "partition_details": partition_details,
                "primary_key_columns": primary_key_columns,
                "schema_with_fill_rates": schema_with_stats,
                "fill_rate_sample_size": sample_size if column_fill_rates else 0,
                "sample_data": sample_data,
            }

            return _create_success_response(data=table_details)

        except (GoogleCloudError, Exception) as e:
            return _create_error_response(e)
