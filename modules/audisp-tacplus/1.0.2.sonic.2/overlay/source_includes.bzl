def private_includes():
    repository = native.repository_name().lstrip("@")
    return ["-iquote" + ("external/" + repository + "/" if repository else "") + "."]
