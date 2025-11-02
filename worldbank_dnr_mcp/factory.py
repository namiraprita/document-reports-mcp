"""
Factory for creating World Bank MCP servers with different transport configurations.

This module handles server creation and tool registration, injecting the
transport-specific response parser into the tools.
"""

import json
from typing import Optional, Callable, Tuple, List, Dict, Any

from mcp.server.fastmcp import FastMCP

from .core import (
    WorldBankSearchInput,
    WorldBankDocumentDetailsInput,
    WorldBankExploreFacetsInput,
    WorldBankProjectSearchInput,
    ResponseFormat,
    make_api_request,
    format_document_markdown,
    format_document_json,
    build_query_params,
    truncate_if_needed,
)


def create_worldbank_server(
    transport: str,
    port: Optional[int] = None,
    response_parser: Optional[Callable[[Dict[str, Any]], Tuple[List[Dict], int]]] = None
) -> FastMCP:
    """
    Create a World Bank MCP server with specified transport configuration.
    
    This factory eliminates duplication by:
    1. Creating server with appropriate transport settings
    2. Injecting transport-specific response parser
    3. Registering all tools with shared business logic
    
    Args:
        transport: Transport type ("stdio" or "sse")
        port: Port number (required for SSE, ignored for STDIO)
        response_parser: Function to parse API responses (transport-specific)
        
    Returns:
        Configured FastMCP server instance
    """
    # Create server with transport-specific initialization
    if port:
        mcp = FastMCP("worldbank_mcp", port=port)
    else:
        mcp = FastMCP("worldbank_mcp")
    
    # Store parser for use in tools
    if response_parser is None:
        raise ValueError("response_parser must be provided")
    
    mcp._response_parser = response_parser
    
    # Register all tools
    _register_search_tool(mcp)
    _register_details_tool(mcp)
    _register_facets_tool(mcp)
    _register_project_tool(mcp)
    
    return mcp


def _register_search_tool(mcp: FastMCP):
    """Register the document search tool."""
    
    @mcp.tool(
        name="worldbank_search_documents",
        annotations={
            "title": "Search World Bank Documents",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True
        }
    )
    async def worldbank_search_documents(params: WorldBankSearchInput) -> str:
        """Search for documents in the World Bank Documents & Reports database."""
        try:
            query_params = build_query_params(
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
            
            response = await make_api_request(query_params)
            
            # Use transport-specific parser
            docs_list, total = mcp._response_parser(response)
            
            if total == 0:
                return (
                    "No documents found matching your query.\n\n"
                    "Suggestions:\n"
                    "- Try broader search terms\n"
                    "- Remove some filters\n"
                    "- Check spelling of country names or document types\n"
                    "- Use the worldbank_explore_facets tool to see available filter values"
                )
            
            if params.response_format == ResponseFormat.MARKDOWN:
                output = f"# World Bank Document Search Results\n\n"
                output += f"**Query:** {params.query}\n"
                output += f"**Total Results:** {total:,}\n"
                output += f"**Showing:** {params.offset + 1}-{params.offset + len(docs_list)} of {total:,}\n"
                
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
                
                for doc in docs_list:
                    output += format_document_markdown(doc)
                
                has_more = (params.offset + len(docs_list)) < total
                if has_more:
                    next_offset = params.offset + len(docs_list)
                    output += f"\n**More results available.** Use offset={next_offset} to see the next page.\n"
                
                output = truncate_if_needed(output, docs_list)
                return output
                
            else:
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
                    "documents": [format_document_json(doc) for doc in docs_list]
                }
                
                json_output = json.dumps(result, indent=2)
                json_output = truncate_if_needed(json_output, docs_list)
                return json_output
                
        except Exception as e:
            return f"Error searching World Bank documents: {str(e)}"


def _register_details_tool(mcp: FastMCP):
    """Register the document details tool."""
    
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
        """Retrieve detailed information for a specific World Bank document."""
        try:
            query_params = build_query_params(
                limit=1,
                id=params.document_id
            )
            
            response = await make_api_request(query_params)
            
            # Use transport-specific parser
            docs_list, _ = mcp._response_parser(response)
            
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
            
            if params.response_format == ResponseFormat.MARKDOWN:
                output = f"# World Bank Document Details\n\n"
                output += format_document_markdown(doc)
                
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
                
            else:
                result = format_document_json(doc)
                return json.dumps(result, indent=2)
                
        except Exception as e:
            return f"Error retrieving document details: {str(e)}"


