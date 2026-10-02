#include "probe.pb.h"

#include <dlfcn.h>
#include <limits.h>
#include <stdlib.h>

#include <iostream>
#include <string>

#include <google/protobuf/stubs/common.h>
#include <google/protobuf/util/json_util.h>

static_assert(GOOGLE_PROTOBUF_VERSION == 3021012, "Expected protobuf 3.21.12 headers");

int main() {
    GOOGLE_PROTOBUF_VERIFY_VERSION;
    protobuf_legacy_test::Probe input;
    input.set_value(42);
    input.mutable_timestamp()->set_seconds(1700000000);
    std::string serialized;
    if (!input.SerializeToString(&serialized)) return 1;
    protobuf_legacy_test::Probe parsed;
    if (!parsed.ParseFromString(serialized) || !parsed.has_value() || parsed.value() != 42 ||
        parsed.timestamp().seconds() != 1700000000) return 2;
    std::string json;
    if (!google::protobuf::util::MessageToJsonString(parsed, &json).ok()) return 3;
    protobuf_legacy_test::Probe json_parsed;
    if (!google::protobuf::util::JsonStringToMessage(json, &json_parsed).ok() ||
        !json_parsed.has_value() || json_parsed.value() != 42) return 4;
    Dl_info information{};
    if (!dladdr(reinterpret_cast<void*>(&google::protobuf::ShutdownProtobufLibrary), &information)) return 5;
    char path[PATH_MAX];
    if (!realpath(information.dli_fname, path)) return 6;
    std::cout << "PROTOBUF_LIBRARY=" << path << '\n';
    return 0;
}
