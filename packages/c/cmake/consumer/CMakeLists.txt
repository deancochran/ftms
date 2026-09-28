cmake_minimum_required(VERSION 3.16)
project(ftms_add_subdirectory_consumer LANGUAGES C)

add_subdirectory("${CMAKE_CURRENT_LIST_DIR}/../.." ftms-build EXCLUDE_FROM_ALL)
add_executable(ftms_add_subdirectory_consumer planner.c)
target_link_libraries(ftms_add_subdirectory_consumer PRIVATE ftms::ftms)
