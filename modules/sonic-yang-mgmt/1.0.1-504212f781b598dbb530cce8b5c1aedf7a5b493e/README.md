# SONiC YANG management 1.0.1-504212f781b598dbb530cce8b5c1aedf7a5b493e

Source and build targets come from [src/sonic-yang-mgmt in buildimage](https://github.com/securely1g/sonic-buildimage/tree/504212f781b598dbb530cce8b5c1aedf7a5b493e/src/sonic-yang-mgmt). The registry selects that directory from the immutable archive and qualifies the module version. The source owner supplies the BUILD file, Python lock and runtime test.

The independent consumer builds SWSS Common’s schema header with the selected management library. The wheel, install TAR, runtime metadata and SONiC production-model test use the same source recipe.
