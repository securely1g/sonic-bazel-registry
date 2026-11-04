"""Execute actual typed-feature workflow routing over real Git diffs."""
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
BRANCH = "codex/registry-worker-provenance"
ALLOWED = (".github/workflows/registry-ci.yml", "ci/registry_ci.py",
           "ci/container_provenance.py", "ci/README.md",
           "ci/tests/test_container_provenance.py", "ci/tests/test_typed_workflow_scope.py")
REPOSITORY = "securely1g/sonic-bazel-registry"
WORKFLOW = (ROOT / ".github/workflows/registry-ci.yml").read_text()
SCRIPT = WORKFLOW.split("          python3 - <<'PY'\n", 1)[1].split("          PY\n", 1)[0]
SCRIPT = "\n".join(line[10:] for line in SCRIPT.splitlines())

class TypedWorkflowScopeTests(unittest.TestCase):
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

    def test_owned_feature_has_no_module_jobs_and_preserves_policy_evidence(self):
        matrix = self.matrix()
        result, files, original = self.route(matrix, changed=ALLOWED, branch=BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output_matrix(files), {"include": []})
        proof = json.loads(files["plan-scope.json"])
        self.assertEqual(proof["planned_jobs"], len(matrix["include"]))
        self.assertEqual(proof["retained_jobs"], 0)
        self.assertEqual([row["job"] for row in proof["excluded_jobs"]], matrix["include"])
        self.assertEqual(proof["changed_files"], sorted(ALLOWED))
        self.assertEqual(proof["original_plan_sha256"], hashlib.sha256(original).hexdigest())
        self.assertEqual(proof["effective_plan_sha256"], hashlib.sha256(files["plan-effective.json"]).hexdigest())

    def test_actual_catalog_including_deb_fixtures_is_unselected(self):
        spec = importlib.util.spec_from_file_location("typed_scope_registry", ROOT / "ci/registry_ci.py")
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        rows = []
        for name, version in module.latest_presubmits(ROOT):
            config = json.loads((ROOT / "modules" / name / version / "presubmit.json").read_text())
            rows.extend({"module": name, "version": version, "architecture": arch,
                         "runner": module.RUNNERS[arch]} for arch in config["architectures"])
        self.assertTrue({"sonic-build-infra", "sonic-linux-kernel"} <= {row["module"] for row in rows})
        result, files, _ = self.route({"include": rows}, changed=ALLOWED, branch=BRANCH)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.output_matrix(files), {"include": []})
        self.assertEqual(json.loads(files["plan-scope.json"])["planned_jobs"], len(rows))

    def test_empty_module_and_unlisted_changes_fail_before_matrix_output(self):
        for changed in ((), ("modules/sonic-swss-common/metadata.json",),
                        ("ci/registry_ci.py", "ci/source_mirrors.cfg"),
                        ("ci/tests/unreviewed_test.py",), ("ci/README.md\nmodules/hidden",)):
            with self.subTest(changed=changed):
                result, files, _ = self.route(self.matrix(), changed=changed, branch=BRANCH)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Typed-provenance test scope rejects unexpected files", result.stderr)
                self.assertTrue(all(value is None for value in files.values()))

    def test_other_branch_suffix_repo_push_and_manual_are_unchanged(self):
        matrix = self.matrix()
        for context in ({"branch": "unrelated"}, {"branch": BRANCH + "-suffix"},
                        {"repository": "other/fork"}, {"workflow_repository": "other/fork"},
                        {"event": "push"}, {"event": "workflow_dispatch"}):
            with self.subTest(context=context):
                result, files, _ = self.route(matrix, changed=("modules/other/metadata.json",),
                                             **{"branch": BRANCH, **context})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(self.output_matrix(files), matrix)
                self.assertIsNone(files["plan-effective.json"])
                self.assertIsNone(files["plan-scope.json"])

    def test_policy_and_both_runner_suites_are_preserved(self):
        text = (ROOT / ".github/workflows/registry-ci.yml").read_text()
        self.assertLess(text.index("python3 ci/registry_ci.py plan --published"),
                        text.index('matrix = json.loads(Path("plan.json").read_text())'))
        unit = text.split("\n  unit:\n", 1)[1].split("\n  modules:\n", 1)[0]
        for arch in ("amd64", "arm64"): self.assertIn("architecture: " + arch, unit)
        self.assertNotIn("\n    if:", "\n" + unit)
        self.assertIn("python3 -m unittest discover -s ci/tests -v", unit)
        self.assertIn("if: needs.plan.outputs.has_jobs == 'true'", text)

if __name__ == "__main__":
    unittest.main()
