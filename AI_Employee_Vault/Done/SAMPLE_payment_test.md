---
type: approval_request
action_type: payment
amount: 150.00
recipient: Test Vendor Inc.
invoice_ref: TEST-001
created: 2026-03-30T03:30:00
status: pending
priority: normal
---

# Approval Request: Payment

## Description
Payment to Test Vendor Inc. for services rendered.

## Reason for Approval
Payment amount ($150.00) exceeds $50 threshold per Company Handbook rules.

## Details

```yaml
action_type: payment
amount: 150.00
recipient: Test Vendor Inc.
invoice_ref: TEST-001
due_date: 2026-04-15
vendor_category: Professional Services
```

## Instructions for Human Reviewer

✅ **To Approve:** Move this file to `/Approved/` folder
❌ **To Reject:** Move this file to `/Rejected/` folder

**After moving to Approved:**
- The Approval Handler will automatically process the payment
- Result will be logged to `/Logs/2026-03-30.json`
- File will be archived to `/Done/`

## Action Log

*Waiting for human decision...*

---
*Created by AI Employee v0.2 (Silver Tier)*
*This is a SAMPLE approval request for testing purposes*
