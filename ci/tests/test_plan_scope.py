"""Inert temporary-Git tests: no Bazel, package, network or build execution."""
from pathlib import Path
import unittest
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
        full = registry_ci.plan(self.root, base, head, published=base, max_jobs=100)
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

    def test_runtime_jobs_wait_for_successful_scope_plan(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/registry-ci.yml").read_text()
        self.assertIn("--base \"$BASE_SHA\" --head \"$HEAD_SHA\"", workflow)
        for start, end in (("  unit:", "  cross_fixture:"), ("  cross_fixture:", "  modules_local:")):
            job = workflow.split(start, 1)[1].split(end, 1)[0]
            self.assertIn("if: ${{ !cancelled() && needs.plan.result == 'success' }}", job)
        self.assertIn('[[ "$PLAN_RESULT" == success ]]', workflow)


if __name__ == "__main__":
    unittest.main()
