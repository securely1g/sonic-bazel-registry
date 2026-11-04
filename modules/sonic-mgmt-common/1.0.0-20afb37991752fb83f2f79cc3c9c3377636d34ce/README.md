# Management-common with shared YANG owners

Registers `sonic-mgmt-common@1.0.0-20afb37991752fb83f2f79cc3c9c3377636d34ce`
from the exact tested [source #3](https://github.com/securely1g/sonic-mgmt-common/pull/3).
The only registry source patch gives its MODULE the immutable source version.

Management-framework and gNMI compile against the public CVL, translib and
OpenConfig bindings and install the owner's runtime TAR. This integration root
and management-common now select the public `openconfig_goyang` and
`openconfig_ygot` modules, sharing one Go type graph. They no longer apply copies
of those two owners' patches. The other existing Go patches, Go 1.25.9/Python 3.13,
import paths, source schemas and Make/vendor inputs remain unchanged.

The ordinary native AMD64/Trixie integration root retains all six build targets
and four tests from registry #165: it compiles the separate Go consumer and
public libraries, builds both TARs and checks installed contents, schemas and
20 independent generator runs. Only the two duplicated dependency overrides
are replaced by normal public-module dependencies. It uses no management-common
source override and no DEB producer.

This is a Draft follow-up to [registry #165](https://github.com/securely1g/sonic-bazel-registry/pull/165),
with [goyang #212](https://github.com/securely1g/sonic-bazel-registry/pull/212) and
[ygot #214](https://github.com/securely1g/sonic-bazel-registry/pull/214) on the
explicit review base. It replaces the sole unpublished management-common
candidate; maintained registry files and current image pins remain unchanged.
After acceptance, gNMI's registration must update its management-common minimum,
and consuming image roots must update both their direct dependency and existing
`single_version_override`. Commit suffixes do not provide chronological version
ordering. No consumer adoption is included in this registration.

Source #3 has verified current-head native CI, all 14 source test reports,
20 generator runs, schema invalidation/restoration, real owner/consumer module
graphs and clean tracked files after the separate consumer. Its runtime TAR
matches the landed producer. Generated Go differs only in the dependency's
provenance comment. The inherited documentation ordering difference is repaired
separately by [source #4](https://github.com/securely1g/sonic-mgmt-common/pull/4),
which is not included in this source pin. Full code-generation TAR reproducibility
across build roots is therefore not claimed here. This registration's ordinary
consumer acceptance and current-head hosted CI remain pending.

The shared ygot module preserves the two historical SONiC patch files and
explicitly documents additional compatibility and correctness repairs verified
by the original full suite. Its complete runtime source tree is not claimed to
be byte-identical to the old vendored dependency. Actual management-common
source/consumer behavior is covered by source #3's acceptance; Docker/VS
assembly remains separate.
