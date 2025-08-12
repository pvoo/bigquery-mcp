#!/usr/bin/env python3
"""BigQuery MCP Server - Clean interface for BigQuery operations."""

import argparse
import os
import sys

from dotenv import load_dotenv
from fastmcp import FastMCP
from google.cloud import bigquery

# Add current directory to path for direct execution
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))

try:
    # Try relative imports first (when run as module)
    from .bigquery_tools import register_tools
except ImportError:
    # Fall back to absolute imports (when run directly)
    from bigquery_tools import register_tools  # type: ignore[import-not-found,no-redef]


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments.

    Priority order: CLI args > environment variables > defaults
    """
    parser = argparse.ArgumentParser(
        description="BigQuery MCP Server - LLM-optimized interface for Google BigQuery",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (can be overridden by CLI arguments):
  GCP_PROJECT_ID               Google Cloud project ID
  BIGQUERY_LOCATION            BigQuery location (e.g., 'US', 'EU', 'us-central1')
  GOOGLE_APPLICATION_CREDENTIALS  Path to service account key file
  BIGQUERY_MAX_RESULTS         Default max results for queries (default: 20)
  BIGQUERY_LIST_MAX_RESULTS    Max results for list operations (default: 500)
  BIGQUERY_SAMPLE_ROWS         Sample rows in table details (default: 3)

Examples:
  # Using environment variables
  export GCP_PROJECT_ID=my-project
  export BIGQUERY_LOCATION=US
  bigquery-mcp

  # Using CLI arguments
  bigquery-mcp --project my-project --location US

  # Using service account key
  bigquery-mcp --project my-project --location EU --key-file /path/to/key.json

  # Using with uvx
  uvx bigquery-mcp --project my-project --location US
        """,
    )

    parser.add_argument(
        "--project",
        dest="project_id",
        help="Google Cloud project ID (overrides GCP_PROJECT_ID env var)",
    )

    parser.add_argument(
        "--location",
        help="BigQuery location, e.g., 'US', 'EU', 'us-central1' (overrides BIGQUERY_LOCATION env var)",
    )

    parser.add_argument(
        "--key-file",
        dest="key_file",
        help="Path to service account JSON key file (overrides GOOGLE_APPLICATION_CREDENTIALS env var)",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        dest="max_results",
        help="Default max results for queries (overrides BIGQUERY_MAX_RESULTS env var)",
    )

    parser.add_argument(
        "--sample-rows",
        type=int,
        dest="sample_rows",
        help="Number of sample rows in table details (overrides BIGQUERY_SAMPLE_ROWS env var)",
    )

    parser.add_argument(
        "--datasets",
        nargs="+",
        dest="allowed_datasets",
        help="Limit access to specific datasets (space-separated list)",
    )

    parser.add_argument(
        "--check-auth",
        action="store_true",
        dest="check_auth",
        help="Check authentication and exit (useful for testing credentials)",
    )

    return parser.parse_args()


def run_server(
    project_id: str,
    location: str,
    key_file: str | None = None,
    max_results: int | None = None,
    sample_rows: int | None = None,
    allowed_datasets: list[str] | None = None,
    check_auth_only: bool = False,
) -> None:
    """Run the BigQuery MCP server with the given configuration.

    Args:
        project_id: Google Cloud project ID
        location: BigQuery location
        key_file: Optional path to service account key file
        max_results: Optional override for default max results
        sample_rows: Optional override for sample rows
        allowed_datasets: Optional list of allowed dataset IDs
        check_auth_only: If True, only check authentication and exit
    """
    # Set environment variables for configuration overrides
    if max_results is not None:
        os.environ["BIGQUERY_MAX_RESULTS"] = str(max_results)

    if sample_rows is not None:
        os.environ["BIGQUERY_SAMPLE_ROWS"] = str(sample_rows)

    if key_file:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = key_file

    if allowed_datasets:
        os.environ["BIGQUERY_ALLOWED_DATASETS"] = ",".join(allowed_datasets)

    # Initialize BigQuery client with configured project
    bigquery_client = bigquery.Client(project=project_id)

    # Validate authentication - create a synchronous version to avoid event loop conflicts
    def validate_auth_sync() -> None:
        """Synchronous version of authentication validation."""
        try:
            print(f"🔍 Validating Google Cloud authentication for project: {project_id}")
            if location:
                print(f"📍 Using BigQuery location: {location}")

            # Test BigQuery access with minimal operation - list first dataset
            list(bigquery_client.list_datasets(max_results=1))

            # Test we can create a simple query job
            test_query = "SELECT 1 as test_column"
            job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
            bigquery_client.query(test_query, job_config=job_config)

            print("✅ Google Cloud authentication successful")
            print("✅ BigQuery permissions validated")

        except Exception as auth_error:
            # Use the same error handling as the async version
            try:
                from .auth import get_helpful_auth_error
            except ImportError:
                from auth import get_helpful_auth_error  # type: ignore[import-not-found,no-redef]
            helpful_message = get_helpful_auth_error(auth_error)
            print(f"❌ Authentication failed:\n{helpful_message}")
            sys.exit(1)

    # Run the validation synchronously
    validate_auth_sync()

    if check_auth_only:
        print("✅ Authentication successful! BigQuery access verified.")
        print(f"   Project: {project_id}")
        print(f"   Location: {location}")
        return

    # Initialize FastMCP server
    mcp = FastMCP("bigquery-mcp")

    # Register all BigQuery tools with the MCP server
    register_tools(mcp, bigquery_client, allowed_datasets)

    print("🚀 Ready to accept BigQuery MCP requests")
    # Start the server - this will run until interrupted
    mcp.run()


def main() -> None:
    """Main entry point for the BigQuery MCP server.

    This function is called when the package is run as a console script.
    It handles argument parsing and server initialization.
    """
    # Load environment variables from .env file if present
    load_dotenv()

    # Parse command-line arguments
    args = parse_arguments()

    # Determine configuration with priority: CLI args > env vars > error
    project_id = args.project_id or os.getenv("GCP_PROJECT_ID")
    location = args.location or os.getenv("BIGQUERY_LOCATION")

    # Validate required configuration
    if not project_id:
        print("ERROR: Google Cloud project ID is required.", file=sys.stderr)
        print("Set it via --project argument or GCP_PROJECT_ID environment variable.", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  bigquery-mcp --project my-project --location US", file=sys.stderr)
        print("  export GCP_PROJECT_ID=my-project", file=sys.stderr)
        sys.exit(1)

    if not location:
        print("ERROR: BigQuery location is required.", file=sys.stderr)
        print("Set it via --location argument or BIGQUERY_LOCATION environment variable.", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  bigquery-mcp --project my-project --location US", file=sys.stderr)
        print("  export BIGQUERY_LOCATION=US", file=sys.stderr)
        sys.exit(1)

    # Run the server
    try:
        run_server(
            project_id=project_id,
            location=location,
            key_file=args.key_file,
            max_results=args.max_results,
            sample_rows=args.sample_rows,
            allowed_datasets=args.allowed_datasets,
            check_auth_only=args.check_auth,
        )
    except KeyboardInterrupt:
        print("\nServer stopped by user.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
