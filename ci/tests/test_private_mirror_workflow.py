"""Exercise mirror secret boundaries and fail-closed artifact publication."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github/workflows"
ROOT_SECRETS = {
    "DEBIAN_MIRROR_ROOT": "https://debian-fixture.example.invalid/archive/debian/",
    "DEBIAN_SECURITY_MIRROR_ROOT": "https://security-fixture.example.invalid/archive/debian-security/",
}
DATED_SECRETS = {
    "DEBIAN_MIRROR_BASE_URL": ROOT_SECRETS["DEBIAN_MIRROR_ROOT"] + "20200101T000000Z/",
    "DEBIAN_SECURITY_MIRROR_BASE_URL": ROOT_SECRETS["DEBIAN_SECURITY_MIRROR_ROOT"] + "20200102T000000Z/",
}
SECRETS = ROOT_SECRETS | DATED_SECRETS
CHECKOUT_FILES = {
    "roots": ("ci/private_mirrors.py", "ci/debian_snapshots.json"),
    "dated": ("ci/private_mirrors.py",),
    "": (),
}
TRIXIE = ["self-hosted", "Linux", "X64", "debian-trixie-container"]
LARGE_TRIXIE = ["self-hosted", "Linux", "X64", "debian-trixie-container-large"]


def expression_value(expression, context):
    """Evaluate the workflow's small Boolean/context expression subset."""
    expression = re.sub(r"\b(?:github|matrix|inputs|secrets|steps|runner|needs)(?:\.[A-Za-z_][A-Za-z_0-9]*)+",
                        lambda match: f"lookup({match[0]!r})", expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = re.sub(r"!(?!=)", "not ", expression)
    return eval(expression.strip(), {"__builtins__": {}}, {
        "lookup": lambda key: context.get(key, ""),
        "contains": lambda values, value: value in values,
        "fromJSON": json.loads,
        "hashFiles": lambda path: "fixture-hash" if path in context.get("_files", ()) else "",
        "always": lambda: True,
        "cancelled": lambda: context.get("_cancelled", False),
    })


def step(text, name):
    return text.split(f"      - name: {name}\n", 1)[1].split("      - ", 1)[0]


def script(text, name):
    return textwrap.dedent(step(text, name).split("        run: |\n", 1)[1])


def workflow_job(text, name):
    body = text.split(f"\n  {name}:\n", 1)[1]
    return re.split(r"^  [a-z_]+:\n", body, maxsplit=1, flags=re.M)[0]


def mirror_kind(job, context):
    chooser = step(job, "Identify the checked-out mirror configuration")
    guard = re.search(r"if: \$\{\{ (.*) \}\}", chooser)[1]
    choice = re.search(r'echo "kind=\$\{\{ (.*) \}\}"', chooser)[1]
    return expression_value(choice, context) if expression_value(guard, context) else ""


class PrivateMirrorSecretBoundaryTest(unittest.TestCase):
    def test_agent_compiles_once_without_secrets_or_tool_installation(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        self.assertNotIn("\n  http_audit:\n", workflow)
        producer = workflow.split("  plan:\n", 1)[1].split("  unit:\n", 1)[0]
        self.assertIn("runs-on: [self-hosted, Linux, X64, debian-trixie-container]", producer)
        compile_step = step(producer, "Compile the maintained audit source once")
        upload_step = step(producer, "Publish the same-run audit agent")
        self.assertIn("continue-on-error: true", compile_step)
        self.assertIn("continue-on-error: true", upload_step)
        self.assertIn("timeout-minutes: 2", compile_step)
        self.assertIn("timeout-minutes: 2", upload_step)
        self.assertIn("if: steps.http_audit_build.outcome == 'success'", upload_step)
        self.assertIn("http_audit_artifact_id: ${{ steps.http_audit_upload.outputs.artifact-id }}", producer)
        self.assertLess(producer.index("Compile the maintained audit source once"), producer.index("Select module versions"))
        self.assertNotIn("secrets.", producer)
        self.assertNotIn("apt-get", producer)
        self.assertNotIn("setup-java", producer)
        self.assertNotIn("curl", producer)
        self.assertEqual(workflow.count("python3 ci/build_http_audit.py"), 1)
        self.assertNotIn("build_http_audit.py", (WORKFLOWS / "registry-module.yml").read_text())
        self.assertIn("${{ github.run_attempt }}", producer)
        self.assertIn("retention-days: 30", producer)
        self.assertIn("${{ github.event.pull_request.head.sha || github.sha }}", producer)
        expression = re.search(r"^        if: \$\{\{ (.*) \}\}$", compile_step, re.M)[1]
        for event, head, actor, expected in (
            ("pull_request", "owner/repo", "maintainer", True),
            ("pull_request", "fork/repo", "contributor", False),
            ("pull_request", "owner/repo", "dependabot[bot]", False),
            ("pull_request_target", "owner/repo", "maintainer", False),
            ("push", "", "maintainer", True),
            ("workflow_dispatch", "", "maintainer", True),
        ):
            context = {"github.event_name": event, "github.actor": actor, "github.repository": "owner/repo",
                       "github.event.pull_request.head.repo.full_name": head}
            self.assertEqual(bool(expression_value(expression, context)), expected)

    def test_optional_agent_does_not_skip_public_test_jobs(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        for name in ("unit", "cross_fixture", "modules_local"):
            job = re.split(r"\n  [A-Za-z_]+:\n", workflow.split(f"  {name}:\n", 1)[1], maxsplit=1)[0]
            condition = re.search(r"^    if: \$\{\{ (.*) \}\}$", job, re.M)[1]
            self.assertIn("needs: plan", job)
            for plan_result in ("success", "failure", "skipped"):
                self.assertEqual(bool(expression_value(condition, {"needs.plan.result": plan_result,
                                                                   "needs.plan.outputs.has_local_jobs": "true"})),
                                 name != "modules_local" or plan_result == "success")
                self.assertFalse(expression_value(condition, {"needs.plan.result": plan_result,
                                                               "needs.plan.outputs.has_local_jobs": "true",
                                                               "_cancelled": True}))
        hosted = workflow.split("  modules_hosted_arm:\n", 1)[1].split("  required:\n", 1)[0]
        self.assertNotIn("http_audit", hosted)
        reusable = (WORKFLOWS / "registry-module.yml").read_text()
        self.assertRegex(reusable, r"http_audit_artifact_id:\n\s+description: [^\n]+\n\s+type: string\n\s+default: ''")

    def test_agent_downloads_are_same_run_and_exclude_hosted_arm(self):
        for filename in ("registry-ci.yml", "registry-module.yml"):
            workflow = (WORKFLOWS / filename).read_text()
            chunks = workflow.split("      - name: Download the optional same-run HTTP audit agent\n")[1:]
            self.assertTrue(chunks)
            for chunk in chunks:
                download = chunk.split("      - ", 1)[0]
                self.assertIn("continue-on-error: true", download)
                self.assertIn("artifact-ids:", download)
                self.assertIn("merge-multiple: true", download)
                self.assertNotIn("github-token:", download)
                self.assertNotIn("run-id:", download)
                self.assertNotIn("repository:", download)
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        unit = workflow.split("  unit:\n", 1)[1].split("  cross_fixture:\n", 1)[0]
        download = step(unit, "Download the optional same-run HTTP audit agent")
        condition = re.search(r"^        if: \$\{\{ (.*) \}\}$", download, re.M)[1]
        for runner, expected in ((TRIXIE, True), (["ubuntu-24.04-arm"], False)):
            self.assertEqual(expression_value(condition, {"matrix.runner": runner,
                                                         "needs.plan.outputs.http_audit_artifact_id": "123"}), expected)
    def test_live_mirror_probe_requires_an_explicit_manual_request(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        self.assertRegex(workflow, r"private_mirror_probe:\n\s+description: [^\n]+\n"
                                   r"\s+type: boolean\n\s+default: false")
        content = step(workflow, "Validate private Debian mirrors from the Trixie runner")
        self.assertIn("python3 ci/private_mirrors.py probe", content)
        self.assertNotIn("sudo", content)  # The final privacy scan reads mode-0600 receipts as the runner.
        expression = re.search(r"^        if: \$\{\{ (.*) \}\}$", content, re.M)[1]
        for event, requested, runner, expected in (
            ("pull_request", True, TRIXIE, False),
            ("push", True, TRIXIE, False),
            ("workflow_dispatch", False, TRIXIE, False),
            ("workflow_dispatch", "", TRIXIE, False),
            ("workflow_dispatch", True, ["ubuntu-24.04-arm"], False),
            ("workflow_dispatch", True, ["self-hosted", "Linux", "X64"], False),
            ("workflow_dispatch", True, TRIXIE, True),
        ):
            with self.subTest(event=event, requested=requested, runner=runner):
                context = {"github.event_name": event, "github.actor": "maintainer",
                           "inputs.private_mirror_probe": requested, "matrix.runner": runner}
                self.assertEqual(bool(expression_value(expression, context)), expected)

    def test_secret_expressions_reject_forks_bots_and_untrusted_runner_labels(self):
        main = (WORKFLOWS / "registry-ci.yml").read_text()
        reusable = (WORKFLOWS / "registry-module.yml").read_text()
        plan = workflow_job(main, "plan")
        jobs = {name: workflow_job(main, name) for name in ("unit", "cross_fixture", "modules_local")}
        jobs["validate"] = workflow_job(reusable, "validate")
        for name, job in jobs.items():
            bindings = re.findall(r"^\s+(DEBIAN_[A-Z_]+): \$\{\{ (.*) \}\}$", job, re.M)
            self.assertEqual({key for key, _ in bindings}, set(SECRETS), name)
            chooser = plan if name == "modules_local" else job
            self.assertLess(chooser.index("uses: actions/checkout@"), chooser.index("id: mirror_config"))
            self.assertNotIn("secrets.", step(chooser, "Identify the checked-out mirror configuration"))
            large_module_cases = (
                ("pull_request", "owner/repo", "maintainer", LARGE_TRIXIE, True),
                ("pull_request", "fork/repo", "contributor", LARGE_TRIXIE, False),
                ("pull_request", "owner/repo", "dependabot[bot]", LARGE_TRIXIE, False),
                ("push", "", "maintainer", LARGE_TRIXIE, True),
                ("workflow_dispatch", "", "maintainer", LARGE_TRIXIE, True),
                ("push", "", "maintainer", ["debian-trixie-container-large"], False),
                ("push", "", "maintainer", [*TRIXIE[:-1], "debian-trixie-container-larger"], False),
            ) if name in ("modules_local", "validate") else ()
            for event, head, actor, runner, trusted in (
                *large_module_cases,
                ("pull_request", "owner/repo", "maintainer", TRIXIE, True),
                ("push", "", "maintainer", TRIXIE, True),
                ("workflow_dispatch", "", "maintainer", TRIXIE, True),
                ("pull_request", "fork/repo", "contributor", TRIXIE, False),
                ("pull_request", "owner/repo", "dependabot[bot]", TRIXIE, False),
                ("pull_request_target", "owner/repo", "maintainer", TRIXIE, False),
                ("workflow_run", "owner/repo", "maintainer", TRIXIE, False),
                ("push", "", "maintainer", ["ubuntu-24.04-arm"], False),
                ("push", "", "maintainer", ["self-hosted", "Linux", "X64"], False),
                ("push", "", "maintainer", ["debian-trixie-container"], False),
            ):
                # The cross fixture has a fixed Trixie label set in runs-on.
                if name == "cross_fixture" and "self-hosted" in runner and runner != TRIXIE:
                    continue
                ctx = {"github.event_name": event, "github.actor": actor, "github.repository": "owner/repo",
                       "github.event.pull_request.head.repo.full_name": head, "matrix.runner": runner,
                       "runner.environment": "self-hosted" if "self-hosted" in runner else "github-hosted",
                       "inputs.runner": json.dumps(runner), **{f"secrets.{key}": value for key, value in SECRETS.items()}}
                for kind, files in (*CHECKOUT_FILES.items(), ("", ("ci/debian_snapshots.json",))):
                    ctx["_files"] = files
                    if name == "modules_local":
                        # The plan always runs on Trixie, independently of the target matrix runner.
                        ctx["needs.plan.outputs.mirror_config"] = mirror_kind(plan, ctx | {"runner.environment": "self-hosted"})
                    else:
                        ctx["steps.mirror_config.outputs.kind"] = mirror_kind(job, ctx)
                    pair = {"roots": ROOT_SECRETS, "dated": DATED_SECRETS, "": {}}[kind] if trusted else {}
                    for key, expression in bindings:
                        with self.subTest(job=name, event=event, runner=runner, head=head, kind=kind, secret=key):
                            self.assertEqual(expression_value(expression, ctx), pair.get(key, ""))
                            self.assertEqual(expression_value(expression, ctx | {f"secrets.{key}": ""}), "")

    def test_hosted_arm_call_does_not_forward_secrets(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        arm_job = workflow.split("  modules_hosted_arm:\n", 1)[1].split("  required:\n", 1)[0]
        self.assertNotIn("secrets:", arm_job)
        cross_fixture = workflow.split("  cross_fixture:\n", 1)[1].split("  modules_local:\n", 1)[0]
        self.assertIn("runs-on: [self-hosted, Linux, X64, debian-trixie-container]", cross_fixture)
        for secret in SECRETS:
            self.assertIn(f"secrets.{secret}", cross_fixture)
        reusable = (WORKFLOWS / "registry-module.yml").read_text()
        declarations = reusable.split("    secrets:\n", 1)[1].split("\npermissions:", 1)[0]
        for secret in SECRETS:
            self.assertRegex(declarations, rf"{secret}:\n\s+description: [^\n]+\n\s+required: false")

    def test_local_native_and_cross_calls_forward_secrets_only_for_trusted_runs(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        local_job = workflow_job(workflow, "modules_local")
        plan = workflow_job(workflow, "plan")
        self.assertIn("mirror_config: ${{ steps.mirror_config.outputs.kind }}", plan)
        for secret in SECRETS:
            expression = re.search(rf"^\s+{secret}: \$\{{\{{ (.*) \}}\}}$", local_job, re.M)[1]
            for architecture, cross in (("amd64", False), ("arm64", True)):
                for head, actor, expected in (("owner/repo", "maintainer", "fixture-value"),
                                               ("fork/repo", "contributor", ""),
                                               ("owner/repo", "dependabot[bot]", "")):
                    context = {"github.event_name": "pull_request", "github.actor": actor,
                               "github.repository": "owner/repo",
                               "github.event.pull_request.head.repo.full_name": head,
                               "matrix.runner": TRIXIE, "matrix.architecture": architecture,
                               "matrix.execution_architecture": "amd64", "matrix.cross_compile": cross,
                               "runner.environment": "self-hosted",
                               "_files": CHECKOUT_FILES["roots" if secret in ROOT_SECRETS else "dated"],
                               f"secrets.{secret}": "fixture-value"}
                    context["needs.plan.outputs.mirror_config"] = mirror_kind(plan, context)
                    with self.subTest(secret=secret, architecture=architecture, head=head, actor=actor):
                        self.assertEqual(expression_value(expression, context), expected)

    def test_large_module_audit_download_uses_same_trust_gate_and_matching_artifact(self):
        reusable = (WORKFLOWS / "registry-module.yml").read_text()
        download = step(reusable, "Download the optional same-run HTTP audit agent")
        guard = re.search(r"if: \$\{\{ (.*) \}\}", download)[1]
        for runner, head, actor, artifact, allowed in (
            (LARGE_TRIXIE, "owner/repo", "maintainer", "123", True),
            (LARGE_TRIXIE, "fork/repo", "contributor", "123", False),
            (LARGE_TRIXIE, "owner/repo", "dependabot[bot]", "123", False),
            (LARGE_TRIXIE, "owner/repo", "maintainer", "", False),
            (["ubuntu-24.04-arm"], "owner/repo", "maintainer", "123", False),
        ):
            context = {"inputs.runner": json.dumps(runner), "inputs.http_audit_artifact_id": artifact,
                       "github.event_name": "pull_request", "github.actor": actor,
                       "github.repository": "owner/repo", "github.event.pull_request.head.repo.full_name": head}
            with self.subTest(runner=runner, head=head, actor=actor, artifact=artifact):
                self.assertEqual(bool(expression_value(guard, context)), allowed)

    def test_failed_privacy_check_blocks_each_upload(self):
        for filename, name, check in (
            ("registry-ci.yml", "Retain runner test results", "privacy"),
            ("registry-ci.yml", "Retain cross fixture results", "privacy"),
            ("registry-module.yml", "Retain module validation results", "archive"),
        ):
            content = step((WORKFLOWS / filename).read_text(), name)
            expression = re.search(r"^        if: (.*)$", content, re.M)[1]
            for outcome in ("failure", "cancelled", "skipped", ""):
                self.assertFalse(expression_value(expression, {f"steps.{check}.outcome": outcome}))
            self.assertTrue(expression_value(expression, {f"steps.{check}.outcome": "success"}))


class PrivateMirrorWorkflowCommandTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="private-mirror-workflow-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.capture = self.directory / "commands.jsonl"
        self.environment = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}",
                                GITHUB_WORKSPACE=str(self.directory), RUNNER_TEMP=str(self.directory / "tmp"),
                                CI_MODULE="fixture", CI_VERSION="1.0", CI_ARCHITECTURE="amd64",
                                CI_EXECUTION_ARCHITECTURE="amd64", CI_CROSS_COMPILE="false",
                                ARM_TEST_EXECUTOR="/usr/local/bin/sonic-arm64",
                                TEST_CONTAINER_IMAGE="", SONIC_RUNNER_IMAGE_REFERENCE="fixture@sha256:" + "a" * 64,
                                CAPTURE=str(self.capture), FAIL_CHECK="0", GITHUB_ACTIONS="true", **ROOT_SECRETS)
        for name in DATED_SECRETS:
            self.environment.pop(name, None)
        self.executable("git", "#!/bin/sh\nexit 0\n")
        self.executable("sudo", textwrap.dedent("""\
            #!/bin/sh
            preserved=""
            while [ "${1#-}" != "$1" ]; do
                case "$1" in --preserve-env=*) preserved=${1#--preserve-env=};; esac
                shift
            done
            for name in DEBIAN_MIRROR_ROOT DEBIAN_SECURITY_MIRROR_ROOT DEBIAN_MIRROR_BASE_URL DEBIAN_SECURITY_MIRROR_BASE_URL GITHUB_ACTIONS; do
                case ",$preserved," in *,$name,*) ;; *) unset "$name";; esac
            done
            exec "$@"
            """))
        self.executable("python3", "#!/usr/bin/python3\n" + textwrap.dedent("""\
            import json, os, sys
            with open(os.environ['CAPTURE'], 'a') as log:
                log.write(json.dumps({'args': sys.argv[1:], 'github_actions': os.environ.get('GITHUB_ACTIONS'),
                    'secrets': [os.environ.get(name) for name in
                    ('DEBIAN_MIRROR_ROOT', 'DEBIAN_SECURITY_MIRROR_ROOT', 'DEBIAN_MIRROR_BASE_URL',
                     'DEBIAN_SECURITY_MIRROR_BASE_URL') if os.environ.get(name)]}) + '\\n')
            if 'check-artifacts' in sys.argv:
                raise SystemExit(int(os.environ['FAIL_CHECK']))
            """))

    def executable(self, name, contents):
        path = self.bin / name
        path.write_text(contents)
        path.chmod(0o755)

    def run_step(self, name):
        workflow = (WORKFLOWS / "registry-module.yml").read_text()
        return subprocess.run(["bash", "-c", script(workflow, name)], cwd=self.directory,
                              env=self.environment, capture_output=True, text=True)

    def test_module_build_uses_private_wrapper_without_secret_command_arguments(self):
        for architecture, cross in (("amd64", False), ("arm64", True)):
            with self.subTest(architecture=architecture, cross=cross):
                self.capture.unlink(missing_ok=True)
                self.environment.update(CI_ARCHITECTURE=architecture, CI_CROSS_COMPILE=str(cross).lower())
                result = self.run_step("Build and test through the registry")
                self.assertEqual(result.returncode, 0, result.stderr)
                command = json.loads(self.capture.read_text())
                self.assertEqual(command["args"][:2], ["ci/private_mirrors.py", "run"])
                self.assertIn("ci/registry_ci.py", command["args"])
                self.assertIn("--bazel-build-arg=--jobs=1", command["args"])
                self.assertIn("--bazel-startup-arg=--host_jvm_args=-Xmx2g", command["args"])
                self.assertEqual(command["secrets"], list(ROOT_SECRETS.values()))
                self.assertEqual(command["github_actions"], "true")
                self.assertNotIn("debian-fixture", " ".join(command["args"]))
                self.assertNotIn("security-fixture", " ".join(command["args"]))
                private_path = Path(command["args"][command["args"].index("--private-dir") + 1])
                artifact_path = Path(command["args"][command["args"].index("--artifacts") + 1])
                self.assertFalse(private_path.is_relative_to(artifact_path))
                self.assertEqual(command["args"][command["args"].index("--architecture") + 1], architecture)
                self.assertEqual("--cross-compile" in command["args"], cross)
                self.assertEqual("--test-executor" in command["args"], cross)
                if cross:
                    self.assertEqual(command["args"][command["args"].index("--test-executor") + 1],
                                     self.environment["ARM_TEST_EXECUTOR"])

    def test_legacy_module_helper_receives_only_dated_mirrors_through_sudo(self):
        self.environment.update(dict.fromkeys(ROOT_SECRETS, ""))
        self.environment.update(DATED_SECRETS)
        result = self.run_step("Build and test through the registry")
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(self.capture.read_text())
        self.assertEqual(command["secrets"], list(DATED_SECRETS.values()))
        for value in DATED_SECRETS.values():
            self.assertNotIn(value, " ".join(command["args"]))

    def test_only_successful_artifact_download_adds_absolute_agent_path(self):
        for status in ("success", "failure", "skipped", ""):
            with self.subTest(status=status):
                self.capture.unlink(missing_ok=True)
                self.environment["HTTP_AUDIT_READY"] = status
                result = self.run_step("Build and test through the registry")
                self.assertEqual(result.returncode, 0, result.stderr)
                args = json.loads(self.capture.read_text())["args"]
                self.assertEqual("--http-audit-jar" in args, status == "success")
                if status == "success":
                    self.assertEqual(args[args.index("--http-audit-jar") + 1],
                                     str(self.directory / "tmp/debian-http-audit/debian-http-audit.jar"))
                    self.assertLess(args.index("--http-audit-jar"), args.index("--"))

    def test_native_and_cross_suites_receive_the_optional_agent(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        for name, suite in (("Test planning and validation runner", "native"),
                            ("Test the cross compiler and ARM runtime", "cross")):
            for status in ("success", "skipped"):
                with self.subTest(suite=suite, status=status):
                    self.capture.unlink(missing_ok=True)
                    self.environment["HTTP_AUDIT_READY"] = status
                    result = subprocess.run(["bash", "-c", script(workflow, name)], cwd=self.directory,
                                            env=self.environment, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    args = json.loads(self.capture.read_text())["args"]
                    self.assertEqual(args[:2], ["ci/private_mirrors.py", "suite"])
                    self.assertEqual(args[-2:], ["--suite", suite])
                    self.assertEqual("--http-audit-jar" in args, status == "success")
                    if status == "success":
                        self.assertEqual(args[args.index("--http-audit-jar") + 1],
                                         str(self.directory / "tmp/debian-http-audit/debian-http-audit.jar"))

    def test_module_evidence_is_not_archived_after_failed_privacy_scan(self):
        for architecture, cross in (("amd64", False), ("arm64", True)):
            with self.subTest(architecture=architecture, cross=cross):
                self.capture.unlink(missing_ok=True)
                self.environment.update(CI_ARCHITECTURE=architecture, CI_CROSS_COMPILE=str(cross).lower())
                self.environment["FAIL_CHECK"] = "1"
                (self.directory / "ci").mkdir(exist_ok=True)
                (self.directory / "ci/archive_artifacts.sh").write_text("touch archive-was-called\n")
                result = self.run_step("Archive module validation results")
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((self.directory / "archive-was-called").exists())
                command = json.loads(self.capture.read_text())
                self.assertEqual(command["args"][:2], ["ci/private_mirrors.py", "check-artifacts"])
                self.assertEqual(command["secrets"], list(ROOT_SECRETS.values()))
                self.assertEqual(command["github_actions"], "true")

    def test_manual_probe_preserves_production_environment_and_user_owned_evidence_directory(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        result = subprocess.run(["bash", "-c", script(workflow, "Validate private Debian mirrors from the Trixie runner")],
                                cwd=self.directory, env=self.environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(self.capture.read_text())
        self.assertEqual(command["args"][:2], ["ci/private_mirrors.py", "probe"])
        self.assertEqual(command["secrets"], list(ROOT_SECRETS.values()))
        self.assertEqual(command["github_actions"], "true")
        artifact_path = Path(command["args"][command["args"].index("--artifacts") + 1])
        self.assertEqual(artifact_path, self.directory / "runner-ci-artifacts/private-mirror-probe")
        self.assertTrue(artifact_path.is_dir())
        self.assertEqual(artifact_path.stat().st_uid, os.getuid())


if __name__ == "__main__":
    unittest.main()
