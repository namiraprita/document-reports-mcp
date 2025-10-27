#!/usr/bin/env -S uv run
"""
World Bank Documents & Reports MCP Server (STDIO Transport)

This MCP server provides tools to search and retrieve documents from the World Bank's
Documents & Reports API. It enables LLMs to find research papers, reports, project
documents, and other publications from the World Bank.

This version uses STDIO transport for Claude Desktop and CLI clients.

API Documentation: https://documents.worldbank.org/en/publication/documents-reports/api
"""

import json
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict
from mcp.server.fastmcp import FastMCP

# ============================================================================
# CONSTANTS
# ============================================================================

# Server follows naming convention: {service}_mcp
# This makes it clear which service we're integrating with
mcp = FastMCP("worldbank_mcp")

# World Bank API base URL
API_BASE_URL = "https://search.worldbank.org/api/v3/wds"

# Character limit to prevent overwhelming responses (from MCP best practices)
CHARACTER_LIMIT = 25000

# Default timeout for API requests (in seconds)
REQUEST_TIMEOUT = 30.0

# ============================================================================
# ENUMS AND PYDANTIC MODELS
# ============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses.
    
    MARKDOWN: Human-readable format with headers, lists, and formatting (default)
    JSON: Machine-readable structured data for programmatic processing
    """
    MARKDOWN = "markdown"
    JSON = "json"


class SortOrder(str, Enum):
    """Sort order for results.
    
    ASC: Ascending order (oldest first)
    DESC: Descending order (newest first)
    """
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# INPUT MODELS - Using Pydantic v2 with proper validation
# ============================================================================

class WorldBankSearchInput(BaseModel):
    """Input model for searching World Bank documents.
    
    This model validates all search parameters and provides clear field descriptions
    to help the LLM understand how to use the search effectively.
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,  # Auto-strip whitespace from strings
        validate_assignment=True,    # Validate on assignment
        extra='forbid'              # Forbid extra fields not in schema
    )
    
    query: str = Field(
        ...,  # Required field
        description="Search query to find documents. Searches across title, abstract, report number, project name, and other fields. Examples: 'climate change', 'education reform', 'infrastructure development'",
        min_length=1,
        max_length=500
    )
    
    countries: Optional[List[str]] = Field(
        default=None,
        description="Filter by country names. Examples: ['Kenya', 'Brazil'], ['United States']. Use exact country names.",
        max_items=20
    )
    
    document_types: Optional[List[str]] = Field(
        default=None,
        description="Filter by document type. Examples: ['Procurement Plan', 'Project Appraisal Document', 'Environmental Assessment']. Use explore_facets tool to see available types.",
        max_items=10
    )
    
    languages: Optional[List[str]] = Field(
        default=None,
        description="Filter by language. Examples: ['English', 'Spanish', 'French', 'Arabic']. Use explore_facets tool to see available languages.",
        max_items=5
    )
    
    date_from: Optional[str] = Field(
        default=None,
        description="Start date for documents (format: YYYY-MM-DD or MM-DD-YYYY). Example: '2020-01-01' to find documents from January 2020 onwards.",
        pattern=r'^\d{4}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{4}$'
    )
    
    date_to: Optional[str] = Field(
        default=None,
        description="End date for documents (format: YYYY-MM-DD or MM-DD-YYYY). Example: '2023-12-31' to find documents up to end of 2023.",
        pattern=r'^\d{4}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{4}$'
    )
    
    limit: int = Field(
        default=20,
        description="Maximum number of results to return per page (1-100). Default is 20.",
        ge=1,
        le=100
    )
    
    offset: int = Field(
        default=0,
        description="Number of results to skip for pagination. Use 0 for first page, 20 for second page (if limit=20), etc.",
        ge=0
    )
    
    sort_by: Optional[str] = Field(
        default="docdt",
        description="Field to sort by. Options: 'docdt' (document date), 'repnb' (report number), 'docty' (document type). Default is 'docdt'."
    )
    
    sort_order: SortOrder = Field(
        default=SortOrder.DESC,
        description="Sort order: 'asc' for ascending (oldest first), 'desc' for descending (newest first). Default is 'desc'."
    )
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable format (default), 'json' for machine-readable structured data."
    )


