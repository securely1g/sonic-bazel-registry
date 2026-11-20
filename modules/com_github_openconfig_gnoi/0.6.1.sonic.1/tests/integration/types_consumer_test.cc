#include <iostream>
#include <string>

#include "github.com/openconfig/gnoi/types/types.pb.h"

int main() {
    gnoi::types::Path path;
    path.set_origin("openconfig");
    auto* element = path.add_elem();
    element->set_name("interface");
    (*element->mutable_key())["name"] = "Ethernet0";

    std::string wire;
    if (!path.SerializeToString(&wire)) {
        std::cerr << "Could not serialize the public gNOI Path message\n";
        return 1;
    }
    gnoi::types::Path restored;
    if (!restored.ParseFromString(wire) || restored.origin() != "openconfig" ||
        restored.elem_size() != 1 || restored.elem(0).name() != "interface" ||
        restored.elem(0).key().size() != 1 ||
        restored.elem(0).key().find("name") == restored.elem(0).key().end() ||
        restored.elem(0).key().at("name") != "Ethernet0") {
        std::cerr << "The gNOI Path round trip lost its origin or interface key\n";
        return 1;
    }
    return 0;
}
