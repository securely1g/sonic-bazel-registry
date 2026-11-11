# Distributed APT requests and workspace locks

Components keep their `apt.install` and `apt.install_file` declarations. In unified
mode, a root `apt.import_lock` selects the production graph for the shared
extension; dependency locks remain standalone defaults. Sources still use
`sources_file`. Legacy imports retain their independent payload locks.

`apt.export_requests(name = "apt_request_export")` creates the public
`@apt_request_export//:requests` JSON export without fetching package indexes.
It contains evaluated requests, the selected source document, production lock
path and root `apt.lock_view` outputs. Collection-only repositories provide the
existing `use_repo` namespaces without fetching DEBs.

`apt.lock_view(file = "//image:apt.lock.json", dependency_sets = ["image_deps"])`
declares an updater-managed compatibility view, not a second production graph.
Production locks with `_inputs.distributed = true` require exact agreement with
the current evaluated request document, including removals.

Use the sonic-build-infra workspace updater to collect, resolve and publish.
Original DEB/data/control targets, library exports and versioned repositories
remain available. Existing package identities and checksums remain enforced.

Optional source-record `default_architectures` selects the nonempty subset of
`architectures` used for requests without architecture qualifiers. Explicit
qualifiers can still select other configured architectures. Omitting the field
preserves the previous all-configured-architectures behavior. Infrastructure
uses AMD64/ARM64 defaults while retaining explicit ARMHF cross inputs.

## Preserve legacy image locks

Legacy `apt.import_lock(lock = ..., dependency_sets = ...)` calls keep the
per-lock payload repositories from `.16`, alongside ordinary `apt.install`
resolution. They do not opt into a single production lock merely because a
transitive dependency selects this newer ruleset.

