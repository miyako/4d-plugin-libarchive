"""Narrow cleanup and validation for the existing CMake package layout."""

import argparse
from pathlib import Path
import plistlib
import re
import shutil
import subprocess

import version_model


ROOT = Path(__file__).resolve().parents[2]
PRODUCT = "4DArchive"
BUNDLE = Path("4DArchive/4DArchive-test/Plugins/4DArchive.bundle")
CONTENTS = BUNDLE / "Contents"
EXECUTABLE = CONTENTS / "MacOS/4DArchive"
WINDOWS = Path("4DArchive/4DArchive-test/Plugins/4DArchive/Contents/Windows64/4DArchive.4DX")
RESOURCES = ("manifest.json", "constants.xlf")
FILES = (
    EXECUTABLE, CONTENTS / "Info.plist",
    *(CONTENTS / "Resources" / name for name in RESOURCES),
    CONTENTS / "Windows64/4DArchive.4DX",
    CONTENTS / "_CodeSignature/CodeResources",
    Path("winbuild/4DArchive.4DX"),
)
DIRECTORIES = (Path("4DArchive/cmake-build"), CONTENTS / "_CodeSignature")


def generated(path):
    path = Path(path)
    if path in FILES:
        return True
    build = DIRECTORIES[0]
    if not path.is_relative_to(build):
        return False
    relative = path.relative_to(build).as_posix()
    if relative in {
        "CMakeCache.txt", "Makefile", "cmake_install.cmake",
        "libarchive/Makefile", "libarchive/cmake_install.cmake", "libarchive/config.h",
        "libarchive/libarchive/Makefile", "libarchive/libarchive/cmake_install.cmake",
        "libarchive/libarchive/libarchive.a", "libarchive/build/pkgconfig/libarchive.pc",
        "libarchive/cmake.tmp/CheckFuncs_stub.c",
        "CMakeFiles/4DArchive.dir/Info.plist",
    }:
        return True
    if not (relative.startswith("CMakeFiles/") or "/CMakeFiles/" in relative):
        return False
    leaf = path.name
    if leaf in {
        "cmake.check_cache", "Makefile2", "Makefile.cmake", "TargetDirectories.txt",
        "progress.marks", "CMakeDirectoryInformation.cmake", "CMakeConfigureLog.yaml",
        "CMakeOutput.log", "CMakeError.log", "InstallScripts.json",
        "CMakeCCompiler.cmake", "CMakeCXXCompiler.cmake", "CMakeSystem.cmake",
        "CMakeDetermineCompilerABI_C.bin", "CMakeDetermineCompilerABI_CXX.bin",
        "CMakeCCompilerId.c", "CMakeCXXCompilerId.cpp", "a.out",
        "build.make", "cmake_clean.cmake", "cmake_clean_target.cmake",
        "compiler_depend.make", "compiler_depend.ts", "compiler_depend.internal",
        "depend.make", "flags.make", "link.txt", "progress.make", "DependInfo.cmake",
        "confdefs.h", "check_crypto_md.h", "check_crypto_md.c",
    }:
        return True
    return bool(re.fullmatch(r".+\.(?:o|o\.d|obj|bin)", leaf))


def validate_paths(paths):
    for relative in paths:
        path = regular(relative, Path("."))
        if path.is_dir():
            for descendant in path.rglob("*"):
                regular(descendant, Path("."))


def verify_resources():
    validate_resources(Path("."))


def regular(path, root=ROOT):
    root = Path(root)
    path = Path(path)
    relative = path.relative_to(root) if path.is_absolute() else path
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError(f"symlink is not a native input/output: {current}")
        if current.exists() and not current.is_file() and not current.is_dir():
            raise ValueError(f"unsupported native input/output type: {current}")
    return current


def clean(platform, root=ROOT):
    root = Path(root)
    version_model.read(root)
    paths = [Path("4DArchive/cmake-build")]
    if platform == "macos":
        paths += [EXECUTABLE, CONTENTS / "Info.plist", CONTENTS / "_CodeSignature"]
        paths += [CONTENTS / "Resources" / name for name in RESOURCES]
    elif platform == "windows":
        paths += [WINDOWS]
        paths += [WINDOWS.parents[1] / "Resources" / name for name in RESOURCES]
    else:
        raise ValueError("unknown platform")
    checked = [regular(path, root) for path in paths]
    for path in checked:
        if path.is_dir():
            for descendant in path.rglob("*"):
                regular(descendant, root)
    for path in checked:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def validate_resources(root=ROOT):
    root = Path(root)
    for name in RESOURCES:
        source = regular(Path("4DArchive") / name, root)
        destination = regular(CONTENTS / "Resources" / name, root)
        if not source.is_file() or not destination.is_file() or source.read_bytes() != destination.read_bytes():
            raise ValueError(f"copied resource differs from exact source: {name}")


def validate(root=ROOT):
    root = Path(root)
    version = version_model.read(root)
    path = regular(CONTENTS / "Info.plist", root)
    with path.open("rb") as stream:
        metadata = plistlib.load(stream)
    expected = {
        "CFBundleShortVersionString": version,
        "CFBundleExecutable": PRODUCT,
        "CFBundleIdentifier": "com.4d.4DArchive",
        "CFBundlePackageType": "BNDL",
    }
    if version_model.has_build_key(root):
        expected["CFBundleVersion"] = "1.0"
    elif "CFBundleVersion" in metadata:
        raise ValueError("built metadata invented an absent source build key")
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError("built bundle metadata differs from immutable source policy")
    for relative in (EXECUTABLE, CONTENTS / "Windows64/4DArchive.4DX"):
        path = regular(relative, root)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f"missing/empty native output: {relative}")
    validate_resources(root)
    return version


def architectures(output):
    values = output.strip().split()
    if not {"arm64", "x86_64"} <= set(values):
        raise ValueError("native executable must contain exact arm64 and x86_64 architecture tokens")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("clean-macos", "clean-windows", "validate", "architectures"))
    args = parser.parse_args()
    if args.command.startswith("clean-"):
        clean(args.command[6:])
    elif args.command == "validate":
        validate()
    else:
        path = regular(EXECUTABLE)
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("missing/empty newly built macOS executable")
        result = subprocess.run(["lipo", "-archs", str(path)], check=True, text=True, capture_output=True)
        architectures(result.stdout)


if __name__ == "__main__":
    main()
