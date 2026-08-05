from typing import List
from model.PolicyEntities import PolicyFile, Rule, PolicyMacro, PolicyMacroCall


class PolicyRepository:
    """Centralized operations on PolicyFile graphs: merge, macro expansion, and deduplication."""

    def merge(self, files: List[PolicyFile]) -> PolicyFile:
        if not files:
            return PolicyFile()
        out = PolicyFile()
        for pf in files:
            if pf is None:
                continue
            out.type_def.extend(pf.type_def)
            out.attribute.extend(pf.attribute)
            out.contexts.extend(pf.contexts)
            out.se_apps.extend(pf.se_apps)
            out.rules.extend(pf.rules)
            out.macros.extend(pf.macros)
            out.macro_calls.extend(pf.macro_calls)
            out.permissives.extend(pf.permissives)
            out.type_aliases.extend(pf.type_aliases)
            out.type_transitions.extend(pf.type_transitions)
        return out

    def expand_macros(self, policy: PolicyFile) -> PolicyFile:
        if policy is None:
            return PolicyFile()
        # Convert macro calls to rules and append
        new_rules = self._macro_calls_to_rules(policy.macro_calls, policy.macros)
        policy.rules.extend(new_rules)
        return policy

    def _macro_calls_to_rules(
        self, macro_calls: List[PolicyMacroCall], macros: List[PolicyMacro]
    ) -> List[Rule]:
        lst_rules: List[Rule] = []
        for macro_call in macro_calls:
            for macro in macros:
                if macro.name != macro_call.name:
                    continue
                for rule in macro.rules:
                    new_rule = Rule(
                        rule=rule.rule,
                        source=rule.source,
                        target=rule.target,
                        class_type=rule.class_type,
                        permissions=rule.permissions,
                    )
                    for i in range(0, len(macro_call.parameters)):
                        new_rule.source = new_rule.source.replace(
                            "$" + str(i + 1), macro_call.parameters[i]
                        )
                        new_rule.target = new_rule.target.replace(
                            "$" + str(i + 1), macro_call.parameters[i]
                        )
                        new_rule.class_type = new_rule.class_type.replace(
                            "$" + str(i + 1), macro_call.parameters[i]
                        )
                    lst_rules.append(new_rule)
                break
        return lst_rules

    def dedup(self, policy: PolicyFile) -> PolicyFile:
        """Remove exact duplicates from every PolicyFile collection.

        Keys are content-based so two distinct entries that merely share a
        name (e.g. seapp_contexts lines without a ``name=`` selector, or two
        ``typeattribute`` lines for the same type) are both kept.
        """
        if policy is None:
            return PolicyFile()

        def unique(items, key):
            return list({key(item): item for item in items}.values())

        policy.type_def = unique(policy.type_def, lambda t: (t.name, tuple(t.types)))
        policy.attribute = unique(
            policy.attribute, lambda a: (a.name, tuple(a.attributes))
        )
        policy.contexts = unique(
            policy.contexts,
            lambda c: (
                c.path_name,
                c.file_type,
                c.security_context.type if c.security_context else "",
            ),
        )
        policy.se_apps = unique(
            policy.se_apps,
            lambda s: (s.name, s.user, s.seinfo, s.domain, s.type, s.level_from),
        )
        policy.rules = unique(
            policy.rules,
            lambda r: (
                r.rule,
                r.source,
                r.target,
                r.class_type,
                tuple(sorted(r.permissions)),
            ),
        )
        policy.macros = unique(policy.macros, lambda m: (m.name, tuple(m.rules_string)))
        policy.macro_calls = unique(
            policy.macro_calls, lambda m: (m.name, tuple(m.parameters))
        )
        policy.permissives = unique(policy.permissives, lambda p: p.name)
        policy.type_aliases = unique(policy.type_aliases, lambda t: (t.name, t.alias))
        policy.type_transitions = unique(
            policy.type_transitions,
            lambda t: (
                t.rule_type,
                t.source,
                t.target,
                t.class_type,
                t.default_type,
                t.object_name,
            ),
        )
        return policy
