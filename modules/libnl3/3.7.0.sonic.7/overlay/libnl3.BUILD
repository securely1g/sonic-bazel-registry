load("@bazel_skylib//rules:expand_template.bzl", "expand_template")
load("@rules_cc//cc:cc_shared_library.bzl", "cc_shared_library")
load("@rules_cc//cc:cc_static_library.bzl", "cc_static_library")
load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")
load("@rules_distroless//distroless:defs.bzl", "flatten")
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")
load("@tar.bzl", "mutate", "tar")
load("@sonic_build_infra//cc:direct_linker_inputs.bzl", "direct_linker_inputs")

MULTIARCH = {
    "x86_64": "x86_64-linux-gnu",
    "arm64": "aarch64-linux-gnu",
}

# =============================================================================
# Generated headers
# =============================================================================

expand_template(
    name = "defs_h",
    out = "lib/defs.h",
    substitutions = {
        "#undef DISABLE_PTHREADS\n": "/* #undef DISABLE_PTHREADS */\n",
        "#undef HAVE_DLFCN_H\n": "#define HAVE_DLFCN_H 1\n",
        "#undef HAVE_INTTYPES_H\n": "#define HAVE_INTTYPES_H 1\n",
        "#undef HAVE_LIBPTHREAD\n": "#define HAVE_LIBPTHREAD 1\n",
        "#undef HAVE_STDINT_H\n": "#define HAVE_STDINT_H 1\n",
        "#undef HAVE_STDIO_H\n": "#define HAVE_STDIO_H 1\n",
        "#undef HAVE_STDLIB_H\n": "#define HAVE_STDLIB_H 1\n",
        "#undef HAVE_STRERROR_L\n": "#define HAVE_STRERROR_L 1\n",
        "#undef HAVE_STRINGS_H\n": "#define HAVE_STRINGS_H 1\n",
        "#undef HAVE_STRING_H\n": "#define HAVE_STRING_H 1\n",
        "#undef HAVE_SYS_STAT_H\n": "#define HAVE_SYS_STAT_H 1\n",
        "#undef HAVE_SYS_TYPES_H\n": "#define HAVE_SYS_TYPES_H 1\n",
        "#undef HAVE_UNISTD_H\n": "#define HAVE_UNISTD_H 1\n",
        "#undef LT_OBJDIR\n": "#define LT_OBJDIR \".libs/\"\n",
        "#undef NL_DEBUG\n": "#define NL_DEBUG 1\n",
        "#undef PACKAGE\n": "#define PACKAGE \"libnl\"\n",
        "#undef PACKAGE_BUGREPORT\n": "#define PACKAGE_BUGREPORT \"\"\n",
        "#undef PACKAGE_NAME\n": "#define PACKAGE_NAME \"libnl\"\n",
        "#undef PACKAGE_STRING\n": "#define PACKAGE_STRING \"libnl 3.7.0\"\n",
        "#undef PACKAGE_TARNAME\n": "#define PACKAGE_TARNAME \"libnl\"\n",
        "#undef PACKAGE_URL\n": "#define PACKAGE_URL \"http://www.infradead.org/~tgr/libnl/\"\n",
        "#undef PACKAGE_VERSION\n": "#define PACKAGE_VERSION \"3.7.0\"\n",
        "#undef STDC_HEADERS\n": "#define STDC_HEADERS 1\n",
        "#undef VERSION\n": "#define VERSION \"3.7.0\"\n",
        "#undef const\n": "/* #undef const */\n",
        "#undef inline\n": "/* #undef inline */\n",
    },
    template = "lib/defs.h.in",
)

# =============================================================================
# Flex/Bison generated sources for libnl-route-3
# =============================================================================

# =============================================================================
# Header libraries
# =============================================================================

# Public header files for packaging.
filegroup(
    name = "public_header_files",
    srcs = glob(["include/netlink/**/*.h"]),
)

# Public headers: consumers use #include <netlink/...>
cc_library(
    name = "public_headers",
    hdrs = glob(["include/netlink/**/*.h"]),
    strip_include_prefix = "include",
    visibility = ["//visibility:public"],
)

