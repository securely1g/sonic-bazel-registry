"""Relocate extracted pkg-config installation variables without changing its archive payload."""
import pathlib
import posixpath
import re
import sys


def relocate(content, installed):
    directory = posixpath.dirname("/" + installed.lstrip("/"))
    pattern = re.compile(rb"(?m)^((?:prefix|exec_prefix|libdir|includedir)[ \t]*=[ \t]*)(/[^\r\n]*?)([ \t]*)(?=\r?$)")
    def replace(match):
        prefix = match[2].decode("utf-8")
        if "$" in prefix or posixpath.normpath(prefix) != prefix:
            return match[0]
        relative = posixpath.relpath(prefix, directory)
        value = "${pcfiledir}" + ("/" + relative if relative != "." else "")
        return match[1] + value.encode("utf-8") + match[3]
    return pattern.sub(replace, content)


if __name__ == "__main__":
    pathlib.Path(sys.argv[2]).write_bytes(relocate(pathlib.Path(sys.argv[1]).read_bytes(), sys.argv[3]))
