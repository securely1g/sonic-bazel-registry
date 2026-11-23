"""Source root identity from the declared prepared-source repository."""
CPYTHON_SOURCE_ROOT = Label("@cpython_src//:configure.ac").workspace_root
