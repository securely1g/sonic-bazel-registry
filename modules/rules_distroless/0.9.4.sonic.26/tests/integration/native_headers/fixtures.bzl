"""Generate DEB inputs, then invoke the production importer unchanged."""

load("@rules_distroless//apt/private:deb_import.bzl", "deb_import")
load("@rules_distroless//apt/private:deb_filemap.bzl", "deb_filemap")
load("@rules_distroless//apt/private:util.bzl", "util")

def _fixtures_impl(ctx):
    result = ctx.execute([ctx.path(ctx.attr.interpreter), "-I", ctx.path(ctx.attr.generator)])
    if result.return_code:
        fail(result.stderr)
    ctx.file("BUILD.bazel", 'exports_files(glob(["*.deb", "*.sha256", "*.files.json"]))\n')

fixtures = repository_rule(
    implementation = _fixtures_impl,
    attrs = {
        "generator": attr.label(default = "//native_headers:make_fixtures.py", allow_single_file = True),
        "interpreter": attr.label(mandatory = True, allow_single_file = True),
    },
)

def _imports_impl(ctx):
    for module in ctx.modules:
        for package in module.tags.package:
            name = util.sanitize("/header-fixture/{}:all=1".format(package.package))
            deb_filemap(
                name = name + "_filemap",
                files = ctx.read(ctx.path(package.archive).dirname.get_child(package.package + ".files.json")),
                urls = ["file://" + str(ctx.path(package.archive))],
                sha256 = ctx.read(package.digest).strip(),
            )
            deb_import(
                name = name,
                package_name = package.package,
                target_name = package.package,
                urls = ["file://" + str(ctx.path(package.archive))],
                sha256 = ctx.read(package.digest).strip(),
                own_filemap = "@" + name + "_filemap//:filemap.json",
                dep_filemaps = ["@" + util.sanitize("/header-fixture/{}:all=1".format(dep)) + "_filemap//:filemap.json" for dep in package.dependencies],
                depends_on = ["/header-fixture/{}:all=1".format(dep) for dep in package.dependencies],
            )

imports = module_extension(
    implementation = _imports_impl,
    tag_classes = {"package": tag_class(attrs = {
        "package": attr.string(mandatory = True),
        "archive": attr.label(mandatory = True),
        "digest": attr.label(mandatory = True),
        "dependencies": attr.string_list(),
    })},
)