This matters for [SONiC Framework image PR138](https://github.com/securely1g/sonic-buildimage/pull/138).
Its `7567bbd9` source uses separate base, orchagent, Syncd and Framework image
locks, plus Framework `2e6bb6b7`'s CLI lock. BMv2 `.3` selects Distroless `.17`
through module version selection. The [worker analysis](https://github.com/securely1g/sonic-buildimage/actions/runs/42346751048/job/128326066532)
then rejected those distinct documents before any native build action.

| Input | Before this correction | After |
| --- | --- | --- |
| Separate legacy image and CLI locks | Treated as one production lock and rejected | Imported independently with their original group namespaces and checksums |
| Explicit unified inputs or a canonical lock containing `_inputs` | Root-authoritative production graph | Same strict input, request and lock-view checks |
| Duplicate legacy dependency-set names | Rejected | Still rejected |

Unified mode is selected by source/request files, library imports, effective
root fallbacks, root update/export/view tags, or an `_inputs` record in any
active lock. A canonical dependency under a legacy root selects unified mode.
Ignored dependency fallbacks are skipped before reading lock documents. The root's
single-lock check and dependency fallback rules remain unchanged in unified
mode. New mixed graphs must satisfy that mode's production-lock contract;
this compatibility path does not relax it.

`@rules_distroless//apt/tests:locked_import/routing` checks this selection using
pure fixtures. It joins the existing 36 presubmit tests. Actual Framework
image validation remains a separate consumer check; pure routing tests do not
establish a successful image build.

## Native library contracts

APT library imports preserve installed-file ownership and GNU linker-script
semantics through native shared-library boundaries. A script may refer to a
shared object, static archive, object file or nested script through absolute
paths, relative library names, `-lfoo` or `-l:filename`. GROUP and AS_NEEDED
remain linker-controlled. Runtime exports contain ELF libraries using their
SONAMEs; text scripts remain link inputs. Ambiguous runtime SONAMEs fail during
analysis instead of silently choosing a library. Multiple pkg-config libraries
resolve independently, including libraries supplied by dependency packages.

Run the original cross-package script regression from the registry root:

```sh
USE_BAZEL_VERSION=8.5.1 python3 \
  modules/rules_distroless/0.9.4.sonic.18/tests/shared_linker_script_test.py \
  --registry .
```

The complete contract fixture uses the production sonic-build-infra CcInfo
adapter supplied by the caller. It builds thirty-seven two-level shared-library chains,
checks AS_NEEDED and constructor behavior, rejects conflicting SONAMEs, and runs
both Bazel and installed executables without LD_LIBRARY_PATH or LD_PRELOAD.
The build directory is hidden during installed execution. Before native links,
the fixture also builds public deb/data/control targets and verifies original
DEB bytes, control metadata and unchanged configuration payloads. Ordinary
files under directories such as `ld.so.conf.d` remain package data. Broken and
cyclic links and opaque non-ELF bytes are retained in the data archive; selecting
their native targets reports an explicit error without blocking valid neighbors.
Scripts retain GNU commands, comments and whitespace. The fixture covers quoted
operands, SEARCH_DIR, INCLUDE with declared .ld inputs, PROVIDE, dependency-owned
static archives and shared libraries without SONAMEs. Module selection and Requires determine the flags. The fixture checks NOOPEN
on explicit static and dynamic variants, isolated version/missing-module errors,
cross-package and cyclic Requires, private flags, .pc aliases, variables and
continuations, plus host PKG_CONFIG_PATH isolation. Native validation also
builds and imports a CPython extension after hiding the build directory. Optional Go CGo and
Rust executables consume the adapter's actual CcInfo flags and files.

```sh
USE_BAZEL_VERSION=8.5.1 python3 \
  modules/rules_distroless/0.9.4.sonic.18/tests/library_contract_test.py \
  --registry . --adapter /path/to/sonic-build-infra/cc/shared_library.bzl \
  --go /path/to/go --rustc /path/to/rustc
```

For an ARM64 execution check on an AMD64 host, supply `--cross-info compiler.json`
and `--qemu /path/to/qemu-aarch64-static` instead of the language options. The
JSON contains `cc` (absolute aarch64-linux-gnu-gcc path), `sysroot` (absolute
root), and `flags` (compiler argument array for that sysroot). The fixture uses
these files in a declared Bazel cross toolchain, verifies AArch64 ELF headers,
and executes the resulting programs through QEMU with the supplied sysroot.

Requires Python 3 and its matching development headers, Bazel 8.5.1, gcc, ar,
dpkg-deb, xz, file, readelf and pkg-config. All packages
and locks are synthetic; the tests fetch no production package index and build
no business component. Each run prints its retained evidence directory.

## Select pkg-config modules

With library imports enabled, each installed .pc module has architecture-selecting
hub targets. The module name is the .pc filename without its suffix.

```starlark
cc_library(
    name = "consumer",
    srcs = ["consumer.cc"],
    deps = ["@trixie//libbsd-dev:pkgconfig/libbsd"],
)
```

Use `@trixie//libbsd-dev:pkgconfig/libbsd-ctor` to explicitly select automatic
constructors. It follows `Requires: libbsd` and retains its forced-constructor
and nodlopen options. Ordinary `pkgconfig/libbsd` does not select that module.
A module's options apply regardless of whether its libraries are shared or static.

`@trixie//libbsd-dev:pkgconfig/libbsd/static` performs the static query, includes
Libs.private and Requires.private, and prefers declared .a inputs when available.
The program's overall link mode remains controlled by its Bazel rule. Dynamic
queries include Requires link flags and the compilation flags from both public
and private requirements. Module compilation contexts preserve `-I`, `-isystem`, `-iquote` and `-D`.
An explicit module reports compiler options that CcInfo cannot propagate, such
as `-pthread`, `-fopenmp` or `-U`; use its original `:pkgconfig` files with a
consumer that accepts those compiler flags. The flags remain in the metadata.
Legacy labels retain their existing compiler-option compatibility behavior. These field semantics follow the
[pkg-config guide](https://people.freedesktop.org/~dbn/pkg-config-guide.html).

Requires names and version predicates are resolved by the locked pkgconf executable
against a private directory built from the locked package metadata. Providers
can belong to another reviewed collection without being Debian package
dependencies. The generated catalog separates target architectures and source
families connected by reviewed dependency edges. Multiple unresolved providers
produce an explicit ambiguity diagnostic. Missing providers stay errors on the
explicit module interface; they do not trigger package resolution or lock writes. The host's
PKG_CONFIG_PATH, PKG_CONFIG_LIBDIR and sysroot settings do not supply modules.
On Linux AMD64 and ARM64, the importer bootstraps pkgconf, file, readelf,
their runtime libraries and the magic database from the checksummed
[build-infra tools lock](https://github.com/securely1g/sonic-build-infra/blob/08e0956f80574b27a9b68e72fe855cc0089058e5/apt/apt.lock.json).
Bazel downloads these exact archives through its configured downloader. It uses
the host architecture for the tools even when inspecting target packages for
another architecture. Metadata archives use the same URLs
and checksums as their locked DEBs. No lock-format or request-file change is
needed to adopt these interfaces.

Existing package and per-library labels remain compatibility interfaces. Package
labels keep the aggregate library inputs. Their flags come first from a module
matching the package base name, then the name without a leading lib; when neither
exists, the historical aggregate remains. Per-library aliases use an unambiguous
matching module. A missing private requirement or SDK-required metadata field
falls back to the compatibility module's direct fields. Explicit module targets
remain strict. Ambiguous unqualified raw-library aliases fail when selected;
raw archives and precisely selected modules remain usable.
Use the explicit `pkgconfig/<module>` labels for exact module selection. Modules
under usr/share/pkgconfig are also available. Modules that carry only flags
without library files retain those flags across shared-library boundaries.


The ordered link contract retains groups, whole-archive switches and repeated
options. `-Bstatic`, `-Bdynamic` and push/pop state also control file selection.
Library directories take precedence over suffix preference: each directory is
searched in order. Exact `-l:filename` and declared literal archive inputs are
supported. Static queries prefer `.a` within each directory, with the existing
shared-library fallback; an explicit `-Bstatic` requires an archive.

Runtime metadata follows the selected files, GNU script inputs and ELF
DT_NEEDED edges. Plugins carried in the same package are preserved in its data
archive and do not become unrelated module link inputs. The metadata comes from
cycle-free leaf repositories and uses the locked DEB hashes. Temporary archive
inspection trees are removed after indexing.

The contract fixture includes independent SDK/GNU link controls, providers
outside the Debian dependency graph, foreign-suite/architecture exclusions,
legacy versus strict errors, compiler-option diagnostics, duplicate script
references, exact filenames, mixed archive/DSO search order, link state,
internal-name collisions and original metadata under `usr/share/pkgconfig`.


Runtime DSO identities are shared across module and package contexts, so a
shared dependency retains the same solib directory. Module-specific search
paths pass directly to the linker through `-Xlinker`; their order is preserved
without expanding GCC's `COLLECT_GCC_OPTIONS` environment string. The contract
fixture includes 640 distinct modules meeting in one consumer of a shared DSO.


Legacy dynamic defaults derive additional library references from the dynamic
pkg-config query. `Libs.private` dependencies belong to explicit static module
queries and do not become extra dependencies of the dynamic package default.

Selected unversioned dynamic link aliases remain available in CcInfo's dynamic
library files. Foreign build systems can collect these into a dependency prefix
and resolve the original `.pc` file's `-l` names. Native consumers retain the
module's explicit ordered selection and the shared SONAME runtime identity.

Packages without declared headers contribute empty compile-only header stubs.
They add no nonexistent include roots or implicit repository-root quote search
directories to foreign build probes. Header-bearing package interfaces retain
their existing search paths.

Legacy package defaults preserve SDK header paths as system include directories.
Explicit `pkgconfig/...` modules retain the original ordinary `-I` classification.
The contract fixture checks source-header precedence against both interfaces.

Transitive SDK CcInfo leaves glibc runtime selection to the compiler toolchain
and execution environment. The package identified by the libc.so.6 ELF SONAME
keeps its complete archive payload, while its DSOs do not become incidental
solib or foreign-prefix runtime libraries. Explicit selected library and linker
script inputs remain available. This prevents a foreign build-time generator
from mixing the host ELF loader with a different transitive glibc.

## Keep alternative header namespaces explicit

Package-wide header exports now follow the same default pkg-config module as
its ordinary library alias. For example, `libbsd-dev` contains both `libbsd.pc`
and `libbsd-overlay.pc`. Before this correction, the ordinary `libbsd_headers`
export included the overlay-only `usr/include/<triplet>/bsd` directory too.
A foreign build staged its `stdio.h` wrapper into the generic SDK include root;
OpenSSH then recursively included that wrapper until the compiler's depth limit.

The ordinary alias now exports only the default module's include roots plus the
existing declared package roots. Explicit `pkgconfig/libbsd-overlay` still keeps
its overlay include directory and `LIBBSD_OVERLAY` definition. Packages without
pkg-config metadata and the existing aggregate fallback when no primary module
matches retain their previous behavior. Header files, package payloads, linker
inputs, and all explicit module interfaces remain unchanged.

Five tests in the separate `tests/integration/native_headers` module create
small deterministic DEBs, import them through the production native importer,
and compile/run consumers through real foreign-CC staging. They cover direct
and transitive ordinary exports, explicit overlay selection, metadata-free
headers, and the no-primary-match aggregate fallback. All five are selected
unconditionally by the normal AMD64 and ARM64 presubmit configuration, alongside
the existing forty tests.
