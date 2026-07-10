"""
Failing tests for Critical bugs (data corruption / crashes).

Each test is expected to FAIL against the original code and PASS after the fix.
"""

import copy
import dataclasses
import pytest

from model.PolicyEntities import (
    Context,
    FileTypeEnum,
    PolicyFile,
    Rule,
    RuleEnum,
    SeAppContext,
    SecurityContext,
    TypeAlias,
)
from analyzer.ContextsAnalyzer import ContextsAnalyzer
from analyzer.TeAnalyzer import TeAnalyzer
from logic.FilterResult import FilterResult, FilterRule, FilterType


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pf():
    return PolicyFile("test_file", "", FileTypeEnum.FILE_CONTEXTS)


def _contexts_analyzer(file_name="file_contexts"):
    a = ContextsAnalyzer()
    a.policy_file = PolicyFile(file_name, "", FileTypeEnum.FILE_CONTEXTS)
    return a


def _te():
    t = TeAnalyzer()
    t.policy_file = PolicyFile("test.te", "", FileTypeEnum.TE_FILE)
    return t


# ---------------------------------------------------------------------------
# Bug: ContextsAnalyzer.extract_definition – optional file-type flag
#      (-c, -d, -l, -s, -b, -f, -p) between path and security context is
#      consumed as the first field of the security context, silently
#      corrupting user/role/type/level and leaving Context.file_type empty.
# ---------------------------------------------------------------------------

class TestContextsFileTypeFlag:
    def test_flag_d_does_not_corrupt_security_context(self):
        """-d flag must be stored in context.file_type; security context must use
        the next token (u:object_r:dummy_data_file:s0)."""
        c = _contexts_analyzer().extract_definition(
            "/data/misc/dummy  -d  u:object_r:dummy_data_file:s0"
        )
        assert c.security_context.user == "u", (
            f"user should be 'u', got '{c.security_context.user}'. "
            "The -d flag was consumed as the security context user field."
        )
        assert c.security_context.role == "object_r"
        assert c.security_context.type == "dummy_data_file"
        assert c.security_context.level == "s0"

    def test_file_type_flag_stored_in_context(self):
        """The file-type flag must be stored in Context.file_type."""
        c = _contexts_analyzer().extract_definition(
            "/data/misc/dummy  -d  u:object_r:dummy_data_file:s0"
        )
        assert c.file_type == "-d", (
            f"file_type should be '-d', got '{c.file_type}'"
        )

    def test_all_seven_flags_recognized(self):
        """All seven file-type flags must be parsed without corrupting the
        security context."""
        a = _contexts_analyzer()
        for flag in ("-f", "-d", "-l", "-c", "-b", "-s", "-p"):
            c = a.extract_definition(f"/some/path  {flag}  u:object_r:test_t:s0")
            assert c.file_type == flag, (
                f"Flag {flag} not stored; got file_type='{c.file_type}'"
            )
            assert c.security_context.user == "u", (
                f"Flag {flag} corrupted security_context.user: "
                f"got '{c.security_context.user}'"
            )
            assert c.security_context.type == "test_t", (
                f"Flag {flag}: type should be 'test_t', got "
                f"'{c.security_context.type}'"
            )

    def test_entry_without_flag_still_works(self):
        """Entries without a file-type flag must continue to parse correctly."""
        c = _contexts_analyzer().extract_definition(
            "/vendor/bin/hw/svc  u:object_r:vendor_exec:s0"
        )
        assert c.file_type == "", f"No flag present, file_type should be '', got '{c.file_type}'"
        assert c.security_context.user == "u"
        assert c.security_context.type == "vendor_exec"


# ---------------------------------------------------------------------------
# Bug: TypeAlias is missing the @dataclass decorator.
#      Without it, dataclasses.is_dataclass() returns False,
#      dataclasses.fields() raises TypeError, and JSON serialization breaks.
# ---------------------------------------------------------------------------

class TestTypeAlias:
    def test_type_alias_is_a_dataclass(self):
        """TypeAlias must be decorated with @dataclass."""
        assert dataclasses.is_dataclass(TypeAlias), (
            "TypeAlias is missing the @dataclass decorator. "
            "dataclasses.fields(TypeAlias) will raise TypeError, and "
            "JSONWizard serialization will not work correctly."
        )

    def test_type_alias_fields_are_instance_scoped(self):
        """After @dataclass is added, fields() must enumerate all three fields."""
        field_names = {f.name for f in dataclasses.fields(TypeAlias)}
        assert {"name", "alias", "where_is_it"}.issubset(field_names), (
            f"Expected fields name/alias/where_is_it; got {field_names}"
        )


# ---------------------------------------------------------------------------
# Bug: PolicyFile has no `file_name` field.
#      FilterResult.filter sets filtered_policy_file.file_name dynamically;
#      AdvancedDrawer.draw_uml reads policy_file.file_name.
#      Both raise AttributeError when the field is absent.
# ---------------------------------------------------------------------------

class TestPolicyFileFileName:
    def test_policy_file_has_file_name_field(self):
        """PolicyFile must declare a file_name field."""
        field_names = {f.name for f in dataclasses.fields(PolicyFile)}
        assert "file_name" in field_names, (
            "PolicyFile is missing 'file_name'. "
            "FilterResult.filter and AdvancedDrawer.draw_uml both use "
            "policy_file.file_name and will raise AttributeError."
        )

    def test_file_name_accessible_on_new_instance(self):
        """A freshly-created PolicyFile must have file_name accessible without error."""
        pf = PolicyFile()
        _ = pf.file_name  # must not raise AttributeError

    def test_file_name_settable(self):
        """file_name must be settable on PolicyFile instances."""
        pf = PolicyFile()
        pf.file_name = "domain_filtered_read"
        assert pf.file_name == "domain_filtered_read"


