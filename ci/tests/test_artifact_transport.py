"""Exercise the archive uploaded by native registry validation jobs."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ARCHIVER = Path(__file__).resolve().parents[1] / "archive_artifacts.sh"


class ArtifactTransportTests(unittest.TestCase):
    def test_linux_names_modes_links_and_diagnostics_survive_transport(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            files = {
                "outputs/usr/share/man/man3/Text::CharWidth.3pm.gz": b"manual",
                "outputs/usr/include/xt_CONNMARK.h": b"uppercase header",
                "outputs/usr/include/xt_connmark.h": b"lowercase header",
                "outputs/bin/tool": b"#!/bin/sh\nexit 0\n",
                "outputs.json": b'{"target": "outputs/bin/tool"}\n',
                "build.log": b"build log\n",
                "testlogs/test/test.log": b"test log\n",
                "failed-actions/action:stderr.log": b"compiler diagnostic\n",
                ".hidden-evidence": b"hidden evidence\n",
            }
            for name, content in files.items():
                path = evidence / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
            (evidence / "outputs/bin/tool").chmod(0o755)
            (evidence / "outputs/bin/tool-link").symlink_to("tool")
            archive = root / "registry-ci-evidence.tar"
            subprocess.run(["bash", str(ARCHIVER), str(evidence), str(archive)], check=True)
            # The upload service sees one ordinary filename; case-sensitive
            # paths and forbidden ':' characters remain inside the TAR.
            self.assertTrue(archive.is_file())
            restored = root / "restored"
            restored.mkdir()
            subprocess.run(["tar", "-xpf", str(archive), "-C", str(restored)], check=True)
            for name, content in files.items():
                self.assertEqual((restored / name).read_bytes(), content)
                self.assertEqual((evidence / name).read_bytes(), content)
            self.assertEqual((restored / "outputs/bin/tool").stat().st_mode & 0o777, 0o755)
            self.assertEqual(os.readlink(restored / "outputs/bin/tool-link"), "tool")

    def test_archive_cannot_include_itself(self):
        with tempfile.TemporaryDirectory() as temporary:
            evidence = Path(temporary)
            archive = evidence / "evidence.tar"
            result = subprocess.run(["bash", str(ARCHIVER), str(evidence), str(archive)],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("outside the input directory", result.stderr)
            self.assertFalse(archive.exists())

    def test_tar_failure_is_not_uploaded_as_a_partial_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence = root / "evidence"
            evidence.mkdir()
            commands = root / "commands"
            commands.mkdir()
            tar = commands / "tar"
            tar.write_text("#!/bin/sh\nexit 42\n")
            tar.chmod(0o755)
            archive = root / "evidence.tar"
            result = subprocess.run(["bash", str(ARCHIVER), str(evidence), str(archive)],
                                    env={**os.environ, "PATH": str(commands) + os.pathsep + os.environ["PATH"]})
            self.assertEqual(result.returncode, 42)
            self.assertFalse(archive.exists())
            self.assertEqual(list(root.glob("evidence.tar.*")), [])

    def test_setup_failure_without_evidence_does_not_create_an_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / "evidence.tar"
            subprocess.run(["bash", str(ARCHIVER), str(root / "absent"), str(archive)], check=True)
            self.assertFalse(archive.exists())


if __name__ == "__main__":
    unittest.main()
