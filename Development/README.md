# Development workspace

This folder is excluded from releases. Runtime files stay one level above it so the working ComicRack installation keeps its expected paths.

Contributor entry points: [Contributing](../CONTRIBUTING.md) explains compatibility and verification; [Architecture](../ARCHITECTURE.md) maps the commented runtime sections. Some native/color/sample harnesses require local fixtures and installation paths described there; not all checks work from a fresh checkout without those inputs.

- `Test Environment/`: original development fixtures, generated runs, quality lab, native UI renders and color checks. Moving the folder did not change comic archive contents. Old absolute paths in historical reports may refer to the previous location.
- `test_*.py`, `test_*.cjs`, `test_filesystem.ps1`: regression checks.
- `render_ui.ps1`: loads the actual ComicRack IronPython runtime and runs native UI/runtime checks with invisible windows. Requires the existing portable `ComicRackCE_nightly` resources in this workspace.
- `quality_lab.py`, `quality_lab.html`: standalone historical calibration/rating lab.
- `run_sample_tests.py`: non-destructive real-sample conversion checks.
- `Implementation History.md`, `Restart Review.md`: development history, not current user documentation.
- `Legacy Temp/`: preserved leftover sandbox test folder. Not part of the plugin runtime.

Run from the ComicRack appdata workspace:

```powershell
python 'Scripts/WebP Optimizer/Development/test_trial_helper.py'
python 'Scripts/WebP Optimizer/Development/test_color_fidelity.py'
python 'Scripts/WebP Optimizer/Development/test_encoders.py'
python 'Scripts/WebP Optimizer/Development/test_performance.py'
powershell -NoProfile -File 'Scripts/WebP Optimizer/Development/render_ui.ps1'
node 'Scripts/WebP Optimizer/Development/test_quality_lab.cjs'
```

Tests create synthetic or copied fixtures inside this folder. Do not point them at production books. The native checks use generated fixtures from `test_trial_helper.py`; create them first. Original source samples under Test Environment are read-only inputs to the sample tools.

`test_performance.py` benchmarks the same generated eight-page comic with 1/2/4 workers, verifies identical encoded member bytes and ICC profiles, compares ZIP policies, and injects page/CRC failures. Results are saved in Test Environment/Performance Checks. Timing is machine/load/cache dependent and is not a NAS collection forecast. `test_batch.py` runs through render_ui.ps1 and checks native settings, checkpoint identities, pending-output protection, streaming order, interrupted-session reuse and throughput/ETA using isolated generated books and Reports.

The native batch checks include an actual three-book/fifteen-pass quality test and assert that speed/ETA appear after pass one. `render_ui.ps1 -ModalHistorySmoke -HistoryStackBytes 262144` separately tests the real options button inside a modal owner, repeated clicks, real read-only reports and the standalone history hook on a small-stack UI thread. It does not reproduce every aspect of the live ComicRack host; the reported stack-overflow crash still requires a user retest. History diagnostics are bounded to Reports/history-diagnostic.log.

## Build a release

```powershell
python 'Scripts/WebP Optimizer/Development/build_release.py'
```

The builder reads Version from `../Package.ini`, writes a manual-install ZIP and SHA-256 manifest under `../Releases`, and validates its explicit runtime allowlist and member hashes. It does not scan or include Development, Reports, saved settings, temporary files or prior releases. It refuses to overwrite an existing version. Increment the package version or archive the earlier build inside Development before rebuilding.

The ZIP includes the supplied ImageMagick executable, DLLs and supplied license file. Python and Pillow are external prerequisites. The ZIP is not a `.crplugin` installer and has not been tested as a clean-machine installation.

Run `python 'Scripts/WebP Optimizer/Development/build_source.py'` for a separate source-only ZIP whose root can become the GitHub repository. Its allowlist includes MIT/third-party notices, contributor docs, issue/PR templates and development scripts; it excludes local comics/data and all EXE/DLL files. Obtain encoder/runtime dependencies separately when working from this source export. Source and runtime ZIPs have separate manifests and neither builder overwrites an existing version.

Current development version is 0.9.0; first public stable version is reserved as 1.0.0. Earlier local 1.x ZIPs are internal artifacts, preserved under Build Archives rather than presented as public release history. Local runtime bundles remain testing artifacts until the third-party binary distribution items in Release Prep/Release Checklist.md are resolved.


## Reorganization verification

All 58 original sample archives matched their saved SHA-256 hashes after moving into Development/Test Environment. Relocated encoder/color/lab/native tests passed. Delete-on-close tests remove one generated preview run, preserve its report and other runs, reject parent/outside targets and remember the keep preference. The clean ZIP passed allowlist/CRC/hash validation and an extracted-bundle conversion smoke test using its own ImageMagick on a generated comic. This is not a clean-machine ComicRack installation test.

Run the extracted-bundle check with `python 'Scripts/WebP Optimizer/Development/test_packaged_release.py'` after building. Development helpers avoid writing runtime bytecode caches in the plugin root. User Reports and settings.xml stay operational and are excluded from every release by allowlist.
