# SNMP source wheel and install TAR

`sonic-snmpagent@2.1.0-a27e093fac394f7871ec1b19bb12ca6739c29fa9` registers the landed
[SNMP source PR #1](https://github.com/securely1g/sonic-snmpagent/pull/1). The source
module's base version is `2.1.0`; the registry suffix names its exact source commit.
The generated MODULE overlay changes only that version and adds its generated header.
The wheel remains `asyncsnmp-2.1.0-py3-none-any.whl`.

[Buildimage PR #134](https://github.com/securely1g/sonic-buildimage/pull/134) builds
`//tools/bazel/oci:snmp_archive` and its debug image from the owner wheel and the
`snmp_install` TAR, which installs `/usr/share/snmp/sysDescr_pass.py`.

| Input or action | Before | After |
| --- | --- | --- |
| Register the accepted SNMP source | Unpublished `2.1.0` names the pre-merge `5445b313` archive. | `2.1.0-a27e093fac394f7871ec1b19bb12ca6739c29fa9` names the landed source. Both commits have the same complete Git tree. |
| Install the owner outputs | Registry CI checks wheel metadata, all package files, installed AgentX interfaces and the sysDescr TAR. | The same two build targets and installed test run on native AMD64; payload and wheel versions stay unchanged. |

The original source acceptance recorded 419 passed tests, seven existing skips
and four installed tests. Registry [run 41442267822](https://github.com/securely1g/sonic-bazel-registry/actions/runs/41442267822)
and image [run 41457027978](https://github.com/securely1g/sonic-buildimage/actions/runs/41457027978)
validate the previous registration and image. They are historical evidence, not
CI acceptance of this updated registration. The new archive was verified against
every file and Git mode of the identical landed source tree.

The original Python, tar.bzl, platform and integration-test dependencies are
unchanged. Static declaration equality does not establish that Bazel will select
the same complete graph against a later registry main; new registry CI must
validate resolution and the installed consumer. No C++ owner implementation or
package source is changed here.

PR #134 still uses temporary source archive overrides. After this registration
lands, it can select the commit-qualified module version and remove both SNMP
and the already-published platform-common overrides. This registration does not
claim final VS/installer, hardware or multi-namespace acceptance.
