"""Execution-configuration runtimes for the SAI generators."""

PythonRuntimeInfo = provider(
    "Declared Python interpreter and runtime files for execution tools.",
    fields = ["interpreter", "files"],
)

def _python_runtime_impl(ctx):
    runtime = ctx.toolchains["@rules_python//python:toolchain_type"].py3_runtime
    if runtime == None or runtime.interpreter == None:
        fail("SAI generators require a declared Python 3 interpreter")
    return [
        PythonRuntimeInfo(interpreter = runtime.interpreter, files = runtime.files),
        DefaultInfo(files = runtime.files),
    ]

python_runtime = rule(
    implementation = _python_runtime_impl,
    toolchains = ["@rules_python//python:toolchain_type"],
)

def _perl_test_runtime_impl(ctx):
    runtime = ctx.toolchains["@rules_perl//perl:exec_toolchain_type"].perl_runtime
    interpreter = runtime.interpreter.short_path
    if interpreter.startswith("../"):
        interpreter = interpreter[3:]
    else:
        interpreter = ctx.workspace_name + "/" + interpreter
    manifest = ctx.actions.declare_file(ctx.label.name + ".json")
    ctx.actions.write(manifest, json.encode({
        "interpreter": interpreter,
        "options": runtime.perlopt,
    }))
    return [DefaultInfo(
        files = depset([manifest]),
        runfiles = ctx.runfiles(transitive_files = runtime.runtime),
    )]

perl_test_runtime = rule(
    implementation = _perl_test_runtime_impl,
    toolchains = ["@rules_perl//perl:exec_toolchain_type"],
)
