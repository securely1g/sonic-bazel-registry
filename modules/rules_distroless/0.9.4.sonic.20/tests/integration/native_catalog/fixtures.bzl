"""Exercise the real catalog entry point with ambient tools unavailable."""

load("@rules_distroless//apt/private:native_tools.bzl", "catalog_execute", "unlocked_library")
load("@rules_distroless//apt/private:pkgconfig.bzl", "pkgconfig_environment")

def _check_impl(ctx):
    for host_mapping in [
        "libexample.so => /usr/lib/libexample.so (0x1000)",
        "/etc/custom/libpreload.so (0x2000)",
    ]:
        if unlocked_library(host_mapping, "/isolated-tools") != host_mapping:
            fail("Accepted a dependency outside the locked runtime: " + host_mapping)
    for name in ["pkg-config", "file", "readelf"]:
        ctx.file("poison/" + name, "#!/bin/sh\nexit 97\n", executable = True)
    env = {"PATH": str(ctx.path("poison")), "MAGIC": str(ctx.path("absent.mgc"))}
    ctx.file("sample.ld", "INPUT(libsample.so)\n")
    ctx.file("pc/probe.pc", "Name: probe\nDescription: catalog tool smoke test\nVersion: 7.1\n")
    env.update(pkgconfig_environment(ctx, "pc"))

    for name, args, expected in [
        ("file", ["--mime-type", "-b", "sample.ld"], "text/"),
        ("readelf", ["-h", "/proc/self/exe"], "ELF64"),
        ("pkg-config", ["--modversion", "probe"], "7.1"),
    ]:
        result = catalog_execute(ctx, name, args, env)
        if result.return_code or expected not in result.stdout:
            fail("Locked %s failed with poisoned PATH: %s%s" % (name, result.stderr, result.stdout))
    ctx.file("checked", "file, readelf and pkg-config passed\n")
    ctx.file("BUILD.bazel", 'exports_files(["checked"])\n')

check_catalog_tools = repository_rule(implementation = _check_impl)
