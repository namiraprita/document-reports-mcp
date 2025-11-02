#!/usr/bin/env python3

import os
import subprocess
import sys

def start_mcp_server():
    """start the MCP server using uv"""
    # TODO: set the working directory to your project path
    project_dir = '/Users/namirasuniaprita/Documents/GitHub/dnr-mcp/document-reports-mcp'
    os.chdir(project_dir)
    
    # run the server using uv
    try:
        # using subprocess.run with check=True will raise an exception if the command fails
        # subprocess.run(['uv', 'run', 'server_stdio.py'], check=True)
        subprocess.run(['uv', 'run', 'server_stdio_refactored.py'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Server failed to start with return code {e.returncode}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    start_mcp_server()
