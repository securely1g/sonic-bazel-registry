"""Regression for pkg-config field separators used by Debian xtables."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//apt/private:pkgconfig.bzl", "parse_pc", "process_pcconfig")

def _pkgconfig_fields_test_impl(ctx):
    env = unittest.begin(ctx)
    for whitespace in ["", " ", "\t", "\t  "]:
        pc = """prefix = /usr
libdir=${prefix}/lib
includedir=${prefix}/include
  # Indented comments do not define variables.
url = https://example.invalid/?feature=1
search_path = /first:/second
caption = mode: value=1
Name:{space}xtables
Description:{space}fields: retain = inside values
URL:{space}${url}
Libs:{space}-L${libdir} -lxtables
Libs.private:{space}
Cflags:{space}-I${includedir} -DFEATURE=1
""".replace("{space}", whitespace)
        directives, variables = parse_pc(pc)
        asserts.equals(env, "xtables", directives["Name"])
        asserts.equals(env, "fields: retain = inside values", directives["Description"])
        asserts.equals(env, "https://example.invalid/?feature=1", directives["URL"])
        asserts.equals(env, "https://example.invalid/?feature=1", variables["url"])
        asserts.equals(env, "/first:/second", variables["search_path"])
        asserts.equals(env, "mode: value=1", variables["caption"])
        asserts.false(env, "URL" in variables)
        asserts.false(env, "url = https" in directives)
        result = process_pcconfig((directives, variables))
        asserts.equals(env, ["libxtables"], result[0])
        asserts.equals(env, ["/usr/lib"], result[4])
        asserts.equals(env, ["/usr/include"], depset(result[5]).to_list())
        asserts.equals(env, ["FEATURE=1"], result[6])
    return unittest.end(env)

pkgconfig_fields_test = unittest.make(_pkgconfig_fields_test_impl)
