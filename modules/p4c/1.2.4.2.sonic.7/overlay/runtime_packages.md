# P4C installation interfaces

`p4lang-p4c.runtime` contains the original configured compiler programs, Python driver, P4 include files, driver configurations and Debian documentation. AMD64 also includes the original installed p4testgen; ARM64 follows Make with test tools disabled.

`p4lang-p4c.runtime.debug_symbols` pairs with the runtime ELF Build IDs and GNU debuglink checksums. `p4lang-p4c.runtime_metadata` derives package identity, dependencies, architecture and payload identity from the original Debian recipe and actual installation TAR. Consumers use these producer interfaces directly.
