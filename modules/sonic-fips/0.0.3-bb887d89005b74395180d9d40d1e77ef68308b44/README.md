# Preserve large OpenSSH and Kerberos compiler flag lists

Register [FIPS #14](https://github.com/securely1g/sonic-fips/pull/14) at
`bb887d89005b74395180d9d40d1e77ef68308b44` for the native source base consumed by
[sFlow #152](https://github.com/securely1g/sonic-buildimage/pull/152),
[Orchagent #151](https://github.com/securely1g/sonic-buildimage/pull/151), and
[MACsec #149](https://github.com/securely1g/sonic-buildimage/pull/149).
Their Distroless `.15` closure makes GCC's generated `COLLECT_GCC_OPTIONS`
string too large when launching `cc1`; the compiler itself starts normally.
The owner sends ordered `CPPFLAGS` through GCC14's `-Wp,@file` preprocessor
response interface. CFLAGS, LDFLAGS, configure features and installed runtime
interfaces stay unchanged. Driver-only CPPFLAGS are rejected explicitly.

The ordinary external consumer preserves the inherited published
`rules_distroless/0.9.4.sonic.13` interface and all 18 output targets/five
package and integration tests on native AMD64 and ARM64. Source CI additionally
runs the real oversized-argument Autoconf/GCC14/recursive-Make regression and
the original client/crypto suites. No source override or DEB output is added.

A separate `.15` consumer attempt passed the compiler-launch stage and exposed
an existing provider-selection gap: Debian OpenSSL headers 3.5.6 precede the
source 3.5.7 headers while the source library is loaded. Direct and response
flags select the same wrong header in the retained real-header diagnostic.
The strict mismatch check correctly rejects it. A separate owner/registry
follow-up selects the source OpenSSL SDK and carries the cumulative `.15`
acceptance. Image consumers must wait for that positive pairing and strict
mismatch-negative validation; this transport registration alone is insufficient.

This builds on the published entries through
[registry #184](https://github.com/securely1g/sonic-bazel-registry/pull/184).
It retains the already-landed FIPS #9/#10 execution-root mappings and OpenSSL
compiler metadata normalization, plus FIPS #11's provider/engine RPATH fix.
The inherited runtime, SDK, debug, package-metadata and integrity checks remain.
The core's random integrity key and assembly/timestamp reproducibility gaps
are unchanged; this does not establish full-image byte reproducibility.
All published entries through `0.0.3-44d18af69f1b1868cebd41a93a76feb7c0b9a0f6` are preserved.

Commit suffixes do not sort chronologically. Consumers must align direct and
transitive requests, use a root `single_version_override` where needed, and
verify the actually resolved source module. Ordinary registry defaults remain
on maintained main; a Draft consumer may use the reviewed full registry SHA
for this candidate. Registry/source CI and full-image acceptance are separate
claims; see the PR's current evidence before adopting the candidate.
