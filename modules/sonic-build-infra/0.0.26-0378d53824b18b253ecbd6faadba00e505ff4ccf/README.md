# Non-executable debug symbols with the existing native tools

This registration carries [infra #76](https://github.com/securely1g/sonic-build-infra/pull/76)
into the sole unpublished `0.0.26` candidate, replacing the entry from
[registry #175](https://github.com/securely1g/sonic-bazel-registry/pull/175).
It retains that candidate's CLI/XML/BFD, DocBook and kernel tool subset features,
its native component interfaces, all patches and all existing consumer tests.
Published versions and earlier immutable catalogs are unchanged.

SONiC WPA's source-built `wpasupplicant.debug.tar.gz` contains three `.build-id`
debug ELF files. The previous shared TAR helper assigned its default executable
mode to those data files. The owner fix uses upstream `mtree_mutate` to set only
regular debug files to `0644`; directories remain traversable and links retain
their metadata. It does not add a TAR writer or change ELF contents.

| Input or action | Before | After |
| --- | --- | --- |
| Package the three actual WPA debug ELF files | Each regular member has mode `0755` | Each has mode `0644`, matching Debian debug-symbol file permissions |
| Package directories and symbolic links | Directory mode `0755`; existing link metadata | Unchanged |
| Repackage the same debug payload twice | Existing payload, ownership and fixed timestamps | Identical payload hashes and byte-identical corrected archives |

Native AMD64 presubmit retains all 37 build targets and 41 tests from #175,
and adds the archive metadata boundary test and actual ELF debug-TAR timestamp
and permission test: 37 build targets, 43 tests. The retained tools-only kernel
checks do not generate Debian packages. Registry validation does not establish
full WPA/MACsec image acceptance; consumers must select this candidate and
validate their own artifacts.

Keep this registration Draft while #175 and #76 remain unlanded. The normal
consumer endpoint remains maintained main; temporary Draft validation uses one
complete immutable catalog plus BCR. This source hash suffix sorts below the
previous `.26-270b1cb...` and `.26-75c6327...` suffixes, so update required direct
and transitive requests together and verify the actual resolved graph. Merely
adding the new root version does not guarantee that Bazel selects it.
