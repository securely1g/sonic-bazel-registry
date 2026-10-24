"""Expose the declared rules_python interpreter to upstream CMake generators."""
import os
import sys
os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
