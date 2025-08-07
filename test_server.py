#!/usr/bin/env python3
"""Test script to verify server functionality."""

import asyncio
from server import mcp, run_query, list_datasets, list_tables

async def test_tools():
    """Test that tools are properly registered."""
    print("Testing BigQuery MCP Server")
    print("=" * 40)
    
    # Access the original functions through the tool's function attribute
    print("\n1. Testing list_datasets:")
    result = await list_datasets.fn(project_id="test-project")
    print(f"   Result: {result}")
    
    print("\n2. Testing list_tables:")
    result = await list_tables.fn(dataset_id="test_dataset", project_id="test-project")
    print(f"   Result: {result}")
    
    print("\n3. Testing run_query:")
    result = await run_query.fn(query="SELECT 1 as test", project_id="test-project")
    print(f"   Result: {result}")
    
    print("\n" + "=" * 40)
    print("Note: Errors are expected without valid GCP credentials")
    
    # List registered tools
    print("\nRegistered tools in MCP server:")
    print(f"  - run_query: {run_query.name}")
    print(f"  - list_datasets: {list_datasets.name}")
    print(f"  - list_tables: {list_tables.name}")

if __name__ == "__main__":
    asyncio.run(test_tools())