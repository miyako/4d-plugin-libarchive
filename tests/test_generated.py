from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github/scripts"))
import native


class GeneratedTests(unittest.TestCase):
    def test_exact_outputs_and_cmake_intermediates(self):
        paths = [
            *map(str, native.FILES),
            "4DArchive/cmake-build/CMakeCache.txt",
            "4DArchive/cmake-build/libarchive/config.h",
            "4DArchive/cmake-build/libarchive/libarchive/libarchive.a",
            "4DArchive/cmake-build/CMakeFiles/4DArchive.dir/archive_commands.cpp.o",
            "4DArchive/cmake-build/libarchive/libarchive/CMakeFiles/archive_static.dir/archive_read.c.o.d",
            "4DArchive/cmake-build/CMakeFiles/3.31.0/CompilerIdC/CMakeCCompilerId.c",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertTrue(native.generated(path))

    def test_no_broad_bundle_cmake_or_xcode_exemption(self):
        paths = [
            "VERSION", "4DArchive/CMakeLists.txt", "4DArchive/Info.plist.in",
            "4DArchive/manifest.json", "4DArchive/constants.xlf", "deps/libarchive/source.c",
            str(native.CONTENTS / "Resources/manifest.json.bak"),
            str(native.CONTENTS / "Resources/unexpected.cpp"),
            str(native.CONTENTS / "MacOS/other"),
            "4DArchive/cmake-build-evil/CMakeCache.txt",
            "4DArchive/cmake-build/unexpected-source.cpp",
            "4DArchive/cmake-build/CMakeFiles/unexpected-source.cpp",
            "4DArchive/cmake-build/CMakeFiles/build.db-evil",
            "build/XCBuildData/build.db",
            "build/XCBuildData/unexpected-source.cpp",
            "build/XCBuildData/build.db-evil",
            "build/XCBuildData/evil.xcbuilddata/manifest.json",
            "build/XCBuildData/0123456789abcdef0123456789abcdef.xcbuilddata/manifest.json",
            "4DArchive/cmake-build/build/XCBuildData/evil.xcbuilddata/manifest.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertFalse(native.generated(path))


if __name__ == "__main__":
    unittest.main()
