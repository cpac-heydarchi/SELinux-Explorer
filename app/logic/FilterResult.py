from model.PolicyEntities import *
from drawer.RelationDrawer import *
from drawer.AdvanceDrawer import *
from dataclasses import dataclass
from dataclass_wizard import JSONWizard
from drawer.DrawerHelper import *
from logic.PolicyRepository import PolicyRepository


class FilterType(Enum):
    DOMAIN = 1
    CLASS_TYPE = 2
    PERMISSION = 3
    FILE_PATH = 4
    # ATTRIBUTE = 5
    # MACRO_CALL = 5
    MACRO_DEF = 5


@dataclass
class FilterRule(JSONWizard):
    filter_type: FilterType = FilterType.DOMAIN
    keyword: str = ""
    exact_word: bool = False

    def __eq__(self, other):
        return (
            isinstance(other, FilterRule)
            and self.filter_type == other.filter_type
            and self.keyword == other.keyword
            and self.exact_word == other.exact_word
        )

    def __hash__(self):
        return hash((self.filter_type, self.keyword, self.exact_word))

    @staticmethod
    def get_filter_type_from_str(keyword):
        for filter_type in FilterType:
            if keyword == filter_type.name:
                return filter_type


class FilterResult:
    # Maximum length for the base filename (without directory or extension).
    # Linux allows 255 bytes per component; we use 180 to leave headroom for
    # the "out/seq_" prefix, the ".puml" / ".png" suffix, and multibyte chars.
    _MAX_FILENAME_LEN = 180

    def filter(self, lst_rules, policy_file):
        """Apply the filter rules, then render the result as diagrams.

        Returns (diagram_file_path, filtered_policy_file).
        """
        filtered_policy_file = self.apply_filters(lst_rules, policy_file)
        self.render(filtered_policy_file)
        return (
            generate_diagram_file_name(filtered_policy_file.file_name),
            filtered_policy_file,
        )

    def apply_filters(self, lst_rules, policy_file):
        """Pure filtering step: no files are written, nothing is drawn."""
        filtered_policy_file = PolicyFile()
        filtered_policy_file.file_name = "domain_filtered"

        for filter_rule in lst_rules:
            filtered_policy_file.file_name = (
                filtered_policy_file.file_name
                + ("_ew_" if filter_rule.exact_word else "_")
                + filter_rule.keyword
            )

            if FilterType(filter_rule.filter_type) == FilterType.DOMAIN:
                filtered_policy_file = self.filter_domain(
                    filter_rule, policy_file, filtered_policy_file
                )
            elif FilterType(filter_rule.filter_type) == FilterType.PERMISSION:
                filtered_policy_file = self.filter_permission(
                    filter_rule, policy_file, filtered_policy_file
                )
            elif FilterType(filter_rule.filter_type) == FilterType.FILE_PATH:
                filtered_policy_file = self.filter_pathname(
                    filter_rule, policy_file, filtered_policy_file
                )
            elif FilterType(filter_rule.filter_type) == FilterType.CLASS_TYPE:
                filtered_policy_file = self.filter_classtype(
                    filter_rule, policy_file, filtered_policy_file
                )

            elif FilterType(filter_rule.filter_type) == FilterType.MACRO_DEF:
                filtered_policy_file = self.filter_macro_def(
                    filter_rule, policy_file, filtered_policy_file
                )

        # Truncate to stay within the OS filename-length limit
        if len(filtered_policy_file.file_name) > self._MAX_FILENAME_LEN:
            filtered_policy_file.file_name = (
                filtered_policy_file.file_name[: self._MAX_FILENAME_LEN - 3] + "___"
            )

        return self.remove_duplicated_Items(filtered_policy_file)

    def render(self, filtered_policy_file):
        """Rendering step: write .puml files and generate diagrams."""
        RelationDrawer().draw_uml(filtered_policy_file)
        AdvancedDrawer().draw_uml(filtered_policy_file)

    def remove_duplicated_Items(self, filtered_policy_file):
        """Remove duplicated items from filtered_policy_file.

        Delegates to PolicyRepository.dedup so there is a single
        deduplication implementation.
        """
        return PolicyRepository().dedup(filtered_policy_file)

    def filter_domain(self, filter_rule, policy_file, filtered_policy_file):
        filtered_policy_file.type_def.extend(
            self.filter_typedef(filter_rule, policy_file)
        )
        filtered_policy_file.contexts.extend(
            self.filter_context(filter_rule, policy_file)
        )
        filtered_policy_file.se_apps.extend(
            self.filter_se_app(filter_rule, policy_file)
        )
        filtered_policy_file.rules.extend(self.filter_rule(filter_rule, policy_file))
        filtered_policy_file.macros.extend(
            self.select_macro_def(filter_rule, policy_file)
        )
        filtered_policy_file.attribute.extend(
            self.filter_attribute(filter_rule, policy_file)
        )

        return filtered_policy_file

    def filter_filename(self, filter_rule, policy_file, filtered_policy_file):
        # print("----filter_filename")
        if self.check_similarity(filter_rule, policy_file.file_name):
            filtered_policy_file.type_def.extend(policy_file.type_def)
            filtered_policy_file.contexts.extend(policy_file.contexts)
            filtered_policy_file.se_apps.extend(policy_file.se_apps)
            filtered_policy_file.rules.extend(policy_file.rules)
            filtered_policy_file.macros.extend(policy_file.macros)
            filtered_policy_file.attribute.extend(policy_file.attribute)

        return filtered_policy_file

    def filter_permission(self, filter_rule, policy_file, filtered_policy_file):
        """Filter rules having permission in the policy_file and put them in filtered_policy_file"""
        # print("----filter_permission: ", filter_rule)
        for rule in policy_file.rules:
            if filter_rule.keyword in rule.permissions:
                # print(rule)
                import copy

                temp_rule = copy.copy(rule)
                temp_rule.permissions = [filter_rule.keyword]
                filtered_policy_file.rules.append(temp_rule)
                filtered_policy_file.type_def.extend(
                    self.filter_typedef(
                        FilterRule(FilterType.DOMAIN, rule.source, True), policy_file
                    )
                )
                filtered_policy_file.type_def.extend(
                    self.filter_typedef(
                        FilterRule(FilterType.DOMAIN, rule.target, True), policy_file
                    )
                )
                filtered_policy_file.contexts.extend(
                    self.filter_context(
                        FilterRule(FilterType.DOMAIN, rule.source, True), policy_file
                    )
                )
                filtered_policy_file.contexts.extend(
                    self.filter_context(
                        FilterRule(FilterType.DOMAIN, rule.target, True), policy_file
                    )
                )
                filtered_policy_file.se_apps.extend(
                    self.filter_se_app(
                        FilterRule(FilterType.DOMAIN, rule.source, True), policy_file
                    )
                )
                filtered_policy_file.se_apps.extend(
                    self.filter_se_app(
                        FilterRule(FilterType.DOMAIN, rule.target, True), policy_file
                    )
                )

        return filtered_policy_file

    def filter_pathname(self, filter_rule, policy_file, filtered_policy_file):
        """filter context having path_name or se_apps having name
        in policy_file and add to filtered_policy_file"""
        for context in policy_file.contexts:
            # print("context.path_name: ", context.path_name, filter_rule)
            if self.check_similarity(filter_rule, context.path_name):
                if context.security_context.type.strip().endswith("_exec"):
                    domain = context.security_context.type.strip().replace("_exec", "")
                else:
                    domain = context.security_context.type
                # print("context.security_context.type: ", context.security_context.type)
                filtered_policy_file.contexts.append(context)
                filtered_policy_file.type_def.extend(
                    self.filter_typedef(
                        FilterRule(FilterType.DOMAIN, domain, True), policy_file
                    )
                )
                filtered_policy_file.se_apps.extend(
                    self.filter_se_app(
                        FilterRule(FilterType.DOMAIN, domain, True), policy_file
                    )
                )
                filtered_policy_file.rules.extend(
                    self.filter_rule(
                        FilterRule(FilterType.DOMAIN, domain, True), policy_file
                    )
                )

        for se_app in policy_file.se_apps:
            # print("se_apps.name: ", se_app.name, filter_rule)
            if self.check_similarity(filter_rule, se_app.name):
                if se_app.domain.strip().endswith("_exec"):
                    domain = se_app.domain.strip().replace("_exec", "")
                else:
                    domain = se_app.domain.strip()
                # print("domain: ", domain)
                filtered_policy_file.se_apps.append(se_app)
                filtered_policy_file.type_def.extend(
                    self.filter_typedef(
                        FilterRule(FilterType.DOMAIN, domain, True), policy_file
                    )
                )
                filtered_policy_file.contexts.extend(
                    self.filter_context(
                        FilterRule(FilterType.DOMAIN, domain, True), policy_file
                    )
                )
                filtered_policy_file.rules.extend(
                    self.filter_rule(
                        FilterRule(FilterType.DOMAIN, domain, True), policy_file
                    )
                )

        return filtered_policy_file

    def filter_macro_def(self, filter_rule, policy_file, filtered_policy_file):
        """filter macro_def having name in policy_file and add to filtered_policy_file"""
        for macro in policy_file.macros:
            if self.check_similarity(filter_rule, macro.name):
                filtered_policy_file.macros.append(macro)

        return filtered_policy_file

    def filter_classtype(self, filter_rule, policy_file, filtered_policy_file):
        """find domain and rule with the same class type
        and then filter based on the found domain"""
        for type_def in policy_file.type_def:
            for type_ in type_def.types:
                if self.check_similarity(filter_rule, type_):
                    filtered_policy_file.type_def.append(type_def)
                    filtered_policy_file.rules.extend(
                        self.filter_rule(
                            FilterRule(FilterType.DOMAIN, type_def.name, True),
                            policy_file,
                        )
                    )
                    filtered_policy_file.contexts.extend(
                        self.filter_context(
                            FilterRule(FilterType.DOMAIN, type_def.name, True),
                            policy_file,
                        )
                    )
                    filtered_policy_file.se_apps.extend(
                        self.filter_se_app(
                            FilterRule(FilterType.DOMAIN, type_def.name, True),
                            policy_file,
                        )
                    )

        for rule in policy_file.rules:
            if self.check_similarity(filter_rule, rule.class_type):
                filtered_policy_file.rules.append(rule)
                filtered_policy_file.type_def.extend(
                    self.filter_typedef(
                        FilterRule(FilterType.DOMAIN, rule.source, True), policy_file
                    )
                )
                filtered_policy_file.type_def.extend(
                    self.filter_typedef(
                        FilterRule(FilterType.DOMAIN, rule.target, True), policy_file
                    )
                )
                filtered_policy_file.contexts.extend(
                    self.filter_context(
                        FilterRule(FilterType.DOMAIN, rule.source, True), policy_file
                    )
                )
                filtered_policy_file.contexts.extend(
                    self.filter_context(
                        FilterRule(FilterType.DOMAIN, rule.target, True), policy_file
                    )
                )
                filtered_policy_file.se_apps.extend(
                    self.filter_se_app(
                        FilterRule(FilterType.DOMAIN, rule.source, True), policy_file
                    )
                )
                filtered_policy_file.se_apps.extend(
                    self.filter_se_app(
                        FilterRule(FilterType.DOMAIN, rule.target, True), policy_file
                    )
                )

        for se_app in policy_file.se_apps:
            for type_ in se_app.type_def.types:
                if self.check_similarity(filter_rule, type_):
                    filtered_policy_file.type_def.append(se_app.type_def)
                    filtered_policy_file.rules.extend(
                        self.filter_rule(
                            FilterRule(FilterType.DOMAIN, se_app.type_def.name, True),
                            policy_file,
                        )
                    )
                    filtered_policy_file.contexts.extend(
                        self.filter_context(
                            FilterRule(FilterType.DOMAIN, se_app.type_def.name, True),
                            policy_file,
                        )
                    )
                    filtered_policy_file.se_apps.extend(
                        self.filter_se_app(
                            FilterRule(FilterType.DOMAIN, se_app.type_def.name, True),
                            policy_file,
                        )
                    )

        return filtered_policy_file

    def check_similarity(self, filter_rule, string_to_check):
        if filter_rule.exact_word:
            return string_to_check.strip() == filter_rule.keyword.strip()
        else:
            return filter_rule.keyword.strip() in string_to_check.strip()

    def filter_typedef(self, filter_rule, policy_file):
        lst_tye_def = []
        for type_def in policy_file.type_def:
            if self.check_similarity(filter_rule, type_def.name):
                lst_tye_def.append(type_def)
        return lst_tye_def

    def filter_context(self, filter_rule, policy_file):
        lst_context = []
        for context in policy_file.contexts:
            if self.check_similarity(filter_rule, context.security_context.type):
                lst_context.append(context)
        return lst_context

    def filter_context_by_pathname(self, filter_rule, policy_file):
        lst_context = []
        for context in policy_file.contexts:
            if self.check_similarity(filter_rule, context.path_name):
                lst_context.append(context)
        return lst_context

    def filter_se_app(self, filter_rule, policy_file):
        lst_se_app = []
        for se_app in policy_file.se_apps:
            if self.check_similarity(filter_rule, se_app.domain):
                lst_se_app.append(se_app)
        return lst_se_app

    def filter_se_app_by_name(self, filter_rule, policy_file):
        lst_se_app = []
        for se_app in policy_file.se_apps:
            if self.check_similarity(filter_rule, se_app.name):
                lst_se_app.append(se_app)
        return lst_se_app

    def filter_rule(self, filter_rule, policy_file):
        lst_rule = []
        for rule in policy_file.rules:
            if self.check_similarity(filter_rule, rule.source) or self.check_similarity(
                filter_rule, rule.target
            ):
                lst_rule.append(rule)
        return lst_rule

    def filter_attribute(self, filter_rule, policy_file):
        lst_attribute = []
        for attribute in policy_file.attribute:
            if self.check_similarity(filter_rule, attribute.name):
                lst_attribute.append(attribute)
        return lst_attribute

    def select_macro_def(self, filter_rule, policy_file):
        lst_macro_def = []
        for macro_def in policy_file.macros:
            if self.check_similarity(filter_rule, macro_def.name):
                lst_macro_def.append(macro_def)
        return lst_macro_def
