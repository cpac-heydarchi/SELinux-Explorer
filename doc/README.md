# SELinux Explorer Documentation

This documentation provides a high-level overview of the project, key modules, core data models, and how components interact. It also includes PlantUML diagrams you can render locally.

## What this app does

SELinux Explorer parses Android/SELinux policy artifacts (e.g., .te files, seapp_contexts, file_contexts) and produces diagrams that visualize domains, types, contexts, and rules. It also provides a PyQt5 GUI to filter domains, class types, permissions, and file paths and renders focused diagrams.

## Architecture overview

Key layers:
- UI (PyQt5): `app/ui/MainUi.py` is the entry point for the GUI and wires up toolbars, result panes, and filter views.
- Logic: `app/logic/AnalyzerLogic.py` orchestrates analysis, merging results across files into a reference `PolicyFile`, and triggers diagram generation. `app/logic/FilterResult.py` builds filtered `PolicyFile` views and calls drawers.
- Analyzers: `app/analyzer/*.py` parse each input type and return a `PolicyFile` with populated entities (`TypeDef`, `Attribute`, `Rule`, `Context`, `SeAppContext`, etc.). `FileAnalyzer` discovers files and delegates parsing to `TeAnalyzer`, `SeAppAnalyzer`, and `ContextsAnalyzer` based on filename.
- Model: `app/model/PolicyEntities.py` defines all core dataclasses and enums: `PolicyFile`, `Rule`, `TypeDef`, `Attribute`, `Context`, `SeAppContext`, `PolicyMacro`, etc.
- Drawing: `app/drawer/*.py` generates PlantUML text and renders diagrams via PlantUML jar. `RelationDrawer` draws a participant/sequence-like view; `AdvancedDrawer` produces domain packages, notes for types/attributes/users, and colored edges for allow/neverallow.
- Utilities and Settings: `AppSetting.py` holds app metadata/settings and output folders; `MyLogger.py` provides error and debug logging; helpers for files and system are expected in `PythonUtilityClasses`.

Render paths and output folders are controlled by constants such as `OUT_DIR` (defaults to `out/`). PlantUML rendering calls Java with `app/plantuml/plantuml.jar`.

## Important parts of the code

### Entrypoint and UI
- `app/main.py` creates a `QApplication` and shows `MainWindow`.
- `app/ui/MainUi.py` builds the main layout and connects UI components. It loads/saves `AppSetting` to persist last paths and filter preferences.

### Analyzer orchestrator
- `AnalyzerLogic.analyze_all(included_paths, excluded_paths)` calls `FileAnalyzer.analyze()` and optionally merges results. It then builds a consolidated `ref_policy_file` via `make_ref_policy_file()` and expands `PolicyMacroCall` entries into concrete `Rule`s using `convert_macrocall_to_rule()`.
- It signals UI updates with generated diagram files and passes the reference policy file to the result panel.

### File discovery and parsing
- `FileAnalyzer.gather_file_info()` walks selected paths and collects files using `SystemUtility`. `detect_lang()` maps filenames to `FileTypeEnum` and chooses a concrete analyzer in `invoke_analyzer_class()`.
- `TeAnalyzer` parses SELinux `.te` files:
  - Collects multi-line statements and macro definitions/calls in `extract_items_to_process()`.
  - Processes lines to extract `TypeDef`, attributes, rules (`allow`, `neverallow`, `auditallow`, `dontaudit`), permissives, type aliases, macro defs, and macro calls.
  - `extract_rule()` handles brace groups and expands bracketed lists into multiple `Rule` objects.
- `SeAppAnalyzer` reads `seapp_contexts` and maps selectors to `SeAppContext` fields.
- `ContextsAnalyzer` reads `*contexts` files and produces `Context` entries with populated `SecurityContext`.

### Data model
- `PolicyFile` is a container for all extracted entities from a single source. `AnalyzerLogic` merges multiple `PolicyFile` instances into a reference view and expands macros into rules.
- Key types:
  - `Rule(rule, source, target, class_type, permissions)` describes an SELinux rule.
  - `TypeDef(name, types)` a domain and its class types.
  - `Attribute(name, attributes)` attributes associated with a domain.
  - `SeAppContext` selectors for Android app domains, plus derived output fields (`domain`, `type`, `level`).
  - `Context(path_name, security_context)` for file/service contexts.

### Diagram generation
- `RelationDrawer.draw_uml(policy_file)` builds a simple participant list per domain or context and arrows for rules (green for allow, red for neverallow), writes a `.puml`, and runs PlantUML to create a PNG.
- `AdvancedDrawer.draw_uml(policy_file)` groups by domain using "package" containers, and adds notes listing types, attributes, users, and process names; it scales the canvas for larger graphs.

## Diagrams

PlantUML sources are in `doc/diagrams/`:
- `architecture.puml`: high-level component architecture.
- `dataflow.puml`: end-to-end data flow from user actions to rendered diagrams.
- `class-analyzers.puml`: class diagram of analyzers and logic.

To render locally, ensure Java is installed and run PlantUML. You can also use VS Code PlantUML preview extensions.

## How to run the app

Prerequisites:
- Python 3.8+
- Java (for PlantUML rendering)

Install Python dependencies from `requirements.txt`, then start the GUI:

1) Install dependencies
2) Run the GUI

## Notable behaviors and edge cases
- `AnalyzerLogic.convert_macrocall_to_rule()` expands macro calls by parameter index. It replaces `$1`, `$2`, ... in rule source/target/class_type, but note a likely off-by-one in class type replacement (uses `$i` not `$i+1`).
- `TeAnalyzer.extract_items_to_process()` stitches multi-line statements, macro defs, and calls by balancing parentheses and semicolons.
- `FilterResult` constructs a filtered `PolicyFile` and calls both `RelationDrawer` and `AdvancedDrawer` to output diagrams.
- `DrawerHelper.generate_png()` shells out to Java with a relative jar path `plantuml/plantuml.jar`; run from `app/` working directory or adjust path accordingly.

## Repository docs

- `CONTRIBUTING.md` and `TODO.md` provide contribution notes and future work. The new `doc/` folder is for human-oriented documentation and diagrams.

