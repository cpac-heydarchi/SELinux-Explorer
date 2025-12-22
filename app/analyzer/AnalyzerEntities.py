from dataclasses import dataclass, field
from PythonUtilityClasses.SystemUtility import *


@dataclass
class AnalyzerInfo:
    source_file: FileInfo = field(default_factory=FileInfo)
    puml_file: FileInfo = field(default_factory=FileInfo)
    png_file: FileInfo = field(default_factory=FileInfo)
