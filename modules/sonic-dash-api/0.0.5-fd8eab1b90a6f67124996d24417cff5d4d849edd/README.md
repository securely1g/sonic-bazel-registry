# DASH HA original schema and retained runtime metadata

This review composition retains source [API #6](https://github.com/securely1g/sonic-dash-api/pull/6)
runtime metadata and adds the independent original-schema interface from
[API #7](https://github.com/securely1g/sonic-dash-api/pull/7). Its final MODULE-only
integration commit aligns the shared infrastructure to registry #195's verified
`.26-51c838da` candidate. The two source feature branches remain unchanged.

The actual HA source at `5a2508a4` uses API schema `18a29c1c`, where HaScopeConfigKey
has ha_scope_id=1 and vdpu_id=2. Current API consumers use the later reversed
numbers. The owner exposes the three original files separately; current C++ and
Python targets keep their schema. HA retains its original prost Rust generator.
The real protoc descriptor/hash test protects this wire contract.

All six build targets and four tests from registry #156 are retained, with two
schema outputs and its test added. Native consumers explicitly select published
Distroless .15 and the exact current infrastructure candidate. No DEBs are built.
The earlier registry #140 proposal remains untouched; consumers and landing order
must be reconciled separately before promoting this combined candidate.
