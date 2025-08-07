# MCP Inspector Connection Guide

## ✅ Quickest Way to Connect

```bash
# This is the simplest command that should work immediately:
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector uv run python server.py
```

After running this command:
1. Wait for "MCP Inspector is up and running at:" message
2. Browser should open automatically
3. If not, copy the URL from terminal (http://localhost:6274)

## What You Should See When Connected

### In the Terminal:
```
Starting MCP inspector...
⚙️ Proxy server listening on localhost:6277
⚠️  WARNING: Authentication is disabled. This is not recommended.

🚀 MCP Inspector is up and running at:
   http://localhost:6274

🌐 Opening browser...
```

### In the Browser:

1. **Connected Status** - Green "Connected" indicator at top
2. **Server Info Panel** - Shows "bigquery-mcp"
3. **Tools Tab** - Lists 3 tools:
   - `run_query`
   - `list_datasets`
   - `list_tables`

## Testing the Tools

### 1. Test list_datasets
Click on `list_datasets` and run with:
```json
{}
```
Or with limit:
```json
{
  "max_results": 5
}
```

### 2. Test run_query
Click on `run_query` and run with:
```json
{
  "query": "SELECT 'Hello BigQuery' as message, CURRENT_TIMESTAMP() as time"
}
```

### 3. Test list_tables
First run `list_datasets` to get a dataset name, then:
```json
{
  "dataset_id": "your_dataset_name"
}
```

## If Connection Fails

### Step 1: Verify Server Works
```bash
# This should show the FastMCP banner
uv run python server.py
```
Press Ctrl+C to exit.

### Step 2: Check Your Setup
```bash
# Run the debug script
uv run python debug_server.py
```

All checks should show ✓. If not, fix the issues shown.

### Step 3: Manual Browser Access
If the browser doesn't open automatically:

1. Look in terminal for the URL
2. Copy the entire URL including the token:
   ```
   http://localhost:6274/?MCP_PROXY_AUTH_TOKEN=...
   ```
3. Paste in your browser

### Step 4: Alternative Ports
If port 6274 is in use:
```bash
# Kill any existing processes
pkill -f "modelcontextprotocol/inspector"

# Wait a few seconds, then retry
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector uv run python server.py
```

## Common Issues

### "Connection Failed" in Browser
- Server not running → Check terminal for errors
- Wrong URL → Use the exact URL from terminal output
- Firewall blocking → Allow localhost connections

### No Tools Showing
- Server initialization failed → Check for Python errors
- Authentication issues → Use DANGEROUSLY_OMIT_AUTH=true for testing

### Browser Doesn't Open
- Pop-up blocker → Check browser settings
- WSL/Remote environment → Copy URL manually

## Testing Without Inspector

If inspector won't work, test the server directly:

```bash
# Test that queries work
uv run python test_real.py

# Test with public data
uv run python test_bigquery_public.py
```

## Full Working Example

```bash
# Complete setup from scratch
cd /path/to/bigquery-mcp
source .venv/bin/activate
uv pip install -e .

# Set up environment
cat > .env << EOF
GCP_PROJECT_ID=bi-project-392012
EOF

# Authenticate
gcloud auth application-default login

# Run inspector
DANGEROUSLY_OMIT_AUTH=true npx @modelcontextprotocol/inspector uv run python server.py

# Browser opens → You're connected! 🎉
```

## Need More Help?

1. Check terminal output for specific error messages
2. Run `uv run python debug_server.py` for system check
3. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions
4. Test tools work with `uv run python test_real.py`