"""Preserve the source owner's private quoted-header search paths."""

def private_includes(directories):
    repository = native.repository_name().lstrip("@")
    prefix = "external/" + repository + "/" if repository else ""
    return ["-iquote" + prefix + directory for directory in directories]