# Compat headers: consumers use #include <libnl3/netlink/...>
# This matches the Debian libnl3-dev package layout.
cc_library(
    name = "public_headers_compat",
    hdrs = glob(["include/netlink/**/*.h"]),
    include_prefix = "libnl3",
    strip_include_prefix = "include",
    visibility = ["//visibility:public"],
)

# Private kernel headers must precede the toolchain's system kernel headers.
cc_library(
    name = "linux_private_headers",
    hdrs = glob(["include/linux-private/**/*.h"]),
    strip_include_prefix = "include/linux-private",
    features = ["-external_include_paths"],
)

# Includes netlink-private/ and the generated defs.h.
cc_library(
    name = "private_headers",
    hdrs = glob([
        "include/netlink-private/**/*.h",
    ]) + [":defs_h"],
    # _GNU_SOURCE is required by the private headers (e.g. struct ucred in
    # netlink-private/types.h). Propagate it to all consumers via defines.
    defines = ["_GNU_SOURCE"],
    # include/netlink-private/netlink.h uses #include <defs.h>,
    # so we need lib/ in the include path (where defs.h is generated).
    #
    includes = [
        "include",
        "lib",
    ],
    deps = [
        ":linux_private_headers",
        ":public_headers",
    ],
)

# =============================================================================
# Common build settings
# =============================================================================

LIBNL_COPTS = [
    "-g",
    "-fstack-protector-strong",
    "-Wformat",
    "-Werror=format-security",
    "-Wdate-time",
    "-D_FORTIFY_SOURCE=2",
    "-Wall",
    "-Wextra",
    "-Wmissing-prototypes",
    "-Wno-missing-field-initializers",
    "-Wpointer-arith",
    "-D_GNU_SOURCE",
    "-O2",
    # Suppress warnings from upstream third-party code.
    "-Wno-unused-parameter",
    "-Wno-sign-compare",
] + select({
    "@sonic_build_infra//platforms:bookworm": [],
    "//conditions:default": [
        "-Werror=implicit-function-declaration",
        "-fstack-clash-protection",
    ],
})

LIBNL_LIBRARY_COPTS = LIBNL_COPTS + ['-DSYSCONFDIR=\\"/etc/libnl-3\\"']

LIBNL_LINKOPTS = ["-Wl,-z,relro"]

[
    genrule(
        name = stem + "_" + kind + "_generated",
        srcs = [directory + stem + "_" + kind + extension],
        outs = [directory + stem + "_" + kind + suffix for suffix in [".c", ".h"]],
        cmd = "$(execpath @sonic_build_infra//tools/build_tools:" + tool + ") -o $(location " + directory + stem + "_" + kind + ".c) " + ("--defines=" if kind == "syntax" else "--header-file=") + "$(location " + directory + stem + "_" + kind + ".h) $(location " + directory + stem + "_" + kind + extension + ")",
        tools = ["@sonic_build_infra//tools/build_tools:" + tool],
    )
    for stem, directory in [
        ("pktloc", "lib/route/"),
        ("ematch", "lib/route/cls/"),
    ]
    for kind, extension, tool in [
        ("syntax", ".y", "bison"),
        ("grammar", ".l", "flex"),
    ]
]

[
    cc_library(
        name = stem + "_syntax",
        srcs = [":" + stem + "_syntax_generated"],
        copts = LIBNL_LIBRARY_COPTS,
        includes = [directory],
        implementation_deps = [":private_headers"],
    )
    for stem, directory in [
        ("pktloc", "lib/route"),
        ("ematch", "lib/route/cls"),
    ]
]

[
    alias(
        name = stem + "_grammar",
        actual = ":" + stem + "_grammar_generated",
    )
    for stem in [
        "pktloc",
        "ematch",
    ]
]

# =============================================================================
# Core library: libnl-3
# =============================================================================

cc_library(
    name = "libnl_3",
    srcs = glob(["lib/*.c"]),
    copts = LIBNL_LIBRARY_COPTS,
    linkopts = LIBNL_LINKOPTS,
    visibility = ["//visibility:public"],
    implementation_deps = [":private_headers"],
    deps = [
        ":public_headers",
        ":public_headers_compat",
    ],
)

