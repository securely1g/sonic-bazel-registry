"""Original Debian kernel sources, shared by standalone and image consumers."""

load("@bazel_tools//tools/build_defs/repo:http.bzl", "http_file")
load("@sonic_build_infra//source:prepared_source.bzl", "prepared_source")
load("@sonic_build_infra//source:patch_tools.bzl", "patch_tools_repository")

KERNEL_SOURCES = {
    "kernel_dsc": struct(
        name = "linux_6.12.94-1.dsc",
        sha256 = "985a33d437c11f73f672b808b62589a0db3e97c6c286f315dbe14d1fc43f1191",
    ),
    "kernel_orig": struct(
        name = "linux_6.12.94.orig.tar.xz",
        sha256 = "3eea3dd18f67a103f6f8312e314075f695a27eaddd839e7b6c4641e6616dabba",
    ),
    "kernel_debian": struct(
        name = "linux_6.12.94-1.debian.tar.xz",
        sha256 = "8c5130fd9dee8d6efcc594dc3357809ad8e0d0234357139f85f5ed39b37922b4",
    ),
}

def _source_urls(name):
    # Debian Snapshot retains the exact Makefile inputs after archive rotation.
    return [
        "https://snapshot.debian.org/archive/debian-security/20260621T081639Z/pool/updates/main/l/linux/" + name,
        "https://packages.trafficmanager.net/public/debian-security/pool/updates/main/l/linux/" + name,
    ]

def _kernel_sources_impl(module_ctx):
    for name, source in KERNEL_SOURCES.items():
        http_file(
            name = name,
            urls = _source_urls(source.name),
            downloaded_file_path = source.name,
            sha256 = source.sha256,
        )

    patch_tools_repository(name = "kernel_patch_tools", lock = "@sonic_build_infra//apt:apt.lock.json")
    steps = [
        json.encode({"op": "archive", "urls": _source_urls(KERNEL_SOURCES["kernel_orig"].name), "sha256": KERNEL_SOURCES["kernel_orig"].sha256, "strip_prefix": "linux-6.12.94"}),
        json.encode({"op": "archive", "urls": _source_urls(KERNEL_SOURCES["kernel_debian"].name), "sha256": KERNEL_SOURCES["kernel_debian"].sha256}),
        json.encode({"op": "patch_series", "series": "debian/patches/series", "format": "gnu"}),
    ]
    prepared_source(name = "kernel_debian_prepared", steps = steps,
                    gnu_tools = "@kernel_patch_tools//:ROOT", build_file = Label("//tools/bazel:prepared.BUILD.bazel"))
    patch_names = []
    for line in module_ctx.read(Label("//:patches-sonic/series")).splitlines():
        line = line.partition("#")[0].strip()
        if line:
            patch_names.append("patches-sonic/" + line)
    inputs = {name: Label("//:" + name) for name in patch_names}
    for name in patch_names:
        steps.append(json.encode({"op": "patch", "input": name, "format": "gnu"}))
    prepared_source(name = "kernel_prepared", steps = steps, inputs = inputs,
                    gnu_tools = "@kernel_patch_tools//:ROOT", build_file = Label("//tools/bazel:prepared.BUILD.bazel"))

kernel_sources = module_extension(implementation = _kernel_sources_impl)
