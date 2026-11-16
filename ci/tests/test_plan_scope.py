"""Inert temporary-Git tests: no Bazel, package, network or build execution."""
from pathlib import Path
import unittest
from unittest import mock
import json
from test_registry_ci import FixtureTestCase, registry_ci


class PredispatchScopeTests(FixtureTestCase):
    def test_stale_event_base_does_not_fan_out_inherited_main_ci(self):
        self.entry("alpha", "1.0.0")
        self.entry("beta", "1.0.0")
        stale = self.commit("published old base")
        self.git("checkout", "-b", "maintained")
        helper = self.root / "ci" / "helper.py"
        helper.parent.mkdir()
        helper.write_text("# inherited maintained helper\n")
        current = self.commit("maintained CI advance")
        self.git("checkout", "-b", "topic", stale)
        self.entry("relay", "1.0.0")
        self.commit("relay candidate")
        self.git("-c", "user.name=Fixture", "-c", "user.email=f@example.invalid",
                 "-c", "commit.gpgsign=false", "merge", "--no-edit", "maintained")
        head = self.git("rev-parse", "HEAD")
        for base in (stale, current):
            plan = registry_ci.plan(self.root, base, head, published=current, max_jobs=1)
            self.assertEqual([j["module"] for j in plan["include"]], ["relay"])

    def test_current_catalog_change_fails_closed_without_truncation(self):
        for module in ("alpha", "beta", "gamma"):
            self.entry(module, "1.0.0")
        base = self.commit("published")
        catalog = self.root / "ci" / "github_sources" / "catalog.json"
        catalog.parent.mkdir(parents=True)
        catalog.write_text('{"sources": []}\n')
        head = self.commit("catalog change requires full coverage")
        full = registry_ci.plan(self.root, base, head, published=base)
        self.assertEqual(len(full["include"]), 3)
        with self.assertRaisesRegex(registry_ci.RegistryError, "3 required jobs > 2"):
            registry_ci.plan(self.root, base, head, published=base, max_jobs=2)

    def test_multi_module_edits_cannot_sneak_below_explicit_one_job_limit(self):
        self.entry("alpha", "1.0.0")
        base = self.commit("published")
        for module in ("beta", "gamma"):
            self.entry(module, "1.0.0")
        head = self.commit("two new modules")
        with self.assertRaisesRegex(registry_ci.RegistryError, "Predispatch scope exceeded"):
            registry_ci.plan(self.root, base, head, published=base, max_jobs=1)

    def test_limit_cannot_disable_publication_immutability(self):
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("published")
        (entry / "MODULE.bazel").write_text('module(name="alpha", version="1.0.0")\n# rewrite\n')
        head = self.commit("illegal published rewrite")
        with self.assertRaisesRegex(registry_ci.RegistryError, "published"):
            registry_ci.plan(self.root, base, head, published=base, max_jobs=100)

    def test_invalid_caps_fail_instead_of_disabling_guard(self):
        self.entry("alpha", "1.0.0")
        base = self.commit("published")
        for cap in (0, -1, True):
            with self.assertRaisesRegex(registry_ci.RegistryError, "positive integer"):
                registry_ci.plan(self.root, base, base, published=base, max_jobs=cap)

    def test_selection_only_classifier_rejects_executor_or_catalog_changes(self):
        self.entry("alpha", "1.0.0")
        folder = self.root / "ci"
        folder.mkdir()
        script = folder / "registry_ci.py"
        script.write_text("import json\ndef plan():\n    return 1\ndef run():\n    return 2\n")
        base = self.commit("baseline executor")
        script.write_text("import json\ndef plan():\n    return 3\ndef run():\n    return 2\n")
        head = self.commit("selection-only change")
        self.assertTrue(registry_ci.planning_only_change(self.root, base, head, ["ci/registry_ci.py"]))
        script.write_text("import json\ndef plan():\n    return 3\ndef run():\n    return 4\n")
        head = self.commit("executor change")
        self.assertFalse(registry_ci.planning_only_change(self.root, base, head, ["ci/registry_ci.py"]))
        self.assertFalse(registry_ci.planning_only_change(self.root, base, head, ["ci/github_sources/catalog.json"]))

    def test_assigned_scope_rejects_unknown_catalog_and_runtime_fanout(self):
        self.entry("sonic-dhcp-relay", "0.1.0-3c5fb7b55b2f2a93bbe493f8ed3eb670e8663622")
        self.entry("alpha", "1.0.0")
        base = self.commit("published baseline")
        for name in ("ci/github_sources/catalog.json", "ci/runtime.py"):
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("# unknown execution input\n")
            head = self.commit("requires unrelated module validation")
            with self.assertRaisesRegex(registry_ci.RegistryError, "scope mismatch"):
                registry_ci.plan(self.root, base, head, published=base, readiness_pr="235")

    def test_assigned_scope_requires_exact_version_and_architecture(self):
        self.entry("alpha", "1.0.0")
        base = self.commit("baseline")
        self.entry("sonic-dhcp-relay", "0.1.0-wrong")
        head = self.commit("wrong immutable version")
        with self.assertRaisesRegex(registry_ci.RegistryError, "scope mismatch"):
            registry_ci.plan(self.root, base, head, published=base, readiness_pr="235")
        with self.assertRaisesRegex(registry_ci.RegistryError, "Unknown bounded"):
            registry_ci.plan(self.root, base, head, published=base, readiness_pr="999")

    def test_unrelated_three_job_pr_keeps_existing_coverage(self):
        self.entry("alpha", "1.0.0")
        base = self.commit("baseline")
        for module in ("beta", "gamma", "delta"):
            self.entry(module, "1.0.0")
        head = self.commit("legitimate three-job unrelated PR")
        self.assertEqual(len(registry_ci.plan(self.root, base, head, published=base)["include"]), 3)

    def test_exact_assigned_pairs_and_wrong_architecture(self):
        self.entry("alpha", "1.0.0")
        base = self.commit("published")
        version = "0.0.5-429b0668a80fabc3d05b3fb67ccda900d863ae3c"
        entry = self.entry("sonic-fips", version)
        path = entry / "presubmit.json"
        cfg = json.loads(path.read_text())
        cfg["architectures"] = ["amd64", "arm64"]
        cfg["platforms"]["arm64"] = "@platforms//host:host"
        path.write_text(json.dumps(cfg))
        head = self.commit("exact FIPS native pair")
        result = registry_ci.plan(self.root, base, head, published=base, readiness_pr="234")
        self.assertEqual(len(result["include"]), 2)
        cfg["architectures"] = ["amd64"]
        del cfg["platforms"]["arm64"]
        path.write_text(json.dumps(cfg))
        head = self.commit("missing required native ARM lane")
        with self.assertRaisesRegex(registry_ci.RegistryError, "scope mismatch"):
            registry_ci.plan(self.root, base, head, published=base, readiness_pr="234")

    def test_rejected_scope_writes_no_plan_file(self):
        output = self.root / "plan.json"
        argv = ["registry_ci.py", "plan", "--published", "a" * 40,
                "--base", "b" * 40, "--head", "c" * 40, "--output", str(output)]
        with mock.patch("sys.argv", argv), mock.patch.dict("os.environ", {"REGISTRY_READINESS_PR": "235"}), \
                mock.patch.object(registry_ci, "plan", side_effect=registry_ci.RegistryError("scope mismatch")) as planner:
            with self.assertRaises(SystemExit) as error:
                registry_ci.main()
            self.assertEqual(error.exception.code, 1)
            self.assertEqual(planner.call_args.kwargs["readiness_pr"], "235")
        self.assertFalse(output.exists())

    def test_trusted_workflow_context_is_not_read_from_pr_files(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/registry-ci.yml").read_text()
        self.assertIn("github.repository == 'securely1g/sonic-bazel-registry'", workflow)
        self.assertIn("github.event.pull_request.number == 234 || github.event.pull_request.number == 235", workflow)
        self.assertNotIn("REGISTRY_READINESS_PR: ${{ vars.", workflow)
        # The entry point writes the output only after successful plan return.
        script = (Path(__file__).resolve().parents[1] / "registry_ci.py").read_text()
        self.assertLess(script.index("result = plan(ROOT"), script.index("args.output.write_text"))
        self.assertIn('[[ "$PLAN_RESULT" == success ]]', workflow)

    def test_runtime_jobs_wait_for_successful_scope_plan(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/registry-ci.yml").read_text()
        self.assertIn("--base \"$BASE_SHA\" --head \"$HEAD_SHA\"", workflow)
        for start, end in (("  unit:", "  cross_fixture:"), ("  cross_fixture:", "  modules_local:")):
            job = workflow.split(start, 1)[1].split(end, 1)[0]
            self.assertIn("if: ${{ !cancelled() && needs.plan.result == 'success' }}", job)
        self.assertIn('[[ "$PLAN_RESULT" == success ]]', workflow)


if __name__ == "__main__":
    unittest.main()
