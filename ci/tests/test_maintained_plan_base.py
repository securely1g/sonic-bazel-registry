"""General maintained-base regression tests; temporary Git only, no builds."""
from test_registry_ci import FixtureTestCase, registry_ci
from unittest import mock


class MaintainedPlanBaseTests(FixtureTestCase):
    def test_inherited_main_ci_is_not_topic_work(self):
        self.entry("alpha", "1.0.0")
        stale = self.commit("published old base")
        self.git("checkout", "-b", "maintained")
        helper = self.root / "ci" / "registry_ci.py"
        helper.parent.mkdir()
        helper.write_text("# maintained planner\n")
        self.entry("beta", "1.0.0")
        current = self.commit("maintained CI and unrelated release")
        self.git("checkout", "-b", "topic", stale)
        self.entry("component", "1.0.0")
        self.commit("component registration")
        self.git("-c", "user.name=Fixture", "-c", "user.email=f@example.invalid",
                 "-c", "commit.gpgsign=false", "merge", "--no-edit", "maintained")
        head = self.git("rev-parse", "HEAD")
        for base in (stale, current):
            plan = registry_ci.plan(self.root, base, head, published=current)
            self.assertEqual([j["module"] for j in plan["include"]], ["component"])

    def test_actual_planner_change_keeps_full_and_additional_coverage(self):
        for module in ("alpha", "beta", "gamma"):
            self.entry(module, "2.0.0")
        self.entry("alpha", "1.0.0")
        base = self.commit("published consumers")
        path = self.root / "ci" / "registry_ci.py"
        path.parent.mkdir()
        path.write_text("def plan():\n    return 'real planner change'\n")
        head = self.commit("planner semantics changed")
        with mock.patch.object(registry_ci, "ADDITIONAL_PRESUBMITS", {("alpha", "1.0.0")}):
            jobs = registry_ci.plan(self.root, base, head, published=base)["include"]
        self.assertEqual({(j["module"],j["version"]) for j in jobs},
                         {("alpha", "1.0.0"), ("alpha", "2.0.0"), ("beta", "2.0.0"), ("gamma", "2.0.0")})

    def test_published_input_rewrite_still_rejected(self):
        entry = self.entry("alpha", "1.0.0")
        base = self.commit("published")
        (entry / "MODULE.bazel").write_text('module(name="alpha", version="1.0.0")\n# mutation\n')
        head = self.commit("forbidden published mutation")
        with self.assertRaisesRegex(registry_ci.RegistryError, "published"):
            registry_ci.plan(self.root, base, head, published=base)
