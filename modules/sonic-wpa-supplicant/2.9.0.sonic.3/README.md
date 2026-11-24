# WPA supplicant with FIPS 1.11

This release uses the native OpenSSL libraries and installed runtime archive
from SONiC FIPS 1.11. The WPA package test verifies ELF dependencies and
debug symbols, and the upstream executable suite covers the MACsec controlled
port state machine. The source and consumer declare AMD64 support.

The only registry patch stamps the release version. The owner source includes
[the OpenSSL update](https://github.com/securely1g/sonic-wpa-supplicant/pull/5),
[the upstream synchronization](https://github.com/securely1g/sonic-wpa-supplicant/pull/6),
and [the external package-test import fix](https://github.com/securely1g/sonic-wpa-supplicant/pull/7).