cc_shared_library(
    name = "libnl_3_shared",
    additional_linker_inputs = ["libnl-3.sym"],
    user_link_flags = LIBNL_LINKOPTS + [
        "-Wl,--version-script=$(location libnl-3.sym)",
        "-Wl,-soname,libnl-3.so.200",
    ],
    visibility = ["//visibility:public"],
    deps = [":libnl_3"],
)

# =============================================================================
# Generic Netlink library: libnl-genl-3
# =============================================================================

cc_library(
    name = "libnl_genl_3",
    srcs = glob(["lib/genl/*.c"]),
    copts = LIBNL_LIBRARY_COPTS,
    visibility = ["//visibility:public"],
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
    ],
)

cc_shared_library(
    name = "libnl_genl_3_shared",
    additional_linker_inputs = ["libnl-genl-3.sym"],
    dynamic_deps = [":libnl_3_shared"],
    user_link_flags = LIBNL_LINKOPTS + [
        "-Wl,--version-script=$(location libnl-genl-3.sym)",
        "-Wl,-soname,libnl-genl-3.so.200",
    ],
    visibility = ["//visibility:public"],
    deps = [":libnl_genl_3"],
)

# =============================================================================
# Route library: libnl-route-3
# =============================================================================

cc_library(
    name = "libnl_route_3",
    srcs = glob(
        [
            "lib/route/*.c",
            "lib/route/**/*.c",
            "lib/fib_lookup/*.c",
        ],
    ) + [
        ":ematch_grammar",
        ":pktloc_grammar",
    ],
    copts = LIBNL_LIBRARY_COPTS,
    visibility = ["//visibility:public"],
    implementation_deps = [":private_headers"],
    deps = [
        ":ematch_syntax",
        ":libnl_3",
        ":pktloc_syntax",
    ],
)

cc_shared_library(
    name = "libnl_route_3_shared",
    additional_linker_inputs = ["libnl-route-3.sym"],
    dynamic_deps = [":libnl_3_shared"],
    user_link_flags = LIBNL_LINKOPTS + [
        "-Wl,--version-script=$(location libnl-route-3.sym)",
        "-Wl,-soname,libnl-route-3.so.200",
    ],
    visibility = ["//visibility:public"],
    deps = [":libnl_route_3"],
)

# =============================================================================
# Netfilter library: libnl-nf-3
# =============================================================================

cc_library(
    name = "libnl_nf_3",
    srcs = glob(["lib/netfilter/*.c"]),
    copts = LIBNL_LIBRARY_COPTS,
    visibility = ["//visibility:public"],
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_nf_3_shared",
    additional_linker_inputs = ["libnl-nf-3.sym"],
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_route_3_shared",
    ],
    user_link_flags = LIBNL_LINKOPTS + [
        "-Wl,--version-script=$(location libnl-nf-3.sym)",
        "-Wl,-soname,libnl-nf-3.so.200",
    ],
    visibility = ["//visibility:public"],
    deps = [":libnl_nf_3"],
)

# =============================================================================
# CLI library: libnl-cli-3
# =============================================================================

cc_library(
    name = "libnl_cli_3",
    srcs = glob(["src/lib/*.c"]),
    copts = LIBNL_COPTS + ['-DSYSCONFDIR=\\"/etc\\"'],
    defines = select({
        "@platforms//cpu:" + cpu: ['PKGLIBDIR=\\"/usr/lib/{}/libnl-3\\"'.format(multiarch)]
        for cpu, multiarch in MULTIARCH.items()
    }),
    visibility = ["//visibility:public"],
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_genl_3",
        ":libnl_nf_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_3_shared",
    additional_linker_inputs = ["libnl-cli-3.sym"],
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_genl_3_shared",
        ":libnl_nf_3_shared",
        ":libnl_route_3_shared",
    ],
    user_link_flags = LIBNL_LINKOPTS + [
        "-Wl,--version-script=$(location libnl-cli-3.sym)",
        "-Wl,-soname,libnl-cli-3.so.200",
    ],
    visibility = ["//visibility:public"],
    deps = [":libnl_cli_3"],
)

# CLI plugin shared objects installed under the target multiarch libnl-3/cli directory.
# These are loadable modules (not linked libraries), built as individual .so files.

