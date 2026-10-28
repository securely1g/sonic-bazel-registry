# libyang 3.12.2.sonic.6

Native Bazel C rules build the SONiC-patched libyang 3.12.2 library, interactive yanglint and yangre. Target PCRE2 and xxHash shared libraries use fixed Debian APT snapshots selected for Trixie or Bookworm. The public interface provides SONAME libyang.so.3, installed headers and pkg-config metadata.
