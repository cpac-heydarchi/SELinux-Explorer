"""Tests for FileAnalyzer.detect_lang.

The previous implementation only returned UNDEFINED for unmatched files
because UNDEFINED's empty label made ``endswith("")`` match everything —
reordering the enum would silently misclassify files. These tests pin the
intended behavior of the explicit implementation.
"""

import pytest

from analyzer.FileAnalyzer import FileAnalyzer
from model.PolicyEntities import FileTypeEnum


@pytest.fixture
def analyzer():
    return FileAnalyzer()


@pytest.mark.parametrize(
    "file_name,expected",
    [
        ("init.te", FileTypeEnum.TE_FILE),
        ("/some/dir/vendor_app.te", FileTypeEnum.TE_FILE),
        ("init_te", FileTypeEnum.TE_FILE_2),
        ("te_init", FileTypeEnum.TE_FILE_3),
        ("file_contexts", FileTypeEnum.FILE_CONTEXTS),
        ("seapp_contexts", FileTypeEnum.SEAPP_CONTEXTS),
        ("property_contexts", FileTypeEnum.PROPERTY_CONTEXTS),
        ("vndservice_contexts", FileTypeEnum.VNDSERVICE_CONTEXTS),
    ],
)
def test_known_file_types(analyzer, file_name, expected):
    assert analyzer.detect_lang(file_name) == expected


@pytest.mark.parametrize(
    "file_name",
    ["README.md", "Makefile", "policy.cil", "notes.txt", "plantuml.jar"],
)
def test_unknown_files_are_undefined(analyzer, file_name):
    assert analyzer.detect_lang(file_name) == FileTypeEnum.UNDEFINED


def test_undefined_files_are_skipped_by_invoke(analyzer):
    assert analyzer.invoke_analyzer_class(FileTypeEnum.UNDEFINED, "whatever") is None
