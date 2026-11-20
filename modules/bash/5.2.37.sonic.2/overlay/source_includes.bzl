"""Preserve the original private quoted builtins headers before libc headers."""
def private_builtins_include():
    repository = native.repository_name().lstrip("@")
    return "-iquote" + ("external/" + repository + "/" if repository else "") + "builtins"

def reproducibility_copts():
    """Map the actual source/packaging repositories to Debian debug paths."""
    directories = [
        "external/" + native.repository_name().lstrip("@"),
        "external/" + Label("@bash_debian//:debian/control").workspace_name,
    ]
    return ["-ffile-prefix-map=" + directory + "=." for directory in directories] + [
        "-fdebug-prefix-map=" + directory + "=/usr/src/bash-5.2.37-2"
        for directory in directories
    ]
