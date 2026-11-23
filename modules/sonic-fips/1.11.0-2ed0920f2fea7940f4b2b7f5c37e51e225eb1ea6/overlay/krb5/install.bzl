"""One original install manifest and TAR producer for both Debian target ABIs."""
load("@sonic_build_infra//tar:sonic_deploy_tar.bzl", "sonic_deploy_tar")

_DEBIAN_TARGETS = [
    ("amd64", "@platforms//cpu:x86_64", "x86_64-linux-gnu"),
    ("arm64", "@platforms//cpu:aarch64", "aarch64-linux-gnu"),
]

def native_install_package(name, srcs, mtree, binaries = {}, visibility = ["//visibility:public"], **kwargs):
    sonic_deploy_tar(
        name = name,
        srcs = srcs,
        binaries = binaries,
        mtree = mtree,
        visibility = visibility,
        mtree_substitutions = select({
            cpu: {"{DEB_HOST_MULTIARCH}": multiarch}
            for _, cpu, multiarch in _DEBIAN_TARGETS
        }),
        **kwargs
    )

def target_multiarch_substitutions(substitutions):
    return select({
        cpu: {key: value.replace("{DEB_HOST_MULTIARCH}", multiarch) for key, value in substitutions.items()}
        for _, cpu, multiarch in _DEBIAN_TARGETS
    })
