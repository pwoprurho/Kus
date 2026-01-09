import sys
import os
import logging

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Create Server
mcp = FastMCP("Kusmus Tools")

# Redirect stdout during import to prevent print pollution
# (Standard prints in mcp_tools would break one-way stdio transport)
original_stdout = sys.stdout
sys.stdout = sys.stderr

try:
    from services.mcp_tools import MCP_TOOLKIT
finally:
    sys.stdout = original_stdout

# Register Tools
for name, func in MCP_TOOLKIT.items():
    if func:
        mcp.tool()(func)

if __name__ == "__main__":
    # The MCP runner expects to control stdout/stdin
    mcp.run()
