# SONiC kernel: 0.0.1-3d737ef1195f3d4b5aa5cf8eeb4dda6df5233a60

This entry publishes `//:kernel_packages`, the AMD64 Trixie VS source target for
the unsigned `6.12.41-1` kernel, matching headers and kbuild package. It selects
shared build infrastructure `0.0.15-3a3d42932877e303385fd0b6503d1c413fc86bab`.

The AMD64 registry presubmit checks source-input identity, package handoff
validation, and rejection of invalid remote-cache evidence. Those focused
tests do not compile a kernel and are not full package-build evidence. The
kernel source workflow performs the cold source build and verifies a fresh
consumer obtains identical packages through a remote action cache. The
buildimage integration validates that registered external-consumer path.

See the registered source's `tools/bazel/README.md` for the four package
outputs, tool/input provenance and execution limitations. No ARM64, signing,
separate debug-package delivery, or full image-boot claim is made by this entry.
The registered source revision is `3d737ef1195f3d4b5aa5cf8eeb4dda6df5233a60`.
