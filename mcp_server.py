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
    # Add USSD and BTC payment tools if available
    from core.wallet import Wallet
    from core.gateways import USSDGateway, BTCGateway
    def ussd_payment(phone_number, amount):
        """Real USSD payment via gateway."""
        return USSDGateway.send_payment(phone_number, amount)
    def btc_payment(user_id, to_address, amount_btc):
        """Send BTC from user's wallet to another address."""
        wallet = Wallet(user_id)
        return BTCGateway.send_btc(wallet.btc_private_key, to_address, amount_btc)
    def btc_balance(user_id):
        """Get BTC balance for user's wallet."""
        wallet = Wallet(user_id)
        return BTCGateway.get_balance(wallet.btc_address)
    MCP_TOOLKIT["ussd_payment"] = ussd_payment
    MCP_TOOLKIT["btc_payment"] = btc_payment
    MCP_TOOLKIT["btc_balance"] = btc_balance
finally:
    sys.stdout = original_stdout

# Register Tools
for name, func in MCP_TOOLKIT.items():
    if func:
        mcp.tool()(func)

if __name__ == "__main__":
    # The MCP runner expects to control stdout/stdin
    mcp.run()
