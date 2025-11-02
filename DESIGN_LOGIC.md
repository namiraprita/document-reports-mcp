# World Bank MCP Server - Design & Logic Explained

This document explains the **why** behind every design decision in the World Bank MCP server, following Anthropic's MCP builder skills.

**Last Updated:** Reflects the latest implementation with FastMCP, multi-transport support, and Pydantic v2.

## Core Design Principles

### 1. **Agent-Centric, Not API-Centric**

**The Logic:**
Instead of just wrapping every API endpoint, we designed tools around **workflows** that LLMs actually need to complete.

**Example:**
```python
# ❌ Bad: Just wrapping API endpoints
@mcp.tool()
def get_documents_by_query(query: str): ...

@mcp.tool()
def get_documents_by_country(country: str): ...

@mcp.tool()
def get_documents_by_date(date: str): ...

# ✅ Good: Workflow-oriented tool
@mcp.tool()
def worldbank_search_documents(
    query: str,
    countries: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    # ... all filters in one coherent tool
): ...
```

**Why this matters:**
- LLMs think in terms of "find documents about X with these constraints"
- Not "first query by X, then filter by Y, then..."
- Reduces tool calls needed (1 instead of 3-4)
- More context-efficient

### 2. **Context Window is Precious**

**The Logic:**
LLMs have limited context. Every character counts. We optimize for **high-signal, low-noise** responses.

**Implementation:**
```python
# prevent overwhelming responses. 
#TODO: reiteration on rule of thumbs 
CHARACTER_LIMIT = 25000  

def _truncate_if_needed(content: str, data: List[Any]) -> str:
    if len(content) > CHARACTER_LIMIT:
        # truncate but provide actionable guidance
        notice = "Use offset/filters to see more results"
        return truncated_content + notice
```

**Markdown vs JSON:**
```python
# Using Enum for type safety
class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"  # Human optimized
    JSON = "json"          # Machine optimized

# Markdown (default) - Human optimized
"""
### Project Report on Climate Adaptation
**Date:** 2024-01-15
**Countries:** Kenya, Tanzania
"""

# JSON - Machine optimized
{
  "title": "Project Report on Climate Adaptation",
  "document_date": "2024-01-15",
  "countries": ["Kenya", "Tanzania"]
}
```

**Why:**
- Markdown is more readable when presenting to users
- JSON is better when LLM needs to process data programmatically
- Enum ensures type safety and clear options
- Default to markdown (most common use case)

## Architecture Decisions

### API Integration Details

**World Bank API Endpoint:**
```
https://search.worldbank.org/api/v3/wds
```

**API Parameter Mapping:**
- Our `query` → API `qterm`
- Our `limit` → API `rows`
- Our `offset` → API `os`
- Our `countries` → API `count_exact` (multi-value with `^` separator)
- Our `document_types` → API `docty_exact` (multi-value with `^` separator)
- Our `languages` → API `lang_exact` (multi-value with `^` separator)
- Our `date_from` → API `strdate`
- Our `date_to` → API `enddate`
- Our `sort_by` → API `srt`
- Our `sort_order` → API `order`

**Response Structure:**
```python
{
  "total": 15000,
  "documents": {
    "D33234291": {...},  # Document ID as key
    "D40008089": {...},
    "facets": {...}      # Facets embedded (filtered out)
  }
}
```

**Why This Mapping?**
- API uses different parameter names than user-friendly names
- Multi-value filters need `^` separator (URL encoded as `%5E`)
- Documents returned as dict with IDs as keys (not array)
- Need to extract and filter out `facets` key from documents dict

### Why 4 Tools (Not 1, Not 20)?

**Tool 1: `worldbank_search_documents`**
- **Purpose:** Primary search with all filtering options
- **Covers:** 80% of use cases
- **Logic:** Users usually start with "find documents about X"
- **Input Model:** `WorldBankSearchInput`

