"""Integration tests for BigQuery MCP Server using public datasets via MCP protocol.

These tests verify the complete MCP server functionality using BigQuery's free public datasets,
making them suitable for open-source development and CI/CD environments.
"""

import json
import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv

from tests.mcp_client import MCPClient

# Load environment variables for testing
load_dotenv()

# Skip tests if no credentials are available
pytest_skip_no_credentials = pytest.mark.skipif(
    not os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    and not os.path.exists(os.path.expanduser("~/.config/gcloud/application_default_credentials.json")),
    reason="No BigQuery credentials available - authenticate with gcloud or set GOOGLE_APPLICATION_CREDENTIALS",
)


@pytest.fixture
def public_dataset_env():
    """Environment configuration for public dataset testing."""
    # Use current project from .env, but queries will target public datasets
    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("BIGQUERY_LOCATION", "US")

    if not project_id:
        pytest.skip("GCP_PROJECT_ID not set in .env file")

    return {"GCP_PROJECT_ID": project_id, "BIGQUERY_LOCATION": location}


@pytest_asyncio.fixture
async def mcp_client(public_dataset_env):
    """Create MCP client for integration testing."""
    server_command = ["uv", "run", "python", "-m", "src.bigquery_mcp.server"]

    client = MCPClient(server_command, env=public_dataset_env)
    await client.start_server()

    yield client

    await client.stop_server()


