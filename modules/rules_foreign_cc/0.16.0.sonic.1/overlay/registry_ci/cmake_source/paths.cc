#include <sdk_warning.h>
#include <system_warning.h>
#include <ordinary.h>
int value() { return sdk_function(0) + vendor_function(0) + ORDINARY_HEADER_FOUND; }
