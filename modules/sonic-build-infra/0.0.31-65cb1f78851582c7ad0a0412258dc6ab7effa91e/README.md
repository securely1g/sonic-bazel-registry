# Native sFlow runtime infrastructure dependency

Register maintained-master commit `65cb1f78851582c7ad0a0412258dc6ab7effa91e`, the merge of [sonic-build-infra#98](https://github.com/securely1g/sonic-build-infra/pull/98), for [sonic-buildimage#152](https://github.com/securely1g/sonic-buildimage/pull/152). It adds `sflow_debian` (`dmidecode:amd64=3.6-2`, `libhiredis1.1.0:amd64=1.2.0-6+b3`, `libmnl0:amd64=1.0.5-3`, `lsb-base:amd64=11.6`) to the unified APT lock, preserving all 2,429 prior package records and 58 prior dependency sets. Existing native tools, archive rules, target runtimes and installation RPATH support remain available.

The source archive is fetched from the maintained repository and verified by SHA-256. Published versions remain unchanged.
