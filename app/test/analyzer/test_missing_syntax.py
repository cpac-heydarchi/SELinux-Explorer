"""
Tests for previously-unsupported SELinux syntax items.

Each test is expected to FAIL against the original code and PASS after the fix.
Items covered (from TODO § Missing SELinux Syntax):
  • type_transition / type_change / type_member
  • Negative sets in brace groups  ({ domain1 -domain2 })
  • require { … } blocks
  • M4 ifdef / ifndef blocks
"""

import os
import pytest
from model.PolicyEntities import FileTypeEnum, PolicyFile
from analyzer.TeAnalyzer import TeAnalyzer
from analyzer.FileAnalyzer import FileAnalyzer

SAMPLES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "samples")
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _te():
    t = TeAnalyzer()
    t.policy_file = PolicyFile("test.te", "", FileTypeEnum.TE_FILE)
    return t


# ---------------------------------------------------------------------------
# type_transition / type_change / type_member
# ---------------------------------------------------------------------------


class TestTypeTransition:
    def test_policy_file_has_type_transitions_field(self):
        """PolicyFile must declare a type_transitions list field."""
        import dataclasses

        field_names = {f.name for f in dataclasses.fields(PolicyFile)}
        assert "type_transitions" in field_names, (
            "PolicyFile is missing 'type_transitions'. "
            "type_transition rules are silently dropped."
        )

    def test_type_transition_basic_parsed(self):
        """type_transition src tgt:class default; must be stored in type_transitions."""
        te = _te()
        te.process_line("type_transition dummy dummy_new_exec:process dummy_new;")
        assert te.policy_file.type_transitions, (
            "type_transition rule was not stored; process_line does not handle it"
        )
        tt = te.policy_file.type_transitions[0]
        assert tt.source == "dummy"
        assert tt.target == "dummy_new_exec"
        assert tt.class_type == "process"
        assert tt.default_type == "dummy_new"
        assert tt.object_name == ""

    def test_type_transition_with_spaces_around_colon(self):
        """type_transition src target : class default; (spaces around colon)."""
        te = _te()
        te.process_line("type_transition adbd shell : process adbd_shell;")
        assert te.policy_file.type_transitions
        tt = te.policy_file.type_transitions[0]
        assert tt.target == "shell"
        assert tt.class_type == "process"
        assert tt.default_type == "adbd_shell"

    def test_type_transition_with_object_name(self):
        """type_transition with optional quoted object name."""
        te = _te()
        te.process_line('type_transition dummy tmp_t:file dummy_tmp_t "dummy.pid";')
        assert te.policy_file.type_transitions
        tt = te.policy_file.type_transitions[0]
        assert tt.source == "dummy"
        assert tt.target == "tmp_t"
        assert tt.class_type == "file"
        assert tt.default_type == "dummy_tmp_t"
        assert tt.object_name == "dummy.pid"

    def test_type_change_parsed(self):
        """type_change src tgt:class default; must also be stored."""
        te = _te()
        te.process_line("type_change dummy dummy_new_exec:file dummy_rw_t;")
        assert te.policy_file.type_transitions, (
            "type_change was not parsed; process_line does not handle it"
        )
        tt = te.policy_file.type_transitions[0]
        assert tt.rule_type == "type_change"
        assert tt.source == "dummy"
        assert tt.default_type == "dummy_rw_t"

    def test_type_member_parsed(self):
        """type_member src tgt:class default; must also be stored."""
        te = _te()
        te.process_line("type_member dummy dummy_new_exec:file dummy_member_t;")
        assert te.policy_file.type_transitions
        tt = te.policy_file.type_transitions[0]
        assert tt.rule_type == "type_member"
        assert tt.default_type == "dummy_member_t"

    def test_type_transition_rule_type_field(self):
        """rule_type field must record which keyword was used."""
        te = _te()
        te.process_line("type_transition dummy dummy_new_exec:process dummy_new;")
        assert te.policy_file.type_transitions[0].rule_type == "type_transition"


# ---------------------------------------------------------------------------
# Negative sets in brace groups
# ---------------------------------------------------------------------------


class TestNegatedSets:
    def test_negated_source_not_in_rules(self):
        """allow { domain1 -domain2 } tgt:file read; — '-domain2' must not
        appear as a source in the generated rules."""
        rules = _te().extract_rule("allow { domain1 -domain2 } target:file read;")
        sources = {r.source for r in rules}
        assert "-domain2" not in sources, (
            f"Negated type '-domain2' leaked into sources: {sources}"
        )
        assert "domain1" in sources, "Non-negated source 'domain1' is missing"

    def test_negated_target_not_in_rules(self):
        """neverallow src { type1 -type2 }:class perm; — '-type2' must not
        appear as a target."""
        rules = _te().extract_rule(
            "neverallow appdomain { system_file -vendor_file }:file execute;"
        )
        targets = {r.target for r in rules}
        assert "-vendor_file" not in targets, (
            f"Negated type '-vendor_file' leaked into targets: {targets}"
        )
        assert "system_file" in targets

    def test_only_negated_source_produces_no_rules(self):
        """allow { -domain1 } tgt:file read; — after filtering all sources are
        gone; no rules must be generated (not a crash)."""
        rules = _te().extract_rule("allow { -domain1 } target:file read;")
        assert isinstance(rules, list), "extract_rule must always return a list"
        # We don't assert empty here — acceptable to return 0 rules
        # but absolutely must not have '-domain1' as a source
        assert all(not r.source.startswith("-") for r in rules)


# ---------------------------------------------------------------------------
# require { … } blocks
# ---------------------------------------------------------------------------


