"""Google Cloud authentication validation for BigQuery MCP Server."""

import asyncio
import os
import sys

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import bigquery


def get_helpful_auth_error(error: Exception) -> str:
    """Convert BigQuery/GCloud errors into helpful authentication guidance.

    Args:
        error: The exception that occurred during authentication

    Returns:
        User-friendly error message with resolution steps
    """
    error_str = str(error).lower()

    if isinstance(error, DefaultCredentialsError):
        return (
            "No Google Cloud credentials found. Please authenticate using one of:\n"
            "  1. gcloud auth application-default login\n"
            "  2. Set GOOGLE_APPLICATION_CREDENTIALS to your service account JSON file path\n"
            "  3. Use a service account in a GCP environment (Compute Engine, Cloud Run, etc.)"
        )

    if "permission denied" in error_str or "forbidden" in error_str:
        return (
            f"Permission denied: {error}\n"
            "Please ensure your credentials have BigQuery permissions:\n"
            "  - BigQuery Data Viewer (to read data)\n"
            "  - BigQuery Job User (to run queries)\n"
            "  - BigQuery User (for general BigQuery access)"
        )

    if "quota exceeded" in error_str:
        return f"BigQuery quota exceeded: {error}\nPlease check your project's BigQuery quotas and billing settings."

    if "project" in error_str and ("not found" in error_str or "invalid" in error_str):
        return (
            f"Project access issue: {error}\n"
            f"Please verify:\n"
            f"  - GCP_PROJECT_ID is set correctly: {os.getenv('GCP_PROJECT_ID')}\n"
            f"  - Your credentials have access to this project\n"
            f"  - The BigQuery API is enabled in this project"
        )

    if "location" in error_str:
        return (
            f"BigQuery location issue: {error}\n"
            f"Please verify BIGQUERY_LOCATION is set correctly: {os.getenv('BIGQUERY_LOCATION')}"
        )

    # Generic error with helpful context
    return (
        f"Authentication failed: {error}\n"
        "Common solutions:\n"
        "  1. Run: gcloud auth application-default login\n"
        "  2. Verify your GCP_PROJECT_ID environment variable\n"
        "  3. Check that BigQuery API is enabled in your project\n"
        "  4. Ensure your account has BigQuery permissions"
    )


async def validate_authentication(
    bigquery_client: bigquery.Client, project_id: str, location: str | None = None
) -> None:
    """Validate Google Cloud authentication and BigQuery access on startup.

    This function performs a minimal BigQuery operation to ensure credentials
    are valid and the user has necessary permissions before the server starts
    accepting requests.

    Args:
        bigquery_client: Initialized BigQuery client
        project_id: GCP project ID to validate access
        location: BigQuery location (optional)

    Raises:
        SystemExit: If authentication fails (exits with code 1)
    """
    try:
        print(f"🔍 Validating Google Cloud authentication for project: {project_id}")
        if location:
            print(f"📍 Using BigQuery location: {location}")

        # Test BigQuery access with minimal operation - list first dataset
        await asyncio.to_thread(lambda: list(bigquery_client.list_datasets(max_results=1)))

        # Also verify we can access project info
        await asyncio.to_thread(
            lambda: bigquery_client.get_job("dummy").project  # This will fail but tests project access
        )

    except Exception as auth_error:
        # Handle the dummy job error - we just wanted to test project access
        error_str = str(auth_error).lower()
        if "not found" in error_str and "job" in error_str:
            # This is expected - dummy job doesn't exist, but we validated project access
            pass
        else:
            # Real authentication error
            helpful_message = get_helpful_auth_error(auth_error)
            print(f"❌ Authentication failed:\n{helpful_message}")
            sys.exit(1)

    # Additional validation - test we can create a simple query job
    try:
        test_query = "SELECT 1 as test_column"
        # Use job_config to set dry_run mode
        from google.cloud import bigquery

        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        bigquery_client.query(test_query, job_config=job_config)
        # Note: dry_run jobs complete immediately, no need to wait for result

    except Exception as query_error:
        helpful_message = get_helpful_auth_error(query_error)
        print(f"❌ BigQuery query permissions validation failed:\n{helpful_message}")
        sys.exit(1)

    print("✅ Google Cloud authentication successful")
    print("✅ BigQuery permissions validated")
    print("🚀 Ready to accept BigQuery MCP requests")
