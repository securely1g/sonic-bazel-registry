"""Test BMv2's real configure frontend before and after the exec-size boundary."""

import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile


def main():
    adapter, frontend, foreign_tools, configure_environment = [Path(value).resolve() for value in sys.argv[1:]]
    tools = {name: shutil.which(name) for name in ("bash", "make", "gcc", "g++", "ar")}
    assert all(tools.values()), tools
    with tempfile.TemporaryDirectory(dir=os.environ.get("TEST_TMPDIR")) as temporary:
        # Model the actual long Bazel sandbox prefix shared by 328 native
        # library directories; recursive Make must shorten relative to its cwd.
        root = Path(temporary) / ("sandbox-" + "s" * 100) / ("execroot-" + "e" * 100)
        root.mkdir(parents=True)
        native = root / "native deps/include/usr/include"
        native.mkdir(parents=True)
        (native / "selected.h").write_text("#define SELECTED 99\n")
        for name, value in (("first", 13), ("second", 29)):
            (root / name).mkdir()
            (root / name / "selected.h").write_text("#define SELECTED " + str(value) + "\n")
        (root / "quoted include").mkdir()
        (root / "quoted include/quoted_path.h").write_text("#define SPACE_HEADER 31\n")
        for name, value in (("first library", 41), ("second library", 42)):
            directory = root / name
            directory.mkdir()
            (directory / "choice.c").write_text("int chosen(void) { return " + str(value) + "; }\n")
            subprocess.run([tools["gcc"], "-c", str(directory / "choice.c"), "-o", str(directory / "choice.o")], check=True)
            subprocess.run([tools["ar"], "rcs", str(directory / "libchoice.a"), str(directory / "choice.o")], check=True)
        program = ('#include <selected.h>\n#include <quoted_path.h>\n'
                   '#ifdef __cplusplus\nextern "C"\n#endif\nint chosen(void);\n'
                   'static const char *text = STRING;\n'
                   'int main(void) { return chosen() != 41 || VALUE + SELECTED != 20 || SPACE_HEADER != 31 || '
                   "text[0] != 'q' || text[6] != ' ' || text[7] != 'v'; }\n")
        for suffix in ("c", "cc"):
            (root / ("unit." + suffix)).write_text(program)
        (root / "configure.ac").write_text(
            'AC_INIT([bmv2-flag-transport], [1])\nAC_CONFIG_SRCDIR([unit.c])\n'
            'AC_PROG_CC\nAC_PROG_CXX\nAC_PROG_CPP\nAC_PROG_CXXCPP\nLT_INIT\n'
            'AC_CONFIG_FILES([Makefile])\nAC_OUTPUT\n')
        (root / "Makefile.in").write_text(
            'CC = @CC@\nCXX = @CXX@\nCPPFLAGS = @CPPFLAGS@\n'
            'CFLAGS = @CFLAGS@\nCXXFLAGS = @CXXFLAGS@\nLDFLAGS = @LDFLAGS@\n'
            '.PHONY: all nested\nall:\n\tmkdir -p nested\n'
            '\t$(MAKE) --no-print-directory -C nested -f ../Makefile nested\n'
            'nested:\n\t../libtool --tag=CC --mode=link $(CC) $(CPPFLAGS) $(CFLAGS) ../unit.c $(LDFLAGS) -o ../c-program\n'
            '\t../libtool --tag=CXX --mode=link $(CXX) $(CPPFLAGS) $(CXXFLAGS) ../unit.cc $(LDFLAGS) -o ../cxx-program\n')
        common = shlex.join(["-DVALUE=1", "-UVALUE", "-DVALUE=7", '-DSTRING="quoted value"',
                             "-isystem", str(root / "first"), "-isystem", str(root / "second"),
                             "-I" + str(root / "quoted include")])
        long_flags = " ".join("-iquote/nonexistent/" + str(i) + "/" + "x" * 180
                              for i in range(750)) + " " + common
        assert len(long_flags.encode()) > 141742
        link_flags = shlex.join(["-L" + str(root / "first library"), "-L" + str(root / "second library"),
                                "-Wl,-z,relro,-z,now", "-lchoice"])
        long_link_flags = " ".join("-L" + str(root) + "/nonexistent/" + str(i) + "/" + "x" * 100
                                   for i in range(328)) + " " + link_flags
        assert len(long_link_flags.encode()) > 136826

        def run(flags, prefix, ldflags=link_flags):
            assignments = {
                "CC": tools["gcc"], "CXX": tools["g++"], "CPPFLAGS": flags,
                "CFLAGS": "-O2 -g -frandom-seed=fixture",
                "CXXFLAGS": "-O2 -g -frandom-seed=fixture", "LDFLAGS": ldflags,
                "BAZEL_P4_TOOLS": str(foreign_tools), "BAZEL_PKGCONFIG_FILES": "",
                "BAZEL_PKGCONF": "/unused/pkgconf", "BAZEL_CONFIGURE_ENV": str(configure_environment),
                "EXT_BUILD_ROOT": "/usr", "EXT_BUILD_DEPS": str(root / "native deps"),
            }
            command = " ".join(key + "=" + shlex.quote(value) for key, value in assignments.items())
            if prefix:
                command += " source " + shlex.quote(str(adapter))
            command += " " + shlex.join(["/bin/sh", str(frontend), "--prefix=/usr"])
            script = root / "invoke.sh"
            # Match the generated foreign action: flags are temporary inline
            # assignments for configure; the following Make runs in this same
            # shell without a fresh Python-created environment.
            script.write_text("set -eu\nunset CPPFLAGS LDFLAGS\nexport COMPILER_PATH=/usr/bin\n" +
                              "export LIBRARY_PATH=" + shlex.quote(str(root / "second library")) + "\n" + command +
                              '\ntest "${CPPFLAGS+x}" != x\n' +
                              'test "${LDFLAGS+x}" != x\n' +
                              shlex.join([tools["make"], "--no-print-directory"]) + "\n")
            result = subprocess.run([tools["bash"], script], cwd=root, capture_output=True, text=True)
            if result.returncode and (root / "config.log").exists():
                evidence = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", os.environ.get("TEST_TMPDIR", "/tmp")))
                evidence.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(root / "config.log", evidence / "bmv2-flags-failed-config.log")
            return result

        old = run(long_flags, False)
        assert old.returncode != 0 and "Argument list too long" in old.stderr, old.stderr
        old_link = run(common, False, long_link_flags)
        assert old_link.returncode != 0 and "Argument list too long" in old_link.stderr, old_link.stderr
        hashes = []
        for flags, ldflags in ((common, link_flags), (long_flags, link_flags), (long_flags, long_link_flags)):
            accepted = run(flags, True, ldflags)
            assert accepted.returncode == 0, accepted.stdout + accepted.stderr
            assert (root / ".bazel-bmv2-cppflags.rsp").read_text() == (
                flags + '\n-isystem\n"' + str(native) + '"\n')
            assert (root / ".sonic-linker-arguments").read_text().splitlines() == [
                "sonic-linker-arguments-v1", *shlex.split(ldflags)]
            row = {}
            for name in ("c-program", "cxx-program"):
                binary = root / name
                subprocess.run([binary], check=True)
                row[name] = hashlib.sha256(binary.read_bytes()).hexdigest()
            hashes.append(row)
        assert hashes[0] == hashes[1] == hashes[2], hashes
        launcher = root / ".sonic-compiler-argv"
        response = root / ".sonic-linker-arguments"
        original_response = response.read_bytes()
        capture = root / "capture-arguments.py"
        capture.write_text("#!/usr/bin/python3\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n")
        capture.chmod(0o755)
        opaque = root / "ordinary-gcc.rsp"
        opaque.write_text("-L/unmodified\n")
        original_arguments = ["-L" + str(root / "first library"), "@" + str(opaque)]
        captured = subprocess.run([launcher, capture, *original_arguments], check=True, text=True, capture_output=True)
        assert json.loads(captured.stdout) == original_arguments
        values = ["-L" + str(root / "first library"), "-L" + str(root / "second library"),
                  "-Wl,--as-needed", "-Xlinker", "-Lliteral-operand", "quoted space", "literal\\backslash", "", "-lchoice"]
        response.write_text("sonic-linker-arguments-v1\n" + "".join(value + "\n" for value in values))
        captured = subprocess.run([launcher, capture, "-before", "@" + str(response), "-after"], cwd=root / "nested", check=True, text=True, capture_output=True)
        assert json.loads(captured.stdout) == ["-before", "-L../first library", "-L../second library", *values[2:], "-after"]
        response.write_text("wrong-format\n-L/not-accepted\n")
        rejected_format = subprocess.run([launcher, capture, "@" + str(response)], text=True, capture_output=True)
        assert rejected_format.returncode == 2 and "Invalid private linker argument response" in rejected_format.stderr
        response.write_bytes(original_response)
        driver = subprocess.run([launcher, tools["gcc"], "-###", "-x", "c", str(root / "unit.c"),
                                 "@" + str(response), "-o", str(root / "trace-program")],
                                cwd=root / "nested", text=True, capture_output=True, check=True)
        collected = [line for line in driver.stderr.splitlines() if line.startswith("COLLECT_GCC_OPTIONS=")]
        assert collected and max(len(line.encode()) + 1 for line in collected) < 131072
        evidence = Path(os.environ.get("TEST_UNDECLARED_OUTPUTS_DIR", os.environ.get("TEST_TMPDIR", "/tmp")))
        evidence.mkdir(parents=True, exist_ok=True)
        (evidence / "bmv2-flags-proof.json").write_text(json.dumps({
            "cppflags_input_bytes": len(long_flags.encode()), "ldflags_input_bytes": len(long_link_flags.encode()),
            "ldflags_transport_bytes": len(("LDFLAGS=@" + str(response)).encode()) + 1,
            "maximum_collect_gcc_options_line_bytes": max(len(line.encode()) + 1 for line in collected),
            "same_short_and_long_output_hashes": hashes, "recursive_make_uses_nested_cwd": True,
            "real_autoconf_libtool_c_and_cxx": True, "competing_default_library_search_preserved": True,
            "opaque_response_unchanged": True, "private_vector_order_and_quoting_preserved": True,
            "invalid_private_format_rejected": True,
        }, indent=2) + "\n")
        rejected = run("-Wl,--as-needed", True)
        assert rejected.returncode != 0 and "CPPFLAGS must contain GCC preprocessor options" in rejected.stderr
    print("Pre-exec E2BIG rejection, original Autoconf frontend, recursive C/C++ Make, "
          "ordered/quoted flags, native-header precedence and identical outputs passed")


if __name__ == "__main__":
    main()
