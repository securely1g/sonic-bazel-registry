"""Keep the temporary no-DEB matrix restriction explicit and fail closed."""

import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "collector_scope", Path(__file__).resolve().parents[1] / "collector_validation_scope.py")
scope = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(scope)


class CollectorScopeTests(unittest.TestCase):
    def setUp(self):
        self.source = {"module": "sonic-build-infra", "version": scope.VERSION,
                       "architecture": "amd64", "runner": "ubuntu-24.04"}
        self.matrix = {"include": [self.source, {"module": "other", "version": "1", "architecture": "amd64"}]}

    def test_collector_only_keeps_real_runner_tests_without_module_jobs(self):
        self.assertEqual(scope.select(self.matrix, ["ci/registry_ci.py"],
                                      "codex/registry-unicode-artifacts", None), {"include": []})

    def test_consumer_keeps_exact_source_job(self):
        self.assertEqual(scope.select(self.matrix, [scope.CANDIDATE + "/source.json", "ci/registry_ci.py"],
                                      "codex/docbook-tools-registry", scope.CANDIDATE_TREE),
                         {"include": [self.source]})

    def test_other_branches_are_not_eligible(self):
        with self.assertRaises(ValueError):
            scope.select(self.matrix, [], "main", None)

    def test_unknown_ci_and_module_changes_are_rejected(self):
        for branch in scope.BRANCHES:
            for path in ["modules/other/1/source.json", "ci/unsafe.py"]:
                with self.subTest(branch=branch, path=path), self.assertRaises(ValueError):
                    scope.select(self.matrix, [path], branch, scope.CANDIDATE_TREE)
        with self.assertRaises(ValueError):
            scope.select(self.matrix, [scope.CANDIDATE + "/source.json"],
                         "codex/registry-unicode-artifacts", None)

    def test_changed_source_graph_requires_new_review(self):
        with self.assertRaisesRegex(ValueError, "action graph"):
            scope.select(self.matrix, [], "codex/docbook-tools-registry", "0" * 40)

    def test_missing_duplicate_or_other_architecture_job_is_rejected(self):
        for jobs in [[], [self.source, self.source], [dict(self.source, architecture="arm64")]]:
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                scope.select({"include": jobs}, [], "codex/docbook-tools-registry", scope.CANDIDATE_TREE)


if __name__ == "__main__":
    unittest.main()
