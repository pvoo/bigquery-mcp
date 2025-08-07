#!/usr/bin/env python3
"""Debug script to test MCP server connection."""

import json
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment():
    """Test environment setup."""
    print("=== Environment Check ===")
    
    # Check Python version
    print(f"Python version: {sys.version}")
    
    # Check environment variables
    project_id = os.getenv("GCP_PROJECT_ID")
    print(f"GCP_PROJECT_ID: {project_id if project_id else 'NOT SET'}")
    
    # Check for credentials
    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        print(f"GOOGLE_APPLICATION_CREDENTIALS: {creds_path}")
        if os.path.exists(creds_path):
            print("  ✓ Credentials file exists")
        else:
            print("  ✗ Credentials file NOT found")
    else:
        print("GOOGLE_APPLICATION_CREDENTIALS: Using ADC")
    
    print()

def test_imports():
    """Test if all required packages are installed."""
    print("=== Package Import Test ===")
    
    packages = [
        ("fastmcp", "FastMCP"),
        ("google.cloud.bigquery", "BigQuery Client"),
        ("dotenv", "Python Dotenv"),
        ("mcp", "MCP SDK"),
    ]
    
    for package, name in packages:
        try:
            __import__(package)
            print(f"✓ {name} imported successfully")
        except ImportError as e:
            print(f"✗ {name} import failed: {e}")
    
    print()

def test_server_initialization():
    """Test server initialization."""
    print("=== Server Initialization Test ===")
    
    try:
        from server import mcp, run_query, list_datasets, list_tables
        print("✓ Server module imported successfully")
        
        # Check if tools are registered
        print(f"✓ Tool 'run_query' registered: {run_query.name}")
        print(f"✓ Tool 'list_datasets' registered: {list_datasets.name}")
        print(f"✓ Tool 'list_tables' registered: {list_tables.name}")
        
    except Exception as e:
        print(f"✗ Server initialization failed: {e}")
    
    print()

def test_stdio_mode():
    """Test if server can run in stdio mode."""
    print("=== STDIO Mode Test ===")
    print("To test STDIO mode manually, run:")
    print("  echo '{}' | uv run python server.py")
    print()
    print("The server should respond with initialization message.")
    print()

if __name__ == "__main__":
    print("BigQuery MCP Server Debugging")
    print("=" * 40)
    print()
    
    test_environment()
    test_imports()
    test_server_initialization()
    test_stdio_mode()
    
    print("=" * 40)
    print("Debugging complete!")
    print()
    print("If all checks pass, try running:")
    print("  npx @modelcontextprotocol/inspector uv run python server.py")
    print()
    print("Or test directly with:")
    print("  uv run python server.py")