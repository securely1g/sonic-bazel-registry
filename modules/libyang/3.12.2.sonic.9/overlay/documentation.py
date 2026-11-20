"""Expand upstream Doxyfile paths and run declared documentation tools."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from python.runfiles import runfiles


def main():
    template, output, logo, stylesheet, *sources = sys.argv[1:]
    resolver = runfiles.Create()
    doxygen = resolver.Rlocation("sonic_build_infra/tools/build_tools/doxygen")
    dot = resolver.Rlocation("sonic_build_infra/tools/build_tools/dot")
    config = Path(template).read_text()
    substitutions = {
        "PROJECT_NAME": "libyang",
        "PROJECT_VERSION": "3.12.2",
        "PROJECT_DESCRIPTION": "libyang is YANG data modelling language parser and toolkit written (and providing API) in C.",
        "DOC_LOGO": str(Path(logo).resolve()),
        "DOXY_INPUT": " ".join('"' + str(Path(source).resolve()) + '"' for source in sources),
        "INTERNAL_DOCS": "NO",
        "HAVE_DOT": "YES",
    }
    for name, value in substitutions.items():
        config = config.replace("@" + name + "@", value)
    values = {
        "OUTPUT_DIRECTORY": '"' + str(Path(output).resolve()) + '"',
        "HTML_OUTPUT": ".",
        "HTML_EXTRA_STYLESHEET": '"' + str(Path(stylesheet).resolve()) + '"',
        "DOT_PATH": '"' + str(Path(dot).absolute().parent) + '"',
    }
    for name, value in values.items():
        config = re.sub(r"(?m)^" + name + r"\s*=.*$", name + " = " + value, config)
    with tempfile.TemporaryDirectory(prefix="libyang-docs-") as temporary:
        path = Path(temporary) / "Doxyfile"
        path.write_text(config)
        subprocess.run([str(Path(doxygen).absolute()), str(path)], check=True)


if __name__ == "__main__":
    main()
