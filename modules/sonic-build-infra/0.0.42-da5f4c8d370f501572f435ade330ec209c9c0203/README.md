# Large native header lists with the retained build tools

This replaces registry #195's sole unpublished infrastructure `0.0.26` candidate with its existing inputs plus [infra #80](https://github.com/securely1g/sonic-build-infra/pull/80). The source is `2cfc059c2cf1dc3b2f2b2ec1bcd70400b04ecb75`: accepted metadata/tools source `51c838da6ff57295fde6e0bc3807841cb31a8568` plus the standalone header-option fix `29ff728553da66e3f07bcc3b4a27fdb02458a62a`, adapting only CI guards to preserve the existing package-free tool tests. The compiler adapter and its actual C/C++ regression match the standalone feature exactly. Every published module version remains unchanged.

The concrete consumer is [AMD64 gearbox image #154](https://github.com/securely1g/sonic-buildimage/pull/154), whose `@p4lang_pi//:sdk` uses 132 quote roots and 272 system roots. GCC copies those header and library arguments into one environment string. Its exact retained configure command exceeds Linux's 131,072-byte string limit and cannot spawn `cc1`, despite no individual argument exceeding 394 bytes. The existing launcher now forwards quote/system options as well as ordinary includes, preserving their original order and warning classes.

| Input or action | Before | After |
| --- | --- | --- |
| Exact PI compiler command | Collected options reach 136,783 bytes; `cc1` fails with `Argument list too long` | Same options occupy 53,415 bytes; configure-style program compiles |
| Quote-only and system-header roots | Distinct search and warning behavior | Preserved, including ordinary-header rejection under `-Werror` |
| Response files and linker/output operands | Passed through without reinterpretation | Preserved |

All prior features remain: finalized-control metadata from [infra #77](https://github.com/securely1g/sonic-build-infra/pull/77), the native component interfaces, CLI/XML/BFD and DocBook tools, kernel-tool subset, deterministic TAR metadata and debug-file permissions. Finalized controls still use actual ELF dependency analysis; source templates still require their real debhelper compatibility metadata. The existing native-interface and registry-visibility patches are unchanged.

Presubmit retains all 37 prior build targets and 43 test labels, and adds five retained Libtool outputs: the installed program, its two libraries, configure log and compiler-argument receipt. Kernel tests remain tools-only. The ordinary consumer preserves published Distroless `.15` and the owner's inherited `.13` minimum. Source AMD64/Trixie C/C++, Autoconf, recursive Libtool and installed-consumer checks pass; ordinary registry acceptance and the full PI SDK/image rebuild remain pending. No DEB output is introduced.

The PR remains stacked on registry #195 and consumes combined unlanded source, so it stays Draft. Existing frozen consumer catalogs remain available until the replacement passes acceptance. The complete comparison patch must include all cumulative changes from published `.25`, including the retained tools and metadata features.
