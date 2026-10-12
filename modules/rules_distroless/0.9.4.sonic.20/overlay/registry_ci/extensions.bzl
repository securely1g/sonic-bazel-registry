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

_LUA = {
    "amd64": {
        "multiarch": "x86_64-linux-gnu",
        "dev": "363759cbaccd47f06b972e578ea6112e50c833d728b7a11e15609764665dabbc",
        "runtime": "e98fb0eaa8d07fd24bbaefd3b2bd356b8c6df241865780c42adb08f7ebcf8563"
    },
    "arm64": {
        "multiarch": "aarch64-linux-gnu",
        "dev": "f0bbb58d879faa5d3f4ce40f404ac266f4ad54d20915bcaabeb8a6bd118ef2b1",
        "runtime": "d70ec396d05c96d73098a16802bea1d2066497bc32eb2e83244d3b1777e84590"
    }
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

    metadata_packages = {}
    metadata_sets = {}

    for architecture, package in _LUA.items():
        key = "/registry_ci/liblua5.1-0:{}=5.1.5-11".format(architecture)
        repository = util.sanitize(key)
        deb_import(
            name = repository,
            package_name = "liblua5.1-0",
            sha256 = package["runtime"],
            target_name = repository,
            urls = ["https://deb.debian.org/debian/pool/main/l/lua5.1/liblua5.1-0_5.1.5-11_{}.deb".format(architecture)],
        )
        deb_filemap(
            name = repository + "_filemap",
            files = json.encode([
                "usr/lib/{}/{}.{}".format(package["multiarch"], library, suffix)
                for library in ["liblua5.1.so", "liblua5.1-c++.so"]
                for suffix in ["0", "0.0.0"]
            ]),
        )
        deb_import(
            name = "registry_ci_lua_" + architecture,
            depends_on = [key],
            dep_filemaps = ["@" + repository + "_filemap//:filemap.json"],
            package_name = "liblua5.1-0-dev",
            sha256 = package["dev"],
            target_name = "liblua5.1-0-dev",
            urls = ["https://deb.debian.org/debian/pool/main/l/lua5.1/liblua5.1-0-dev_5.1.5-11_{}.deb".format(architecture)],
        )

        dev_key = "/registry_ci/liblua5.1-0-dev:{}=5.1.5-11".format(architecture)
        # Exercise the same generated aliases an apt.install consumer receives.
        deb_import(
            name = util.sanitize(dev_key),
            depends_on = [key],
            dep_filemaps = ["@" + repository + "_filemap//:filemap.json"],
            package_name = "liblua5.1-0-dev",
            sha256 = package["dev"],
            target_name = "liblua5.1-0-dev",
            urls = ["https://deb.debian.org/debian/pool/main/l/lua5.1/liblua5.1-0-dev_5.1.5-11_{}.deb".format(architecture)],
        )
        metadata_packages[key] = {"name": "liblua5.1-0", "architecture": architecture}
        metadata_packages[dev_key] = {
            "name": "liblua5.1-0-dev",
            "version": "5.1.5-11",
            "architecture": architecture,
            "suite": "registry_ci",
            "filename": "pool/main/l/lua5.1/liblua5.1-0-dev_5.1.5-11_{}.deb".format(architecture),
            "sha256": package["dev"],
            "depends_on": [key],
        }
        metadata_sets[architecture] = {dev_key.split("=")[0]: "5.1.5-11"}

    translate_dependency_set(
        name = "registry_ci_pkgconfig",
        depset_name = "registry_ci",
        lock_content = json.encode({
            "version": 2,
            "sources": {"registry_ci": {"uris": ["https://deb.debian.org/debian"]}},
            "packages": metadata_packages,
            "dependency_sets": {"registry_ci": {"sets": metadata_sets}},
        }),
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
