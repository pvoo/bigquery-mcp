"""Authentication tests for BigQuery MCP Server."""

import os
from unittest.mock import Mock, patch

import pytest
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.exceptions import GoogleCloudError

from src.bigquery_mcp.auth import get_helpful_auth_error, validate_authentication


@pytest.fixture(autouse=True)
def setup_env(env_vars):
    """Automatically set up environment for all tests."""
    pass  # The env_vars fixture does the actual work


def test_get_helpful_auth_error_default_credentials():
    """Test helpful error message for DefaultCredentialsError."""
    error = DefaultCredentialsError("Could not automatically determine credentials")

    message = get_helpful_auth_error(error)

    assert "No Google Cloud credentials found" in message
    assert "gcloud auth application-default login" in message
    assert "GOOGLE_APPLICATION_CREDENTIALS" in message


def test_get_helpful_auth_error_permission_denied():
    """Test helpful error message for permission denied."""
    error = Exception("Permission denied: BigQuery access forbidden")

    message = get_helpful_auth_error(error)

    assert "Permission denied" in message
    assert "BigQuery Data Viewer" in message
    assert "BigQuery Job User" in message


def test_get_helpful_auth_error_quota_exceeded():
    """Test helpful error message for quota exceeded."""
    error = Exception("Quota exceeded for BigQuery queries")

    message = get_helpful_auth_error(error)

    assert "BigQuery quota exceeded" in message
    assert "quotas and billing settings" in message


def test_get_helpful_auth_error_project_not_found():
    """Test helpful error message for project not found."""
    error = Exception("Project 'invalid-project' not found")

    message = get_helpful_auth_error(error)

    assert "Project access issue" in message
    assert "GCP_PROJECT_ID" in message
    assert "BigQuery API is enabled" in message


def test_get_helpful_auth_error_location_issue():
    """Test helpful error message for location issues."""
    error = Exception("Location 'invalid-location' is not supported")

    message = get_helpful_auth_error(error)

    assert "BigQuery location issue" in message
    assert "BIGQUERY_LOCATION" in message


def test_get_helpful_auth_error_generic():
    """Test helpful error message for generic errors."""
    error = Exception("Some unknown authentication error")

    message = get_helpful_auth_error(error)

    assert "Authentication failed" in message
    assert "gcloud auth application-default login" in message
    assert "GCP_PROJECT_ID" in message


@pytest.mark.asyncio
async def test_validate_authentication_success():
    """Test successful authentication validation."""
    mock_client = Mock()

    with patch("src.bigquery_mcp.auth.asyncio.to_thread") as mock_to_thread:
        # Mock successful dataset listing
        mock_to_thread.side_effect = [
            [],  # list_datasets succeeds (empty list is fine)
            Exception("Job 'dummy' not found"),  # Expected error for dummy job
            None,  # dry_run query succeeds
        ]

        # Mock the query method for dry_run test
        mock_client.query.return_value = None

        # Should not raise any exception
        await validate_authentication(mock_client, "test-project", "US")


@pytest.mark.asyncio
async def test_validate_authentication_list_datasets_fails():
    """Test authentication validation when list_datasets fails."""
    mock_client = Mock()

    with patch("src.bigquery_mcp.auth.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.side_effect = GoogleCloudError("Permission denied")

        with patch("src.bigquery_mcp.auth.sys.exit") as mock_exit:
            await validate_authentication(mock_client, "test-project", "US")
            mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_validate_authentication_project_access_fails():
    """Test authentication validation when project access check fails."""
    mock_client = Mock()

    with patch("src.bigquery_mcp.auth.asyncio.to_thread") as mock_to_thread:
        # First call succeeds (list_datasets), second call fails (project access)
        mock_to_thread.side_effect = [
            [],  # list_datasets succeeds
            GoogleCloudError("Project access denied"),  # project access fails
        ]

        with patch("src.bigquery_mcp.auth.sys.exit") as mock_exit:
            await validate_authentication(mock_client, "test-project", "US")
            mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_validate_authentication_query_permissions_fail():
    """Test authentication validation when query permissions fail."""
    mock_client = Mock()

    with patch("src.bigquery_mcp.auth.asyncio.to_thread") as mock_to_thread:
        # First two calls succeed, query test fails
        mock_to_thread.side_effect = [
            [],  # list_datasets succeeds
            Exception("Job 'dummy' not found"),  # Expected error for dummy job
        ]

        # Mock query to raise an error
        mock_client.query.side_effect = GoogleCloudError("Query permission denied")

        with patch("src.bigquery_mcp.auth.sys.exit") as mock_exit:
            await validate_authentication(mock_client, "test-project", "US")
            mock_exit.assert_called_once_with(1)


@pytest.mark.asyncio
async def test_validate_authentication_without_location():
    """Test authentication validation without specifying location."""
    mock_client = Mock()

    with patch("src.bigquery_mcp.auth.asyncio.to_thread") as mock_to_thread:
        # Mock successful validation
        mock_to_thread.side_effect = [
            [],  # list_datasets succeeds
            Exception("Job 'dummy' not found"),  # Expected error for dummy job
        ]

        mock_client.query.return_value = None

        # Should not raise any exception
        await validate_authentication(mock_client, "test-project", None)


def test_get_helpful_auth_error_includes_env_vars():
    """Test that helpful error messages include current environment variable values."""
    # Set environment variables for testing
    os.environ["GCP_PROJECT_ID"] = "test-project-123"
    os.environ["BIGQUERY_LOCATION"] = "EU"

    try:
        error = Exception("Project 'test-project-123' not found")
        message = get_helpful_auth_error(error)

        assert "test-project-123" in message

        error = Exception("Location 'EU' is not supported")
        message = get_helpful_auth_error(error)

        assert "EU" in message

    finally:
        # Clean up
        os.environ.pop("GCP_PROJECT_ID", None)
        os.environ.pop("BIGQUERY_LOCATION", None)
