"""Regression tests for FilterResult filtering.

A filename-truncation change once moved the per-rule dispatch chain out of
the ``for filter_rule`` loop and into the truncation ``if`` block, so
filtering silently returned an empty result for every normal-length
filter.  These tests make sure every filter rule in the list is applied.

``apply_filters`` is the pure filtering step (no files written, nothing
drawn); ``filter`` additionally renders diagrams, so it is tested once
with the drawers stubbed out.
"""

import logic.FilterResult as filter_result_module
from logic.FilterResult import FilterResult, FilterRule, FilterType
from model.PolicyEntities import PolicyFile, Rule, TypeDef


def make_policy_file():
    policy_file = PolicyFile()
    policy_file.type_def.append(TypeDef(name="init"))
    policy_file.type_def.append(TypeDef(name="vendor_app"))
    policy_file.rules.append(
        Rule(
            rule="allow",
            source="init",
            target="init_exec",
            class_type="file",
            permissions=["read", "execute"],
        )
    )
    policy_file.rules.append(
        Rule(
            rule="allow",
            source="vendor_app",
            target="vendor_data_file",
            class_type="file",
            permissions=["write"],
        )
    )
    return policy_file


def test_domain_filter_returns_matches():
    fr = FilterResult()
    filtered = fr.apply_filters(
        [FilterRule(FilterType.DOMAIN, "init", True)], make_policy_file()
    )
    assert [t.name for t in filtered.type_def] == ["init"]
    assert len(filtered.rules) == 1
    assert filtered.rules[0].source == "init"


def test_permission_filter_returns_matches():
    fr = FilterResult()
    filtered = fr.apply_filters(
        [FilterRule(FilterType.PERMISSION, "write", True)], make_policy_file()
    )
    assert len(filtered.rules) == 1
    assert filtered.rules[0].source == "vendor_app"
    assert filtered.rules[0].permissions == ["write"]


def test_every_rule_in_list_is_applied():
    """All filter rules must be dispatched, not just the last one."""
    fr = FilterResult()
    filtered = fr.apply_filters(
        [
            FilterRule(FilterType.DOMAIN, "init", True),
            FilterRule(FilterType.DOMAIN, "vendor_app", True),
        ],
        make_policy_file(),
    )
    assert sorted(t.name for t in filtered.type_def) == ["init", "vendor_app"]
    assert len(filtered.rules) == 2


def test_long_filename_is_truncated_and_still_filters():
    fr = FilterResult()
    long_keyword = "init" + "x" * 300
    policy_file = make_policy_file()
    policy_file.type_def.append(TypeDef(name=long_keyword))
    filtered = fr.apply_filters(
        [FilterRule(FilterType.DOMAIN, long_keyword, True)], policy_file
    )
    assert len(filtered.file_name) <= FilterResult._MAX_FILENAME_LEN
    assert [t.name for t in filtered.type_def] == [long_keyword]


def test_filter_applies_rules_and_renders(monkeypatch):
    """filter() must return the filtered result and invoke the renderer."""
    rendered = []
    monkeypatch.setattr(
        FilterResult, "render", lambda self, policy_file: rendered.append(policy_file)
    )
    fr = FilterResult()
    diagram_name, filtered = fr.filter(
        [FilterRule(FilterType.DOMAIN, "init", True)], make_policy_file()
    )
    assert rendered == [filtered]
    assert filtered.file_name in diagram_name
    assert [t.name for t in filtered.type_def] == ["init"]
