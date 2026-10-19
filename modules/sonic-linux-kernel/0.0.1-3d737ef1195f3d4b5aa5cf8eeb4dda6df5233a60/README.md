# SONiC kernel: 0.0.1-3d737ef1195f3d4b5aa5cf8eeb4dda6df5233a60

This entry publishes `//:kernel_packages`, the AMD64 Trixie VS source target for
the unsigned `6.12.41-1` kernel, matching headers and kbuild package. It selects
shared build infrastructure `0.0.16-717519d972fe8405e4e7dec424de3058e8952b14`.

The AMD64 registry presubmit checks source-input identity, package handoff
validation, and rejection of invalid remote-cache evidence. Those focused
tests do not compile a kernel and are not full package-build evidence. The
kernel source workflow performs the cold source build and verifies a fresh
consumer obtains identical packages through a remote action cache. Buildimage currently uses a local source override; this registry route is not yet its selected source.

See the registered source's `tools/bazel/README.md` for the four package
outputs, tool/input provenance and execution limitations. No ARM64, signing,
separate debug-package delivery, or full image-boot claim is made by this entry.
The registered source revision is `3d737ef1195f3d4b5aa5cf8eeb4dda6df5233a60`.

The MODULE patch selects the refreshed shared tools while preserving this exact kernel source archive. The source and registry changes remain Draft until their prerequisites land.
