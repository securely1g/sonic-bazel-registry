# Complete common registry comparison

Published registry baseline: `ccf06568a0b85b18780becdad95e26d87f89d04e`.
Candidate: `03f870c62fa2bab567133c6a9303f71392e4986e`. Previous published module: `sonic-swss-common@0.0.8-a0450924`.

The patch retains the previous published entry and includes all cumulative registry changes needed to reproduce the candidate tree, including inherited prerequisite entries.

SHA-256: `d55810b1e49b53932d81e3f661388a5b5a5c54bd06a7297c31b730e2de101909`.

Apply in a clean registry checkout at the baseline:

```sh
git checkout --detach ccf06568a0b85b18780becdad95e26d87f89d04e
git apply --index --binary complete-registry-comparison.patch
git diff --cached --exit-code 03f870c62fa2bab567133c6a9303f71392e4986e --
```

Application was verified with a separate Git index; every resulting tracked file and Git mode matches the candidate. This artifact records inputs and comparison completeness; it does not establish native build or test success.
