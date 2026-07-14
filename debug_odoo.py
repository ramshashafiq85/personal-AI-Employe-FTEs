import xmlrpc.client
import json

# --- CONFIGURATION ---
ODOO_URL = "http://localhost:8069"
DB_NAME = "AI-Employee"
EMAIL = "ramshashafiq85@gmail.com"
PASSWORD = "ramsha1234"

# Connect to Odoo via XML-RPC
common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')

# Authenticate
uid = common.authenticate(DB_NAME, EMAIL, PASSWORD, {})
if not uid:
    print("Authentication failed!")
    exit(1)

print(f"Authenticated! User ID: {uid}")

# Search contacts
print("\n=== Contacts ===")
contact_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
    'res.partner', 'search', [[['is_company', '=', True]]],
    {'limit': 10}
)

if not contact_ids:
    print("No company contacts found. Trying all partners...")
    contact_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
        'res.partner', 'search', [[]],
        {'limit': 10}
    )

contacts = models.execute_kw(DB_NAME, uid, PASSWORD,
    'res.partner', 'read', [contact_ids],
    {'fields': ['id', 'name', 'email', 'phone']}
)

print(f"Found {len(contacts)} contacts:")
for c in contacts:
    print(f"  - ID: {c.get('id')}, Name: {c.get('name')}, Email: {c.get('email')}")

# Search invoices
print("\n=== Invoices ===")
invoice_ids = models.execute_kw(DB_NAME, uid, PASSWORD,
    'account.move', 'search', [[['move_type', '=', 'out_invoice']]],
    {'limit': 10, 'order': 'create_date desc'}
)

if not invoice_ids:
    print("No invoices found.")
else:
    invoices = models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'read', [invoice_ids],
        {'fields': ['id', 'name', 'partner_id', 'amount_total', 'state', 'invoice_date']}
    )
    print(f"Found {len(invoices)} invoices:")
    for inv in invoices:
        partner = inv.get('partner_id', [None, 'Unknown'])
        print(f"  - ID: {inv.get('id')}, Number: {inv.get('name')}, "
              f"Client: {partner[1] if partner else 'N/A'}, "
              f"Total: {inv.get('amount_total')}, State: {inv.get('state')}")

# Revenue summary
print("\n=== Revenue Summary ===")
all_invoices = models.execute_kw(DB_NAME, uid, PASSWORD,
    'account.move', 'read', [models.execute_kw(DB_NAME, uid, PASSWORD,
        'account.move', 'search', [[['move_type', '=', 'out_invoice']]])],
    {'fields': ['amount_total', 'state']}
)

total_posted = sum(i.get('amount_total', 0) for i in all_invoices if i.get('state') == 'posted')
total_draft = sum(i.get('amount_total', 0) for i in all_invoices if i.get('state') == 'draft')
print(f"Total Posted Revenue: ${total_posted:,.2f}")
print(f"Total Draft Revenue:  ${total_draft:,.2f}")
print(f"Invoice Count:        {len(all_invoices)}")
