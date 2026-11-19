"""Private quoted headers precede glibc system headers in generated parsers."""

def private_include():
    repository = native.repository_name().lstrip("@")
    return "-iquote" + ("external/" + repository + "/" if repository else "") + "lib"
