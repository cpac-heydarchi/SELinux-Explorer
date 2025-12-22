from analyzer.ContextsAnalyzer import ContextsAnalyzer
from model.PolicyEntities import Context


def test_contexts_parser_bounds():
    a = ContextsAnalyzer()
    # Simulate file name selection
    a.policy_file = type("pf", (), {"where_is_it": "file_contexts"})()

    # Minimal entries
    c = a.extract_definition("/dev/null u:object_r:null_device:s0")
    assert isinstance(c, Context)
    assert c.security_context.user == "u"
    assert c.security_context.role == "object_r"
    assert c.security_context.type == "null_device"
    assert c.security_context.level == "s0"

    # Missing level/categories
    c2 = a.extract_definition("/path something:something_else:typeonly")
    assert c2.security_context.type == "typeonly"
