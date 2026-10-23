"""Exercise artifact collection with actual Bazel tree outputs and build events."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "registry_ci_artifact_integration", Path(__file__).resolve().parents[1] / "registry_ci.py"
)
assert SPEC is not None and SPEC.loader is not None
registry_ci = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry_ci
SPEC.loader.exec_module(registry_ci)


RULE = '''
def _artifact_impl(ctx):
    tree = ctx.actions.declare_directory("payload")
    runtime = ctx.actions.declare_file("runtime.tar")
    debug = ctx.actions.declare_file("runtime.debug.tar")
    ctx.actions.run_shell(
        outputs = [tree, runtime, debug],
        arguments = [tree.path, runtime.path, debug.path],
        command = """
set -eu
mkdir -p "$1/empty"
printf 'perl manual\\n' > "$1/Text::CharWidth.3pm.gz"
printf 'UPPER header\\n' > "$1/xt_CONNMARK.h"
printf 'lower header\\n' > "$1/xt_connmark.h"
printf '#!/bin/sh\\nprintf fixture\\\\n\\n' > "$1/tool"
chmod 751 "$1/tool"
ln -s tool "$1/alias"
tar -cf "$2" -C "$1" tool
tar -cf "$3" -C "$1" xt_CONNMARK.h
""",
    )
    return [DefaultInfo(files = depset([tree, runtime, debug]))]

artifact = rule(implementation = _artifact_impl)
'''


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL"),
                     "set REGISTRY_CI_TEST_BAZEL to run the real Bazel artifact fixture")
class BazelArtifactIntegrationTest(unittest.TestCase):
    def test_genuine_bep_preserves_directory_and_adjacent_tar_outputs(self):
        with tempfile.TemporaryDirectory(prefix="registry-bazel-artifacts-") as temporary:
            work = Path(temporary)
            consumer, artifacts = work / "consumer", work / "artifacts"
            consumer.mkdir()
            artifacts.mkdir()
            producer = consumer / "producer"
            producer.mkdir()
            (consumer / "MODULE.bazel").write_text(
                'module(name = "fixture_consumer")\n'
                'bazel_dep(name = "artifact_fixture", version = "1.0.0")\n'
                'local_path_override(module_name = "artifact_fixture", path = "producer")\n'
            )
            (consumer / "BUILD.bazel").write_text('platform(name = "fixture_platform")\n')
            (producer / "MODULE.bazel").write_text('module(name = "artifact_fixture", version = "1.0.0")\n')
            (producer / "artifact.bzl").write_text(RULE)
            (producer / "BUILD.bazel").write_text(
                'load(":artifact.bzl", "artifact")\n'
                'package(default_visibility = ["//visibility:public"])\n'
                'artifact(name = "artifact")\n'
                'alias(name = "artifact_alias", actual = ":artifact")\n'
            )
            prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--batch", "--ignore_all_rc_files",
                      "--output_user_root=" + str(work / "bazel")]
            flags = ["--incompatible_autoload_externally=", "--lockfile_mode=off",
                     "--host_platform=//:fixture_platform", "--platforms=//:fixture_platform"]
            labels = ["@artifact_fixture//:artifact", "@artifact_fixture//:artifact_alias"]
            bep = artifacts / "build-events.jsonl"
            try:
                with (artifacts / "build.log").open("w") as log:
                    build = subprocess.run(
                        prefix + ["build", *flags, "--build_event_json_file=" + str(bep), *labels],
                        cwd=consumer, stdout=log, stderr=subprocess.STDOUT, timeout=180,
                    )
                self.assertEqual(build.returncode, 0, (artifacts / "build.log").read_text()[-10000:])
                execution_root = Path(subprocess.check_output(
                    prefix + ["info", *flags, "execution_root"], cwd=consumer, text=True,
                    stderr=subprocess.PIPE, timeout=120,
                ).strip())
                declared = registry_ci.query_output_trees(prefix, flags, labels, consumer, artifacts)
                self.assertEqual(set(declared), set(labels))
                self.assertEqual(len(declared[labels[0]]), 1)
                self.assertEqual(declared[labels[0]], declared[labels[1]])
                tree_root = declared[labels[0]][0]
                events = [json.loads(line) for line in bep.read_text().splitlines()]
                reported = ["/".join([*item.get("pathPrefix", []), item["name"]])
                            for event in events for item in event.get("namedSetOfFiles", {}).get("files", [])]
                # This is the production failure: Bazel reports children rather
                # than a directory URI. A fabricated directory event misses it.
                self.assertIn(tree_root + "/Text::CharWidth.3pm.gz", reported)
                self.assertNotIn(tree_root, reported)
                registry_ci.collect_outputs(bep, labels, work, artifacts,
                                            declared_trees=declared, execution_root=execution_root)
                index = json.loads((artifacts / "outputs.json").read_text())
                self.assertEqual(index[labels[0]], index[labels[1]])
                records = index[labels[0]]
                self.assertEqual(len(records), 3)
                trees = [record for record in records if record.get("type") == "tree_archive"]
                self.assertEqual(len(trees), 1)
                tree = trees[0]
                self.assertEqual(tree["root"], tree_root)
                restored = work / "restored"
                restored.mkdir()
                source_mode = (execution_root / tree_root / "tool").stat().st_mode & 0o777
                with tarfile.open(artifacts / tree["path"]) as archive:
                    self.assertEqual(archive.getmember(tree_root + "/tool").mode, source_mode)
                    archive.extractall(restored, filter="data")
                payload = restored / tree_root
                self.assertEqual((payload / "Text::CharWidth.3pm.gz").read_bytes(), b"perl manual\n")
                self.assertEqual((payload / "xt_CONNMARK.h").read_bytes(), b"UPPER header\n")
                self.assertEqual((payload / "xt_connmark.h").read_bytes(), b"lower header\n")
                # Bazel makes outputs read-only, and Python's safe extraction
                # filter restores owner write access. Check exact archive modes
                # above and retained executability after safe extraction here.
                self.assertTrue(source_mode & 0o100)
                self.assertEqual((payload / "tool").stat().st_mode & 0o111, source_mode & 0o111)
                self.assertTrue((payload / "alias").is_symlink())
                self.assertEqual((payload / "alias").readlink(), Path("tool"))
                self.assertEqual((payload / "alias").read_bytes(), (payload / "tool").read_bytes())
                self.assertTrue((payload / "empty").is_dir())
                self.assertEqual(list((payload / "empty").iterdir()), [])
                ordinary = [record for record in records if record.get("type") != "tree_archive"]
                self.assertEqual({Path(record["path"]).name for record in ordinary},
                                 {"runtime.tar", "runtime.debug.tar"})
                for record in records:
                    data = (artifacts / record["path"]).read_bytes()
                    self.assertEqual(record["size"], len(data))
                    self.assertEqual(record["sha256"], hashlib.sha256(data).hexdigest())
                for record in ordinary:
                    logical = Path(record["path"]).relative_to("outputs")
                    self.assertEqual((artifacts / record["path"]).read_bytes(),
                                     (execution_root / logical).read_bytes())
                uploaded_names = [path.relative_to(artifacts).as_posix()
                                  for path in artifacts.rglob("*") if path.is_file()]
                self.assertFalse(any(":" in name for name in uploaded_names))
                self.assertEqual(len(uploaded_names), len({name.casefold() for name in uploaded_names}))
            finally:
                destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                if destination:
                    shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
