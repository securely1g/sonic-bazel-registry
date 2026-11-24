# SAI 1.19.2

SONiC Sairedis at `c41b95c` pins [SAI v1.19.2](https://github.com/opencomputeproject/SAI/releases/tag/v1.19.2) at `5664fda1e55bc7d3ce95505c04b59e32f6d8c3a1`. This module supplies that source's public headers, generated API metadata and static metadata library. The registry SHA256 for the upstream archive is `775838ec8311552dfb447fc4ffaaed9effdac3909f1b2b5c0c7605f5bc34ffa5`.

## Regenerate the Make reference

Use a clean checkout of the tagged source with the 36 release tags and peeled commits listed in [attribute_versions.json](overlay/attribute_versions.json). Upstream's attribute-version generator scans the tags in version order, then scans HEAD. Bazel's source archive lacks this Git history, so the overlay includes the Make-generated [saiattrversion.h](overlay/meta/saiattrversion.h).

Run `make -C meta saimetadata.c` in the checkout. This reference used Debian Trixie on AMD64, Doxygen 1.9.8 and Aspell 0.60.8.1 with its English dictionary. [The expected digests](overlay/bazel/generated_output_sha256.json) cover `saiattrversion.h`, `saimetadata.c`, `saimetadata.h`, `saimetadatatest.c` and `saiswig.i`. These are generated source files shared by AMD64 and ARM64.

## Bazel targets

- `@sai//:metadata` generates the four metadata files using the shared execution tools from Build Infra.
- `@sai//:metadata_library` links the generated metadata. The C consumer test checks the API version and looks up a LAG attribute introduced in 1.19.2.
- `@sai//:generated_outputs_test` compares all five files with Make. `@sai//:configurable_aspell_test` exercises the retained patch which lets the generator use a declared Aspell binary. The upstream Make default remains `/usr/bin/aspell`.
