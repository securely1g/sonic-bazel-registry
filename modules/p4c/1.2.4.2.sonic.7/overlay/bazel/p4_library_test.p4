#include <core.p4>
#include <v1model.p4>
#include "p4_library_test_defs.h"

header ethernet_t {
    bit<48> dstAddr;
    bit<48> srcAddr;
    bit<16> etherType;
}

struct headers_t {
    ethernet_t ethernet;
}

struct metadata_t {
}

parser MyParser(packet_in packet,
                out headers_t hdr,
                inout metadata_t meta,
                inout standard_metadata_t standard_metadata) {
    state start {
        packet.extract(hdr.ethernet);
        transition accept;
    }
}

control MyVerifyChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply {}
}

control MyIngress(inout headers_t hdr,
                  inout metadata_t meta,
                  inout standard_metadata_t standard_metadata) {
    action forward(bit<TEST_PORT_WIDTH> port) {
        standard_metadata.egress_spec = port;
    }
#ifdef TEST_EXTRA_TABLE
    table forward_table {
        key = {
            hdr.ethernet.dstAddr: exact;
        }
        actions = {
            forward;
            NoAction;
        }
        size = 64;
        default_action = NoAction();
    }
#endif
    apply {
#ifdef TEST_EXTRA_TABLE
        forward_table.apply();
#endif
    }
}

control MyEgress(inout headers_t hdr,
                 inout metadata_t meta,
                 inout standard_metadata_t standard_metadata) {
    apply {}
}

control MyComputeChecksum(inout headers_t hdr, inout metadata_t meta) {
    apply {}
}

control MyDeparser(packet_out packet, in headers_t hdr) {
    apply {
        packet.emit(hdr.ethernet);
    }
}

V1Switch(
    MyParser(),
    MyVerifyChecksum(),
    MyIngress(),
    MyEgress(),
    MyComputeChecksum(),
    MyDeparser()
) main;
