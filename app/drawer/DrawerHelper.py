import os
import shutil
import subprocess
from AppSetting import OUT_DIR
from enum import Enum
from dataclasses import dataclass, field
from typing import List

DIAGRAM_FILE_EXTENSION = ".png"


def generate_puml_file_name(file_name):
    return file_name.replace("/", "-") + ".puml"


def generate_diagram_file_name(file_name):
    return file_name.replace("/", "-") + "" + DIAGRAM_FILE_EXTENSION


def _resolve_plantuml_jar():
    # Try relative to app/ directory
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(os.path.dirname(here), "plantuml", "plantuml.jar")
    if os.path.isfile(candidate):
        return candidate
    # Also try CWD/out configured locations as a fallback
    alt = os.path.join(os.getcwd(), "app", "plantuml", "plantuml.jar")
    if os.path.isfile(alt):
        return alt
    return None


def generate_png(filepath):
    jar = _resolve_plantuml_jar()
    if jar is None:
        # Graceful fallback: keep .puml only
        print("PlantUML jar not found; skipped PNG rendering for:", filepath)
        return
    if shutil.which("java") is None:
        print("Java not found; skipped PNG rendering for:", filepath)
        return
    try:
        # Pass arguments as a list to avoid shell injection and let subprocess handle quoting
        result = subprocess.run(["java", "-jar", jar, filepath], capture_output=True, text=True)
    except FileNotFoundError:
        # Shouldn't happen because shutil.which was checked, but handle defensively
        print("Java executable not found; skipped PNG rendering for:", filepath)
        return
    if result.returncode != 0:
        print("PlantUML failed to render PNG for:", filepath, "exit:", result.returncode)
        if result.stderr:
            print(result.stderr)


def generate_svg(filepath):
    jar = _resolve_plantuml_jar()
    if jar is None:
        print("PlantUML jar not found; skipped SVG rendering for:", filepath)
        return
    if shutil.which("java") is None:
        print("Java not found; skipped SVG rendering for:", filepath)
        return
    try:
        result = subprocess.run(["java", "-jar", jar, "-tsvg", filepath], capture_output=True, text=True)
    except FileNotFoundError:
        print("Java executable not found; skipped SVG rendering for:", filepath)
        return
    if result.returncode != 0:
        print("PlantUML failed to render SVG for:", filepath, "exit:", result.returncode)
        if result.stderr:
            print(result.stderr)


@dataclass
class DrawingPackage:
    domain: str = ""
    names: List[str] = field(default_factory=list)
    type_defs: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)


class DrawingPosition(Enum):
    RIGHT = "tight"
    LEFT = "left"
    TOP = "top"
    BOTTOM = "bottom"


class DrawingStyle(Enum):
    NOTE = "note"
    DOMAIN = "package"
    LEGEND = "legend"


class DrawingColor(Enum):
    BLUE = "#blue"
    BLUE_LIGHT = "#lightblue"
    GREEN = "#green"
    GREEN_LIGHT = "#lightgreen"
    RED = "#red"
    RED_LIGHT = "#lightred"
    YELLOW = "#yellow"
    ORANGE = "#orange"


class DrawingTool:
    default_height = 1200  # 1500
    default_width = 2200  # 2500

    @staticmethod
    def generate_start_of_puml(height=default_height, width=default_width):
        lst_output = []
        lst_output.append("@startuml")
        lst_output.append("scale max %s height" % height)
        lst_output.append("scale max %s width" % width)
        lst_output.append("")
        return lst_output

    @staticmethod
    def generate_end_of_puml():
        lst_output = []
        lst_output.append("@enduml")
        return lst_output

    @staticmethod
    def define_note_style():
        lst_note = []
        lst_note.append("skinparam " + DrawingStyle.NOTE.value + " {")
        lst_note.append("borderColor black")
        lst_note.append("backgroundColor #FFD28A")
        lst_note.append("}")
        lst_note.append("")
        return lst_note

    @staticmethod
    def define_domain_style():
        lst_domain = []
        lst_domain.append("skinparam " + DrawingStyle.DOMAIN.value + " {")
        lst_domain.append("borderColor black")
        lst_domain.append("backgroundColor #A5FFD6")
        lst_domain.append("}")
        lst_domain.append("")
        return lst_domain

    @staticmethod
    def generate_note(title, position: DrawingPosition, items, first_line=""):
        items = list(dict.fromkeys(items))
        lst_note = []
        if title.strip() != "" and len(items) >= 1:
            lst_note.append(
                DrawingStyle.NOTE.value + " " + position.value + " of [" + title + "]"
            )
            lst_note.append("<b>" + first_line + "</b>")
            for item in items:
                lst_note.append("  - " + item)
            lst_note.append("end " + DrawingStyle.NOTE.value)
            lst_note.append("")
        return lst_note

    @staticmethod
    def generate_legend(
        title,
        position_vertical: DrawingPosition,
        position_horizontal: DrawingPosition,
        items,
        back_color: DrawingColor,
    ):
        items = list(dict.fromkeys(items))
        lst_note = []
        if title.strip() != "" and len(items) >= 1:
            lst_note.append(
                DrawingStyle.LEGEND.value
                + " "
                + position_vertical.value
                + "   "
                + position_horizontal.value
            )
            lst_note.append("<b>" + title + "</b>")
            for item in items:
                lst_note.append("  - " + item)
            lst_note.append("end" + DrawingStyle.LEGEND.value)
            lst_note.append("")
        return lst_note

    @staticmethod
    def generate_domain(title, description=None):
        lst_domain = []
        if title.strip() != "":
            lst_domain.append(DrawingStyle.DOMAIN.value + ' "*' + title + '*" {')
            lst_domain.append("[" + title + "]")
            lst_domain.append("}")
            lst_domain.append("")
        return lst_domain

    @staticmethod
    def generate_other_label(title, description=""):
        lst_domain = []
        if title.strip() != "":
            lst_domain.append(
                DrawingStyle.DOMAIN.value + ' "' + description + '" #FFA07A{'
            )
            lst_domain.append("[" + title + "]")
            lst_domain.append("}")
            lst_domain.append("")
        return lst_domain


if __name__ == "__main__":
    print(DrawingStyle.NOTE)
    print(DrawingStyle.NOTE.value)
