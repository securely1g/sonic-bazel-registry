# Complete registry #182 version comparison

Published baseline: 51de33d8d4eb949ed7e5a02578deee2eeab34e76. Candidate: 2b87d3d58022e878951a343c61089d4ae1e31a6a.

The raw patch includes all version-entry changes, inherited prerequisites, metadata, tests and supporting CI files. Its header gives exact application instructions. Applying it after the documented copies reproduces the complete candidate tree and Git file modes while retaining every published entry.

[Download the complete applicable patch](../registry-182.patch). SHA-256: 04e415cccd5cda1148db6169e8cc3020ded12c381ec451a5793a378c1a544189.

The full colored comparison is split into the consecutive parts below so GitHub can display every line. Parts are for review; apply the complete raw patch. Concatenating the unmodified part bytes exactly reproduces the raw patch.

| Part | Bytes |
| --- | ---: |
| [View colored part 1](part-01.patch) | 180000 |
| [View colored part 2](part-02.patch) | 179977 |
| [View colored part 3](part-03.patch) | 179934 |
| [View colored part 4](part-04.patch) | 179971 |
| [View colored part 5](part-05.patch) | 157083 |

## Compared entries

| Module | Published version | Candidate version |
| --- | --- | --- |
| sonic-build-infra | 0.0.26-51c838da6ff57295fde6e0bc3807841cb31a8568 | 0.0.25-3ee15ec9b4d99d7f8eae3e324cead79b203b451e |
| sonic-mgmt-common | 1.0.0-f5361ba8b88cde7ec59bdb4652a986c68d66da64 | 1.0.0-71eb5f710b5347ca0510ee8e3f5294a7c64bb744 |
| sonic-swss-common | 0.0.8-a0450924719a9f706125cc44a07dc88934935003 | 0.0.8-43598143ef4a46431eae0859915cd7d951dad1ed |
| openconfig_ygot | No published predecessor | 0.7.1.sonic.1 |
| sonic-gnmi | No published predecessor | 0.1.0-ce49e93eb3a0cff8daf77a3092535d76265ebc3d |