cc_library(
    name = "libnl_cli_cls_basic",
    srcs = ["lib/cli/cls/basic.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_cls_basic_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_cls_basic"],
)

cc_library(
    name = "libnl_cli_cls_cgroup",
    srcs = ["lib/cli/cls/cgroup.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_cls_cgroup_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_cls_cgroup"],
)

cc_library(
    name = "libnl_cli_qdisc_bfifo",
    srcs = ["lib/cli/qdisc/bfifo.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_bfifo_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_bfifo"],
)

cc_library(
    name = "libnl_cli_qdisc_blackhole",
    srcs = ["lib/cli/qdisc/blackhole.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_blackhole_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_blackhole"],
)

cc_library(
    name = "libnl_cli_qdisc_fq_codel",
    srcs = ["lib/cli/qdisc/fq_codel.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_fq_codel_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_fq_codel"],
)

cc_library(
    name = "libnl_cli_qdisc_hfsc",
    srcs = ["lib/cli/qdisc/hfsc.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_hfsc_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_hfsc"],
)

cc_library(
    name = "libnl_cli_qdisc_htb",
    srcs = ["lib/cli/qdisc/htb.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_htb_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_htb"],
)

cc_library(
    name = "libnl_cli_qdisc_ingress",
    srcs = ["lib/cli/qdisc/ingress.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_ingress_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_ingress"],
)

cc_library(
    name = "libnl_cli_qdisc_pfifo",
    srcs = ["lib/cli/qdisc/pfifo.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_pfifo_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_pfifo"],
)

cc_library(
    name = "libnl_cli_qdisc_plug",
    srcs = ["lib/cli/qdisc/plug.c"],
    copts = LIBNL_LIBRARY_COPTS,
    implementation_deps = [":private_headers"],
    deps = [
        ":libnl_3",
        ":libnl_cli_3",
        ":libnl_route_3",
    ],
)

cc_shared_library(
    name = "libnl_cli_qdisc_plug_shared",
    dynamic_deps = [
        ":libnl_3_shared",
        ":libnl_cli_3_shared",
        ":libnl_route_3_shared",
    ],
    deps = [":libnl_cli_qdisc_plug"],
)

# Runtime paths match the upstream libtool ABI version and Debian layout.
RUNTIME_LIBRARIES = {
    "libnl-3": ":libnl_3_shared",
    "libnl-genl-3": ":libnl_genl_3_shared",
    "libnl-route-3": ":libnl_route_3_shared",
    "libnl-nf-3": ":libnl_nf_3_shared",
    "libnl-cli-3": ":libnl_cli_3_shared",
}

CLI_PLUGINS = {
    "cls/basic.so": ":libnl_cli_cls_basic_shared",
    "cls/cgroup.so": ":libnl_cli_cls_cgroup_shared",
    "qdisc/bfifo.so": ":libnl_cli_qdisc_bfifo_shared",
    "qdisc/blackhole.so": ":libnl_cli_qdisc_blackhole_shared",
    "qdisc/fq_codel.so": ":libnl_cli_qdisc_fq_codel_shared",
    "qdisc/hfsc.so": ":libnl_cli_qdisc_hfsc_shared",
    "qdisc/htb.so": ":libnl_cli_qdisc_htb_shared",
    "qdisc/ingress.so": ":libnl_cli_qdisc_ingress_shared",
    "qdisc/pfifo.so": ":libnl_cli_qdisc_pfifo_shared",
    "qdisc/plug.so": ":libnl_cli_qdisc_plug_shared",
}

