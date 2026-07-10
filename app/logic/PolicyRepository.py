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
        if policy is None:
            return PolicyFile()
        # Unique by keys
        policy.type_def = list({item.name: item for item in policy.type_def}.values())
        policy.attribute = list({item.name: item for item in policy.attribute}.values())
        policy.contexts = list(
            {item.path_name: item for item in policy.contexts}.values()
        )
        policy.se_apps = list({item.name: item for item in policy.se_apps}.values())

        def rule_key(r: Rule):
            return (
                r.rule,
                r.source,
                r.target,
                r.class_type,
                tuple(sorted(r.permissions)),
            )

        policy.rules = list({rule_key(r): r for r in policy.rules}.values())
        return policy
