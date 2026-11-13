# Source preparation

The original archive and Debian archive retain the SHA256 values listed by
`socat_1.8.0.2-1.dsc`. Debian's `debian/patches/series` supplies the ordered patches:
`00-Manpage`, `01-Index`, `03-Truncate`, `06-socat.1.patch`,
`07-compat-define-PATH_MAX.patch`, `08-test.sh-fixes.patch` and
`09-xioinitialize.c.patch`.

After that series, `bazel/enable_readline.patch` applies the unchanged SONiC
`src/socat/patch/enable_readline.patch`: it removes Debian's fixed
`--disable-readline` and declares the readline development dependency. It is a
SONiC downstream packaging change, not an upstream source change. Its original
`-p0` paths and patch bytes remain intact. The shared unified-diff adapter
handles its adjacent file sections; the native patch engine otherwise treats
the second section as part of the preceding change.

The registry overlay contains only Bazel adaptation and its consumer test.
Debian originals and patches remain files of the fixed external Debian archive.
The registry source root owns the module entry, while the prepared source tree
owns archive merging and patching. Both entries reuse the same immutable archive
identity and download cache; they perform separate extraction for those roles.

After the readline patch, `bazel/0003-procan-namespace-nul.patch` preserves
the network namespace readlink termination fix from `1.8.0.2.sonic.6`.
Compiler metadata is supplied by native C rules; the Makefile-only compiler
metadata patch from that version is no longer needed.
