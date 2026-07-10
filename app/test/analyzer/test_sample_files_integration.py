"""
Integration tests: run FileAnalyzer over the full samples directory and assert
that the parser produces correct data for the rules added to cover the
parsing-correctness bugs.

Covered scenarios
-----------------
1. Multi-class rule  ``allow src tgt:{cls1 cls2} perms;``
   – class_type must contain actual class names, never the internal "###" token.
2. Multi-source + multi-class  ``allow {s1 s2} tgt:{c1 c2} perm;``
   – both expansions must be applied simultaneously.
3. neverallow with multi-class  ``neverallow src tgt:{c1 c2} perm;``
   – same fix path as allow rules.
4. seapp_contexts with multiple consecutive spaces between key=value fields
   – all fields must be stored in the correct attribute.
5. file_contexts: extra path entries are parsed and stored.
"""

import os
import pytest
from analyzer.FileAnalyzer import FileAnalyzer
from model.PolicyEntities import RuleEnum

SAMPLES_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "samples")
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_all(results, attr):
    """Flatten a list attribute from every PolicyFile in results."""
    return [item for pf in results for item in getattr(pf, attr, [])]


@pytest.fixture(scope="module")
def parsed():
    """Parse the whole samples directory once; share across all tests."""
    fa = FileAnalyzer()
    result = fa.analyze([SAMPLES_DIR], [])
    assert result, "FileAnalyzer returned no PolicyFiles for the samples directory"
    return result


# ---------------------------------------------------------------------------
# 1 & 2 & 3 – multi-class rule parsing (the ###-placeholder bug)
# ---------------------------------------------------------------------------

class TestMultiClassRules:
    def test_multiclass_allow_produces_correct_class_types(self, parsed):
        """dummy.te: allow dummy dummy_exec:{file lnk_file} {read getattr open execute};
        must create two rules whose class_type is 'file' and 'lnk_file', not '###'."""
        rules = _get_all(parsed, "rules")
        target_rules = [
            r for r in rules
            if r.source == "dummy" and r.target == "dummy_exec"
        ]
        assert target_rules, (
            "No rules found with source='dummy', target='dummy_exec'. "
            "Check that dummy.te was parsed."
        )
        class_types = {r.class_type for r in target_rules}
        assert "###" not in class_types, (
            f"Internal placeholder '###' leaked into class_type. "
            f"Multi-class rule parsing is still broken. Got: {class_types}"
        )
        assert "file" in class_types, (
            f"Expected class_type 'file' in multi-class rule; got {class_types}"
        )
        assert "lnk_file" in class_types, (
            f"Expected class_type 'lnk_file' in multi-class rule; got {class_types}"
        )

    def test_multiclass_allow_three_classes(self, parsed):
        """dummy.te: allow dummy dummy_exec:{file lnk_file chr_file} getattr;
        must produce three rules, one per class."""
        rules = _get_all(parsed, "rules")
        getattr_rules = [
            r for r in rules
            if r.source == "dummy"
            and r.target == "dummy_exec"
            and "getattr" in r.permissions
        ]
        class_types = {r.class_type for r in getattr_rules}
        assert "###" not in class_types, (
            f"Placeholder '###' in class_type for three-class rule: {class_types}"
        )
        assert {"file", "lnk_file", "chr_file"}.issubset(class_types), (
            f"Expected all of {{file, lnk_file, chr_file}} in class_types; got {class_types}"
        )

    def test_multisource_multiclass_allow(self, parsed):
        """hal_dummy.te: allow {system_app priv_app} hal_dummy_hwservice:{hwservice_manager service_manager} find;
        must produce 4 rules (2 sources × 2 classes), all with correct fields."""
        rules = _get_all(parsed, "rules")
        combo_rules = [
            r for r in rules
            if r.source in {"system_app", "priv_app"}
            and r.target == "hal_dummy_hwservice"
            and "find" in r.permissions
        ]
        assert combo_rules, (
            "No rules found for multi-source+multi-class rule in hal_dummy.te"
        )
        class_types = {r.class_type for r in combo_rules}
        sources = {r.source for r in combo_rules}
        assert "###" not in class_types, (
            f"Placeholder '###' in class_type for multi-source+multi-class rule: {class_types}"
        )
        assert "hwservice_manager" in class_types, (
            f"class_type 'hwservice_manager' missing; got {class_types}"
        )
        assert "service_manager" in class_types, (
            f"class_type 'service_manager' missing; got {class_types}"
        )
        assert "system_app" in sources and "priv_app" in sources, (
            f"Not all sources present; got {sources}"
        )

    def test_multiclass_neverallow_no_placeholder(self, parsed):
        """dummy.te: neverallow dummy dummy_exec:{file dir} write;
        must produce two rules, none with class_type='###'."""
        rules = _get_all(parsed, "rules")
        neverallow_rules = [
            r for r in rules
            if str(r.rule) in (str(RuleEnum.NEVER_ALLOW), "neverallow", "RuleEnum.NEVER_ALLOW")
            and r.source == "dummy"
            and r.target == "dummy_exec"
        ]
        assert neverallow_rules, (
            "No neverallow rules found for dummy→dummy_exec in dummy.te"
        )
        class_types = {r.class_type for r in neverallow_rules}
        assert "###" not in class_types, (
            f"Placeholder '###' in neverallow rule class_type: {class_types}"
        )
        assert {"file", "dir"}.issubset(class_types), (
            f"Expected {{file, dir}} in neverallow class_types; got {class_types}"
        )

    def test_no_hash_placeholder_anywhere(self, parsed):
        """Regression: no rule in any sample file should have class_type='###'."""
        rules = _get_all(parsed, "rules")
        bad = [r for r in rules if r.class_type == "###"]
        assert not bad, (
            f"Found {len(bad)} rule(s) with class_type='###' (internal placeholder leaked): "
            + "; ".join(f"{r.source}->{r.target}:{r.class_type}" for r in bad[:5])
        )


