"""
Failing tests that document known parsing-correctness bugs.

Each test is expected to FAIL against the original code and PASS after the fix.
The module name and each test docstring describe the exact bug being exercised.
"""

import pytest
from model.PolicyEntities import FileTypeEnum, PolicyFile
from analyzer.TeAnalyzer import TeAnalyzer
from analyzer.SeAppAnalyzer import SeAppAnalyzer
from analyzer.AnalyzerUtility import clean_line


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _te(policy_file=None):
    t = TeAnalyzer()
    t.policy_file = policy_file or PolicyFile("test.te", "", FileTypeEnum.TE_FILE)
    return t


def _seapp(policy_file=None):
    s = SeAppAnalyzer()
    s.policy_file = policy_file or PolicyFile(
        "seapp_contexts", "", FileTypeEnum.SEAPP_CONTEXTS
    )
    return s


# ---------------------------------------------------------------------------
# Bug: extract_rule – multi-class rule maps class names to `target` and
#      stores "###" as class_type instead of the real class name.
#
#      allow src tgt:{cls1 cls2} perm;
#      should produce:
#        Rule(source="src", target="tgt", class_type="cls1", permissions=["perm"])
#        Rule(source="src", target="tgt", class_type="cls2", permissions=["perm"])
# ---------------------------------------------------------------------------

def test_extract_rule_multiclass_single_perm():
    """Multi-class with a single permission – target and class_type must be correct."""
    rules = _te().extract_rule("allow src tgt:{cls1 cls2} perm;")

    assert len(rules) == 2, f"Expected 2 rules, got {len(rules)}: {rules}"

    targets = {r.target for r in rules}
    class_types = {r.class_type for r in rules}

    assert targets == {"tgt"}, f"target should be 'tgt', got {targets}"
    assert class_types == {"cls1", "cls2"}, (
        f"class_type should be {{'cls1','cls2'}}, got {class_types}"
    )
    assert all(r.source == "src" for r in rules)
    assert all(r.permissions == ["perm"] for r in rules)


def test_extract_rule_multiclass_multi_perm():
    """Multi-class with a permission set – target and class_type must be correct."""
    rules = _te().extract_rule("allow src tgt:{cls1 cls2} {p1 p2};")

    assert len(rules) == 2, f"Expected 2 rules, got {len(rules)}: {rules}"

    targets = {r.target for r in rules}
    class_types = {r.class_type for r in rules}

    assert targets == {"tgt"}, f"target should be 'tgt', got {targets}"
    assert class_types == {"cls1", "cls2"}, (
        f"class_type should be {{'cls1','cls2'}}, got {class_types}"
    )
    assert all(r.source == "src" for r in rules)
    assert all(set(r.permissions) == {"p1", "p2"} for r in rules)


def test_extract_rule_multiclass_no_class_type_is_hash_placeholder():
    """Regression guard: class_type must never be the internal '###' placeholder."""
    rules = _te().extract_rule("allow src tgt:{cls1 cls2 cls3} {p1 p2};")
    for r in rules:
        assert r.class_type != "###", (
            f"class_type was left as the internal placeholder '###'; "
            f"multi-class parsing is broken (rule: {r})"
        )


# ---------------------------------------------------------------------------
# Bug: SeAppAnalyzer.extract_definition – uses split(" ") so tab-separated
#      or mixed-whitespace lines are not tokenised correctly.  When a tab
#      separates key=value pairs, the whole remainder of the line is consumed
#      as the value of the first key.
# ---------------------------------------------------------------------------

def test_seapp_tab_separated_fields_are_parsed():
    """Fields separated by a tab character must each be stored in the right attribute."""
    se_app = _seapp().extract_definition(
        "user=_app\tseinfo=platform\tdomain=myapp\ttype=app_data_file"
    )

    assert se_app.user == "_app", (
        f"user should be '_app', got '{se_app.user}' "
        f"(tab after value was probably consumed into the user field)"
    )
    assert se_app.seinfo == "platform", f"seinfo should be 'platform', got '{se_app.seinfo}'"
    assert se_app.domain == "myapp", f"domain should be 'myapp', got '{se_app.domain}'"
    assert se_app.type == "app_data_file", f"type should be 'app_data_file', got '{se_app.type}'"


def test_seapp_mixed_whitespace_all_fields_parsed():
    """Consecutive spaces and tabs between key=value pairs must not drop any field."""
    se_app = _seapp().extract_definition(
        "user=_app  seinfo=platform  name=com.example  domain=myapp"
    )

    assert se_app.user == "_app"
    assert se_app.seinfo == "platform"
    assert se_app.name == "com.example"
    assert se_app.domain == "myapp"


# ---------------------------------------------------------------------------
# Bug: clean_line – unconditionally replaces "--" everywhere in the input
#      string, which corrupts identifiers or rule content that legitimately
#      contain a double-dash (e.g., vendor type names like "hal--service").
# ---------------------------------------------------------------------------

