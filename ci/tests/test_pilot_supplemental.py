import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "pilot_supplemental.py"


class FleetSupplementalTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.path = Path(self.scratch.name)
        self.runner = ["self-hosted", "Linux", "X64", "debian-trixie-container"]

    def primary(self):
        rows = []
        for module in ("iproute2", "p4c", "rules_go", "sonic-sairedis", "sonic-swss", "socat", "sflowtool"):
            arch = "amd64" if module == "sflowtool" else "arm64"
            cross = module not in {"socat", "sflowtool"}
            execution = "amd64" if cross else arch
            rows.append({"module": module, "version": "6.11.0.sonic.3" if module == "sflowtool" else "1.0",
                         "architecture": arch, "execution_architecture": execution, "emulated_arm": execution == "arm64",
                         "physical_architecture": "amd64", "runner": self.runner, "cross_compile": cross})
        return rows

    def invoke(self, rows):
        plan = json.dumps({"include": rows}, indent=2)
        (self.path / "plan.json").write_text(plan)
        result = subprocess.run([sys.executable, "-I", str(SCRIPT)], cwd=self.path, text=True, capture_output=True,
                                env={**os.environ, "GITHUB_OUTPUT": str(self.path / "outputs")})
        self.assertEqual((self.path / "plan.json").read_text(), plan)
        return result

    def test_required_routes_and_output_use_separate_names_and_keep_all_inputs(self):
        rows = self.primary()
        result = self.invoke(rows)
        self.assertEqual(result.returncode, 0, result.stderr)
        supplemental = json.loads((self.path / "fleet-supplemental.json").read_text())
        outputs = dict(line.split("=", 1) for line in (self.path / "outputs").read_text().splitlines())
        self.assertEqual(json.loads(outputs["matrix"]), supplemental)
        self.assertEqual(outputs["has_jobs"], "true")
        for row, extra in zip(rows, supplemental["include"], strict=True):
            with self.subTest(module=row["module"]):
                if row["module"] == "sflowtool":
                    self.assertEqual(extra, {**row, "version": "6.11.0.sonic.2", "case": "legacy-output"})
                elif row["cross_compile"]:
                    self.assertEqual(extra, {**row, "case": "arm-guest", "execution_architecture": "arm64",
                                             "cross_compile": False, "emulated_arm": True})
                else:
                    self.assertEqual(extra, {**row, "case": "arm-cross", "execution_architecture": "amd64",
                                             "cross_compile": True, "emulated_arm": False})

    def test_checks_already_in_primary_are_not_repeated(self):
        rows = self.primary()
        for row in rows:
            if row["module"] == "sflowtool":
                row["version"] = "6.11.0.sonic.2"
            else:
                row["cross_compile"] = not row["cross_compile"]
                row["execution_architecture"] = "amd64" if row["cross_compile"] else "arm64"
                row["emulated_arm"] = not row["cross_compile"]
        result = self.invoke(rows)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((self.path / "fleet-supplemental.json").read_text()), {"include": []})
        self.assertIn("has_jobs=false", (self.path / "outputs").read_text().splitlines())

    def test_missing_primary_module_stops_the_plan(self):
        result = self.invoke([row for row in self.primary() if row["module"] != "sonic-sairedis"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sonic-sairedis", result.stderr)
        self.assertFalse((self.path / "fleet-supplemental.json").exists())
