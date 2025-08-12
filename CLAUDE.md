# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BigQuery MCP server - A Python implementation using FastMCP to provide BigQuery operations through the Model Context Protocol. The project is optimized for navigating large datasets efficiently while keeping LLM context minimal.

## Development Commands

```bash
# Setup (recommended approach)
make install                # Setup environment and pre-commit hooks
# OR manual setup:
uv sync                     # Install all dependencies
uv run pre-commit install   # Setup git hooks

# Run the server
make run                    # Runs bigquery-mcp console script
# OR:
uv run bigquery-mcp --project YOUR_PROJECT --location US

# Development workflow
make check                  # Run all quality checks (lint, type, format)
make test                   # Run pytest test suite
make inspect                # Launch MCP inspector for testing

# Individual tools
uv run ruff check .         # Lint code
uv run ruff format .        # Format code
uv run mypy                 # Type checking (configured for src/ directory)
uv run pytest              # Run tests

# Build and distribution
make build                  # Build wheel file
make clean                  # Clean build artifacts
```

## Architecture

### Modular Package Structure
- **src/bigquery_mcp/server.py**: Main entry point and CLI argument handling
- **src/bigquery_mcp/bigquery_tools.py**: Core MCP tool implementations
- **src/bigquery_mcp/auth.py**: Authentication helpers and error formatting
- **src/bigquery_mcp/query_safety.py**: SQL query validation and safety checks
- FastMCP decorators for clean tool definitions
- Async operations for BigQuery interactions

### Tool Implementation Pattern
```python
@mcp.tool()
async def tool_name(param: str) -> dict:
    """Tool description for MCP."""
    # Input validation with helpful error messages
    # BigQuery operation with proper client handling
    # Comprehensive error handling with context
    # Return structured response optimized for LLM consumption
```

### Key Architectural Decisions
- **Console Script Entry**: Uses `bigquery-mcp` command via pyproject.toml scripts
- **Dual Response Modes**: Basic (minimal tokens) vs Detailed (full metadata) for efficient LLM usage
- **Safety-First Queries**: Only SELECT/WITH allowed, comprehensive SQL validation
- **Flexible Authentication**: Supports both Application Default Credentials and service account keys
- **Environment-Driven Config**: CLI args override env vars for flexible deployment

## BigQuery Patterns

1. **Authentication**: Use Application Default Credentials or service account JSON
2. **Project ID**: Default from environment, allow override in tool parameters
3. **Query Results**: Limit default results, provide pagination info
4. **Resource Listing**: Include basic metadata, sort alphabetically

## Environment Variables

Required:
- `GCP_PROJECT_ID` - Google Cloud project ID (can be overridden with --project)
- `BIGQUERY_LOCATION` - BigQuery location/region (can be overridden with --location)

Optional:
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON key
- `BIGQUERY_MAX_RESULTS` - Default max results for queries (default: 20)
- `BIGQUERY_LIST_MAX_RESULTS` - Default max results for list operations (default: 500)
- `BIGQUERY_SAMPLE_ROWS` - Sample rows returned in table details (default: 3)
- `BIGQUERY_ALLOWED_DATASETS` - Comma-separated list of allowed datasets to show

## Code Style & Quality

- **Python 3.10+** with comprehensive type hints (mypy configured)
- **Async/await** for all BigQuery operations
- **Ruff** for linting and formatting (configured in pyproject.toml)
- **Pre-commit hooks** for automated quality checks
- **Pytest** for testing with async support
- **Descriptive variable names** and comprehensive docstrings
- **Error handling**: Convert BigQuery exceptions to helpful user messages

## Testing Strategy

- **Unit tests**: Core functionality in tests/test_server.py
- **Safety tests**: SQL validation in tests/test_safety.py
- **Integration tests**: Real BigQuery interactions in tests/test_integration.py
- **Authentication tests**: Credential handling in tests/test_auth.py
- **MCP client**: Helper for testing MCP protocol in tests/mcp_client.py

## Project Structure

```
bigquery-mcp/
├── pyproject.toml          # Project config, dependencies, tools (ruff, mypy, pytest)
├── Makefile               # Development workflow automation
├── src/bigquery_mcp/      # Main package
│   ├── server.py          # CLI entry point and server setup
│   ├── bigquery_tools.py  # MCP tool implementations
│   ├── auth.py           # Authentication helpers
│   └── query_safety.py   # SQL safety validation
├── tests/                 # Comprehensive test suite
│   ├── conftest.py       # Pytest configuration and fixtures
│   ├── mcp_client.py     # MCP protocol testing helper
│   ├── test_server.py    # Server functionality tests
│   ├── test_safety.py    # Query safety validation tests
│   ├── test_auth.py      # Authentication tests
│   └── test_integration.py # Real BigQuery integration tests
├── examples/              # Usage examples and demos
├── Dockerfile            # Container deployment
└── tox.ini              # Multi-environment testing
```

## Core Tool Behaviors

- **list_datasets**: Returns minimal data by default, detailed on request
- **list_tables**: Shows basic info (name, rows, modified) unless detailed=true
- **get_table**: Always returns comprehensive schema and metadata
- **run_query**: Executes SELECT-only queries with safety validation

## Development Workflow

1. **Quality First**: All commits run through pre-commit hooks
2. **Test Coverage**: Aim for comprehensive test coverage of core functionality
3. **Type Safety**: Use mypy for static type checking
4. **Format Consistency**: Ruff handles code formatting automatically
