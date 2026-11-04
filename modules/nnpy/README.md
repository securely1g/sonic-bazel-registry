# nnpy source runtime

`nnpy@1.4.2.sonic.1` builds upstream nanomsg/nnpy tag 1.4.2, commit
`d8f260a176212bfe5f6626942c487b7d90842414`, for native AMD64 CPython 3.13.
BMv2 installs `bm_p4dbg` and `bm_nanomsg_events`; both import this binding.
There is no nnpy entry in BCR or a Debian Trixie nnpy package.

The unchanged upstream `generate.py` reads the declared nanomsg headers and
library through its supported `site.cfg`, emits C through CFFI's public API,
and generates the original Python constants. A standard `cc_binary` builds
the extension against explicit Python 3.13 headers and the same imported
`libnanomsg.so.5` ABI selected by BMv2. The generator runs on the execution
platform; it never compiles the target extension or searches host headers.

The public targets are `@nnpy//:runtime`, `@nnpy//:runtime.debug_symbols`,
`@nnpy//:source`, and `@nnpy//:generation.json`. Runtime files live under
`usr/lib/python3/dist-packages`, including the original Python modules,
generated constants, `_nnpy.so`, and upstream setuptools egg metadata.
The MIT license is retained under `usr/share/doc/nnpy/LICENSE`.
The source TAR contains the original entry points and package sources.
No Debian package identity, wheel, or DEB producer is invented for this
upstream Python distribution. The consumer supplies CPython 3.13, CFFI
1.17.1 and nanomsg from its declared external runtime packages.

The pinned CFFI, pycparser and setuptools wheels are external execution/test
dependencies. They are not included in the nnpy runtime TAR. This follows
the existing libyang Python CFFI and upstream egg-metadata build pattern.

`@nnpy//:package_test` checks installed source bytes, distribution metadata,
the exact declared nanomsg library, both original upstream socket tests,
missing-extension rejection, and positive/negative split-DWARF lookup with
GNU build-ID and debuglink CRC verification. Python 3.13's standard test
loader runs the original `Tests` class because upstream's convenience
`suite()` uses the removed `unittest.makeSuite`; no assertions are changed.

Native AMD64 ordinary-consumer acceptance passes all four outputs and the
installed package test, including both original upstream socket cases. The
configured graph contains 2,029 actions and no DEB producers. A second output
root with the disk action cache disabled performs real compilation and produces
all four outputs byte-for-byte identically. The no-op executes no spawns; a real
Python source edit changes its installed behavior and only the expected source
and runtime payloads, and restoration recovers all four exact baseline hashes.

The unchanged installed BMv2 `bm_nanomsg_events` decodes a real private nanomsg
packet event and config-change notification. The unchanged `bm_p4dbg` performs
its original attach/detach exchange with exact request IDs over a private
REQ/REP socket. Both clients retain their documented explicit socket/JSON
mode. These are binding and client protocol checks; complete DASH-engine,
switch forwarding and inherited-image acceptance remain separate.
