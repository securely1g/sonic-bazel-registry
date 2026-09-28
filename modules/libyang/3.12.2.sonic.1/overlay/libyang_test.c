#include <libyang/libyang.h>
#include <libyang/version.h>
#include <string.h>

int main(void) {
    struct ly_ctx *ctx = NULL;
    struct lys_module *module = NULL;
    struct lyd_node *data = NULL;
    if (strcmp(ly_version_proj_str(), "3.12.2") || ly_ctx_new(NULL, 0, &ctx)) return 1;
    const char *schema = "module smoke {namespace urn:smoke; prefix s; leaf value {type string {pattern '[a-z]+';}}}";
    int rc = lys_parse_mem(ctx, schema, LYS_IN_YANG, &module);
    if (!rc) rc = lyd_parse_data_mem(ctx, "{\"smoke:value\":\"hello\"}", LYD_JSON, 0, LYD_VALIDATE_PRESENT | LYD_VALIDATE_NOEXTDEPS, &data);
    lyd_free_all(data);
    ly_ctx_destroy(ctx);
    return rc;
}
