#include <PI/pi.h>
#include <PI/p4info.h>
#include <PI/proto/pi_server.h>
#include <p4/config/v1/p4info.pb.h>
int main() {
    p4::config::v1::P4Info info;
    info.mutable_pkg_info()->set_name("source-sdk");
    return info.pkg_info().name() == "source-sdk" ? 0 : 1;
}
