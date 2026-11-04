# gNMI registration comparison

Published registry baseline: `51de33d8d4eb949ed7e5a02578deee2eeab34e76`. Candidate: `288afeee754c3d096299eaa1f9c24a330187b413`. Module: `sonic-gnmi@0.1.0-ce49e93eb3a0cff8daf77a3092535d76265ebc3d`. This is the first published gNMI registration; there is no predecessor version to copy.

The patch includes all cumulative registry changes from maintained main, including required infrastructure #218, Common #199, ygot #214 and Management #219 entries. It includes every new or changed tracked file and Git mode. Published entries remain intact.

Apply in a fresh checkout of the exact published baseline. Candidate version directories must not already exist. Keep the patch outside the checkout:

```sh
git checkout --detach 51de33d8d4eb949ed7e5a02578deee2eeab34e76
git apply --check /path/to/complete-registry-comparison.patch
git apply --index /path/to/complete-registry-comparison.patch
git write-tree
```

Expected complete tree: `bbd780da5b9ae50bf28cf21b72764323e40c5f7a`. Patch SHA-256: `89415638e64fa74ea5e4199dbef750675dd2a96917ea0c46db6f93a4651fc7bd`. Verification applied this actual patch in an isolated RAM baseline checkout and obtained that exact tree, including all file modes. Existing whitespace in inherited patches is preserved. Source MODULE patches, source archive integrity and original six-build/three-test presubmit coverage were checked separately. Current native CI remains pending; patch application is not build or runtime acceptance.
