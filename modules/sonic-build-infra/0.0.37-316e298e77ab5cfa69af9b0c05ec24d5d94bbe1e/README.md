# Finalized package controls with the retained native tools

This updates the sole unpublished infrastructure `0.0.26` candidate from [registry #179](https://github.com/securely1g/sonic-bazel-registry/pull/179). It adds [infra #77](https://github.com/securely1g/sonic-build-infra/pull/77)'s finalized-control metadata fix while preserving the existing CLI/XML/BFD, DocBook, kernel-tool subset, debug-symbol permissions and native component interfaces. Every published version is unchanged.

The independent source fix is `0b920096239bdafe9952aecde461e70e14b57761` on maintained master. The consumed combined source is `51c838da6ff57295fde6e0bc3807841cb31a8568`: existing `0378d53824b18b253ecbd6faadba00e505ff4ccf` plus only that fix, with its CI branch guard adapted to preserve the existing tools-only checks. Production metadata and regression files match the independent fix exactly. The existing native-interface and registry-visibility patches remain byte-for-byte unchanged.

OTEL's source-built runtime TAR installs `lib/systemd/system/otelcol-contrib.service` and uses its existing finalized release control, version `0.144.0`. It has no Debian source recipe or unfinished helper substitutions. Previously the metadata action invoked `dh_installsystemd` and failed for missing debhelper compatibility input. The owner now runs recipe helpers only for source templates; finalized controls retain their actual dependencies. ELF symbol/dependency analysis and `dpkg-gencontrol` remain active. No DEB is built or new Debian recipe invented.

| Input or action | Before | After |
| --- | --- | --- |
| OTEL's actual finalized control and systemd unit | Fails with unsupported compatibility level 1 | Describes the actual source-built TAR and preserves package identity/unit bytes |
| Source template with the same service | Uses real Debian helpers and requires source compat metadata | Same behavior and same rejection when compat is missing |
| Finalized control with an undeclared target library | Rejects missing target libc | Still rejected; finalized text cannot replace actual ELF dependency analysis |
| Existing debug/native/CLI/XML/BFD/DocBook/kernel features | Reviewed179 candidate interfaces | Preserved, including regular debug-file mode `0644` |

Presubmit retains every registry #179 build and test target:37 builds and 43 test labels, including the extended metadata rule tests. Kernel checks remain tools-only and do not generate packages. The ordinary consumer selects published Distroless `.15`, matching native SONiC image use, while preserving the owner's inherited `.13` minimum. Independent AMD64/Trixie metadata tests pass; ordinary combined-candidate and hosted acceptance are in progress. This does not claim complete OTEL or downstream image acceptance.

The review base combines exact registry #179 inputs with [rules_go #193](https://github.com/securely1g/sonic-bazel-registry/pull/193), so the OTEL consumer can select both requirements from one immutable registry endpoint. Registry #147 is a separate Ready but unpublished registration of landed native source; it is neither rewritten nor treated as a published baseline here. Keep this stack Draft until the exact combined source history and registry prerequisites land, then return consumers to maintained main. Existing frozen catalogs remain available while consumers are deliberately reassessed.
