"""Run upstream success/failure fixtures with each Makefile's actual switches."""
from pathlib import Path
import re
import subprocess
import sys

cli = str(Path(sys.argv[1]).absolute())
root = Path(sys.argv[2]).absolute().parent
count = 0
for makefile in sorted(root.glob("*/Makefile")):
    contents = makefile.read_text()
    for target, case, success in [("ok", "succeed", True), ("broken", "fail", False)]:
        recipe = contents.split("\n" + target + ":\n", 1)[1].split("\nbroken:", 1)[0]
        flags = ["--openconfig", "-p", str(root / "common")]
        if "--oc-only" in recipe:
            flags.append("--oc-only")
        if "--print-error-code" in recipe:
            flags.append("--print-error-code")
        for code in re.findall(r"-E\s+([A-Z_]+)", recipe):
            flags.extend(["-E", code])
        # Preserve multi-module augment cases too, not just the main fixture.
        models = re.findall(r"[A-Za-z0-9_-]+\.yang", recipe)
        if not models:
            raise AssertionError("No upstream fixture in " + str(makefile) + "/" + target)
        result = subprocess.run([cli, *flags, *models],
                                cwd=makefile.parent, text=True, capture_output=True)
        status = result.returncode
        # Three original recipes pipe diagnostics through grep -v. Preserve
        # their assertion: the expected warning must be the only diagnostic.
        excluded = re.search(r"grep -v ([A-Z_]+)", recipe)
        if excluded:
            output = result.stdout + result.stderr
            if excluded.group(1) not in output:
                raise AssertionError("Expected upstream diagnostic is missing: " + output)
            status = 0 if any(excluded.group(1) not in line for line in output.splitlines()) else 1
        if (status == 0) != success:
            raise AssertionError(str(makefile.parent.name) + "/" + case + "\n" + result.stdout + result.stderr)
        count += 1
print(f"Passed {count} original OpenConfig linter fixtures")
