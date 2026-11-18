# sonic-snmpagent

Registry version `2.1.1-61e1b148eca5d14f3ad5eb838b9dd724408d0820` uses [the source snapshot](https://github.com/securely1g/sonic-snmpagent/tree/61e1b148eca5d14f3ad5eb838b9dd724408d0820) from `securely1g/sonic-snmpagent`. The source repository owns its build definitions and dependency pins; this entry adds the commit-qualified module identity and retained registry integration.

The pinned source is preserved on [the owner branch](https://github.com/securely1g/sonic-snmpagent/tree/codex/registry-deps-sonic-snmpagent-20261118) and is not yet landed. This registration must remain Draft until the source prerequisite lands.

```starlark
bazel_dep(
    name = "sonic-snmpagent",
    version = "2.1.1-61e1b148eca5d14f3ad5eb838b9dd724408d0820",
)
```

Current dependency versions are in [MODULE.bazel](MODULE.bazel). They select the published catalog at [`3d1cc5e8dfd5`](https://github.com/securely1g/sonic-bazel-registry/tree/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf).

## Presubmit contract

The retained registry matrix selects: `amd64`. Platform mappings, additional architecture-specific targets and consumer settings are defined in [presubmit.json](presubmit.json). These declarations describe coverage, not a claim that CI passed.

Build targets:

```text
@sonic-snmpagent//:sonic_snmpagent_wheel
@sonic-snmpagent//:snmp_install
```

Test targets:

```text
//:installed_wheel_test
```

The standalone consumer is [tests/integration](tests/integration).

Source archive integrity and the ordered patch/overlay inputs are recorded in [source.json](source.json). [Previous registration notes](https://github.com/securely1g/sonic-bazel-registry/blob/3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf/modules/sonic-snmpagent/2.1.0-a27e093fac394f7871ec1b19bb12ca6739c29fa9/README.md) describe `2.1.0-a27e093fac394f7871ec1b19bb12ca6739c29fa9` and are historical rather than instructions for this version.
