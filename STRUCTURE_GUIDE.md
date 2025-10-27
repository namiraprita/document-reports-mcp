# World Bank DNR MCP Server Structure

## 📁 New File Structure

Your document-reports-mcp now has a similar structure to the data360-mcp repository:

```
document-reports-mcp/
├── start_server_claude.py      # 🆕 Launcher script for Claude Desktop
├── server_stdio.py              # 🆕 Main server with STDIO transport
├── server_sse.py                # 🆕 Alternative server with SSE transport
├── worldbank_dnr_mcp.py         # ✅ Original file (now with uv shebang)
├── pyproject.toml               # ✅ Updated with SSE dependencies
├── claude_desktop_config.example.json  # ✅ Updated to use launcher
└── requirements.txt
```

---

## 🎯 What Each File Does

### 1. **start_server_claude.py** - The Launcher
**Purpose:** Entry point for Claude Desktop  
**What it does:**
- Changes to the project directory
- Runs `uv run server_stdio.py`
- Handles errors gracefully

**Logic:**
```python
# This is like a "smart wrapper" that:
# 1. Sets up the environment
# 2. Launches the actual server
# 3. Catches and reports any startup errors
```

---

### 2. **server_stdio.py** - STDIO Transport Server
**Purpose:** Main server for Claude Desktop and CLI clients  
**Transport:** Standard Input/Output (STDIO)  
**When to use:** For Claude Desktop, command-line tools

**Key difference from original:**
```python
# At the end of the file:
if __name__ == "__main__":
    mcp.run(transport="stdio")  # ← Explicitly specified
```

**Logic:** STDIO transport allows Claude Desktop to communicate with the server through pipes (stdin/stdout), which is perfect for local desktop applications.

---

### 3. **server_sse.py** - SSE Transport Server
**Purpose:** Alternative server for web/API clients  
**Transport:** Server-Sent Events (SSE)  
**When to use:** For web applications, remote access, API integrations

**Key differences:**
```python
# At the top:
mcp = FastMCP("worldbank_mcp", port=8002)  # ← Port specified

# At the bottom:
if __name__ == "__main__":
    mcp.run(transport="sse")  # ← SSE transport
```

**Logic:** SSE transport allows the server to run as a web service on port 8002, enabling remote access and integration with web applications.

---

### 4. **worldbank_dnr_mcp.py** - Original File
**Updates made:**
```python
#!/usr/bin/env -S uv run  # ← Changed from python3 to uv run
```

**Purpose:** Can still be used as a standalone script  
**Benefit:** Now uses `uv` for automatic dependency management

---

## 🔧 Updated Dependencies (pyproject.toml)

**Before:**
```toml
dependencies = [
    "mcp>=1.0.0",
    "httpx>=0.27.0",
    "pydantic>=2.0.0"
]
```

**After:**
```toml
dependencies = [
    "anthropic>=0.8.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "fastapi>=0.100.0",       # ← For SSE transport
    "uvicorn>=0.23.0",        # ← For SSE transport
    "mcp>=0.1.0",
    "httpx>=0.28.0"
]
```

**Why the changes:**
- `fastapi` and `uvicorn`: Required for SSE transport (web server functionality)
- `anthropic`: Aligns with data360-mcp structure
- `python-dotenv`: For environment variable management
- Updated versions to match data360-mcp

---

## 📝 Updated Configuration (claude_desktop_config.example.json)

**Before:**
```json
{
  "mcpServers": {
    "worldbank-dnr": {
      "command": "uv",
      "args": ["run", "/path/to/worldbank_dnr_mcp.py"],
      "cwd": "/path/to/document-reports-mcp"
    }
  }
}
```

**After:**
```json
{
  "mcpServers": {
    "worldbank-dnr": {
      "command": "uv",
      "args": ["run", "/path/to/start_server_claude.py"],
      "cwd": "/path/to/document-reports-mcp"
    }
  }
}
```

**Why:** Now uses the launcher script for better error handling and cleaner startup.

---

## 🚀 How to Use Each Version

