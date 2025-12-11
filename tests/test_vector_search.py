"""Tests for vector search functionality."""

from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_mcp_and_client():
    """Create mock MCP and BigQuery client for testing."""
    tools = {}

    def mock_tool(fn=None, *, description=None):
        def decorator(func):
            tools[func.__name__] = func
            return func

        return decorator(fn) if fn else decorator

    mcp = Mock()
    mcp.tool = mock_tool
    mock_bigquery_client = Mock()

    return mcp, mock_bigquery_client, tools


@pytest.fixture
def enable_vector_search(monkeypatch):
    """Enable vector search for tests."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_COLUMN_CONTAINS", "embedding")


@pytest.mark.asyncio
async def test_vector_search_discovery_mode(mock_mcp_and_client, enable_vector_search):
    """Test that vector_search discovery mode uses INFORMATION_SCHEMA query."""
    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client

    # Mock INFORMATION_SCHEMA query result
    mock_row1 = Mock()
    mock_row1.dataset_id = "dataset1"
    mock_row1.table_id = "products"
    mock_row1.column_name = "embedding"

    mock_row2 = Mock()
    mock_row2.dataset_id = "dataset1"
    mock_row2.table_id = "categories"
    mock_row2.column_name = "text_embedding"

    mock_query_job = Mock()
    mock_query_job.result.return_value = [mock_row1, mock_row2]
    mock_bigquery_client.query.return_value = mock_query_job

    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]
    # No query_text = discovery mode
    result = await vector_search()

    assert result["success"] is True
    assert result["mode"] == "discovery"
    assert len(result["data"]) == 2

    # Verify INFORMATION_SCHEMA was queried
    call_args = mock_bigquery_client.query.call_args[0][0]
    assert "INFORMATION_SCHEMA.COLUMNS" in call_args
    assert "ARRAY<FLOAT64>" in call_args


@pytest.mark.asyncio
async def test_vector_search_discovery_caches_results(mock_mcp_and_client, enable_vector_search):
    """Test that discovery results are cached after first call."""
    from bigquery_mcp.bigquery_tools import clear_embedding_tables_cache, register_tools

    # Clear any existing cache
    clear_embedding_tables_cache()

    mcp, mock_bigquery_client, tools = mock_mcp_and_client

    mock_row = Mock()
    mock_row.dataset_id = "dataset1"
    mock_row.table_id = "products"
    mock_row.column_name = "embedding"

    mock_query_job = Mock()
    mock_query_job.result.return_value = [mock_row]
    mock_bigquery_client.query.return_value = mock_query_job

    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]

    # First call - discovery mode
    result1 = await vector_search()
    assert result1["success"] is True
    assert result1["mode"] == "discovery"

    # Second call with same parameters should use cache
    result2 = await vector_search()
    assert result2["success"] is True
    assert result2["cached"] is True

    # Query should only be called once due to caching
    assert mock_bigquery_client.query.call_count == 1


@pytest.mark.asyncio
async def test_vector_search_tool_not_registered_when_disabled(mock_mcp_and_client, monkeypatch):
    """Test that vector_search tool is not registered when disabled."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "false")

    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client
    register_tools(mcp, mock_bigquery_client, None, "US")

    assert "vector_search" not in tools


