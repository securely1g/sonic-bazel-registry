# Management-common with shared YANG owners

Registers `sonic-mgmt-common@1.0.1-24211db5e3f7e514246f60572169260a0b5f0589`
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

This registration supersedes PR #219 by incorporating deterministic YANG
documentation discovery from landed [source #4](https://github.com/securely1g/sonic-mgmt-common/pull/4),
ensuring reproducible code-generation TARs across build roots.
