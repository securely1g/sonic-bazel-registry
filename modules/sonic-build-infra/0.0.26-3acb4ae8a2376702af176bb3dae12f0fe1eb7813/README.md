# Go module ZIP locks and CGo warning ownership

Registers the source from https://github.com/securely1g/sonic-build-infra/pull/70.
The `//go:lock.py` interface updates Gazelle ZIP locks with the configured Go SDK.
Project warning flags remain enabled for native C/C++ and are excluded from CGo
through rules_go's documented unsupported-feature mechanism.

Inherited source tools, runtime, packaging and metadata interfaces retain their
existing registry coverage. The Go updater contract runs in the source CI.
