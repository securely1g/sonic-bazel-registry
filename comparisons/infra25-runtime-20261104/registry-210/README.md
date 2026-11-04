# Complete registry #210 version comparison

Published baseline: 51de33d8d4eb949ed7e5a02578deee2eeab34e76. Candidate: b6f9a1f85057a45a1533a35d8dc043149eb4e9cd.

The raw patch includes all version-entry changes, inherited prerequisites, metadata, tests and supporting CI files. Its header gives exact application instructions. Applying it after the documented copies reproduces the complete candidate tree and Git file modes while retaining every published entry.

[Download the complete applicable patch](../registry-210.patch). SHA-256: 19228baf3a717ba13f15d7b976f5dde661f5ccfc7601a88e169c3a4498552058.

The full colored comparison is split into the consecutive parts below so GitHub can display every line. Parts are for review; apply the complete raw patch. Concatenating the unmodified part bytes exactly reproduces the raw patch.

| Part | Bytes |
| --- | ---: |
| [View colored part 1](part-01.patch) | 179981 |
| [View colored part 2](part-02.patch) | 86517 |

## Compared entries

| Module | Published version | Candidate version |
| --- | --- | --- |
| sonic-build-infra | 0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568 | 0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e |
| sonic-fips | 0.0.4-ef423363e8fd50358f0aa2a8a20d3e08d4450a56 | 0.0.5-15fcb926a302059ec379f0c2fd15eb3d88bda4c9 |
| sonic-swss-common | 0.0.8-a0450924719a9f706125cc44a07dc88934935003 | 0.0.8-43598143ef4a46431eae0859915cd7d951dad1ed |
| sonic-wpa-supplicant | No published predecessor | 2.9.0.sonic.1 |
