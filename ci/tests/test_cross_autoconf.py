"""Check cross configure identity without changing native or explicit settings."""

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "cross_autoconf_tested", Path(__file__).resolve().parents[1] / "cross_autoconf.py")
autoconf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(autoconf)


class CrossAutoconfTests(unittest.TestCase):
    def test_shell_guard_uses_compiler_identity_and_preserves_native_or_explicit_aliases(self):
        script = '''
uname() { printf '%s\\n' "$fixture_machine"; }
compiler() {
    test "$1" = --fixture-flag && shift
    test "$1" = -dumpmachine || return 2
    test "$fixture_target" != failed || return 1
    printf '%s\\n' "$fixture_target"
}
. "$1"
printf 'host=%s\\nbuild=%s\\nprefix=%s\\ncross=%s\\n' \
    "${host_alias-}" "${build_alias-}" "${ac_tool_prefix-}" "$cross_compiling"
'''
        unchanged = {"host": "", "build": "", "prefix": "", "cross": "no"}
        cases = [
            ({}, {"host": "aarch64-linux-gnu", "build": "x86_64-linux-gnu",
                  "prefix": "aarch64-linux-gnu-", "cross": "yes"}),
            ({"fixture_target": "x86_64-linux-gnu"}, unchanged),
            ({"fixture_machine": "aarch64"}, unchanged),
            ({"fixture_target": "failed"}, unchanged),
            ({"CC": ""}, unchanged),
            ({"host_alias": "explicit-host"}, {**unchanged, "host": "explicit-host"}),
            ({"build_alias": "explicit-build"}, {**unchanged, "build": "explicit-build"}),
            ({"host_alias": "explicit-host", "build_alias": "explicit-build", "cross_compiling": "maybe"},
             {**unchanged, "host": "explicit-host", "build": "explicit-build", "cross": "maybe"}),
        ]
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                environment = {**os.environ, "fixture_machine": "x86_64",
                               "fixture_target": "aarch64-linux-gnu", "CC": "compiler --fixture-flag",
                               "host_alias": "", "build_alias": "", "ac_tool_prefix": "",
                               "cross_compiling": "no", **overrides}
                result = subprocess.run(["/bin/sh", "-c", script, "test-site",
                                         str(Path(autoconf.__file__).with_suffix(".site"))],
                                        env=environment, text=True, capture_output=True, check=True)
                self.assertEqual(dict(line.split("=", 1) for line in result.stdout.splitlines()), expected)

    def test_readonly_site_mount_retains_exact_source_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            flags = ["--jobs=1"]
            receipt = autoconf.prepare(root, root, flags)
            site = Path(receipt["site_path"])
            self.assertEqual(site.read_bytes(), Path(autoconf.__file__).with_suffix(".site").read_bytes())
            self.assertEqual((root / "cross-autoconf.site").read_bytes(), site.read_bytes())
            self.assertEqual(hashlib.sha256(site.read_bytes()).hexdigest(), receipt["site_sha256"])
            self.assertEqual(site.stat().st_mode & 0o777, 0o444)
            self.assertIn(f"--sandbox_add_mount_pair={site.parent}:{site.parent}", flags)
            self.assertIn(f"--action_env=CONFIG_SITE={site}", flags)
            self.assertEqual(json.loads((root / "cross-autoconf.json").read_text()), receipt)
            site.chmod(0o644)
            site.write_text("changed source")
            with self.assertRaisesRegex(ValueError, "content-addressed"):
                autoconf.prepare(root, root, [])

    def test_explicit_action_environment_keeps_its_value_or_inheritance(self):
        for caller in (["--action_env=CONFIG_SITE=/custom/site"], ["--action_env=CONFIG_SITE"],
                       ["--action_env", "CONFIG_SITE=/custom/site"], ["--action_env=CONFIG_SITE="]):
            with self.subTest(caller=caller), tempfile.TemporaryDirectory() as temporary:
                flags = caller.copy()
                receipt = autoconf.prepare(Path(temporary), Path(temporary), flags)
                self.assertFalse(receipt["enabled"])
                self.assertEqual(flags, caller)
                self.assertFalse((Path(temporary) / "cross-autoconf").exists())