@pytest.mark.asyncio
async def test_vector_search_basic_functionality(mock_mcp_and_client, monkeypatch):
    """Test that vector_search performs similarity search."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_MODEL", "my_project.my_dataset.my_model")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_COLUMN_CONTAINS", "embedding")

    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client

    # Mock query result
    mock_row1 = Mock()
    mock_row1.keys.return_value = ["name", "similarity_pct", "distance"]
    mock_row1.__getitem__ = lambda self, key: {"name": "Product A", "similarity_pct": 95.5, "distance": 0.045}[key]
    mock_row1.__iter__ = lambda self: iter([("name", "Product A"), ("similarity_pct", 95.5), ("distance", 0.045)])
    mock_row1.items.return_value = [("name", "Product A"), ("similarity_pct", 95.5), ("distance", 0.045)]

    mock_query_job = Mock()
    mock_query_job.result.return_value = [mock_row1]
    mock_query_job.total_bytes_processed = 1000
    mock_bigquery_client.query.return_value = mock_query_job

    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]
    result = await vector_search(
        query_text="solenoid valve for water",
        table_path="my_dataset.my_table",
        top_k="10",
    )

    assert result["success"] is True
    assert result["mode"] == "search"
    # Verify the query was called
    mock_bigquery_client.query.assert_called()
    call_args = mock_bigquery_client.query.call_args[0][0]
    assert "VECTOR_SEARCH" in call_args
    assert "ML.GENERATE_EMBEDDING" in call_args


@pytest.mark.asyncio
async def test_vector_search_requires_embedding_model(mock_mcp_and_client, enable_vector_search):
    """Test that vector_search fails gracefully when no embedding model configured."""
    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client
    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]
    result = await vector_search(
        query_text="test query",
        table_path="dataset.table",
        # No BIGQUERY_EMBEDDING_MODEL env set
    )

    assert result["success"] is False
    assert "BIGQUERY_EMBEDDING_MODEL" in result["error"]


@pytest.mark.asyncio
async def test_vector_search_requires_table_path(mock_mcp_and_client, monkeypatch):
    """Test that vector_search fails when table_path missing in search mode."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_MODEL", "project.dataset.model")

    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client
    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]
    result = await vector_search(
        query_text="test query",
        # table_path missing
    )

    assert result["success"] is False
    assert "table_path" in result["error"]


@pytest.mark.asyncio
async def test_vector_search_invalid_top_k(mock_mcp_and_client, monkeypatch):
    """Test that invalid top_k values are rejected."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_MODEL", "project.dataset.model")

    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client
    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]

    # Test top_k = 0
    result = await vector_search(
        query_text="test",
        table_path="dataset.table",
        top_k="0",
    )
    assert result["success"] is False
    assert "top_k" in result["error"]

    # Test top_k > 1000
    result = await vector_search(
        query_text="test",
        table_path="dataset.table",
        top_k="1001",
    )
    assert result["success"] is False
    assert "top_k" in result["error"]


@pytest.mark.asyncio
async def test_vector_search_with_select_columns(mock_mcp_and_client, monkeypatch):
    """Test that select_columns filters returned columns."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_MODEL", "project.dataset.model")

    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client

    mock_query_job = Mock()
    mock_query_job.result.return_value = []
    mock_query_job.total_bytes_processed = 0
    mock_bigquery_client.query.return_value = mock_query_job

    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]
    await vector_search(
        query_text="test",
        table_path="dataset.table",
        select_columns="name,price",
    )

    # Verify select clause includes specified columns
    call_args = mock_bigquery_client.query.call_args[0][0]
    assert "base.`name`" in call_args
    assert "base.`price`" in call_args


@pytest.mark.asyncio
async def test_vector_search_uses_env_distance_type(mock_mcp_and_client, monkeypatch):
    """Test that BIGQUERY_DISTANCE_TYPE env var is used."""
    monkeypatch.setenv("BIGQUERY_VECTOR_SEARCH_ENABLED", "true")
    monkeypatch.setenv("BIGQUERY_EMBEDDING_MODEL", "project.dataset.model")
    monkeypatch.setenv("BIGQUERY_DISTANCE_TYPE", "EUCLIDEAN")

    from bigquery_mcp.bigquery_tools import register_tools

    mcp, mock_bigquery_client, tools = mock_mcp_and_client

    mock_query_job = Mock()
    mock_query_job.result.return_value = []
    mock_query_job.total_bytes_processed = 0
    mock_bigquery_client.query.return_value = mock_query_job

    register_tools(mcp, mock_bigquery_client, None, "US")

    vector_search = tools["vector_search"]
    await vector_search(
        query_text="test",
        table_path="dataset.table",
    )

    # Verify distance type from env is used
    call_args = mock_bigquery_client.query.call_args[0][0]
    assert "EUCLIDEAN" in call_args
