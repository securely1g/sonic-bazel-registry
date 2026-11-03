# Pinned OpenConfig linter

Exports `@oc-pyang//:openconfig_linter` for Python consumers and
`@oc-pyang//:oclint` as an execution tool. The source revision
`4607fd1987d4f586aba03b40f222015cb3ef8161` is the exact oc-pyang revision used
by sonic-mgmt-common's Make build (upstream version 0.1.10).

The overlay supplies Bazel declarations only; it does not patch the linter.
Python 3.13, pyang 2.4.0, lxml 5.3.0 and setuptools 75.8.2 are declared and
hash-locked. These match the management-common migration's selected tool set.
The unused upstream documentation generator and its Jinja dependencies are
outside this linter target.

The AMD64 consumer CI runs every upstream `tests/oclinter` success and failure
fixture with its original Makefile's OpenConfig-only setting. No build action
clones a repository, invokes Make, or produces a DEB.
