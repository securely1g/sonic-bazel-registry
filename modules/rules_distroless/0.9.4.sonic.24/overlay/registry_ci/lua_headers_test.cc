#include <cstring>
extern "C" {
#include <lua5.1/lua.h>
#include <lua5.1/lauxlib.h>
}

static_assert(LUA_VERSION_NUM == 501, "Expected the pinned Lua 5.1 API");
static_assert(sizeof(lua_Number) == sizeof(double), "Expected the Debian Lua number ABI");

int main() {
#if defined(__aarch64__)
    return std::strcmp(DEB_HOST_MULTIARCH, "aarch64-linux-gnu");
#elif defined(__x86_64__)
    return std::strcmp(DEB_HOST_MULTIARCH, "x86_64-linux-gnu");
#else
#error "This regression requires native AMD64 or ARM64"
#endif
}
