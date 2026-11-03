# Scapy for SONiC

`scapy@2.6.1.sonic.1` builds the exact Scapy source selected by SONiC's
`src/scapy` gitlink (`8e08cbf759de6709a5b4af6bea3655d293129bb4`).
The module version describes the upstream 2.6.1 source integration. The wheel
and installed Python distribution retain Make's explicit `2.6.1.dev0` version:
`scapy-2.6.1.dev0-py3-none-any.whl`.

The two selected SONiC patches preserve version discovery for a Git submodule
and close all AsyncSniffer sockets after open/close errors. Their original
authorship is retained and the registry lists them in application order.
One test-only patch updates upstream’s obsolete .git-directory expectation to
assert the retained SONiC submodule behavior. No production source bytes are
changed by that test adaptation. A second test-only patch gives the native TLS
server an ephemeral loopback port so it cannot conflict with earlier automaton
fixtures; all original TLS handshake and shutdown assertions remain.
No upstream Bazel support or compatible BCR/SONiC registry module existed at
implementation time. This entry adds only the missing integration through
`rules_python` 1.9.0 and the pinned upstream Python build frontend/backend; it
does not fork Scapy or serialize wheels itself. Scapy’s existing `pyproject.toml`
and `setup.py` remain the only package metadata definitions.

Public targets are `@scapy//:scapy` (Python library) and `@scapy//:wheel`.
The verified consumer is sonic-buildimage's docker-orchagent Python runtime,
currently fed by Make's wheel. Image integration is separate work tracked by
[issue #114](https://github.com/securely1g/sonic-buildimage/issues/114).
This producer addresses [issue #101](https://github.com/securely1g/sonic-buildimage/issues/101).
It introduces no DEB targets and changes no Make recipe.

## Validation

The registry's independent AMD64 consumer builds the wheel and runs:

- `wheel_test`: compare payload inventory, bytes, modes, version, license,
  console entry points, dependencies and supported metadata with a native
  legacy `setup.py bdist_wheel` reference built from declared source and tools. Install
  the result using the upstream `installer` library; execute the installed CLI,
  decode IPv4/IPv6 packets and exercise the actual patched AsyncSniffer cleanup.
- `upstream_test`: run upstream's Linux UTscapy configuration against the
  installed wheel under Python 3.13, without source-tree import fallback.
  Root/network, optional libpcap, external packet tools and hardware/CI-service fixtures are
  excluded by their upstream tags. Original assertions remain unchanged except
  for the documented submodule expectation fixed by the selected SONiC patch.

The build/test requirements lock includes the native Python build tools and
upstream optional test dependencies; none enters the runtime wheel. Brotli
1.2.0 supplies a Python 3.13 wheel, replacing upstream tox's older test-only
constraint; all original assertions remain. Runtime Scapy has no mandatory
third-party Python requirements. This candidate claims AMD64/Python 3.13 only.

The source action runs `python -m build --wheel --no-isolation` with pinned
frontend/backend packages, no package index access, Make's explicit version
override and a fixed source epoch. The independent legacy setup.py reference
checks its payload and metadata, including upstream Maintainer and Keywords.
No metadata or wheel serialization is reimplemented in the registry.
