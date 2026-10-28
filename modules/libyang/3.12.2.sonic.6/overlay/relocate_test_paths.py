"""Relocate upstream test path literals to the declared runtime fixtures."""
from pathlib import Path
import re
import sys

source, destination = map(Path, sys.argv[1:])
text = source.read_text()
tokens = list(re.finditer(r'"(?:\\.|[^"\\])*"|\b(?:TESTS_DIR_MODULES_YANG|TESTS_SRC|TESTS_BIN|PATH_SEPARATOR|LYPLG_SUFFIX)\b', text))
replacements = []
index = 0
while index < len(tokens):
    end = index + 1
    while end < len(tokens) and not text[tokens[end - 1].end():tokens[end].start()].strip():
        end += 1
    group = tokens[index:end]
    if any(token.group() in ('TESTS_SRC', 'TESTS_BIN', 'TESTS_DIR_MODULES_YANG') for token in group):
        values = [token.group() for token in group]
        replacements.append((group[0].start(), group[-1].end(), 'ly_tests_join_path(' + str(len(values)) + ', ' + ', '.join(values) + ')'))
    index = end
for start, end, value in reversed(replacements):
    text = text[:start] + value + text[end:]
destination.write_text(text)
