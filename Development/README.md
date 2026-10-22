# Development workspace

Start with [Contributing](../CONTRIBUTING.md) for compatibility and [Architecture](../ARCHITECTURE.md) for code ownership. This directory contains contributor tools and tests; it is excluded from the install ZIP. The source ZIP includes an explicit subset of it.

## Layout

- `test_*.py`, `test_*.cjs`, `test_filesystem.ps1`: regression checks.
- `render_ui.ps1`: actual IronPython/WinForms harness, with hidden/offscreen test windows.
- `build_release.py`, `build_source.py`, `audit_release.py`: package allowlists, manifests and audits.
- `ENCODER_BUILD.md`, `encoder_sources.json`, `build_encoder.py`, `package_encoder.py`, `inspect_pe.py`: pinned minimal encoder build and provenance checks.
- `quality_lab.py`, `quality_lab.html`: historical standalone calibration/rating lab; current users compare through the native viewer.
- `run_sample_tests.py`: checks on copied real samples.
- Local-only `Test Environment`, `Build Archives`, `Release Prep`, session/history notes and old temporary folders: private inputs and generated results; not public source/runtime content.

## Run checks

The commands below assume the original ComicRack AppData workspace. From a standalone repository, remove the `Scripts/WebP Optimizer/` prefix and configure the paths needed by each harness.

```powershell
python 'Scripts/WebP Optimizer/Development/test_trial_helper.py'
python 'Scripts/WebP Optimizer/Development/test_encoders.py'
python 'Scripts/WebP Optimizer/Development/test_safety.py'
python 'Scripts/WebP Optimizer/Development/test_long_paths.py'
python 'Scripts/WebP Optimizer/Development/test_performance.py'
python 'Scripts/WebP Optimizer/Development/test_performance_support.py'
powershell -NoProfile -File 'Scripts/WebP Optimizer/Development/render_ui.ps1'
```

Use generated/disposable comics, never a production library. CPython tests require Python/Pillow and the tools named in each script. A source checkout omits the encoder executable; follow [ENCODER_BUILD.md](ENCODER_BUILD.md) before bundled-encoder tests. A local ComicRack test installation is needed for native checks.

Some harnesses are installation-specific. The native launcher locates DLLs in the local `ComicRackCE_nightly` folder and reads historical report fixtures; generate trial fixtures with `test_trial_helper.py` first. `test_color_fidelity.py` and `run_sample_tests.py` use private real-comic fixtures that are intentionally absent from Git. The historical `test_quality_lab.cjs` uses Node. Read fixture paths before running these tools; the complete original harness does not run unconfigured on a fresh checkout.

### What the checks cover

| Area | Check |
|---|---|
| Archive/source safety, collisions and injected failures | `test_safety.py`, `test_encoders.py`, `test_long_paths.py` |
| Five-quality trials and retained preview fidelity | `test_trial_helper.py` |
| All seven worker counts, encoded member/profile identity and CRC failures | `test_performance.py` |
| CPU/memory/logical I/O accounting, bounded prefetch and cleanup | `test_performance_support.py` |
| Bundled encoder DLLs, color/profiles and optional old/new byte comparison | `test_bundled_encoder.py` |
| Native settings, safe stop, history, cleanup and color-managed viewer | `test_runtime_features.py`, `test_history.py` via `render_ui.ps1` |
| Checkpoints, streaming conversion and three-book quality ETA | `test_batch.py` via `render_ui.ps1` |
| Setup, preflight, workflow tags, recovery, sleep and dark controls | `test_release_features.py` via `render_ui.ps1` |
| Native benchmarks, applying worker settings and copy/prefetch pipeline | `test_performance_ui.py` via `render_ui.ps1` |
| Known RGB changes, 8x heatmap, pixel coordinates and async close/switch cleanup | `test_preview_difference.py` via `render_ui.ps1` |

Native renders are saved under `Test Environment/UI Review`. The preview tests compare identical images, known signed brightness shifts and localized changes; they do not assert a perceptual quality score. Pixel diagnostics create no persistent user assets.

For history process isolation, use `render_ui.ps1 -HistoryHostSmoke`. It tests child failure containment, subsequent reopening, Unicode settings transfer and session cleanup. `-ModalHistorySmoke -HistoryStackBytes 262144` tests repeated actual options-button launches. These checks terminate only disposable helper processes, not ComicRack or production sources. User confirmation of live history is recorded separately in private release-prep notes.

## Build and verify packages

```powershell
python 'Scripts/WebP Optimizer/Development/build_release.py'
python 'Scripts/WebP Optimizer/Development/build_release.py' --plugin-only
python 'Scripts/WebP Optimizer/Development/build_source.py'
python 'Scripts/WebP Optimizer/Development/test_packaged_release.py'
python 'Scripts/WebP Optimizer/Development/test_packaged_release.py' --plugin-only
python 'Scripts/WebP Optimizer/Development/test_source_package.py'
python 'Scripts/WebP Optimizer/Development/audit_release.py'
```

Builders read `Package.ini`, use explicit allowlists and write ZIPs plus SHA-256 manifests under `Releases`. They refuse to overwrite a version; retain an old draft privately under Development before rebuilding. Every file is CRC/hash checked. The audit expects the normal, plugin-only and source ZIPs and verifies their bytes match current files.

The normal manual-install ZIP includes the minimal static ImageMagick Windows x64 executable, matching license notices and build identity. No loose Microsoft/codec DLLs or compiler tools are shipped. Python/Pillow remain external prerequisites. The optional plugin-only ZIP requires a separately available encoder; its smoke test uses the locally available external tool. The source ZIP includes build recipes/legal materials, without encoder executables, settings, reports, comic fixtures or generated results.

`test_packaged_release.py` extracts to an isolated generated fixture and converts a disposable comic. This proves package behavior on the current PC, not a fresh Windows installation. Follow the user-facing setup/quick start in a separate test profile or PC before stable release.

## Release status

Current stable release: **1.0.0**, promoted from the reviewed 0.9.13 preparation build. The final feature addition was preview diagnostics. Keep maintenance fixes separate from new feature work. Defaults remain Q80, no resize, one worker, Normal priority and prefetch off. Preserve checkpoint policy compatibility unless conversion semantics change.

The reviewed minimal encoder replaced the earlier broad Visual Studio binary and loose runtime DLLs. Historical licensing gates refer to that retired build. The current package retains matching component notices and pinned provenance; see [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). Keep final installation acceptance distinct from automated tests.
