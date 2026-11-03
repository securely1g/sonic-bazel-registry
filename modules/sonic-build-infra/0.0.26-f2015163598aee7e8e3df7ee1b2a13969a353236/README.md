# Shared CLI source-generation tools

This candidate registers [build-infra #72](https://github.com/securely1g/sonic-build-infra/pull/72)
for the Framework CLI source migration tracked by
[buildimage #109](https://github.com/securely1g/sonic-buildimage/issues/109).
Framework's checked-in klish 2.1.4 patches need GNU patch; its existing
`klish_platform_features_process.sh` and command-tree schema checks need
xsltproc and xmllint. The shared foreign runtime now provides these tools with
its declared private loader and library closure. Consumers use those existing
public execution-tool interfaces instead of creating their own tool package set.

The source archive is pinned to `f2015163598aee7e8e3df7ee1b2a13969a353236`.
The version patch only aligns the registry identity; the existing cross-test
visibility patch and validation overlay remain unchanged. No published entry is
modified. This is an independent registration from registry main: it does not
require the separate management-common registration.

The native AMD64 presubmit builds the three public tool targets and runs the
shared foreign-runtime regression, including real patch/rejection, XML schema
positive/negative checks and XSLT after relocation with an empty PATH. Existing
source-TAR, compiler, runtime, package-metadata and AMD64-to-ARM compiler checks
remain enabled. The kernel runtime is still constructed through its manifest
output. Its separate sample-DEB-producing regression is deliberately not run
in this no-DEB CLI migration; neither is the native ARM fallback that calls it.
Existing published registrations and source ARM workflows are unchanged.

Keep this registration Draft while source PR #72 remains unmerged. Local source
runtime tests do not substitute for the external-consumer registry CI or a
complete Framework image build.
