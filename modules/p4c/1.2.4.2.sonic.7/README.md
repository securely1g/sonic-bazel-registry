# Native P4C 1.2.4.2 for SONiC

Build the existing SONiC compiler selection with native Bazel C++ targets and declared Bison, Flex, IR and Protobuf generation. The upstream compiler commit, Debian recipe and five SONiC patches retain their original identities. Original Protobuf 21.12, P4Runtime, Inja and AMD64 Z3 inputs stay fixed.

The original backend configuration and installed programs remain: eight compiler programs on both architectures, plus the original installed p4testgen on AMD64. Published interfaces are `p4lang-p4c.runtime`, matching `p4lang-p4c.runtime.debug_symbols`, producer `p4lang-p4c.runtime_metadata`, and the existing BMv2 build tool `p4c_bm2_ss`. Legacy package aliases remain available.

Validation compares Bazel compilation actions, generated inputs and installation artifacts with the analyzed Make/CMake contract. The package contract checks installation paths and permissions, ELF architecture and dependencies, absence of installation RPATH, static Protobuf, matching Build IDs/debuglink CRC, and Debian metadata. It inspects target programs as files and runs no compiler, driver, packet or upstream runtime suite.