**Tool 2: `worldbank_get_document_details`**
- **Purpose:** Deep dive into specific document
- **Covers:** Follow-up after search
- **Logic:** After finding a document, users want complete details
- **Input Model:** `WorldBankDocumentDetailsInput`

**Tool 3: `worldbank_explore_facets`**
- **Purpose:** Discovery - what can I filter by?
- **Covers:** "What document types exist?"
- **Logic:** Helps LLM learn what's available before searching
- **Input Model:** `WorldBankExploreFacetsInput`

**Tool 4: `worldbank_search_by_project`**
- **Purpose:** Project-centric workflow
- **Covers:** "Find all docs for project P123456"
- **Logic:** Projects are a natural organizational unit
- **Input Model:** `WorldBankProjectSearchInput`

**Why not more tools?**
- Each additional tool increases cognitive load
- Similar operations consolidated (e.g., all search in one tool)
- LLMs perform better with fewer, more powerful tools

**Why not fewer tools?**
- Each tool has a distinct workflow/purpose
- Combining them would make parameters confusing
- Separation allows for focused docstrings

## Server Architecture

### Multi-Transport Support

**The Current Structure:**
```
document-reports-mcp/
├── start_server_claude.py      # Launcher for Claude Desktop
├── server_stdio.py              # STDIO transport (default)
├── server_sse.py                # SSE transport (web/API)
└── worldbank_dnr_mcp.py         # Original standalone script
```

**Why Multiple Files?**
- **Separation of concerns**: Each transport type has its own file
- **Different use cases**: STDIO for local clients, SSE for web/remote access
- **Easy maintenance**: Transport-specific logic isolated
- **Follows best practices**: Matches structure of reference implementations

**FastMCP Usage:**
```python
# STDIO version
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("worldbank_mcp")

# SSE version
mcp = FastMCP("worldbank_mcp", port=8002)
```

**Why FastMCP?**
- Modern MCP SDK with better performance
- Built-in transport handling (STDIO, SSE)
- Simplified server setup
- Better error handling and logging

## Code Architecture

### DRY Principle: Shared Utilities

**The Problem:**
Without shared utilities, we'd duplicate code across tools.

**The Solution:**
```python
# ✅ shared utility - used by all tools
API_BASE_URL = "https://search.worldbank.org/api/v3/wds"

async def _make_api_request(
    params: Dict[str, Any],
    timeout: float = REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """Single HTTP client, error handling, JSON parsing"""
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(API_BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
```

**Why async?**
```python
# ❌ synchronous blocks the entire server
def make_request(url):
    response = requests.get(url)  # blocks
    return response.json()

# ✅ asynchronous allows concurrent requests
async def make_request(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # non-blocking
        return response.json()
```

**Benefits:**
- Server can handle multiple tool calls concurrently
- Better performance for LLMs making multiple calls
- Follows modern Python async/await patterns

### Pydantic Models: Validation is Free

**The Logic:**
Instead of manual validation, we define constraints once in Pydantic models.

**Using Pydantic v2:**
```python
# ❌ manual validation (error-prone, verbose)
def search(query: str, limit: int):
    if not query:
        raise ValueError("Query required")
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be 1-100")
    if not isinstance(query, str):
        raise TypeError("Query must be string")
    # ... search logic

# ✅ pydantic v2 validation (automatic, declarative)
from pydantic import BaseModel, Field, ConfigDict

class WorldBankSearchInput(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Auto-strip whitespace
        validate_assignment=True,    # Validate on assignment
        extra='forbid'              # No extra fields allowed
    )
    
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    # validation happens automatically!

@mcp.tool()
async def worldbank_search_documents(params: WorldBankSearchInput):
    # params is already validated!
    # just use the values
```

**Pydantic v2 Features We Use:**
- `ConfigDict`: Modern configuration approach
- `str_strip_whitespace=True`: Auto-clean user input
- `extra='forbid'`: Prevents unexpected fields
- Type validation: Automatic type checking
- Field constraints: `ge`, `le`, `min_length`, `max_length`

