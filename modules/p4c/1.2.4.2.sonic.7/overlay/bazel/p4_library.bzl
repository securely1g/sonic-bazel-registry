"""P4 compilation rules backed by SONiC's hermetic p4c_tool binaries."""

def _extract_common_p4c_args(ctx):
    """Extract common arguments for p4c build rules."""
    p4file = ctx.file.src
    args = [
        '"{}"'.format(p4file.path),
        "--std",
        '"{}"'.format(ctx.attr.std),
        "--arch",
        '"{}"'.format(ctx.attr.arch),
    ]

    # Omit _p4include here so p4c_tool's P4C_16_INCLUDE_PATH matches ToP4's
    # system-header prefix while still staging deps and workspace include dirs.
    include_dirs = {d.dirname: 0 for d in ctx.files.deps}
    include_dirs[p4file.dirname] = 0
    include_dirs["."] = 0
    if p4file.owner.workspace_root:
        include_dirs[p4file.owner.workspace_root] = 0
    if ctx.label.workspace_root:
        include_dirs[ctx.label.workspace_root] = 0
    args += ['"-I{}"'.format(directory) for directory in include_dirs.keys()]

    return args

def _extract_p4c_inputs(ctx):
    """Extract input P4 files to pass to p4c from the build rule context."""
    return ctx.files._p4include + ctx.files.deps + [ctx.file.src]

def _p4_library_impl(ctx):
    p4c = ctx.executable.p4c_backend
    p4file = ctx.file.src
    target = ctx.attr.target
    args = _extract_common_p4c_args(ctx)
    args += ["--target", '"{}"'.format(target if target else "bmv2")]

    if ctx.attr.extra_args:
        args.append(ctx.attr.extra_args)

    outputs = []

    if ctx.outputs.bf_rt_schema_out:
        if target != "dpdk":
            fail('Must use `target = "dpdk"` when specifying bf_rt_schema_out.')
        args += ["--bf-rt-schema", '"{}"'.format(ctx.outputs.bf_rt_schema_out.path)]
        outputs.append(ctx.outputs.bf_rt_schema_out)

    if ctx.outputs.context_out:
        if target != "dpdk":
            fail('Must use `target = "dpdk"` when specifying context_out.')
        args += ["--context", '"{}"'.format(ctx.outputs.context_out.path)]
        outputs.append(ctx.outputs.context_out)

    if ctx.outputs.p4info_out:
        if target != "" and target != "bmv2":
            fail('Must use `target = "bmv2"` when specifying p4info_out.')
        args += ["--p4runtime-files", '"{}"'.format(ctx.outputs.p4info_out.path)]
        outputs.append(ctx.outputs.p4info_out)

    if ctx.outputs.target_out:
        if not target:
            fail("Cannot specify target_out without specifying target explicitly.")
        args += ["-o", '"{}"'.format(ctx.outputs.target_out.path)]
        outputs.append(ctx.outputs.target_out)

    if not outputs:
        fail("No outputs specified. Must specify p4info_out or target_out or both.")

    ctx.actions.run_shell(
        command = 'exec "{p4c}" {p4c_args}'.format(
            p4c = p4c.path,
            p4c_args = " ".join(args),
        ),
        inputs = _extract_p4c_inputs(ctx),
        outputs = outputs,
        tools = [ctx.attr.p4c_backend[DefaultInfo].files_to_run],
        mnemonic = "P4Compile",
        progress_message = "Compiling P4 program %s" % p4file.short_path,
    )

    return [DefaultInfo(files = depset(outputs), runfiles = ctx.runfiles(files = outputs))]

