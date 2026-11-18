"""Check the importer's mode when a dependency adds a lock under a legacy root."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("@rules_distroless//apt/private:configuration.bzl", "install_requests", "requests_document", "selected_lock_tags", "uses_unified_lock")

def _module(root, lock, fallback = False, requests = None, installs = [], install_files = []):
    tag = struct(lock = lock, fallback = fallback, libraries = False, requests = requests, sources = None)
    return struct(is_root = root, tags = struct(
        import_lock = [tag],
        install = installs,
        install_file = install_files,
        export_lock = [],
        export_requests = [],
        lock_view = [],
    ))

def _mixed_lock_routing_test_impl(ctx):
    env = unittest.begin(ctx)
    root = _module(True, "root")

    # get() is sufficient to model mctx.read here. Reading an ignored fallback
    # returns None and fails JSON decoding, so the test also checks access.
    read = {"root": "{}", "old": "{}", "new": '{"_inputs": {}}'}.get
    mixed = struct(modules = [root, _module(False, "new")], read = read)
    asserts.true(env, uses_unified_lock(mixed))
    _, selected = selected_lock_tags(mixed)
    asserts.equals(env, ["root"], [tag.lock for _, tag in selected])

    legacy = struct(modules = [root, _module(False, "old")], read = read)
    asserts.false(env, uses_unified_lock(legacy))
    # An ignored dependency lock cannot supply requests. Its independently
    # declared apt.install and apt.install_file inputs still apply.
    installed = struct(dependency_set = "direct", packages = ["libc6"], suites = [], include_transitive = True)
    child = _module(False, "unread", fallback = True, requests = "unread", installs = [installed], install_files = [struct(file = "child_requests")])
    only_default = _module(False, "unread", fallback = True, requests = "unread")
    ignored = struct(modules = [root, only_default], read = read)
    asserts.false(env, uses_unified_lock(ignored))
    files = {
        "root_requests": '{"dependency_sets":{"central":{"packages":["netbase"]}}}',
        "child_requests": '{"version":1,"dependency_sets":{"child":{"packages":["liblua5.1-0"]}}}',
    }
    # A standalone root fallback deliberately contributes its own requests.
    standalone = _module(True, "root", fallback = True, requests = "root_requests")
    requests = install_requests(struct(modules = [standalone, child], read = files.get))
    groups = requests_document(requests)["dependency_sets"]
    asserts.equals(env, {"central": ["netbase"], "child": ["liblua5.1-0"], "direct": ["libc6"]}, {
        name: group["packages"]
        for name, group in groups.items()
    })
    return unittest.end(env)

mixed_lock_routing_test = unittest.make(_mixed_lock_routing_test_impl)