@pytest_skip_no_credentials
@pytest.mark.integration
@pytest.mark.asyncio
class TestBigQueryMCPIntegration:
    """Integration test suite for BigQuery MCP server using public datasets."""

    async def test_server_initialization_and_capabilities(self, mcp_client):
        """Test that MCP server initializes correctly and reports proper capabilities."""
        capabilities = await mcp_client.initialize()

        # Verify server capabilities
        assert isinstance(capabilities, dict)
        assert "tools" in capabilities

        # Verify server is properly initialized
        assert mcp_client.initialized is True

    async def test_tool_discovery_and_schema_validation(self, mcp_client):
        """Test tool discovery and validate tool schemas."""
        tools = await mcp_client.list_tools()

        # Verify we have all expected tools
        tool_names = {tool["name"] for tool in tools}
        expected_tools = {"run_query", "list_datasets_in_project", "list_tables_in_dataset", "get_table"}
        assert expected_tools == tool_names
        assert len(tools) == len(expected_tools)

        # Verify each tool has proper schema structure
        for tool in tools:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert "outputSchema" in tool

            # Verify input schema is valid
            input_schema = tool["inputSchema"]
            assert "type" in input_schema
            assert input_schema["type"] == "object"

    async def test_shakespeare_dataset_query_analysis(self, mcp_client):
        """Test Shakespeare dataset query via MCP."""
        result = await mcp_client.call_tool(
            "run_query",
            {
                "query": """
            SELECT
                word,
                word_count,
                corpus
            FROM `bigquery-public-data.samples.shakespeare`
            WHERE word = 'love'
            ORDER BY word_count DESC
            LIMIT 5
            """,
                "max_results": 10,
            },
        )

        # Verify MCP response structure
        assert "content" in result
        content = result["content"][0]
        tool_result = json.loads(content["text"])

        assert tool_result["success"] is True
        assert isinstance(tool_result["data"], list)
        assert len(tool_result["data"]) > 0

        # Verify Shakespeare data structure
        love_data = tool_result["data"][0]
        assert love_data["word"] == "love"
        assert "word_count" in love_data
        assert "corpus" in love_data

    async def test_dataset_exploration_workflow(self, mcp_client):
        """Test complete dataset exploration workflow."""
        # Step 1: List datasets (will show user's project datasets)
        result = await mcp_client.call_tool("list_datasets_in_project", {"detailed": False, "max_results": 10})

        content = result["content"][0]
        basic_result = json.loads(content["text"])

        assert basic_result["success"] is True
        assert isinstance(basic_result["data"], list)

        # Step 2: Get detailed dataset info with SAME max_results
        result = await mcp_client.call_tool(
            "list_datasets_in_project",
            {
                "detailed": True,
                "max_results": 10,  # Same as basic call
            },
        )

        content = result["content"][0]
        detailed_result = json.loads(content["text"])

        assert detailed_result["success"] is True

        # CRITICAL: detailed=True should return same number of datasets as detailed=False
        # This was the bug - detailed=True was returning fewer results
        if basic_result["returned_count"] > 0:
            assert detailed_result["returned_count"] == basic_result["returned_count"], (
                f"detailed=True returned {detailed_result['returned_count']} datasets but detailed=False returned {basic_result['returned_count']}"
            )

            # Verify same dataset IDs are returned
            basic_dataset_ids = set(basic_result["data"])
            detailed_dataset_ids = {d["dataset_id"] for d in detailed_result["data"]}
            assert basic_dataset_ids == detailed_dataset_ids, (
                "detailed=True should return the same datasets as detailed=False"
            )

            # Verify detailed structure (location field should NOT be present)
            dataset = detailed_result["data"][0]
            assert "dataset_id" in dataset
            assert "description" in dataset
            assert "location" not in dataset  # Fixed: location should not be in response
            assert "table_count" in dataset
        else:
            # Both should return 0 datasets
            assert detailed_result["returned_count"] == 0

    async def test_dataset_search_with_special_characters(self, mcp_client):
        """Test that search with underscores and other special characters works consistently."""
        # Test search patterns that might contain underscores or other special chars
        search_patterns = ["_admin", "test_", "_"]

        for search_term in search_patterns:
            # Test with detailed=False
            result_basic = await mcp_client.call_tool(
                "list_datasets_in_project", {"search": search_term, "detailed": False, "max_results": 50}
            )

            content_basic = result_basic["content"][0]
            basic_result = json.loads(content_basic["text"])

            # Test with detailed=True
            result_detailed = await mcp_client.call_tool(
                "list_datasets_in_project", {"search": search_term, "detailed": True, "max_results": 50}
            )

            content_detailed = result_detailed["content"][0]
            detailed_result = json.loads(content_detailed["text"])

            # Both should succeed
            assert basic_result["success"] is True
            assert detailed_result["success"] is True

            # CRITICAL: Both modes should return the same number of results
            assert basic_result["returned_count"] == detailed_result["returned_count"], (
                f"Search '{search_term}': detailed=True returned {detailed_result['returned_count']} "
                f"but detailed=False returned {basic_result['returned_count']}"
            )

            # Verify the same datasets are returned
            if basic_result["returned_count"] > 0:
                basic_ids = set(basic_result["data"])
                detailed_ids = {d["dataset_id"] for d in detailed_result["data"]}
                assert basic_ids == detailed_ids, (
                    f"Search '{search_term}': Different datasets returned in detailed vs non-detailed mode"
                )

                # Verify all results actually contain the search term
                for dataset_id in basic_ids:
                    assert search_term.lower() in dataset_id.lower(), (
                        f"Dataset '{dataset_id}' doesn't contain search term '{search_term}'"
                    )

    async def test_table_operations(self, mcp_client):
        """Test table listing and analysis operations."""
        # First, list datasets to find one we can analyze
        result = await mcp_client.call_tool("list_datasets_in_project", {"max_results": 10})

        content = result["content"][0]
        tool_result = json.loads(content["text"])

        if tool_result["success"] and tool_result["returned_count"] > 0:
            # If user has datasets, try to list tables in first one
            dataset_id = tool_result["data"][0]

            result = await mcp_client.call_tool("list_tables_in_dataset", {"dataset_id": dataset_id, "max_results": 5})

            content = result["content"][0]
            table_result = json.loads(content["text"])

            # Verify table listing structure
            assert table_result["success"] is True
            assert "dataset_context" in table_result
            assert table_result["dataset_context"]["dataset_id"] == dataset_id

            if table_result["returned_count"] > 0:
                # If we have tables, analyze the first one
                table_id = (
                    table_result["data"][0]
                    if isinstance(table_result["data"][0], str)
                    else table_result["data"][0]["table_id"]
                )

                result = await mcp_client.call_tool("get_table", {"dataset_id": dataset_id, "table_id": table_id})

                content = result["content"][0]
                detail_result = json.loads(content["text"])

                if detail_result["success"]:
                    table_details = detail_result["data"]

                    # Verify table analysis structure
                    required_fields = [
                        "table_path",
                        "type",
                        "total_row_count",
                        "size_bytes",
                        "schema_with_fill_rates",
                        "sample_data",
                    ]
                    for field in required_fields:
                        assert field in table_details

                    assert isinstance(table_details["schema_with_fill_rates"], list)
                    assert isinstance(table_details["sample_data"], list)

    async def test_query_safety_and_validation(self, mcp_client):
        """Test query safety mechanisms with public dataset references."""
        # Test dangerous operations are blocked
        dangerous_queries = [
            "DELETE FROM `bigquery-public-data.samples.shakespeare` WHERE word = 'test'",
            "DROP TABLE `bigquery-public-data.samples.shakespeare`",
            "UPDATE `bigquery-public-data.samples.shakespeare` SET word = 'modified'",
            "INSERT INTO `bigquery-public-data.samples.shakespeare` VALUES ('fake', 1, 'test', 2023)",
        ]

        for dangerous_query in dangerous_queries:
            result = await mcp_client.call_tool("run_query", {"query": dangerous_query})

            content = result["content"][0]
            tool_result = json.loads(content["text"])

            # Should be blocked
            assert tool_result["success"] is False
            error_msg = tool_result["error"].lower()
            assert any(keyword in error_msg for keyword in ["dangerous", "not allowed", "only select"])

    async def test_error_handling_and_recovery(self, mcp_client):
        """Test comprehensive error handling scenarios."""
        # Test 1: Invalid SQL syntax
        result = await mcp_client.call_tool("run_query", {"query": "SELECT FROM WHERE INVALID SQL"})

        content = result["content"][0]
        tool_result = json.loads(content["text"])
        assert tool_result["success"] is False
        assert "error" in tool_result

        # Test 2: Non-existent table reference
        result = await mcp_client.call_tool("run_query", {"query": "SELECT * FROM `nonexistent.dataset.table`"})

        content = result["content"][0]
        tool_result = json.loads(content["text"])
        assert tool_result["success"] is False

        # Test 3: Invalid tool parameters
        result = await mcp_client.call_tool(
            "run_query",
            {
                # Missing required 'query' parameter
                "max_results": 10
            },
        )

        # Should get an error response (either MCP level or tool level)
        if "isError" in result:
            assert result["isError"] is True
        else:
            content = result["content"][0]
            tool_result = json.loads(content["text"])
            assert tool_result["success"] is False

    async def test_large_result_handling(self, mcp_client):
        """Test handling of large query results with limits."""
        # Query that could return many results, but limit it
        result = await mcp_client.call_tool(
            "run_query",
            {
                "query": """
            SELECT word, word_count, corpus
            FROM `bigquery-public-data.samples.shakespeare`
            ORDER BY word_count DESC
            """,
                "max_results": 100,  # Limit results
            },
        )

        content = result["content"][0]
        tool_result = json.loads(content["text"])

        assert tool_result["success"] is True
        assert isinstance(tool_result["data"], list)
        assert len(tool_result["data"]) <= 100  # Should respect limit
        assert tool_result["total_count"] <= 100

        # Verify result structure
        if tool_result["data"]:
            row = tool_result["data"][0]
            assert "word" in row
            assert "word_count" in row
            assert "corpus" in row
