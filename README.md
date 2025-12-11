# 🗂️ BigQuery MCP Server

Practical MCP server for navigating BigQuery datasets and tables by LLMs. Designed for larger projects with many datasets/tables, optimized to keep LLM context small while staying fast and safe.

- **Minimal by default**: list datasets and tables names; fetch details only when asked
- **Navigate larger projects**: filter by name, request detailed metadata/schemas on demand
- **Quick table insight**: optional schema, column descriptions and fill-rate to help an agent decide relevance fast
- **Safe to run**: read-only query execution with guardrails (SELECT/WITH only, comment stripping)
- **Supports vector search**: Use bigquery as your vector store. See [Vector Search](#-vector-search-optional) section for full setup instructions.

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

### Vector Search Configuration
See [Vector Search](#-vector-search-optional) section for full setup instructions.
```bash
--embedding-model project.dataset.model
--embedding-tables dataset.table1 dataset.table2
--distance-type COSINE
```

## 🛠️ Tools Overview

This MCP server provides 5 BigQuery tools optimized for LLM efficiency:

### 📊 Smart Dataset & Table Discovery
- **`list_datasets`** - Dual mode: basic (names only) vs detailed (full metadata)
- **`list_tables`** - Context-aware table browsing with optional schema details
- **`get_table`** - Complete table analysis with schema and sample data

### 🔍 Safe Query Execution
- **`run_query`** - Execute SELECT/WITH queries only, with cost tracking and safety validation. Use LIMIT clause in queries to control result size.

### 🔮 Vector Search (Optional)
- **`vector_search`** - Dual-mode tool: discover embedding tables (no query_text) or perform semantic similarity search (with query_text)

**Key Features:**
- ✅ **Minimal by default** - 70% fewer tokens in basic mode
- ✅ **Safe queries only** - Blocks all write operations
- ✅ **LLM-optimized** - Returns structured data perfect for AI analysis
- ✅ **Cost transparent** - Shows bytes processed for each query

## 🔮 Vector Search (Optional)

Enable semantic similarity search using BigQuery vector embeddings.

### Prerequisites: Setting Up Embeddings in BigQuery

Before using vector search, you need an embedding model and tables with embeddings:

**Step 1: Create a Vertex AI connection** (one-time setup)
```sql
-- In BigQuery console or bq command line
-- This creates a connection to Vertex AI for generating embeddings
CREATE EXTERNAL CONNECTION `your-project.your-region.vertex-ai`
  OPTIONS (
    endpoint = 'https://your-region-aiplatform.googleapis.com',
    type = 'CLOUD_RESOURCE'
  );
```

**Step 2: Create the embedding model**
```sql
CREATE OR REPLACE MODEL `your-project.your_dataset.text_embedding_model`
REMOTE WITH CONNECTION `your-project.your-region.vertex-ai`
OPTIONS (ENDPOINT = 'text-embedding-005');
```

**Step 3: Add embeddings to your table**
```sql
-- Add embedding column to existing table
ALTER TABLE `your-project.your_dataset.products`
ADD COLUMN IF NOT EXISTS embedding ARRAY<FLOAT64>;

-- Generate embeddings for your text data
UPDATE `your-project.your_dataset.products` t
SET embedding = (
  SELECT ml_generate_embedding_result
  FROM ML.GENERATE_EMBEDDING(
    MODEL `your-project.your_dataset.text_embedding_model`,
    (SELECT t.name AS content),
    STRUCT(TRUE AS flatten_json_output)
  )
)
WHERE embedding IS NULL;
```

> See [BigQuery text embeddings documentation](https://cloud.google.com/bigquery/docs/generate-text-embedding) for detailed setup instructions and connection permissions.

### MCP Configuration for Vector Search

Once you have embeddings set up, configure the MCP server:

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "uvx",
      "args": [
        "bigquery-mcp",
        "--project", "your-project",
        "--location", "US",
        "--embedding-model", "your-project.your_dataset.text_embedding_model",
        "--embedding-tables", "your_dataset.products", "your_dataset.documents"
      ]
    }
  }
}
```

### Configuration Reference

| CLI Argument | Environment Variable | Default | Description |
|--------------|---------------------|---------|-------------|
| `--embedding-model` | `BIGQUERY_EMBEDDING_MODEL` | - | **Required.** Full path to embedding model (`project.dataset.model`). Validated on startup. |
| `--embedding-tables` | `BIGQUERY_EMBEDDING_TABLES` | - | Tables with embedding columns (skips auto-discovery) |
| `--vector-column-contains` | `BIGQUERY_EMBEDDING_COLUMN_CONTAINS` | `embedding` | Pattern for finding embedding columns (column name must contain this) |
| `--distance-type` | `BIGQUERY_DISTANCE_TYPE` | `COSINE` | Distance metric: `COSINE`, `EUCLIDEAN`, `DOT_PRODUCT` |
| `--no-vector-search` | `BIGQUERY_VECTOR_SEARCH_ENABLED=false` | enabled | Disable vector search tools |

### Usage Examples

**Discovery mode** - find tables with embeddings:
```json
{
  "query_text": ""
}
```

**Search mode** - semantic similarity search:
```json
{
  "query_text": "solenoid valve for water",
  "table_path": "my_dataset.products",
  "top_k": "10",
  "select_columns": "name,description,price"
}
```

### Required Permissions

| Role | Purpose |
|------|---------|
| `roles/bigquery.dataViewer` | Read tables and models |
| `roles/bigquery.jobUser` | Run BigQuery jobs |
| `roles/bigquery.metadataViewer` | Auto-discover embedding tables (optional) |

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
