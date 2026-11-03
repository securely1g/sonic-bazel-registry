# SONiC FIPS source OpenSSL selection candidate

This draft registers source commit `e910ec2217bc42aae8a185a398b23a329f482fef`
from [FIPS #15](https://github.com/securely1g/sonic-fips/pull/15), stacked on
[FIPS #14](https://github.com/securely1g/sonic-fips/pull/14). The registry branch
uses a review base containing exact [#194](https://github.com/securely1g/sonic-bazel-registry/pull/194)
and [Distroless #200](https://github.com/securely1g/sonic-bazel-registry/pull/200),
then replaces the sole unpublished FIPS candidate. Published entries are unchanged.

OpenSSH explicitly selects the source OpenSSL SDK using upstream
`--with-ssl-dir`, with SONiC's source multiarch library directory first. The
actual `.15` graph previously selected Debian 3.5.6 headers while loading the
source 3.5.7 library; OpenSSH's strict check rejected that mismatch. The same
check remains enabled. This source feature is separate from #14's ordered
GCC14 preprocessor-response transport repair, which remains included.

The ordinary native AMD64/ARM64 consumer explicitly selects candidate
Distroless `0.9.4.sonic.16`; the owner's module minimum remains `.13`.
The prior `.15` consumer passed all tests on ARM64, but AMD64's original
OpenSSL AF_ALG test exposed a separate shared header-export defect: the
importer selected ARM64 kernel headers on AMD64. Distroless #200 fixes
those target include paths without skipping crypto tests or changing this
FIPS source. The registry's own diff remains a single FIPS feature.
All 18 runtime/debug/SDK/metadata outputs and five installed/integration tests
are retained. Source CI additionally runs actual OpenSSH configure against
source-built SDK TARs: the matching source pair must succeed, and changing
only a private header must be rejected by the original mismatch check.

Native source, ordinary `.16` registry acceptance, and loaded image acceptance
are separate checks. The image consumers are sonic-buildimage #149, #151 and
#152. Keep them frozen until the cumulative candidate is accepted; selecting
this registry entry alone does not prove their images work.

The cumulative source also retains the landed execution-root mappings,
OpenSSL compiler metadata normalization and SymCrypt provider/engine RPATH
fixes inherited through #172/#184. No crypto, entropy, integrity sealing or
DEB output is changed. Sealed-core and whole-image reproducibility remain
separate, unproven claims.

Committed registry defaults remain maintained main plus BCR. Temporary Draft
validation replaces main with one explicit candidate catalog. Consumers with
an explicit FIPS single_version_override must update it with the direct pin
and verify the fetched MODULE; do not rely on SHA suffix ordering.
