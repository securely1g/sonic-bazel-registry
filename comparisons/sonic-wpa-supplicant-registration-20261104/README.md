# sonic-wpa-supplicant complete registration comparison

Published baseline: `51de33d8d4eb949ed7e5a02578deee2eeab34e76`. Candidate: `74d85408232a0044b2913e707c69dd4901fdaf4b`. This is an initial registration with no published predecessor. The complete patch includes the module entry, metadata and all inherited review dependencies. Published files and Git modes remain unchanged.

Use a fresh checkout of the exact baseline, where the candidate version directories do not yet exist. Keep the patch outside that checkout:

```sh
git checkout --detach 51de33d8d4eb949ed7e5a02578deee2eeab34e76
git apply --check /path/to/complete-registry-comparison.patch
git apply --index /path/to/complete-registry-comparison.patch
git write-tree
```

Expected entire tree: `0b972053f0f7fef80fa725424fee411bca96452d`. Patch SHA-256: `e72e7ad4e741ffb50398ac372df4e7f9522c2aeb7e2c071c2799c3358812a2d2`. This exact patch was applied in an isolated baseline checkout and reproduced the whole candidate tree, including file modes. Existing whitespace in inherited source patches is preserved. Source archive identity, source MODULE patch equality and all existing presubmit targets were checked separately. Current configured-action/native/runtime acceptance remains pending.
