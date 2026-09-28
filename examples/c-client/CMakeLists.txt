cmake_minimum_required(VERSION 3.16)
project(ftms_c_client_example LANGUAGES C)

find_package(ftms CONFIG REQUIRED)

add_executable(ftms_c_client main.c)
target_compile_features(ftms_c_client PRIVATE c_std_99)
target_link_libraries(ftms_c_client PRIVATE ftms::ftms)

enable_testing()
add_test(NAME ftms_c_client COMMAND ftms_c_client)
