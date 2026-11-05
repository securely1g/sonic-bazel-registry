# WPA source TARs for the MACsec image

SONiC's `docker-macsec` needs the patched WPA supplicant and its database
adapter. This entry consumes the source-owned targets from
[WPA PR #1](https://github.com/securely1g/sonic-wpa-supplicant/pull/1) and its
[compiler-flag fix #2](https://github.com/securely1g/sonic-wpa-supplicant/pull/2), which
compile the repository's selected source with `debian/config/wpasupplicant/linux`.
The public outputs are `wpasupplicant_pkg`, its matching `debug_symbols` output,
and `runtime_packages.json`. They include `wpa_supplicant`, `wpa_cli`,
`wpa_passphrase`, the declared service/configuration/documentation payload and
non-executable detached symbols. No DEB-producing targets are selected.

WPA is an upstream third-party project even though this patched source is kept
in a SONiC fork. The registry version is `2.9.0.sonic.1`, matching the source
module's mapping of WPA 2.9 and its existing SONiC/Debian downstream changes.
The immutable archive owns all build definitions. A narrow registry patch
updates only the source MODULE dependency declarations to match the registered
module; it does not replace the owner build implementation.

The ordinary consumer selects Common `.8-43598143`, infrastructure
`.25-3ee15ec9`, FIPS `.3-15fcb926` and published Distroless `.16`.
FIPS source `15fcb926a302059ec379f0c2fd15eb3d88bda4c9` declares version `.3`.
The earlier review entry called that same source `.5`; this entry now uses the
corrected owner registration from [FIPS #221](https://github.com/securely1g/sonic-bazel-registry/pull/221).
The source commit is unchanged by this correction.
Direct version requirements select these current candidates;
there are no root source overrides or replacement build definitions. It keeps
Common's declared YANG-enabled default. AMD64 CI builds all three public outputs
and executes the owner's upstream, installed-package, flag-preservation and
large-include-list tests. Those tests check exact payload bytes/modes/links/epoch,
three ELF/debug pairs, real GDB lookup, declared Common/libnl/OpenSSL loading,
the IEEE PBKDF2 vector and private supplicant/control-client PING/PONG. Twelve
upstream programs compile; nine self-contained suites execute. Three HTTPS/X.509
programs have compile-only coverage because their external fixtures are absent.

The previous entry is [registration #185](https://github.com/securely1g/sonic-bazel-registry/pull/185).
This separate fix updates its sole unpublished WPA version to source commit
`d14bf3ac61597273e8940f9b14c8034568cccff7`. In
[MACsec image #149](https://github.com/securely1g/sonic-buildimage/pull/149),
133,110 bytes of ordered preprocessing flags exceeded Linux's limit before Make
could start. The owner now sources a Bash adapter through `rules_foreign_cc`'s
public tool-prefix hook and passes the same flags in GCC's response file.
The added test reproduces the original exec failure, verifies recursive C/C++
compilation with quoted values and include paths, and rejects driver options in
preprocessing flags. No validation or runtime features are removed.

The isolated review catalog starts from maintained main and preserves published
[libnl #181](https://github.com/securely1g/sonic-bazel-registry/pull/181),
[Distroless #200](https://github.com/securely1g/sonic-bazel-registry/pull/200), and
[infrastructure #218](https://github.com/securely1g/sonic-bazel-registry/pull/218).
It retains the exact Common `.8-43598143` review entry and its runtime backport
from [Common #199](https://github.com/securely1g/sonic-bazel-registry/pull/199),
alongside the newer published Common entry, and carries the corrected
[FIPS #221](https://github.com/securely1g/sonic-bazel-registry/pull/221) candidate.
The source MODULE patch and registry MODULE match byte-for-byte. The source
archive, runtime code, compiler-response-file fix, three build targets and four
tests are unchanged. Current-candidate ordinary-consumer and MACsec acceptance remains pending on
this exact dependency graph; earlier source/registry and selected-image receipts
retain their original FIPS version and catalog attribution. Keep Draft
until relevant prerequisites land, this registration targets maintained main and
current CI passes. Every published version remains unchanged.

The image consumer is [buildimage issue #131](https://github.com/securely1g/sonic-buildimage/issues/131).
Image assembly, an actual installed macsecmgrd/WPA handoff and full VS installer
coverage are separate from source/registry acceptance. ARM, cross builds,
physical MACsec traffic and ASIC/FIPS POST behavior are outside this phase.

This dependency refresh selects maintained infrastructure source 3ee15ec9 through
registry #218. Its numeric version is .25; published .26 entries remain intact.
Fresh module-graph checks must verify the selected version, followed by the
unchanged ordinary-consumer outputs and tests. This metadata/source-patch proof
does not establish native or image acceptance. Existing worker runs and earlier
receipts retain their exact preceding dependency inputs.
