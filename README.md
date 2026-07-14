md# 🤖 Personal AI Employee Framework (Platinum Tier)
### *A Multi-Agent Autonomous Workforce for Modern Business Operations*

![Status](https://img.shields.io/badge/Status-100%25_Complete-brightgreen)
![Tier](https://img.shields.io/badge/Tier-Platinum-blue)
![Stack](https://img.shields.io/badge/Stack-Python_%7C_Docker_%7C_Odoo_%7C_Obsidian-orange)

## 🌟 Overview
This project is a sophisticated framework for building and managing a team of **Autonomous AI Employees (FTEs)**. Unlike traditional chatbots, these agents operate 24/7 within a containerized environment, performing specialized roles like accounting, email triage, and business research, all while maintaining a **Human-in-the-Loop (HITL)** safety boundary.

---

## 🏢 The Digital Workforce Architecture

| Agent Role | Core Responsibility | Tech Stack |
| :--- | :--- | :--- |
| **The Manager** | Orchestration, Health Monitoring, Task Delegation | `orchestrator.py` |
| **The Accountant** | ERP Integration, Revenue Logging, Invoice Management | `odoo_client.py` + Odoo 19 |
| **The Clerk** | File Ingestion, Metadata Extraction, Deduplication | `filesystem_watcher.py` |
| **The Messenger** | Omni-channel Communication (Email/WhatsApp) | `gmail_mcp.py` + Playwright |
| **The Sentinel** | Security Boundaries, Secret Redaction, Auth Monitoring | `secrets_boundary.py` |

---

## 🏆 Engineering Milestone: The 4-Tier Progression

### 🥉 Bronze Tier: Infrastructure
- Established the **Obsidian Vault** as the GUI and long-term memory.
- Implemented real-time filesystem monitoring using `Watchdog`.
- Automated file categorization and metadata generation.

### 🥈 Silver Tier: Safety & Workflow
- Developed the **Human-in-the-Loop (HITL)** workflow.
- Sensitive actions (payments > $50) require explicit cryptographic or manual approval.
- Integrated Gmail API for intelligent email triage.

### 🥇 Gold Tier: Ecosystem Integration
- Deployed **Odoo ERP** for professional-grade accounting.
- Integrated **WhatsApp Web** for real-time mobile notifications.
- Automated **Weekly CEO Briefings** with performance metrics and financial summaries.

### 💎 Platinum Tier: Cloud & Enterprise Security
- Full **Dockerized** deployment for 24/7 reliability.
- **Secrets Boundary:** Strict architectural separation between "Brain" (Cloud) and "Safe" (Local) agents.
- Secure Remote Access via **ngrok/Cloudflare Tunnels**.
- Automated audit logging and vault synchronization.

---

## 🛠️ The "Magic" Workflow
1.  **Ingestion:** A raw invoice (PDF/TXT) is dropped into the vault.
2.  **Perception:** The **Clerk Agent** detects the file and extracts metadata.
3.  **Reasoning:** The **Accountant Agent** validates the data and drafts an Odoo entry.
4.  **Approval:** The system generates an `approval_request.md` in the user's mobile dashboard.
5.  **Execution:** Upon user approval, the entry is pushed to Odoo and the user is notified on WhatsApp.

---

## 🛡️ Security & Privacy
- **Zero-Trust Tunnels:** No open ports; all communication is end-to-end encrypted.
- **Secret Redaction:** Runtime scanners prevent API keys or PII from ever hitting the cloud agent.
- **Immutable Audit Trail:** Every decision is logged in JSON for total accountability.

---

## 🚀 Getting Started
1.  **Clone the Repo:** `git clone ...`
2.  **Environment:** Set up your `.env` using the provided `.env.example`.
3.  **Launch Stack:** `docker compose up -d`
4.  **Initialize Agents:** `python orchestrator.py`

---
**Developed with 💙 by Ramsha Shafiq**  
*Building the future of autonomous business operations.*
