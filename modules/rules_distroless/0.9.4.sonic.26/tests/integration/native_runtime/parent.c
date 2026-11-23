int apt_runtime_leaf(void);
int apt_runtime_other(void);
int apt_runtime_parent(void) { return apt_runtime_leaf() + apt_runtime_other(); }
