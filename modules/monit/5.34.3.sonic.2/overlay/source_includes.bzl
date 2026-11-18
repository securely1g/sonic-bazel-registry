"""Preserve source-private Make -I ordering without propagating it to monit."""

def private_includes(directories):
    repository = native.repository_name().lstrip("@")
    prefix = "external/" + repository + "/" if repository else ""
    return ["-I" + prefix + directory for directory in directories]
