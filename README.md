# World Bank MCP Server

A Model Context Protocol (MCP) server for accessing the World Bank's Documents & Reports database. Provides searching, retrieval, and detailed breakdowns of World Bank documents for LLMs and programmatic use.

## Repository Structure

- **Server and main code**: (in root)
- **Documentation**: All docs are in [`docs/`](docs/). See below for summaries and quick navigation.
- **Single README:** All documentation is managed/indexed here. Individual .md files are not kept at root.

## Project Features

- Comprehensive document search with advanced filters
- Multi-dimensional filtering (by country, type, language, etc.)
- Result faceting and category exploration
- Metadata and abstract retrieval
- Project-based lookup
- Flexible Markdown/JSON output
- Extensive error handling and validation

## Quick Documentation Index

- [API Document (PDF)](docs/API%20Document.pdf): Official World Bank API documentation.
- [DESIGN_LOGIC.md](docs/DESIGN_LOGIC.md): Core design principles and logic described.
- [STRUCTURE_GUIDE.md](docs/STRUCTURE_GUIDE.md): Folder and file structure, update logic, configuration.
- [NEW_API_ANALYSIS.md](docs/NEW_API_ANALYSIS.md): Coverage of edge cases and API responses.
- [REFACTORING_SUMMARY.md](REFACTORING_SUMMARY.md): Complete refactoring documentation and code quality metrics.

## How To Use

1. **Install Requirements:**
   ```bash
   pip install -r requirements.txt
   # or using uv (recommended for modern Python)
   uv sync
   ```

2. **Run the server (for Claude Desktop):**
   - Update Claude Desktop config as described in [STRUCTURE_GUIDE.md](docs/STRUCTURE_GUIDE.md)
   - Start with:
     ```bash
     uv run start_server_claude.py
     ```

3. **API/CLI usage details, development process, and edge cases:**
   - See [DESIGN_LOGIC.md](docs/DESIGN_LOGIC.md) and [NEW_API_ANALYSIS.md](docs/NEW_API_ANALYSIS.md)

4. **For detailed World Bank API usage:**
   - Refer to [API Document.pdf](docs/API%20Document.pdf)

## Development & Contribution

- See [STRUCTURE_GUIDE.md](docs/STRUCTURE_GUIDE.md) for proper code organization and best practices.
- Adhere to the DRY principle and use Pydantic models for validation.
- Use async/await patterns for all I/O in new code.

---

For full usage, architecture breakdown, and troubleshooting, see documentation in the `docs/` folder, indexed above.
