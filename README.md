# World Bank MCP Server

A Model Context Protocol (MCP) server that provides access to the World Bank's Documents & Reports database. This server enables LLMs like Claude to search and retrieve World Bank publications, research papers, project documents, and reports.

## Features

- 🔍 **Comprehensive Search**: Full-text search across World Bank documents with advanced filtering
- 🌍 **Multi-dimensional Filtering**: Filter by country, document type, language, date range, and more
- 📊 **Facet Exploration**: Discover available categories and values for refined searching
- 📄 **Document Details**: Retrieve complete metadata and abstracts for specific documents
- 🎯 **Project-based Search**: Find all documents associated with specific World Bank projects
- 📋 **Flexible Output**: Choose between human-readable Markdown or machine-readable JSON formats
- ⚡ **Pagination Support**: Efficiently browse large result sets
- 🛡️ **Robust Error Handling**: Clear, actionable error messages for LLMs

## Available Tools

### 1. `worldbank_search_documents`
Search the World Bank document database with comprehensive filtering options.

**Parameters:**
- `query` (required): Search terms
- `countries`: Filter by country names (e.g., `["Kenya", "Brazil"]`)
- `document_types`: Filter by document type (e.g., `["Procurement Plan"]`)
- `languages`: Filter by language (e.g., `["English", "Spanish"]`)
- `date_from`: Start date (YYYY-MM-DD format)
- `date_to`: End date (YYYY-MM-DD format)
- `limit`: Results per page (1-100, default 20)
- `offset`: Pagination offset (default 0)
- `sort_by`: Sort field (default "docdt")
- `sort_order`: "asc" or "desc" (default "desc")
- `response_format`: "markdown" or "json" (default "markdown")

**Example queries:**
```python
# Find climate change documents
{"query": "climate change"}

# Find Kenya procurement plans since 2020
{
  "query": "procurement",
  "countries": ["Kenya"],
  "document_types": ["Procurement Plan"],
  "date_from": "2020-01-01"
}

# Recent education reports in Spanish
{
  "query": "education",
  "languages": ["Spanish"],
  "date_from": "2023-01-01",
  "limit": 10
}
```

### 2. `worldbank_get_document_details`
Retrieve complete details for a specific document.

**Parameters:**
- `document_id` (required): Document ID from search results
- `response_format`: "markdown" or "json" (default "markdown")

**Example:**
```python
{
  "document_id": "000333037_20150825102649"
}
```

### 3. `worldbank_explore_facets`
Discover available filter values (countries, document types, languages, themes, topics).

**Parameters:**
- `facets` (required): List of facets to explore
  - `"count_exact"`: Countries
  - `"lang_exact"`: Languages
  - `"docty_exact"`: Document types
  - `"majtheme_exact"`: Major themes
  - `"topic_exact"`: Topics
- `query`: Optional filter by search query
- `response_format`: "markdown" or "json" (default "markdown")

**Example:**
```python
# Explore available countries and document types
{
  "facets": ["count_exact", "docty_exact"]
}

# Explore languages in climate change documents
{
  "facets": ["lang_exact"],
  "query": "climate change"
}
```

### 4. `worldbank_search_by_project`
Find all documents associated with a specific World Bank project.

**Parameters:**
- `project_id`: World Bank project ID (e.g., "P123456")
- `project_name`: Project name to search
- `limit`: Results per page (1-100, default 20)
- `offset`: Pagination offset (default 0)
- `response_format`: "markdown" or "json" (default "markdown")

**Note:** Either `project_id` or `project_name` must be provided.

**Example:**
```python
# Find documents for a specific project
{
  "project_id": "P123456"
}

# Search by project name
{
  "project_name": "Rural Education Project"
}
```

## Installation

### Prerequisites
- Python 3.10 or higher
- pip (Python package manager)

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install mcp httpx pydantic
```

## Configuration

### For Claude Desktop

Add the server to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "worldbank": {
      "command": "python",
      "args": ["/absolute/path/to/worldbank_mcp.py"]
    }
  }
}
```

**Important:** Replace `/absolute/path/to/worldbank_mcp.py` with the actual full path to the file.

After adding the configuration:
1. Save the file
2. Restart Claude Desktop
3. Look for the 🔌 icon in Claude's interface to verify the server is connected

### For Other MCP Clients

The server uses stdio transport and can be integrated with any MCP-compatible client:

```python
# Example for programmatic usage
from mcp import Client

async with Client("python", ["worldbank_mcp.py"]) as client:
    result = await client.call_tool(
        "worldbank_search_documents",
        {"query": "climate change", "limit": 5}
    )
    print(result)
```

## Usage Examples

### Example 1: Basic Search
```
User: Find recent World Bank documents about renewable energy in Africa

Claude will use: worldbank_search_documents
Parameters: {
  "query": "renewable energy Africa",
  "date_from": "2023-01-01",
  "limit": 10
}
```

### Example 2: Filtered Search
```
User: Show me procurement plans for Kenya from 2022

Claude will use: worldbank_search_documents
Parameters: {
  "query": "procurement",
  "countries": ["Kenya"],
  "document_types": ["Procurement Plan"],
  "date_from": "2022-01-01",
  "date_to": "2022-12-31"
}
```

