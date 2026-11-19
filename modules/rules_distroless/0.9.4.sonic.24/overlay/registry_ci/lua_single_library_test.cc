extern "C" {
#include <lua5.1/lua.h>
#include <lua5.1/lauxlib.h>
}

int main() {
    lua_State *state = luaL_newstate();
    if (!state) return 1;
    int status = luaL_loadstring(state, "return 6 * 7");
    if (status == 0) status = lua_pcall(state, 0, 1, 0);
    const bool correct = status == 0 && lua_tointeger(state, -1) == 42;
    lua_close(state);
    return correct ? 0 : 1;
}
