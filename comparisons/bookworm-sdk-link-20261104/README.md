# Complete registry candidate comparisons

These patches apply to the complete published registry tree at `8917da90e1490cec813036b3c964fc0a04b4664b`.
They include all inherited CI/prerequisite and entry changes, including file modes.

```sh
git checkout --detach 8917da90e1490cec813036b3c964fc0a04b4664b
git apply --index registry-226-with-transport-and-sdk-link.patch
git write-tree
```

Use the matching 211 patch instead when reviewing BMv2. Each complete patch applies independently to the same baseline. These are comparison artifacts, not a source or validation catalog. Corrected native acceptance is pending.

- #226: candidate `5bca2800d0ebb782ead3a868709001e699eea93c`, SHA256 `fe1f4c5e75da4bbc0e518570b33f333e15214c2e4464c086af855f0d68ed0a6d`.
- #211: candidate `f37f811d50a87e94c1dd0334bced73864b0a19a1`, SHA256 `a0470c0d61db028340e2f8f9cec6d914e4034ba425bd06fa8a8d7463cc53b6f6`.