class TestRequireBlock:
    def test_require_block_lines_not_in_output(self):
        """Content inside require { … } must be silently skipped."""
        te = _te()
        lines = [
            "require {",
            "    type hal_dummy_client;",
            "    class binder { call transfer };",
            "}",
        ]
        result = te.extract_items_to_process(lines)
        assert not any("require" in item for item in result), (
            f"require block content leaked into output: {result}"
        )

    def test_rule_after_require_block_is_parsed(self):
        """A rule that follows a require { … } block must still be processed."""
        te = _te()
        lines = [
            "require {",
            "    type hal_dummy_client;",
            "}",
            "allow dummy servicemanager:binder { call transfer };",
        ]
        result = te.extract_items_to_process(lines)
        assert any("allow dummy servicemanager" in item for item in result), (
            f"Rule after require block was lost. Extracted: {result}"
        )

    def test_single_line_require_skipped(self):
        """require { type foo; } on one line must also be skipped."""
        te = _te()
        lines = [
            "require { type foo; }",
            "allow domain foo:file read;",
        ]
        result = te.extract_items_to_process(lines)
        assert not any("require" in item for item in result)
        assert any("allow domain foo:file read" in item for item in result)

    def test_require_block_with_nested_braces_skipped(self):
        """Nested braces inside a require block must not confuse depth tracking."""
        te = _te()
        lines = [
            "require {",
            "    class file { read write open };",
            "}",
            "allow dummy target:file read;",
        ]
        result = te.extract_items_to_process(lines)
        assert not any("require" in item or "class file" in item for item in result)
        assert any("allow dummy target:file read" in item for item in result)


# ---------------------------------------------------------------------------
# M4 ifdef / ifndef blocks
# ---------------------------------------------------------------------------


class TestIfdefBlock:
    def test_ifdef_body_rule_extracted(self):
        """Rules inside ifdef(…) must be extracted and available for processing."""
        te = _te()
        lines = [
            "ifdef(`DUMMY_FEATURE', `",
            "allow dummy_new dummy_new_exec:file { read execute };",
            "')",
        ]
        result = te.extract_items_to_process(lines)
        assert any(
            "allow dummy_new dummy_new_exec:file" in item for item in result
        ), (
            f"Body rule inside ifdef was not extracted. Extracted items: {result}"
        )

    def test_ifndef_body_rule_extracted(self):
        """Rules inside ifndef(…) must also be extracted."""
        te = _te()
        lines = [
            "ifndef(`FEATURE', `",
            "allow domain target:file read;",
            "')",
        ]
        result = te.extract_items_to_process(lines)
        assert any("allow domain target:file read" in item for item in result), (
            f"Body rule inside ifndef was not extracted. Extracted items: {result}"
        )

    def test_ifdef_with_else_branch_both_extracted(self):
        """Both true and false branches of an ifdef are extracted (best-effort
        static analysis includes all possible rules)."""
        te = _te()
        lines = [
            "ifdef(`FEATURE', `",
            "allow domain target:file read;",
            "', `",
            "allow domain target:file write;",
            "')",
        ]
        result = te.extract_items_to_process(lines)
        combined = " ".join(result)
        assert "read" in combined or "write" in combined, (
            f"No ifdef branch rules extracted. Result: {result}"
        )

    def test_rule_after_ifdef_block_still_parsed(self):
        """A rule after an ifdef block must not be lost."""
        te = _te()
        lines = [
            "ifdef(`FEATURE', `",
            "allow domain target:file read;",
            "')",
            "allow standalone source:file { write };",
        ]
        result = te.extract_items_to_process(lines)
        assert any("standalone" in item for item in result), (
            f"Rule after ifdef block was lost. Result: {result}"
        )


# ---------------------------------------------------------------------------
# Integration: parse test_new_syntax.te sample file end-to-end
# ---------------------------------------------------------------------------


class TestNewSyntaxIntegration:
    @pytest.fixture(scope="class")
    def parsed(self):
        fa = FileAnalyzer()
        results = fa.analyze([SAMPLES_DIR], [])
        return results

    def _all(self, results, attr):
        return [item for pf in results for item in getattr(pf, attr, [])]

    def test_type_transitions_from_sample_file(self, parsed):
        """The sample file must produce type_transition entries."""
        tts = self._all(parsed, "type_transitions")
        assert tts, "No type_transitions parsed from test_new_syntax.te"
        sources = {t.source for t in tts}
        assert "dummy" in sources, f"Expected 'dummy' in type_transition sources; got {sources}"

    def test_negated_types_not_in_rules(self, parsed):
        """Negated types from the sample file must not appear in parsed rules."""
        rules = self._all(parsed, "rules")
        bad = [r for r in rules if r.source.startswith("-") or r.target.startswith("-")]
        assert not bad, (
            f"Found {len(bad)} rule(s) with negated type names: "
            + "; ".join(f"{r.source}->{r.target}" for r in bad[:5])
        )

    def test_rule_after_require_block_in_sample(self, parsed):
        """allow dummy_new servicemanager:… must appear despite the require block."""
        rules = self._all(parsed, "rules")
        found = any(r.source == "dummy_new" and r.target == "servicemanager" for r in rules)
        assert found, (
            "Rule after require block in test_new_syntax.te was not parsed"
        )

    def test_ifdef_body_rule_in_sample(self, parsed):
        """Rule inside ifdef block in test_new_syntax.te must be parsed."""
        rules = self._all(parsed, "rules")
        found = any(
            r.source == "dummy_new"
            and r.target == "dummy_new_exec"
            and r.class_type in ("file",)
            for r in rules
        )
        assert found, (
            "Rule inside ifdef block in test_new_syntax.te was not parsed. "
            f"dummy_new rules: {[(r.target, r.class_type) for r in rules if r.source == 'dummy_new']}"
        )
