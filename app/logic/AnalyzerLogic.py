import os
from analyzer.FileAnalyzer import *
from drawer.RelationDrawer import *
from drawer.DrawerHelper import *
from AppSetting import *
from model.PolicyEntities import *
from logic.FilterResult import *
from logic.PolicyRepository import PolicyRepository
from PythonUtilityClasses import SystemUtility as SU


class AnalyzerLogic:
    def __init__(self):
        super().__init__()
        self._init_variables()
        self.init_analyzer()

    def _init_variables(self):
        self.keep_result = False
        self.list_of_diagrams = []
        self.ref_policy_file = PolicyFile()
        # Persist collected policy files across runs when keep_result is enabled
        self.collected_policy_files = []
        self.drawer = RelationDrawer()
        self.repository = PolicyRepository()
        # UI callbacks default to no-ops so the logic layer is usable
        # (and testable) without a UI wired up via the set_*_signal methods.
        self.update_generated_diagram_list = lambda diagrams: None
        self.update_analyzer_output_data = lambda policy_file: None
        self.update_statusbar = lambda message: None

    def init_analyzer(self):
        self.analyzer = FileAnalyzer()

    def analyze_all(self, included_paths, excluded_paths):
        # Analyze new inputs
        analyzed = self.analyzer.analyze(included_paths, excluded_paths) or []

        # Respect keep_result flag by accumulating results across runs
        if self.keep_result:
            self.collected_policy_files.extend(analyzed)
            policy_files = self.collected_policy_files
        else:
            self.collected_policy_files = analyzed
            policy_files = self.collected_policy_files
        self.update_statusbar("Analyze finished")
        self.ref_policy_file = self.make_ref_policy_file(policy_files)
        self.on_analyze_finished(None)
        self.update_analyzer_output_data(self.ref_policy_file)

    def make_ref_policy_file(self, policy_files):
        self.update_statusbar("Make reference policy file finished")
        if policy_files is None or len(policy_files) == 0:
            return None

        # Build reference policy using repository operations
        ref_policy_file = self.repository.merge(policy_files)
        ref_policy_file = self.repository.expand_macros(ref_policy_file)
        ref_policy_file = self.repository.dedup(ref_policy_file)
        return ref_policy_file

    # Backward-compatibility wrapper for existing callers/tests
    def convert_macrocall_to_rule(self, macro_calls, macros):
        return self.repository._macro_calls_to_rules(macro_calls, macros)

    def clear_output(self):
        files = SU.SystemUtility().get_list_of_files(os.getcwd() + "/" + OUT_DIR, "*")
        for file in files:
            if os.path.isfile(file):
                SU.SystemUtility().delete_files(file)
        self.on_analyze_finished(None)

    def clear_file_from_analyzer(self, file_path):
        self.analyzer.clear()
        SU.SystemUtility().delete_files(generate_diagram_file_name(file_path))
        SU.SystemUtility().delete_files(generate_puml_file_name(file_path))
        self.on_analyze_finished(None)

    def remove_file(self, file_path):
        SU.SystemUtility().delete_files(
            os.path.splitext(file_path)[0] + DIAGRAM_FILE_EXTENSION
        )
        SU.SystemUtility().delete_files(os.path.splitext(file_path)[0] + ".puml")

    def clear(self):
        self.ref_policy_file = PolicyFile()
        self.update_analyzer_output_data(None)

    def get_image_path(self, file_path):
        return generate_diagram_file_name(file_path)

    def set_keep_result(self, state):
        self.keep_result = state
        # print("self.keep_result:", self.keep_result)

    def set_ui_update_generated_diagrams_signal(self, _update_generated_diagram_list):
        self.update_generated_diagram_list = _update_generated_diagram_list

    def set_ui_update_analyzer_data_signal(self, _update_analyzer_output_data):
        self.update_analyzer_output_data = _update_analyzer_output_data

    def on_analyze_finished(self, filtered_policy_file):
        self.list_of_diagrams = SU.SystemUtility().get_list_of_files(
            os.getcwd() + "/" + OUT_DIR, "*" + DIAGRAM_FILE_EXTENSION
        )
        self.update_generated_diagram_list(self.list_of_diagrams)

    def set_statusbar_update_signal(self, _update_statusbar):
        self.update_statusbar = _update_statusbar

    """This function collects all the information of a filter rule and returns it as a list of string"""

    def get_info_of_item(self, filter_rule):
        if self.ref_policy_file is None:
            return None

        lst_info = []
        filter_result = FilterResult()
        # print("filter_rule: ", filter_rule)
        if filter_rule.filter_type == FilterType.DOMAIN:
            lst_info.extend(
                filter_result.filter_se_app(filter_rule, self.ref_policy_file)
            )
            lst_info.extend(
                filter_result.filter_context(filter_rule, self.ref_policy_file)
            )
            lst_info.extend(
                filter_result.filter_context(
                    FilterRule(
                        filter_rule.filter_type,
                        filter_rule.keyword + DOMAIN_EXECUTABLE,
                        filter_rule.exact_word,
                    ),
                    self.ref_policy_file,
                )
            )
            return lst_info
        elif filter_rule.filter_type == FilterType.CLASS_TYPE:
            lst_info.extend(
                filter_result.filter_context(filter_rule, self.ref_policy_file)
            )
            lst_info.extend(
                filter_result.filter_se_app(filter_rule, self.ref_policy_file)
            )
            return lst_info
        elif filter_rule.filter_type == FilterType.FILE_PATH:
            lst_info.extend(
                filter_result.filter_context_by_pathname(
                    filter_rule, self.ref_policy_file
                )
            )
            lst_info.extend(
                filter_result.filter_se_app_by_name(filter_rule, self.ref_policy_file)
            )
            return lst_info
        elif filter_rule.filter_type == FilterType.MACRO_DEF:
            lst_info.extend(
                filter_result.select_macro_def(filter_rule, self.ref_policy_file)
            )
            return lst_info
        else:
            return None
