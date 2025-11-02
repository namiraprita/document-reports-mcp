"""
Core business logic for World Bank Documents & Reports MCP Server.

This module contains all shared code used by both STDIO and SSE transports:
- Constants
- Enums
- Pydantic models
- Utility functions
- Tool logic (without transport-specific parts)
"""

import json
from typing import Optional, List, Dict, Any, Callable
from enum import Enum

import httpx
from pydantic import BaseModel, Field, field_validator, ConfigDict


# ============================================================================
# CONSTANTS
# ============================================================================

API_BASE_URL = "https://search.worldbank.org/api/v3/wds"
CHARACTER_LIMIT = 25000
REQUEST_TIMEOUT = 30.0


# ============================================================================
# ENUMS
# ============================================================================

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"


class SortOrder(str, Enum):
    """Sort order for results."""
    ASC = "asc"
    DESC = "desc"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class WorldBankSearchInput(BaseModel):
    """Input model for searching World Bank documents."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    query: str = Field(
        ...,
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
        return v


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def make_api_request(
    params: Dict[str, Any],
    timeout: float = REQUEST_TIMEOUT
) -> Dict[str, Any]:
    """Make an HTTP request to the World Bank API."""
    async with httpx.AsyncClient(timeout=timeout) as client:
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


def format_document_markdown(doc: Dict[str, Any]) -> str:
    """Format a single document in Markdown format."""
    title = doc.get('display_title', doc.get('repnme', 'Untitled'))
    doc_date = doc.get('docdt', 'N/A')
    doc_type = doc.get('docty', 'N/A')
    doc_id = doc.get('id', doc.get('guid', 'N/A'))
    countries = ', '.join(doc.get('count', [])) if doc.get('count') else 'N/A'
    abstract = doc.get('abstracts', 'No abstract available')
    pdf_url = doc.get('pdfurl', doc.get('url', 'N/A'))
    report_num = doc.get('repnb', 'N/A')
    
    md = f"### {title}\n\n"
    md += f"**Document ID:** {doc_id}\n"
    md += f"**Report Number:** {report_num}\n"
    md += f"**Type:** {doc_type}\n"
    md += f"**Date:** {doc_date}\n"
    md += f"**Countries:** {countries}\n"
    
    if doc.get('lang'):
        langs = ', '.join(doc['lang']) if isinstance(doc['lang'], list) else doc['lang']
        md += f"**Languages:** {langs}\n"
    
    if doc.get('majtheme'):
        themes = ', '.join(doc['majtheme']) if isinstance(doc['majtheme'], list) else doc['majtheme']
        md += f"**Major Themes:** {themes}\n"
    
    if abstract and abstract != 'No abstract available':
        md += f"\n**Abstract:**\n{abstract}\n"
    
    if pdf_url and pdf_url != 'N/A':
        md += f"\n**PDF URL:** {pdf_url}\n"
    
    return md + "\n---\n"


def format_document_json(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Format a document in JSON structure."""
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


def build_query_params(
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
    """Build query parameters for the World Bank API."""
    params: Dict[str, Any] = {
        "format": "json",
        "rows": limit,
        "os": offset,
    }
    
    if query:
        params["qterm"] = query
    
    if countries:
        params["count_exact"] = "^".join(countries)
    
    if document_types:
        params["docty_exact"] = "^".join(document_types)
    
    if languages:
        params["lang_exact"] = "^".join(languages)
    
    if date_from:
        params["strdate"] = date_from
    
    if date_to:
        params["enddate"] = date_to
    
    if sort_by:
        params["srt"] = sort_by
        if sort_order:
            params["order"] = sort_order
    
    if facets:
        params["fct"] = ",".join(facets)
    
    params.update(kwargs)
    
    return params


def truncate_if_needed(content: str, data: List[Any], limit: int = CHARACTER_LIMIT) -> str:
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
