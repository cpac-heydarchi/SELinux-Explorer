"""Integration tests for the AnalyzerLogic analyze pipeline.

Runs analyze_all over the real sample files (parse -> merge -> macro
expansion -> dedup) without any UI wired up, relying on the default
no-op signal callbacks.
"""

import os

from logic.AnalyzerLogic import AnalyzerLogic

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "samples")


def test_usable_without_ui_signals():
    """AnalyzerLogic must not raise AttributeError without set_*_signal calls."""
    logic = AnalyzerLogic()
    logic.analyze_all([], [])  # nothing to analyze; must not raise
    assert logic.ref_policy_file is None


def test_analyze_all_over_samples_produces_merged_policy():
    logic = AnalyzerLogic()
    logic.analyze_all([SAMPLES_DIR], [])

    ref = logic.ref_policy_file
    assert ref is not None
    assert len(ref.type_def) > 0
    assert len(ref.rules) > 0
    assert len(ref.contexts) > 0
    assert len(ref.se_apps) > 0

    # dedup ran: no two rules share the same content key
    keys = [
        (r.rule, r.source, r.target, r.class_type, tuple(sorted(r.permissions)))
        for r in ref.rules
    ]
    assert len(keys) == len(set(keys))


def test_excluded_paths_are_respected():
    logic = AnalyzerLogic()
    logic.analyze_all([SAMPLES_DIR], [SAMPLES_DIR])
    assert logic.ref_policy_file is None
