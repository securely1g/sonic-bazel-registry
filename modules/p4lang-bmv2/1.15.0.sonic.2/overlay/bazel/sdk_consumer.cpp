#include <bm/bm_sim/bytecontainer.h>
#include <iostream>

int main() {
    const bm::ByteContainer bytes("0a0b0102");
    if (bytes.size() != 4 || bytes.to_hex() != "0a0b0102") return 1;
    std::cout << "BMv2 installed SDK consumer passed\n";
}
