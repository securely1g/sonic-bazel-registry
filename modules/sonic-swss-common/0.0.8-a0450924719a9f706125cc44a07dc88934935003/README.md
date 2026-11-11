# Declared loaders for Common native test execution

Registers https://github.com/securely1g/sonic-swss-common/pull/37.
Go and Python native test runners use the declared Trixie ELF interpreter,
including Go's XML wrapper self-execution. The source-owned loader regression
and hiredis CGo test join the inherited registry matrix.

Standalone consumption retains the declared Go 1.25.0 SDK and existing source
library dependencies. Buildimage also validates Go 1.26.7 and both YANG modes.
