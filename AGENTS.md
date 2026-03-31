# Repository Guidelines

## Project Structure & Module Organization
`app.py` is the Flask entry point and wires API routes, SSE streaming, and confirmation flows. Core orchestration logic lives in `core/` (`orchestrator.py`, `agent_factory.py`, `shared.py`, `utils.py`). Agent implementations live in `agents/`, and their system prompts live in `prompts/`. Frontend assets are the root-level `index.html` and `history.html`. Persistent and generated data go to `data/`, `workspace/`, and `temp/`. Design notes and implementation plans live in `docs/` and `plans/`.

## Build, Test, and Development Commands
Use the provided shell scripts instead of ad hoc setup.

- `bash setup.sh`: installs system packages, creates `venv`, installs Python dependencies, and initializes local directories.
- `./start.sh`: activates `venv`, refreshes dependencies, and starts Gunicorn on `http://localhost:5000`.
- `python smoke_test_phase0.py`: runs a fast smoke test against a running local server.
- `python test_cases.py`: exercises routed agent flows and PM save behavior.
- `python test_concurrency_pm.py --tc 1 2 3 4`: runs concurrency and workspace-switch scenarios.

## Coding Style & Naming Conventions
Follow existing Python style: 4-space indentation, `snake_case` for functions and variables, `PascalCase` for classes, and uppercase constants such as `BASE_URL`. Keep modules focused by responsibility and place shared runtime logic in `core/` rather than duplicating it across agents. Prefer short docstrings on non-obvious helpers. There is no configured formatter in the repo, so match surrounding code closely and keep imports and logging consistent with existing files.

## Testing Guidelines
This repository uses script-based integration tests rather than a dedicated `pytest` suite. Add new checks near the relevant script, and name standalone test files `test_*.py`. Before opening a PR, start the server with `./start.sh`, then run at least `python smoke_test_phase0.py` and the most relevant scenario test for your change. Changes touching routing, workspace handling, or PM flows should include a concurrency or end-to-end check.

## Commit & Pull Request Guidelines
Recent history follows a version-prefixed conventional style such as `v0.23.0 — feat: ...` or `v0.23.0 — fix: ...`. Keep commit subjects short and action-oriented. PRs should state the user-visible impact, list the commands used for verification, link any related plan or issue, and include screenshots when `index.html` or `history.html` behavior changes.

## Security & Configuration Tips
Do not commit `.env`, API keys, or generated SQLite data. Keep writes inside `workspace/` or configured allowed roots, and validate any new file operations against the workspace guard behavior already used by the app.
