"""pytest configuration — adds backend/ to sys.path so tests can import main, database, etc."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