class WorldBankDocumentDetailsInput(BaseModel):
    """Input model for retrieving document details by ID."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    document_id: str = Field(
        ...,
        description="Unique document identifier (ID or GUID). Example: '000333037_20150825102649' or similar ID from search results.",
        min_length=1,
        max_length=200
    )
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable (default), 'json' for machine-readable."
    )


class WorldBankExploreFacetsInput(BaseModel):
    """Input model for exploring available facet values."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    facets: List[str] = Field(
        ...,
        description="Facets to explore. Common options: 'count_exact' (countries), 'lang_exact' (languages), 'docty_exact' (document types), 'majtheme_exact' (major themes), 'topic_exact' (topics). Multiple facets can be requested.",
        min_items=1,
        max_items=10
    )
    
    query: Optional[str] = Field(
        default=None,
        description="Optional search query to filter facet values. If provided, only facets from matching documents are returned.",
        max_length=500
    )
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable (default), 'json' for machine-readable."
    )


class WorldBankProjectSearchInput(BaseModel):
    """Input model for searching documents by project."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    project_id: Optional[str] = Field(
        default=None,
        description="World Bank project ID. Example: 'P123456'. Either project_id or project_name must be provided.",
        max_length=100
    )
    
    project_name: Optional[str] = Field(
        default=None,
        description="Project name to search for. Example: 'Rural Education Project'. Either project_id or project_name must be provided.",
        max_length=500
    )
    
    limit: int = Field(
        default=20,
        description="Maximum number of results to return (1-100). Default is 20.",
        ge=1,
        le=100
    )
    
    offset: int = Field(
        default=0,
        description="Number of results to skip for pagination.",
        ge=0
    )
    
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable (default), 'json' for machine-readable."
    )
    
    @field_validator('project_id')
    @classmethod
    def validate_project_fields(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure at least one of project_id or project_name is provided."""
        # This validator runs for project_id, but we need to check both fields
        # We'll do final validation in the tool function
        return v


# ============================================================================
# SHARED UTILITY FUNCTIONS
# ============================================================================
# Following DRY principle - extract common functionality to avoid duplication
# These utilities are used across multiple tools

