"""Keep Linux tree contents usable after artifact download and relocation."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location(
    "registry_ci_preservation", Path(__file__).resolve().parents[1] / "registry_ci.py"
)
assert SPEC is not None and SPEC.loader is not None
registry_ci = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = registry_ci
SPEC.loader.exec_module(registry_ci)


class ArtifactPreservationTests(unittest.TestCase):
    label = "@fixture//:artifact"
    tree_path = "bazel-out/bin/tree"

    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="registry-preservation-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.work = self.root / "work"
        self.execution_root = self.work / "execroot"
        self.tree = self.execution_root / self.tree_path
        self.tree.mkdir(parents=True)
        self.artifacts = self.root / "artifacts"

    def collect(self, additional_files: list[dict] | None = None) -> tuple[dict, Path]:
        events = [
            {"id": {"namedSet": {"id": "outputs"}},
             "namedSetOfFiles": {"files": additional_files or []}},
            {"id": {"targetCompleted": {"label": self.label}},
             "completed": {"success": True, "outputGroup": [
                 {"name": "default", "fileSets": [{"id": "outputs"}]},
             ]}},
        ]
        bep = self.root / "build-events.jsonl"
        bep.write_text("".join(json.dumps(event) + "\n" for event in events))
        registry_ci.collect_outputs(
            bep, [self.label], self.work, self.artifacts,
            declared_trees={self.label: [self.tree_path]}, execution_root=self.execution_root,
        )
        index = json.loads((self.artifacts / "outputs.json").read_text())
        trees = [record for record in index[self.label] if record.get("type") == "tree_archive"]
        self.assertEqual(len(trees), 1)
        self.assertEqual(trees[0]["root"], self.tree_path)
        return index, self.artifacts / trees[0]["path"]

    def restore(self, archive_path: Path) -> Path:
        restored = self.root / "restored"
        with tarfile.open(archive_path) as archive:
            archive.extractall(restored, filter="data")
        return restored / self.tree_path

    def test_directory_modes_names_and_internal_file_and_directory_links(self) -> None:
        self.tree.chmod(0o750)
        for name in ("Text::CharWidth.3pm.gz", "xt_TCPMSS.h", "xt_tcpmss.h", "tool"):
            (self.tree / name).write_bytes(name.encode())
        (self.tree / "tool").chmod(0o751)
        (self.tree / "private").mkdir(mode=0o700)
        readonly = self.tree / "read-only"
        readonly.mkdir()
        (readonly / "file").write_bytes(b"read-only payload")
        readonly.chmod(0o500)
        self.addCleanup(readonly.chmod, 0o700)
        (self.tree / "tool-link").symlink_to("tool")
        (self.tree / "directory-link").symlink_to("private")

        _, archive_path = self.collect()
        with tarfile.open(archive_path) as archive:
            for suffix, mode in (("", 0o750), ("/private", 0o700),
                                 ("/read-only", 0o500), ("/tool", 0o751)):
                self.assertEqual(archive.getmember(self.tree_path + suffix).mode, mode)
            for name in ("Text::CharWidth.3pm.gz", "xt_TCPMSS.h", "xt_tcpmss.h"):
                self.assertEqual(archive.extractfile(self.tree_path + "/" + name).read(), name.encode())
            self.assertEqual(archive.extractfile(self.tree_path + "/read-only/file").read(),
                             b"read-only payload")
            for name, target in (("tool-link", "tool"), ("directory-link", "private")):
                member = archive.getmember(self.tree_path + "/" + name)
                self.assertTrue(member.issym())
                self.assertEqual(member.linkname, target)
            self.assertTrue(archive.getmember(self.tree_path + "/private").isdir())
        # Archiving must not alter the original build-output permissions.
        self.assertEqual(readonly.stat().st_mode & 0o777, 0o500)
        restored = self.restore(archive_path)
        self.assertEqual((restored / "tool-link").read_bytes(), b"tool")
        self.assertEqual((restored / "directory-link").readlink(), Path("private"))
        self.assertEqual(list((restored / "directory-link").iterdir()), [])

    def test_standalone_absolute_and_outside_tree_links_keep_their_payloads(self) -> None:
        (self.work / "runtime.tar").write_bytes(b"runtime")
        generated = self.work / "generated"
        generated.mkdir()
        standalone = generated / "linked.tar"
        standalone.symlink_to("../runtime.tar")
        (self.tree / "bin").mkdir()
        (self.tree / "bin/tool").write_bytes(b"tool")
        (self.tree / "relative").symlink_to("bin/tool")
        (self.tree / "absolute").symlink_to(self.tree / "bin/tool")
        (self.tree.parent / "debug.tar").write_bytes(b"debug")
        (self.tree / "outside").symlink_to("../debug.tar")

        index, archive_path = self.collect([{
            "name": "standalone.tar", "pathPrefix": ["bazel-out", "bin"],
            "uri": standalone.as_uri(),
        }])
        ordinary = [record for record in index[self.label] if record.get("type") != "tree_archive"]
        self.assertEqual(len(ordinary), 1)
        retained = self.artifacts / ordinary[0]["path"]
        self.assertFalse(retained.is_symlink())
        self.assertEqual(retained.read_bytes(), b"runtime")
        restored = self.restore(archive_path)
        self.assertTrue((restored / "relative").is_symlink())
        self.assertEqual((restored / "relative").read_bytes(), b"tool")
        for name, expected in (("absolute", b"tool"), ("outside", b"debug")):
            self.assertFalse((restored / name).is_symlink())
            self.assertEqual((restored / name).read_bytes(), expected)

    def test_parent_after_absolute_directory_link_uses_original_target(self) -> None:
        (self.tree / "sub/inner").mkdir(parents=True)
        (self.tree / "sub/value").write_bytes(b"original target")
        (self.tree / "value").write_bytes(b"wrong target after relocation")
        (self.tree / "absolute-directory").symlink_to(self.tree / "sub/inner")
        (self.tree / "through-absolute").symlink_to("absolute-directory/../value")
        self.assertEqual((self.tree / "through-absolute").read_bytes(), b"original target")

        _, archive_path = self.collect()
        restored = self.restore(archive_path)
        self.assertFalse((restored / "through-absolute").is_symlink())
        self.assertEqual((restored / "through-absolute").read_bytes(), b"original target")

    def test_mixed_link_chain_keeps_target_after_absolute_hop_is_materialized(self) -> None:
        (self.tree / "nested/inner").mkdir(parents=True)
        (self.tree / "inner").mkdir()
        (self.tree / "payload").write_bytes(b"correct payload")
        (self.tree / "nested/payload").write_bytes(b"wrong payload after relocation")
        (self.tree / "safe").symlink_to("nested/inner")
        (self.tree / "nested/hop").symlink_to(self.tree / "inner")
        (self.tree / "probe").symlink_to("safe/../hop/../payload")
        self.assertEqual((self.tree / "probe").read_bytes(), b"correct payload")

        _, archive_path = self.collect()
        restored = self.restore(archive_path)
        self.assertTrue((restored / "safe").is_symlink())
        self.assertFalse((restored / "nested/hop").is_symlink())
        self.assertFalse((restored / "probe").is_symlink())
        self.assertEqual((restored / "probe").read_bytes(), b"correct payload")

    def test_symlink_loop_is_a_registry_error_without_a_completed_archive(self) -> None:
        (self.tree / "first").symlink_to("second")
        (self.tree / "second").symlink_to("first")
        with self.assertRaises(registry_ci.RegistryError):
            self.collect()
        self.assertEqual(list((self.artifacts / "outputs/trees").iterdir()), [])

    def test_outside_workspace_link_is_rejected_without_a_completed_archive(self) -> None:
        outside = self.root / "outside"
        outside.write_bytes(b"not a build input")
        (self.tree / "escape").symlink_to(outside)
        with self.assertRaisesRegex(registry_ci.RegistryError, "escapes work-dir"):
            self.collect()
        self.assertEqual(list((self.artifacts / "outputs/trees").iterdir()), [])


if __name__ == "__main__":
    unittest.main()
