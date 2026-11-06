"""Build with native tools and execute ARM64 output through the runner wrapper."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("registry_ci_cross_integration", ROOT / "ci/registry_ci.py")
assert SPEC is not None and SPEC.loader is not None
registry_ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(registry_ci)

MODULE = '''module(name = "runner_arm_cross_fixture")
bazel_dep(name = "sonic-build-infra", version = "0.0.25-34de7330abc72229dfc8dab88dec71b89c52aa88", repo_name = "sonic_build_infra")
bazel_dep(name = "rules_cc", version = "0.2.22")
bazel_dep(name = "rules_python", version = "1.8.0")
bazel_dep(name = "rules_distroless", version = "0.9.4.sonic.15")
apt = use_extension("@rules_distroless//apt:extensions.bzl", "apt")
apt.install(
    dependency_set = "cross_fixture_runtime",
    packages = ["libc6"],
    suites = ["trixie", "trixie-updates", "trixie-security"],
)
use_repo(apt, "cross_fixture_runtime")
'''
BUILD = '''load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_test")
load(":objcopy.bzl", "copy_elf")
load("@rules_python//python:defs.bzl", "py_binary", "py_test")
load("@sonic_build_infra//testing:exec_test.bzl", "exec_test")
load("@sonic_build_infra//cc:runtime_test.bzl", "native_runtime_test")
cc_binary(name = "generator", srcs = ["generator.c"])
genrule(
    name = "generated_header",
    outs = ["generated_value.h"],
    tools = [":generator"],
    cmd = "$(location :generator) > $@",
)
cc_test(
    name = "arm_probe",
    srcs = ["probe.cc", ":generated_header"],
    linkopts = ["-pthread"],
)
copy_elf(name = "stripped_probe", src = ":arm_probe", testonly = True)
py_test(
    name = "python_probe",
    srcs = ["python_probe.py"],
    data = [":arm_probe"],
    args = ["$(location :arm_probe)"],
)
py_binary(name = "python_checker", srcs = ["python_probe.py"], main = "python_probe.py")
exec_test(name = "exec_python_probe", runner = ":python_checker", srcs = [":arm_probe"])
cc_binary(name = "runtime_program", srcs = ["runtime_program.c"])
native_runtime_test(
    name = "native_python_probe",
    binary = ":runtime_program",
    runtime_payloads = ["@cross_fixture_runtime//libc6:data"],
)
'''
TEST_TARGETS = ["//:arm_probe", "//:python_probe", "//:exec_python_probe",
                "//:native_python_probe"]
OBJCOPY = '''load("@rules_cc//cc:find_cc_toolchain.bzl", "find_cpp_toolchain")

def _copy_impl(ctx):
    cc = find_cpp_toolchain(ctx)
    output = ctx.actions.declare_file(ctx.label.name)
    ctx.actions.run(
        executable = cc.objcopy_executable,
        arguments = ["--strip-debug", ctx.file.src.path, output.path],
        inputs = depset([ctx.file.src], transitive = [cc.all_files]),
        outputs = [output],
        mnemonic = "CrossObjcopy",
    )
    return [DefaultInfo(files = depset([output]))]

copy_elf = rule(
    implementation = _copy_impl,
    attrs = {"src": attr.label(allow_single_file = True)},
    fragments = ["cpp"],
    toolchains = ["@bazel_tools//tools/cpp:toolchain_type"],
)
'''

GENERATOR = '''#include <stdio.h>
#ifndef __x86_64__
#error The source generator must run on the AMD64 execution platform.
#endif
int main(void) { puts("#define GENERATED_VALUE 42"); return 0; }
'''
RUNTIME_PROGRAM = '''#include <stdio.h>
#ifndef __aarch64__
#error The native-runtime fixture must use an ARM64 binary and target libc.
#endif
int main(void) { puts("native runtime ARM64"); return 0; }
'''
CPP_PROBE = '''#include "generated_value.h"
#include <iostream>
#include <stdexcept>
#include <thread>
#ifndef __aarch64__
#error The target output must be ARM64.
#endif
int main() {
    int value = 0;
    std::thread worker([&] { value = GENERATED_VALUE; });
    worker.join();
    try { throw std::runtime_error("ARM64 exceptions work"); }
    catch (const std::runtime_error& error) { std::cout << error.what() << "\\n"; }
    std::cout << "ARM64 generated value: " << value << "\\n";
    return value == 42 ? 0 : 1;
}
'''
CPP_OUTPUT = "ARM64 exceptions work\nARM64 generated value: 42\n"
PYTHON_PROBE = '''import json, platform, subprocess, sys
from pathlib import Path

header = Path(sys.executable).read_bytes()[:20]
assert header[:4] == b"\\x7fELF" and int.from_bytes(header[18:20], "little") == 183
assert platform.machine() == "aarch64", (sys.executable, platform.machine())
binary = Path(sys.argv[1]).resolve(strict=True)
assert int.from_bytes(binary.read_bytes()[18:20], "little") == 183
assert subprocess.check_output([str(binary)], text=True) == "ARM64 exceptions work\\nARM64 generated value: 42\\n"
child = json.loads(subprocess.check_output([
    sys.executable, "-I", "-S", "-c",
    "import json,platform,sys; header=open(sys.executable,'rb').read(20); "
    "print(json.dumps([platform.machine(),int.from_bytes(header[18:20],'little')]))",
], text=True))
assert child == ["aarch64", 183], child
print(json.dumps(dict(machine=platform.machine(), python=sys.executable, child=child)))
'''
RUNTIME_PROBE = '''import json, os, platform, subprocess, sys
from pathlib import Path

with open(sys.executable, "rb") as executable:
    header = executable.read(20)
assert header[:4] == b"\\x7fELF" and int.from_bytes(header[18:20], "little") == 183
assert platform.machine() == "aarch64"
assert os.getcwd() == os.environ["SONIC_CROSS_EXPECT_CWD"]
assert Path(os.environ["SONIC_CROSS_LINK"]).read_text() == os.environ["SONIC_CROSS_TOKEN"]
child_code = (
    "import json,os,platform,sys; "
    "header=open(sys.executable,'rb').read(20); "
    "print(json.dumps(dict(machine=platform.machine(),elf_machine=int.from_bytes(header[18:20],'little'),"
    "cwd=os.getcwd(),token=os.environ['SONIC_CROSS_TOKEN'],argument=sys.argv[1])))"
)
child = json.loads(subprocess.check_output(
    [sys.executable, "-I", "-S", "-c", child_code, "nested argument with spaces"], text=True))
assert child == dict(machine="aarch64", elf_machine=183, cwd=os.getcwd(),
                     token=os.environ["SONIC_CROSS_TOKEN"], argument="nested argument with spaces")
cpp_output = subprocess.check_output([os.environ["SONIC_CROSS_PROBE"]], text=True)
assert cpp_output == "ARM64 exceptions work\\nARM64 generated value: 42\\n"
generator_output = subprocess.check_output([os.environ["SONIC_CROSS_GENERATOR"]], text=True)
assert generator_output == "#define GENERATED_VALUE 42\\n"
architecture = subprocess.check_output(["/usr/bin/dpkg", "--print-architecture"], text=True).strip()
release = dict(line.split("=", 1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
codename = release["VERSION_CODENAME"].strip(chr(34))
assert architecture == "arm64" and codename == "trixie"
assert Path.home() == Path(os.environ["HOME"])
(Path.home() / "home-proof").write_text(os.environ["SONIC_CROSS_TOKEN"])
result = dict(machine=platform.machine(), python_elf_machine=183, child=child,
              cwd=os.getcwd(), architecture=architecture, codename=codename,
              cpp_output=cpp_output, native_generator_output=generator_output)
(Path(os.environ["TEST_TMPDIR"]) / "runtime-proof.json").write_text(json.dumps(result))
print(json.dumps(result))
'''


def elf_machine(path: Path) -> int:
    with path.open("rb") as executable:
        header = executable.read(20)
    if header[:4] != b"\x7fELF" or header[4:6] != b"\x02\x01":
        raise AssertionError(f"Expected a 64-bit little-endian ELF executable: {path}")
    return int.from_bytes(header[18:20], "little")


@unittest.skipUnless(os.environ.get("REGISTRY_CI_TEST_BAZEL") and os.environ.get("REGISTRY_CI_TEST_ARM_EXECUTOR"),
                     "set REGISTRY_CI_TEST_BAZEL and REGISTRY_CI_TEST_ARM_EXECUTOR for the ARM64 fixture")
class ArmCrossRuntimeIntegrationTest(unittest.TestCase):
    def test_native_generator_and_nested_arm_runtime(self):
        executor = Path(os.environ["REGISTRY_CI_TEST_ARM_EXECUTOR"]).resolve(strict=True)
        self.assertTrue(os.access(executor, os.X_OK), executor)
        with tempfile.TemporaryDirectory(prefix="registry-arm-cross-") as temporary:
            work = Path(temporary).resolve()
            consumer, artifacts = work / "consumer", work / "artifacts"
            consumer.mkdir()
            artifacts.mkdir()
            sources = {"MODULE.bazel": MODULE, "BUILD.bazel": BUILD,
                       "generator.c": GENERATOR, "probe.cc": CPP_PROBE, "python_probe.py": PYTHON_PROBE,
                       "runtime_program.c": RUNTIME_PROGRAM, "objcopy.bzl": OBJCOPY}
            for name, content in sources.items():
                (consumer / name).write_text(content)
                (artifacts / name).write_text(content)

            def execute(case: str, command: list[str], cwd: Path, *, environment=None, timeout=180):
                (artifacts / (case + "-command.json")).write_text(json.dumps(command, indent=2) + "\n")
                stdout, stderr = artifacts / (case + ".stdout"), artifacts / (case + ".stderr")
                with stdout.open("w") as out, stderr.open("w") as err:
                    process = subprocess.Popen(command, cwd=cwd, env=environment, stdout=out, stderr=err,
                                               start_new_session=True)
                    try:
                        process.wait(timeout=timeout)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                        self.fail(f"{case} exceeded {timeout}s; see preserved command/output artifacts")
                self.assertEqual(process.returncode, 0, (stdout.read_text() + stderr.read_text())[-12000:])
                return stdout.read_text()

            try:
                output_root = work / "bazel"
                bazel_prefix = [os.environ["REGISTRY_CI_TEST_BAZEL"], "--ignore_all_rc_files",
                                "--host_jvm_args=-Xmx2g", "--output_user_root=" + str(output_root)]
                flags = ["--registry=" + ROOT.as_uri(), "--registry=https://bcr.bazel.build/",
                         "--experimental_downloader_config=" + str(ROOT / "ci/source_mirrors.cfg"),
                         *registry_ci.HTTP_DOWNLOAD_FLAGS, "--lockfile_mode=update",
                         "--jobs=1", "--discard_analysis_cache"]
                # A host-derived parent on this machine is AMD64. The generated
                # adapter must override it while preserving native build tools.
                adapted = registry_ci.cross_toolchain.prepare(
                    ROOT, consumer, work, artifacts, bazel_prefix, flags,
                    "@platforms//host:host", "@platforms//host:host", registry_ci.run_logged)
                self.assertTrue(adapted["module_versions_unchanged"])
                self.assertIsNotNone(adapted["provider"])
                # Libtool can drop GCC's -B flags from a foreign shared link.
                # Exercise that invocation with only the adapter driver and its declared inputs.
                driver = work / "cross-cc-repository" / "aarch64-linux-gnu-gcc"
                shared = artifacts / "foreign-link.so"
                subprocess.run([str(driver), "-x", "c", "-fPIC", "-shared", "-o", str(shared), "-"],
                               input=b"int foreign_link_probe(void) { return 42; }\n", check=True)
                self.assertEqual(elf_machine(shared), 183)
                flags.extend(["--host_platform=" + adapted["execution_platform"],
                              "--platforms=" + adapted["target_platform"]])
                command = [*bazel_prefix, "build", *flags,
                           "--build_event_json_file=" + str(artifacts / "build-events.jsonl"), "//:arm_probe", "//:stripped_probe"]
                execute("build", command, consumer, timeout=1200)
                binary = (consumer / "bazel-bin/arm_probe").resolve(strict=True)
                generators = [path.resolve() for path in (consumer / "bazel-out").glob("*/bin/generator")
                              if path.is_file()]
                self.assertEqual(len(generators), 1, generators)
                generator = generators[0]
                self.assertEqual(elf_machine(generator), 62, generator)
                self.assertEqual(elf_machine(binary), 183, binary)
                stripped = (consumer / "bazel-bin/stripped_probe").resolve(strict=True)
                self.assertEqual(elf_machine(stripped), 183, stripped)
                self.assertEqual(execute("native-generator", [str(generator)], consumer, timeout=30),
                                 "#define GENERATED_VALUE 42\n")
                for name, path in (("generator", generator), ("arm_probe", binary)):
                    shutil.copy2(path, artifacts / name)

                # The explicit bindings are outside cwd; absolute runfiles-like
                # symlinks must survive the wrapper's guest filesystem view.
                runtime_cwd, bound_data, test_tmp = work / "runtime cwd", work / "bound data", work / "test tmp"
                for path in (runtime_cwd, bound_data, test_tmp):
                    path.mkdir()
                home = test_tmp / "home"
                home.mkdir()
                token = "preserved environment with spaces and 'quotes'"
                (bound_data / "payload.txt").write_text(token)
                link = runtime_cwd / "absolute-link"
                link.symlink_to(bound_data / "payload.txt")
                probe = runtime_cwd / "probe.py"
                probe.write_text(RUNTIME_PROBE)
                (artifacts / "runtime-probe.py").write_text(RUNTIME_PROBE)
                environment = {**os.environ, "HOME": str(home), "TEST_TMPDIR": str(test_tmp),
                               "SONIC_CROSS_TOKEN": token, "SONIC_CROSS_LINK": str(link),
                               "SONIC_CROSS_PROBE": str(binary), "SONIC_CROSS_GENERATOR": str(generator),
                               "SONIC_CROSS_EXPECT_CWD": str(runtime_cwd)}
                prefix = [str(executor), "--bind", str(output_root), "--bind", str(consumer),
                          "--bind", str(bound_data), "--"]
                self.assertEqual(execute("arm-cpp", [*prefix, str(binary)], runtime_cwd,
                                         environment=environment, timeout=60), CPP_OUTPUT)
                self.assertEqual(execute("arm-objcopy", [*prefix, str(stripped)], runtime_cwd,
                                         environment=environment, timeout=60), CPP_OUTPUT)
                runtime = json.loads(execute("arm-python", [*prefix, "/usr/bin/python3", "-I", "-S", str(probe)],
                                             runtime_cwd, environment=environment, timeout=60))
                self.assertEqual(json.loads((test_tmp / "runtime-proof.json").read_text()), runtime)
                self.assertEqual((home / "home-proof").read_text(), token)
                info_flags = [flag for flag in flags if flag.startswith((
                    "--registry=", "--lockfile_mode=", "--experimental_downloader_config="))]
                output_base = Path(execute("info", [*bazel_prefix, "info", *info_flags, "output_base"],
                                           consumer, timeout=60).strip())
                mappings = registry_ci.prepare_cross_python_runtimes(
                    bazel_prefix, flags, TEST_TARGETS, output_base, consumer, artifacts, prefix)
                self.assertTrue(mappings, "The exec-configured Python checker must have a mapped ARM runtime")
                native_identities = {}
                for mapping in mappings:
                    native = Path(mapping["destination"]) / "bin/python3"
                    self.assertEqual(elf_machine(native), 62, native)
                    self.assertEqual(elf_machine(Path(mapping["source"]) / "bin/python3"), 183, mapping)
                    native_identities[native] = hashlib.sha256(native.read_bytes()).hexdigest()
                    prefix[-1:-1] = ["--bind-at", mapping["source"], mapping["destination"]]
                test_events = artifacts / "test-events.jsonl"
                execute("bazel-test", [*bazel_prefix, "test", *flags,
                                       "--strategy=TestRunner=" + registry_ci.TEST_SANDBOX_STRATEGY,
                                       "--test_env=HOME=", "--nocache_test_results", "--test_output=all",
                                       "--run_under=" + shlex.join(prefix),
                                       "--build_event_json_file=" + str(test_events), *TEST_TARGETS],
                        consumer, timeout=300)
                summaries = {event["id"]["testSummary"]["label"]: event["testSummary"]
                             for line in test_events.read_text().splitlines()
                             if "testSummary" in (event := json.loads(line))}
                self.assertEqual(len(summaries), len(TEST_TARGETS), summaries)
                for target in TEST_TARGETS:
                    matches = [summary for label, summary in summaries.items()
                               if label.endswith(target[target.index("//"):])]
                    self.assertEqual(len(matches), 1, (target, summaries))
                    self.assertEqual(matches[0]["overallStatus"], "PASSED", (target, matches))
                    self.assertEqual(matches[0].get("totalNumCached", 0), 0, (target, matches))
                # Test-only filesystem mappings must leave native build tools intact.
                for native, digest in native_identities.items():
                    self.assertEqual(elf_machine(native), 62, native)
                    self.assertEqual(hashlib.sha256(native.read_bytes()).hexdigest(), digest, native)
                runtime_program = (consumer / "bazel-bin/runtime_program").resolve(strict=True)
                self.assertEqual(elf_machine(runtime_program), 183, runtime_program)
                shutil.copy2(runtime_program, artifacts / "runtime_program")
                self.assertEqual(execute("native-generator-after-tests", [str(generator)], consumer, timeout=30),
                                 "#define GENERATED_VALUE 42\n")
                (artifacts / "result.json").write_text(json.dumps({
                    "native_generator_elf_machine": elf_machine(generator), "target_elf_machine": elf_machine(binary),
                    "generator_sha256": hashlib.sha256(generator.read_bytes()).hexdigest(),
                    "target_sha256": hashlib.sha256(binary.read_bytes()).hexdigest(),
                    "executor_sha256": hashlib.sha256(executor.read_bytes()).hexdigest(), "runtime": runtime,
                    "bazel_test_summaries": summaries, "python_runtime_mappings": mappings,
                    "cross_platforms": adapted,
                }, indent=2) + "\n")
            finally:
                try:
                    # Match production server mode: batch mode discards the
                    # incrementality state required by the helper's cquery.
                    execute("shutdown", [*bazel_prefix, "shutdown"], consumer, timeout=60)
                finally:
                    lock = consumer / "MODULE.bazel.lock"
                    if lock.is_file():
                        shutil.copy2(lock, artifacts / lock.name)
                    destination = os.environ.get("REGISTRY_CI_TEST_ARTIFACTS")
                    if destination:
                        shutil.copytree(artifacts, Path(destination) / work.name)


if __name__ == "__main__":
    unittest.main()
