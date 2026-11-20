## Dependency refresh for `24.9.0.sonic.2`

This candidate retains the `24.9.0.sonic.1` source and existing patches. Its module dependencies select the newest non-yanked versions published at `3d1cc5e8dfd553d2acbe4198e504a245e6bdbddf`. Versions introduced by this refresh are not dependency targets of the same refresh.

PcapPlusPlus upstream 24.09 is represented as 24.9.0.sonic.1 for the registry three-component version convention. The source hash and DHCP-port patch match sonic-dhcp-relay/dhcp4relay Make inputs. Native Common++, Packet++, Pcap++ retain the default Linux/libpcap backend; DPDK/PF_RING/XDP and LightPcapNg zstd remain disabled as in the original unconfigured build.
