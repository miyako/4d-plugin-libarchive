# 4DArchive

A 4D plugin for creating, extracting, and listing archive files. Built on [libarchive](https://github.com/libarchive/libarchive) — the same library behind `bsdtar`, `bsdcpio`, and macOS's built-in archive tools.

## Supported Formats

| Format | Create | Extract | List |
|---|---|---|---|
| tar (ustar/pax/GNU) | ✅ | ✅ | ✅ |
| ZIP | ✅ | ✅ | ✅ |
| 7-Zip | ✅ | ✅ | ✅ |
| cpio | ✅ | ✅ | ✅ |
| RAR (v4/v5) | — | ✅ | ✅ |
| CAB | — | ✅ | ✅ |

## Supported Compression

| Filter | Constant |
|---|---|
| None | `Archive filter none` |
| gzip (.gz) | `Archive filter gzip` |
| bzip2 (.bz2) | `Archive filter bzip2` |
| xz (.xz) | `Archive filter xz` |
| zstd (.zst) | `Archive filter zstd` |
| lz4 (.lz4) | `Archive filter lz4` |

Extraction and listing auto-detect compression — no need to specify.

## Requirements

- 4D v21.1 or later

## Installation

Download the latest release from the [Releases](../../releases) page.

### macOS & Windows (single download)

1. Download the `.zip` from the release
2. Extract to get the `4DArchive.bundle` folder
3. Copy the `.bundle` into your 4D application's **Plugins** folder
4. Restart 4D

### macOS only (notarized DMG)

1. Download the `.dmg` from the release
2. Mount it and copy the `.bundle` into your **Plugins** folder
3. Restart 4D

## Commands

### `Archive Create`

Create an archive from a file or folder.

```4d
$status:=Archive Create($source; $archive; $format; $filter)
```

| Parameter | Type | Description |
|---|---|---|
| `$source` | Text | POSIX path to file or folder to archive |
| `$archive` | Text | POSIX path for output archive file |
| `$format` | Longint | Archive format constant |
| `$filter` | Longint | Compression filter constant |
| `$status` | Longint | 0 on success, non-zero on error |

**Example:**

```4d
$status:=Archive Create("/Users/me/Documents"; "/Users/me/backup.tar.gz"; Archive format tar; Archive filter gzip)
```

### `Archive Extract`

Extract an archive to a destination folder. Format and compression are auto-detected.

```4d
$status:=Archive Extract($archive; $destination)
```

| Parameter | Type | Description |
|---|---|---|
| `$archive` | Text | POSIX path to archive file |
| `$destination` | Text | POSIX path to extraction folder (created if needed) |
| `$status` | Longint | 0 on success, non-zero on error |

**Example:**

```4d
$status:=Archive Extract("/Users/me/backup.tar.gz"; "/Users/me/restored")
```

### `Archive List`

List the contents of an archive as a JSON array.

```4d
$json:=Archive List($archive)
```

| Parameter | Type | Description |
|---|---|---|
| `$archive` | Text | POSIX path to archive file |
| `$json` | Text | JSON array of entry objects |

**Entry object format:**
```json
{"path": "folder/file.txt", "size": 1234, "type": "file", "mtime": "2024-01-15T10:30:00Z"}
```

**Example:**

```4d
$json:=Archive List("/Users/me/backup.tar.gz")
$entries:=JSON Parse($json)
For each ($entry; $entries)
    // $entry.path, $entry.size, $entry.type, $entry.mtime
End for each
```

### `Archive SET PASSPHRASE`

Set a passphrase for the next archive operation (encrypted ZIP, 7-Zip, or RAR).

```4d
Archive SET PASSPHRASE($passphrase)
```

| Parameter | Type | Description |
|---|---|---|
| `$passphrase` | Text | Password for encryption/decryption |

The passphrase is consumed and cleared after the next `Archive Create`, `Archive Extract`, or `Archive List` call.

**Example:**

```4d
Archive SET PASSPHRASE("secret123")
$status:=Archive Extract("/Users/me/encrypted.zip"; "/Users/me/decrypted")
```

## Constants

### Archive Format

| Constant | Value | Description |
|---|---|---|
| `Archive format tar` | 1 | tar (pax interchange format) |
| `Archive format zip` | 2 | ZIP |
| `Archive format 7zip` | 3 | 7-Zip |
| `Archive format cpio` | 4 | cpio (SVR4/newc) |

### Archive Filter

| Constant | Value | Description |
|---|---|---|
| `Archive filter none` | 0 | No compression |
| `Archive filter gzip` | 1 | gzip (.gz) |
| `Archive filter bzip2` | 2 | bzip2 (.bz2) |
| `Archive filter xz` | 3 | xz (.xz) |
| `Archive filter zstd` | 4 | Zstandard (.zst) |
| `Archive filter lz4` | 5 | LZ4 (.lz4) |

## Building from Source

### Prerequisites

- CMake 3.20+
- Xcode (macOS) or Visual Studio 2022+ (Windows)

### Clone

```bash
git clone --recurse-submodules https://github.com/{owner}/4darchive-plugin.git
cd 4darchive-plugin
```

### Build (macOS)

```bash
cd 4DArchive
mkdir -p cmake-build && cd cmake-build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build .
```

### Build (Windows)

```pwsh
cd 4DArchive
mkdir cmake-build; cd cmake-build
cmake .. -A x64
cmake --build . --config Release
```

### Run Tests

Requires [tool4d](https://developer.4d.com/docs/Admin/cli/) (free, no license needed):

**macOS:**
```bash
tool4d.app/Contents/MacOS/tool4d --dataless --startup-method=test_all \
  --project=$(pwd)/4DArchive/4DArchive-test/Project/4DArchive.4DProject
```

**Windows:**
```pwsh
./tool4d/tool4d.exe --dataless --startup-method=test_all `
  --project="$((Get-Location).Path)\4DArchive\4DArchive-test\Project\4DArchive.4DProject"
```

## CI/CD

| Workflow | Trigger | Description |
|---|---|---|
| `test.yml` | Tag push / manual | Builds and tests on macOS + Windows |
| `bump-version.yml` | Manual | Bumps `VERSION`, commits, and pushes a `vX.Y.Z` tag |
| `release.yml` | `v*.*.*` tag | Builds universal binary, codesigns, notarizes, publishes release |

### Required Secrets (for `release.yml` only)

| Secret | Description |
|---|---|
| `APPLE_DEVELOPER_ID_CERTIFICATE` | Base64-encoded `.p12` Developer ID Application certificate |
| `APPLE_DEVELOPER_ID_CERTIFICATE_PASSWORD` | Password for the `.p12` file |
| `KEYCHAIN_PASSWORD` | Arbitrary password for the CI keychain |
| `NOTARYTOOL_APPLE_ID` | Apple ID email for notarization |
| `NOTARYTOOL_TEAM_ID` | Apple Developer Team ID |
| `NOTARYTOOL_PASSWORD` | App-specific password from [appleid.apple.com](https://appleid.apple.com) |

## Dependencies

- [4D Plugin SDK](https://github.com/4d/4D-Plugin-SDK) — 4D plugin interface
- [libarchive](https://github.com/libarchive/libarchive) — Multi-format archive library (static, bundled)

## License

MIT
