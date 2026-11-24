# Native DASH SAI build

This entry builds the DASH revision selected by sonic-buildimage's DASH SAI
Make recipe, `d5c003dd7774c2b43f275c0233acc73a0ea28d2f`. The registry overlay supplies Bazel rules and
generator adapters with explicit input and output paths. SAI comes from
the gitlink at `8dd59e5eba472f0e53e8db00530e7c6e5ce2a335`.

P4C `1.2.4.2.sonic.7` and PI `0.1.3.sonic.7` provide the pipeline compiler and
link dependencies. Syncd VS can consume `@sonic-dash//:sdk`,
`:runtime`, `:runtime.debug_symbols` and `:runtime_packages.json`.

The native build creates an empty `saimetadatasize.h` for the SAI source archive. Its tests do not check ABI sizes against the pristine headers at the pinned SAI commit or reject an enlarged union. The Make workflow exercises those checks in [DASH #3](https://github.com/securely1g/DASH/pull/3).
