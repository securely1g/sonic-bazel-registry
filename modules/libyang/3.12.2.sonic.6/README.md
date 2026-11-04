# libyang 3.12.2.sonic.6

Native Bazel C rules build the SONiC-patched libyang 3.12.2 library, interactive yanglint and yangre. Target PCRE2 and xxHash shared libraries use fixed Debian APT snapshots selected for Trixie or Bookworm. The public interface provides SONAME libyang.so.3, installed headers and pkg-config metadata.

The validation also executes the public API consumer against the installed runtime TAR, with build-tree library search paths removed. Package checks enforce Debian file and directory permissions alongside existing ELF/debug pairing checks.

After the Bazel tests, native CI verifies the collected TAR sizes and SHA256 hashes before using GDB to resolve `ly_ctx_new` to `context.c`. Runtime and symbol files are extracted separately, with GDB auto-load and debuginfod disabled. The log and `libyang-installed-debug.json` receipt bind that lookup to the delivered bytes.
