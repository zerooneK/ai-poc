# Internal AI Assistant POC (GEMINI.md)

This project is a Proof of Concept (POC) for an **Internal AI Assistant Platform** designed specifically for Thai employees. It uses a multi-agent architecture to generate various corporate documents (HR, Accounting, Management, PM) and handle general conversation in Thai.

---

## 🚀 Project Overview

- **Purpose**: Automate the creation of Thai corporate documents and provide general AI assistance.
- **Goal**: Demonstrate AI capability to senior management to secure budget for full production development.
- **Current Version**: v0.12.2 (Updated: March 26, 2026)

### **Architecture**
- **Orchestration**: A central Orchestrator analyzes user input and routes it to specialized agents or the general chat agent.
- **Multi-Agent System**:
    - **Chat Agent (New)**: Handles general greetings, system inquiries, and casual conversation without document generation.
    - **HR Agent**: Handles employment contracts, JDs, and internal policies.
    - **Accounting Agent**: Handles Invoices (with VAT) and Expense Reports (without VAT).
    - **Manager Advisor**: Provides management scripts, feedback, and action plans.
    - **PM Agent**: Orchestrates multi-departmental tasks using an agentic loop with MCP tools.
- **Advanced Capabilities**:
    - **Web Search**: Agents can perform internet searches via DuckDuckGo (DDGS) for real-time information.
    - **Conversation Memory**: Remembers the last 10 turns (20 messages) for contextual awareness in routing and generation.
- **Persistence**: SQLite (`db.py`) for job history and session management with graceful degradation.
- **Filesystem Tools**: MCP (Model Context Protocol) via `mcp_server.py` for workspace operations.
- **Export Engine**: `converter.py` for multi-format export (.txt, .docx, .xlsx, .pdf) with full Thai font support.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11 + Flask + flask-cors
- **AI Provider**: OpenRouter API (OpenAI SDK) using `anthropic/claude-sonnet-4-5` (default).
- **Streaming**: Server-Sent Events (SSE) for real-time typewriter-style responses.
- **Frontend**: Single-file Vanilla HTML/JS/CSS ("The Silent Concierge" design system).
- **Libraries**: `openai`, `python-dotenv`, `mcp`, `watchdog`, `python-docx`, `openpyxl`, `weasyprint`, `markdown`.

---

## 📜 Mandatory Development Rules

### **1. Language & Locale**
- **All AI outputs and UI text MUST be in Thai.**
- **Dates**: Always use Buddhist Era (พ.ศ.) (Current year is 2569).
- **Disclaimer**: Every AI-generated document MUST include: `⚠️ เอกสารฉบับร่างนี้จัดทำโดย AI — กรุณาตรวจสอบความถูกต้องก่อนนำไปใช้งานจริง`.

### **2. File Management**
- **Filenames**: All files created in `workspace/` MUST use **English snake_case** (e.g., `employment_contract_somchai.docx`). **NO Thai characters in filenames.**
- **Paths**: Agents operate strictly within the `workspace/` directory.

### **3. Versioning & Documentation**
- **Every code change MUST bump the version** in `index.html` (line 1238 approx.) and add a entry in `CHANGELOG.md`.
- Follow semantic versioning (v0.MINOR.PATCH).
- Update `PROJECT_SUMMARY.md` and `DEMO-READINESS-REPORT.md` if features or architecture change.

### **4. Workflow & Process Rules**
1. **Clear Understanding**: Thoroughly understand the goals and requirements of any instruction before starting work.
2. **Detailed Planning**: Create a detailed plan before making any modifications to code or related documentation.
3. **Documentation Sync**: After completing improvements, plan and execute updates to all related documents to ensure they are current and consistent.
4. **Git Commits**: Commit to Git immediately after every version bump.
5. **No .env Access**: NEVER modify or directly read `.env` files. If a configuration change or check is required, provide a detailed step-by-step instruction and clear examples for the user to perform the action manually.

---

## ⚙️ Building, Running & Testing

### **Setup**
```bash
bash setup.sh
```
Installs system dependencies (WeasyPrint, Thai fonts), creates `venv`, installs `pip` packages, and prepares directories.

### **Running**
```bash
./start.sh
```
Activates `venv` and runs Flask on `http://localhost:5000` (host=0.0.0.0 for WSL compatibility).

### **Testing & Validation**
- **Full Test Suite**: `PYTHONUTF8=1 python test_cases.py` (Tests all agents and PM flows).
- **Smoke Test**: `python smoke_test_phase0.py` (Validates health and SSE).
- **Quick Demo Check**: `python quick-demo-check.py` (Final readiness validation).

---

## 🏗️ Architecture (Modular — Completed in v0.12.0, Hardened in v0.12.2)

The project was refactored from a monolithic `app.py` to a modular structure:
- **`app.py`**: Flask Routes and request/response flow only
- **`core/`**: `orchestrator.py`, `agent_factory.py`, `shared.py`, `utils.py`
- **`agents/`**: `base_agent.py`, `hr_agent.py`, `accounting_agent.py`, `manager_agent.py`, `pm_agent.py`, `chat_agent.py`
- **`prompts/`**: System prompts as `.md` files for easy prompt engineering (`orchestrator.md`, `hr_agent.md`, `accounting_agent.md`, `manager_agent.md`, `pm_agent.md`, `chat_agent.md`)

### Hardening Rules (v0.12.2)
- Both SSE Response generators must be wrapped with `stream_with_context` — prevents silent crashes under Gunicorn/production WSGI.
- All `str(e)` in SSE error events replaced with Thai user-friendly messages; full tracebacks logged server-side with `exc_info=True`.
- Bare `except: pass` blocks replaced with `except OSError` (or specific exception) to avoid swallowing signals.

---

## 🤖 Specialized Sub-Agents

Instructional context for specific tasks can be found in `.claude/agents/`:
- `backend-python-reviewer.md`: **Primary reviewer** — run on every change to `app.py`, `core/`, `agents/`, `db.py`, `converter.py`, `mcp_server.py` before committing.
- `python-reviewer.md`: Reviewing other `.py` files (test scripts, etc.).
- `frontend-developer.md` & `ui-ux-reviewer.md`: UI/UX updates to `index.html` or `history.html`.
- `thai-doc-checker.md`: Validating Thai document quality and cultural correctness.
- `debug-assistant.md`: Troubleshooting errors — run immediately on any error, before attempting fixes.
- `security-checker.md`: Run before demo, before git commit, and when touching `.env` or API key config.
- `db-checker.md`: Run after editing `db.py` or `converter.py`, and before demo.
- `prompt-engineer.md`: Run when agent output is wrong, routing misbehaves, or when writing/editing system prompts.
- `demo-preparer.md`: Run when preparing for demo or dry-run.
- `project-documenter.md`: Updating `poc-plan.md` at end of sessions.
