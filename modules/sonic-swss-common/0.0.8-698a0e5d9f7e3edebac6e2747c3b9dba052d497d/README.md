# Common Go binding for gNMI

Update registry #161's single unreleased Common candidate to the combined
source `698a0e5d9f7e3edebac6e2747c3b9dba052d497d` from
[Common #38](https://github.com/securely1g/sonic-swss-common/pull/38).
That alias change is stacked on the exact current
[Common #37](https://github.com/securely1g/sonic-swss-common/pull/37) source
`453985cbf56ba2860ef0ed9cfc21ddaf7efb2038`, preserving its declared-runtime
loader and Go XML self-execution fixes. Both source prerequisites are unlanded.

The native gNMI migration in [buildimage #110](https://github.com/securely1g/sonic-buildimage/issues/110)
imports `github.com/sonic-net/sonic-gnmi/swsscommon`. The owner target
`@sonic_swss_common//goext:swsscommon` accepts that spelling and its
canonical import while retaining one generated Go/C++ binding and public type
identity. Native Make behavior remains unchanged.

The separate consumer selects gNMI's Go 1.25.9 SDK. It retains #161's 13 build
targets, 16 tests (including the loader and hiredis regressions), runtime
preparation and inherited native AMD64/ARM64 matrix, and adds the owner alias
test. No DEB target is selected. The alias test exchanges field/value objects
through the real C++ library using both import spellings. Full gNMI service
coverage belongs to the separate owner consumer migration.

The sole patch updates the module version; the source repository owns all
implementation changes. Published versions remain unchanged. The prior
`0.0.8-c7c6797ace975b95c4e8c547fa687fbbec5b69bf` draft is replaced in this stack,
not retained as a second release. Its contributor PR/commit and validation
remain available as history. Reassess immutable versions if #161 publishes first.
