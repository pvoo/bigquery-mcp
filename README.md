# 🗂️ BigQuery MCP Server

Practical MCP server for navigating BigQuery datasets and tables by LLMs. Designed for larger projects with many datasets/tables, optimized to keep LLM context small while staying fast and safe.

- **Minimal by default**: list datasets and tables names; fetch details only when asked
- **Navigate larger projects**: filter by name, request detailed metadata/schemas on demand
- **Quick table insight**: optional schema, column descriptions and fill-rate to help an agent decide relevance fast
- **Safe to run**: read-only query execution with guardrails (SELECT/WITH only, comment stripping)

## Quick Start

**Prerequisites:** Python 3.10+ and [uv](https://github.com/astral-sh/uv) package manager

### 🚀 Quick Setup

**Option 1: Direct from PyPI (Recommended)**
```bash
# 1. Authenticate
gcloud auth application-default login

# 2. Run server
uvx bigquery-mcp --project YOUR_PROJECT --location US
```

**Option 2: Clone locally (development setup)**
```bash
# 1. Clone and setup
git clone https://github.com/pvoo/bigquery-mcp.git
cd bigquery-mcp

# 2. Configure environment
cp .env.example .env
# Edit .env with your project and location

# 3. Run or inspect
make run      # Start server
make inspect  # Open MCP inspector
```

### 🔧 MCP Client Configuration

**Option 1: PyPI package (Recommended)**
Simplest setup using the published PyPI package:
```json
{
  "mcpServers": {
    "bigquery": {
      "command": "uvx",
      "args": [
        "bigquery-mcp",
        "--project", "your-project-id",
        "--location", "US"
     ]
    }
  }
}
```


**Option 2: Local clone (for development)**
```bash
# Clone first
git clone https://github.com/pvoo/bigquery-mcp.git
```

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/bigquery-mcp", "run", "bigquery-mcp"],
      "env": {
        "GCP_PROJECT_ID": "your-project-id",
        "BIGQUERY_LOCATION": "US"
      }
    }
  }
}
```

### 🧪 Test Your Setup

```bash
# Test with MCP inspector
npx @modelcontextprotocol/inspector uvx bigquery-mcp --project YOUR_PROJECT --location US
```

## 🔧 Configuration Options

All configuration can be set via CLI arguments or environment variables. CLI arguments take precedence.

### Required Parameters
```bash
--project YOUR_PROJECT    # Google Cloud project ID
--location US             # BigQuery location (US, EU, etc.)
```

### Optional Parameters
```bash
# Dataset Access Control
--datasets dataset1 dataset2    # Restrict to specific datasets (default: all datasets)

# Query & Result Limits
--list-max-results 500          # Max results for basic list operations (default: 500)
--detailed-list-max 25          # Max results for detailed list operations (default: 25)

# Table Analysis
--sample-rows 3                 # Sample data rows returned in get_table (default: 3)
--stats-sample-size 500         # Rows sampled for column fill rate calculations (default: 500)

# Authentication
--key-file /path/to/key.json    # Service account key file (default: ADC)
```

### Environment Variables
All CLI options have corresponding environment variables:
```bash
export GCP_PROJECT_ID=your-project
export BIGQUERY_LOCATION=US
export BIGQUERY_ALLOWED_DATASETS=dataset1,dataset2
export BIGQUERY_LIST_MAX_RESULTS=500
export BIGQUERY_LIST_MAX_RESULTS_DETAILED=25
export BIGQUERY_SAMPLE_ROWS=3
export BIGQUERY_SAMPLE_ROWS_FOR_STATS=500
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

## 🛠️ Tools Overview

This MCP server provides 4 core BigQuery tools optimized for LLM efficiency:

### 📊 Smart Dataset & Table Discovery
- **`list_datasets`** - Dual mode: basic (names only) vs detailed (full metadata)
- **`list_tables`** - Context-aware table browsing with optional schema details
- **`get_table`** - Complete table analysis with schema and sample data

### 🔍 Safe Query Execution
- **`run_query`** - Execute SELECT/WITH queries only, with cost tracking and safety validation. Use LIMIT clause in queries to control result size.

**Key Features:**
- ✅ **Minimal by default** - 70% fewer tokens in basic mode
- ✅ **Safe queries only** - Blocks all write operations
- ✅ **LLM-optimized** - Returns structured data perfect for AI analysis
- ✅ **Cost transparent** - Shows bytes processed for each query

