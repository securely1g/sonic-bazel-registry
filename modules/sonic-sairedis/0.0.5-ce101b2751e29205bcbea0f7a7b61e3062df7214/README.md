# Sairedis SAI code generation

This version registers landed source `ce101b2751e29205bcbea0f7a7b61e3062df7214`. Its Redis, VS and Proxy SAI stub generator runs with Python selected for the execution platform, so an AMD64 builder can generate C++ for ARM64. [Sairedis source change](https://github.com/securely1g/sonic-sairedis/pull/10)

The registry retains all 19 build labels and seven test labels from published version 0.0.4. The identity patch preserves the published gzip toolchain registration and uses the landed source's Common and infrastructure declarations. The source archive and all four patches are pinned in `source.json`.

The ARM64 build caught a type mismatch in the ZeroMQ buffer logs. For example, the truncation message used `%d` for a configured buffer size stored as a `long`. Patch `0002` applies the producer's correction to this archive so GCC can check the log calls with `-Werror=format`. [Sairedis #11](https://github.com/securely1g/sonic-sairedis/pull/11)

The two Syncd MACsec POST status logs pass serialized status text to a printf-style `%s` field. Patch `0003` passes the C string expected by the logger so the ARM64 `libsyncd` build compiles with format checking enabled. [Source fix](https://github.com/securely1g/sonic-sairedis/commit/c97f9d0ad590092e2b5c045c07625cbc4e93f351)

Patch `0004` also corrects integer formats found by compiling the producer with the same format checks. For example, the Syncd counter log uses `%zu` for vector lengths, and saidump uses `PRIu64` for its 64-bit size limit. [Sairedis #12](https://github.com/securely1g/sonic-sairedis/pull/12)
