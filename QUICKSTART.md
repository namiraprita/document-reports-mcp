# Quick Start Guide - World Bank MCP Server

Get your World Bank MCP server running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Navigate to the directory containing worldbank_mcp.py
cd /path/to/worldbank-mcp

# Install required Python packages
pip install -r requirements.txt
```

## Step 2: Test the Server

Before integrating with Claude Desktop, verify the server runs:

```bash
# Check Python syntax
python -m py_compile worldbank_mcp.py

# Run with --help to see it loads
python worldbank_mcp.py --help
```

**Note:** The server will appear to "hang" when run directly - this is expected! It's waiting for MCP protocol messages via stdin. Press Ctrl+C to exit.

## Step 3: Configure Claude Desktop

### Find your config file:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

### Get the absolute path:
```bash
# macOS/Linux
pwd  # Copy the full path, then add /worldbank_mcp.py
# Example: /Users/yourname/projects/worldbank-mcp/worldbank_mcp.py

# Windows
cd  # Copy the full path
# Example: C:\Users\yourname\projects\worldbank-mcp\worldbank_mcp.py
```

### Edit the config:
```json
{
  "mcpServers": {
    "worldbank": {
      "command": "python",
      "args": [
        "/Users/yourname/projects/worldbank-mcp/worldbank_mcp.py"
      ]
    }
  }
}
```

**Replace the path with your actual path!**

### If you have multiple MCP servers:
```json
{
  "mcpServers": {
    "worldbank": {
      "command": "python",
      "args": ["/path/to/worldbank_mcp.py"]
    },
    "other-server": {
      "command": "node",
      "args": ["/path/to/other-server/index.js"]
    }
  }
}
```

## Step 4: Restart Claude Desktop

1. **Quit Claude Desktop completely** (don't just close the window)
   - macOS: Cmd+Q or Claude menu → Quit
   - Windows: File → Exit

2. **Reopen Claude Desktop**

3. **Look for the connection icon** in the interface (usually bottom-right)
   - Click it to see connected servers
   - "worldbank" should appear in the list

## Step 5: Test It Out!

Try these prompts in Claude:

### Test 1: Basic Search
```
Find recent World Bank documents about climate change
```

### Test 2: Filtered Search
```
Show me procurement plans for Kenya from 2023
```

### Test 3: Explore Options
```
What types of documents are available in the World Bank database?
```

### Test 4: Get Details
```
[After a search] Tell me more details about the first document
```

## Troubleshooting

### Server not showing in Claude Desktop

**Check 1: Config file location**
```bash
# macOS - verify file exists
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json

# Windows
type %APPDATA%\Claude\claude_desktop_config.json
```

**Check 2: JSON syntax**
- Use a JSON validator: https://jsonlint.com/
- Common mistake: Missing comma between servers
- Common mistake: Wrong quote type (use " not ')

**Check 3: Python path**
```bash
# Verify Python is in PATH
python --version

# If not, use full path to Python:
# macOS: /usr/local/bin/python3 or /opt/homebrew/bin/python3
# Windows: C:\Python310\python.exe
```

**Check 4: File path**
```bash
# Verify the file exists at the path you specified
ls /path/to/worldbank_mcp.py  # macOS/Linux
dir C:\path\to\worldbank_mcp.py  # Windows
```

**Check 5: Restart properly**
- Completely quit Claude Desktop (not just minimize)
- Wait 5 seconds
- Reopen

### "Module not found" errors

```bash
# Install dependencies again
pip install mcp httpx pydantic

# If you have multiple Python versions:
python3 -m pip install mcp httpx pydantic

# Or use a virtual environment (recommended):
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Then update your config to use the venv Python:
# "command": "/path/to/venv/bin/python"
```

### API returns no results

This is usually fine! Try:
- Different search terms
- Broader queries
- Use `worldbank_explore_facets` to see what's available

### Server stops responding

1. Check Claude Desktop logs (Help → Debug → Show Logs)
2. Restart Claude Desktop
3. Test the server manually (Step 2)

## What to Expect

### Server is working when:
- Connection icon shows "worldbank" in connected servers
- Claude can answer questions about World Bank documents
- You see tool calls like `worldbank_search_documents` in responses

### Server needs attention when:
- No connection icon appears
- Claude says "I don't have access to that tool"
- Connection errors in Claude Desktop logs

## Next Steps

Once it's working:

1. **Try advanced searches**:
   - Multiple filters
   - Date ranges
   - Different output formats (ask for JSON)

2. **Explore the data**:
   - Use `worldbank_explore_facets` to discover categories
   - Search by project
   - Browse different document types

3. **Combine with other tools**:
   - If you have other MCP servers, Claude can use them together
   - Example: Search World Bank docs + read them with a file browser

## Common Use Cases

### Research Assistant
```
Find World Bank research papers about sustainable agriculture in Sub-Saharan 
Africa from the last 3 years, focusing on those available in French
```

### Project Tracking
```
Show me all documents for World Bank project P123456 and summarize the 
project's progress based on the implementation reports
```

### Data Discovery
```
What countries have the most World Bank documents? Show me the top 10 and 
tell me what types of documents are most common for each
```

## Getting Help

- **Server issues**: Check the main README.md
- **Claude Desktop**: https://support.claude.com
- **MCP Protocol**: https://modelcontextprotocol.io
- **World Bank API**: https://documents.worldbank.org/en/publication/documents-reports/api

---

Enjoy your new World Bank research assistant!
