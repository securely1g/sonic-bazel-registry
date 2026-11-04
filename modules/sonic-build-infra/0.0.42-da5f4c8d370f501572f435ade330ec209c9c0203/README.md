# Unique paths in selected APT layers

Register merged [infra #81](https://github.com/securely1g/sonic-build-infra/pull/81)
at source commit `3ee15ec9b4d99d7f8eae3e324cead79b203b451e`. The source includes the merged compiler
header-option fix from [infra #80](https://github.com/securely1g/sonic-build-infra/pull/80).

Gearbox image [#154](https://github.com/securely1g/sonic-buildimage/pull/154)
selects package TARs with shared directory headers. `apt_layer` now enables
Distroless `flatten(..., deduplicate=True)` to emit each path once, preserving
last-entry payload and metadata semantics. The overlap regression checks shared
directories, regular files, symlinks, hardlinks and a later configuration override.

The recipe retains the prior CLI patch/XML tools and external-test visibility.
Native component interfaces are supplied by the merged source, replacing the
previous large registry patch. The source module base version is `0.0.25`;
consumers must verify Bazel selects this exact commit-based registration when
other dependencies request a higher numeric release or commit suffix.

Presubmit retains all 44 required outputs and 45 tests, including the overlap
layer and selection receipt. It pins published Distroless `0.9.4.sonic.16`.
Published registrations, including `0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568`,
retain their original consumer inputs. Registry acceptance covers the registered
module; full Gearbox image acceptance is a separate consumer boundary.
