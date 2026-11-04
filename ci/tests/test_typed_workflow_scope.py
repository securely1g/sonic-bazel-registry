"""Execute actual typed-feature workflow routing over real Git diffs."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import test_release_order as existing

ROOT = Path(__file__).resolve().parents[2]
BRANCH = "codex/registry-worker-provenance"
ALLOWED = (".github/workflows/registry-ci.yml", "ci/registry_ci.py",
           "ci/container_provenance.py", "ci/README.md",
           "ci/tests/test_container_provenance.py", "ci/tests/test_typed_workflow_scope.py")

class TypedWorkflowScopeTests(unittest.TestCase):
    route = existing.ReleaseOrderWorkflowTests.route
    matrix = existing.ReleaseOrderWorkflowTests.matrix
    output_matrix = existing.ReleaseOrderWorkflowTests.output_matrix

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
        self.assertIn("codex/registry-goyang-release-order", text)

if __name__ == "__main__":
    unittest.main()
