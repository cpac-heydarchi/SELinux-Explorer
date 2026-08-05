import sys
from analyzer.AnalyzerUtility import *
from analyzer.AbstractAnalyzer import *
from model.PolicyEntities import *
from PythonUtilityClasses import FileReader as FR
from MyLogger import MyLogger


class TeAnalyzer(AbstractAnalyzer):
    def __init__(self) -> None:
        self.policy_file = None

    def analyze(self, file_path):
        try:
            self.file_path = file_path
            self.policy_file = PolicyFile(file_path, "", FileTypeEnum.TE_FILE)
            file_reader = FR.FileReader()
            temp_lines = file_reader.read_file_lines(file_path)
            lstItems = self.extract_items_to_process(temp_lines)
            for line in lstItems:
                # print("line: ", line)
                self.process_line(line)

            # print("self.policy_file: ", self.policy_file)
            return self.policy_file
        except Exception as err:
            MyLogger.log_error(sys, err)
            return None

    """This function is used to extract the items from the file as a list. 
    Then the out put of this function is passed to the process_line function."""

    def extract_items_to_process(self, file_lines):
        lst_lines = []
        tmp_lst_lines = ""
        define_macro_found = False
        macro_call_found = False
        multi_line = False
        require_block_depth = 0  # tracks depth of require { … } blocks to skip
        for line in file_lines:
            line = clean_line(line)
            if line is None:
                continue

            # ── require { … } blocks: skip entirely ──────────────────────
            if require_block_depth > 0:
                require_block_depth += line.count("{") - line.count("}")
                if require_block_depth < 0:
                    require_block_depth = 0
                continue

            tokens = line.split()
            if tokens and tokens[0] == "require" and "{" in line:
                require_block_depth = line.count("{") - line.count("}")
                if require_block_depth < 0:
                    require_block_depth = 0
                continue

            # ── existing state machine ────────────────────────────────────
            if define_macro_found:
                if ")" in line and (tmp_lst_lines.count("(") + line.count("(")) == (
                    tmp_lst_lines.count(")") + line.count(")")
                ):
                    define_macro_found = False
                    lst_lines.append(tmp_lst_lines + "\n " + line)
                    tmp_lst_lines = ""
                else:
                    tmp_lst_lines = tmp_lst_lines + "\n " + line
            elif macro_call_found:
                if ")" in line and (tmp_lst_lines.count("(") + line.count("(")) == (
                    tmp_lst_lines.count(")") + line.count(")")
                ):
                    macro_call_found = False
                    assembled = tmp_lst_lines + "\n " + line
                    tmp_lst_lines = ""
                    # ifdef/ifndef: extract body lines so inner rules are parsed.
                    # first_token may be "ifdef(`FEATURE'," so use startswith.
                    first_token = assembled.split()[0] if assembled.split() else ""
                    if first_token.startswith(("ifdef", "ifndef")):
                        for body_line in assembled.splitlines()[1:]:
                            body_line = body_line.strip()
                            # skip M4 closing/separator markers like '), ', `
                            if not body_line or body_line.startswith("'"):
                                continue
                            if (
                                ";" in body_line
                                and body_line.count("(") == body_line.count(")")
                                and body_line.count("{") == body_line.count("}")
                            ):
                                lst_lines.append(body_line)
                    else:
                        lst_lines.append(assembled)
                else:
                    tmp_lst_lines = tmp_lst_lines + "\n " + line
            elif multi_line:
                if ";" in line:
                    multi_line = False
                    lst_lines.append(tmp_lst_lines + " " + line)
                    tmp_lst_lines = ""
                else:
                    tmp_lst_lines = tmp_lst_lines + " " + line
            else:
                if "define" in line:
                    define_macro_found = True
                    tmp_lst_lines = line
                elif (
                    ";" in line
                    and line.count("(") == line.count(")")
                    and line.count("{") == line.count("}")
                ):
                    lst_lines.append(line)
                elif "(" in line:
                    if line.count("(") == line.count(")"):
                        lst_lines.append(line)
                    else:
                        macro_call_found = True
                        tmp_lst_lines = line
                else:
                    multi_line = True
                    tmp_lst_lines = line

        # If an unclosed define/macro-call block was still open at end-of-file,
        # attempt to salvage any self-contained statements embedded inside it.
        if tmp_lst_lines:
            MyLogger.log_error(
                None,
                "Unclosed block in " + getattr(self, "file_path", "?"),
                tmp_lst_lines[:120],
            )
            for salvage_line in tmp_lst_lines.splitlines():
                salvage_line = salvage_line.strip()
                if not salvage_line or "define" in salvage_line:
                    continue
                if (
                    ";" in salvage_line
                    and salvage_line.count("(") == salvage_line.count(")")
                    and salvage_line.count("{") == salvage_line.count("}")
                ):
                    lst_lines.append(salvage_line)

        # print("lst_lines: ", "\n-----------------\n".join(lst_lines))
        return lst_lines

    def process_line(self, input_string):
        input_string = clean_line(input_string)
        if input_string is None:
            return
        items = input_string.split()
        # print("items: ", items)
        if len(items) > 0:
            if items[0].strip() == "type":
                type_def = self.extract_definition(input_string)
                if type_def is not None:
                    self.policy_file.type_def.append(type_def)
            elif items[0].strip() in ["typeattribute", "attribute"]:
                attribute = self.extract_attribute(input_string)
                if attribute is not None:
                    self.policy_file.attribute.append(attribute)
            elif items[0] in ["allow", "neverallow", "auditallow", "dontaudit"]:
                self.policy_file.rules.extend(self.extract_rule(input_string))
            elif items[0] == "permissive":
                permissive = self.extract_permissive(input_string)
                if permissive is not None:
                    self.policy_file.permissives.append(permissive)
            elif items[0] == "typealias":
                type_alias = self.extract_type_alias(input_string)
                if type_alias is not None:
                    self.policy_file.type_aliases.append(type_alias)
            elif items[0] in [x.value for x in XpermRuleEnum]:
                xperm_rule = self.extract_xperm_rule(input_string)
                if xperm_rule is not None:
                    self.policy_file.xperm_rules.append(xperm_rule)
            elif items[0] in ["type_transition", "type_change", "type_member"]:
                tt = self.extract_type_transition(input_string)
                if tt is not None:
                    self.policy_file.type_transitions.append(tt)
            elif "define" in input_string:
                macro = self.extract_macro(input_string)
                if macro is not None:
                    self.policy_file.macros.append(macro)
            elif "(" in input_string and ")" in input_string:
                macro_call = self.extract_macro_call(input_string)
                if macro_call is not None:
                    self.policy_file.macro_calls.append(macro_call)
            # if any values of NotSupportedRuleEnum can be found in input_string, then continue
            elif any(x.value in input_string for x in NotSupportedRuleEnum):
                return
            else:
                MyLogger.log_error(
                    None, "Unknown input from " + self.file_path, input_string
                )

    # will extract typealias type_id alias alias_id;
    def extract_type_alias(self, input_string):
        try:
            items = input_string.replace(";", "").split()
            type_alias = TypeAlias()
            type_alias.name = items[1].strip()
            type_alias.alias = items[3].strip()
            return type_alias
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def extract_type_transition(self, input_string):
        """Parse type_transition / type_change / type_member rules.

        Syntax: rule_type source target:class default_type ["object_name"];
        """
        try:
            s = (
                input_string.replace(" : ", ":")
                .replace(" :", ":")
                .replace(": ", ":")
                .replace(";", "")
                .strip()
            )
            items = s.split()
            tt = TypeTransition()
            tt.rule_type = items[0]
            tt.source = items[1]
            colon_pos = items[2].find(":")
            if colon_pos < 0:
                return None
            tt.target = items[2][:colon_pos]
            tt.class_type = items[2][colon_pos + 1 :]
            tt.default_type = items[3]
            if len(items) > 4:
                tt.object_name = items[4].strip('"')
            tt.where_is_it = self.policy_file.where_is_it
            return tt
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def extract_xperm_rule(self, input_string):
        """Parse extended-permission rules.

        Syntax: allowxperm source target:class operation xperm_set;
        where xperm_set is a single value or a brace group
        (e.g. ``{ 0x8910-0x8926 }`` or a named set).
        """
        try:
            s = (
                input_string.replace(" : ", ":")
                .replace(" :", ":")
                .replace(": ", ":")
                .replace(";", "")
                .replace("{", " ")
                .replace("}", " ")
                .strip()
            )
            items = s.split()
            colon_pos = items[2].find(":")
            if colon_pos < 0:
                return None
            xperm_rule = XpermRule()
            xperm_rule.rule = items[0]
            xperm_rule.source = items[1]
            xperm_rule.target = items[2][:colon_pos]
            xperm_rule.class_type = items[2][colon_pos + 1 :]
            xperm_rule.operation = items[3]
            xperm_rule.permissions = items[4:]
            xperm_rule.where_is_it = self.policy_file.where_is_it
            return xperm_rule
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def extract_permissive(self, input_string):
        try:
            items = input_string.replace(";", "").split()
            permissive = Permissive()
            permissive.name = items[1].strip()
            permissive.where_is_it = self.policy_file.where_is_it
            return permissive
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def extract_definition(self, input_string):
        try:
            types = (
                input_string.replace(";", "").replace("type ", "").strip().split(",")
            )
            type_def = TypeDef()
            type_def.name = types[0].strip()
            type_def.types.extend(types[1:])
            type_def.types = [x.strip() for x in type_def.types]
            type_def.where_is_it = self.policy_file.where_is_it
            if DOMAIN_EXECUTABLE in type_def.name:
                if not self.merge_exec_domain(type_def):
                    return type_def
            else:
                return type_def

        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def merge_exec_domain(self, type_def_exec):
        try:
            title = type_def_exec.name.replace(DOMAIN_EXECUTABLE, "")
            for type_def in self.policy_file.type_def:
                if type_def.name == title:
                    type_def.types.extend(type_def_exec.types)
                    return True
            return False
        except Exception as err:
            MyLogger.log_error(sys, err, type_def_exec)
            return False

    def extract_attribute(self, input_string):
        """Need to extract multiple attribute in one line
        typeattribute type1 attribute1, attribute2;
        """
        try:
            input_string = clean_line(input_string)
            if input_string is None:
                return

            types = (
                input_string.replace(";", "")
                .replace(",", " ")
                .replace("typeattribute ", "")
                .replace("attribute ", "")
                .strip()
                .split()
            )
            attribute = Attribute()
            attribute.name = types[0].strip()
            attribute.where_is_it = self.policy_file.where_is_it
            if len(types) > 1:
                attribute.attributes.extend(types[1:])
            return attribute
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def extract_rule(self, input_string):
        lst_rules = []
        try:
            input_string = (
                input_string.replace(" : ", ":")
                .replace(" :", ":")
                .replace(": ", ":")
                .strip()
            )
            input_string = input_string.replace("{", " { ").replace("}", " } ").strip()
            input_string = (
                input_string.replace(": {", ":{ ").replace("} :", "}:").strip()
            )
            input_string = (
                input_string.replace(":  {", ":{ ").replace("}  :", "}:").strip()
            )

            # print("inputString; " + inputString)
            input_string = input_string.replace(";", "").strip()
            items = input_string.split()
            for rule_enum in RuleEnum:
                if rule_enum.value == items[0].strip():
                    count_brackets = input_string.count("}")
                    lst_bracket_items = []
                    if count_brackets > 0:
                        offset = 0
                        while "{" in input_string[offset:]:
                            # print (inputString[offset:])
                            start = input_string.find("{", offset)
                            end = input_string.find("}", start)
                            bracket_string = input_string[start + 1 : end]
                            input_string = (
                                input_string[:start] + "###" + input_string[end + 1 :]
                            )
                            lst_bracket_items.append(bracket_string)
                            offset = start
                    items = (
                        input_string.replace(";", "").replace(": ", ":").strip().split()
                    )
                    sources = (
                        [items[1]]
                        if "###" not in items[1]
                        else lst_bracket_items.pop(0).strip().split()
                    )

                    # Split target:class – each side may be a "###" placeholder
                    # for a brace group, supporting multi-target AND multi-class rules.
                    colon_pos = items[2].find(":")
                    if colon_pos < 0:
                        break  # malformed rule, no target:class separator
                    target_token = items[2][:colon_pos]
                    class_token = items[2][colon_pos + 1 :]

                    targets = (
                        [target_token]
                        if "###" not in target_token
                        else lst_bracket_items.pop(0).strip().split()
                    )

                    # Filter negated types (e.g. "-domain" from { domain -domain2 })
                    sources = [s for s in sources if not s.startswith("-")]
                    targets = [t for t in targets if not t.startswith("-")]
                    if not sources or not targets:
                        break

                    classes = (
                        [class_token]
                        if "###" not in class_token
                        else lst_bracket_items.pop(0).strip().split()
                    )

                    permissions = (
                        [items[3]]
                        if "###" not in items[3]
                        else lst_bracket_items.pop(0).strip().split()
                    )
                    for source in sources:
                        for target in targets:
                            for cls in classes:
                                rule = Rule()
                                rule.where_is_it = self.policy_file.where_is_it
                                rule.rule = rule_enum.value
                                rule.source = source
                                rule.target = target
                                rule.class_type = cls
                                rule.permissions = permissions
                                lst_rules.append(rule)

        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
        finally:
            return lst_rules

    def extract_macro(self, input_string):
        try:
            # print("extract_macro input_string: ", input_string)
            lst_lines = input_string.splitlines()
            macro = PolicyMacro()
            # It's supposed to have "define" in the first item
            first_line = lst_lines.pop(0).replace("define", "").replace("'", "")
            first_line = first_line.replace("`", "").replace("(", "").replace(",", "")
            macro.name = first_line.strip()
            macro.where_is_it = self.policy_file.where_is_it
            for line in lst_lines:
                if line.strip() == "":
                    continue
                if ")" in line.strip():
                    break
                macro.rules_string.append(line)
                macro.rules.extend(self.extract_rule(line))
            return macro
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None

    def extract_macro_call(self, input_string):
        try:
            # print("extract_macro_call input_string: ", input_string)
            # Convert string to PolicyMacroCall
            macro_call = PolicyMacroCall()
            macro_call.name = input_string.split("(")[0].strip()
            macro_call.where_is_it = self.policy_file.where_is_it
            parameters = (
                input_string.split("(")[1]
                .replace(")", "")
                .replace(";", "")
                .strip()
                .split(",")
            )

            # remove white clearspaces in parameters
            # print("parameters: ", parameters)
            macro_call.parameters = [x.strip() for x in parameters]
            return macro_call
        except Exception as err:
            MyLogger.log_error(sys, err, input_string)
            return None


if __name__ == "__main__":
    print(sys.argv)
    te_analyzer = TeAnalyzer()
    print(te_analyzer.analyze(sys.argv[1]))
