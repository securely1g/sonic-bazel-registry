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
SECRETS = ("DEBIAN_MIRROR_BASE_URL", "DEBIAN_SECURITY_MIRROR_BASE_URL")
TRIXIE = ["self-hosted", "Linux", "X64", "debian-trixie-container"]


def expression_value(expression, context):
    """Evaluate the workflow's small Boolean/context expression subset."""
    expression = re.sub(r"\b(?:github|matrix|inputs|secrets|steps|runner)(?:\.[A-Za-z_][A-Za-z_0-9]*)+",
                        lambda match: f"lookup({match[0]!r})", expression)
    expression = expression.replace("&&", " and ").replace("||", " or ")
    expression = re.sub(r"!(?!=)", "not ", expression)
    return eval(expression.strip(), {"__builtins__": {}}, {
        "lookup": lambda key: context.get(key, ""),
        "contains": lambda values, value: value in values,
        "fromJSON": json.loads,
        "always": lambda: True,
        "cancelled": lambda: False,
    })


def step(text, name):
    return text.split(f"      - name: {name}\n", 1)[1].split("      - ", 1)[0]


def script(text, name):
    return textwrap.dedent(step(text, name).split("        run: |\n", 1)[1])


class PrivateMirrorSecretBoundaryTest(unittest.TestCase):
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
        for filename in ("registry-ci.yml", "registry-module.yml"):
            workflow = (WORKFLOWS / filename).read_text()
            for secret in SECRETS:
                expressions = re.findall(rf"^\s+{secret}: \$\{{\{{ (.*) \}}\}}$", workflow, re.M)
                self.assertTrue(expressions, filename)
                for expression in expressions:
                    for event, head, actor, runner, expected in (
                        ("pull_request", "owner/repo", "maintainer", TRIXIE, "fixture-value"),
                        ("push", "", "maintainer", TRIXIE, "fixture-value"),
                        ("workflow_dispatch", "", "maintainer", TRIXIE, "fixture-value"),
                        ("pull_request", "fork/repo", "contributor", TRIXIE, ""),
                        ("pull_request", "owner/repo", "dependabot[bot]", TRIXIE, ""),
                        ("pull_request_target", "owner/repo", "maintainer", TRIXIE, ""),
                        ("workflow_run", "owner/repo", "maintainer", TRIXIE, ""),
                        ("push", "", "maintainer", ["ubuntu-24.04-arm"], ""),
                        ("push", "", "maintainer", ["self-hosted", "Linux", "X64"], ""),
                        ("push", "", "maintainer", ["debian-trixie-container"], ""),
                    ):
                        # The cross fixture has a fixed Trixie label set in
                        # runs-on. Only that worker and hosted isolation apply.
                        fixed = "runner.environment" in expression
                        if fixed and "self-hosted" in runner and runner != TRIXIE:
                            continue
                        context = {
                            "github.event_name": event,
                            "github.actor": actor,
                            "github.repository": "owner/repo",
                            "github.event.pull_request.head.repo.full_name": head,
                            "matrix.runner": runner,
                            "runner.environment": "self-hosted" if "self-hosted" in runner else "github-hosted",
                            "inputs.runner": json.dumps(runner),
                            f"secrets.{secret}": "fixture-value",
                        }
                        with self.subTest(filename=filename, event=event, head=head,
                                          actor=actor, runner=runner, secret=secret):
                            self.assertEqual(expression_value(expression, context), expected)
                            context[f"secrets.{secret}"] = ""
                            self.assertEqual(expression_value(expression, context), "")

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
        local_job = workflow.split("  modules_local:\n", 1)[1].split("  modules_hosted_arm:\n", 1)[0]
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
                               f"secrets.{secret}": "fixture-value"}
                    with self.subTest(secret=secret, architecture=architecture, head=head, actor=actor):
                        self.assertEqual(expression_value(expression, context), expected)

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
                                CAPTURE=str(self.capture), FAIL_CHECK="0", GITHUB_ACTIONS="true",
                                DEBIAN_MIRROR_BASE_URL="debian-fixture",
                                DEBIAN_SECURITY_MIRROR_BASE_URL="security-fixture")
        self.executable("git", "#!/bin/sh\nexit 0\n")
        self.executable("sudo", textwrap.dedent("""\
            #!/bin/sh
            preserved=""
            while [ "${1#-}" != "$1" ]; do
                case "$1" in --preserve-env=*) preserved=${1#--preserve-env=};; esac
                shift
            done
            for name in DEBIAN_MIRROR_BASE_URL DEBIAN_SECURITY_MIRROR_BASE_URL GITHUB_ACTIONS; do
                case ",$preserved," in *,$name,*) ;; *) unset "$name";; esac
            done
            exec "$@"
            """))
        self.executable("python3", "#!/usr/bin/python3\n" + textwrap.dedent("""\
            import json, os, sys
            with open(os.environ['CAPTURE'], 'a') as log:
                log.write(json.dumps({'args': sys.argv[1:], 'github_actions': os.environ.get('GITHUB_ACTIONS'),
                    'secrets': [os.environ.get(name) for name in
                    ('DEBIAN_MIRROR_BASE_URL', 'DEBIAN_SECURITY_MIRROR_BASE_URL')]}) + '\\n')
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
                self.assertEqual(command["secrets"], ["debian-fixture", "security-fixture"])
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
                self.assertEqual(command["secrets"], ["debian-fixture", "security-fixture"])
                self.assertEqual(command["github_actions"], "true")

    def test_manual_probe_preserves_production_environment_and_user_owned_evidence_directory(self):
        workflow = (WORKFLOWS / "registry-ci.yml").read_text()
        result = subprocess.run(["bash", "-c", script(workflow, "Validate private Debian mirrors from the Trixie runner")],
                                cwd=self.directory, env=self.environment, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        command = json.loads(self.capture.read_text())
        self.assertEqual(command["args"][:2], ["ci/private_mirrors.py", "probe"])
        self.assertEqual(command["secrets"], ["debian-fixture", "security-fixture"])
        self.assertEqual(command["github_actions"], "true")
        artifact_path = Path(command["args"][command["args"].index("--artifacts") + 1])
        self.assertEqual(artifact_path, self.directory / "runner-ci-artifacts/private-mirror-probe")
        self.assertTrue(artifact_path.is_dir())
        self.assertEqual(artifact_path.stat().st_uid, os.getuid())


if __name__ == "__main__":
    unittest.main()