def test_clean_line_preserves_double_dash_in_identifier():
    """A type name containing '--' must be returned intact; not silently mangled."""
    line = "allow hal--service target:file { read };"
    result = clean_line(line)
    assert "--" in result, (
        f"clean_line removed '--' from content: got '{result}'. "
        "The unconditional replace('--', '') must be removed."
    )
    assert "hal--service" in result, (
        f"Identifier 'hal--service' was corrupted to '{result}'"
    )


def test_clean_line_double_dash_comment_style():
    """A line that is purely a '--' comment should still return None (treated as blank)."""
    # This is NOT standard SELinux comment syntax, but the function should not
    # corrupt content that happens to contain '--'.
    line = "type hal--svc, domain; -- legacy name"
    result = clean_line(line)
    # After the fix the identifier must be preserved; the '-- legacy name' part
    # can be stripped or kept, but 'hal--svc' must not become 'halsvc'.
    assert result is not None
    assert "hal--svc" in result, (
        f"Identifier 'hal--svc' should be present in cleaned result, got: '{result}'"
    )


# ---------------------------------------------------------------------------
# Bug: extract_items_to_process – an unclosed define() block causes all
#      subsequent lines to be absorbed into tmp_lst_lines and never emitted.
# ---------------------------------------------------------------------------

def test_extract_items_unclosed_define_does_not_swallow_subsequent_rules():
    """
    A malformed file where a define() macro is never closed must not silently
    discard rules that appear after the unclosed block.
    """
    lines = [
        "define(`my_macro', `",          # opens macro, never closed
        "allow a b:c { read };",          # inside unclosed macro body
        # No closing ')'
        "allow standalone source:file { write };",  # rule AFTER the broken block
    ]

    te = _te()
    result = te.extract_items_to_process(lines)

    # The standalone rule must appear in the output even though the define
    # above it was never closed.
    joined = " ".join(result)
    assert any("standalone" in item for item in result), (
        f"Rule containing 'standalone' was swallowed by the unclosed define(). "
        f"Extracted items: {result}"
    )


# ---------------------------------------------------------------------------
# Bug: SeAppAnalyzer – key matching uses substring ("seinfo" in split[0])
#      which silently mis-routes keys that contain a known key as a substring
#      (e.g. "seinfo_extra" matches the "seinfo" branch).
#      Also: split("=") without a limit drops the rest of a value that
#      contains "=" (e.g. name=com.example=v2 → only stores "com.example").
# ---------------------------------------------------------------------------

def test_seapp_substring_key_does_not_match_superset_key():
    """A key like 'seinfo_extra' must NOT match the 'seinfo' handler."""
    se_app = _seapp().extract_definition(
        "user=_app seinfo=platform seinfo_extra=should_be_ignored domain=myapp"
    )
    # 'seinfo' must be 'platform', not overwritten by 'seinfo_extra'
    assert se_app.seinfo == "platform", (
        f"seinfo should be 'platform', got '{se_app.seinfo}'. "
        "Substring key matching caused 'seinfo_extra' to overwrite the seinfo field."
    )
    assert se_app.domain == "myapp"


def test_seapp_value_with_equals_sign_preserved():
    """A value that contains '=' must be stored in full (requires split('=', 1))."""
    se_app = _seapp().extract_definition(
        "user=_app name=com.example=v2 domain=myapp"
    )
    assert se_app.name == "com.example=v2", (
        f"name should be 'com.example=v2', got '{se_app.name}'. "
        "split('=') without a limit drops the '=v2' portion of the value."
    )


def test_seapp_camelcase_levelFrom_parsed_correctly():
    """Android seapp_contexts uses 'levelFrom' (camelCase), not 'level_from'.
    The parser must map it to se_app.level_from, not se_app.level."""
    se_app = _seapp().extract_definition(
        "user=_app seinfo=platform domain=myapp type=app_data_file levelFrom=user"
    )
    assert se_app.level_from == "user", (
        f"level_from should be 'user', got '{se_app.level_from}'. "
        "The camelCase key 'levelFrom' was not mapped to level_from."
    )
    # The 'level' field must remain empty — levelFrom must not fall through to it
    assert getattr(se_app, "level", "") != "user", (
        "The value 'user' landed in se_app.level instead of se_app.level_from."
    )


def test_seapp_camelcase_isPrivApp_parsed_correctly():
    """Android seapp_contexts uses 'isPrivApp' (camelCase), not 'is_priv_app'."""
    se_app = _seapp().extract_definition(
        "user=_app seinfo=platform isPrivApp=true domain=myapp"
    )
    assert se_app.is_priv_app is True, (
        f"is_priv_app should be True, got {se_app.is_priv_app}. "
        "The camelCase key 'isPrivApp' was not recognised."
    )
