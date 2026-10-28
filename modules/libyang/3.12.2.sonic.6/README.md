# libyang 3.12.2.sonic.6

Native Bazel C rules build the SONiC-patched libyang 3.12.2 library, interactive yanglint and yangre. Target PCRE2 and xxHash shared libraries use fixed Debian APT snapshots selected for Trixie or Bookworm. The public interface provides SONAME libyang.so.3, installed headers and pkg-config metadata.

## Native Draft validation prerequisites

The libyang candidate uses infrastructure `0.0.25-917c7d5792f88c9de485ea5172a835bb0c06bf6a` from [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147) and the `.13` library exports from [#146](https://github.com/securely1g/sonic-bazel-registry/pull/146). This infrastructure supplies the shared Bookworm execution-tool set and corrected packaged Python extension lookup.

Its native CI stages only those exact prerequisite recipes from the immutable Draft catalog pinned by [this PR’s workflow](../../../.github/workflows/registry-ci.yml); the PR's own `libyang@3.12.2.sonic.6` recipe stays under test. The runner uses that single local catalog plus BCR, and retains `draft-prerequisites.json` with the exact entry trees. This is temporary validation, not a published dependency or a Ready criterion. Remove the staging step and verify maintained-main resolution after the prerequisites land.

| Input or action | Before | After |
| --- | --- | --- |
| Native libyang registry validation for FRR's libraries and installation TARs | Older Draft infrastructure omits the reviewed execution-tool fixes | The reviewed `0.0.25-917c7d57…` recipe supplies the shared Bookworm tools and Python extension lookup; `.13` provides the required APT library targets |

For local reproduction, stage the same entry trees from the pinned catalog into a disposable registry worktree, preserving this candidate, then run its existing `ci/registry_ci.py run --module libyang --version 3.12.2.sonic.6` command for the native architecture. Published module entries in the PR remain unchanged; historical cross-build results do not establish native ARM64 execution.

The validation also executes the public API consumer against the installed runtime TAR, with build-tree library search paths removed. Package checks enforce Debian file and directory permissions alongside existing ELF/debug pairing checks.

After the Bazel tests, native CI verifies the collected TAR sizes and SHA256 hashes before using GDB to resolve `ly_ctx_new` to `context.c`. Runtime and symbol files are extracted separately, with GDB auto-load and debuginfod disabled. The log and `libyang-installed-debug.json` receipt bind that lookup to the delivered bytes.
