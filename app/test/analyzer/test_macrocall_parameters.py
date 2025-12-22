from analyzer.TeAnalyzer import TeAnalyzer
from model.PolicyEntities import PolicyMacroCall


def test_te_analyzer_extract_macro_call_parameters():
    t = TeAnalyzer()
    # Set minimal context
    t.policy_file = type("pf", (), {"where_is_it": "file.te"})()
    call = t.extract_macro_call("allow3(s1, t1, file);")
    assert isinstance(call, PolicyMacroCall)
    assert call.name == "allow3"
    assert call.parameters == ["s1", "t1", "file"]