### Option 1: For Claude Desktop (Recommended)
```json
// In your Claude Desktop config:
{
  "command": "uv",
  "args": ["run", "/full/path/to/start_server_claude.py"],
  "cwd": "/full/path/to/document-reports-mcp"
}
```

### Option 2: Run STDIO Server Directly
```bash
cd /path/to/document-reports-mcp
uv run server_stdio.py
```

### Option 3: Run SSE Server for Web Access
```bash
cd /path/to/document-reports-mcp
uv run server_sse.py
```
Then access at: `http://localhost:8002`

### Option 4: Run Original Standalone Script
```bash
cd /path/to/document-reports-mcp
uv run worldbank_dnr_mcp.py
```

---

## 🧠 The Logic Behind This Structure

### Why Separate Files?

1. **Separation of Concerns**
   - `start_server_claude.py`: Handles startup and error management
   - `server_stdio.py`: Focused on STDIO transport logic
   - `server_sse.py`: Focused on SSE/web transport logic

2. **Different Use Cases**
   - **STDIO**: Fast, local, perfect for Claude Desktop
   - **SSE**: Network-accessible, perfect for web apps and remote access

3. **Better Maintainability**
   - Each transport type is in its own file
   - Easier to debug and test separately
   - Clear separation makes code more understandable

### Why Use `uv`?

**Traditional Approach (pip):**
```bash
# Manual steps:
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python worldbank_dnr_mcp.py
```

**Modern Approach (uv):**
```bash
# Just one command:
uv run worldbank_dnr_mcp.py
# uv automatically:
# - Creates virtual environment if needed
# - Installs dependencies from pyproject.toml
# - Runs the script
```

**Benefits:**
- ⚡ **Faster**: 10-100x faster than pip
- 🔒 **Isolated**: Each project has its own environment
- 🎯 **Automatic**: No manual venv management
- 🔄 **Reproducible**: Same environment every time

---

## 📊 Comparison with data360-mcp

| Feature | data360-mcp | worldbank-dnr-mcp (Now) |
|---------|-------------|-------------------------|
| Launcher script | ✅ | ✅ |
| STDIO server | ✅ | ✅ |
| SSE server | ✅ | ✅ |
| Resources | ✅ | ❌ (Tools only) |
| Port | 8001 | 8002 |
| Structure | Identical | Identical |

---

## 🎓 Key Concepts Explained

### STDIO Transport
**Think of it like:** A telephone conversation  
- Sends messages through stdin (speaking)
- Receives responses through stdout (listening)
- Perfect for local, one-on-one communication

### SSE Transport  
**Think of it like:** A radio broadcast
- Server broadcasts on a port (radio frequency)
- Multiple clients can listen
- Perfect for web applications

### The Shebang (`#!/usr/bin/env -S uv run`)
**What it does:** Tells the system how to run the file  
**How it works:**
```bash
./server_stdio.py  # This will automatically use uv run
# Instead of:
python server_stdio.py  # Old way
```

---

## ✅ Next Steps

1. **Update your Claude Desktop config** to point to `start_server_claude.py`
2. **Install dependencies**: Run `uv sync` in the project directory
3. **Test the setup**: Restart Claude Desktop
4. **(Optional)** Try the SSE server: `uv run server_sse.py`

---

## 🔍 Troubleshooting

**If uv command not found:**
```bash
# Install uv first:
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**If server won't start:**
```bash
# Check dependencies:
uv sync

# Try running directly:
uv run server_stdio.py
```

**If Claude Desktop can't connect:**
1. Check the path in your config is absolute
2. Verify the `cwd` points to your project directory
3. Restart Claude Desktop

---

## 📚 Summary

You now have a professional, modular MCP server structure that:
- ✅ Uses modern Python tooling (`uv`)
- ✅ Supports multiple transport types
- ✅ Has clean separation of concerns
- ✅ Includes error handling
- ✅ Matches industry best practices
- ✅ Is easy to maintain and extend

The structure mirrors data360-mcp, making it consistent and professional! 🎉
