cmake_minimum_required(VERSION 3.16)
project(ftms_c_client_example LANGUAGES C CXX)

find_package(ftms CONFIG REQUIRED)

add_executable(ftms_c_client main.c)
target_compile_features(ftms_c_client PRIVATE c_std_99)
target_link_libraries(ftms_c_client PRIVATE ftms::ftms)

enable_testing()
add_test(NAME ftms_c_client COMMAND ftms_c_client)

# Compile the same public-interface example as C++ while linking the C library.
configure_file(main.c ${CMAKE_CURRENT_BINARY_DIR}/main.cpp COPYONLY)
add_executable(ftms_cpp_client ${CMAKE_CURRENT_BINARY_DIR}/main.cpp)
target_compile_features(ftms_cpp_client PRIVATE cxx_std_11)
target_link_libraries(ftms_cpp_client PRIVATE ftms::ftms)
add_test(NAME ftms_cpp_client COMMAND ftms_cpp_client)
