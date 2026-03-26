# Internal AI Assistant POC (GEMINI.md)

This project is a Proof of Concept (POC) for an **Internal AI Assistant Platform** designed for Thai employees. It uses a multi-agent architecture to generate various corporate documents (HR, Accounting, Management, PM) in Thai.

## Project Overview

- **Purpose**: Automate the creation of Thai documents like employment contracts, invoices, job descriptions, and management scripts using AI.
- **Architecture**: 
    - **Backend**: Flask (Python 3.11) with SSE (Server-Sent Events) for real-time streaming.
    - **AI Engine**: OpenRouter API (Claude 3.5 Sonnet / 4.5) via OpenAI SDK.
    - **Orchestration**: A central Orchestrator routes requests to specialized agents (HR, Accounting, Manager, PM).
    - **Frontend**: Single-file Vanilla HTML/JS/CSS ("The Silent Concierge" design) with `marked.js` for Markdown rendering.
    - **Persistence**: SQLite (`db.py`) for job history and session management.
    - **Tools**: MCP (Model Context Protocol) Server for filesystem operations in the `workspace/` directory.
    - **Export**: Multi-format support (.txt, .docx, .xlsx, .pdf) using `weasyprint`, `python-docx`, and `openpyxl`.

## Getting Started

### Prerequisites
- Python 3.10+ (Tested on 3.11)
- WSL (Windows Subsystem for Linux) recommended for Linux-based setup scripts.
- OpenRouter API Key.

### Setup & Installation
The easiest way to set up the project is using the provided script:
```bash
bash setup.sh
```
This script will:
1. Install system dependencies (WeasyPrint requirements + Thai fonts).
2. Create a virtual environment (`venv`).
3. Install Python dependencies from `requirements.txt`.
4. Create necessary directories (`workspace/`, `temp/`, `data/`).
5. Create a `.env` file from `.env.example`.

**Manual Configuration:**
Edit the `.env` file and provide your `OPENROUTER_API_KEY`.
```env
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=anthropic/claude-sonnet-4-5
WORKSPACE_PATH=/path/to/your/workspace
```

### Running the Application
Use the start script to launch the Flask server:
```bash
./start.sh
```
The server will run at `http://localhost:5000`.
- **Main Interface**: `http://localhost:5000`
- **Job History**: `http://localhost:5000/history`

### Testing
Several test scripts are available for validation:
- **Automated Use Cases**: `PYTHONUTF8=1 python test_cases.py` (Tests 5 core use cases).
- **Smoke Test**: `python smoke_test_phase0.py` (Basic health and SSE check).
- **Full Demo Check**: `python quick-demo-check.py` (Comprehensive readiness check).

## Development Conventions

### General Rules
- **Language**: All UI elements and AI outputs must be in **Thai**.
- **Disclaimers**: Every AI-generated document must include the standard AI disclaimer.
- **Filenames**: All files created by agents in the `workspace/` must use **English snake_case** (e.g., `employment_contract_somchai.docx`).
- **Versioning**: Follow semantic versioning (v0.X.X). Update `index.html` and `CHANGELOG.md` with every commit.

### Code Style
- **Backend**: Standard Python (PEP 8) with logging. Use `db.py` for all persistence.
- **Frontend**: Vanilla JS preferred. No heavy frameworks. Use CSS variables for the "Silent Concierge" design tokens.
- **Errors**: Return user-friendly Thai error messages via SSE.

### Specialized Subagents
The project uses specialized instructions for different tasks, located in `.claude/agents/`:
- `debug-assistant.md`: For troubleshooting.
- `frontend-developer.md` & `ui-ux-reviewer.md`: For UI changes.
- `python-reviewer.md`: For backend code quality.
- `thai-doc-checker.md`: For validating Thai document quality.
- `demo-preparer.md`: For final demo readiness.

### Maintenance
After making changes, you MUST update the following documentation to keep it in sync:
- `PROJECT_SUMMARY.md`: High-level overview and architecture.
- `CLAUDE.md`: Operational rules and version history.
- `CHANGELOG.md`: Detailed list of changes.
- `DEMO-READINESS-REPORT.md`: Status of demo features.
