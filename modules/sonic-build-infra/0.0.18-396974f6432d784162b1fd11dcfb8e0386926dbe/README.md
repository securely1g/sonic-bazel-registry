# Declared tools for existing configure/Make source builds

Register the shared source tool bundle from [build-infra #53](https://github.com/securely1g/sonic-build-infra/pull/53).
`foreign_runtime` supplies relocatable Autotools/Libtool, protobuf/gRPC and Thrift generators, Python, Perl XML modules and Graphviz. `metadata_runtime` provides the existing pinned Doxygen/Aspell tools through public wrappers. Both reuse the pinned shared dependency/tool resolver.

PI, BMv2 and DASH use these declared tools with their upstream configure/Make recipes. Their source builds emit runtime and matching debug TARs directly; this entry adds no Debian package producer and does not change legacy Make recipes.

The native AMD64/ARM64 matrix retains existing toolchain, runtime and debug tests and adds real code-generation/relocation tests with an empty host PATH. Source PR CI and these registry consumer checks must both pass. The version is 0.0.18 so minimum-version selection cannot silently choose the older 0.0.17 tool API.

This is a draft registration of an unmerged source revision. Wait for #53 to land, repin to the maintained-branch commit, and revalidate before marking Ready.
