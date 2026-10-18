# Real Debian installation and existing Distroless fixes

This version retains the SONiC fixes in `0.9.4.sonic.6` and adds the optional
`apt_install` rule from [rules_distroless #2](https://github.com/securely1g/rules_distroless/pull/2).
It installs original DEBs using the base filesystem's APT and dpkg, including
package configuration scripts and triggers. For example, `ca-certificates`
creates its configuration and certificate links during installation.

The retained native shared-library provider fix keeps versioned runtime paths
visible to Bazel without changing ELF loader tags.

Package imports expose each verified original archive as `:deb`. The installer
returns a complete configured filesystem TAR and an installation receipt.
The TAR replaces the preceding filesystem; appending it could restore files
removed by package upgrades. See the fetched module's `apt/INSTALL.md` for the
isolated native execution contract and its limitations.

[Patch provenance and validation](PATCHES.md) describes the retained fixes and
the 12 native registry tests. CI uses Bazel 8.5.1 and imports existing pinned
Debian packages without producing DEBs. Published entries remain unchanged.
