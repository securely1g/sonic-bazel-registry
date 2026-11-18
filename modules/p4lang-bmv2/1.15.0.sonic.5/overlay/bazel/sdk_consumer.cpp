#include <bm/bm_sim/bytecontainer.h>
#include <bm/PI/pi.h>
#include <PI/pi.h>
#include <dlfcn.h>
#include <iostream>
#include <string>

int main() {
    const bm::ByteContainer bytes("0a0b0102");
    if (bytes.size() != 4 || bytes.to_hex() != "0a0b0102") return 1;
    bm::pi::register_switch(nullptr);
    Dl_info target{};
    void *init = dlsym(RTLD_DEFAULT, "_pi_init");
    if (!init || !dladdr(init, &target) || !target.dli_fname ||
        std::string(target.dli_fname).find("libbmpi.so") == std::string::npos) {
        std::cerr << "PI target must resolve to the BMv2 backend\n";
        return 2;
    }
    if (pi_init(0, nullptr) != PI_STATUS_SUCCESS) return 3;
    if (pi_destroy() != PI_STATUS_SUCCESS) return 4;
    std::cout << "BMv2 installed SDK consumer passed\n";
}