[
    sonic_deploy_tar(
        name = stem + kind + "_" + cpu,
        srcs = [
            "etc/classid",
            "etc/pktloc",
        ] if stem == "libnl-3" else [],
        binaries = {
            "usr/lib/{}/{}.so.200.26.0 uid=0 gid=0 mode=0644 type=file".format(multiarch, stem): binary,
        } | ({
            "usr/lib/{}/libnl-3/cli/{} uid=0 gid=0 mode=0644 type=file".format(multiarch, path): plugin
            for path, plugin in CLI_PLUGINS.items()
        } if stem == "libnl-cli-3" else {}),
        force_debug_build = True,
        mtree = [
            "usr/lib/{}/{}.so.200 uid=0 gid=0 type=link time=0 link={}.so.200.26.0".format(multiarch, stem, stem),
        ] + ([
            "usr/lib/{}/{}.so uid=0 gid=0 type=link time=0 link={}.so.200".format(multiarch, stem, stem),
        ] if kind == "_pkg" else []) + ([
            "etc/libnl-3/{} uid=0 gid=0 mode=0644 type=file content=$(location etc/{})".format(name, name)
            for name in [
                "classid",
                "pktloc",
            ]
        ] if stem == "libnl-3" else []),
        target_compatible_with = ["@platforms//cpu:" + cpu],
        visibility = ["//visibility:public"],
    )
    for stem, binary in RUNTIME_LIBRARIES.items()
    for kind in [
        "_pkg",
        "-runtime_files",
    ]
    for cpu, multiarch in MULTIARCH.items()
]

[
    alias(
        name = stem + "_pkg" + suffix,
        actual = select({
            "@platforms//cpu:" + cpu: ":" + stem + "_pkg_" + cpu + suffix
            for cpu in MULTIARCH
        }),
        visibility = ["//visibility:public"],
    )
    for stem in RUNTIME_LIBRARIES
    for suffix in [
        "",
        ".debug_symbols",
    ]
]

# =============================================================================
# Packaging: headers tarball
# =============================================================================

tar(
    name = "libnl3-dev_headers",
    srcs = glob(["include/netlink/**/*.h"]),
    mtree = [
        "usr/include/libnl3/{} uid=0 gid=0 mode=0644 type=file content=$(location {})".format(
            path.removeprefix("include/"),
            path,
        )
        for path in glob(["include/netlink/**/*.h"])
    ],
    visibility = ["//visibility:public"],
)

# =============================================================================
# Packaging: pkgconfig files
# =============================================================================

# Generate pkg-config metadata for the installed library layout.
[
    expand_template(
        name = name + "_" + cpu,
        out = cpu + "/" + stem + ".0.pc",
        substitutions = {
            "@prefix@": "/usr",
            "@exec_prefix@": "${prefix}",
            "@libdir@": "${prefix}/lib/" + multiarch,
            "@includedir@": "${prefix}/include",
            "@PACKAGE_VERSION@": "3.7.0",
            "@MAJ_VERSION@": "3",
            "@LIBS@": "-lpthread ",
        },
        target_compatible_with = ["@platforms//cpu:" + cpu],
        template = stem + ".0.pc.in",
        visibility = ["//visibility:public"],
    )
    for name, stem in [
        ("libnl3_pc_generated", "libnl-3"),
        ("libnl3_genl_pc_generated", "libnl-genl-3"),
        ("libnl3_route_pc_generated", "libnl-route-3"),
        ("libnl3_nf_pc_generated", "libnl-nf-3"),
        ("libnl3_cli_pc_generated", "libnl-cli-3"),
    ]
    for cpu, multiarch in MULTIARCH.items()
]

[
    alias(
        name = name,
        actual = select({"@platforms//cpu:" + cpu: ":" + name + "_" + cpu for cpu in MULTIARCH}),
        visibility = ["//visibility:public"],
    )
    for name in [
        "libnl3_pc_generated",
        "libnl3_genl_pc_generated",
        "libnl3_route_pc_generated",
        "libnl3_nf_pc_generated",
        "libnl3_cli_pc_generated",
    ]
]

[
    tar(
        name = "libnl3_pkgconfig_" + cpu,
        srcs = [
            ":libnl3_cli_pc_generated",
            ":libnl3_genl_pc_generated",
            ":libnl3_nf_pc_generated",
            ":libnl3_pc_generated",
            ":libnl3_route_pc_generated",
        ],
        mutate = mutate(
            package_dir = "./usr/lib/" + multiarch + "/pkgconfig",
            strip_prefix = package_name(),
        ),
        target_compatible_with = ["@platforms//cpu:" + cpu],
    )
    for cpu, multiarch in MULTIARCH.items()
]

alias(
    name = "libnl3_pkgconfig",
    actual = select({
        "@platforms//cpu:" + cpu: ":libnl3_pkgconfig_" + cpu
        for cpu in MULTIARCH
    }),
)

