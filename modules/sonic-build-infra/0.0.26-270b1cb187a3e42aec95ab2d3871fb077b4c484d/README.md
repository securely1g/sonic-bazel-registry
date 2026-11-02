# Shared DocBook tools with native SONiC interfaces

SONiC WPA generates five installed manuals from its maintained DocBook SGML
sources. This replaces the unpublished `0.0.26` candidate from
[registry #168](https://github.com/securely1g/sonic-bazel-registry/pull/168)
with the same shared CLI/XML/BFD tools plus
[DocBook #74](https://github.com/securely1g/sonic-build-infra/pull/74), which
uses the [kernel tool subset #75](https://github.com/securely1g/sonic-build-infra/pull/75).
The combined source commit preserves all four independent source histories.

| Input or action | Before | After |
| --- | --- | --- |
| WPA `wpa_supplicant.sgml` with `SOURCE_DATE_EPOCH=1598266417` | No declared DocBook converter is available in this candidate | `//tools/build_tools:docbook2man` produces the installed manual with Debian's original SGMLS backend |
| Add DocBook to the shared execution package set | The whole set would enlarge the kernel runtime with unrelated documentation tools | The kernel runtime retains its maintained 63 AMD64/62 ARM64 package roots and their complete dependencies |
| Select native component test/Perl interfaces already used by SONiC consumers | The older .26 candidate lacks the reviewed .25 interface patch | Preserve those interfaces from [registry #147](https://github.com/securely1g/sonic-bazel-registry/pull/147), together with the CLI/XML/BFD source additions |

The one shared `build_tools` APT selection owns DocBook, OpenSP, SGMLS and their
execution libraries. No component-specific execution package set is introduced.
Existing compiler versions, CLI tool contracts and target library ownership stay
unchanged. The native-interface patch is adapted to this combined source; it does
not introduce a second implementation of those interfaces.

Native AMD64 presubmit retains all 35 existing build targets and 26 tests, adds
the historical native-interface regressions and the DocBook/kernel tools-only
checks, and now contains 37 build targets and 41 tests. The real manual backend,
relocated runtime, declared BFD linker and installed TAR contracts remain tested.
This registration validates its explicit external-consumer targets; it does not
copy the old .25 patch's source-CI target arrays into the combined source branch
or claim that all historical source-CI coverage has run.
The tools-only kernel test omits only Debian package creation; cross-target tools
and native compiler/metadata assertions remain covered. No DEB output is created.

Keep this registration Draft while #168, #147 and #74 remain unlanded. The normal
consumer registry remains maintained main; temporary Draft validation selects
this complete immutable catalog plus BCR. Its hash suffix sorts below the old
`.26-75c6327...` suffix, so consumers with that transitive request must explicitly
select this version and verify the resolved graph. Old immutable source and
catalog commits remain available to existing builds. Source/registry validation
does not establish full WPA runtime or MACsec image acceptance.
