# Validate dependencies while retaining base packages

This source keeps packages already supplied by an image base or its declared
Make manifest, then validates Depends and Pre-Depends against the final package
inventory. Compatible FIPS OpenSSL can satisfy tcpdump without replacement;
a retained version that does not satisfy a requirement fails the build.

The pinned python-debian library provides Debian parsing and version ordering.
The checker supports alternatives, virtual providers and the declared native
architecture. Invalid or missing metadata fails explicitly. It checks package
presence and versions, not installation order, maintainer scripts, Conflicts,
Breaks or runtime ABI compatibility.

Reviewed locks feed ordinary apt.install declarations and an automatically
generated public data/control label mapping. Standard Distroless flatten
assembles selected archives. Parent selection receipts carry complete control
metadata into child layers, so runtime APT additions remain visible to debug
validation without modifying the inherited dpkg database.

This entry selects rules_distroless 0.9.4.sonic.1 without a Distroless override;
the dotted version sorts above upstream 0.9.4. The existing tar.bzl
0.10.5-sonic.1 override remains. Registry CI validates the shared dependency
checker, selection, declared inputs, real package assembly and Protobuf headers
on native AMD64 and ARM64. Tests import existing packages
and produce tar files, never DEBs. Orchagent PR #15 consumes this source.
