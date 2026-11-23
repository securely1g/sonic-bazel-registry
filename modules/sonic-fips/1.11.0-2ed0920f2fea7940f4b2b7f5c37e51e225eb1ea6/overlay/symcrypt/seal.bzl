"""Strip the SymCrypt ELF before its upstream FIPS integrity postprocessing."""
load("@sonic_build_infra//binary:debug_symbols.bzl", "DebugSymbolsInfo")
load("@sonic_build_infra//toolchains/binutils:binutils_toolchain.bzl", "BINUTILS_TOOLCHAIN_TYPE")

def _seal_impl(ctx):
    elf = ctx.actions.declare_file(ctx.label.name + "/libsymcrypt.so.103.13.0")
    debug = ctx.actions.declare_directory(ctx.label.name + ".debug")
    evidence = ctx.actions.declare_directory(ctx.label.name + ".processing")
    binutils = ctx.toolchains[BINUTILS_TOOLCHAIN_TYPE].binutils
    processor = ctx.attr.processor[DefaultInfo].files_to_run
    gawk = ctx.attr.gawk[DefaultInfo].files_to_run
    # Copying this single linked ELF is the required installation transformation.
    # No source/header tree is staged or modified. All ELF edits precede sealing.
    ctx.actions.run_shell(
        inputs = [ctx.file.src],
        outputs = [elf, debug, evidence],
        tools = [binutils.objcopy, binutils.readelf, processor, gawk],
        arguments = [ctx.file.src.path, elf.path, debug.path, evidence.path,
                     binutils.objcopy.executable.path, binutils.readelf.executable.path,
                     gawk.executable.path, processor.executable.path],
        command = """set -euo pipefail
id=$("$6" -n "$1" | "$7" '/Build ID:/ { print $NF }')
[[ -n "$id" ]]
symbols="$3/.build-id/${id:0:2}/${id:2}.debug"
mkdir -p "${symbols%/*}" "$4" "${2%/*}"
"$5" --only-keep-debug "$1" "$symbols"
"$5" --strip-unneeded -K SymCryptVolatileFipsHmacKey -K SymCryptVolatileFipsHmacKeyRva -K SymCryptVolatileFipsBoundaryOffset -K SymCryptVolatileFipsHmacDigest "$1" "$2"
"$5" --add-gnu-debuglink="$symbols" "$2"
"$8" "$2" -p "$4" -d
""",
        mnemonic = "SymCryptFipsSeal",
    )
    return [DefaultInfo(files = depset([elf])), DebugSymbolsInfo(symbols = depset([debug])),
            OutputGroupInfo(debug = depset([debug]), processing = depset([evidence]))]

symcrypt_seal = rule(
    implementation = _seal_impl,
    attrs = {
        "src": attr.label(allow_single_file = True, mandatory = True),
        "processor": attr.label(executable = True, cfg = "exec", mandatory = True),
        "gawk": attr.label(executable = True, cfg = "exec", default = Label("@sonic_build_infra//tools/build_tools:gawk")),
    },
    toolchains = [BINUTILS_TOOLCHAIN_TYPE],
)

def _runtime_impl(ctx):
    tar = ctx.attr.tar[DefaultInfo]
    return [DefaultInfo(files = tar.files, runfiles = tar.default_runfiles),
            DebugSymbolsInfo(symbols = depset(transitive = [x[DebugSymbolsInfo].symbols for x in ctx.attr.components]))]

sealed_runtime = rule(
    implementation = _runtime_impl,
    attrs = {"tar": attr.label(mandatory = True), "components": attr.label_list(providers = [DebugSymbolsInfo])},
)
