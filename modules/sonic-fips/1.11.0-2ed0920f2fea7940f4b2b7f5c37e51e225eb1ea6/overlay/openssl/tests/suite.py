"""Preserve upstream recipe selection and assertions; provide native build layout."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser()
    for name in ("runfiles", "source", "manifest", "perl", "kernel"):
        parser.add_argument("--" + name, required=True, type=Path)
    args, recipes = parser.parse_known_args()
    source = args.source.resolve()
    build = Path(os.environ["TEST_TMPDIR"]) / "build"
    build.mkdir()
    for destination, runfile in json.loads(args.manifest.read_text()).items():
        path = build / destination
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(args.runfiles / runfile)
    # Recipes write generated configurations and result files only in TEST_TMPDIR.
    for directory in ("test", "engines", "providers", "apps", "test-runs"):
        (build / directory).mkdir(exist_ok=True)
    environment = dict(os.environ)
    environment.update(
        SRCTOP=str(source), BLDTOP=str(build), PERL=str(build / "util/perl"),
        OPENSSL_SUITE_MANAGED_PERL=str(args.perl),
        OPENSSL_SUITE_PERL=str(build / "util/perl"),
        OPENSSL_SUITE_PERL_MODULES=str(build / "util"),
        OPENSSL_SOURCE_ROOT=str(source), OPENSSL_CONFIG_ROOT=str(build),
        EXE_EXT="", EXE_SHELL="", OPENSSL_RUNNING_UNIT_TESTS="yes", RESULT_D=str(build / "test-runs"),
        PATH=str(build / "util") + os.pathsep + str(args.kernel / "bin"),
    )
    # The SONiC test patch requires this exact upstream FIPS installation key.
    environment["FIPSKEY"] = "f4556650ac31d35461610bac4ed81b1a181b2d8a43ea2854cbae22ca74560813"
    return subprocess.call([str(build / "util/perl"), str(source / "test/run_tests.pl")] + recipes,
                           cwd=build, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
