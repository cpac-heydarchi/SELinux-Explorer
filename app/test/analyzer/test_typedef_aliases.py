"""Tests that TypeDef.aliases is populated from typealias statements."""

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


def test_alias_attached_to_matching_type_def():
    policy = analyze_content(
        "type app_data_file, file_type;\n"
        "typealias app_data_file alias download_file;\n"
    )
    type_def = next(t for t in policy.type_def if t.name == "app_data_file")
    assert type_def.aliases == ["download_file"]
    # the standalone TypeAlias entry is still stored as before
    assert len(policy.type_aliases) == 1


def test_alias_without_matching_type_def_is_kept_standalone():
    policy = analyze_content("typealias foreign_type alias other_name;\n")
    assert len(policy.type_aliases) == 1
    assert all(t.aliases == [] for t in policy.type_def)
