import pytest
from model.PolicyEntities import (
    Rule,
    PolicyMacro,
    PolicyMacroCall,
    RuleEnum,
    PolicyFile,
)
from logic.AnalyzerLogic import AnalyzerLogic


def test_convert_macrocall_to_rule_replaces_all_indices():
    logic = AnalyzerLogic()
    # Macro define: allow $1 $2:$3 { read write }
    macro = PolicyMacro()
    macro.name = "allow3"
    r = Rule()
    r.rule = RuleEnum.ALLOW
    r.source = "$1"
    r.target = "$2"
    r.class_type = "$3"
    r.permissions = ["read", "write"]
    macro.rules.append(r)

    call = PolicyMacroCall()
    call.name = "allow3"
    call.parameters = ["s1", "t1", "file"]

    out = logic.convert_macrocall_to_rule([call], [macro])
    assert len(out) == 1
    rr = out[0]
    assert rr.source == "s1"
    assert rr.target == "t1"
    assert rr.class_type == "file"
    assert rr.permissions == ["read", "write"]
