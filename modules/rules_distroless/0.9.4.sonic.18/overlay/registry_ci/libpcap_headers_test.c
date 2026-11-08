#include <pcap/pcap.h>

int main(void) {
    struct pcap_pkthdr packet = {0};
    return packet.caplen != 0;
}
