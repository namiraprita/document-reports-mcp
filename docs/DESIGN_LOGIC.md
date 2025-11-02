# Design & Logic Explained

This document explains the **why** behind every design decision in the World Bank MCP server, following Anthropic's MCP builder skills.

## Core Design Principles

### 1. **Agent-Centric, Not API-Centric**

**The Logic:**
Instead of just wrapping every API endpoint, we designed tools around **workflows** that LLMs actually need to complete.

**Example:**
```python
# Just wrapping API endpoints
@mcp.tool()
def get_documents_by_query(query: str): ...

@mcp.tool()
def get_documents_by_country(country: str): ...

@mcp.tool()
def get_documents_by_date(date: str): ...

# GOOD: Workflow-oriented tool
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
CHARACTER_LIMIT = 25000  # Prevent overwhelming responses

def _truncate_if_needed(content: str, data: List[Any]) -> str:
    if len(content) > CHARACTER_LIMIT:
        # Truncate but provide actionable guidance
        notice = "Use offset/filters to see more results"
        return truncated_content + notice
```

**Markdown vs JSON:**
```python
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
- We support both, defaulting to markdown

## Architecture Decisions

### Why 4 Tools (Not 1, Not 20)?

**Tool 1: `worldbank_search_documents`**
- **Purpose:** Primary search with all filtering options
- **Covers:** 80% of use cases
- **Logic:** Users usually start with "find documents about X"

**Tool 2: `worldbank_get_document_details`**
- **Purpose:** Deep dive into specific document
- **Covers:** Follow-up after search
- **Logic:** After finding a document, users want complete details

**Tool 3: `worldbank_explore_facets`**
- **Purpose:** Discovery - what can I filter by?
- **Covers:** "What document types exist?"
- **Logic:** Helps LLM learn what's available before searching

**Tool 4: `worldbank_search_by_project`**
- **Purpose:** Project-centric workflow
- **Covers:** "Find all docs for project P123456"
- **Logic:** Projects are a natural organizational unit

**Why not more tools?**
- Each additional tool increases cognitive load
- Similar operations consolidated (e.g., all search in one tool)
- LLMs perform better with fewer, more powerful tools

**Why not fewer tools?**
- Each tool has a distinct workflow/purpose
- Combining them would make parameters confusing
- Separation allows for focused docstrings

## Code Architecture

### DRY Principle: Shared Utilities

**The Problem:**
Without shared utilities, we'd duplicate code across tools.

**The Solution:**
```python
# GOOD: Shared utility - used by all tools
async def _make_api_request(params: Dict[str, Any]) -> Dict[str, Any]:
    """Single HTTP client, error handling, JSON parsing"""
    async with httpx.AsyncClient() as client:
        response = await client.get(API_BASE_URL, params=params)
        response.raise_for_status()
        return response.json()
```

**Why async?**
```python
# Synchronous blocks the entire server
def make_request(url):
    response = requests.get(url)  # Blocks
    return response.json()

# GOOD: Asynchronous allows concurrent requests
async def make_request(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)  # Non-blocking
        return response.json()
```

**Benefits:**
- Server can handle multiple tool calls concurrently
- Better performance for LLMs making multiple calls
- Follows modern Python async/await patterns

### Pydantic Models: Validation is Free

**The Logic:**
Instead of manual validation, we define constraints once in Pydantic models.

```python
# Manual validation (error-prone, verbose)
def search(query: str, limit: int):
    if not query:
        raise ValueError("Query required")
    if limit < 1 or limit > 100:
        raise ValueError("Limit must be 1-100")
    if not isinstance(query, str):
        raise TypeError("Query must be string")
    # ... search logic

# GOOD: Pydantic validation (automatic, declarative)
class SearchInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(default=20, ge=1, le=100)
    # Validation happens automatically!

@mcp.tool()
async def search(params: SearchInput):
    # params is already validated!
    # Just use the values
```

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
  "total": 15000,           # Total matching documents
  "count": 20,              # Documents in this response
  "offset": 0,              # Current position
  "has_more": true,         # More results available
  "next_offset": 20,        # What to use for next page
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
        "readOnlyHint": True,       # Doesn't modify data
        "destructiveHint": False,    # Not applicable for read-only
        "idempotentHint": True,      # Same query = same results
        "openWorldHint": True        # Calls external API
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
# Without prefix
@mcp.tool(name="search_documents")  # Conflicts with other servers!

# GOOD: With prefix
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
    description="Search query (e.g., 'climate change')",
    min_length=1,        # At least one character
    max_length=500       # Prevent abuse/errors
)

limit: int = Field(
    default=20,
    ge=1,                # Greater than or equal to 1
    le=100               # Less than or equal to 100
)
```

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
- Server can handle multiple requests
- Better resource utilization

### 2. Single HTTP Client Per Request

```python
async with httpx.AsyncClient(timeout=30.0) as client:
    # Use client
    # Automatically closes after with block
```

**Benefits:**
- Connection pooling
- Automatic cleanup
- Proper timeout handling

### 3. Character Limits Prevent Overwhelm

```python
if len(result) > CHARACTER_LIMIT:
    # Truncate with clear guidance
```

**Why 25,000 characters?**
- Based on MCP best practices
- ~6,000 tokens (depending on content)
- Leaves room for other context
- Rarely hit with reasonable limits (20-50 results)

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

APPLIED: **Server naming:** `worldbank_mcp` format
APPLIED: **Tool prefixes:** All tools start with `worldbank_`
APPLIED: **Response formats:** Support both markdown and JSON
APPLIED: **Pagination:** Consistent pattern with metadata
APPLIED: **Character limits:** 25,000 with truncation messages
APPLIED: **Error handling:** Actionable, educational errors
APPLIED: **Tool annotations:** Proper hints for all tools

### From Agent-Centric Design

APPLIED: **Workflow tools:** Not just API wrappers
APPLIED: **Context efficiency:** Defaults optimize for readability
APPLIED: **Smart defaults:** Minimize required parameters
APPLIED: **Composable operations:** Tools work together naturally

### From Python Best Practices

APPLIED: **Type hints:** Throughout the code
APPLIED: **Async/await:** All I/O operations
APPLIED: **Pydantic v2:** Modern validation patterns
APPLIED: **DRY principle:** Shared utilities, no duplication
APPLIED: **Error handling:** Specific exceptions, clear messages

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

## Learning Resources

To understand why we made these choices:

1. **MCP Protocol**: https://modelcontextprotocol.io/
2. **Anthropic Skills**: https://github.com/anthropics/skills
3. **Pydantic Docs**: https://docs.pydantic.dev/
4. **HTTPX Docs**: https://www.python-httpx.org/
5. **World Bank API**: https://documents.worldbank.org/en/publication/documents-reports/api

---

## Summary: The Core Logic

1. **Think workflows, not endpoints** → Fewer, more powerful tools
2. **Optimize for LLM context** → Readable defaults, structured options
3. **Make errors educational** → Guide the LLM to success
4. **Share code liberally** → DRY principle throughout
5. **Validate automatically** → Pydantic does the work
6. **Document thoroughly** → Fields, docstrings, README
7. **Follow standards** → MCP best practices, Python patterns

This creates an MCP server that's:
- Easy for LLMs to use
- Easy for developers to maintain
- Easy for users to understand
- Ready for production use

Built with these principles, your MCP server becomes a natural extension of the LLM's capabilities!