**Benefits:**
- Zero validation code needed
- Clear field descriptions for LLMs
- Automatic JSON schema generation
- Type safety throughout

### Error Messages: Guide, Don't Just Inform

**Bad error messages:**
```python
"Error: 404"
"Invalid parameter"
"Request failed"
```

**Good error messages (what we do):**
```python
"Document with ID 'X' not found.\n\n"
"This could mean:\n"
"- The document ID is incorrect\n"
"- The document has been removed\n\n"
"Try using worldbank_search_documents to find the correct ID."
```

**The Logic:**
LLMs can't just "figure it out" - they need:
1. What went wrong
2. Why it might have happened
3. What to do next

This turns errors into **learning opportunities** for the LLM.

## Response Format Strategy

### Markdown for Humans, JSON for Machines

**When to use Markdown:**
```
User: "Show me climate change reports"
→ Markdown output (readable, scannable, links)
```

**When to use JSON:**
```
User: "Find 50 documents and create a spreadsheet analyzing them by country"
→ JSON output (structured, processable)
```

**Implementation:**
```python
class ResponseFormat(str, Enum):
    MARKDOWN = "markdown"  # Default
    JSON = "json"          # For processing
```

**The Format Decision Tree:**
1. Is LLM presenting to user? → Markdown
2. Is LLM processing data further? → JSON
3. Not sure? → Markdown (default)

### Pagination Strategy

**The Challenge:**
World Bank has millions of documents. Can't return all at once.

**Our Solution:**
```python
{
  "total": 15000,           # total matching documents
  "count": 20,              # documents in this response
  "offset": 0,              # current position
  "has_more": true,         # more results available
  "next_offset": 20,        # what to use for next page
  "documents": [...]
}
```

**Why this works:**
- LLM knows total scope ("15,000 documents found")
- LLM knows current position ("showing 1-20")
- LLM knows how to get more ("use offset=20")
- Clear stopping condition ("has_more=false")

## Tool Annotations Explained

```python
@mcp.tool(
    name="worldbank_search_documents",
    annotations={
        "title": "Search World Bank Documents",
        "readOnlyHint": True,       # doesn't modify data
        "destructiveHint": False,    # not applicable for read-only
        "idempotentHint": True,      # same query = same results
        "openWorldHint": True        # calls external API
    }
)
```

**What these mean:**

**`readOnlyHint: True`**
- Tool only reads data, never modifies
- Claude Desktop can show these differently
- Safe to call repeatedly

**`destructiveHint: False`**
- Tool won't delete or modify data
- Only meaningful when readOnlyHint is false
- For our search tool, not applicable

**`idempotentHint: True`**
- Same inputs = same outputs
- Safe to retry on failure
- Caching-friendly

**`openWorldHint: True`**
- Interacts with external systems (World Bank API)
- Results may vary over time as data changes
- Requires internet connection

## Naming Strategy

### Server Name: `worldbank_mcp`

**Following the pattern:** `{service}_mcp`

**Why:**
- Clear what service this integrates with
- Consistent with other MCP servers (slack_mcp, github_mcp)
- Not tied to specific features (future-proof)

### Tool Names: `worldbank_*`

**Pattern:** `{service}_{action}_{resource}`

**Examples:**
- `worldbank_search_documents`
- `worldbank_get_document_details`
- `worldbank_explore_facets`

**Why prefix with service?**
```python
# ❌ Without prefix
@mcp.tool(name="search_documents")  # Conflicts with other servers!

# ✅ With prefix
@mcp.tool(name="worldbank_search_documents")  # Unique, clear
```

Users often run multiple MCP servers. Prefixes prevent naming conflicts.

## Parameter Design Philosophy

### Required vs Optional

