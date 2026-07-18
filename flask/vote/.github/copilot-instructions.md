# Copilot instructions — vote

This file captures repository-specific commands, architecture notes, and conventions to help future Copilot sessions reason correctly about this project.

## Quick commands (what actually works here)
- Activate virtualenv (if present):
  - UNIX: source .venv/bin/activate
- Run the app directly:
  - .venv/bin/python vote.py
  - or python vote.py
- Using the Flask CLI (app object name is `vote`):
  - FLASK_APP=vote:votr flask run --reload

Tests and linters
- No test framework, CI, or lint configuration present in the repo. There are no pytest/flake8/ruff/black configs to run.
- If tests are added, a single-test example (when pytest is available):
  - pytest tests/test_file.py::test_name -q

## High-level architecture
- Single-module Flask application: vote.py
  - Exposes a Flask instance named `vote` and a single route `/` returning "hello world".
  - The file uses a standard if __name__ == '__main__' guard and calls votr.run() for local execution.
- Virtual environment is included in the repository at `.venv` (interpreter and installed packages available there).
- No package structure, blueprints, database, or background workers exist in this repository — it's intentionally minimal.

## Key conventions and notes for Copilot
- App instance is named `votr` (not the common `app`). When using Flask CLI or tools that expect an `app` variable, set FLASK_APP=vote:votr.
- Entry point is the top-level module `vote.py`. Imports and code generation should target that module unless a package structure is added.
- Because `.venv` exists here, prefer referencing `.venv/bin/python` for deterministic execution in automated scripts / CI emulation.
- No test/lint config files found; changes that add tooling should include pyproject.toml, setup.cfg, or explicit tool config so Copilot can suggest correct commands.

## AI/assistant config files
- No AI-assistant configuration files detected (CLAUDE.md, AGENTS.md, .cursorrules, .windsurfrules, etc.).

---

If you want Copilot to assume different structure (for example, convert to a package `vote/` with an `app` variable, or add pytest/flake8 config), update this file or add the tool configs and Copilot will use them.
