"""Test configuration and fixtures for BigQuery MCP Server tests."""

import os
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_bigquery_client():
    """Mock BigQuery client for testing."""
    # Don't patch the client since we're now passing it as parameter to register_tools
    mock_client = Mock()

    # Mock dataset
    mock_dataset = Mock()
    mock_dataset.dataset_id = "test_dataset"
    mock_dataset.project = "test_project"
    mock_dataset.full_dataset_id = "test_project.test_dataset"
    mock_dataset.friendly_name = "Test Dataset"
    mock_dataset.description = "A test dataset"
    mock_dataset.location = "US"
    mock_dataset.created = None
    mock_dataset.modified = None

    # Mock table
    mock_table = Mock()
    mock_table.table_id = "test_table"
    mock_table.project = "test_project"
    mock_table.dataset_id = "test_dataset"
    mock_table.table_type = "TABLE"
    mock_table.friendly_name = "Test Table"
    mock_table.time_partitioning = None
    mock_table.range_partitioning = None

    # Mock table object (from get_table)
    mock_table_obj = Mock()
    mock_table_obj.description = "A test table"
    mock_table_obj.created = None
    mock_table_obj.modified = None
    mock_table_obj.num_rows = 100
    mock_table_obj.num_bytes = 5000
    mock_table_obj.schema = []
    mock_table_obj.labels = {}
    mock_table_obj.tags = []
    mock_table_obj.time_partitioning = None
    mock_table_obj.range_partitioning = None
    mock_table_obj.table_constraints = None

    # Setup mock client methods
    mock_client.list_datasets.return_value = [mock_dataset]
    mock_client.list_tables.return_value = [mock_table]
    mock_client.get_table.return_value = mock_table_obj
    mock_client.dataset.return_value = Mock()

    # Mock query job
    mock_query_job = Mock()
    mock_query_job.result.return_value = []
    mock_query_job.total_bytes_processed = 1000
    mock_query_job.total_bytes_billed = 2000
    mock_client.query.return_value = mock_query_job

    return mock_client


@pytest.fixture
def env_vars():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    test_env = {"GCP_PROJECT_ID": "test-project", "BIGQUERY_LOCATION": "US"}
    os.environ.update(test_env)
    yield test_env
    os.environ.clear()
    os.environ.update(original_env)
