"""Regression evidence for downloads outside Bazel's main build/test events."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CI = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CI))
import debian_downloads


class DownloadEvidenceTest(unittest.TestCase):
    def test_snapshot_hash_urls_report_the_content_address(self):
        path = "/file/" + "a" * 40
        self.assertEqual(debian_downloads.location("https://snapshot.debian.org" + path),
                         ("public", "content-addressed", path))
        self.assertEqual(debian_downloads.location("[private-mirror]" + path),
                         ("private", "content-addressed", path))

    def test_launcher_preserves_custom_config_and_existing_event_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / "bazel"
            fake.write_text("#!/usr/bin/python3\nimport sys,json\nprint(json.dumps(sys.argv[1:]))\n")
            fake.chmod(0o755)
            prefix = [sys.executable, str(CI / "debian_downloads.py"), str(fake),
                      str(root / "artifacts"), str(root), str(root / "unused-map")]
            for cfg, managed in (([], True), (["--downloader_config=" + str(CI / "source_mirrors.cfg")], True),
                                 (["--downloader_config=custom.cfg"], False)):
                command = ["--output_base", "test", "fetch", *cfg, "--build_event_json_file=existing",
                           "--", "--downloader_config=literal"]
                args = json.loads(subprocess.check_output([*prefix, *command]))
                self.assertEqual(f"--experimental_downloader_config={root / 'downloader.cfg'}" in args, managed)
                self.assertEqual(args[-2:], command[-2:])
                self.assertEqual(args.count("--build_event_json_file=existing"), 1)

    def test_preparation_failure_retains_debian_fetches_and_original_status(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            output = work / "artifacts"
            table = work / "map.json"
            table.write_text(json.dumps({"mirrors": {"snapshot": "https://secret.example/private-path/archive/debian/date/"}}))
            urls = [("https://secret.example/private-path/archive/debian/date/dists/trixie/Packages.xz", True),
                    ("https://snapshot.debian.org/archive/debian/date/dists/trixie/Packages.bz2", False),
                    ("https://deb.debian.org/debian/pool/main/f/foo/foo_1.orig.tar.gz", True),
                    ("https://example.net/unrelated.tar.gz", True)]
            fake = work / "bazel"
            fake.write_text("#!/usr/bin/python3\nimport sys,json\nfrom pathlib import Path\n"
                            "p=next(a.split('=',1)[1] for a in sys.argv if a.startswith('--build_event_json_file='))\n"
                            "assert sys.argv[-2:] == ['--', 'literal-argument']\n"
                            "assert any(a.endswith('/downloader.cfg') for a in sys.argv)\n"
                            f"events=[{{'id':{{'fetch':{{'url':u}}}}, 'fetch':{{'success':ok}}}} for u,ok in {urls!r}]\n"
                            "Path(p).write_text(''.join(json.dumps(e)+'\\n' for e in events))\nsys.exit(37)\n")
            fake.chmod(0o755)
            result = subprocess.run([sys.executable, str(CI / "debian_downloads.py"), str(fake),
                                     str(output), str(work), str(table), "--batch", "--output_base", "run",
                                     "fetch", "--", "literal-argument"])
            self.assertEqual(result.returncode, 37)
            event_file, = (output / "download-traces").glob("*-events.jsonl")
            self.assertTrue(event_file.name.startswith("fetch-"))
            text = event_file.read_text()
            self.assertNotIn("secret.example", text)
            self.assertNotIn("private-path", text)
            self.assertNotIn("unrelated.tar.gz", text)
            (output / "test-runtime.apt.log").write_text(
                "Get:1 file:/tmp/private-map.mirrors Mirrorlist [185 B]\n"
                "Get:2 [private-mirror] trixie InRelease [140 kB]\n"
                "Get:3 [private-mirror] trixie/main amd64 libbar amd64 4.1 [50.8 kB]\n"
                "Get:4 https://snapshot.debian.org/archive/debian/date/ trixie/main amd64 libfoo amd64 1.2 [12 kB]\n")
            report = debian_downloads.report(output)
            self.assertEqual({(x["kind"], x["object"]) for x in report["exceptions"]},
                             {("binary", "libfoo amd64 1.2"), ("source", "/debian/pool/main/f/foo/foo_1.orig.tar.gz")})
            self.assertEqual(report["incomplete_traces"], ["download-traces/" + event_file.name])
            self.assertEqual(report["failed_public_candidates"][0]["object"],
                             "/archive/debian/date/dists/trixie/Packages.bz2")
            self.assertIn({"origin": "private", "kind": "binary", "outcome": "APT Get", "count": 1}, report["counts"])
            self.assertIn({"origin": "private", "kind": "metadata", "outcome": "APT Get", "count": 1}, report["counts"])
            self.assertIn({"origin": "private", "kind": "index", "outcome": "successful candidate", "count": 1},
                          report["counts"])
            self.assertIn({"origin": "public", "kind": "index", "outcome": "failed candidate", "count": 1},
                          report["counts"])


if __name__ == "__main__":
    unittest.main()
