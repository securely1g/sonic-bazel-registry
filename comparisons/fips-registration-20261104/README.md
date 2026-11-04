# Complete fips registry comparison

Published registry baseline: `ccf06568a0b85b18780becdad95e26d87f89d04e`.
Candidate: `8374b07ca138b98546122186d832544f1b46ac07`. Previous published module: `sonic-fips@0.0.4-ef423363e8fd50358f0aa2a8a20d3e08d4450a56`.

The patch retains the previous published entry and includes all cumulative registry changes needed to reproduce the candidate tree, including inherited prerequisite entries.

SHA-256: `8c4d017cd8675cd9b7bf9c2576ffb3f121a5af82a5a2537ecc0ce89ea50a9fba`.

Apply in a clean registry checkout at the baseline:

```sh
git checkout --detach ccf06568a0b85b18780becdad95e26d87f89d04e
git apply --index --binary complete-registry-comparison.patch
git diff --cached --exit-code 8374b07ca138b98546122186d832544f1b46ac07 --
```

Application was verified with a separate Git index; every resulting tracked file and Git mode matches the candidate. This artifact records inputs and comparison completeness; it does not establish native build or test success.