# =============================================================================
# Packaging: -dev package tarballs (runtime + headers + pkgconfig)
# =============================================================================

flatten(
    name = "libnl-3-dev_pkg",
    deduplicate = True,
    tars = [
        ":libnl-3_pkg",
        ":libnl3-dev_headers",
        ":libnl3_pkgconfig",
    ],
    visibility = ["//visibility:public"],
)

flatten(
    name = "libnl-genl-3-dev_pkg",
    deduplicate = True,
    tars = [
        ":libnl-genl-3_pkg",
        ":libnl-3-dev_pkg",
    ],
    visibility = ["//visibility:public"],
)

flatten(
    name = "libnl-route-3-dev_pkg",
    deduplicate = True,
    tars = [
        ":libnl-route-3_pkg",
        ":libnl-3-dev_pkg",
    ],
    visibility = ["//visibility:public"],
)

flatten(
    name = "libnl-nf-3-dev_pkg",
    tars = [
        ":libnl-nf-3_pkg",
        ":libnl-3-dev_pkg",
        ":libnl-route-3_pkg",
    ],
    visibility = ["//visibility:public"],
)

# libnl-cli-3-dev only contains the unversioned symlink and pkgconfig;
# the runtime .so and plugins are in libnl-cli-3_pkg.
flatten(
    name = "libnl-cli-3-dev_pkg",
    deduplicate = True,
    tars = [
        ":libnl-cli-3_pkg",
        ":libnl-3-dev_pkg",
    ],
    visibility = ["//visibility:public"],
)

# Exact development-file splits from Debian 3.7.0-0.2's *.install manifests.
# The older *_dev_pkg targets above remain aggregate SDKs for compatibility.
direct_linker_inputs(
    name = "route_archive_inputs",
    deps = [
        ":ematch_syntax",
        ":libnl_route_3",
        ":pktloc_syntax",
    ],
)

cc_static_library(
    name = "core_archive",
    visibility = ["//visibility:public"],
    deps = [":libnl_3"],
)

cc_static_library(
    name = "route_archive",
    visibility = ["//visibility:public"],
    deps = [":route_archive_inputs"],
)

[
    tar(
        name = stem + "-dev_library_files_" + cpu,
        srcs = [
            archive,
            pc,
        ],
        mtree = [
            "usr/lib/{}/{}.a uid=0 gid=0 mode=0644 type=file content=$(location {})".format(multiarch, stem, archive),
            "usr/lib/{}/{}.so uid=0 gid=0 type=link time=0 link={}.so.200".format(multiarch, stem, stem),
            "usr/lib/{}/pkgconfig/{}.0.pc uid=0 gid=0 mode=0644 type=file content=$(location {})".format(multiarch, stem, pc),
        ],
        target_compatible_with = ["@platforms//cpu:" + cpu],
    )
    for stem, archive, pc in [
        ("libnl-3", ":core_archive", ":libnl3_pc_generated"),
        ("libnl-route-3", ":route_archive", ":libnl3_route_pc_generated"),
    ]
    for cpu, multiarch in MULTIARCH.items()
]

[
    alias(
        name = stem + "-dev_library_files",
        actual = select({
            "@platforms//cpu:" + cpu: ":" + stem + "-dev_library_files_" + cpu
            for cpu in MULTIARCH
        }),
    )
    for stem in [
        "libnl-3",
        "libnl-route-3",
    ]
]

flatten(
    name = "libnl-3-dev_files",
    tars = [
        ":libnl-3-dev_library_files",
        ":libnl3-dev_headers",
    ],
    visibility = ["//visibility:public"],
)

alias(
    name = "libnl-route-3-dev_files",
    actual = ":libnl-route-3-dev_library_files",
    visibility = ["//visibility:public"],
)

[
    alias(
        name = stem + "-runtime_files" + suffix,
        actual = select({
            "@platforms//cpu:" + cpu: ":" + stem + "-runtime_files_" + cpu + suffix
            for cpu in MULTIARCH
        }),
        visibility = ["//visibility:public"],
    )
    for stem in RUNTIME_LIBRARIES
    for suffix in [
        "",
        ".debug_symbols",
    ]
]