# ---------------------------------------------------------------------------
# Bug: SeAppContext has no `level` field declared.
#      SeAppAnalyzer.extract_definition assigns se_app.level = value, but the
#      field is absent from the dataclass, so it is not included in JSON
#      serialization and dataclasses.fields() does not enumerate it.
# ---------------------------------------------------------------------------

class TestSeAppContextLevel:
    def test_seapp_context_has_level_field(self):
        """SeAppContext must declare a level field."""
        field_names = {f.name for f in dataclasses.fields(SeAppContext)}
        assert "level" in field_names, (
            "SeAppContext is missing the 'level' field. "
            "SeAppAnalyzer sets se_app.level but the field is absent, so the "
            "value is never included in JSON serialization."
        )

    def test_level_survives_json_round_trip(self):
        """A SeAppContext with level set must round-trip through JSON correctly."""
        ctx = SeAppContext()
        ctx.level = "s0:c512,c768"
        as_json = ctx.to_json()
        restored = SeAppContext.from_json(as_json)
        assert restored.level == "s0:c512,c768", (
            f"level lost after JSON round-trip: got '{restored.level}'. "
            "The field is likely not declared in the dataclass."
        )


# ---------------------------------------------------------------------------
# Bug: FilterResult.filter_permission mutates the source Rule object.
#      temp_rule = rule is a reference, not a copy.
#      temp_rule.permissions = [filter_rule.keyword] overwrites the original.
# ---------------------------------------------------------------------------

class TestFilterPermissionMutation:
    def _make_policy_with_rule(self, permissions):
        pf = PolicyFile()
        r = Rule()
        r.rule = RuleEnum.ALLOW
        r.source = "domain"
        r.target = "target"
        r.class_type = "file"
        r.permissions = list(permissions)
        pf.rules.append(r)
        return pf, r

    def test_original_rule_permissions_unchanged_after_filter(self):
        """filter_permission must not modify the permissions list of the original
        Rule in the master policy_file."""
        pf, original_rule = self._make_policy_with_rule(["read", "write"])
        original_permissions = list(original_rule.permissions)

        fr = FilterResult()
        filter_rule = FilterRule(FilterType.PERMISSION, "read", False)
        filtered_pf = PolicyFile()
        fr.filter_permission(filter_rule, pf, filtered_pf)

        assert original_rule.permissions == original_permissions, (
            f"Original rule permissions were mutated from {original_permissions} "
            f"to {original_rule.permissions}. "
            "filter_permission must copy the rule before modifying permissions."
        )

    def test_filtered_rule_has_only_requested_permission(self):
        """The rule in filtered_policy_file must have only the filtered permission."""
        pf, _ = self._make_policy_with_rule(["read", "write"])

        fr = FilterResult()
        filter_rule = FilterRule(FilterType.PERMISSION, "read", False)
        filtered_pf = PolicyFile()
        fr.filter_permission(filter_rule, pf, filtered_pf)

        assert filtered_pf.rules, "No rules in filtered result"
        assert filtered_pf.rules[0].permissions == ["read"], (
            f"Filtered rule should have only ['read'], "
            f"got {filtered_pf.rules[0].permissions}"
        )

    def test_second_filter_still_finds_write_permission(self):
        """After filtering for 'read', the master policy_file must still contain
        'write' so a subsequent filter for 'write' also finds it."""
        pf, _ = self._make_policy_with_rule(["read", "write"])

        fr = FilterResult()
        # First filter: read
        fr.filter_permission(FilterRule(FilterType.PERMISSION, "read", False), pf, PolicyFile())
        # Second filter: write — must still work on the un-mutated pf
        filtered_write = PolicyFile()
        fr.filter_permission(FilterRule(FilterType.PERMISSION, "write", False), pf, filtered_write)

        assert filtered_write.rules, (
            "No 'write' rules found after 'read' filter ran first. "
            "The original rule's permissions were mutated by the first filter call."
        )


# ---------------------------------------------------------------------------
# Bug: Rule.rule is annotated as str = "" but extract_rule stores a RuleEnum.
#      String comparisons (rule.rule == "allow") silently return False.
#      to_string() produces "RuleEnum.ALLOW" instead of "allow".
# ---------------------------------------------------------------------------

class TestRuleRuleField:
    def test_extract_rule_stores_string_keyword(self):
        """rule.rule must be the string keyword ('allow'), not a RuleEnum instance."""
        rules = _te().extract_rule("allow src tgt:file read;")
        assert rules
        assert rules[0].rule == "allow", (
            f"Expected rule.rule == 'allow' (str), got {repr(rules[0].rule)}. "
            "extract_rule stores a RuleEnum enum value instead of the string."
        )

    def test_neverallow_stores_string_keyword(self):
        """neverallow rules must also store the string keyword."""
        rules = _te().extract_rule("neverallow src tgt:file write;")
        assert rules
        assert rules[0].rule == "neverallow", (
            f"Expected 'neverallow', got {repr(rules[0].rule)}"
        )

    def test_rule_to_string_does_not_contain_enum_repr(self):
        """to_string() must not produce 'RuleEnum.ALLOW'; it must produce 'allow'."""
        rules = _te().extract_rule("allow src tgt:file read;")
        assert rules
        s = rules[0].to_string()
        assert "RuleEnum" not in s, (
            f"to_string() contains enum repr 'RuleEnum': {s[:120]}"
        )