**Required parameters:**
```python
query: str = Field(...)  # Required - no default
```
- Must provide meaningful results
- No sensible default exists
- Core to the operation

**Optional parameters:**
```python
limit: int = Field(default=20, ge=1, le=100)
```
- Has sensible default
- Refines results but not required
- Progressive enhancement

### Constraint Philosophy

```python
query: str = Field(
    ...,
    description="Search query to find documents. Searches across title, abstract, report number, project name, and other fields. Examples: 'climate change', 'education reform', 'infrastructure development'",
    min_length=1,        # at least one character
    max_length=500        # prevent abuse/errors
)

limit: int = Field(
    default=20,
    description="Maximum number of results to return per page (1-100). Default is 20.",
    ge=1,                # greater than or equal to 1
    le=100               # less than or equal to 100
)

# Enum for type-safe choices
sort_order: SortOrder = Field(
    default=SortOrder.DESC,
    description="Sort order: 'asc' for ascending (oldest first), 'desc' for descending (newest first). Default is 'desc'."
)
```

**Additional Constraints:**
- `countries: max_items=20` - Prevents excessive filter lists
- `document_types: max_items=10` - Reasonable limit for document types
- `languages: max_items=5` - Typical language count
- `facets: min_items=1, max_items=10` - Must request at least one facet

**Why these constraints?**
- `min_length=1`: Empty queries are meaningless
- `max_length=500`: API limitations + reasonable query length
- `ge=1`: Can't request 0 or negative results
- `le=100`: Protects context window, API fair use

## Performance Optimizations

### 1. Async Everything

```python
# All I/O operations use async/await
async def _make_api_request(...)  # HTTP request
async def worldbank_search_documents(...)  # Tool function
```

**Why:**
- Non-blocking I/O
- Server can handle multiple requests concurrently
- Better resource utilization
- FastMCP handles async naturally

### 2. Single HTTP Client Per Request

```python
REQUEST_TIMEOUT = 30.0

async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
    response = await client.get(API_BASE_URL, params=params)
    # automatically closes after with block
```

**Benefits:**
- Connection pooling
- Automatic cleanup
- Proper timeout handling (30 seconds default)
- Prevents hanging requests

### 3. Error Handling Strategy

```python
async def _make_api_request(...):
    try:
        response = await client.get(API_BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise Exception(
            f"World Bank API returned error {e.response.status_code}: {e.response.text}. "
            f"This usually means invalid parameters or the API is unavailable. "
            f"Try adjusting your search parameters or try again later."
        )
    except httpx.RequestError as e:
        raise Exception(
            f"Network error connecting to World Bank API: {str(e)}. "
            f"Check your internet connection and try again."
        )
```

**Why structured error messages?**
- LLMs can understand what went wrong
- Provides actionable guidance
- Distinguishes between API errors and network errors

### 4. Character Limits Prevent Overwhelm

```python
def _truncate_if_needed(content: str, data: List[Any], limit: int = CHARACTER_LIMIT) -> str:
    """Check response size and truncate if it exceeds the character limit."""
    if len(content) <= limit:
        return content
    
    truncated = content[:limit]
    notice = f"\n\n**TRUNCATED**: Response exceeded {limit} characters.\n"
    notice += f"Showing partial results. Original had {len(data)} items.\n"
    notice += "To see more results:\n"
    notice += "- Use the 'offset' parameter for pagination\n"
    notice += "- Add more specific filters (countries, document_types, dates)\n"
    notice += "- Reduce the 'limit' parameter\n"
    
    return truncated + notice
```

**Why 25,000 characters?**
- Based on MCP best practices
- ~6,000 tokens (depending on content)
- Leaves room for other context
- Rarely hit with reasonable limits (20-50 results)
- Truncation message guides LLM on how to get more results

### 5. Document Formatting Utilities

**Two formatting functions for consistency:**

