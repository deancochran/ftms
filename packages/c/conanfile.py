from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy
from pathlib import Path


class FtmsConan(ConanFile):
    name = "ftms"
    package_type = "static-library"
    license = "MIT"
    url = "https://github.com/deancochran/ftms"
    description = "Portable C99 FTMS protocol codecs and capability interpretation"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    exports = "VERSION"

    def set_version(self):
        self.version = (Path(self.recipe_folder) / "VERSION").read_text().strip()

    def export_sources(self):
        for pattern in ("CMakeLists.txt", "VERSION", "README.md", "CHANGELOG.md", "cmake/*", "include/*", "src/*"):
            copy(self, pattern, self.recipe_folder, self.export_sources_folder)
        license_dir = Path(self.recipe_folder)
        if not (license_dir / "LICENSE").is_file():
            license_dir = license_dir.parents[1]
        copy(self, "LICENSE", str(license_dir), self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        toolchain = CMakeToolchain(self)
        toolchain.variables["FTMS_WARNINGS_AS_ERRORS"] = "OFF"
        toolchain.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        if self.options.get_safe("fPIC") is not None:
            toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(self.options.fPIC)
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "ftms")
        self.cpp_info.set_property("cmake_target_name", "ftms::ftms")
        self.cpp_info.libs = ["ftms"]
        self.cpp_info.includedirs = ["include"]
