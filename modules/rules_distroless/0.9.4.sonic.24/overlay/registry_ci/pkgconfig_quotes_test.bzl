"""Quoted .pc variables and flag arguments, verified against native pkgconf."""

load("@bazel_skylib//lib:unittest.bzl", "asserts", "unittest")
load("//apt/private:pkgconfig.bzl", "parse_pc", "process_pcconfig")

def _pkgconfig_quotes_test_impl(ctx):
    env = unittest.begin(ctx)
    for triplet in ["x86_64-linux-gnu", "aarch64-linux-gnu"]:
        # Debian libpcap 1.10.5-2 quotes its variables, then expands them inside
        # more quotes. Neither include paths nor link paths may retain quotes.
        pc = '''prefix="/usr"
exec_prefix="${prefix}"
includedir="${prefix}/include"
libdir="${prefix}/lib/{triplet}"
Name: libpcap
Description: Platform-independent network traffic capture library
Version: 1.10.5
Libs: -L${libdir}  -lpcap
Cflags: -I${includedir}
'''.replace("{triplet}", triplet)
        result = process_pcconfig(parse_pc(pc))
        libdir = "/usr/lib/" + triplet
        asserts.equals(env, ["libpcap"], result[0])
        asserts.equals(env, "/usr/include", result[1])
        asserts.equals(env, libdir, result[2])
        asserts.equals(env, ["-Wl,-rpath=" + libdir], result[3])
        asserts.equals(env, [libdir], result[4])
        asserts.equals(env, ["/usr/include"], depset(result[5]).to_list())

    for prefix in ["/opt/sdk with spaces", "/opt/sdk\\ with\\ spaces"]:
        # An unquoted variable can contain spaces when its field use is quoted.
        pc = '''prefix={prefix_value}
includedir=${prefix}/include
libdir=${prefix}/lib
Name: example
Libs: -L"${libdir}" -l"example" -Wl,"-z,now" '' ""
Cflags: -I"${includedir}" -DNAME="hello world" -DQUOTE='literal "quote"'
'''.replace("{prefix_value}", prefix)

        # A backslash inside double quotes is literal unless it escapes a
        # quote, backslash, dollar, backtick or newline. An escaped-space
        # variable therefore needs an unquoted field use instead.
        if "\\ " in prefix:
            pc = pc.replace('-L"${libdir}"', "-L${libdir}").replace('-I"${includedir}"', "-I${includedir}")
        result = process_pcconfig(parse_pc(pc))
        asserts.equals(env, ["libexample"], result[0])
        asserts.equals(env, "/opt/sdk with spaces/include", result[1])
        asserts.equals(env, "/opt/sdk with spaces/lib", result[2])
        asserts.equals(env, ["-Wl,-rpath=/opt/sdk with spaces/lib", "-Wl,-z,now"], result[3])
        asserts.equals(env, ["/opt/sdk with spaces/include"], depset(result[5]).to_list())
        asserts.equals(env, ["NAME=hello world", 'QUOTE=literal "quote"'], result[6])

    result = process_pcconfig(({
        "Name": "escaped",
        "Cflags": r'''-I/escaped\ path -DNAME=two\ words -DWIN='C:\sdk' -DUNKNOWN="a\q"''',
        "Libs": r"""-L/escaped\ lib -lfoo -Wl,-rpath,/escaped\ lib""",
    }, {}))
    asserts.equals(env, ["/escaped path"], depset(result[5]).to_list())
    asserts.equals(env, ["NAME=two words", r"WIN=C:\sdk", r"UNKNOWN=a\q"], result[6])
    asserts.equals(env, ["-Wl,-rpath=/escaped lib", "-Wl,-rpath,/escaped lib"], result[3])
    return unittest.end(env)

pkgconfig_quotes_test = unittest.make(_pkgconfig_quotes_test_impl)
