# Platform daemon wheels for PMON

PMON uses the eleven public Python 3.13 wheels built by Platform Daemons.
`@sonic-platform-daemons//:daemons.wheels` exports the wheels.
`:daemons.runtime` exports their installation TARs and `:daemons.runtime_metadata`
exports the matching wheel identities and Python requirements. The execution tool
for YCable uses the owner’s locked grpcio-tools version.

The external consumer verifies each wheel SHA-256 and installed METADATA, plus
the original setup.py versions, dependencies, Python files, entry points,
permissions and ownership. The owner runs the native daemon suites.
