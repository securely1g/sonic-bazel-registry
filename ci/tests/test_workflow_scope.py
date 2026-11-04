"""Execute the workflow's actual routing against real changed-file diffs."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
BRANCH = "codex/registry-integration-version-pins"
REPOSITORY = "securely1g/sonic-bazel-registry"
WORKFLOW = (ROOT / ".github/workflows/registry-ci.yml").read_text()
SCRIPT = WORKFLOW.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
SCRIPT = "\n".join(line[10:] for line in SCRIPT.splitlines())
ALLOWED = (
    ".github/workflows/registry-ci.yml",
    "ci/registry_ci.py",
    "ci/README.md",
    "ci/tests/test_registry_ci.py",
    "ci/tests/test_workflow_scope.py",
)


class VersionPinWorkflowScopeTest(unittest.TestCase):
    def route(self, matrix, *, changed=("ci/registry_ci.py",), event="pull_request",
              branch=BRANCH, repository=REPOSITORY, workflow_repository=REPOSITORY):
        with tempfile.TemporaryDirectory(prefix="registry-workflow-scope-") as temporary:
            work = Path(temporary)
            environment = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

            def git(*arguments):
                return subprocess.check_output(
                    ["git", *arguments], cwd=work, env=environment, text=True,
                    stderr=subprocess.PIPE,
                ).strip()

            def commit(message):
                git("add", "--all")
                git("-c", "user.name=Registry CI fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", message)
                return git("rev-parse", "HEAD")

            git("init", "--quiet")
            (work / "initial").write_text("fixture\n")
            base = commit("baseline")
            for name in changed:
                path = work / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("changed fixture\n")
            head = commit("validator change")
            # Whitespace is intentional: routing must preserve the original bytes.
            original = (json.dumps(matrix, indent=4) + "\n\n").encode()
            (work / "plan.json").write_bytes(original)
            environment.update(EVENT_NAME=event, HEAD_REF=branch, HEAD_REPOSITORY=repository,
                               REPOSITORY=workflow_repository, BASE_SHA=base, HEAD_SHA=head,
                               GITHUB_OUTPUT=str(work / "output"))
            result = subprocess.run([sys.executable, "-I", "-c", SCRIPT], cwd=work, env=environment,
                                    text=True, capture_output=True, timeout=30)
            self.assertEqual((work / "plan.json").read_bytes(), original)
            files = {name: (work / name).read_bytes() if (work / name).exists() else None
                     for name in ("output", "plan-effective.json", "plan-scope.json")}
            return result, files, original

    def matrix(self):
        return {"include": [
            {"module": module, "version": "reviewed-version", "architecture": architecture,
             "runner": "ubuntu-24.04" if architecture == "amd64" else "ubuntu-24.04-arm"}
            for module in ("sonic-build-infra", "rules_distroless", "sonic-linux-kernel", "sonic-mgmt-common")
            for architecture in ("amd64", "arm64")
        ]}

    def output_matrix(self, files):
        values = dict(line.split("=", 1) for line in files["output"].decode().splitlines())
        matrix = json.loads(values["matrix"])
        self.assertEqual(values["has_jobs"], str(bool(matrix["include"])).lower())
        return matrix

    def test_owned_pr_retains_other_jobs_and_records_each_deferred_job(self):
        matrix = self.matrix()
        result, files, original = self.route(matrix, changed=ALLOWED)
        self.assertEqual(result.returncode, 0, result.stderr)
        expected = {"include": [job for job in matrix["include"]
                                if job["module"] in ("rules_distroless", "sonic-mgmt-common")]}
        self.assertEqual(self.output_matrix(files), expected)
        self.assertEqual(json.loads(files["plan-effective.json"]), expected)
        receipt = json.loads(files["plan-scope.json"])
        self.assertEqual(receipt["changed_files"], sorted(ALLOWED))
        self.assertEqual(receipt["planned_jobs"], 8)
        self.assertEqual(receipt["retained_jobs"], 4)
        self.assertEqual(receipt["original_plan_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(receipt["effective_plan_sha256"], hashlib.sha256(files["plan-effective.json"]).hexdigest())
        self.assertEqual([row["job"] for row in receipt["excluded_jobs"]],
                         [job for job in matrix["include"] if job not in expected["include"]])
        self.assertTrue(all("Debian test packages" in row["reason"] for row in receipt["excluded_jobs"]))
        self.assertEqual((receipt["event"], receipt["branch"], receipt["repository"]),
                         ("pull_request", BRANCH, REPOSITORY))
        self.assertRegex(receipt["base"], r"^[a-f0-9]{40}$")
        self.assertRegex(receipt["head"], r"^[a-f0-9]{40}$")
        self.assertNotEqual(receipt["base"], receipt["head"])

    def test_actual_catalog_keeps_every_job_outside_two_packaging_suites(self):
        spec = importlib.util.spec_from_file_location("workflow_registry_ci", ROOT / "ci/registry_ci.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        rows = []
        for name, version in sorted(module.latest_presubmits(ROOT)):
            manifest = json.loads((ROOT / "modules" / name / version / "presubmit.json").read_text())
            rows.extend({"module": name, "version": version, "architecture": architecture,
                         "runner": module.RUNNERS[architecture]} for architecture in manifest["architectures"])
        result, files, _ = self.route({"include": rows})
        self.assertEqual(result.returncode, 0, result.stderr)
        excluded = [row for row in rows if row["module"] in ("sonic-build-infra", "sonic-linux-kernel")]
        self.assertEqual({row["module"] for row in excluded},
                         {"sonic-build-infra", "sonic-linux-kernel"})
        retained = [row for row in rows if row not in excluded]
        self.assertEqual(self.output_matrix(files)["include"], retained)
        receipt = json.loads(files["plan-scope.json"])
        self.assertEqual([item["job"] for item in receipt["excluded_jobs"]], excluded)
        self.assertEqual(receipt["planned_jobs"], len(rows))
        self.assertEqual(receipt["retained_jobs"], len(retained))

    def test_empty_or_unexpected_diff_fails_before_publishing_matrix(self):
        for changed in ((), ("modules/sonic-linux-kernel/metadata.json",),
                        ("ci/registry_ci.py", "ci/source_mirrors.cfg"),
                        ("ci/tests/unreviewed_test.py",), ("ci/README.md\nmodules/hidden",)):
            with self.subTest(changed=changed):
                result, files, _ = self.route(self.matrix(), changed=changed)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Version-pin test scope rejects unexpected files", result.stderr)
                self.assertTrue(all(value is None for value in files.values()))

    def test_other_branch_repository_push_and_manual_selection_are_unchanged(self):
        matrix = self.matrix()
        for context in (
            {"branch": "ordinary"},
            {"repository": "another/fork"},
            {"workflow_repository": "another/fork"},
            {"event": "push"},
            {"event": "workflow_dispatch"},
        ):
            with self.subTest(context=context):
                result, files, _ = self.route(matrix, changed=("modules/other/metadata.json",), **context)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.output_matrix(files), matrix)
                self.assertIsNone(files["plan-effective.json"])
                self.assertIsNone(files["plan-scope.json"])

    def test_empty_effective_matrix_has_no_module_jobs(self):
        matrix = {"include": [row for row in self.matrix()["include"]
                              if row["module"] in ("sonic-build-infra", "sonic-linux-kernel")]}
        result, files, _ = self.route(matrix)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output_matrix(files), {"include": []})
        self.assertEqual(len(json.loads(files["plan-scope.json"])["excluded_jobs"]), 4)

    def test_workflow_retains_both_plan_artifacts_and_runner_architectures(self):
        upload = WORKFLOW.split("      - name: Retain validation plan\n", 1)[1].split("\n  unit:\n", 1)[0]
        for name in ("plan.json", "plan.log", "plan-effective.json", "plan-scope.json"):
            self.assertIn("            " + name + "\n", upload)
        unit = WORKFLOW.split("\n  unit:\n", 1)[1].split("\n  modules:\n", 1)[0]
        self.assertIn("architecture: amd64", unit)
        self.assertIn("architecture: arm64", unit)
        self.assertNotIn("\n    if:", "\n" + unit)
        self.assertIn("python3 -m unittest discover -s ci/tests -v", unit)


if __name__ == "__main__":
    unittest.main()
