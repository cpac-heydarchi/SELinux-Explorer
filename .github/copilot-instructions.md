## Quick orientation for AI coding agents

This repository is a Python 3.x utility with a desktop GUI (PyQt5) that analyzes and visualizes SELinux policies.
Focus on the `app/` folder for runtime code, `analyzer/` for policy parsing, `drawer/` for visual output, and `ui/` for the GUI.

Key entry points and how code is run
- GUI: `cd app` then `python main.py` (this is the documented and expected working directory).
  - `app/main.py` imports `ui.MainUi` and expects the current working directory to be `app/` (there is no top-level `app` package).
- Tests: run `pytest` from the repository root; tests live under `app/test/`. `app/test/conftest.py` inserts the `app/` directory onto `sys.path` so imports like `from analyzer.TeAnalyzer import TeAnalyzer` work.

Dependencies & environment
- System packages: Graphviz, PyQt5 and Python 3.8+. `setup.sh` installs system deps on Debian/Ubuntu.
- Python packages: see `requirements.txt` (PyQt5, dataclass-wizard, pylint, black, pytest, codespell, psutil). Use `pip install -r requirements.txt`.
- GUI requires a display environment (X11/Wayland). On WSL/remote CI you will need an X server or run tests headlessly.

Project structure and data flow (big picture)
- Input parsers: `app/analyzer/` (TeAnalyzer, ContextsAnalyzer, SeAppAnalyzer, FileAnalyzer). They parse policy files (`*.te`, `file_contexts`, `service_contexts`, etc.).
- Core logic: `app/logic/AnalyzerLogic.py` and `FilterResult.py` apply filtering and aggregation.
- Model objects: `app/model/PolicyEntities.py` holds entity classes produced by analyzers.
- Drawers: `drawer/` (AdvanceDrawer, RelationDrawer) generate visual representations and interact with `plantuml/` components.
- UI: `ui/` contains windows and widgets (e.g. `MainUi.py`, `ResultUi.py`) that orchestrate analyzers and drawers.

Conventions & patterns specific to this repo
- Working-directory-based imports: many modules assume you run from `app/` (not the repo root). When editing or running scripts from root, prefer `cd app` first or run tests which add `app/` to `sys.path`.
- Persistent settings: `app/AppSetting.py` uses a dataclass (`AppSetting`) and `dataclass_wizard` for JSON serialization; saved refs go under `ref/` and outputs under `out/`.
- Logging: use `app/MyLogger.py` helpers which write to `app.log`. Prefer using `MyLogger.log_*` helpers to be consistent with current log format.
- Tests directory: tests are under `app/test/`. `conftest.py` ensures imports resolve by prepending `app/` to `sys.path`.

Developer workflows (commands)
- Install deps (Linux):
  - `./setup.sh` (installs apt packages and pip deps)
  - or `pip install -r requirements.txt`
- Run GUI (from repository root):
  - `cd app; python main.py`
- Run tests (from repository root):
  - `pytest -q`  (or `python -m pytest app/test`)
- Lint/formatting: `pylint` and `black` are in `requirements.txt`.

Integration points and external concerns
- Graphviz and PyQt5 are external system-level dependencies; drawing or UI changes often require these installed locally.
- The project may use `plantuml/` outputs — be mindful of relative paths (`OUT_DIR`, `ref/`) defined in `app/AppSetting.py`.

Editing tips for automated changes
- Prefer small, focused changes and run the local tests under `app/test` after edits.
- When adding imports in tests or scripts executed from the repo root, either run from `app/` or mirror `app/test/conftest.py` behaviour (add `app/` to `sys.path`).
- When touching UI code (`ui/`), run `cd app; python main.py` to verify the window launches; unit tests do not exercise PyQt GUI.

Files to inspect for context (examples)
- `app/main.py`, `app/AppSetting.py`, `app/MyLogger.py`
- `app/analyzer/*.py` (parsers)
- `app/logic/AnalyzerLogic.py`, `drawer/AdvanceDrawer.py`, `ui/MainUi.py`

If something's unclear
- Ask which target (GUI behavior, analyzer logic, or drawer output) you should change; indicate whether you can run the GUI locally (X server) or must rely on unit tests only.

----
If you'd like, I can iterate and tighten examples (e.g., copy-paste command snippets for Windows/WSL) or merge additional doc fragments from `doc/README.md` into this file.
