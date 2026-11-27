# SONiC YANG management 1.0.1-bef87d0525044844e67f42eab4712cc010e33cba

Source and build targets come from [src/sonic-yang-mgmt in buildimage](https://github.com/securely1g/sonic-buildimage/tree/bef87d0525044844e67f42eab4712cc010e33cba/src/sonic-yang-mgmt). The registry selects that directory from the immutable archive and qualifies the module version. The source owner supplies the BUILD file, Python lock and runtime test.

The independent consumer builds SWSS Common’s schema header with the selected management library. The wheel, install TAR, runtime metadata and SONiC production-model test use the same source recipe.
