#include <PI/pi.h>
#include <PI/p4info.h>
#include <PI/proto/pi_server.h>
#include <p4/config/v1/p4info.pb.h>
int main() {
    p4::config::v1::P4Info info;
    info.mutable_pkg_info()->set_name("source-sdk");
    pi_p4info_t *config = nullptr;
    if (pi_empty_config(&config) != PI_STATUS_SUCCESS || config == nullptr) return 1;
    return pi_destroy_config(config) == PI_STATUS_SUCCESS &&
           info.pkg_info().name() == "source-sdk" ? 0 : 1;
}
