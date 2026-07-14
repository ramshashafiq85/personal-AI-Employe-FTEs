import os
import requests
from mcp.server.fastmcp import FastMCP

# --- CONFIGURATION ---
# Update these with your Odoo details
ODOO_URL = "http://localhost:8069"
DB_NAME = os.getenv("ODOO_DB", "AI-Employee")       # Replace with your DB name
EMAIL = os.getenv("ODOO_EMAIL", "ramshashafiq85@gmail.com") # Replace with your email
PASSWORD = os.getenv("ODOO_PASSWORD", "ramsha1234")    # Replace with your password

mcp = FastMCP("Odoo MCP Server")

def odoo_json_rpc(endpoint, params):
    """Helper to make JSON-RPC calls to Odoo"""
    url = f"{ODOO_URL}/{endpoint}"
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "params": params,
        "id": 1
    }
    response = requests.post(url, json=payload)
    result = response.json().get("result")
    if "error" in response.json():
        raise Exception(response.json()["error"])
    return result

def authenticate():
    """Authenticate and get session info"""
    result = odoo_json_rpc("web/session/authenticate", {
        "db": DB_NAME,
        "login": EMAIL,
        "password": PASSWORD
    })
    if not result.get("uid"):
        raise Exception("Odoo Authentication failed")
    return result

@mcp.tool()
def search_contacts(name: str = ""):
    """Search for contacts in Odoo. Returns list of partners."""
    session = authenticate()
    domain = [["name", "ilike", name]] if name else []
    result = odoo_json_rpc("web/dataset/search_read", {
        "model": "res.partner",
        "fields": ["id", "name", "email", "phone"],
        "domain": domain,
        "limit": 20
    })
    return result.get("records", [])

@mcp.tool()
def create_invoice(partner_name: str, amount: float, description: str):
    """Create a draft invoice in Odoo for a specific partner."""
    session = authenticate()
    
    # 1. Find Partner ID
    partners = odoo_json_rpc("web/dataset/search_read", {
        "model": "res.partner",
        "fields": ["id"],
        "domain": [["name", "=", partner_name]],
        "limit": 1
    })
    if not partners.get("records"):
        return f"Error: Partner '{partner_name}' not found."
    
    partner_id = partners["records"][0]["id"]

    # 2. Create Invoice
    invoice_data = {
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_line_ids": [(0, 0, {
            "name": description,
            "quantity": 1,
            "price_unit": amount
        })]
    }
    
    result = odoo_json_rpc("web/dataset/call_kw", {
        "model": "account.move",
        "method": "create",
        "args": [invoice_data],
        "kwargs": {}
    })
    
    return f"Invoice created successfully! ID: {result.get('id')}"

if __name__ == "__main__":
    mcp.run()
