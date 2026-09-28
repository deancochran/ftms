cmake_minimum_required(VERSION 3.16)

file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/VERSION" FTMS_VERSION
     LIMIT_COUNT 1 REGEX "^[0-9]+\\.[0-9]+\\.[0-9]+$")
if(NOT FTMS_VERSION)
  message(FATAL_ERROR "packages/c/VERSION must contain a semantic version")
endif()

project(ftms VERSION "${FTMS_VERSION}" LANGUAGES C)

include(GNUInstallDirs)
include(CMakePackageConfigHelpers)

add_library(ftms STATIC
  src/ftms.c
  src/control.c
  src/capabilities.c
  src/measurement.c
  src/status.c)
add_library(ftms::ftms ALIAS ftms)

target_compile_features(ftms PUBLIC c_std_99)
target_include_directories(ftms
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:${CMAKE_INSTALL_INCLUDEDIR}>)

option(FTMS_WARNINGS_AS_ERRORS "Treat FTMS library warnings as errors" OFF)
if(CMAKE_C_COMPILER_ID MATCHES "GNU|Clang|AppleClang")
  target_compile_options(ftms PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wsign-conversion)
  if(FTMS_WARNINGS_AS_ERRORS)
    target_compile_options(ftms PRIVATE -Werror)
  endif()
endif()

install(TARGETS ftms EXPORT ftmsTargets
  ARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}"
  INCLUDES DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}")
install(DIRECTORY include/ftms/ DESTINATION "${CMAKE_INSTALL_INCLUDEDIR}/ftms"
  FILES_MATCHING PATTERN "*.h")
if(EXISTS "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
  set(FTMS_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/LICENSE")
else()
  set(FTMS_LICENSE "${CMAKE_CURRENT_SOURCE_DIR}/../../LICENSE")
endif()
install(FILES "${FTMS_LICENSE}"
  DESTINATION "${CMAKE_INSTALL_DATAROOTDIR}/licenses/ftms")

set(FTMS_CMAKE_INSTALL_DIR "${CMAKE_INSTALL_LIBDIR}/cmake/ftms")
configure_package_config_file(
  "${CMAKE_CURRENT_SOURCE_DIR}/cmake/ftmsConfig.cmake.in"
  "${CMAKE_CURRENT_BINARY_DIR}/ftmsConfig.cmake"
  INSTALL_DESTINATION "${FTMS_CMAKE_INSTALL_DIR}")
write_basic_package_version_file(
  "${CMAKE_CURRENT_BINARY_DIR}/ftmsConfigVersion.cmake"
  VERSION "${PROJECT_VERSION}"
  COMPATIBILITY SameMinorVersion)
install(FILES
  "${CMAKE_CURRENT_BINARY_DIR}/ftmsConfig.cmake"
  "${CMAKE_CURRENT_BINARY_DIR}/ftmsConfigVersion.cmake"
  DESTINATION "${FTMS_CMAKE_INSTALL_DIR}")
install(EXPORT ftmsTargets NAMESPACE ftms:: DESTINATION "${FTMS_CMAKE_INSTALL_DIR}")

# Compute prefix from the installed .pc file rather than baking an install path
# into it. This also works when CMAKE_INSTALL_LIBDIR is multiarch.
set(FTMS_PC_DIR "${CMAKE_INSTALL_FULL_LIBDIR}/pkgconfig")
file(RELATIVE_PATH FTMS_PC_PREFIX_RELATIVE "${FTMS_PC_DIR}" "${CMAKE_INSTALL_PREFIX}")
configure_file("${CMAKE_CURRENT_SOURCE_DIR}/cmake/ftms.pc.in"
               "${CMAKE_CURRENT_BINARY_DIR}/ftms.pc" @ONLY)
install(FILES "${CMAKE_CURRENT_BINARY_DIR}/ftms.pc"
  DESTINATION "${CMAKE_INSTALL_LIBDIR}/pkgconfig")
