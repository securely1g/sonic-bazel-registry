# lm-sensors 3.6.0 SONiC native module

The recipe preserves Debian 1:3.6.0-7.1, its eight source patches and the two
SONiC packaging patches. C, Flex and Bison actions build the selected programs
and SONAME libsensors.so.5 directly. The original scanner test driver is built
and exercised on configuration text without accessing sensors.

Public installation interfaces:

- `lm-sensors.runtime`, `libsensors5.runtime`, `libsensors-config.runtime`, `fancontrol.runtime`, `sensord.runtime`
- `runtime_packages.json` and the five corresponding `<package>.control` TARs
- `<package>.runtime.debug_symbols` for lm-sensors, libsensors5 and sensord
- `debug_sources` for the original source-debug handoff

`libsensors-config.runtime` remains an optional standalone payload. PMON selects its owner
record and control files when it installs the source-built configuration.
Consumers using the Debian configuration package can keep that selection.

Documentation is installed by the declared original Debian changelog helper
and compressed at the final installed-file boundary with pigz. Runtime TARs
are uncompressed. Scanner, version and help tests avoid sensor enumeration;
installed-resource and debug tests inspect package contents without running
maintainer scripts or touching devices.
