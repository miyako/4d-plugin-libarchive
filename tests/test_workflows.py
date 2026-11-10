from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkflowContractTests(unittest.TestCase):
    def test_exact_manual_build_and_bump(self):
        release = (ROOT / ".github/workflows/release.yml").read_text()
        bump = (ROOT / ".github/workflows/bump-version.yml").read_text()
        self.assertTrue(release.startswith("name: Build\n"))
        trigger = release.split("permissions:", 1)[0]
        self.assertIn("workflow_dispatch:", trigger)
        self.assertNotIn("inputs:", trigger)
        self.assertNotIn("push:", trigger)
        self.assertNotIn("workflow_run:", trigger)
        self.assertIn("default: patch", bump)
        self.assertIn("required: true", bump)
        self.assertEqual(re.findall(r"^      \w+:\s*$", bump.split("permissions:", 1)[0], re.M), ["      mode:"])
        for mode in ("patch", "minor", "major"):
            self.assertIn(f"- {mode}", bump)
        self.assertNotIn("git tag", bump)
        self.assertNotIn("gh workflow", bump)

    def test_every_checkout_immutable_including_unrelated_testing(self):
        for workflow in (ROOT / ".github/workflows").glob("*.yml"):
            text = workflow.read_text()
            checkouts = re.findall(r"uses: actions/checkout@[^\n]+\n(.*?)(?=\n\s+- |\Z)", text, re.S)
            self.assertTrue(checkouts, workflow.name)
            for checkout in checkouts:
                self.assertIn("ref: ${{ github.sha }}", checkout, workflow.name)

    def test_testing_trigger_and_platform_policy_preserved(self):
        test = (ROOT / ".github/workflows/test.yml").read_text()
        self.assertIn("push:\n    tags:\n      - '*'", test)
        self.assertIn("workflow_dispatch:", test)
        self.assertNotIn("pull_request:", test)
        self.assertIn("tool4d_arm64.tar.xz", test)
        self.assertIn("tool4d_win.tar.xz", test)
        self.assertIn("--startup-method=test_all", test)
        self.assertIn("cmake --build . --config Release", test)

    def test_original_native_topology_and_signing_secrets(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        self.assertIn("build-windows:", workflow)
        self.assertIn("build-macos:", workflow)
        self.assertIn("needs: [version, build-windows]", workflow)
        self.assertIn("MACOS_DEPLOYMENT_TARGET: '10.13'", workflow)
        self.assertIn("cancel-in-progress: false", workflow)
        self.assertNotIn("group: release-${{ github.ref }}", workflow)
        for name in (
            "APPLE_DEVELOPER_ID_CERTIFICATE", "APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD",
            "KEYCHAIN_PASSWORD", "NOTARYTOOL_APPLE_ID", "NOTARYTOOL_TEAM_ID", "NOTARYTOOL_PASSWORD",
        ):
            self.assertIn("secrets." + name, workflow)
        cmake = (ROOT / "4DArchive/CMakeLists.txt").read_text()
        for policy in (
            'set(BUILD_SHARED_LIBS OFF', 'set(ENABLE_ZLIB ON',
            'set(ENABLE_BZip2 ON', 'set(ENABLE_CNG ON',
            'add_subdirectory("${LIBARCHIVE_DIR}" "${CMAKE_BINARY_DIR}/libarchive")',
            'target_link_libraries(${PLUGIN_NAME} PRIVATE archive_static)',
            'MACOSX_BUNDLE_BUNDLE_VERSION "1.0"',
        ):
            self.assertIn(policy, cmake)

    def test_build_disables_checkout_conversion_in_scoped_inherited_git_environment(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        environment = workflow.split("\nenv:\n", 1)[1].split("\nconcurrency:", 1)[0]
        self.assertIn("GIT_CONFIG_COUNT: '1'", environment)
        self.assertIn("GIT_CONFIG_KEY_0: core.autocrlf", environment)
        self.assertIn("GIT_CONFIG_VALUE_0: 'false'", environment)
        self.assertNotIn("git config --global", workflow)
        self.assertEqual(workflow.count("submodules: recursive"), 3)


if __name__ == "__main__":
    unittest.main()
