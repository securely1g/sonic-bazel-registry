"""Generate upstream atom initializers from target-preprocessed registrations."""
from pathlib import Path
import re
import sys

text = "\n".join(Path(path).read_text() for path in sys.argv[1:-1])
lines = []
for kind in ("builder", "map"):
    # The upstream macros expand to a function with a registration call. Reading
    # preprocessed input preserves the feature guards used for these definitions.
    names = sorted(set(re.findall(r"void init_atom_" + kind + r"_([A-Za-z0-9_]+)\(\)", text)))
    if not names:
        raise ValueError("No preprocessed atom " + kind + " registrations")
    lines.extend("void init_atom_" + kind + "_" + name + "(void);" for name in names)
    lines.extend(["void init_atom_" + kind + "(void) {", "static int init = 0; if (init) return; init++;"])
    lines.extend("init_atom_" + kind + "_" + name + "();" for name in names)
    lines.append("}")
Path(sys.argv[-1]).write_text("\n".join(lines) + "\n")
