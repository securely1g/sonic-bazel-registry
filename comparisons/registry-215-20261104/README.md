# Complete registry PR #215 comparison

Complete cumulative delta including prerequisite entries.

- Maintained main: 51de33d8d4eb949ed7e5a02578deee2eeab34e76
- Review base: 4bdf38541f509097df157aae39fde5bc7b29c6f6
- Candidate head: 28ea8a8b17f6ecf85a32aadf8ef5eb4f65ca9623
- Candidate tree: ecf7524bdf05c848d3fe4da837635d78e97dfafd
- Patch SHA256: 397e5e748e3cd17b48fa7ae22eee5a2eac1fc2cda87ddacb4d23025ee2deab20
- Patch size: 275062 bytes

In a clean throwaway checkout at maintained main, run: git apply --index --binary complete-registry-comparison.patch. The resulting git write-tree must equal the candidate tree above. This reproduces files and modes without compiling.

All 1758 published version files/modes and metadata are preserved. The event planner selects only this module on AMD64 and ARM64. Configured/native acceptance remains pending. No DEB generation, merge or broad all/latest execution is authorized by this artifact.
