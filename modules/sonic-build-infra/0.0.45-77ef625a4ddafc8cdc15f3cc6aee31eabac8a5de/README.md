# sonic-build-infra 0.0.45

Registers merged Infra commit `77ef625a4ddafc8cdc15f3cc6aee31eabac8a5de`
from PR #136. `sonic_deb` accepts explicitly declared mtree sources and streams
compressed control/data members directly into the final Debian package.
The legacy TAR input remains available. This entry retains the earlier shared
OCI APIs and independent consumer checks, and selects the source's published
rules_distroless 0.9.4.sonic.26 dependency.
