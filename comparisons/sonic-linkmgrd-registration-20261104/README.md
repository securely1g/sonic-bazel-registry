# sonic-linkmgrd complete registration comparison

Published baseline: `51de33d8d4eb949ed7e5a02578deee2eeab34e76`. Candidate: `b6b0b1bfcd784c7b2fa4bc7ada101c276d0258aa`. This is an initial registration with no published predecessor. The complete patch includes the module entry, metadata and all inherited review dependencies. Published files and Git modes remain unchanged.

Use a fresh checkout of the exact baseline, where the candidate version directories do not yet exist. Keep the patch outside that checkout:

```sh
git checkout --detach 51de33d8d4eb949ed7e5a02578deee2eeab34e76
git apply --check /path/to/complete-registry-comparison.patch
git apply --index /path/to/complete-registry-comparison.patch
git write-tree
```

Expected entire tree: `12b0c904f70324bbd44dc11f569bdc07ae05334f`. Patch SHA-256: `ba111ff69e4b7761a8fe4f8ce6546deef29e4b93bf21bfe37d1c2a5283271051`. This exact patch was applied in an isolated baseline checkout and reproduced the whole candidate tree, including file modes. Existing whitespace in inherited source patches is preserved. Source archive identity, source MODULE patch equality and all existing presubmit targets were checked separately. Current configured-action/native/runtime acceptance remains pending.
