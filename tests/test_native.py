import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github/scripts"))
import native
import version_model


class NativeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / ".github/scripts").mkdir(parents=True)
        for path in (ROOT / ".github/scripts").iterdir():
            if path.is_file():
                shutil.copyfile(path, self.root / ".github/scripts" / path.name)
        for name in ("VERSION", "4DArchive/CMakeLists.txt", "4DArchive/Info.plist.in",
                     "4DArchive/manifest.json", "4DArchive/constants.xlf"):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.version = version_model.read(self.root)
        self.populate()

    def populate(self, binary=False):
        contents = self.root / native.CONTENTS
        contents.mkdir(parents=True, exist_ok=True)
        (contents / "Info.plist").write_bytes(plistlib.dumps({
            "CFBundleShortVersionString": self.version, "CFBundleVersion": "1.0",
            "CFBundleExecutable": "4DArchive", "CFBundleIdentifier": "com.4d.4DArchive",
            "CFBundlePackageType": "BNDL",
        }, fmt=plistlib.FMT_BINARY if binary else plistlib.FMT_XML))
        for relative in (native.EXECUTABLE, native.CONTENTS / "Windows64/4DArchive.4DX",
                         native.DOWNLOAD, native.CONTENTS / "_CodeSignature/CodeResources"):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"fresh native bytes")
        for name in native.RESOURCES:
            path = contents / "Resources" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((self.root / "4DArchive" / name).read_bytes())

    def test_built_xml_and_binary_metadata(self):
        for binary in (False, True):
            self.populate(binary)
            self.assertEqual(native.validate(self.root), self.version)
            self.assertEqual(native.validate_final(self.root), self.version)

    def test_unsigned_merge_validation_does_not_require_final_signature(self):
        (self.root / native.CONTENTS / "_CodeSignature/CodeResources").unlink()
        self.assertEqual(native.validate(self.root), self.version)
        with self.assertRaisesRegex(ValueError, "final native leaf"):
            native.validate_final(self.root)

    def test_final_windows_download_must_equal_merged_bytes(self):
        (self.root / native.DOWNLOAD).write_bytes(b"late different download")
        with self.assertRaisesRegex(ValueError, "exact downloaded artifact"):
            native.validate_final(self.root)

    def test_metadata_drift_and_missing_short(self):
        path = self.root / native.CONTENTS / "Info.plist"
        for changes in ({"CFBundleShortVersionString": "0.0.0"}, {"CFBundleVersion": "9.0"},
                        {"CFBundleExecutable": "wrong"}, {"CFBundleShortVersionString": None}):
            self.populate()
            value = plistlib.loads(path.read_bytes())
            value.update(changes)
            value = {key: item for key, item in value.items() if item is not None}
            path.write_bytes(plistlib.dumps(value))
            with self.assertRaises(ValueError):
                native.validate(self.root)

    def test_final_resources_exact_source(self):
        for name in native.RESOURCES:
            self.populate()
            (self.root / native.CONTENTS / "Resources" / name).write_bytes(b"tampered")
            with self.assertRaisesRegex(ValueError, "exact source"):
                native.validate(self.root)

    def test_exact_architecture_tokens_extras_preserved(self):
        for output in ("arm64 x86_64", "arm64 x86_64 i386", "arm64e arm64 x86_64"):
            native.architectures(output)
        for output in ("arm64e x86_64", "arm64 x86_64h", "", "i386"):
            with self.assertRaises(ValueError):
                native.architectures(output)

    def test_selective_cleanup_preserves_inputs_and_windows(self):
        resource = self.root / native.CONTENTS / "Resources/keep.txt"
        resource.write_text("not generated")
        windows = self.root / native.CONTENTS / "Windows64/4DArchive.4DX"
        native.clean("macos", self.root)
        self.assertEqual(resource.read_text(), "not generated")
        self.assertEqual(windows.read_bytes(), b"fresh native bytes")
        self.assertTrue((self.root / "4DArchive/manifest.json").is_file())
        self.assertFalse((self.root / native.EXECUTABLE).exists())

    def test_cleanup_prevalidates_symlinks_before_any_deletion(self):
        output = self.root / native.EXECUTABLE
        output.unlink()
        output.symlink_to(self.root / "VERSION")
        with self.assertRaisesRegex(ValueError, "symlink"):
            native.clean("macos", self.root)
        self.assertTrue((self.root / native.CONTENTS / "Info.plist").exists())

    def test_cleanup_rejects_intermediate_symlink(self):
        build = self.root / "4DArchive/cmake-build"
        build.mkdir()
        (build / "escape").symlink_to(self.root / "VERSION")
        with self.assertRaises(ValueError):
            native.clean("macos", self.root)
        self.assertTrue((self.root / native.EXECUTABLE).is_file())

    def stub_path(self):
        tools = self.root / "closed-tools"
        tools.mkdir()
        (tools / "python3").symlink_to(sys.executable)
        stub = tools / "stub"
        stub.write_text(f"""#!{sys.executable}
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
with open(os.environ['NATIVE_LOG'], 'a') as log:
    log.write(json.dumps([name] + sys.argv[1:]) + '\\n')
if name == 'cmake':
    if os.environ.get('FAIL_CMAKE') == ('build' if '--build' in sys.argv else 'configure'):
        sys.exit(7)
    if '--build' in sys.argv and not os.environ.get('NO_BINARY'):
        suffix = '4DArchive/Contents/Windows64/4DArchive.4DX' if '--config' in sys.argv else '4DArchive.bundle/Contents/MacOS/4DArchive'
        target = pathlib.Path('4DArchive/4DArchive-test/Plugins') / suffix
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'fresh closed-PATH native output')
elif name == 'lipo':
    print(os.environ.get('ARCHS', 'arm64 x86_64'))
elif name == 'security':
    print('1) ABC "Developer ID Application: fixture"')
elif name == 'xcrun' and 'notarytool' in sys.argv:
    print(json.dumps({{'status': os.environ.get('NOTARY_STATUS', 'Accepted')}}))
    sys.exit(int(os.environ.get('NOTARY_EXIT', '0')))
elif name in ('ditto', 'hdiutil'):
    target = sys.argv[-1] if name == 'ditto' else sys.argv[-1]
    pathlib.Path(target).write_bytes(b'asset fixture')
""")
        stub.chmod(0o755)
        for name in ("cmake", "lipo", "security", "codesign", "ditto", "hdiutil", "xcrun"):
            (tools / name).symlink_to(stub.name)
        for name, script in (
            ("grep", 'import sys\nlines=sys.stdin.readlines()\nprint("".join(s for s in lines if "Developer ID Application" in s),end="")'),
            ("head", 'import sys\nprint(sys.stdin.readline(),end="")'),
            ("sed", 'import sys\nprint(sys.stdin.read().split(\'"\')[1])'),
        ):
            path = tools / name
            path.write_text(f"#!{sys.executable}\n{script}\n")
            path.chmod(0o755)
        return tools

    def run_phase(self, phase, **extra):
        env = dict(os.environ, PATH=str(self.tools), NATIVE_LOG=str(self.root / "native.log"),
                   MACOS_DEPLOYMENT_TARGET="10.13", GITHUB_ENV=str(self.root / "github.env"),
                   KEYCHAIN_PATH=str(self.root / "fixture.keychain"), RUNNER_TEMP=str(self.root),
                   BUNDLE_PATH=str(native.BUNDLE), **extra)
        return subprocess.run(["/bin/bash", ".github/scripts/native.sh", phase], cwd=self.root,
                              env=env, capture_output=True, text=True)

    def test_actual_shell_build_only_closed_native_stubs(self):
        self.tools = self.stub_path()
        result = self.run_phase("build")
        self.assertEqual(result.returncode, 0, result.stderr)
        log = (self.root / "native.log").read_text()
        self.assertIn("arm64;x86_64", log)
        self.assertIn("10.13", log)
        result = self.run_phase("build", ARCHS="arm64e x86_64")
        self.assertNotEqual(result.returncode, 0)
        result = self.run_phase("build", NO_BINARY="1")
        self.assertNotEqual(result.returncode, 0)
        for stage in ("configure", "build"):
            result = self.run_phase("build", FAIL_CMAKE=stage)
            self.assertNotEqual(result.returncode, 0)

    def test_actual_shell_sign_and_notary_fail_closed(self):
        self.tools = self.stub_path()
        result = self.run_phase("sign")
        self.assertEqual(result.returncode, 0, result.stderr)
        for extra in ({}, {"NOTARY_STATUS": "Invalid"}, {"NOTARY_EXIT": "1"}):
            (self.root / "native.log").write_text("")
            result = self.run_phase("package", **extra)
            self.assertEqual(result.returncode == 0, not extra, result.stderr)
            log = (self.root / "native.log").read_text()
            self.assertEqual('"stapler"' in log, not extra)

    def test_actual_extracted_windows_powershell_closed_native_stubs(self):
        powershell = shutil.which("pwsh")
        self.assertIsNotNone(powershell, "PowerShell is required for the Windows offline cases")
        self.tools = self.stub_path()
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        body = workflow.split("      - name: build with CMake\n", 1)[1]
        script = textwrap.dedent(body.split("        run: |\n", 1)[1].split("\n      - name:", 1)[0])
        path = self.root / "windows-build.ps1"
        path.write_text(script)
        for extra in ({}, {"FAIL_CMAKE": "configure"}, {"FAIL_CMAKE": "build"}, {"NO_BINARY": "1"}):
            output = self.root / native.WINDOWS
            if output.exists():
                output.unlink()
            env = dict(os.environ, PATH=str(self.tools), NATIVE_LOG=str(self.root / "native.log"), **extra)
            result = subprocess.run([powershell, "-NoProfile", "-NonInteractive", "-File", str(path)],
                                    cwd=self.root, env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode == 0, not extra, result.stderr)
            if not extra:
                self.assertEqual(output.read_bytes(), b"fresh closed-PATH native output")


if __name__ == "__main__":
    unittest.main()
