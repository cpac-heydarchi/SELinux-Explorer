from model.PolicyEntities import (
    PolicyFile,
    PolicyMacro,
    PolicyMacroCall,
    Rule,
    RuleEnum,
    TypeDef,
)
from logic.PolicyRepository import PolicyRepository


def _pf(types=None, rules=None, macros=None, calls=None):
    pf = PolicyFile()
    if types:
        pf.type_def.extend(types)
    if rules:
        pf.rules.extend(rules)
    if macros:
        pf.macros.extend(macros)
    if calls:
        pf.macro_calls.extend(calls)
    return pf


def test_merge_combines_fields():
    repo = PolicyRepository()
    a = _pf(types=[TypeDef(name="a")])
    b = _pf(types=[TypeDef(name="b")])
    out = repo.merge([a, b])
    assert {t.name for t in out.type_def} == {"a", "b"}


def test_expand_macros_creates_rules():
    repo = PolicyRepository()
    m = PolicyMacro()
    m.name = "allow3"
    r = Rule(
        rule=RuleEnum.ALLOW,
        source="$1",
        target="$2",
        class_type="$3",
        permissions=["read"],
    )
    m.rules.append(r)

    call = PolicyMacroCall(name="allow3", parameters=["s", "t", "file"])
    pf = _pf(macros=[m], calls=[call])

    out = repo.expand_macros(pf)
    assert any(
        rr.source == "s" and rr.target == "t" and rr.class_type == "file"
        for rr in out.rules
    )


def test_dedup_removes_duplicates():
    repo = PolicyRepository()
    t1 = TypeDef(name="a")
    t2 = TypeDef(name="a")
    dup_rule = Rule(
        rule=RuleEnum.ALLOW,
        source="s",
        target="t",
        class_type="c",
        permissions=["x", "y"],
    )
    pf = _pf(types=[t1, t2], rules=[dup_rule, dup_rule])

    out = repo.dedup(pf)
    assert len(out.type_def) == 1
    assert len(out.rules) == 1
