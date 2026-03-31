---
name: docs-standards
description: Documentation standards for completed software projects. Defines two levels of documentation — Standard (every project) and Formal (enterprise or regulated projects). Covers README, Architecture, Backend Manual, Frontend Manual, User Guide, Changelog, Execution Summary, and optionally SRS and final PRD. Load this before writing any documentation.
license: MIT
compatibility: opencode
---

## What I cover

Document types, content requirements, formatting rules, writing tone, and quality gates for each document. Two levels: Standard (all projects) and Formal (enterprise/regulated). Instructions for determining which level applies and how to write each file from scratch.

## When to use me

Load this skill at the start of every documentation task before writing any file. The Orchestrator will specify Level 1 or Level 2 — if not specified, default to Level 1.

---

## Document Levels

### Level 1 — Standard (every project, no exceptions)

| File | Audience | Purpose |
|---|---|---|
| `README.md` | All | Entry point — setup, run, test |
| `ARCHITECTURE.md` | Developers | System design decisions and structure |
| `BACKEND_MANUAL.md` | Developers / API consumers | Full API reference |
| `FRONTEND_MANUAL.md` | Developers | UI structure and component guide |
| `USER_GUIDE.md` | End users | How to use the product — no technical jargon |
| `CHANGELOG.md` | All | What was built in this version |
| `EXECUTION_SUMMARY.md` | Team / Stakeholders | AI team process log |

### Level 2 — Formal (add when PRD indicates enterprise, regulated, or client-facing project)

| File | Audience | Purpose |
|---|---|---|
| `SRS.md` | Engineers / Auditors | IEEE-style requirements specification |
| `PRD_FINAL.md` | Product / Stakeholders | Final product requirements as actually built |

**How to determine level:**
- Level 2 if PRD mentions: enterprise client, compliance, audit, formal sign-off, government, healthcare, finance, or regulated industry
- Level 2 if user explicitly requests SRS or formal documentation
- Level 1 for all other projects

---

## Writing Rules (apply to every file)

1. **Write one file at a time.** Complete, verify, and save before starting the next.
2. **Re-read after writing.** Confirm zero placeholder text: no `[TBD]`, `[insert here]`, `TODO`, or empty sections.
3. **Never leave a section blank.** If a section genuinely does not apply, write: `N/A — not applicable for this project.`
4. **Source everything from the codebase.** Read actual file contents — never invent endpoint names, field names, or behaviors.
5. **Match audience tone per document.** Technical precision for developer docs. Plain language for USER_GUIDE. Formal register for SRS.
6. **Use markdown formatting throughout:** tables for structured data, code blocks for all commands and code, clear `##` and `###` headings.
7. **All command examples must be copy-pasteable.** Test mentally that every command shown would actually work on a fresh clone.

---

## README.md

**Audience:** Everyone — first file any reader opens.
**Tone:** Clear, welcoming, concise.

### Required Sections

```markdown
# [Project Name]

> One sentence describing what this project does and who it's for.

## Features
- [Feature 1]
- [Feature 2]

## Tech Stack
| Layer | Technology |
|---|---|
| Backend | Python / Flask [version] |
| Frontend | Next.js [version] |
| Database | [SQLite / PostgreSQL] |
| Auth | [JWT / None] |

## Prerequisites
- Python 3.11+
- Node.js 18+
- [Any other requirement]

## Quick Start

### 1. Clone and install
```bash
git clone [repo-url]
cd [project]
```

### 2. Backend setup
```bash
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your values
flask db upgrade
python run.py
```

### 3. Frontend setup
```bash
cd frontend
npm install
cp .env.example .env.local
# Edit .env.local — set NEXT_PUBLIC_API_URL=http://localhost:5000
npm run dev
```

## Running Tests
```bash
# Backend
cd backend && python -m pytest tests/ -v

# Frontend
cd frontend && npx playwright test
```

## Project Structure
[Brief directory tree showing top-level layout only]

## Environment Variables
| Variable | Required | Description |
|---|---|---|
| SECRET_KEY | Yes | Flask secret key |
| DATABASE_URL | Yes | Database connection string |
| NEXT_PUBLIC_API_URL | Yes | Backend base URL |

## License
[License name]
```

---

## ARCHITECTURE.md

**Audience:** Developers joining the project or doing code review.
**Tone:** Technical, decision-focused.

### Required Sections

