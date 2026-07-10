import sys
from analyzer.AnalyzerUtility import *
from analyzer.AbstractAnalyzer import *
from model.PolicyEntities import *
from PythonUtilityClasses import FileReader as FR
from MyLogger import MyLogger

# Map camelCase key names used in real Android seapp_contexts files to the
# canonical snake_case attribute names used in SeAppContext.
_SEAPP_KEY_ALIASES = {
    "isPrivApp": "is_priv_app",
    "isSystemServer": "is_system_server",
    "isEphemeralApp": "is_ephemeral_app",
    "fromRunAs": "from_run_as",
    "minTargetSdkVersion": "min_target_sdk_version",
    "levelFrom": "level_from",
}


class SeAppAnalyzer(AbstractAnalyzer):
    def __init__(self) -> None:
        self.policy_file = None

    def analyze(self, filePath):
        try:
            self.policy_file = PolicyFile(filePath, "", FileTypeEnum.SEAPP_CONTEXTS)
            file_reader = FR.FileReader()
            temp_lines = file_reader.read_file_lines(filePath)
            for line in temp_lines:
                self.process_line(line)

            # print(self.policy_file)
            return self.policy_file
        except Exception as err:
            MyLogger.log_error(sys, err, filePath)
            return None

    def process_line(self, input_string):
        input_string = clean_line(input_string)
        if input_string is None:
            return
        self.policy_file.se_apps.append(self.extract_definition(input_string))

    def extract_definition(self, input_string):
        try:
            se_app = SeAppContext()
            if "neverallow" in input_string:
                se_app.never_allow = True
                input_string = input_string.replace("neverallow", "").strip()

            items = input_string.strip().split()
            se_app.where_is_it = self.policy_file.where_is_it

            for item in items:
                split = item.split("=", 1)
                if len(split) < 2:
                    continue
                # Normalise camelCase keys (Android format) to snake_case
                key = _SEAPP_KEY_ALIASES.get(split[0], split[0])
                value = split[1]
                # Input selectors
                if key == "user":
                    se_app.user = value
                elif key == "is_priv_app":
                    se_app.is_priv_app = self.convert_to_boolean(value)
                elif key == "is_system_server":
                    se_app.is_system_server = self.convert_to_boolean(value)
                elif key == "is_ephemeral_app":
                    se_app.is_ephemeral_app = self.convert_to_boolean(value)
                elif key == "name":
                    se_app.name = value
                elif key == "min_target_sdk_version":
                    se_app.min_target_sdk_version = value
                elif key == "from_run_as":
                    se_app.from_run_as = value
                elif key == "seinfo":
                    se_app.seinfo = value
                # Outputs
                elif key == "domain":
                    se_app.domain = value
                elif key == "type":
                    se_app.type = value
                elif key == "level_from":
                    se_app.level_from = value
                elif key == "level":
                    se_app.level = value

            return se_app

        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def convert_to_boolean(self, input_string):
        if "true" in input_string or "True" in input_string:
            return True
        elif "false" in input_string or "False" in input_string:
            return False
        else:
            return None


if __name__ == "__main__":
    print(sys.argv)
    seAppAnalyzer = SeAppAnalyzer()
    seAppAnalyzer.analyze(sys.argv[1])
