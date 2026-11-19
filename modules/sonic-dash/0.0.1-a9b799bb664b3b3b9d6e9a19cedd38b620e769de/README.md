# DASH with the native PI SDK

This version registers DASH `a9b799bb664b3b3b9d6e9a19cedd38b620e769de`. Its recursive Make adapter links
`libsai.so` against the ABI filenames `libpiprotogrpc.so.0` and
`libpiprotobuf.so.0` exported by the `p4lang-pi` `0.1.3.sonic.6` SDK.
[DASH source change](https://github.com/securely1g/DASH/pull/5)

The AMD64 and ARM64 presubmits build the SDK, runtime TAR, debug TAR and
runtime package inventory. The runtime test checks the installed artifacts.
The Make regression test exercises compiler and linker flag propagation and
the ABI filenames used by the final shared-library link.
