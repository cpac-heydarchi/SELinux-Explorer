from model.PolicyEntities import (
    Permissive,
    PolicyFile,
    PolicyMacro,
    PolicyMacroCall,
    Rule,
    RuleEnum,
    SeAppContext,
    TypeAlias,
    TypeDef,
    TypeTransition,
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


def test_dedup_covers_all_collections():
    repo = PolicyRepository()
    pf = PolicyFile()
    macro = PolicyMacro(name="m1", rules_string=["allow a b:c d;"])
    pf.macros.extend([macro, PolicyMacro(name="m1", rules_string=["allow a b:c d;"])])
    call = PolicyMacroCall(name="m1", parameters=["a", "b"])
    pf.macro_calls.extend([call, PolicyMacroCall(name="m1", parameters=["a", "b"])])
    pf.permissives.extend([Permissive(name="p1"), Permissive(name="p1")])
    pf.type_aliases.extend(
        [TypeAlias(name="t", alias="u"), TypeAlias(name="t", alias="u")]
    )
    tt = TypeTransition(
        rule_type="type_transition",
        source="s",
        target="t",
        class_type="file",
        default_type="d",
    )
    pf.type_transitions.extend(
        [
            tt,
            TypeTransition(
                rule_type="type_transition",
                source="s",
                target="t",
                class_type="file",
                default_type="d",
            ),
        ]
    )

    out = repo.dedup(pf)
    assert len(out.macros) == 1
    assert len(out.macro_calls) == 1
    assert len(out.permissives) == 1
    assert len(out.type_aliases) == 1
    assert len(out.type_transitions) == 1


def test_dedup_keeps_distinct_entries_sharing_a_name():
    """Content-based keys: same name but different content must survive."""
    repo = PolicyRepository()
    pf = PolicyFile()
    # Two seapp_contexts entries without a name= selector (name defaults "")
    pf.se_apps.extend(
        [
            SeAppContext(user="system", domain="system_app"),
            SeAppContext(user="_app", domain="untrusted_app"),
        ]
    )
    # Two macro calls with the same macro name but different parameters
    pf.macro_calls.extend(
        [
            PolicyMacroCall(name="m1", parameters=["a"]),
            PolicyMacroCall(name="m1", parameters=["b"]),
        ]
    )

    out = repo.dedup(pf)
    assert len(out.se_apps) == 2
    assert len(out.macro_calls) == 2
