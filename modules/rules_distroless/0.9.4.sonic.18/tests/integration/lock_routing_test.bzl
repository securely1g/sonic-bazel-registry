"""Check the importer's mode when a dependency adds a lock under a legacy root."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("@rules_distroless//apt/private:configuration.bzl", "selected_lock_tags", "uses_unified_lock")

def _module(root, lock, fallback = False):
    tag = struct(lock = lock, fallback = fallback, libraries = False, requests = None, sources = None)
    return struct(is_root = root, tags = struct(
        import_lock = [tag],
        install_file = [],
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
    ignored = struct(modules = [root, _module(False, "unread", fallback = True)], read = read)
    asserts.false(env, uses_unified_lock(ignored))
    return unittest.end(env)

mixed_lock_routing_test = unittest.make(_mixed_lock_routing_test_impl)
