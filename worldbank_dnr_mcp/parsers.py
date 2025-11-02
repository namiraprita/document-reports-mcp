"""
Transport-specific response parsers for World Bank API.

This module contains the ONLY transport-specific code in the entire server.
Different transports receive different response formats from the API.
"""

from typing import Dict, Any, List, Tuple


def parse_stdio_response(response: Dict[str, Any]) -> Tuple[List[Dict], int]:
    """
    Parse World Bank API response for STDIO transport.
    
    STDIO format: Documents returned as dictionary with doc IDs as keys.
    Example: {documents: {doc_id_1: {...}, doc_id_2: {...}}, total: 100}
    
    Args:
        response: Raw API response dictionary
        
    Returns:
        Tuple of (documents_list, total_count)
    """
    documents = response.get('documents', {})
    docs_list = [
        doc for key, doc in documents.items() 
        if key != 'facets' and isinstance(doc, dict)
    ]
    total = response.get('total', 0)
    return docs_list, total


def parse_sse_response(response: Dict[str, Any]) -> Tuple[List[Dict], int]:
    """
    Parse World Bank API response for SSE transport.
    
    SSE format: Documents returned in nested structure with 'docs' array.
    Example: {documents: {docs: [...], numFound: 100}}
    
    Args:
        response: Raw API response dictionary
        
    Returns:
        Tuple of (documents_list, total_count)
    """
    documents = response.get('documents', {})
    docs_list = documents.get('docs', [])
    total = documents.get('numFound', 0)
    return docs_list, total


def parse_default_response(response: Dict[str, Any]) -> Tuple[List[Dict], int]:
    """
    Default parser that tries both formats.
    
    This is useful for testing or when the transport type is unknown.
    Tries SSE format first, then falls back to STDIO format.
    
    Args:
        response: Raw API response dictionary
        
    Returns:
        Tuple of (documents_list, total_count)
    """
    documents = response.get('documents', {})
    
    # Try SSE format first (has 'docs' key)
    if 'docs' in documents:
        return parse_sse_response(response)
    
    # Fallback to STDIO format
    return parse_stdio_response(response)
