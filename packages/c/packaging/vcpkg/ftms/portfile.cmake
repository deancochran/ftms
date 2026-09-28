# This checked-in overlay is only for validation from a verified local source archive.
# Public registry submissions are generated after an immutable c-vVERSION release exists.
set(FTMS_SOURCE_ARCHIVE "$ENV{FTMS_SOURCE_ARCHIVE}")
set(FTMS_SOURCE_ARCHIVE_SHA512 "$ENV{FTMS_SOURCE_ARCHIVE_SHA512}")
if(NOT FTMS_SOURCE_ARCHIVE OR NOT FTMS_SOURCE_ARCHIVE_SHA512)
  message(FATAL_ERROR "Set FTMS_SOURCE_ARCHIVE and FTMS_SOURCE_ARCHIVE_SHA512 from a verified release artifact; do not submit this overlay to a public registry.")
endif()
vcpkg_check_linkage(ONLY_STATIC_LIBRARY)
vcpkg_download_distfile(ARCHIVE
  URLS "file://${FTMS_SOURCE_ARCHIVE}"
  FILENAME "ftms-${VERSION}.tar.gz"
  SHA512 "${FTMS_SOURCE_ARCHIVE_SHA512}")
vcpkg_extract_source_archive_ex(
  OUT_SOURCE_PATH SOURCE_PATH
  ARCHIVE "${ARCHIVE}"
)
vcpkg_cmake_configure(SOURCE_PATH "${SOURCE_PATH}")
vcpkg_cmake_install()
vcpkg_cmake_config_fixup(CONFIG_PATH lib/cmake/ftms)
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/include")
vcpkg_fixup_pkgconfig()
file(REMOVE_RECURSE "${CURRENT_PACKAGES_DIR}/debug/share")
vcpkg_install_copyright(FILE_LIST "${SOURCE_PATH}/LICENSE")
