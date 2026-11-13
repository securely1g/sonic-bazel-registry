"""A snapshot rollover changes reviewed data, never the mirror secrets or code."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from test_private_mirrors import MIRRORS, ROOT, candidates


ROOTS = {key: f"https://stable-mirror.example.test/archive/{archive}/"
         for key, archive in MIRRORS.MIRROR_ROOTS}
OLD = "20200102T030405Z"
NEW = "20300203T040506Z"


def payload(stage, archive):
    return f"{archive} reviewed probe bytes, generation {stage}\n".encode()


def manifest(stage=0):
    result = {}
    for _key, archive in MIRRORS.MIRROR_ROOTS:
        suite = "trixie" if archive == "debian" else "trixie-security"
        prefix = "pool/main" if archive == "debian" else "pool/updates/main"
        result[archive] = {
            "current": OLD,
            "probe": {"path": f"{prefix}/f/fixture/fixture_1_amd64.deb",
                      "sha256": hashlib.sha256(payload(0, archive)).hexdigest()},
            "snapshots": {OLD: {suite: {"Packages": ["", ".gz", ".xz"],
                                       "Contents": ["", ".gz"]}}},
        }
        if stage:
            result[archive]["current"] = NEW
            result[archive]["probe"] = {
                "path": f"{prefix}/f/fixture/fixture_2_arm64.deb",
                "sha256": hashlib.sha256(payload(1, archive)).hexdigest(),
            }
            result[archive]["snapshots"][NEW] = {
                suite: {"Packages": [".xz"], "Contents": ["", ".xz"]},
            }
    return MIRRORS.validate_manifest(result)



class DebianSnapshotRolloverTest(unittest.TestCase):
    def test_dated_inputs_and_apt_keep_history_after_current_changes(self):
        stable = MIRRORS.selected_mirrors(ROOTS)
        for stage in (0, 1):
            reviewed = manifest(stage)
            config = MIRRORS.configuration("", stable, manifest=reviewed)
            apt = MIRRORS.apt_mirror_map(stable, reviewed)
            for key, archive in MIRRORS.MIRROR_ROOTS:
                path = reviewed[archive]["probe"]["path"]
                for date in reviewed[archive]["snapshots"]:
                    base = f"https://snapshot.debian.org/archive/{archive}/{date}"
                    self.assertEqual(apt[base], stable[key] + date + "/")
                    for host in ("snapshot.debian.org", "snapshot-cloudflare.debian.org"):
                        dated = f"https://{host}/archive/{archive}/{date}/{path}"
                        self.assertEqual(candidates(config, dated), [stable[key] + date + "/" + path, dated])
                unknown = f"https://snapshot.debian.org/archive/{archive}/19990101T000000Z"
                self.assertNotIn(unknown, apt)
            self.assertEqual(stable, ROOTS)

    def test_signed_packages_and_contents_formats_change_only_for_new_date(self):
        reviewed = manifest(1)
        for archive in reviewed.values():
            for formats in archive["snapshots"][NEW].values():
                formats["Packages"] = [".xz", ".zst", ".future1"]
                formats["Contents"] = ["", ".xz", ".lz4"]
        config = MIRRORS.configuration("", ROOTS, manifest=reviewed)
        for key, archive in MIRRORS.MIRROR_ROOTS:
            for date, suites in reviewed[archive]["snapshots"].items():
                for suite, formats in suites.items():
                    for arch in ("amd64", "arm64", "armhf"):
                        for kind, index in (("Packages", f"binary-{arch}/Packages"),
                                            ("Contents", f"Contents-{arch}")):
                            for suffix in ("", ".gz", ".xz", ".bz2", ".zst", ".lz4", ".future1", ".unknown9"):
                                path = f"{date}/dists/{suite}/main/{index}{suffix}"
                                original = f"https://snapshot.debian.org/archive/{archive}/{path}"
                                with self.subTest(archive=archive, date=date, index=index, suffix=suffix):
                                    routes = candidates(config, original)
                                    self.assertEqual(routes[0], ROOTS[key] + path)
                                    self.assertEqual(original in routes, suffix in formats[kind])
            # A date without reviewed Release metadata retains the public route.
            original = (f"https://snapshot.debian.org/archive/{archive}/19990101T000000Z/"
                        "dists/unknown/main/binary-amd64/Packages.bz2")
            self.assertIn(original, candidates(config, original))

    def test_signatures_by_hash_and_unreviewed_indexes_retain_public_fallback(self):
        reviewed = manifest(1)
        config = MIRRORS.configuration("", ROOTS, manifest=reviewed)
        for key, archive in MIRRORS.MIRROR_ROOTS:
            suite = "trixie" if archive == "debian" else "trixie-security"
            paths = [f"{NEW}/dists/{suite}/main/{index}{suffix}"
                     for index in ("binary-amd64/Packages", "Contents-arm64")
                     for suffix in (".gpg", ".pgp", ".asc", ".sig", ".xz.asc", ".gz.gpg")]
            paths.extend([
                f"{NEW}/dists/{suite}/main/binary-armhf/by-hash/SHA256/" + "a" * 64,
                f"{NEW}/dists/unreviewed/main/binary-amd64/Packages.future1",
                f"19990101T000000Z/dists/{suite}/main/Contents-amd64.future1",
            ])
            for path in paths:
                original = f"https://snapshot.debian.org/archive/{archive}/{path}"
                with self.subTest(path=path):
                    self.assertEqual(candidates(config, original), [ROOTS[key] + path, original])

    def test_manifest_rejects_missing_metadata_bad_pins_and_unsafe_paths(self):
        broken = []
        value = manifest()
        value["debian"]["current"] = NEW
        broken.append(value)
        value = manifest()
        value["debian"]["snapshots"][OLD] = {}
        broken.append(value)
        value = manifest()
        value["debian"]["probe"]["sha256"] = "not-a-checksum"
        broken.append(value)
        value = manifest()
        value["debian"]["probe"]["path"] = "pool/../secret"
        broken.append(value)
        value = manifest()
        value["debian"]["snapshots"][OLD]["trixie"]["Contents"] = [".gzip/../unsafe"]
        broken.append(value)
        for value in broken:
            with self.subTest(manifest=value), self.assertRaises(ValueError):
                MIRRORS.validate_manifest(value)

    def test_probe_selection_tracks_current_date_path_and_new_checksum(self):
        for stage in (0, 1):
            reviewed = manifest(stage)
            expected = [
                (key, archive, NEW if stage else OLD,
                 reviewed[archive]["probe"]["path"],
                 hashlib.sha256(payload(stage, archive)).hexdigest())
                for key, archive in MIRRORS.MIRROR_ROOTS
            ]
            self.assertEqual(MIRRORS.probe_packages(reviewed), expected)

    def test_cli_preparation_changes_only_the_adjacent_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            scripts = work / "ci"
            scripts.mkdir()
            for source in (ROOT / "ci").glob("*.py"):
                shutil.copyfile(source, scripts / source.name)
            unchanged = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in scripts.glob("*.py")}
            capture = work / "capture.json"
            child = work / "capture.py"
            child.write_text(
                "import json,os,pathlib,sys\n"
                "arg=next(a for a in sys.argv if a.startswith('--bazel-build-arg=--experimental_downloader_config='))\n"
                "config=pathlib.Path(arg.split('=',2)[2]).read_text()\n"
                "apt=json.loads(pathlib.Path(os.environ['SONIC_APT_MIRROR_CONFIG']).read_text())\n"
                "assert 'DEBIAN_MIRROR_ROOT' not in os.environ\n"
                "assert 'DEBIAN_SECURITY_MIRROR_ROOT' not in os.environ\n"
                f"pathlib.Path({str(capture)!r}).write_text(json.dumps(dict(config=config,apt=apt)))\n")
            public = work / "public.cfg"
            public.write_text("")
            environment = {k: v for k, v in os.environ.items() if k not in ROOTS}
            environment.update(ROOTS)
            environment.pop("GITHUB_ACTIONS", None)
            command = [sys.executable, str(scripts / "private_mirrors.py"), "run",
                       "--artifacts", str(work / "artifacts"), "--private-dir", str(work / "private"),
                       "--public-config", str(public), "--", sys.executable, str(child)]
            for stage in (0, 1):
                reviewed = manifest(stage)
                (scripts / "debian_snapshots.json").write_text(json.dumps(reviewed))
                result = subprocess.run(command, env=environment, capture_output=True, text=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                captured = json.loads(capture.read_text())
                self.assertEqual(captured["apt"]["mirrors"], MIRRORS.apt_mirror_map(ROOTS, reviewed))
                for key, archive in MIRRORS.MIRROR_ROOTS:
                    path = reviewed[archive]["probe"]["path"]
                    original = f"https://deb.debian.org/{archive}/{path}"
                    self.assertEqual(candidates(captured["config"], original)[0],
                                     ROOTS[key] + reviewed[archive]["current"] + "/" + path)
                self.assertEqual(unchanged, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                            for p in scripts.glob("*.py")})


if __name__ == "__main__":
    unittest.main()
