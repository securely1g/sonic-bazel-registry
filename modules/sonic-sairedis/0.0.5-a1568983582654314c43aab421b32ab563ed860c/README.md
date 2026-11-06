# Sairedis SAI code generation

This version builds the Redis, VS and Proxy SAI stub generator for the platform executing the Bazel action. On an AMD64-to-ARM64 build the Python interpreter and Perl run on AMD64, while the generated C++ is compiled for ARM64. [Sairedis source change](https://github.com/securely1g/sonic-sairedis/pull/10)

The registry tests the same 19 build labels and seven test labels as version 0.0.4. The source archive and registry MODULE patch are pinned in `source.json`.