p4_library = rule(
    doc = "Compiles P4 program using the p4c compiler.",
    implementation = _p4_library_impl,
    attrs = {
        "src": attr.label(
            doc = "P4 source file to pass to p4c.",
            mandatory = True,
            allow_single_file = [".p4"],
        ),
        "deps": attr.label_list(
            doc = "Additional P4 dependencies (optional). Use for #include-ed files.",
            mandatory = False,
            allow_files = [".p4", ".h"],
            default = [],
        ),
        "bf_rt_schema_out": attr.output(
            mandatory = False,
            doc = "The name of the dpdk bf rt schema output file.",
        ),
        "context_out": attr.output(
            mandatory = False,
            doc = "The name of the dpdk context output file.",
        ),
        "p4info_out": attr.output(
            mandatory = False,
            doc = "The name of the p4info output file.",
        ),
        "target_out": attr.output(
            mandatory = False,
            doc = "The name of the target output file, passed to p4c via -o.",
        ),
        "target": attr.string(
            doc = "The --target argument passed to p4c (default: bmv2).",
            mandatory = False,
            default = "",
        ),
        "arch": attr.string(
            doc = "The --arch argument passed to p4c (default: v1model).",
            mandatory = False,
            default = "v1model",
        ),
        "std": attr.string(
            doc = "The --std argument passed to p4c (default: p4-16).",
            mandatory = False,
            default = "p4-16",
        ),
        "extra_args": attr.string(
            doc = "String of additional command line arguments to pass to p4c.",
            mandatory = False,
            default = "",
        ),
        "p4c_backend": attr.label(
            default = Label("//:p4c_bm2_ss"),
            executable = True,
            cfg = "exec",
        ),
        "_p4include": attr.label(
            default = Label("//p4include"),
            allow_files = [".p4", ".h"],
        ),
    },
)

def _p4_graphs_impl(ctx):
    p4c = ctx.executable.p4c_backend
    p4file = ctx.file.src
    output_file = ctx.outputs.out

    if not output_file.path.lower().endswith(".dot"):
        fail("The output graph file must have extension .dot")

    args = _extract_common_p4c_args(ctx)
    graph_dir = output_file.path + "-graphs-dir"
    args += ["--graphs-dir", '"{}"'.format(graph_dir)]
    if ctx.attr.extra_args:
        args.append(ctx.attr.extra_args)

    ctx.actions.run_shell(
        command = "\n".join([
            'rm -rf "{graph_dir}" && mkdir -p "{graph_dir}"',
            '"{p4c}" {p4c_args}',
            'cat "{graph_dir}"/* > "{output_file}"',
        ]).format(
            p4c = p4c.path,
            p4c_args = " ".join(args),
            graph_dir = graph_dir,
            output_file = output_file.path,
        ),
        inputs = _extract_p4c_inputs(ctx),
        outputs = [output_file],
        tools = [ctx.attr.p4c_backend[DefaultInfo].files_to_run],
        mnemonic = "P4Graphs",
        progress_message = "Generating the graphs for P4 program %s" % p4file.short_path,
    )

    return [DefaultInfo(files = depset([output_file]), runfiles = ctx.runfiles(files = [output_file]))]

p4_graphs = rule(
    doc = "Generates the graphs for a P4 program using p4c-graphs, and merges them in a single GraphViz file.",
    implementation = _p4_graphs_impl,
    attrs = {
        "src": attr.label(
            doc = "P4 source file to pass to p4c.",
            mandatory = True,
            allow_single_file = [".p4"],
        ),
        "deps": attr.label_list(
            doc = "Additional P4 dependencies (optional). Use for #include-ed files.",
            mandatory = False,
            allow_files = [".p4", ".h"],
            default = [],
        ),
        "out": attr.output(
            doc = "The name of the output DOT file",
            mandatory = True,
        ),
        "arch": attr.string(
            doc = "The --arch argument passed to p4c (default: v1model).",
            mandatory = False,
            default = "v1model",
        ),
        "std": attr.string(
            doc = "The --std argument passed to p4c (default: p4-16).",
            mandatory = False,
            default = "p4-16",
        ),
        "extra_args": attr.string(
            doc = "String of additional command line arguments to pass to p4c.",
            mandatory = False,
            default = "",
        ),
        "p4c_backend": attr.label(
            default = Label("//:p4c_graphs"),
            executable = True,
            cfg = "exec",
        ),
        "_p4include": attr.label(
            default = Label("//p4include"),
            allow_files = [".p4", ".h"],
        ),
    },
)
