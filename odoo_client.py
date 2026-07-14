import os
import json
import sys
import xmlrpc.client

# --- CONFIGURATION ---
ODOO_URL = "http://localhost:8069"
DB_NAME = "AII-EMPLOYEE-FTE"          # <--- Match your actual Odoo database
EMAIL = "ramshashafiq85@gmail.com"
PASSWORD = "admin123"                 # <--- Match your reset password

# Connect to Odoo via XML-RPC
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

def authenticate():
    uid = common.authenticate(DB_NAME, EMAIL, PASSWORD, {})
    if not uid:
        print("Authentication failed!")
        sys.exit(1)
    return uid

def search_contacts(name=""):
    uid = authenticate()
    domain = [['name', 'ilike', name]] if name else []
    contact_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
        'res.partner', 'search', [domain],
        {'limit': 20, 'order': 'id asc'}
    )
    contacts = models.execute_kw(DB_NAME, uid, PASSWORD,
        'res.partner', 'read', [contact_ids],
        {'fields': ['id', 'name', 'email', 'phone']}
    )
    return contacts

def create_partner(name, email=None):
    uid = authenticate()
    partner_id = models.execute_kw(DB_NAME, uid, PASSWORD,
        'res.partner', 'create', [{
            'name': name,
            'email': email or f"{name.lower().replace(' ', '.')}@example.com"
        }]
    )
    return partner_id

def create_invoice(partner_name, amount, description, reference=None):
    uid = authenticate()
    
    # Find Partner ID
    partner_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
        'res.partner', 'search', [[['name', '=', partner_name]]],
        {'limit': 1}
    )
    
    if not partner_ids:
        print(f"Partner '{partner_name}' not found. Creating new partner...")
        partner_id = create_partner(partner_name)
    else:
        partner_id = partner_ids[0]
    
    # Create Invoice
    invoice_data = {
        'move_type': 'out_invoice',
        'partner_id': partner_id,
        'invoice_line_ids': [(0, 0, {
            'name': description,
            'quantity': 1,
            'price_unit': amount
        })]
    }
    
    if reference:
        invoice_data['ref'] = reference
        
    invoice_id = models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'create', [invoice_data]
    )
    
    return f"Invoice created successfully! ID: {invoice_id}"

def list_invoices():
    uid = authenticate()
    invoice_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'search', [[['move_type', '=', 'out_invoice']]],
        {'limit': 10, 'order': 'create_date desc'}
    )
    if not invoice_ids:
        return []
    invoices = models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'read', [invoice_ids],
        {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state', 'invoice_date']}
    )
    return invoices

def get_revenue_summary():
    uid = authenticate()
    invoice_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'search', [[['move_type', '=', 'out_invoice']]]
    )
    if not invoice_ids:
        return {"total_posted_revenue": 0, "total_draft_revenue": 0, "invoice_count": 0}
    
    invoices = models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'read', [invoice_ids],
        {'fields': ['amount_total', 'state']}
    )
    
    total_posted = sum(i.get('amount_total', 0) for i in invoices if i.get('state') == 'posted')
    total_draft = sum(i.get('amount_total', 0) for i in invoices if i.get('state') == 'draft')
    return {
        "total_posted_revenue": total_posted,
        "total_draft_revenue": total_draft,
        "invoice_count": len(invoices)
    }

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python odoo_client.py <command> [args]")
        print("Commands: contacts, invoices, create_invoice, revenue")
        sys.exit(1)

    command = sys.argv[1]

    if command == "contacts":
        name = sys.argv[2] if len(sys.argv) > 2 else ""
        result = search_contacts(name)
        print(json.dumps(result, indent=2, default=str))

    elif command == "invoices":
        result = list_invoices()
        print(json.dumps(result, indent=2, default=str))

    elif command == "create_invoice":
        if len(sys.argv) < 5:
            print("Usage: python odoo_client.py create_invoice <partner_name> <amount> <description>")
            sys.exit(1)
        result = create_invoice(sys.argv[2], float(sys.argv[3]), sys.argv[4])
        print(result)

    elif command == "revenue":
        result = get_revenue_summary()
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
