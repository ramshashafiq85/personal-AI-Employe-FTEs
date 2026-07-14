---
type: approval_request
action_type: email
to: client@example.com
subject: Test Email Approval
created: 2026-03-30T20:00:00
status: pending
priority: normal
---

# Approval Request: Send Email

## Description
Send a test email to client@example.com

## Reason for Approval
Email to external contact requires approval per Company Handbook rules.

## Details

```yaml
action_type: email
to: client@example.com
subject: Test Email Approval
body: |
  Dear Client,
  
  This is a test email from AI Employee.
  
  Best regards,
  AI Employee Team
```

## Instructions for Human Reviewer

✅ **To Approve:** Move this file to `/Approved/` folder
❌ **To Reject:** Move this file to `/Rejected/` folder

**After moving to Approved:**
- The Approval Handler will automatically process the email
- Result will be logged to `/Logs/2026-03-30.json`
- File will be archived to `/Done/`

## Action Log

*Waiting for human decision...*

---
*Created by AI Employee v0.2 (Silver Tier)*
*This is a LIVE test - YOU approve this request!*