## 🏗️ Development Setup

### Local Development
```bash
# Clone and setup
git clone https://github.com/pvoo/bigquery-mcp.git
cd bigquery-mcp
make install  # Setup environment + pre-commit hooks

# Development workflow
make run      # Start server
make test     # Run test suite
make check    # Lint + format + typecheck
make inspect  # Launch MCP inspector
```

### Testing & Quality
```bash
make test                    # Full test suite
pytest tests/test_safety.py  # SQL safety validation tests
pytest tests/test_server.py  # Core server functionality tests
make check                   # Run all quality checks
```

## 🔐 Authentication & Permissions

**Authentication Methods:**
1. **Application Default Credentials** (recommended): `gcloud auth application-default login`
2. **Service Account Key**: Use `--key-file` or set `GOOGLE_APPLICATION_CREDENTIALS`

**Required BigQuery Permissions:**
- `bigquery.datasets.get`, `bigquery.datasets.list`
- `bigquery.tables.list`, `bigquery.tables.get`
- `bigquery.jobs.create`, `bigquery.data.get`

## 🚨 Troubleshooting

**Authentication Issues:**
```bash
# Check current auth
gcloud auth application-default print-access-token

# Re-authenticate
gcloud auth application-default login

# Enable BigQuery API
gcloud services enable bigquery.googleapis.com
```

**MCP Connection Issues:**
- Ensure absolute paths in MCP config
- Test server manually: `make run`
- Check that project and location environment variables or args are set correctly

**Performance Issues:**
- Use `{"detailed": false}` for faster responses
- Add search filters: `{"search": "pattern"}`
- Reduce max_results for large datasets

## 💡 Usage Examples

### 📊 SQL Query Example
```sql
-- Query public datasets
SELECT
    EXTRACT(YEAR FROM pickup_datetime) as year,
    COUNT(*) as trips,
    ROUND(AVG(fare_amount), 2) as avg_fare
FROM `bigquery-public-data.new_york_taxi_trips.tlc_yellow_trips_2020`
WHERE pickup_datetime BETWEEN '2020-01-01' AND '2020-12-31'
GROUP BY year
LIMIT 20
```

### 🤖 Example: Usage with Claude Code subagent

**Scenario:** Use the specialized BigQuery Table Analyst agent in Claude Code to automatically explore your data warehouse, analyze table relationships, and provide structured insights. By using the subagent you can take the context used for analyzing the tables out of the main thread and return actionable insights into the main agent thread for writing SQL or analyzing.

**Setup:**
```bash
# 1. Clone and configure
git clone https://github.com/pvoo/bigquery-mcp.git
cd bigquery-mcp

# 2. Setup environment
export GCP_PROJECT_ID="your-project-id"
export BIGQUERY_LOCATION="US"
gcloud auth application-default login

# 3. Launch Claude Code
claude-code
```

**Example Usage:**
```
💬 You: "I need to understand our sales data structure and find tables related to customer orders"

🤖 Claude: I'll use the BigQuery Table Analyst agent to explore your sales datasets and identify relevant tables with their relationships.

[Agent automatically:]
- Lists all datasets to identify sales-related ones
- Explores table schemas with detailed metadata
- Shows actual sample data from key tables
- Discovers join relationships between tables
- Provides ready-to-use SQL queries
```

**What the Agent Returns:**
- **Table schemas** with column descriptions and types
- **Sample data** showing actual values (not placeholders)
- **Join relationships** with working SQL examples
- **Data quality insights** (null rates, freshness, etc.)
- **Actionable SQL queries** you can immediately execute



## 🤝 Contributing

We welcome contributions! Looking forward to your feedback for improvements.

**Quick Start:**
```bash
# Fork on GitHub, then:
git clone https://github.com/yourusername/bigquery-mcp.git
cd bigquery-mcp
make install  # Setup dev environment
make check    # Verify everything works

# Make changes, then:
make test     # Run tests
make check    # Quality checks
# Submit PR!
```

**Development Guidelines:**
- Add tests for new features
- Update documentation
- Follow existing code style (enforced by pre-commit hooks)
- Ensure all quality checks pass

**Found an issue or have a feature request?**
- 🐛 **Bug reports:** [Open an issue](https://github.com/pvoo/bigquery-mcp/issues)
- 🔧 **Code improvements:** Submit a pull request
- 📖 **Documentation:** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**🌟 Star this repo if it helps you!**
