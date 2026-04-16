---
type: approval_request_template
version: 1.0
---

# Approval Request Template

Use this template when creating approval requests programmatically.

## YAML Frontmatter Fields

```yaml
---
type: approval_request
action_type: [payment|email|file_delete|contract|other]
created: YYYY-MM-DDTHH:MM:SS
status: pending
amount: 100.00          # For payments
recipient: Vendor Name  # For payments
to: email@example.com  # For emails
subject: Email Subject  # For emails
priority: high|normal|low
requires_by: YYYY-MM-DD # Optional deadline
---
```

## Action Types

### Payment
```yaml
action_type: payment
amount: 500.00
recipient: ABC Corp
invoice_ref: INV-2026-001
due_date: 2026-04-15
```

### Email
```yaml
action_type: email
to: client@example.com
subject: Re: Your Inquiry
cc: manager@example.com
```

### File Delete
```yaml
action_type: file_delete
file_path: C:/path/to/file.txt
reason: Cleanup old temp files
```

### Contract/Agreement
```yaml
action_type: contract
counterparty: Company Name
contract_type: Service Agreement
value: 5000.00
```

## Workflow

1. **AI Creates Request** → File appears in `Pending_Approval/`
2. **Human Reviews** → Reads file, evaluates request
3. **Human Decides:**
   - ✅ Move to `Approved/` → Action executes automatically
   - ❌ Move to `Rejected/` → Request declined, logged
4. **Archive** → File moved to `Done/` after execution

## Company Handbook Rules

Per `Company_Handbook.md`:

| Action | Threshold | Approval Required |
|--------|-----------|-------------------|
| Payment | < $50 | No (auto-log) |
| Payment | $50 - $500 | Yes |
| Payment | > $500 | Yes + Notify human |
| Email to new contact | Any | Yes |
| File deletion | Outside vault | Yes |
| Contract signing | Any | Yes |

---

*Template for AI Employee v0.2 (Silver Tier)*
