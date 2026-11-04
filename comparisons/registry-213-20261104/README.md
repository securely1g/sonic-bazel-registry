# Complete registry PR #213 comparison

Complete cumulative delta including prerequisite entries.

- Maintained main: 51de33d8d4eb949ed7e5a02578deee2eeab34e76
- Review base: 29c5c4ea7f1bed176edc7dd8c7e18ccd4c330691
- Candidate head: dd35a932bfebdcb8f9c31c1127ed7496cf334df2
- Candidate tree: e66982b027734d48b3cc045c871fb55b57e0d47c
- Patch SHA256: cddbdb3b3b0f633be7b4d11fb3a27e70422fe28e0a7040044f0480432127c617
- Patch size: 295572 bytes

In a clean throwaway checkout at maintained main, run: git apply --index --binary complete-registry-comparison.patch. The resulting git write-tree must equal the candidate tree above. This reproduces files and modes without compiling.

All 1758 published version files/modes and metadata are preserved. The event planner selects only this module on AMD64 and ARM64. Configured/native acceptance remains pending. No DEB generation, merge or broad all/latest execution is authorized by this artifact.
