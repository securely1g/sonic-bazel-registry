"""Exercise the real catalog entry point with ambient tools unavailable."""

load("@rules_distroless//apt/private:native_tools.bzl", "catalog_execute", "unlocked_library")
load("@rules_distroless//apt/private:pkgconfig.bzl", "resolve_modules")

def _check_impl(ctx):
    for host_mapping in [
        "libexample.so => /usr/lib/libexample.so (0x1000)",
        "/etc/custom/libpreload.so (0x2000)",
    ]:
        if unlocked_library(host_mapping, "/isolated-tools") != host_mapping:
            fail("Accepted a dependency outside the locked runtime: " + host_mapping)
    for name in ["file", "readelf"]:
        ctx.file("poison/" + name, "#!/bin/sh\nexit 97\n", executable = True)
    env = {"PATH": str(ctx.path("poison")), "MAGIC": str(ctx.path("absent.mgc"))}
    ctx.file("sample.ld", "INPUT(libsample.so)\n")

    for name, args, expected in [
        ("file", ["--mime-type", "-b", "sample.ld"], "text/"),
        ("readelf", ["-h", "/proc/self/exe"], "ELF64"),
    ]:
        result = catalog_execute(ctx, name, args, env)
        if result.return_code or expected not in result.stdout:
            fail("Locked %s failed with poisoned PATH: %s%s" % (name, result.stderr, result.stdout))
    # Metadata parsing may use repository files, but must not execute tools.
    # The expected flags are independently checked against locked pkgconf 1.8.1.
    no_execute = struct(file = ctx.file, path = ctx.path, read = ctx.read, delete = ctx.delete)
    documents = [
        {"repo": "fixture", "path": "usr/lib/pkgconfig/root.pc", "own": True, "content": "Name: root\nDescription: oracle fixture\nVersion: 1\nRequires: public >= 1\nRequires.private: private >= 1\nLibs: -lroot\nLibs.private: -lroot_private\nCflags: -DROOT\nCflags.private: -DROOT_STATIC\n"},
        {"repo": "fixture", "path": "usr/lib/pkgconfig/public.pc", "own": True, "content": "Name: public\nDescription: oracle fixture\nVersion: 1\nLibs: -lpublic\nCflags: -DPUBLIC\nCflags.private: -DPUBLIC_STATIC\n"},
        {"repo": "fixture", "path": "usr/lib/pkgconfig/private.pc", "own": True, "content": "Name: private\nDescription: oracle fixture\nVersion: 1\nLibs: -lprivate\nCflags: -DPRIVATE\nCflags.private: -DPRIVATE_STATIC\n"},
    ]
    parsed = resolve_modules(no_execute, documents)["root"]["modes"]
    if parsed["dynamic"]["libs"] != ["-lroot", "-lpublic"]:
        fail("Direct metadata dynamic libs differs: " + str(parsed["dynamic"]))
    if parsed["static"]["libs"] != ["-lroot", "-lroot_private", "-lpublic", "-lprivate"]:
        fail("Direct metadata static libs differs: " + str(parsed["static"]))
    if parsed["dynamic"]["cflags"] != ["-DROOT", "-DPUBLIC", "-DPRIVATE"]:
        fail("Direct metadata dynamic cflags differs: " + str(parsed["dynamic"]))
    if parsed["static"]["cflags"] != ["-DROOT", "-DPUBLIC", "-DPRIVATE", "-DROOT_STATIC", "-DPUBLIC_STATIC", "-DPRIVATE_STATIC"]:
        fail("Direct metadata static cflags differs: " + str(parsed["static"]))
    ctx.file("checked", "file and readelf passed\n")
    ctx.file("BUILD.bazel", 'exports_files(["checked"])\n')

check_catalog_tools = repository_rule(implementation = _check_impl)
