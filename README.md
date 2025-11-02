# World Bank MCP Server

An MCP server for accessing the [World Bank's Documents & Reports database](https://documents.worldbank.org/en/publication/documents-reports/api).  
Provides searching, retrieval, and detailed breakdowns of World Bank documents for LLMs and programmatic use.

## Repository Structure

```
document-reports-mcp/
 worldbank_dnr_mcp/          # main package
    core.py                 # business logic, models, utilities
    factory.py              # server creation and tool registration
    parsers.py              # transport-specific response parsers
    __init__.py             # package exports
 server_stdio.py             # STDIO transport server
 server_sse.py               # SSE transport server
 start_server_claude.py      # launcher for Claude Desktop
 pyproject.toml              # project configuration
 requirements.txt            # legacy requirements file
 docs/                       # documentation
     API Document.pdf
     DESIGN_LOGIC.md
     STRUCTURE_GUIDE.md
     mcp_simulation.mp4      # demonstration video
```

## Project Features

- comprehensive document search with advanced filters
- multi-dimensional filtering (by country, type, language, date range)
- result faceting and category exploration
- metadata and abstract retrieval
- project-based document lookup
- flexible markdown/json output formats
- extensive error handling and validation
- support for both STDIO and SSE transports

## Demonstration Video

Watch the MCP server in action:

**[Watch Demo Video](docs/mcp_simulation.mp4)**

Note: Click the link above to view the demonstration video. GitHub README files don't support embedded video players, but you can download or view the video directly through the link.

## Quick Documentation Index

- [API Document (PDF)](docs/API%20Document.pdf): Official World Bank API documentation
- [DESIGN_LOGIC.md](docs/DESIGN_LOGIC.md): Core design principles and logic explained
- [STRUCTURE_GUIDE.md](docs/STRUCTURE_GUIDE.md): File structure, configuration, and usage

## Installation

Using uv (recommended):
```bash
uv sync
```

Using pip:
```bash
pip install -r requirements.txt
```

## Usage

### For Claude Desktop (STDIO Transport)

1. Update your Claude Desktop config to use the launcher:
   ```json
   {
     "mcpServers": {
       "worldbank-dnr": {
         "command": "uv",
         "args": ["run", "/absolute/path/to/start_server_claude.py"],
         "cwd": "/absolute/path/to/document-reports-mcp"
       }
     }
   }
   ```

2. Restart Claude Desktop


### Testing the SSE Server Locally

You can test the SSE server using the MCP Inspector:

1. Start the SSE server:
   ```bash
   uv run server_sse.py
   ```

2. In another terminal, run the MCP Inspector:
   ```bash
   npx @modelcontextprotocol/inspector@latest
   ```

3. The inspector will open at `http://localhost:6274`

4. Select "SSE" as the transport type

5. Enter the server URL: `http://localhost:8002/sse`

6. Click "Connect" to interact with the server and test tools

Alternatively, you can use the simple test client:
```bash
uv run test_sse_client.py
```

## Available Tools

1. `worldbank_search_documents` - primary search with filters
2. `worldbank_get_document_details` - retrieve detailed document information
3. `worldbank_explore_facets` - discover available filter values
4. `worldbank_search_by_project` - find documents by project ID or name

For detailed tool documentation and API usage, see [DESIGN_LOGIC.md](docs/DESIGN_LOGIC.md).

## Development

The codebase follows these principles:

- DRY principle: shared utilities in `core.py`, no code duplication
- pydantic models: automatic validation for all inputs
- async/await: all I/O operations use async patterns
- transport abstraction: business logic separated from transport-specific code
- factory pattern: centralized server creation with dependency injection

See [STRUCTURE_GUIDE.md](docs/STRUCTURE_GUIDE.md) for detailed architecture explanation.

## Code Organization

- `worldbank_dnr_mcp/core.py`: constants, enums, pydantic models, utility functions, formatting helpers
- `worldbank_dnr_mcp/factory.py`: server factory, tool registration
- `worldbank_dnr_mcp/parsers.py`: transport-specific response parsing (only transport-dependent code)
- `server_stdio.py`: STDIO transport wrapper
- `server_sse.py`: SSE transport wrapper

For full architecture breakdown and troubleshooting, see documentation in the `docs/` folder.