# ---------------------------------------------------------------------------
# 4 – seapp_contexts with multiple consecutive spaces
# ---------------------------------------------------------------------------

class TestSeappMultipleSpaces:
    def test_multispace_entry_all_fields_correct(self, parsed):
        """seapp_contexts: the entry with double spaces between key=value pairs
        must have all fields correctly stored, not run together."""
        se_apps = _get_all(parsed, "se_apps")
        entry = next(
            (a for a in se_apps if a.name == "com.example.dummy"), None
        )
        assert entry is not None, (
            "seapp entry with name='com.example.dummy' not found. "
            "Check that the multi-space entry in seapp_contexts was parsed."
        )
        assert entry.user == "_app", (
            f"user should be '_app', got '{entry.user}'. "
            "Likely caused by tab/multi-space tokenisation bug."
        )
        assert entry.seinfo == "platform", (
            f"seinfo should be 'platform', got '{entry.seinfo}'"
        )
        assert entry.domain == "dummy_client", (
            f"domain should be 'dummy_client', got '{entry.domain}'"
        )
        assert entry.type == "app_data_file", (
            f"type should be 'app_data_file', got '{entry.type}'"
        )

    def test_original_seapp_entry_still_parsed(self, parsed):
        """The original seapp_contexts entry must not be broken by the new addition."""
        se_apps = _get_all(parsed, "se_apps")
        entry = next(
            (a for a in se_apps if a.name == "com.aospinsight.dummyaidlapp"), None
        )
        assert entry is not None, (
            "Original seapp entry 'com.aospinsight.dummyaidlapp' not found"
        )
        assert entry.domain == "dummyapp_service"
        assert entry.seinfo == "platform"


# ---------------------------------------------------------------------------
# 5 – file_contexts: additional path entries
# ---------------------------------------------------------------------------

class TestFileContexts:
    def test_additional_file_contexts_parsed(self, parsed):
        """The three new entries added to file_contexts must all be present."""
        contexts = _get_all(parsed, "contexts")
        path_names = {c.path_name for c in contexts}

        expected = {
            "/vendor/bin/hw/dummy-service",
            "/data/misc/dummy",
            r"/vendor/lib/hw/dummy\.so",
            "/dev/dummy",
        }
        for path in expected:
            assert path in path_names, (
                f"Expected file_contexts entry '{path}' not found in parsed contexts. "
                f"Found paths: {sorted(path_names)}"
            )

    def test_file_context_security_context_parsed(self, parsed):
        """The original entry must have its security context fields set."""
        contexts = _get_all(parsed, "contexts")
        entry = next(
            (c for c in contexts if c.path_name == "/vendor/bin/hw/dummy-service"),
            None,
        )
        assert entry is not None
        assert entry.security_context is not None
        assert entry.security_context.user == "u"
        assert entry.security_context.role == "object_r"
        assert entry.security_context.type == "dummy_exec"
        assert entry.security_context.level == "s0"
