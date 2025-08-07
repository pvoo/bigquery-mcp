# BigQuery MCP Server

A clean, simple MCP (Model Context Protocol) server for Google BigQuery operations. Built with FastMCP for easy integration with Claude and other MCP clients.

## Features

- **Query Execution**: Run BigQuery SQL queries with automatic result pagination
- **Dataset Discovery**: List all datasets in your GCP project
- **Table Exploration**: List tables with schema information

## Installation

### Prerequisites

- Python 3.12+
- Google Cloud project with BigQuery API enabled
- Authentication credentials (service account or ADC)

### Setup with uv

```bash
# Clone the repository
git clone https://github.com/yourusername/bigquery-mcp.git
cd bigquery-mcp

# Create virtual environment with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
uv pip install -e .
```

### Configuration

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` with your configuration:
```env
GCP_PROJECT_ID=your-project-id
# Optional: GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

3. Set up Google Cloud authentication:
   - **Option 1**: Set `GOOGLE_APPLICATION_CREDENTIALS` to your service account JSON
   - **Option 2**: Use Application Default Credentials:
     ```bash
     gcloud auth application-default login
     ```

## Usage

### Running the Server

```bash
uv run python server.py
```

### Testing with MCP Inspector

#### Quick Start
```bash
# For local testing without authentication
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector uv run python server.py
```

#### Standard Setup
```bash
# 1. Ensure environment is activated
source .venv/bin/activate

# 2. Launch the inspector
npx @modelcontextprotocol/inspector uv run python server.py

# 3. The browser should open automatically
# If not, look for the URL in terminal output:
# http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
```

#### Troubleshooting Connection Issues

If the inspector doesn't connect:

1. **Test the server directly:**
```bash
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"capabilities": {}}, "id": 1}' | uv run python server.py
```
You should see a JSON response with server info.

2. **Check authentication:**
```bash
gcloud auth application-default print-access-token
# If this fails, run:
gcloud auth application-default login
```

3. **Debug the setup:**
```bash
uv run python debug_server.py
```

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed help.

### Available Tools

#### 1. run_query
Execute BigQuery SQL queries.

**Parameters:**
- `query` (required): SQL query to execute
- `project_id` (optional): Override default project
- `max_results` (optional): Maximum rows to return (default: 100)

**Example:**
```json
{
  "query": "SELECT name, COUNT(*) as count FROM `dataset.table` GROUP BY name LIMIT 10"
}
```

#### 2. list_datasets
List all datasets in a project.

**Parameters:**
- `project_id` (optional): Override default project
- `max_results` (optional): Maximum datasets to return (default: 100)

#### 3. list_tables
List all tables in a dataset with schema information.

**Parameters:**
- `dataset_id` (required): The dataset to list tables from
- `project_id` (optional): Override default project
- `max_results` (optional): Maximum tables to return (default: 100)

**Example:**
```json
{
  "dataset_id": "my_dataset"
}
```

### Integration with Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "uv",
      "args": ["run", "python", "/path/to/bigquery-mcp/server.py"],
      "env": {
        "GCP_PROJECT_ID": "your-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/credentials.json"
      }
    }
  }
}
```

## Development

### Code Quality

```bash
# Format code
uv run ruff format .

# Lint code
uv run ruff check .

# Type checking
uv run mypy server.py
```

### Running Tests

```bash
uv run pytest
```

## Security Considerations

- Never commit credentials or `.env` files
- Use service accounts with minimal required permissions
- Consider query cost implications with `bytes_billed` in responses
- Implement rate limiting for production use

## License

MIT

## Contributing

Contributions welcome! Please ensure code passes all quality checks before submitting PRs.