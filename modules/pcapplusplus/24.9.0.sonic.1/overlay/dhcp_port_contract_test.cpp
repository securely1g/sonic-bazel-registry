#include <cassert>
#include "DhcpLayer.h"
int main() {
    // SONiC accepts clients using ephemeral source ports (Make patch #0001).
    assert(pcpp::DhcpLayer::isDhcpPorts(12345, 67));
    assert(pcpp::DhcpLayer::isDhcpPorts(12345, 68));
    assert(!pcpp::DhcpLayer::isDhcpPorts(67, 9999));
    return 0;
}
