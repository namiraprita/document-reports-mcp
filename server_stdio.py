#!/usr/bin/env -S uv run
"""
World Bank Documents & Reports MCP Server (STDIO Transport)

Thin wrapper that configures the server for STDIO transport.
All business logic is in worldbank_dnr_mcp package.

This version uses STDIO transport for Claude Desktop and CLI clients.

API Documentation: https://documents.worldbank.org/en/publication/documents-reports/api
"""

from worldbank_dnr_mcp import create_worldbank_server, parse_stdio_response

# Create server with STDIO configuration
mcp = create_worldbank_server(
    transport="stdio",
    port=None,
    response_parser=parse_stdio_response
)

if __name__ == "__main__":
    # Run with STDIO transport
    mcp.run(transport="stdio")
