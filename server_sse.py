#!/usr/bin/env -S uv run
"""
World Bank Documents & Reports MCP Server (SSE Transport)

Thin wrapper that configures the server for SSE transport.
All business logic is in worldbank_dnr_mcp package.

This version uses SSE (Server-Sent Events) transport for web and API clients.

API Documentation: https://documents.worldbank.org/en/publication/documents-reports/api
"""

from worldbank_dnr_mcp import create_worldbank_server, parse_sse_response

# Create server with SSE configuration
mcp = create_worldbank_server(
    transport="sse",
    port=8002,
    response_parser=parse_sse_response
)

if __name__ == "__main__":
    # Run with SSE transport
    mcp.run(transport="sse")
