load("@rules_pkg//pkg:tar.bzl", "pkg_tar")

"""Package libnl's existing Bazel payloads with its original Debian metadata."""

load("@rules_distroless//distroless:defs.bzl", "flatten")
load("@sonic_build_infra//deb:metadata.bzl", "debian_library", "debian_metadata")
load("@sonic_build_infra//deb:sonic_deb.bzl", "sonic_deb")
load("@tar.bzl", "tar")

_VERSION = "3.7.0-0.2+b1sonic1"
_TOOLS = "@sonic_build_infra//tools/build_tools:"

def libnl_debian_package(name, package, data, dependencies = [], library = True, conffiles = False):
    """Keep each binary package's data, ABI metadata and control together."""
    tar(
        name = name + "_documentation",
        srcs = ["@libnl3_debian//:copyright", "@libnl3_debian//:changelog"],
        mtree = [
            "usr/share/doc/%s/copyright uid=0 gid=0 mode=0644 type=file content=$(location @libnl3_debian//:copyright)" % package,
            "usr/share/doc/%s/changelog.Debian uid=0 gid=0 mode=0644 type=file content=$(location @libnl3_debian//:changelog)" % package,
        ],
    )
    flatten(name = name + "_debian_contents", tars = [data, ":" + name + "_documentation"])
    pkg_tar(name = name + "_debian_data", deps = [":" + name + "_debian_contents"], create_parents = True)
    controls = (["shlibs", "symbols", "triggers"] if library else []) + (["conffiles"] if conffiles else [])
    native.genrule(
        name = name + "_debhelper",
        srcs = [":" + name + "_debian_data", "@libnl3_debian//:source_files", "@libnl3_debian//:control"],
        outs = [name + "/" + filename for filename in controls + ["substvars"]],
        tools = [_TOOLS + "dh_installdeb"] + ([_TOOLS + "dh_makeshlibs"] if library else []),
        toolchains = ["@bsd_tar_toolchains//:resolved_toolchain"],
        cmd = """
set -eu
execroot=$$PWD
out=$$execroot/$(RULEDIR)/{name}
work=$$(mktemp -d)
trap 'rm -rf "$$work"' EXIT
mkdir -p "$$work/debian" "$$out"
cp -R "$$(dirname $(location @libnl3_debian//:control))/". "$$work/debian/"
chmod -R u+w "$$work/debian"
mkdir -p "$$work/debian/{package}"
"$(BSDTAR_BIN)" -xf $(location :{name}_debian_data) -C "$$work/debian/{package}"
cd "$$work"
{makeshlibs}
"$$execroot/$(execpath {tools}dh_installdeb)" -p{package}
: >> "debian/{package}.substvars"
cp "debian/{package}.substvars" "$$out/substvars"
{copy_controls}
""".format(
            name = name,
            package = package,
            tools = _TOOLS,
            # SONiC intentionally keeps upstream ELF symbol versions. Its Make
            # build uses -c0 against Debian's older, unversioned symbol template.
            makeshlibs = '"$$execroot/$(execpath %sdh_makeshlibs)" -p%s -- -c0' % (_TOOLS, package) if library else "",
            copy_controls = "\n".join(['cp "debian/%s/DEBIAN/%s" "$$out/%s"' % (package, filename, filename) for filename in controls]),
        ),
    )
    if library:
        debian_library(
            name = name + "_debian_metadata",
            data = ":" + name + "_debian_data",
            symbols = ":" + name + "/symbols",
            shlibs = ":" + name + "/shlibs",
            visibility = ["//visibility:public"],
        )
    debian_metadata(
        name = name + "_debian_control",
        data = ":" + name + "_debian_data",
        control = "@libnl3_debian//:control",
        changelog = "@libnl3_debian//:changelog",
        package = package,
        dependencies = dependencies,
        substvars = ":" + name + "/substvars",
    )
    sonic_deb(
        name = name + "_deb",
        package = package,
        version = _VERSION,
        data = ":" + name + "_debian_data",
        control_file = ":" + name + "_debian_control",
        control_files = {":" + name + "/" + filename: filename for filename in controls},
        visibility = ["//visibility:public"],
    )
