#define _GNU_SOURCE
#include <dlfcn.h>
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct observed_libraries {
    int main_program;
    int middle;
    int leaf;
    int bad_tags;
};

// glibc may already have relocated DT_STRTAB. Accept only an address within
// this object's loaded segments, with or without its load bias.
static const char *string_table(struct dl_phdr_info *info, ElfW(Addr) value) {
    for (int relocated = 1; relocated >= 0; --relocated) {
        uintptr_t address = value + (relocated ? 0 : info->dlpi_addr);
        for (size_t i = 0; i < info->dlpi_phnum; ++i) {
            const ElfW(Phdr) *header = &info->dlpi_phdr[i];
            uintptr_t begin = info->dlpi_addr + header->p_vaddr;
            if (header->p_type == PT_LOAD && address >= begin &&
                address < begin + header->p_memsz) {
                return (const char *)address;
            }
        }
    }
    return NULL;
}

static int inspect_library(struct dl_phdr_info *info, size_t size, void *data) {
    (void)size;
    struct observed_libraries *observed = data;
    const char *name = strrchr(info->dlpi_name, '/');
    name = name ? name + 1 : info->dlpi_name;
    int main_program = !*name;
    int middle = !strcmp(name, "libdistroless_provider_middle.so");
    if (!strcmp(name, "libdistroless_provider_leaf.so.1")) {
        observed->leaf++;
    }
    if (!main_program && !middle) {
        return 0;
    }

    int runpath = 0;
    int rpath = 0;
    const ElfW(Dyn) *dynamic = NULL;
    const char *strings = NULL;
    for (size_t i = 0; i < info->dlpi_phnum; ++i) {
        if (info->dlpi_phdr[i].p_type != PT_DYNAMIC) {
            continue;
        }
        const ElfW(Dyn) *entry = (const ElfW(Dyn) *)(
            info->dlpi_addr + info->dlpi_phdr[i].p_vaddr);
        dynamic = entry;
        for (; entry->d_tag != DT_NULL; ++entry) {
            if (entry->d_tag == DT_STRTAB) {
                strings = string_table(info, entry->d_un.d_ptr);
            }
            runpath |= entry->d_tag == DT_RUNPATH;
            rpath |= entry->d_tag == DT_RPATH;
        }
    }
    if (!runpath || rpath) {
        fprintf(stderr, "%s must have RUNPATH and no RPATH\n",
                main_program ? "test executable" : name);
        observed->bad_tags++;
    }
    int needed_leaf = 0;
    int needed_middle = 0;
    if (strings && dynamic) {
        for (const ElfW(Dyn) *entry = dynamic; entry->d_tag != DT_NULL; ++entry) {
            if (entry->d_tag == DT_NEEDED) {
                const char *needed = strings + entry->d_un.d_val;
                needed_leaf += !strcmp(needed, "libdistroless_provider_leaf.so.1");
                needed_middle += !strcmp(needed, "libdistroless_provider_middle.so");
            }
        }
    }
    if (!strings || (main_program && (needed_middle || needed_leaf)) ||
        (middle && needed_leaf != 1)) {
        fputs("Only the middle library may directly need the imported leaf\n", stderr);
        observed->bad_tags++;
    }
    observed->main_program += main_program;
    observed->middle += middle;
    return 0;
}

int main(int argc, char **argv) {
    const char *library_path = getenv("LD_LIBRARY_PATH");
    const char *preload = getenv("LD_PRELOAD");
    if ((library_path && *library_path) || (preload && *preload)) {
        fputs("The regression requires no loader environment overrides\n", stderr);
        return 1;
    }
    if (argc != 2) {
        fputs("Expected the declared native shared library path\n", stderr);
        return 1;
    }
    void *library = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!library) {
        fprintf(stderr, "Cannot load the native shared library: %s\n", dlerror());
        return 1;
    }
    int (*middle_value)(void) = (int (*)(void))dlsym(library, "distroless_middle_value");
    if (!middle_value) {
        fprintf(stderr, "Cannot find the middle library entry point: %s\n", dlerror());
        return 1;
    }
    struct observed_libraries observed = {0};
    dl_iterate_phdr(inspect_library, &observed);
    if (observed.main_program != 1 || observed.middle != 1 ||
        observed.leaf != 1 || observed.bad_tags) {
        fputs("Expected the executable and both shared libraries\n", stderr);
        return 1;
    }
    return middle_value() == 42 ? 0 : 1;
}