```markdown
# Architecture

## System Overview
[1–2 paragraphs: what the system does, how the layers interact]

## Component Diagram
[ASCII or Mermaid diagram showing Frontend → Backend → Database flow]

## Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Backend framework | Flask | [Why Flask was chosen] |
| Frontend framework | Next.js App Router | [Why] |
| Database | [Name] | [Why — e.g., SQLite chosen for prototype simplicity] |
| Auth | [JWT / None] | [Why] |

## Backend Structure
[Explain App Factory pattern, Blueprint organization, why domains are split as they are]

## Frontend Structure
[Explain App Router layout, Server vs Client component strategy, data fetching approach]

## Data Flow
[Step-by-step: how a typical request flows from browser → Next.js → Flask → DB → back]

## Key Design Decisions
[Any non-obvious architectural choices and the reasoning behind them]

## Known Limitations
[Technical debt, shortcuts taken, things that would change at scale]
```

---

## BACKEND_MANUAL.md

**Audience:** Developers consuming the API or maintaining the backend.
**Tone:** Precise, technical.

### Required Sections

```markdown
# Backend Manual

## Overview
- Base URL: `http://localhost:5000`
- Auth: [JWT Bearer token / None]
- Content-Type: `application/json`

## Authentication
[If JWT: explain how to obtain a token, token lifetime, how to include it in requests]

## Response Format
All responses follow this shape:
```json
// Success
{ "data": ..., "message": "OK" }

// Error
{ "error": "Description", "details": "..." }
```

## Endpoints

### [Domain: e.g., Auth]

#### POST /api/auth/login
[Description]

**Request body:**
```json
{ "email": "user@example.com", "password": "password123" }
```

**Response 200:**
```json
{ "data": { "token": "eyJ...", "user": { "id": 1, "email": "..." } }, "message": "Login successful" }
```

**Error responses:**
| Status | Meaning |
|---|---|
| 401 | Invalid credentials |
| 422 | Missing required fields |

[Repeat for every endpoint in the codebase]

## Database Schema

### [TableName]
| Column | Type | Constraints | Description |
|---|---|---|---|
| id | Integer | PK, auto | Primary key |
| email | String(255) | Unique, Not Null | User email |

## Environment Variables
| Variable | Required | Default | Description |
|---|---|---|---|
| FLASK_APP | Yes | run.py | Entry point |
| SECRET_KEY | Yes | — | Flask secret |
| DATABASE_URL | Yes | sqlite:///dev.db | DB connection |

## Running Migrations
```bash
flask db init      # first time only
flask db migrate -m "description"
flask db upgrade
```
```

---

## FRONTEND_MANUAL.md

**Audience:** Developers working on the frontend.
**Tone:** Technical, component-focused.

### Required Sections

```markdown
# Frontend Manual

## Overview
- Framework: Next.js [version] App Router
- Language: TypeScript (strict mode)
- Styling: Tailwind CSS
- Theme: [Dark / Light / Custom]

## Project Structure
[Directory tree of app/, components/, lib/, hooks/, types/]

## Component Reference

### [ComponentName]
- **Type:** Server Component / Client Component
- **Location:** `app/[path]/ComponentName.tsx`
- **Props:** [TypeScript interface]
- **Purpose:** [What it renders and why]

[Repeat for all significant components]

## Pages and Routes

| Route | File | Auth Required | Description |
|---|---|---|---|
| `/` | `app/page.tsx` | No | Home page |
| `/dashboard` | `app/dashboard/page.tsx` | Yes | User dashboard |

## State Management
[Describe approach — e.g., React Server Components for server state, useState for local UI state, SWR for client-side fetching]

## API Integration
[Explain lib/api.ts, how tokens are handled, how errors are surfaced to the user]

## Environment Variables
| Variable | Description |
|---|---|
| NEXT_PUBLIC_API_URL | Backend API base URL |

## Running the Frontend
```bash
npm install
cp .env.example .env.local
npm run dev      # development
npm run build    # production build check
npm start        # production server
```
```

---

## USER_GUIDE.md

**Audience:** End users — non-technical. No code, no jargon.
**Tone:** Friendly, task-oriented, step-by-step.

### Required Sections

```markdown
# [Project Name] — User Guide

## What is [Project Name]?
[1–2 sentences a non-technical person can understand]

## Getting Started

### Creating an Account
1. Go to [URL]
2. Click **Sign Up**
3. Enter your name, email, and password
4. Click **Create Account**

### Logging In
1. Go to [URL]
2. Enter your email and password
3. Click **Log In**

## [Core Feature 1]
[Step-by-step instructions with UI element names bolded]

## [Core Feature 2]
[Step-by-step instructions]

## Frequently Asked Questions

**Q: [Common question]**
A: [Plain language answer]

## Getting Help
[Where to report issues or get support]
```

**Writing rules specific to USER_GUIDE:**
- Never mention file names, endpoints, or code
- Use bold for UI elements: **Save**, **Dashboard**, **Settings**
- Use numbered lists for every sequence of steps
- Write at a Grade 8 reading level
- If a feature doesn't exist in this project, omit that section entirely

---

## CHANGELOG.md

**Audience:** All — developers, users, stakeholders.
**Tone:** Factual, scannable.

### Required Format

```markdown
# Changelog

