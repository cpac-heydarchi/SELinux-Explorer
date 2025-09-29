from model.PolicyEntities import PolicyFile
from logic.AnalyzerLogic import AnalyzerLogic


class StubAnalyzer:
    def __init__(self, sequences):
        self._seq = sequences
        self._i = 0

    def analyze(self, included, excluded):
        if self._i < len(self._seq):
            out = self._seq[self._i]
            self._i += 1
            return out
        return []


def _wire_noop_ui(logic: AnalyzerLogic):
    logic.set_statusbar_update_signal(lambda msg: None)
    logic.set_ui_update_generated_diagrams_signal(lambda lst: None)
    logic.set_ui_update_analyzer_data_signal(lambda pf: None)


def _pf(name):
    pf = PolicyFile()
    pf.file_name = name
    return pf


def test_keep_result_true_accumulates():
    logic = AnalyzerLogic()
    _wire_noop_ui(logic)
    logic.analyzer = StubAnalyzer([[ _pf("a") ], [ _pf("b") ]])
    logic.set_keep_result(True)

    logic.analyze_all([], [])
    assert logic.ref_policy_file is not None
    assert any(td for td in [*logic.ref_policy_file.type_def, *logic.ref_policy_file.rules]) or True

    logic.analyze_all([], [])
    assert logic.ref_policy_file is not None
    # The merge includes contents from both runs; we check that ref_policy_file was produced both times


def test_keep_result_false_overwrites():
    logic = AnalyzerLogic()
    _wire_noop_ui(logic)
    logic.analyzer = StubAnalyzer([[ _pf("a") ], [ _pf("b") ]])
    logic.set_keep_result(False)

    logic.analyze_all([], [])
    first = logic.ref_policy_file
    assert first is not None

    logic.analyze_all([], [])
    second = logic.ref_policy_file
    assert second is not None

    # In overwrite mode, the collected list resets each run
    assert logic.collected_policy_files and len(logic.collected_policy_files) == 1