def _register_facets_tool(mcp: FastMCP):
    """Register the facets exploration tool."""
    
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
        """Explore available facet values in the World Bank Documents database."""
        try:
            query_params = build_query_params(
                query=params.query,
                facets=params.facets,
                rows=0
            )
            
            response = await make_api_request(query_params)
            
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
            
            if params.response_format == ResponseFormat.MARKDOWN:
                output = "# World Bank Document Facets\n\n"
                
                if params.query:
                    output += f"**Filtered by query:** {params.query}\n\n"
                
                for facet_name in params.facets:
                    if facet_name not in facet_data:
                        output += f"## {facet_name}\n\n*No data available*\n\n"
                        continue
                    
                    facet_values = facet_data[facet_name]
                    
                    facet_pairs = []
                    for i in range(0, len(facet_values), 2):
                        if i + 1 < len(facet_values):
                            value = facet_values[i]
                            count = facet_values[i + 1]
                            facet_pairs.append((value, count))
                    
                    facet_pairs.sort(key=lambda x: x[1], reverse=True)
                    
                    output += f"## {facet_name}\n\n"
                    output += f"Total unique values: {len(facet_pairs)}\n\n"
                    
                    for value, count in facet_pairs[:50]:
                        output += f"- **{value}**: {count:,} documents\n"
                    
                    if len(facet_pairs) > 50:
                        output += f"\n*Showing top 50 of {len(facet_pairs)} total values*\n"
                    
                    output += "\n"
                
                return output
                
            else:
                result = {"facets": {}}
                
                for facet_name in params.facets:
                    if facet_name not in facet_data:
                        result["facets"][facet_name] = []
                        continue
                    
                    facet_values = facet_data[facet_name]
                    
                    facet_pairs = []
                    for i in range(0, len(facet_values), 2):
                        if i + 1 < len(facet_values):
                            value = facet_values[i]
                            count = facet_values[i + 1]
                            facet_pairs.append({"value": value, "count": count})
                    
                    facet_pairs.sort(key=lambda x: x["count"], reverse=True)
                    
                    result["facets"][facet_name] = facet_pairs
                
                if params.query:
                    result["query"] = params.query
                
                return json.dumps(result, indent=2)
                
        except Exception as e:
            return f"Error exploring facets: {str(e)}"


def _register_project_tool(mcp: FastMCP):
    """Register the project search tool."""
    
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
        """Search for documents related to a specific World Bank project."""
        try:
            if not params.project_id and not params.project_name:
                return (
                    "Error: Either project_id or project_name must be provided.\n\n"
                    "Examples:\n"
                    "- project_id='P123456'\n"
                    "- project_name='Rural Education Project'\n"
                    "- Both can be provided for more specific search"
                )
            
            query_params = build_query_params(
                limit=params.limit,
                offset=params.offset
            )
            
            if params.project_id:
                query_params["proid"] = params.project_id
            
            if params.project_name:
                query_params["projn"] = params.project_name
            
            response = await make_api_request(query_params)
            
            # Use transport-specific parser
            docs_list, total = mcp._response_parser(response)
            
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
            
            if params.response_format == ResponseFormat.MARKDOWN:
                output = f"# World Bank Project Documents\n\n"
                
                if params.project_id:
                    output += f"**Project ID:** {params.project_id}\n"
                if params.project_name:
                    output += f"**Project Name:** {params.project_name}\n"
                
                output += f"**Total Documents:** {total:,}\n"
                output += f"**Showing:** {params.offset + 1}-{params.offset + len(docs_list)} of {total:,}\n"
                output += f"\n---\n\n"
                
                for doc in docs_list:
                    output += format_document_markdown(doc)
                
                has_more = (params.offset + len(docs_list)) < total
                if has_more:
                    next_offset = params.offset + len(docs_list)
                    output += f"\n**More results available.** Use offset={next_offset} to see the next page.\n"
                
                output = truncate_if_needed(output, docs_list)
                return output
                
            else:
                result = {
                    "project_id": params.project_id,
                    "project_name": params.project_name,
                    "total": total,
                    "count": len(docs_list),
                    "offset": params.offset,
                    "limit": params.limit,
                    "has_more": (params.offset + len(docs_list)) < total,
                    "next_offset": params.offset + len(docs_list) if (params.offset + len(docs_list)) < total else None,
                    "documents": [format_document_json(doc) for doc in docs_list]
                }
                
                json_output = json.dumps(result, indent=2)
                json_output = truncate_if_needed(json_output, docs_list)
                return json_output
                
        except Exception as e:
            return f"Error searching by project: {str(e)}"
