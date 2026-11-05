"""Prepare the two frequently started CLI test runtimes as declared build actions."""

load("@rules_python//python:py_info.bzl", "PyInfo")

def _runfile(ctx, file):
    return file.short_path[3:] if file.short_path.startswith("../") else ctx.workspace_name + "/" + file.short_path

def _impl(ctx):
    if ctx.target_platform_has_constraint(ctx.attr._x86_64[platform_common.ConstraintValueInfo]):
        machine = 62
    elif ctx.target_platform_has_constraint(ctx.attr._aarch64[platform_common.ConstraintValueInfo]):
        machine = 183
    else:
        fail("Prepared CLI runtime requires an x86_64 or aarch64 target")
    executable = ctx.actions.declare_file(ctx.label.name)
    runtime = ctx.actions.declare_directory(ctx.label.name + ".runtime")
    manifest = ctx.actions.declare_file(ctx.label.name + ".runtime.json")
    template = ctx.actions.declare_file(ctx.label.name + ".launcher.in")
    sources = ctx.attr._metadata[PyInfo].transitive_sources.to_list()
    metadata = [file for file in sources if file.basename == "elf_metadata.py"]
    if len(metadata) != 1:
        fail("Expected exactly one declared ELF metadata parser")
    ctx.actions.expand_template(
        template = ctx.file._launcher_template,
        output = template,
        substitutions = {
            "@@BINARY@@": _runfile(ctx, ctx.file.binary),
            "@@REALPATH@@": _runfile(ctx, ctx.executable._realpath),
            "@@RUNTIME@@": _runfile(ctx, runtime),
        },
    )
    arguments = ctx.actions.args()
    # This execution-platform Python runs the original validator, including all
    # ELF, SONAME, debug-link and transitive RPATH checks. Its existing instrument
    # hook records the validated runtime rather than executing the target here.
    arguments.add_all(["-B", "-S", "-c", "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));sys.argv[0]=sys.argv.pop(1);runpy.run_path(sys.argv[0],run_name='__main__')"])
    arguments.add(metadata[0].dirname)
    arguments.add(ctx.file._validator)
    arguments.add_all(["--target-machine", str(machine), "--binary", ctx.file.binary.path])
    for payload in ctx.files.runtime_payloads:
        arguments.add_all(["--payload", payload.path])
    arguments.add_all(["--instrument", ctx.executable._python.path])
    for argument in [
        "-B", "-S", ctx.file._capture.path,
        "--runtime", runtime.path,
        "--manifest", manifest.path,
        "--launcher", executable.path,
        "--template", template.path,
        "--validator", ctx.file._validator.path,
        "--machine", str(machine),
        "--",
    ]:
        arguments.add("--instrument-arg=" + argument)
    ctx.actions.run(
        executable = ctx.attr._python[DefaultInfo].files_to_run,
        arguments = [arguments],
        inputs = depset([ctx.file.binary, ctx.file._validator, ctx.file._capture, template] + sources + ctx.files.runtime_payloads, transitive = [ctx.attr.binary[DefaultInfo].default_runfiles.files, ctx.attr.binary[DefaultInfo].data_runfiles.files]),
        tools = [ctx.attr._python[DefaultInfo].files_to_run],
        outputs = [runtime, manifest, executable],
        env = {"PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONSAFEPATH": "1"},
        mnemonic = "PrepareLibyangTestRuntime",
        progress_message = "Validating and preparing target CLI runtime for %{label}",
    )
    # Keep the binary in its original runfiles location: its RPATH providers are
    # validated there. Never copy it into the flat library tree.
    runfiles = ctx.runfiles(files = [ctx.file.binary, ctx.executable._realpath, runtime, manifest])
    for target in [ctx.attr.binary, ctx.attr._realpath]:
        runfiles = runfiles.merge(target[DefaultInfo].default_runfiles).merge(target[DefaultInfo].data_runfiles)
    return [DefaultInfo(files = depset([executable]), executable = executable, runfiles = runfiles), OutputGroupInfo(runtime_manifest = depset([manifest]))]

prepared_test_runtime = rule(
    implementation = _impl,
    executable = True,
    attrs = {
        "binary": attr.label(allow_single_file = True, mandatory = True),
        "runtime_payloads": attr.label_list(allow_files = True, mandatory = True),
        "_python": attr.label(default = Label("@sonic_build_infra//tools/build_tools:python3"), executable = True, cfg = "exec"),
        "_realpath": attr.label(default = Label(":test_runtime_realpath"), executable = True, cfg = "exec"),
        "_validator": attr.label(default = Label("@sonic_build_infra//cc:runtime_test.py"), allow_single_file = True, cfg = "exec"),
        "_metadata": attr.label(default = Label("@sonic_build_infra//deb:elf_metadata"), providers = [PyInfo], cfg = "exec"),
        "_capture": attr.label(default = Label(":capture_test_runtime.py"), allow_single_file = True, cfg = "exec"),
        "_launcher_template": attr.label(default = Label(":prepared_test_runtime.sh.in"), allow_single_file = True, cfg = "exec"),
        "_x86_64": attr.label(default = Label("@platforms//cpu:x86_64")),
        "_aarch64": attr.label(default = Label("@platforms//cpu:aarch64")),
    },
)
