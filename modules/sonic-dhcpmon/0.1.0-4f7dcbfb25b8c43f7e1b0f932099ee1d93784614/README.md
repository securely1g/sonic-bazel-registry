# DHCP monitor source registration

Registers the immutable source commit from https://github.com/securely1g/sonic-dhcpmon/pull/1. This is a Draft prerequisite for the coordinated DHCP image, not a released module until merged.

The manifest selects native AMD64 source runtime/debug TARs, installed-package metadata (not DEBs), and ten production utility behavior groups using declared target-loader payloads. ARM, live forwarding, monitor health and dual-ToR are not covered. The canonical registry default remains securely1g main.

Validation: source archive SHA256 and source-file equality verified; registry entry/overlay and publication planning must pass. Fresh configured build/test validation remains pending due to pinned Debian snapshot 503/504/timeouts. Historical Nov 1 source/image results cover the frozen candidate only, not this source head, current dependency graph or declared-runtime wrapper. Do not treat the presubmit declaration as a passed run.

Explicit candidate validation from this reviewed registry checkout (never an implicit production fallback):

```sh
python3 ci/registry_ci.py run --module sonic-dhcpmon --version 0.1.0-4f7dcbfb25b8c43f7e1b0f932099ee1d93784614 --architecture amd64 --work-dir /tmp/dhcpmon-registry-consumer --artifacts /tmp/dhcpmon-registry-evidence --bazel bazel
```

Use fresh empty work/evidence directories. Before execution, inspect the configured actions for the listed targets; no DEB-producing targets are authorized by this migration. Source PR must land before this registration; downstream image acceptance follows registration availability.
