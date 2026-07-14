---
type: approval_request
action_type: payment
amount: 250.00
recipient: Tech Solutions Inc.
invoice_ref: INV-2026-005
created: 2026-03-31T19:30:00
status: pending
priority: normal
---

# Approval Request: Payment

## Description
Pay invoice INV-2026-005 from Tech Solutions Inc. for web development services.

## Reason for Approval
Payment amount ($250.00) exceeds $50 threshold per Company Handbook rules.

## Details

```yaml
action_type: payment
amount: 250.00
recipient: Tech Solutions Inc.
invoice_ref: INV-2026-005
due_date: 2026-04-30
category: Professional Services
```

## Invoice Content

```
Invoice #: INV-2026-005
Date: March 31, 2026
Amount: $250.00
Client: Tech Solutions Inc.
Description: Web development services
```

## Instructions for Human Reviewer

✅ **To Approve:** Move this file to `/Approved/` folder  
❌ **To Reject:** Move this file to `/Rejected/` folder

**After moving to Approved:**
- The Approval Handler will automatically process the payment
- Result will be logged to `/Logs/2026-03-31.json`
- File will be archived to `/Done/`

## Action Log

*Waiting for human decision...*

---
*Created by AI Employee v0.2 (Silver Tier)*
*This request was created AUTOMATICALLY when AI processed the invoice*
