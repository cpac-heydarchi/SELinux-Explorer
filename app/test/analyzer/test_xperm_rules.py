"""Tests for allowxperm-family rule parsing.

These rules were previously listed in NotSupportedRuleEnum and silently
dropped; they are now stored in PolicyFile.xperm_rules.
"""

import os
import tempfile

import pytest

from analyzer.TeAnalyzer import TeAnalyzer


def analyze_content(content):
    with tempfile.NamedTemporaryFile("w", suffix=".te", delete=False) as tmp_file:
        tmp_file.write(content)
        path = tmp_file.name
    try:
        return TeAnalyzer().analyze(path)
    finally:
        os.remove(path)


def test_allowxperm_with_named_set():
    policy = analyze_content(
        "allowxperm domain domain:udp_socket ioctl priv_sock_ioctls;\n"
    )
    assert len(policy.xperm_rules) == 1
    xperm = policy.xperm_rules[0]
    assert xperm.rule == "allowxperm"
    assert xperm.source == "domain"
    assert xperm.target == "domain"
    assert xperm.class_type == "udp_socket"
    assert xperm.operation == "ioctl"
    assert xperm.permissions == ["priv_sock_ioctls"]


def test_allowxperm_with_brace_group():
    policy = analyze_content(
        "allowxperm hal_dummy dev_type:chr_file ioctl { 0x8910 0x8926-0x8927 };\n"
    )
    assert len(policy.xperm_rules) == 1
    xperm = policy.xperm_rules[0]
    assert xperm.permissions == ["0x8910", "0x8926-0x8927"]


@pytest.mark.parametrize(
    "rule_keyword",
    ["allowxperm", "auditallowxperm", "dontauditxperm", "neverallowxperm"],
)
def test_all_xperm_variants_are_stored(rule_keyword):
    policy = analyze_content(f"{rule_keyword} a b:udp_socket ioctl 0x8910;\n")
    assert len(policy.xperm_rules) == 1
    assert policy.xperm_rules[0].rule == rule_keyword


def test_xperm_rule_does_not_pollute_regular_rules():
    policy = analyze_content(
        "allow a b:file read;\n" "allowxperm a b:udp_socket ioctl 0x8910;\n"
    )
    assert len(policy.rules) == 1
    assert policy.rules[0].rule == "allow"
    assert len(policy.xperm_rules) == 1
