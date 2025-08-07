# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BigQuery MCP server - A simple, clean Python implementation using FastMCP to provide BigQuery operations through the Model Context Protocol.

## Development Commands

```bash
# Setup
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
uv pip install -e ".[dev]"  # For development dependencies

# Run the server
uv run python server.py

# Development
uv run ruff check .         # Lint code
uv run ruff format .        # Format code
uv run mypy server.py       # Type checking
uv run pytest               # Run tests (when implemented)

# Testing with MCP
npx @modelcontextprotocol/inspector uv run python server.py
```

## Architecture

### Single-File Design
- `server.py` contains all server logic for simplicity
- FastMCP decorators for clean tool definitions
- Async operations for BigQuery interactions

### Tool Implementation Pattern
```python
@mcp.tool()
async def tool_name(param: str) -> dict:
    """Tool description for MCP."""
    # Input validation
    # BigQuery operation
    # Error handling
    # Return structured response
```

### Error Handling
- Wrap BigQuery exceptions in meaningful error messages
- Return empty results with error details for failed operations
- Log errors for debugging without exposing sensitive information

## BigQuery Patterns

1. **Authentication**: Use Application Default Credentials or service account JSON
2. **Project ID**: Default from environment, allow override in tool parameters
3. **Query Results**: Limit default results, provide pagination info
4. **Resource Listing**: Include basic metadata, sort alphabetically

## Environment Variables

Required:
- `GCP_PROJECT_ID` - Default Google Cloud project

Optional:
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON
- `BIGQUERY_LOCATION` - Default location for operations

## Code Style

- Python 3.12+ with type hints
- Async/await for all BigQuery operations
- Descriptive variable names
- Docstrings for all functions
- Keep it simple - avoid over-engineering

## Project Structure

```
bigquery-mcp/
├── pyproject.toml          # Project metadata and dependencies
├── server.py               # Main MCP server implementation
├── .env.example            # Example environment configuration
├── .gitignore             # Git ignore rules
├── README.md              # User documentation
├── CLAUDE.md              # This file
└── LICENSE                # MIT license
```