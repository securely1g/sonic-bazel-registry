# All FetchContent inputs are already part of the verified OBS source archive.
# Refer to their sources explicitly so a clean out-of-tree build never downloads
# or reuses the original package's generated build files.
set(FETCHCONTENT_FULLY_DISCONNECTED ON CACHE BOOL "" FORCE)
foreach(dependency protobuf p4runtime inja z3)
  string(TOUPPER "${dependency}" upper)
  set(FETCHCONTENT_SOURCE_DIR_${upper} "${CMAKE_CURRENT_SOURCE_DIR}/build/_deps/${dependency}-src" CACHE PATH "" FORCE)
endforeach()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON CACHE BOOL "" FORCE)
set(CCACHE_PROGRAM "OFF" CACHE FILEPATH "" FORCE)
# Inja ships its JSON header in the declared source tree. Do not let host CMake
# metadata replace that target with an undeclared /usr/include dependency.
set(CMAKE_DISABLE_FIND_PACKAGE_nlohmann_json ON CACHE BOOL "" FORCE)
# Compile installed default paths for the SONiC filesystem. The foreign rule's
# install command separately stages files with --prefix $INSTALLDIR/usr.
set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "" FORCE)
