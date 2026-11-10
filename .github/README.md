# Manual versioning and publication

`Bump version` and `Build` are independent manual workflows. Bump has one required
`patch`/`minor`/`major` choice (default `patch`). Select a branch using GitHub's
built-in ref selector. Bump commits only `VERSION`, using the Actions bot identity
and the Copilot App co-author trailer. It never builds, tags, releases or dispatches
another workflow. It requires the selected immutable event commit to remain the
remote branch tip through the actual pre-push advertisement.

`Build` has no custom inputs. Select any intended branch or tag in the built-in
ref selector. The immutable selected source supplies the canonical `X.Y.Z`
version and the new `vX.Y.Z` tag. The original independent CMake bundle build
version remains `1.0`; its short version now derives from `VERSION`. The intake
version is not incremented. The tracked prebuilt bundle is a destination, not
version authority.

The original Windows x64 CMake job precedes the universal macOS CMake job.
libarchive remains an immutable recursively checked-out Git submodule, built
statically in the original CMake intermediate directory. Source resources are
copied exactly. The macOS deployment target remains `10.13`, both exact `arm64`
and `x86_64` slices are required, and additional slices remain permitted. Signing,
notarization of ZIP and DMG, stapling the DMG and strict signature verification
precede final publication. No local native, signing, notarization or 4D execution
is needed for the offline regression suite.

The unrelated `Build and Test` workflow retains its tag-push and manual triggers
and macOS/Windows 4D test jobs. Creating a release tag can trigger that workflow;
Bump and migration branch/PR publication cannot.

## Safety and manual recovery

Build first verifies authentication and the complete draft-inclusive release
inventory, exact API refs and exact remote tag absence, before native work.
After signing/notarization it independently rechecks source HEAD, index, raw
source bytes and initialized submodule content while retaining legitimate
generated output bytes. It validates built metadata and exact copied resources
again. Final validation requires every packaged native leaf, including the
signature, to be a nonempty regular nonsymlink file; the merged Windows binary
must exactly equal the nonempty downloaded artifact. Unsigned pre-sign merge
validation remains separate. All Build checkouts inherit scoped
`core.autocrlf=false`, including recursive dependencies. The index must match
selected file modes everywhere; only Windows worktree regular-file executable
bits are ignored, never symlinks, file types or raw bytes.
Publication uses one repository-wide, cross-ref concurrency group without
cancelling another run; this is serialization, not a FIFO guarantee.

Publication creates a new tag ref at the selected immutable commit, then a new
public release, then uploads assets only to that new release ID. Original empty
release notes are preserved. Existing tags/releases/assets are never reused,
updated, deleted, clobbered or rolled back, including a same-SHA tag race.
Failures retain partial state. Inspect the Actions log and the exact tag,
release ID and uploaded assets; correct the underlying issue and obtain explicit
authorization for any manual recovery. Do not retry publication over partial
state, delete automatically, or change the source checkout to conceal dirt.

Offline checks: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` and `actionlint` for
all workflows, using Python 3, Git, PowerShell (`pwsh`) and actionlint.
Native-command integration cases use a closed stub-only PATH;
they do not exercise hosted toolchains, credentials, signing services or 4D.
