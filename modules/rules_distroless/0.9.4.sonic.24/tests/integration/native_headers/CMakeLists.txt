cmake_minimum_required(VERSION 3.20)
project(native_header_namespaces LANGUAGES C)
add_library(header_probe STATIC probe.c)
# Exercise the actual foreign_cc SDK staging path used by configure projects.
target_include_directories(header_probe PRIVATE "${DECLARED_SDK}/include")
target_compile_definitions(header_probe PRIVATE "HEADER_CASE=${HEADER_CASE}")
install(TARGETS header_probe ARCHIVE DESTINATION lib)