# Additional upstream libraries used by the complete native CLI program set.
[
    cc_library(
        name = "libnl_" + kind + "_3",
        srcs = glob(["lib/" + kind + "/*.c"]),
        copts = LIBNL_LIBRARY_COPTS,
        implementation_deps = [":private_headers"],
        deps = [
            ":libnl_3",
        ],
    )
    for kind in [
        "idiag",
        "xfrm",
    ]
]

[
    cc_shared_library(
        name = "libnl_" + kind + "_3_shared",
        additional_linker_inputs = ["libnl-" + kind + "-3.sym"],
        dynamic_deps = [":libnl_3_shared"],
        user_link_flags = LIBNL_LINKOPTS + [
            "-Wl,--version-script=$(location libnl-" + kind + "-3.sym)",
            "-Wl,-soname,libnl-" + kind + "-3.so.200",
        ],
        deps = [":libnl_" + kind + "_3"],
    )
    for kind in [
        "idiag",
        "xfrm",
    ]
]

# Build every CLI program, independent of DEB selection.
[
    cc_binary(
        name = path.removesuffix(".c"),
        srcs = [path],
        copts = LIBNL_LIBRARY_COPTS,
        dynamic_deps = [":" + name + "_shared" for name in [
            "libnl_3",
            "libnl_genl_3",
            "libnl_route_3",
            "libnl_nf_3",
            "libnl_cli_3",
            "libnl_idiag_3",
        ]],
        linkopts = LIBNL_LINKOPTS + ["-ldl"],
        visibility = ["//visibility:public"],
        deps = [
            ":libnl_cli_3",
            ":libnl_idiag_3",
            ":private_headers",
        ],
    )
    for path in glob(["src/*.c"])
]

filegroup(
    name = "programs",
    srcs = [path.removesuffix(".c") for path in glob(["src/*.c"])],
    visibility = ["//visibility:public"],
)

# Debian -dev archives contain direct library objects, never transitive libs.
[
    direct_linker_inputs(
        name = name + "_archive_inputs",
        deps = [":" + name],
    )
    for name in [
        "libnl_genl_3",
        "libnl_nf_3",
        "libnl_cli_3",
        "libnl_idiag_3",
        "libnl_xfrm_3",
    ] + [label.removesuffix("_shared").removeprefix(":") for label in CLI_PLUGINS.values()]
]

[
    cc_static_library(
        name = name + "_archive",
        visibility = ["//visibility:public"],
        deps = [":" + name + "_archive_inputs"],
    )
    for name in [
        "libnl_genl_3",
        "libnl_nf_3",
        "libnl_cli_3",
        "libnl_idiag_3",
        "libnl_xfrm_3",
    ] + [label.removesuffix("_shared").removeprefix(":") for label in CLI_PLUGINS.values()]
]


# Build every unconditional upstream test program.
[
    cc_binary(
        name = path.removesuffix(".c"),
        srcs = [path],
        copts = LIBNL_LIBRARY_COPTS,
        dynamic_deps = [":" + name + "_shared" for name in [
            "libnl_3",
            "libnl_genl_3",
            "libnl_route_3",
            "libnl_nf_3",
            "libnl_cli_3",
        ]],
        linkopts = LIBNL_LINKOPTS + ["-ldl"],
        visibility = ["//visibility:public"],
        deps = [
            ":libnl_cli_3",
            ":private_headers",
        ],
    )
    for path in glob(["tests/test-*.c"])
]

filegroup(
    name = "check_programs",
    srcs = [path.removesuffix(".c") for path in glob(["tests/test-*.c"])],
    visibility = ["//visibility:public"],
)

exports_files([
    "ChangeLog",
])

filegroup(
    name = "all_libraries",
    srcs = [":" + name + "_shared" for name in [
        "libnl_3",
        "libnl_genl_3",
        "libnl_route_3",
        "libnl_nf_3",
        "libnl_cli_3",
        "libnl_idiag_3",
        "libnl_xfrm_3",
    ]] + [
        ":core_archive",
        ":route_archive",
    ] + [":" + name + "_archive" for name in [
        "libnl_genl_3",
        "libnl_nf_3",
        "libnl_cli_3",
        "libnl_idiag_3",
        "libnl_xfrm_3",
    ]],
    visibility = ["//visibility:public"],
)
