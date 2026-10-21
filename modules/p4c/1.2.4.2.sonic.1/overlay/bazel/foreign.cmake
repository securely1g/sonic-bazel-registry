# All FetchContent inputs are already part of the verified OBS source archive.
# Refer to their sources explicitly so a clean out-of-tree build never downloads
# or reuses the original package's generated build files.
set(FETCHCONTENT_FULLY_DISCONNECTED ON CACHE BOOL "" FORCE)
foreach(dependency protobuf p4runtime inja z3)
  string(TOUPPER "${dependency}" upper)
  set(FETCHCONTENT_SOURCE_DIR_${upper} "${CMAKE_CURRENT_SOURCE_DIR}/build/_deps/${dependency}-src" CACHE PATH "" FORCE)
endforeach()
set(CMAKE_EXPORT_COMPILE_COMMANDS ON CACHE BOOL "" FORCE)
set(CCACHE_PROGRAM "CCACHE_PROGRAM-NOTFOUND" CACHE FILEPATH "" FORCE)
