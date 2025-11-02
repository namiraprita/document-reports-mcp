"""
World Bank Documents & Reports MCP Server

A refactored MCP server following DRY principles with support for multiple transports.
"""

__version__ = "1.0.0"

from .factory import create_worldbank_server
from .parsers import parse_stdio_response, parse_sse_response

__all__ = [
    "create_worldbank_server",
    "parse_stdio_response",
    "parse_sse_response",
]