async def _make_api_request(
    params: Dict[str, Any],
    timeout: float = REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """Make an HTTP request to the World Bank API.
    
    This is a shared utility function used by all tools to interact with the API.
    It handles:
    - HTTP client creation and cleanup
    - Error handling for network issues
    - Status code validation
    - JSON parsing
    
    Args:
        params: Query parameters for the API request
        timeout: Request timeout in seconds
        
    Returns:
        Parsed JSON response from the API
        
    Raises:
        httpx.HTTPStatusError: If the API returns an error status code
        httpx.RequestError: If there's a network error
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(API_BASE_URL, params=params)
            response.raise_for_status()  # Raise exception for 4xx/5xx status codes
            return response.json()
        except httpx.HTTPStatusError as e:
            # Return structured error for the LLM to understand
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


def _format_document_markdown(doc: Dict[str, Any]) -> str:
    """Format a single document in Markdown format.
    
    Creates human-readable output with:
    - Clear headers and structure
    - Important fields highlighted
    - Human-readable dates (not timestamps)
    - Organized sections
    
    Args:
        doc: Document data from API
        
    Returns:
        Markdown-formatted string
    """
    # Extract key fields with fallbacks
    title = doc.get('display_title', doc.get('repnme', 'Untitled'))
    doc_date = doc.get('docdt', 'N/A')
    doc_type = doc.get('docty', 'N/A')
    doc_id = doc.get('id', doc.get('guid', 'N/A'))
    countries = ', '.join(doc.get('count', [])) if doc.get('count') else 'N/A'
    abstract = doc.get('abstracts', 'No abstract available')
    pdf_url = doc.get('pdfurl', doc.get('url', 'N/A'))
    report_num = doc.get('repnb', 'N/A')
    
    # Build markdown output
    md = f"### {title}\n\n"
    md += f"**Document ID:** {doc_id}\n"
    md += f"**Report Number:** {report_num}\n"
    md += f"**Type:** {doc_type}\n"
    md += f"**Date:** {doc_date}\n"
    md += f"**Countries:** {countries}\n"
    
    # Add optional fields if present
    if doc.get('lang'):
        langs = ', '.join(doc['lang']) if isinstance(doc['lang'], list) else doc['lang']
        md += f"**Languages:** {langs}\n"
    
    if doc.get('majtheme'):
        themes = ', '.join(doc['majtheme']) if isinstance(doc['majtheme'], list) else doc['majtheme']
        md += f"**Major Themes:** {themes}\n"
    
    # Abstract section
    if abstract and abstract != 'No abstract available':
        md += f"\n**Abstract:**\n{abstract}\n"
    
    # URL
    if pdf_url and pdf_url != 'N/A':
        md += f"\n**PDF URL:** {pdf_url}\n"
    
    return md + "\n---\n"


def _format_document_json(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Format a document in JSON structure.
    
    Returns complete structured data suitable for programmatic processing.
    Includes all available fields from the API response.
    
    Args:
        doc: Document data from API
        
    Returns:
        Structured dictionary with document data
    """
    return {
        "id": doc.get('id', doc.get('guid')),
        "title": doc.get('display_title', doc.get('repnme')),
        "report_number": doc.get('repnb'),
        "document_type": doc.get('docty'),
        "document_date": doc.get('docdt'),
        "countries": doc.get('count', []),
        "languages": doc.get('lang', []),
        "abstract": doc.get('abstracts'),
        "major_themes": doc.get('majtheme', []),
        "topics": doc.get('topic', []),
        "pdf_url": doc.get('pdfurl'),
        "url": doc.get('url'),
        "project_id": doc.get('proid'),
        "project_name": doc.get('projn'),
        "sectors": doc.get('sectr_exact', []),
        "keywords": doc.get('keywd', []),
        "authors": doc.get('authr', []),
    }


def _build_query_params(
    query: Optional[str] = None,
    countries: Optional[List[str]] = None,
    document_types: Optional[List[str]] = None,
    languages: Optional[List[str]] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    facets: Optional[List[str]] = None,
    **kwargs
) -> Dict[str, Any]:
    """Build query parameters for the World Bank API.
    
    This utility consolidates parameter building logic to avoid duplication.
    It handles:
    - Multi-value parameters (using ^ separator)
    - Optional parameters
    - Pagination
    - Sorting
    - Facets
    
    Args:
        query: Search query string
        countries: List of country names
        document_types: List of document types
        languages: List of languages
        date_from: Start date
        date_to: End date
        limit: Results per page
        offset: Pagination offset
        sort_by: Sort field
        sort_order: Sort direction
        facets: Facets to retrieve
        **kwargs: Additional parameters
        
    Returns:
        Dictionary of query parameters ready for API request
    """
    params: Dict[str, Any] = {
        "format": "json",  # Always request JSON from API
        "rows": limit,
        "os": offset,
    }
    
    # Add query if provided
    if query:
        params["qterm"] = query
    
    # Add filters using exact match fields
    # Multi-value filters use ^ as separator (URL encoded as %5E)
    if countries:
        params["count_exact"] = "^".join(countries)
    
    if document_types:
        params["docty_exact"] = "^".join(document_types)
    
    if languages:
        params["lang_exact"] = "^".join(languages)
    
    # Add date range filters
    if date_from:
        params["strdate"] = date_from
    
    if date_to:
        params["enddate"] = date_to
    
    # Add sorting
    if sort_by:
        params["srt"] = sort_by
        if sort_order:
            params["order"] = sort_order
    
    # Add facets
    if facets:
        params["fct"] = ",".join(facets)
    
    # Add any additional parameters
    params.update(kwargs)
    
    return params


def _truncate_if_needed(content: str, data: List[Any], limit: int = CHARACTER_LIMIT) -> str:
    """Check response size and truncate if it exceeds the character limit.
    
    This prevents overwhelming the LLM's context window with too much data.
    When truncating, we provide clear guidance on how to get more results.
    
    Args:
        content: Formatted content string
        data: Original data list (for counting)
        limit: Maximum character limit
        
    Returns:
        Content, potentially truncated with a helpful message
    """
    if len(content) <= limit:
        return content
    
    # Truncate content
    truncated = content[:limit]
    
    # Add truncation notice
    notice = f"\n\n**TRUNCATED**: Response exceeded {limit} characters.\n"
    notice += f"Showing partial results. Original had {len(data)} items.\n"
    notice += "To see more results:\n"
    notice += "- Use the 'offset' parameter for pagination\n"
    notice += "- Add more specific filters (countries, document_types, dates)\n"
    notice += "- Reduce the 'limit' parameter\n"
    
    return truncated + notice


# ============================================================================
# MCP TOOLS
# ============================================================================
# Each tool is registered with @mcp.tool decorator
# Tools are named with service prefix to avoid conflicts: worldbank_*
# All tools have proper annotations for the MCP protocol

@mcp.tool(
    name="worldbank_search_documents",
    annotations={
        "title": "Search World Bank Documents",
        "readOnlyHint": True,       # Tool only reads data, doesn't modify anything
        "destructiveHint": False,    # Not applicable since readOnlyHint is True
        "idempotentHint": True,      # Same query returns same results
        "openWorldHint": True        # Interacts with external World Bank API
    }
)
async def worldbank_search_documents(params: WorldBankSearchInput) -> str:
    """Search for documents in the World Bank Documents & Reports database.
    
    This is the primary search tool for finding World Bank publications. It supports:
    - Full-text search across titles, abstracts, and other fields
    - Filtering by country, document type, language, and date range
    - Pagination for large result sets
    - Sorting by different fields
    - Both human-readable (Markdown) and machine-readable (JSON) output formats
    
    Use this tool when you need to:
    - Find documents on specific topics (e.g., "climate change in Africa")
    - Filter documents by criteria (e.g., all Procurement Plans from Kenya since 2020)
    - Browse available documents with pagination
    
    Args:
        params (WorldBankSearchInput): Search parameters including:
            - query (str): Search terms
            - countries (Optional[List[str]]): Filter by country names
            - document_types (Optional[List[str]]): Filter by document types
            - languages (Optional[List[str]]): Filter by languages
            - date_from (Optional[str]): Start date (YYYY-MM-DD)
            - date_to (Optional[str]): End date (YYYY-MM-DD)
            - limit (int): Results per page (1-100, default 20)
            - offset (int): Pagination offset (default 0)
            - sort_by (Optional[str]): Sort field (default 'docdt')
            - sort_order (SortOrder): Sort direction (default 'desc')
            - response_format (ResponseFormat): Output format (default 'markdown')
    
    Returns:
        str: Formatted results in requested format (Markdown or JSON) containing:
            - Total number of matching documents
            - List of documents with key metadata
            - Pagination information
            - Document URLs for accessing full content
    
    Example queries:
        - Find climate change documents: query="climate change"
        - Find Kenya procurement plans: query="procurement", countries=["Kenya"], document_types=["Procurement Plan"]
        - Recent education reports: query="education", date_from="2023-01-01"
    
    Error handling:
        - Returns clear error messages if API is unavailable
        - Provides suggestions for refining queries if no results found
        - Handles invalid parameters gracefully
    """
    try:
        # Build API query parameters using shared utility
        query_params = _build_query_params(
            query=params.query,
            countries=params.countries,
            document_types=params.document_types,
            languages=params.languages,
            date_from=params.date_from,
            date_to=params.date_to,
            limit=params.limit,
            offset=params.offset,
            sort_by=params.sort_by,
            sort_order=params.sort_order.value
        )
        
        # Make API request
        response = await _make_api_request(query_params)
        
        # Extract results
        documents = response.get('documents', {})
        docs_list = documents.get('docs', [])
        total = documents.get('numFound', 0)
        
        # Handle no results case
        if total == 0:
            return (
                "No documents found matching your query.\n\n"
                "Suggestions:\n"
                "- Try broader search terms\n"
                "- Remove some filters\n"
                "- Check spelling of country names or document types\n"
                "- Use the worldbank_explore_facets tool to see available filter values"
            )
        
        # Format results based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            # Build markdown output
            output = f"# World Bank Document Search Results\n\n"
            output += f"**Query:** {params.query}\n"
            output += f"**Total Results:** {total:,}\n"
            output += f"**Showing:** {params.offset + 1}-{params.offset + len(docs_list)} of {total:,}\n"
            
            # Add active filters
            filters = []
            if params.countries:
                filters.append(f"Countries: {', '.join(params.countries)}")
            if params.document_types:
                filters.append(f"Types: {', '.join(params.document_types)}")
            if params.languages:
                filters.append(f"Languages: {', '.join(params.languages)}")
            if params.date_from or params.date_to:
                date_range = f"Dates: {params.date_from or 'any'} to {params.date_to or 'any'}"
                filters.append(date_range)
            
            if filters:
                output += f"**Filters:** {' | '.join(filters)}\n"
            
            output += f"\n---\n\n"
            
            # Add each document
            for doc in docs_list:
                output += _format_document_markdown(doc)
            
            # Add pagination info
            has_more = (params.offset + len(docs_list)) < total
            if has_more:
                next_offset = params.offset + len(docs_list)
                output += f"\n**More results available.** Use offset={next_offset} to see the next page.\n"
            
            # Check for truncation
            output = _truncate_if_needed(output, docs_list)
            
            return output
            
        else:  # JSON format
            # Return structured data
            result = {
                "query": params.query,
                "total": total,
                "count": len(docs_list),
                "offset": params.offset,
                "limit": params.limit,
                "has_more": (params.offset + len(docs_list)) < total,
                "next_offset": params.offset + len(docs_list) if (params.offset + len(docs_list)) < total else None,
                "filters": {
                    "countries": params.countries,
                    "document_types": params.document_types,
                    "languages": params.languages,
                    "date_from": params.date_from,
                    "date_to": params.date_to
                },
                "documents": [_format_document_json(doc) for doc in docs_list]
            }
            
            json_output = json.dumps(result, indent=2)
            
            # Check for truncation
            json_output = _truncate_if_needed(json_output, docs_list)
            
            return json_output
            
    except Exception as e:
        # Return error in a format the LLM can understand and act on
        return f"Error searching World Bank documents: {str(e)}"


@mcp.tool(
    name="worldbank_get_document_details",
    annotations={
        "title": "Get World Bank Document Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def worldbank_get_document_details(params: WorldBankDocumentDetailsInput) -> str:
    """Retrieve detailed information for a specific World Bank document.
    
    Use this tool when you have a document ID from search results and need complete
    details about that document. This returns more comprehensive information than
    the search results, including full abstracts, all metadata fields, and URLs.
    
    Args:
        params (WorldBankDocumentDetailsInput): Input parameters including:
            - document_id (str): Unique document identifier from search results
            - response_format (ResponseFormat): Output format (default 'markdown')
    
    Returns:
        str: Complete document details in requested format including:
            - All metadata (title, dates, authors, etc.)
            - Full abstract
            - Country and regional information
            - Project associations
            - Document URLs
            - Themes and topics
            - All available fields from the API
    
    Example:
        Get details for document '000333037_20150825102649'
    """
    try:
        # Query by document ID
        query_params = _build_query_params(
            limit=1,
            id=params.document_id
        )
        
        # Make API request
        response = await _make_api_request(query_params)
        
        # Extract document
        documents = response.get('documents', {})
        docs_list = documents.get('docs', [])
        
        if not docs_list:
            return (
                f"Document with ID '{params.document_id}' not found.\n\n"
                f"This could mean:\n"
                f"- The document ID is incorrect\n"
                f"- The document has been removed from the database\n"
                f"- The ID format is invalid\n\n"
                f"Try using worldbank_search_documents to find the correct document ID."
            )
        
        doc = docs_list[0]
        
        # Format based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            output = f"# World Bank Document Details\n\n"
            output += _format_document_markdown(doc)
            
            # Add additional detailed fields not shown in search results
            if doc.get('keywd'):
                keywords = ', '.join(doc['keywd']) if isinstance(doc['keywd'], list) else doc['keywd']
                output += f"\n**Keywords:** {keywords}\n"
            
            if doc.get('authr'):
                authors = ', '.join(doc['authr']) if isinstance(doc['authr'], list) else doc['authr']
                output += f"**Authors:** {authors}\n"
            
            if doc.get('sectr_exact'):
                sectors = ', '.join(doc['sectr_exact']) if isinstance(doc['sectr_exact'], list) else doc['sectr_exact']
                output += f"**Sectors:** {sectors}\n"
            
            if doc.get('topic'):
                topics = ', '.join(doc['topic']) if isinstance(doc['topic'], list) else doc['topic']
                output += f"**Topics:** {topics}\n"
            
            return output
            
        else:  # JSON format
            result = _format_document_json(doc)
            return json.dumps(result, indent=2)
            
    except Exception as e:
        return f"Error retrieving document details: {str(e)}"


@mcp.tool(
    name="worldbank_explore_facets",
    annotations={
        "title": "Explore World Bank Document Facets",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def worldbank_explore_facets(params: WorldBankExploreFacetsInput) -> str:
    """Explore available facet values in the World Bank Documents database.
    
    Facets are categories of metadata that can be used for filtering. This tool helps
    discover what values are available for filtering, such as:
    - Which countries have documents
    - What document types exist
    - Available languages
    - Major themes and topics
    
    This is useful for:
    - Discovering what data is available before searching
    - Finding the correct values to use in filters
    - Understanding the scope of the document collection
    
    Args:
        params (WorldBankExploreFacetsInput): Input parameters including:
            - facets (List[str]): Facets to explore. Common options:
                - 'count_exact': Countries
                - 'lang_exact': Languages
                - 'docty_exact': Document types
                - 'majtheme_exact': Major themes
                - 'topic_exact': Topics
                - 'admreg': Administrative regions
            - query (Optional[str]): Filter facets by query
            - response_format (ResponseFormat): Output format (default 'markdown')
    
    Returns:
        str: List of available values for each requested facet with document counts
    
    Example:
        Explore available countries: facets=['count_exact']
        Explore document types: facets=['docty_exact']
        Explore multiple: facets=['count_exact', 'lang_exact', 'docty_exact']
    """
    try:
        # Build query params with facets
        query_params = _build_query_params(
            query=params.query,
            facets=params.facets,
            rows=0  # We don't need actual documents, just facet counts
        )
        
        # Make API request
        response = await _make_api_request(query_params)
        
        # Extract facets from response
        facet_data = response.get('facets', {})
        
        if not facet_data:
            return (
                "No facet data available.\n\n"
                "This could mean:\n"
                "- The requested facets don't exist\n"
                "- The query returned no matching documents\n\n"
                "Common facet names:\n"
                "- count_exact (countries)\n"
                "- lang_exact (languages)\n"
                "- docty_exact (document types)\n"
                "- majtheme_exact (major themes)\n"
                "- topic_exact (topics)"
            )
        
        # Format based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            output = "# World Bank Document Facets\n\n"
            
            if params.query:
                output += f"**Filtered by query:** {params.query}\n\n"
            
            # Process each facet
            for facet_name in params.facets:
                if facet_name not in facet_data:
                    output += f"## {facet_name}\n\n*No data available*\n\n"
                    continue
                
                facet_values = facet_data[facet_name]
                
                # Facet data comes as alternating list: [value1, count1, value2, count2, ...]
                # Convert to list of tuples
                facet_pairs = []
                for i in range(0, len(facet_values), 2):
                    if i + 1 < len(facet_values):
                        value = facet_values[i]
                        count = facet_values[i + 1]
                        facet_pairs.append((value, count))
                
                # Sort by count descending
                facet_pairs.sort(key=lambda x: x[1], reverse=True)
                
                # Display facet
                output += f"## {facet_name}\n\n"
                output += f"Total unique values: {len(facet_pairs)}\n\n"
                
                # Show top values
                for value, count in facet_pairs[:50]:  # Limit to top 50
                    output += f"- **{value}**: {count:,} documents\n"
                
                if len(facet_pairs) > 50:
                    output += f"\n*Showing top 50 of {len(facet_pairs)} total values*\n"
                
                output += "\n"
            
            return output
            
        else:  # JSON format
            result = {"facets": {}}
            
            for facet_name in params.facets:
                if facet_name not in facet_data:
                    result["facets"][facet_name] = []
                    continue
                
                facet_values = facet_data[facet_name]
                
                # Convert to structured format
                facet_pairs = []
                for i in range(0, len(facet_values), 2):
                    if i + 1 < len(facet_values):
                        value = facet_values[i]
                        count = facet_values[i + 1]
                        facet_pairs.append({"value": value, "count": count})
                
                # Sort by count descending
                facet_pairs.sort(key=lambda x: x["count"], reverse=True)
                
                result["facets"][facet_name] = facet_pairs
            
            if params.query:
                result["query"] = params.query
            
            return json.dumps(result, indent=2)
            
    except Exception as e:
        return f"Error exploring facets: {str(e)}"


@mcp.tool(
    name="worldbank_search_by_project",
    annotations={
        "title": "Search World Bank Documents by Project",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True
    }
)
async def worldbank_search_by_project(params: WorldBankProjectSearchInput) -> str:
    """Search for documents related to a specific World Bank project.
    
    World Bank projects often have multiple associated documents (project appraisal,
    implementation status reports, environmental assessments, etc.). This tool finds
    all documents associated with a project.
    
    Use this when you:
    - Know a project ID and want to find all related documents
    - Have a project name and want to find its documentation
    - Need to track documents for a specific project
    
    Args:
        params (WorldBankProjectSearchInput): Input parameters including:
            - project_id (Optional[str]): World Bank project ID (e.g., 'P123456')
            - project_name (Optional[str]): Project name to search for
            - limit (int): Results per page (1-100, default 20)
            - offset (int): Pagination offset (default 0)
            - response_format (ResponseFormat): Output format (default 'markdown')
    
    Returns:
        str: List of documents associated with the project
    
    Note: Either project_id or project_name must be provided.
    
    Example:
        Find documents for project P123456: project_id='P123456'
        Find documents by name: project_name='Rural Education Project'
    """
    try:
        # Validate that at least one of project_id or project_name is provided
        if not params.project_id and not params.project_name:
            return (
                "Error: Either project_id or project_name must be provided.\n\n"
                "Examples:\n"
                "- project_id='P123456'\n"
                "- project_name='Rural Education Project'\n"
                "- Both can be provided for more specific search"
            )
        
        # Build query parameters
        query_params = _build_query_params(
            limit=params.limit,
            offset=params.offset
        )
        
        # Add project filters
        if params.project_id:
            query_params["proid"] = params.project_id
        
        if params.project_name:
            query_params["projn"] = params.project_name
        
        # Make API request
        response = await _make_api_request(query_params)
        
        # Extract results
        documents = response.get('documents', {})
        docs_list = documents.get('docs', [])
        total = documents.get('numFound', 0)
        
        # Handle no results
        if total == 0:
            search_term = params.project_id or params.project_name
            return (
                f"No documents found for project: {search_term}\n\n"
                "This could mean:\n"
                "- The project ID or name is incorrect\n"
                "- The project has no publicly available documents\n"
                "- The project doesn't exist in the database\n\n"
                "Try:\n"
                "- Check the project ID format (usually P followed by numbers)\n"
                "- Search for the project by name using worldbank_search_documents\n"
                "- Use broader search terms"
            )
        
        # Format results based on requested format
        if params.response_format == ResponseFormat.MARKDOWN:
            output = f"# World Bank Project Documents\n\n"
            
            if params.project_id:
                output += f"**Project ID:** {params.project_id}\n"
            if params.project_name:
                output += f"**Project Name:** {params.project_name}\n"
            
            output += f"**Total Documents:** {total:,}\n"
            output += f"**Showing:** {params.offset + 1}-{params.offset + len(docs_list)} of {total:,}\n"
            output += f"\n---\n\n"
            
            # Add each document
            for doc in docs_list:
                output += _format_document_markdown(doc)
            
            # Add pagination info
            has_more = (params.offset + len(docs_list)) < total
            if has_more:
                next_offset = params.offset + len(docs_list)
                output += f"\n**More results available.** Use offset={next_offset} to see the next page.\n"
            
            # Check for truncation
            output = _truncate_if_needed(output, docs_list)
            
            return output
            
        else:  # JSON format
            result = {
                "project_id": params.project_id,
                "project_name": params.project_name,
                "total": total,
                "count": len(docs_list),
                "offset": params.offset,
                "limit": params.limit,
                "has_more": (params.offset + len(docs_list)) < total,
                "next_offset": params.offset + len(docs_list) if (params.offset + len(docs_list)) < total else None,
                "documents": [_format_document_json(doc) for doc in docs_list]
            }
            
            json_output = json.dumps(result, indent=2)
            
            # Check for truncation
            json_output = _truncate_if_needed(json_output, docs_list)
            
            return json_output
            
    except Exception as e:
        return f"Error searching by project: {str(e)}"


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server using stdio transport
    # This transport is used by Claude Desktop and other CLI MCP clients
    # that communicate via standard input/output
    mcp.run(transport="stdio")
