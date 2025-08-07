# MCP Inspector Troubleshooting Guide

## Quick Start

```bash
# 1. Ensure you're in the project directory
cd /path/to/bigquery-mcp

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Run the inspector
npx @modelcontextprotocol/inspector uv run python server.py
```

## Common Issues and Solutions

### 1. Inspector Won't Connect

#### Symptom
- Inspector opens but shows "Connection Failed" or spinning loader
- No tools appear in the interface

#### Solutions

**A. Check if server starts correctly:**
```bash
# Test server directly
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"capabilities": {}}, "id": 1}' | uv run python server.py
```

You should see a JSON response with server capabilities.

**B. Use environment variable for authentication token:**
```bash
# Run with auth disabled (for local testing only)
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector uv run python server.py
```

**C. Check for port conflicts:**
```bash
# Check if ports are available
lsof -i :6274
lsof -i :6277
```

If ports are in use, kill the processes or wait a moment and retry.

### 2. Authentication Errors

#### Symptom
- "Your default credentials were not found"
- "403 Forbidden" errors

#### Solutions

**Option 1: Use Application Default Credentials**
```bash
# Login with your Google account
gcloud auth application-default login

# Verify authentication
gcloud auth application-default print-access-token
```

**Option 2: Use Service Account**
```bash
# Download service account key from GCP Console
# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

# Add to .env file
echo "GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json" >> .env
```

### 3. Project Access Issues

#### Symptom
- "Project not found" errors
- "BigQuery API not enabled"

#### Solutions

**A. Verify project ID:**
```bash
# List available projects
gcloud projects list

# Update .env with correct project ID
echo "GCP_PROJECT_ID=your-correct-project-id" > .env
```

**B. Enable BigQuery API:**
```bash
# Enable API for your project
gcloud services enable bigquery.googleapis.com --project=YOUR_PROJECT_ID
```

### 4. Inspector Specific Issues

#### Browser Doesn't Open
```bash
# Copy the URL manually from terminal output
# Look for: http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
```

#### Connection Times Out
```bash
# Increase timeout and run with verbose logging
MCP_TIMEOUT=30000 npx @modelcontextprotocol/inspector uv run python server.py
```

#### Inspector Shows No Tools
```bash
# Verify tools are registered
uv run python -c "from server import run_query, list_datasets, list_tables; print('Tools loaded successfully')"
```

## Step-by-Step Connection Guide

### 1. Prepare Environment
```bash
# Clean install
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 2. Configure Authentication
```bash
# Check current auth status
gcloud auth list
gcloud config get-value project

# Set up ADC if needed
gcloud auth application-default login
```

### 3. Test Server Standalone
```bash
# Run debug script
uv run python debug_server.py

# Test basic functionality
uv run python test_real.py
```

### 4. Launch Inspector
```bash
# Basic launch
npx @modelcontextprotocol/inspector uv run python server.py

# With debugging
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector uv run python server.py

# Alternative: Use direct stdio testing
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"capabilities": {}}, "id": 1}' | uv run python server.py
```

### 5. Using the Inspector

Once connected, you should see:
1. **Server Info**: Shows "bigquery-mcp" as the server name
2. **Tools Tab**: Lists three tools:
   - `run_query` - Execute SQL queries
   - `list_datasets` - List available datasets
   - `list_tables` - List tables in a dataset

#### Testing Tools in Inspector

**Test list_datasets:**
```json
{
  "max_results": 10
}
```

**Test run_query:**
```json
{
  "query": "SELECT 1 as test, CURRENT_TIMESTAMP() as time",
  "max_results": 10
}
```

**Test list_tables:**
```json
{
  "dataset_id": "your_dataset_name",
  "max_results": 10
}
```

## Alternative Testing Methods

### 1. Direct Python Testing
```python
# test_connection.py
import asyncio
from server import run_query

async def test():
    result = await run_query.fn(query="SELECT 1")
    print(result)

asyncio.run(test())
```

### 2. Using MCP Client Library
```bash
# Install MCP client
pip install mcp

# Create test client script
python -c "
from mcp import ClientSession
import asyncio

async def test():
    async with ClientSession() as session:
        await session.initialize()
        result = await session.call_tool('run_query', {'query': 'SELECT 1'})
        print(result)

asyncio.run(test())
"
```

### 3. Manual STDIO Testing
```bash
# Send initialize request
echo '{"jsonrpc": "2.0", "method": "initialize", "params": {"capabilities": {}}, "id": 1}' | uv run python server.py

# Send tool list request
echo '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 2}' | uv run python server.py
```

## Getting Help

1. **Check logs**: Look for error messages in terminal output
2. **Run debug script**: `uv run python debug_server.py`
3. **Test without inspector**: `uv run python test_real.py`
4. **Check GitHub issues**: Report bugs at the project repository

## Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `GCP_PROJECT_ID` | Yes | Your Google Cloud project ID | `my-project-123` |
| `GOOGLE_APPLICATION_CREDENTIALS` | No | Path to service account JSON | `/path/to/key.json` |
| `DANGEROUSLY_OMIT_AUTH` | No | Disable auth for local testing | `true` |
| `MCP_TIMEOUT` | No | Connection timeout in ms | `30000` |