```python
def _format_document_markdown(doc: Dict[str, Any]) -> str:
    """Format single document in Markdown."""
    # Handles edge cases:
    # - Missing fields (defaults to 'N/A')
    # - Nested structures (abstracts.cdata!)
    # - String vs list fields (countries, languages)
    # - Multiple title sources (display_title, repnme)

def _format_document_json(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Format single document in JSON structure."""
    # Returns structured dict with all fields
    # Consistent field names across all documents
    # Handles type variations gracefully
```

**Why separate functions?**
- Reusable across all tools
- Consistent formatting
- Handles API response variations (missing fields, nested structures)
- Easy to maintain and update

### 6. Query Parameter Building

```python
def _build_query_params(...) -> Dict[str, Any]:
    """Build query parameters for the World Bank API."""
    # Handles:
    # - Multi-value parameters (^ separator)
    # - Optional parameters
    # - Pagination (rows, os)
    # - Sorting (srt, order)
    # - Facets (fct)
    # - Always sets format=json
```

**Why a separate function?**
- Single source of truth for parameter mapping
- Handles API-specific quirks (^ separator, parameter names)
- Reusable across all tools
- Easy to update if API changes

## Documentation Strategy

### Triple Documentation Approach

**1. Pydantic Field Descriptions**
```python
query: str = Field(
    ...,
    description="Search query (e.g., 'climate change')"
)
```
→ LLM sees this in JSON schema

**2. Tool Docstrings**
```python
async def worldbank_search_documents(params: SearchInput) -> str:
    """Search for documents in the World Bank database.
    
    This tool enables finding publications by topic, country, type...
    """
```
→ LLM sees this as tool description

**3. README Documentation**
- Human-readable guide
- Examples and use cases
- Troubleshooting

## Design Lessons Applied

### From MCP Best Practices

✅ **Server naming:** `worldbank_mcp` format
✅ **Tool prefixes:** All tools start with `worldbank_`
✅ **Response formats:** Support both markdown and JSON
✅ **Pagination:** Consistent pattern with metadata
✅ **Character limits:** 25,000 with truncation messages
✅ **Error handling:** Actionable, educational errors
✅ **Tool annotations:** Proper hints for all tools

### From Agent-Centric Design

✅ **Workflow tools:** Not just API wrappers
✅ **Context efficiency:** Defaults optimize for readability
✅ **Smart defaults:** Minimize required parameters
✅ **Composable operations:** Tools work together naturally

### From Python Best Practices

✅ **Type hints:** Throughout the code
✅ **Async/await:** All I/O operations
✅ **Pydantic v2:** Modern validation patterns
✅ **DRY principle:** Shared utilities, no duplication
✅ **Error handling:** Specific exceptions, clear messages

## Modern Development Practices

### UV Integration

**Why UV?**
```bash
#!/usr/bin/env -S uv run
# Instead of:
#!/usr/bin/env python3
```

**Benefits:**
- Automatic dependency management
- 10-100x faster than pip
- Isolated environments per project
- No manual virtual environment setup
- Reproducible builds

**Usage:**
```bash
# Run directly
uv run server_stdio.py

# Or with shebang
./server_stdio.py  # Automatically uses uv
```

### Multi-Transport Architecture

**STDIO Transport** (`server_stdio.py`):
- For Claude Desktop
- For CLI tools
- Fast, local communication
- Uses standard input/output

**SSE Transport** (`server_sse.py`):
- For web applications
- For remote access
- Runs on port 8002
- Multiple clients can connect

**Launcher Script** (`start_server_claude.py`):
- Entry point for Claude Desktop
- Error handling
- Path management
- Graceful startup

## Future Enhancements (Ideas)

If you wanted to expand this server:

1. **Advanced Search Tool**
   - Complex boolean queries
   - Wildcard support
   - Field-specific search

2. **Bulk Operations**
   - Download multiple PDFs
   - Compare documents
   - Generate reports

