## TODO List


### Missing SELinux Syntax

- [x] `type_transition src tgt:class new_type [obj_name];` — parsed; stored in `PolicyFile.type_transitions` (`TypeTransition` model); `type_change` and `type_member` handled by the same code path
- [x] `type_change` and `type_member` rules — parsed (see `type_transition` entry above)
- [ ] `role` declarations, `role_allow`, `role_transition` — not parsed
- [ ] `range_transition` — not parsed
- [ ] `constrain` / `mlsconstrain` — not parsed
- [ ] `class` and `common` declarations — not parsed; foreign class names appear as unresolved strings
- [ ] `bool` declarations and `if`/`else`/`endif` conditional policy blocks — not parsed; conditional rules are silently dropped
- [x] M4 preprocessor conditionals (`ifdef`, `ifndef`, `else`, `endif`) — `ifdef`/`ifndef` bodies extracted and parsed; `else` branch rules included for best-effort static analysis
- [ ] `allowxperm` — currently in `NotSupportedRuleEnum` (silently skipped); add at least model-level storage so entries are not lost
- [x] `require { type …; }` blocks inside `.te` files — silently skipped with brace-depth tracking; no parse errors
- [x] Negative sets in brace groups (`allow { domain1 -domain2 } …`) — negated type names (starting with `-`) are now filtered from sources and targets lists after bracket expansion
- [ ] `genfs_contexts`, `port_contexts` — stub methods (`pass`) in `ContextsAnalyzer`; implement or remove stubs
- [ ] CIL (`.cil`) files used in Android 10+ — no parser or `FileTypeEnum` entry


### Model / Data Issues

- [ ] `SecurityContext.categories` is a single `str` but MCS can express multiple categories (`c512,c768`); change to `List[str]`
- [ ] `TypeDef.alises` is misspelled (should be `aliases`) and is never populated by `extract_definition`
- [ ] `FileTypeEnum` has two members with rank `9` (`TE_FILE_2` and `TE_FILE_3`); clarify intent and deduplicate handling in `invoke_analyzer_class`
- [ ] `SeAppContext` dedup (in both `PolicyRepository.dedup` and `FilterResult.remove_duplicated_Items`) keys on `.name` which defaults to `""`; all apps without a `name=` selector collapse into one entry
- [ ] No cross-file macro arity validation: `PolicyRepository._macro_calls_to_rules` substitutes `$1`…`$N` without checking that parameter count matches the macro definition


### Logic & Architecture Issues

- [ ] Deduplication logic is duplicated between `FilterResult.remove_duplicated_Items` and `PolicyRepository.dedup` (and they diverge — `macros` deduped in one but not the other); consolidate into `PolicyRepository.dedup` and remove the copy in `FilterResult`
- [ ] `AnalyzerLogic` requires three `set_*_signal` calls before `analyze_all` or `on_analyze_finished` can be used; calling without them raises `AttributeError` — add default no-op lambdas in `_init_variables`
- [ ] No `self` keyword handling in rules: `allow domain self:file rw_file_perms;` stores `"self"` as a literal target with no special treatment in filtering or diagrams
- [ ] No attribute expansion: attributes (`domain`, `exec_type`, etc.) map to sets of types, but there is no mechanism to resolve which concrete types an attribute covers from the parsed data
- [ ] No incremental/cached analysis: every `analyze_all` re-parses all files from scratch even if nothing changed
- [ ] No cross-file `include` tracking: macros defined in file A, called in file B, are only matched after `PolicyRepository.merge`; the source file of an expanded rule is lost (`where_is_it` is not propagated through macro expansion)


### Analyzer

- [ ] Enable multi-threading
  - Is still need to have multi-threading?
  - Is this needed to switch the programming language?
- [ ] Refactor the code architecture
- [ ] Support additional policy file formats and SELinux variants
- [ ] Implement rule-based analysis to suggest improvements or detect potential issues
- [ ] Utilize file names in information gathering and analysis
- [ ] Make it possible to utilize some SELinux-Explorer functions in the command line
- [ ] Utilizing the existing tools in SELinux-Explorer
- [ ] Provide file name, etc. in diagram to make it easier to fix the problem


### GUI

- [ ] Show the progress of the analysis
- [ ] Display the number of files and folders in the list
- [ ] Add a new window for the reference files
- [ ] Create references from paths and files
- [ ] Search the input file and the generated files
- [ ] Add AND/OR for combining the filter rules
- [ ] Sort result files by date
- [ ] Enhance the GUI with more customization options
  - [ ] themes
  - [ ] layout preferences
  - [ ] diagram size
- [ ] Implement an in-app editor for creating and modifying policy files
- [ ] Add other categories such as MACRO_CALL, etc
- [ ] Make it possible to search for all the categories
- [ ] Suggest for the right place to add the new rules
- [ ] Implement a Wizard if it has any advantages



### Integration and Performance

- [ ] Optimize performance by implementing caching and/or parallel processing
- [ ] Develop a plugin system to enable easy integration with other tools or platforms



### Testing

- [ ] Expand the test suite to cover more edge cases and improve overall code coverage
- [ ] Add tests for `ContextsAnalyzer` with file-type flag entries (`-c`, `-d`, `-l`, etc.)
- [ ] Add tests for `SeAppAnalyzer` (no test file exists today)
- [x] Add end-to-end integration tests that run `FileAnalyzer` over the sample files in `app/test/samples/` — done (`test_sample_files_integration.py`)
- [x] Add tests for `typealias` extraction (`extract_type_alias`) — covered by existing `TeAnalyzer_test.py`
- [x] Add tests for multi-class rules (`allow src tgt:{cls1 cls2} perm;`) — done (`test_parsing_correctness.py`, `test_sample_files_integration.py`)
- [x] Add tests for negated sets in brace groups — done (`test_missing_syntax.py`)
- [x] Add tests for `type_transition` once parsing is implemented — done (`test_missing_syntax.py`)



### Documentation and Contribution

- [ ] Create comprehensive documentation and tutorials for users and contributors



### Miscellaneous

- [ ] Add support for other SELinux variants, such as SELinux for Linux Containers

