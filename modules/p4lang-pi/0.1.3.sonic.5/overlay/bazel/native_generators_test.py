"""Compare the native and installed PI generators using original source fixtures."""

import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


def run(prefix, binary, *arguments):
    return subprocess.run(
        [*prefix, str(binary), *map(str, arguments)], check=False,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30,
    )


def main():
    native_json, native_header, old_json, old_header, runtime, profile, valid, *packages = [
        Path(argument).resolve(strict=True) for argument in sys.argv[1:]
    ]
    with tempfile.TemporaryDirectory(prefix="pi-native-generators-") as directory:
        root = Path(directory)
        # Reuse the runtime test's declared, locked runtime/APT inputs. Neither
        # source preparation nor a compiler is invoked inside this test.
        for archive_path in [*packages, runtime]:
            with tarfile.open(archive_path) as archive:
                archive.extractall(root, filter="data")
        loaders = sorted({path.resolve() for path in root.rglob("ld-linux-*.so.*") if path.is_file()})
        assert len(loaders) == 1, loaders
        libraries = sorted({str(path.parent) for path in root.rglob("*.so*") if path.is_file()})
        prefix = [str(loaders[0]), "--inhibit-cache", "--library-path", ":".join(libraries)]
        for fixture, table_names, action_name in [
            (profile, ["T1", "T2"], "A"),
            (valid, ["T1"], "NOOP"),
        ]:
            results = [run(prefix, binary, fixture) for binary in [old_json, native_json]]
            assert all(result.returncode == 0 for result in results), [r.stderr for r in results]
            parsed = [json.loads(result.stdout) for result in results]
            assert isinstance(parsed[0], dict) and parsed[0], parsed[0]
            assert parsed[0] == parsed[1], fixture.name
            headers = []
            for label, binary in [("installed", old_header), ("native", native_header)]:
                destination = root / (fixture.stem + "-" + label)
                destination.mkdir()
                result = run(prefix, binary, "-c", fixture, "-d", destination, "-n", "fixture")
                assert result.returncode == 0, result.stderr
                headers.append((destination / "pi_fe_defines_fixture.h").read_bytes())
            assert headers[0] == headers[1], fixture.name
            assert headers[0], fixture.name
            if fixture == profile:
                assert b"PI_FIXTURE_ACT_PROF_AP" in headers[0]
            else:
                assert b"PI_FIXTURE_MF_T1_" in headers[0] and b"$valid$" not in headers[0]
            # These are actual original fixture names, not a copy of emitted IDs.
            for symbol in ["ACTION_" + action_name, *["TABLE_" + name for name in table_names]]:
                assert ("PI_FIXTURE_" + symbol).encode() in headers[0], (fixture.name, symbol)
        # Preserve the public argument-error behavior of both original programs.
        for binary in [old_json, native_json, old_header, native_header]:
            result = run(prefix, binary)
            assert result.returncode == 1, (binary.name, result.returncode)
        for binary in [old_header, native_header]:
            result = run(prefix, binary, "-h")
            assert result.returncode == 0 and b"Usage" in result.stdout + result.stderr, result
        missing = root / "does-not-exist.json"
        for binary in [old_json, native_json]:
            assert run(prefix, binary, missing).returncode == 1
        malformed = root / "malformed.json"
        malformed.write_bytes(b"{invalid json")
        failures = [malformed]
        # Truncation after complete nested values reaches parse-error cleanup,
        # rather than failing only at the first token. Keep original fixtures.
        for fixture in [profile, valid]:
            contents = fixture.read_bytes().rstrip()
            assert contents.endswith(b"}")
            truncated = root / (fixture.stem + "-truncated.json")
            truncated.write_bytes(contents[:-1])
            failures.append(truncated)
        for fixture in failures:
            for binary in [old_json, native_json]:
                result = run(prefix, binary, fixture)
                # A signal or allocator abort is not the CLI's ordinary error.
                assert result.returncode == 1, (binary.name, fixture.name, result.returncode)
                assert not result.stdout and b"Error while loading config." in result.stderr
    print("Native/installed JSON and FE header fixtures agree; argument failures remain enforced.")


if __name__ == "__main__":
    main()
