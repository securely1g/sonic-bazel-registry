# Platform daemon installation interfaces

Register source-built Python 3.13 installation TARs and distribution metadata
used by the AMD64 Trixie VS PMON image. The aggregate covers the setup.py owners
in the source repository; it does not build Debian packages or wheels.

Source: https://github.com/securely1g/sonic-platform-daemons/pull/1

Public targets: `@sonic-platform-daemons//:daemons.runtime` and
`@sonic-platform-daemons//:daemons.runtime_metadata`. Application roots retain
protobuf 29.0 to match the original grpcio-tools 1.71.0 generator.

The external consumer checks original setup.py versions, dependencies, Python
files, scripts, entry points, modes and ownership. Source CI separately covers
the generated protocol bindings and daemon tests.

The pinned source is available from the contributor fork during review. This
registration remains Draft until the source PR lands.
