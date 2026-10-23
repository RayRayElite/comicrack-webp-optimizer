# Contributing

Read [README.md](README.md) for user behavior and [ARCHITECTURE.md](ARCHITECTURE.md) for code ownership and searchable section IDs. Runtime files live in the root; development tools live in [Development](Development/README.md).

The project is maintained by RayRayElite at `RayRayElite/comicrack-webp-optimizer`. Plugin code is MIT licensed; contributions intended for inclusion should use the same license. Keep upstream third-party notices separate. Pull requests, testing and documentation improvements are welcome; contributing back is encouraged rather than required by the license.

## Release policy

Version 1.0.0 is the first stable release. The final feature addition was preview diagnostics in preparation build 0.9.13. Keep maintenance changes focused; propose larger features for a later release. Preserve the defaults and source-replacement safeguards, and rerun relevant checks after a fix.

## Working safely

Use a separate ComicRack test installation or disposable copies of comics. Start with analysis and copy mode before testing replacement. Do not run development tools against a production collection. Reports and history contain personal paths; use synthetic examples in issues and pull requests.

Keep adapter code compatible with ComicRack's IronPython/Python 2 runtime: no f-strings, type annotations, pathlib or CPython-only dependencies there. The worker uses Python 3 and Pillow. Native WinForms code cannot be verified merely by compiling the worker with Python 3.

## Make a change

1. Find the owning section using the architecture map. Trace the adapter/worker boundary if changing conversion behavior.
2. Keep the change focused. Explain the purpose and contracts of new functions with short docstrings. Comment why a safety check or unusual implementation is necessary; avoid repeating obvious statements line by line.
3. Preserve searchable section markers and ComicRack's `#@` hook metadata. Add new sections deliberately and update the map when responsibilities change.
4. Add or run the checks relevant to the behavior changed. Use generated fixtures where possible; original comic samples are local development inputs and are not included in source distribution.
5. Update user documentation for changed behavior and the changelog for a release. Describe what changed, how it was checked and any remaining manual checks in the pull request.

Public option labels, saved settings, history XML, legacy report headers and helper CLI/result keys have compatibility implications. Changing one may require coordinated updates or migration. Do not silently fall back to another encoder: users should know which implementation produced their files.

## Verification map

Run commands from the ComicRack appdata workspace as shown in [Development/README.md](Development/README.md); adjust paths if your checkout lives elsewhere. Python worker tests require Pillow and some require 7-Zip/ImageMagick.

| Area | Check |
|---|---|
| Synthetic full quality test, archive/preview fidelity | Development/test_trial_helper.py |
| Bundled encoder: DLL imports, Q levels, profiles, pixel/byte comparison and staged helper | Development/test_bundled_encoder.py |
| Page workers, stage timings, compression and failure/CRC regressions | Development/test_performance.py |
| Process resource measurements, bounded cache and helper handoff | Development/test_performance_support.py |
| Native worker benchmark, settings, stopping and copy/prefetch pipeline | Development/test_performance_ui.py through render_ui.ps1 |
| Atomic XML/checkpoint paths, locks and failure preservation | Development/test_checkpoint_io.py through render_ui.ps1 -CheckpointIoSmoke |
| Native streaming, interrupted-session resume and pending-output guards | Development/test_batch.py via render_ui.ps1 |
| Encoder availability and generated image conversion | Development/test_encoders.py |
| Read-only extraction, AppleDouble attachments and strict integrity | Development/test_archive_edge_cases.py; test_macos_scan.py through render_ui.ps1 |
| Output/page collisions and archive validation | Development/test_safety.py |
| Profile regression using local Adobe RGB sample | Development/test_color_fidelity.py |
| Preview RGB metrics/heatmap, coordinate mapping and async lifecycle | Development/test_preview_difference.py through render_ui.ps1 |
| Native forms, settings, stopping, cleanup and history | Development/render_ui.ps1, test_runtime_features.py, test_history.py |
| Historical HTML calibration controls | Development/test_quality_lab.cjs |
| Real copied samples and replacement failure cases | Development/run_sample_tests.py |
| Release allowlist, CRC and hashes | Development/build_release.py |
| Extracted release conversion | Development/test_packaged_release.py |
| Source export and all-artifact audit | Development/test_source_package.py, Development/audit_release.py |

Some harnesses are tied to the original development installation: native rendering locates portable ComicRack DLLs and historical report fixtures, while color/sample checks require local comic fixtures. Those fixtures are intentionally excluded from Git. Read each harness's paths before running it; a fresh checkout does not contain every input. Generate the trial fixtures with `test_trial_helper.py` before native checks. A passing render does not replace a live ComicRack integration check.

For UI changes, check normal and high-DPI layouts, keyboard/mouse behavior and closing with X. For conversion changes, check source preservation, metadata, dimensions, unchanged members, output collisions, errors and stop behavior. Replacement changes need rollback/failure checks as well as a successful conversion.

## Packaging and source hygiene

The release builder uses an explicit file allowlist; it never bundles the development tree by recursively copying the folder. It refuses to overwrite a version. Follow the build instructions in Development/README.md and review the resulting manifest.

The local `.gitignore` excludes personal settings, reports, generated releases, comic fixtures, test outputs and session notes. It does not remove existing files or untrack files already committed. Check staged contents before publishing, particularly binary archives and personal paths. Development scripts remain available to contributors even though they are excluded from the install ZIP.

Encoder executables and Microsoft DLLs are excluded from Git and the source ZIP. `Development/build_source.py` makes an explicit source allowlist export without those binaries or local data. A source checkout must build the reviewed encoder using [ENCODER_BUILD.md](Development/ENCODER_BUILD.md), or supply a matching reviewed bundle, before building the normal runtime ZIP. The optional plugin-only build excludes the encoder. Follow THIRD_PARTY_NOTICES before public binary distribution. The 0.x changelog entries describe development milestones; 1.0.0 is the first public stable release.

The native regression harness also runs `Development/test_release_features.py`, covering workflow values, preflight cancellation, setup diagnostics, progress delivery, power-state restoration and recovery guards. `webp_runtime_support.py` requires IronPython 2; do not validate it with CPython 3's compiler. Preserve the section IDs and document changes to checkpoint compatibility.