### Example 3: Explore Available Options
```
User: What document types are available in the World Bank database?

Claude will use: worldbank_explore_facets
Parameters: {
  "facets": ["docty_exact"]
}
```

### Example 4: Project Documents
```
User: Find all documents for World Bank project P123456

Claude will use: worldbank_search_by_project
Parameters: {
  "project_id": "P123456"
}
```

### Example 5: Pagination
```
User: Show me the next page of results

Claude will use: worldbank_search_documents
Parameters: {
  "query": "previous search query",
  "offset": 20,  # Automatically calculated based on previous results
  "limit": 20
}
```

## Architecture & Design

This MCP server follows Anthropic's MCP builder best practices:

### Agent-Centric Design
- **Workflow-oriented tools**: Tools are designed around complete tasks, not just API endpoints
- **Context-efficient responses**: Default markdown format optimized for readability, with character limits
- **Actionable error messages**: Errors guide the LLM toward correct usage patterns
- **Smart defaults**: Sensible defaults (20 results, markdown format) minimize required parameters

### Code Quality
- **DRY principle**: Shared utility functions (`_make_api_request`, `_format_document_*`, etc.)
- **Pydantic validation**: All inputs validated automatically with clear constraints
- **Type hints throughout**: Full type coverage for maintainability
- **Async/await patterns**: All I/O operations are async for performance
- **Proper error handling**: Specific exception types with helpful messages

### MCP Best Practices
- **Server naming**: `worldbank_mcp` (follows `{service}_mcp` pattern)
- **Tool naming**: All tools prefixed with `worldbank_` to avoid conflicts
- **Tool annotations**: Proper hints (readOnly, destructive, idempotent, openWorld)
- **Response formats**: Both markdown (human) and JSON (machine) supported
- **Pagination**: Consistent pagination with `limit`, `offset`, `has_more`, `next_offset`
- **Character limits**: 25,000 character limit with graceful truncation

## API Reference

The server uses the World Bank Documents & Reports API v3:
- **Base URL**: https://search.worldbank.org/api/v3/wds
- **Documentation**: https://documents.worldbank.org/en/publication/documents-reports/api
- **Authentication**: None required (public API)
- **Rate limits**: None specified, but be respectful

## Troubleshooting

### Server not showing in Claude Desktop
1. Check the config file path is correct
2. Verify the Python path in the config is absolute
3. Restart Claude Desktop completely
4. Check Claude Desktop logs for errors

### "Module not found" errors
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Or install individually
pip install mcp httpx pydantic
```

### API errors
- The World Bank API is public and requires no authentication
- If you get 503 errors, the API may be temporarily unavailable
- Network errors: Check your internet connection

### Large result sets causing truncation
- Use smaller `limit` values
- Add more specific filters (countries, document types, dates)
- Use pagination to browse results in chunks

## Development

### Running Tests
```bash
# Check syntax
python -m py_compile worldbank_mcp.py

# Test with MCP inspector (if you have it installed)
npx @modelcontextprotocol/inspector python worldbank_mcp.py
```

### Adding New Tools
Follow the pattern in existing tools:
1. Define Pydantic input model
2. Create tool function with `@mcp.tool` decorator
3. Add proper annotations
4. Write comprehensive docstring
5. Use shared utility functions
6. Handle errors gracefully

### Code Structure
```
worldbank_mcp.py
├── Constants (API_BASE_URL, CHARACTER_LIMIT, etc.)
├── Enums (ResponseFormat, SortOrder)
├── Pydantic Models (input validation)
├── Shared Utilities (reusable functions)
│   ├── _make_api_request()
│   ├── _format_document_markdown()
│   ├── _format_document_json()
│   ├── _build_query_params()
│   └── _truncate_if_needed()
├── MCP Tools (4 tools)
│   ├── worldbank_search_documents
│   ├── worldbank_get_document_details
│   ├── worldbank_explore_facets
│   └── worldbank_search_by_project
└── Entry Point (if __name__ == "__main__")
```

## Contributing

When contributing:
1. Follow existing code style and patterns
2. Add type hints to all functions
3. Write comprehensive docstrings
4. Use shared utility functions (DRY principle)
5. Test with real API calls
6. Update README with new features

## License

This MCP server is provided as-is for use with the World Bank's public API. The World Bank's data and documents are subject to their own terms of use.

## Resources

- [MCP Documentation](https://modelcontextprotocol.io/)
- [World Bank API Documentation](https://documents.worldbank.org/en/publication/documents-reports/api)
- [Anthropic MCP Skills](https://github.com/anthropics/skills)
- [Claude Desktop](https://claude.ai/download)

## Support

For issues with:
- **This MCP server**: Open an issue in your GitHub repository
- **Claude Desktop**: Visit https://support.claude.com
- **World Bank API**: Check their official documentation
- **MCP protocol**: Visit https://modelcontextprotocol.io/

---

Built with ❤️ following [Anthropic's MCP Builder Skills](https://github.com/anthropics/skills/tree/main/examples/mcp-builder)
