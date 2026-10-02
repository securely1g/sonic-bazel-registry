"""Pinned Protobuf headers and an empty dependency set for registry CI only."""

load("//apt/private:deb_filemap.bzl", "deb_filemap")
load("//apt/private:deb_import.bzl", "deb_import")
load("//apt/private:translate_dependency_set.bzl", "translate_dependency_set")
load("//apt/private:util.bzl", "util")

_PROTOBUF = {
    "amd64": {
        "multiarch": "x86_64-linux-gnu",
        "dev": "c0328550b6ccd7b09d4e50bc2b325a43638bf8fa5f74148ab6e63d49af7543f3",
        "runtime": {
            "libprotobuf32t64": ["libprotobuf", "38c43ec79a043d2b2659fed321725049a7e457096a66691cf6eb0d3a1a8f0e85"],
            "libprotobuf-lite32t64": ["libprotobuf-lite", "74ed82b17475a1411ac79b27bd8b0223b3727d55660f77b8a5f6d5598e2dd7c2"],
        },
    },
    "arm64": {
        "multiarch": "aarch64-linux-gnu",
        "dev": "26e311a867ef831d2378a33e772b1f21924261eedcefe08f7ce852c6176c2836",
        "runtime": {
            "libprotobuf32t64": ["libprotobuf", "51bf38fcca667be0deef732a903563ee6ffa9bfc04433310c2c49e4c92d06b09"],
            "libprotobuf-lite32t64": ["libprotobuf-lite", "576ce2ca95e4aa98e135e02594a950e6381189d8b9702295ab8d505d49a503ad"],
        },
    },
}

def _registry_ci_impl(module_ctx):
    for architecture, packages in _PROTOBUF.items():
        depends_on = []
        dep_filemaps = []
        for package, (library, sha256) in packages["runtime"].items():
            key = "/registry_ci/{}:{}=3.21.12-11+deb13u1".format(package, architecture)
            repository = util.sanitize(key)
            deb_import(
                name = repository,
                package_name = package,
                sha256 = sha256,
                target_name = repository,
                urls = ["https://deb.debian.org/debian/pool/main/p/protobuf/{}_3.21.12-11+deb13u1_{}.deb".format(package, architecture)],
            )

            # The development package's two linker symlinks point into these
            # runtime packages. Their pinned archives supply the real targets.
            deb_filemap(
                name = repository + "_filemap",
                files = json.encode(["usr/lib/{}/{}.so.32.0.12".format(packages["multiarch"], library)]),
            )
            depends_on.append(key)
            dep_filemaps.append("@" + repository + "_filemap//:filemap.json")

        deb_import(
            name = "registry_ci_protobuf_" + architecture,
            depends_on = depends_on,
            dep_filemaps = dep_filemaps,
            package_name = "libprotobuf-dev",
            sha256 = packages["dev"],
            target_name = "libprotobuf-dev",
            urls = ["https://deb.debian.org/debian/pool/main/p/protobuf/libprotobuf-dev_3.21.12-11+deb13u1_{}.deb".format(architecture)],
        )

    translate_dependency_set(
        name = "registry_ci_architectures",
        depset_name = "registry_ci",
        lock_content = json.encode({
            "version": 2,
            "dependency_sets": {"registry_ci": {"sets": {"amd64": {}, "arm64": {}}}},
        }),
    )
    return module_ctx.extension_metadata(reproducible = True)

registry_ci = module_extension(implementation = _registry_ci_impl)
