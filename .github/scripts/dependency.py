"""Bind the recursively checked-out libarchive source to its selected gitlink."""

import os
from pathlib import Path
import subprocess


PATH = "deps/libarchive"


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args])


def validate(root, selected):
    from repository import actual_blob

    root = Path(root)
    record = git(root, "ls-tree", selected, "--", PATH).decode().strip()
    fields = record.split()
    if len(fields) != 4 or fields[:2] != ["160000", "commit"] or fields[3] != PATH:
        raise ValueError("selected tree must contain the exact libarchive gitlink")
    sha = fields[2]
    staged = git(root, "ls-files", "--stage", "--", PATH).decode().strip()
    if staged != f"160000 {sha} 0\t{PATH}":
        raise ValueError("libarchive index gitlink differs from selected source")
    path = root
    for component in Path(PATH).parts:
        path /= component
        if path.is_symlink() or not path.is_dir():
            raise ValueError("libarchive must be an initialized nonsymlink submodule")
    if not (path / ".git").exists() or (path / ".git").is_symlink():
        raise ValueError("libarchive checkout has no valid Git marker")
    if git(path, "rev-parse", "HEAD").decode().strip() != sha:
        raise ValueError("libarchive HEAD differs from selected gitlink")
    if git(path, "status", "--porcelain=v1", "--untracked-files=all", "--ignored"):
        raise ValueError("libarchive source has tracked, untracked or ignored changes")
    tree = {}
    for record in git(path, "ls-tree", "-r", "-z", sha).split(b"\0"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, kind, blob = metadata.decode().split()
        if kind != "blob" or mode not in ("100644", "100755"):
            raise ValueError("unexpected libarchive source tree entry")
        tree[os.fsdecode(raw_name)] = (mode, blob)
    index = {}
    for record in git(path, "ls-files", "--stage", "-z").split(b"\0"):
        if not record:
            continue
        metadata, raw_name = record.split(b"\t", 1)
        mode, blob, stage = metadata.decode().split()
        if stage != "0":
            raise ValueError("unmerged libarchive index")
        index[os.fsdecode(raw_name)] = (mode, blob)
    if index != tree:
        raise ValueError("libarchive index differs from immutable tree")
    for flag in ("-v", "-f"):
        for record in git(path, "ls-files", flag, "-z").split(b"\0"):
            if record and record[:2] != b"H ":
                raise ValueError("hidden libarchive index flags")
    for name, (mode, blob) in tree.items():
        source = path
        for component in Path(name).parts:
            source /= component
            if source.is_symlink():
                raise ValueError("symlink in immutable libarchive source")
        if not source.is_file():
            raise ValueError("missing immutable libarchive source")
        if actual_blob(source) != (mode, blob):
            raise ValueError(f"raw libarchive source differs from selected tree: {name}")
