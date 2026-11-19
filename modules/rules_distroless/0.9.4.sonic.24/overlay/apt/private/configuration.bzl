"""Central source/request documents and explicit production-lock export."""

def read_sources(mctx):
    """Select the root override or one shared source document, checking conflicts."""
    files = []
    overrides = []
    for module in mctx.modules:
        for tag in module.tags.sources_file:
            document = json.decode(mctx.read(tag.file))
            if document.get("version") != 1 or type(document.get("sources")) != "list":
                fail("APT sources file requires version 1 and sources list: " + str(tag.file))
            if tag.override:
                if not module.is_root:
                    fail("only the root module may override the APT source configuration")
                overrides.append(document)
            else:
                files.append(document)
    if len(overrides) > 1:
        fail("select exactly one root APT source override")
    selected = overrides[0] if overrides else (files[0] if files else None)
    if not overrides:
        for document in files:
            if document != selected:
                fail("conflicting global APT source documents")
    records = []
    if selected:
        records.extend(selected["sources"])
    if not overrides:
        for module in mctx.modules:
            for tag in module.tags.sources_list:
                records.append({"uris": tag.uris, "suites": tag.suites, "components": tag.components, "architectures": tag.architectures, "types": tag.types})
    by_suite = {}
    for record in records:
        for key in ["uris", "suites", "components", "architectures"]:
            value = record.get(key)
            if type(value) != "list" or not value or any([type(item) != "string" or not item for item in value]):
                fail("APT source requires nonempty string list: " + key)
        value = {key: record.get(key, []) for key in ["uris", "components", "architectures", "types"]}
        for suite in record["suites"]:
            if suite in by_suite:
                previous = by_suite[suite]
                if any([previous[key] != value[key] for key in ["uris", "components", "types"]]):
                    fail("conflicting APT source configuration for suite: " + suite)
                if selected and any([arch not in previous["architectures"] for arch in value["architectures"]]):
                    fail("APT consumer requests an architecture absent from the global source: " + suite)
                value = dict(value, architectures = previous["architectures"] + [arch for arch in value["architectures"] if arch not in previous["architectures"]])
            by_suite[suite] = value
    sources = [struct(suites = [suite], **value) for suite, value in by_suite.items()]
    return (sources, selected)

def install_requests(mctx):
    """Read and normalize all source-owned package requests in the module graph."""
    requests = []
    for module in mctx.modules:
        requests.extend(module.tags.install)

        # A root export reads the same reviewed central requests used by imports.
        for tag in module.tags.import_lock:
            if tag.requests:
                document = json.decode(mctx.read(tag.requests))
                for name, value in document["dependency_sets"].items():
                    requests.append(struct(dependency_set = name, packages = value["packages"], suites = value.get("suites", []), include_transitive = value.get("include_transitive", True)))
        for tag in module.tags.install_file:
            document = json.decode(mctx.read(tag.file))
            if document.get("version") != 1 or type(document.get("dependency_sets")) != "dict":
                fail("APT requests file requires version 1 and dependency_sets: " + str(tag.file))
            for name, value in document["dependency_sets"].items():
                if type(value.get("packages")) != "list" or not value["packages"]:
                    fail("APT request requires packages: " + name)
                requests.append(struct(dependency_set = name, packages = value["packages"], suites = value.get("suites", []), include_transitive = value.get("include_transitive", True)))
    return requests

def requests_document(requests):
    """Record semantic inputs without module commits or unrelated source files."""
    groups = {}
    for request in requests:
        group = groups.setdefault(request.dependency_set, {"packages": [], "suites": request.suites, "include_transitive": request.include_transitive})
        if group["suites"] != request.suites or group["include_transitive"] != request.include_transitive:
            fail("conflicting APT request policy for collection: " + request.dependency_set)
        group["packages"].extend([item for item in request.packages if item not in group["packages"]])
    return {"version": 1, "dependency_sets": {name: dict(value, packages = sorted(value["packages"])) for name, value in groups.items()}}

def _export_lock_impl(rctx):
    rctx.file("apt.lock.json", rctx.attr.content)
    rctx.file("BUILD.bazel", 'exports_files(["apt.lock.json"], visibility = ["//visibility:public"])\nfilegroup(name = "lock", srcs = ["apt.lock.json"], visibility = ["//visibility:public"])\n')

export_lock_repository = repository_rule(
    implementation = _export_lock_impl,
    attrs = {"content": attr.string(mandatory = True)},
)
