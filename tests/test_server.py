"""Essential unit tests for BigQuery MCP Server focusing on safety and error handling."""

from unittest.mock import Mock, patch

import pytest
from google.cloud.exceptions import GoogleCloudError


@pytest.fixture(autouse=True)
def setup_env(env_vars):
    """Automatically set up environment for all tests."""
    _ = env_vars  # Use the fixture to avoid unused parameter warning
    pass


@pytest.mark.asyncio
async def test_run_query_with_dangerous_keywords():
    """Test that dangerous SQL keywords are blocked."""
    from bigquery_mcp.bigquery_tools import register_tools

    # Create actual tools by importing them directly
    tools = {}

    # Mock the FastMCP instance
    def mock_tool(fn=None, *, description=None):
        def decorator(func):
            tools[func.__name__] = func
            return func

        return decorator(fn) if fn else decorator

    mcp = Mock()
    mcp.tool = mock_tool

    mock_bigquery_client = Mock()
    register_tools(mcp, mock_bigquery_client)

    run_query = tools["run_query"]

    dangerous_queries = [
        "DELETE FROM table WHERE id = 1",
        "UPDATE table SET name = 'test'",
        "INSERT INTO table VALUES (1, 'test')",
        "DROP TABLE test",
        "CREATE TABLE test (id INT)",
        "ALTER TABLE test ADD COLUMN name VARCHAR(50)",
        "MERGE INTO target USING source ON condition",
    ]

    for query in dangerous_queries:
        result = await run_query(query)
        assert result["success"] is False
        assert (
            "dangerous" in result["error"].lower()
            or "not allowed" in result["error"].lower()
            or "only select" in result["error"].lower()
        )


@pytest.mark.asyncio
async def test_run_query_bigquery_error():
    """Test query execution with BigQuery error."""
    from bigquery_mcp.bigquery_tools import register_tools

    # Create actual tools by importing them directly
    tools = {}

    # Mock the FastMCP instance
    def mock_tool(fn=None, *, description=None):
        def decorator(func):
            tools[func.__name__] = func
            return func

        return decorator(fn) if fn else decorator

    mcp = Mock()
    mcp.tool = mock_tool

    mock_bigquery_client = Mock()
    register_tools(mcp, mock_bigquery_client)

    run_query = tools["run_query"]

    # Mock BigQuery error
    mock_bigquery_client.query.side_effect = GoogleCloudError("Test error")

    result = await run_query("SELECT * FROM test_table")

    assert result["success"] is False
    assert "Test error" in result["error"]
    # GoogleCloudError gets mapped to GoogleAPICallError in the actual implementation
    assert result["error_type"] in ["GoogleCloudError", "GoogleAPICallError"]


@pytest.mark.asyncio
async def test_error_handling_with_mocked_exceptions():
    """Test comprehensive error handling for all tools with mocked exceptions."""
    from bigquery_mcp.bigquery_tools import register_tools

    # Create actual tools by importing them directly
    tools = {}

    # Mock the FastMCP instance
    def mock_tool(fn=None, *, description=None):
        def decorator(func):
            tools[func.__name__] = func
            return func

        return decorator(fn) if fn else decorator

    mcp = Mock()
    mcp.tool = mock_tool

    mock_bigquery_client = Mock()
    register_tools(mcp, mock_bigquery_client)

    # Test BigQuery error with list_datasets_in_project
    list_datasets_in_project = tools["list_datasets_in_project"]

    with patch("bigquery_mcp.bigquery_tools.asyncio.to_thread") as mock_to_thread:
        mock_to_thread.side_effect = GoogleCloudError("BigQuery error")

        result = await list_datasets_in_project()
        assert result["success"] is False
        assert "BigQuery error" in result["error"]
        assert result["error_type"] in ["GoogleCloudError", "GoogleAPICallError"]

    # Test general exception with list_tables_in_dataset
    list_tables_in_dataset = tools["list_tables_in_dataset"]

    # This test should test the allowed_datasets functionality since it's now enabled
    result = await list_tables_in_dataset("test_dataset")
    assert result["success"] is False
    assert "not allowed" in result["error"]  # The allowed_datasets check should trigger

    # Test get_table error handling - should also fail due to allowed_datasets restriction
    get_table = tools["get_table"]

    result = await get_table("test_dataset", "nonexistent_table")
    assert result["success"] is False
    assert "not allowed" in result["error"]  # The allowed_datasets check should trigger
