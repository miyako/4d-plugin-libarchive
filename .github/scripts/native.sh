#!/bin/bash
set -euo pipefail

case "${1:?native phase required}" in
  build)
    python3 .github/scripts/native.py clean-macos
    cmake -S 4DArchive -B 4DArchive/cmake-build \
      -DCMAKE_BUILD_TYPE=Release \
      '-DCMAKE_OSX_ARCHITECTURES=arm64;x86_64' \
      "-DCMAKE_OSX_DEPLOYMENT_TARGET=${MACOS_DEPLOYMENT_TARGET:?}"
    cmake --build 4DArchive/cmake-build
    python3 .github/scripts/native.py architectures
    ;;
  merge)
    python3 - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, ".github/scripts")
import native
source = native.regular(Path("winbuild/4DArchive.4DX"))
target = native.regular(native.CONTENTS / "Windows64/4DArchive.4DX")
if not source.is_file() or source.stat().st_size == 0:
    raise ValueError("missing/empty downloaded Windows binary")
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(source.read_bytes())
native.validate()
PY
    echo "BUNDLE_PATH=4DArchive/4DArchive-test/Plugins/4DArchive.bundle" >> "$GITHUB_ENV"
    ;;
  sign)
    IDENTITY=$(security find-identity -v -p codesigning "$KEYCHAIN_PATH" \
      | grep "Developer ID Application" | head -1 | sed -E 's/.*"(.*)".*/\1/')
    test -n "$IDENTITY"
    codesign --deep --verbose --timestamp --force --options=runtime \
      --sign "$IDENTITY" "$BUNDLE_PATH"
    codesign --verify --deep --strict --verbose=2 "$BUNDLE_PATH"
    ;;
  package)
    VERSION=$(python3 .github/scripts/source_version.py)
    ZIP_PATH="4DArchive-${VERSION}.zip"
    DMG_PATH="4DArchive-${VERSION}.dmg"
    ditto -c -k --keepParent "$BUNDLE_PATH" "$ZIP_PATH"
    hdiutil create -format UDBZ -volname 4DArchive -srcfolder "$BUNDLE_PATH" "$DMG_PATH"
    for asset in "$ZIP_PATH" "$DMG_PATH"; do
      xcrun notarytool submit "$asset" --keychain-profile notarytool-profile \
        --keychain "$KEYCHAIN_PATH" --wait --output-format json > "$RUNNER_TEMP/notary-result.json"
      python3 - "$RUNNER_TEMP/notary-result.json" <<'PY'
import json
import sys
sys.path.insert(0, ".github/scripts")
from release import finite_float, invalid_constant, json_object
with open(sys.argv[1]) as stream:
    result = json.load(stream, object_pairs_hook=json_object,
                       parse_constant=invalid_constant, parse_float=finite_float)
if not isinstance(result, dict) or result.get("status") != "Accepted":
    raise SystemExit("notarization did not return Accepted")
PY
    done
    xcrun stapler staple "$DMG_PATH"
    codesign --verify --deep --strict --verbose=2 "$BUNDLE_PATH"
    python3 .github/scripts/native.py validate
    echo "ZIP_PATH=$ZIP_PATH" >> "$GITHUB_ENV"
    echo "DMG_PATH=$DMG_PATH" >> "$GITHUB_ENV"
    ;;
  *)
    echo "unknown native phase: $1" >&2
    exit 1
    ;;
esac