All notable changes to this project will be documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.0.0] — [YYYY-MM-DD]

### Added
- [Feature or capability that is new]
- [Another new thing]

### Changed
- [Behavior that changed from a previous state]

### Fixed
- [Bug that was resolved]

### Security
- [Security improvement, if any]
```

**Rules:**
- Version is `1.0.0` for initial project delivery
- Date is today's date
- List everything from the PRD that was implemented under **Added**
- List anything from the code review fix cycle under **Fixed**
- Do not leave any section empty — omit the section heading entirely if there's nothing to list

---

## EXECUTION_SUMMARY.md

**Audience:** Team leads, AI team, stakeholders reviewing the build process.
**Tone:** Analytical, factual.

### Required Sections

```markdown
# Execution Summary

## Project
[Project name and 1-sentence description]

## Build Overview
| Item | Detail |
|---|---|
| Date | [Today's date] |
| Backend Framework | Flask + [extensions] |
| Frontend Framework | Next.js [version] |
| Database | [Name] |
| Auth | [JWT / None] |
| Test Framework | pytest + Playwright |

## Features Built
[List every feature from the PRD with ✅ Implemented or ⚠️ Partial note]

## Code Quality Review
| Metric | Score |
|---|---|
| Code Quality & Readability | [X]/10 |
| Performance & Efficiency | [X]/10 |
| Security | [X]/10 |
| Maintainability & Best Practices | [X]/10 |

[Docs summary paragraph from review_code — paste verbatim here]

## Testing Results
- Backend: [N passed, N failed]
- Frontend: [N passed, N failed / Skipped — reason]
- Spec coverage: [N/N scenarios covered]

## Correction Loop Log
| Phase | Iterations Used | Root Cause Summary |
|---|---|---|
| Phase 4 (Runtime) | [N] / 3 | [Brief description or "None"] |
| Phase 5 (Testing) | [N] / 3 | [Brief description or "None"] |
| Phase 5.5 (Review) | [N] | [Brief description or "None"] |

## Notable Technical Decisions
[List any non-obvious choices made during development with brief rationale]

## Known Limitations
[Anything not implemented, deferred, or that would need attention before production]
```

---

## SRS.md (Level 2 only)

**Audience:** Engineers, auditors, formal project stakeholders.
**Tone:** Formal, precise, IEEE 830-inspired.

### Required Sections

```markdown
# Software Requirements Specification
**Version:** 1.0
**Date:** [YYYY-MM-DD]
**Status:** Final

## 1. Introduction
### 1.1 Purpose
### 1.2 Scope
### 1.3 Definitions and Abbreviations
### 1.4 References

## 2. Overall Description
### 2.1 Product Perspective
### 2.2 Product Functions (high-level feature list)
### 2.3 User Classes and Characteristics
### 2.4 Operating Environment
### 2.5 Constraints and Assumptions

## 3. Functional Requirements
[For each feature:]
**FR-01: [Name]**
- Description:
- Input:
- Output:
- Priority: High / Medium / Low

## 4. Non-Functional Requirements
### 4.1 Performance
### 4.2 Security
### 4.3 Reliability
### 4.4 Maintainability

## 5. External Interface Requirements
### 5.1 User Interfaces
### 5.2 API Interfaces
### 5.3 Database Interfaces
```

---

## PRD_FINAL.md (Level 2 only)

**Audience:** Product managers, stakeholders.
**Tone:** Business-focused.

This is the **as-built** PRD — not the original planning document. It reflects what was actually implemented. Derive it by reading the codebase and comparing against the original PRD.

### Required Sections

```markdown
# Product Requirements Document — Final (As Built)
**Version:** 1.0 Final
**Date:** [YYYY-MM-DD]

## Product Goal
[What the product does and the problem it solves]

## Scope
[What is included and what is explicitly out of scope]

## Features Delivered

### [Feature Name]
- **Status:** ✅ Fully implemented / ⚠️ Partially implemented
- **Description:** [What was built]
- **Acceptance Criteria:** [Was it met? Yes / No + note]

## Technical Summary
[Brief non-technical summary of the tech stack]

## Deferred Items
[Anything from original requirements that was not implemented, with reason]
```

---

## Quality Gate — Before Reporting Complete

Run this check on every file before marking it done:

- [ ] File exists on disk and is non-empty
- [ ] No placeholder text: `[TBD]`, `[insert here]`, `TODO`, `...`, empty sections
- [ ] All commands are copy-pasteable and accurate to the actual codebase
- [ ] All endpoint paths, field names, and types match actual code (not PRD assumptions)
- [ ] Tone matches the intended audience for this document
- [ ] Markdown renders correctly — no broken tables, unclosed code blocks
- [ ] Sections that don't apply say "N/A — not applicable for this project"