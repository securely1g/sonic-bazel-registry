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

# Both execution architectures use the same immutable multi-platform image.
# Changing the image also changes the metadata action's arguments/cache key.
SAI_BUILD_TOOLS_IMAGE = "ghcr.io/securely1g/sonic-build-tools@sha256:46fe4567b1565e71a8a6db0321469ef056636d7e7e5a8bb8fe51177e48ba3c86"
SAI_BUILD_TOOLS_RECIPE = "24883edfb6ff483c4b21ad7a0ff39485efe6837c15283caf5779f096f6773dd2"

def _container_tools_impl(ctx):
    return [platform_common.ToolchainInfo(
        image = SAI_BUILD_TOOLS_IMAGE,
        recipe = SAI_BUILD_TOOLS_RECIPE,
        doxygen = "/usr/bin/doxygen",
    )]

container_tools = rule(implementation = _container_tools_impl)
