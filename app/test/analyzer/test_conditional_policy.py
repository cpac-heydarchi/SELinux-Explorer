"""Tests for bool declarations and if/else conditional policy blocks.

Conditional blocks were previously not understood at all: the ``if`` line
was reported as unknown input, the bare ``}``/``} else {`` lines corrupted
the multi-line statement assembler, and the rules inside the block were
lost. Both branches are now parsed (best-effort, same policy as
ifdef/ifndef) and bool declarations are stored in PolicyFile.bools.
"""

import os
import tempfile

from analyzer.TeAnalyzer import TeAnalyzer


def analyze_content(content):
    with tempfile.NamedTemporaryFile("w", suffix=".te", delete=False) as tmp_file:
        tmp_file.write(content)
        path = tmp_file.name
    try:
        return TeAnalyzer().analyze(path)
    finally:
        os.remove(path)


def test_bool_declaration_is_stored():
    policy = analyze_content("bool secure_mode_policy true;\n")
    assert len(policy.bools) == 1
    assert policy.bools[0].name == "secure_mode_policy"
    assert policy.bools[0].default_value == "true"


def test_if_block_rules_are_kept():
    policy = analyze_content(
        "bool secure_mode true;\n"
        "if (secure_mode) {\n"
        "allow app secure_file:file read;\n"
        "}\n"
    )
    assert len(policy.rules) == 1
    assert policy.rules[0].source == "app"
    assert policy.rules[0].target == "secure_file"


def test_if_else_keeps_both_branches():
    policy = analyze_content(
        "if (secure_mode) {\n"
        "allow app secure_file:file read;\n"
        "} else {\n"
        "allow app open_file:file { read write };\n"
        "}\n"
    )
    assert len(policy.rules) == 2
    targets = {rule.target for rule in policy.rules}
    assert targets == {"secure_file", "open_file"}
    else_rule = next(r for r in policy.rules if r.target == "open_file")
    assert sorted(else_rule.permissions) == ["read", "write"]


def test_single_line_if_block():
    policy = analyze_content("if (flag) { allow a b:file read; }\n")
    assert len(policy.rules) == 1
    assert policy.rules[0].source == "a"


def test_complex_condition_expression():
    policy = analyze_content("if (flag1 && !flag2) {\n" "allow a b:file read;\n" "}\n")
    assert len(policy.rules) == 1


def test_parser_state_survives_conditional_block():
    """Statements after the block must still be parsed normally."""
    policy = analyze_content(
        "if (secure_mode) {\n"
        "allow app secure_file:file read;\n"
        "}\n"
        "type later_type, domain;\n"
        "allow later_type other:file write;\n"
    )
    assert any(t.name == "later_type" for t in policy.type_def)
    assert len(policy.rules) == 2