3. **Caching Layer**
   - Cache common queries
   - Reduce API calls
   - Faster responses

4. **Analytics Tool**
   - Trends over time
   - Country comparisons
   - Document type analysis

5. **Resource Registration**
   - Expose documents as MCP resources
   - Allow direct URI access
   - Template-based retrieval

6. **Real-time Updates**
   - SSE streaming for long queries
   - Progress indicators
   - Incremental result delivery

## Implementation Details

### Response Parsing

**API Response Structure:**
```python
response = {
    "total": 578496,
    "documents": {
        "D34442285": {...},  # Minimal fields
        "D40008089": {...},  # Full fields
        "facets": {...}      # Need to filter out
    }
}
```

**Our Parsing Logic:**
```python
documents = response.get('documents', {})
docs_list = [
    doc for key, doc in documents.items() 
    if key != 'facets' and isinstance(doc, dict)
]
total = response.get('total', 0)
```

**Why this approach?**
- API returns documents as dict, not array
- Need to filter out `facets` key
- Handle both minimal and full document structures
- Graceful handling of missing fields

### Field Handling Edge Cases

**Nested Abstracts:**
```python
abstracts = doc.get('abstracts', 'No abstract available')
if isinstance(abstracts, dict):
    abstract = abstracts.get('cdata!', abstracts.get('abstract', 'No abstract available'))
```

**Multiple Title Sources:**
```python
repnme = doc.get('repnme', {})
if isinstance(repnme, dict):
    repnme = repnme.get('repnme', 'Untitled')
title = doc.get('display_title', repnme)
```

**Countries (String or List):**
```python
count = doc.get('count', 'N/A')
if isinstance(count, list):
    countries = ', '.join(count)
elif isinstance(count, str):
    countries = count
else:
    countries = 'N/A'
```

**Why handle all these cases?**
- API responses vary by document
- Some fields missing in minimal responses
- Some fields nested in different structures
- Type variations (string vs list vs dict)
- Defensive programming ensures reliability

## Learning Resources

To understand why we made these choices:

1. **MCP Protocol**: https://modelcontextprotocol.io/
2. **Anthropic Skills**: https://github.com/anthropics/skills
3. **Pydantic v2 Docs**: https://docs.pydantic.dev/latest/
4. **HTTPX Docs**: https://www.python-httpx.org/
5. **World Bank API**: https://documents.worldbank.org/en/publication/documents-reports/api
6. **FastMCP**: MCP SDK documentation
7. **UV Package Manager**: https://github.com/astral-sh/uv

---

## Summary: The Core Logic

1. **Think workflows, not endpoints** → Fewer, more powerful tools
2. **Optimize for LLM context** → Readable defaults, structured options
3. **Make errors educational** → Guide the LLM to success
4. **Share code liberally** → DRY principle throughout
5. **Validate automatically** → Pydantic v2 does the work
6. **Document thoroughly** → Fields, docstrings, README
7. **Follow standards** → MCP best practices, Python patterns
8. **Handle edge cases defensively** → Graceful defaults, type checking
9. **Support multiple transports** → STDIO for local, SSE for web
10. **Use modern tooling** → UV for dependencies, FastMCP for server

**Key Technical Details:**
- **API Endpoint**: `https://search.worldbank.org/api/v3/wds`
- **Framework**: FastMCP with async/await
- **Validation**: Pydantic v2 with `ConfigDict`
- **Transports**: STDIO (default) and SSE (port 8002)
- **Dependency Management**: UV with `#!/usr/bin/env -S uv run`
- **Response Format**: Supports both Markdown (default) and JSON
- **Error Handling**: Structured, actionable error messages

This creates an MCP server that's:
- Easy for LLMs to use
- Easy for developers to maintain
- Easy for users to understand
- Ready for production use
- Robust against API variations
- Modern and maintainable

Built with these principles, your MCP server becomes a natural extension of the LLM's capabilities!
