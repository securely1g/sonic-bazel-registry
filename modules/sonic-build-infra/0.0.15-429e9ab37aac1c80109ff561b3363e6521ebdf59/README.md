# Replace an explicitly identified inherited package

This entry registers [build-infra #28](https://github.com/securely1g/sonic-build-infra/pull/28)
for [Syncd image #13](https://github.com/securely1g/sonic-buildimage/pull/13).
The debug image needs to replace an inherited APT OpenSSH package with its
hash-verified Make FIPS payload while retaining truthful dependency metadata.

`selection.select` accepts an explicit `retained_replacements` mapping bound
to the inherited package's normalized dependency control record. It rejects
stale, missing, redundant or installed-dpkg replacements, preserves ordinary
conflict checks and validates the final package inventory. Receipts retain the
before/after controls and source hash. The consumer remains responsible for
payload hashes and file-ownership policy; this does not alter dpkg status.

The sole source patch aligns the module version. Registry CI selects existing
APT input, dependency, selection, adapter and Protobuf-header targets on native
AMD64 and ARM64. These targets import existing package inputs and produce tar
files; they do not create DEBs. Source workflow and full Syncd image validation
are separate. This source remains unlanded, so this candidate stays Draft.
