import os
import sys

# Ensure the 'app' directory (parent of this file) is on sys.path so imports like
# 'from analyzer.TeAnalyzer import TeAnalyzer' resolve during pytest runs from repo root.
TEST_DIR = os.path.dirname(__file__)
APP_DIR = os.path.dirname(TEST_DIR)
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
