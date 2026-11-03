"""Test BMv2's real configure frontend before and after the exec-size boundary."""

import hashlib
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


def main():
    adapter, frontend, foreign_tools = [Path(value).resolve() for value in sys.argv[1:]]
    tools = {name: shutil.which(name) for name in ("bash", "make", "gcc", "g++")}
    assert all(tools.values()), tools
    with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as temporary:
        root = Path(temporary)
        native = root / "native deps/include/usr/include"
        native.mkdir(parents=True)
        (native / "selected.h").write_text("#define SELECTED 99\n")
        for name, value in (("first", 13), ("second", 29)):
            (root / name).mkdir()
            (root / name / "selected.h").write_text("#define SELECTED " + str(value) + "\n")
        (root / "quoted include").mkdir()
        (root / "quoted include/quoted_path.h").write_text("#define SPACE_HEADER 31\n")
        program = ('#include <selected.h>\n#include <quoted_path.h>\n'
                   'static const char *text = STRING;\n'
                   'int main(void) { return VALUE + SELECTED != 20 || SPACE_HEADER != 31 || '
                   "text[0] != 'q' || text[6] != ' ' || text[7] != 'v'; }\n")
        for suffix in ("c", "cc"):
            (root / ("unit." + suffix)).write_text(program)
        (root / "configure.ac").write_text(
            'AC_INIT([bmv2-flag-transport], [1])\nAC_CONFIG_SRCDIR([unit.c])\n'
            'AC_PROG_CC\nAC_PROG_CXX\nAC_PROG_CPP\nAC_PROG_CXXCPP\n'
            'AC_CONFIG_FILES([Makefile])\nAC_OUTPUT\n')
        (root / "Makefile.in").write_text(
            'CC = @CC@\nCXX = @CXX@\nCPPFLAGS = @CPPFLAGS@\n'
            'CFLAGS = @CFLAGS@\nCXXFLAGS = @CXXFLAGS@\nLDFLAGS = @LDFLAGS@\n'
            '.PHONY: all nested\nall:\n\t$(MAKE) --no-print-directory nested\n'
            'nested:\n\t$(CC) $(CPPFLAGS) $(CFLAGS) unit.c $(LDFLAGS) -o c-program\n'
            '\t$(CXX) $(CPPFLAGS) $(CXXFLAGS) unit.cc $(LDFLAGS) -o cxx-program\n')
        # The shared compiler launcher is covered by its own real GCC/Libtool
        # tests and the complete BMv2 package test. Here its final exec is a
        # transparent fixture so this test isolates the owner pre-exec boundary.
        launch = root / "configure-launch.sh"
        launch.write_text('exec "$@"\n')
        common = shlex.join(["-DVALUE=1", "-UVALUE", "-DVALUE=7", '-DSTRING="quoted value"',
                             "-isystem", str(root / "first"), "-isystem", str(root / "second"),
                             "-I" + str(root / "quoted include")])
        long_flags = " ".join("-iquote/nonexistent/" + str(i) + "/" + "x" * 180
                              for i in range(750)) + " " + common
        assert len(long_flags.encode()) > 141742

        def run(flags, prefix):
            assignments = {
                "CC": tools["gcc"], "CXX": tools["g++"], "CPPFLAGS": flags,
                "CFLAGS": "-O2 -g -frandom-seed=fixture",
                "CXXFLAGS": "-O2 -g -frandom-seed=fixture", "LDFLAGS": "",
                "BAZEL_P4_TOOLS": str(foreign_tools), "BAZEL_PKGCONFIG_FILES": "",
                "BAZEL_PKGCONF": "/unused/pkgconf", "BAZEL_CONFIGURE_ENV": str(launch),
                "EXT_BUILD_ROOT": str(root), "EXT_BUILD_DEPS": str(root / "native deps"),
            }
            command = " ".join(key + "=" + shlex.quote(value) for key, value in assignments.items())
            if prefix:
                command += " source " + shlex.quote(str(adapter))
            command += " " + shlex.join(["/bin/sh", str(frontend), "--prefix=/usr"])
            script = root / "invoke.sh"
            # Match the generated foreign action: flags are temporary inline
            # assignments for configure; the following Make runs in this same
            # shell without a fresh Python-created environment.
            script.write_text("set -eu\nunset CPPFLAGS\n" + command +
                              '\ntest "${CPPFLAGS+x}" != x\n' +
                              shlex.join([tools["make"], "--no-print-directory"]) + "\n")
            return subprocess.run([tools["bash"], script], cwd=root, capture_output=True, text=True)

        old = run(long_flags, False)
        assert old.returncode != 0 and "Argument list too long" in old.stderr, old.stderr
        hashes = []
        for flags in (common, long_flags):
            accepted = run(flags, True)
            assert accepted.returncode == 0, accepted.stdout + accepted.stderr
            assert (root / ".bazel-bmv2-cppflags.rsp").read_text() == (
                flags + '\n-isystem\n"' + str(native) + '"\n')
            row = {}
            for name in ("c-program", "cxx-program"):
                binary = root / name
                subprocess.run([binary], check=True)
                row[name] = hashlib.sha256(binary.read_bytes()).hexdigest()
            hashes.append(row)
        assert hashes[0] == hashes[1], hashes
        rejected = run("-Wl,--as-needed", True)
        assert rejected.returncode != 0 and "CPPFLAGS must contain GCC preprocessor options" in rejected.stderr
    print("Pre-exec E2BIG rejection, original Autoconf frontend, recursive C/C++ Make, "
          "ordered/quoted flags, native-header precedence and identical outputs passed")


if __name__ == "__main__":
    main()
