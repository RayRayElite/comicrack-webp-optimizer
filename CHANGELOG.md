# Release notes

## 1.1.0 - 2026-10-29

### Features

- Open interrupted-work review from results, check and allow retries for multiple attempts, and prepare a retry for cleared books from the current run.
- Record WebPReadOnly during analysis for smart lists identifying protected original archives. Reanalysis refreshes Yes/No/Unknown without changing file attributes.
- Filter and search results by outcome, including a separate Not processed category for untouched books. Sort columns or bring errors to the top.
- View, copy or save one book's complete details. Selecting a book also shows its explanation and suggested next step below the table.
- Prepare another run for selected failures, with settings review and existing interrupted-work safeguards.
- Prepare editable support information, optionally add setup-check results, then redact before copying or saving.
- Review recorded run settings and access report tools through More. Optional status colors and sort preferences are remembered.

### Changes

- Apply a coordinated design to options, results, progress, previews, history, setup, recovery and benchmarks, with clearer headings, grouped settings and prominent primary actions.
- Show concise quality estimates with an About this estimate explanation. Start buttons name the selected action.
- Lead results with the outcome, savings and elapsed time. Keep secondary settings/support/report tools under More.
- Use dark mode by default while preserving saved preferences. Improve contrast, keyboard navigation, search shortcuts and resizing.
- Open large results with 250-book pages and load technical text only when requested. Complete reports remain available.
- Give clearer failure explanations and skip reasons without removing technical evidence.
- Simplify Python/Pillow setup and add a user-facing error reference.

### Fixes

- Detect read-only original archives before replacement conversion and explain how to resolve the protection without changing it automatically.
- Identify the failed replacement step and distinguish access denial from file locks. Preserve completed encoding/validation details when final installation fails.

- Handle results selection events safely when row data is missing or the list is refreshing/closing, preventing a NoneType error.
- Restore readable backgrounds and button text when switching from dark to light mode.
- Fix temporary-folder paths ending in a backslash or pasted inside quotes; explain invalid folder entries before processing.
- Fix text-encoding errors involving valid non-English characters and symbols in filenames.
- Detect an existing destination CBZ before starting CBR replacement, avoiding unnecessary conversion while protecting existing files.
- Distinguish archive damage and conflicting page names from encoder failures; do not label a readable source corrupt without evidence.
- Avoid referring to a recovery file that was never created.

## 1.0.2 - 2026-10-23

### Fixes

- Handle read-only pages and attachments extracted from comics, including cleanup afterward. Original comic permissions remain unchanged.
- Recognize macOS metadata files as attachments rather than comic pages, preventing false image errors. Their contents are still preserved and checked.
- Use shorter temporary filenames when saving progress, settings and history, preventing avoidable Windows path-length errors.
- Give more useful details when saving progress fails, while preserving existing records and preventing conversion without reliable recovery tracking.

## 1.0.1 - 2026-10-22

### Fixes

- Find standalone 7-Zip installations in standard folders, registered custom locations and PATH, resolving false missing-tool errors.
- Recognize ComicRack's `7za64.exe` in its main resource folder.
- Explain where the plugin looks when 7-Zip cannot be found.

## 1.0.0 - 2026-10-22

First public stable release for ComicRack Community Edition.

### Features

- Analyze CBZ/CBR comics and add ImageFormat, WebPStatus and WebPReason values for smart lists.
- Convert JPEG pages to WebP at Q60-Q90, creating copies or replacing originals after validation. Preserve metadata and reading progress, with optional backups.
- Compare five quality levels in a full-screen viewer with linked zoom/scroll, pixel inspection and optional difference measurements and heatmap.
- Choose 1-12 page workers, benchmark worker counts, use local temporary storage or run at Background priority. Optional prefetch prepares the next book while the current one converts.
- Safely stop after the current book, resume compatible completed work and review interrupted attempts.
- Reopen reports and retained previews through Run history, clean up preview files, use dark mode and remember settings.
- Include the ImageMagick encoder and its license notices. Python and Pillow are installed separately; WinRAR is needed only to create CBR output.
- Include installation, workflow and contributor guides with screenshots.

Tested with copy/replacement, NAS storage, CBR-to-CBZ conversion and reader workflows. Individual installations and source files can still expose issues.

## Development history

These milestones describe work before the first public release. Internal build numbers were not public stable releases.

## 0.9.13 - 2026-10-22

### Features

- Add optional pixel-difference measurements, an amplified difference heatmap and an RGB inspector to the preview viewer.

### Changes

- Run analysis in the background without adding files or slowing normal conversions. Matching page dimensions and a 16-million-pixel limit keep memory use bounded.
- Refresh release documentation and shorten the README.

## 0.9.12 - Bundled encoder and licensing

### Features

- Bundle a smaller Windows x64 ImageMagick encoder without requiring a separate Visual C++ runtime installation. Python/Pillow remain separate prerequisites.

### Changes

- Include dependency licenses, notices and a documented encoder build process.
- Add package checks for unexpected dependencies or changed bundled files.
- Replace two icons with original MIT-licensed artwork.

## 0.9.11 - Release preparation

### Changes

- Freeze the initial release's feature set and review installation/performance guidance.
- Add repeatable package checks for included files, version numbers and download checksums.
- Confirm that normal replacement retains the existing ComicRack entry after restarting.

## 0.9.10 - Prefetch follow-up

### Changes

- Show whether prefetch was used and whether the next book was ready in conversion reports.
- Keep prefetch optional and off by default because measured benefits were small.

### Fixes

- Avoid starting an unnecessary cleanup process when the conversion worker has already removed its prefetched files. Keep fallback cleanup when needed.

## 0.9.9 - Performance choices

### Features

- Offer 1, 2, 4, 6, 8, 10 and 12 page workers, with one worker as the default.
- Add Quick and Thorough benchmarks showing conversion speed, CPU use, estimated RAM, file activity and time spent at each stage.
- Add remembered Normal/Background priority and optional local prefetch of the next archive.

### Changes

- Speed up CBZ validation by checking multiple pages within the selected worker and memory limits, while retaining all integrity checks.

## 0.9.8 - Long filenames and size-policy skips

### Features

- Use **Skipped - size policy** when a converted book does not meet the chosen savings requirement, keeping it separate from other skips.

### Changes

- Document an optional smart list for these informational skips.
- List missing, unexpected and duplicate archive entries when validation fails.

### Fixes

- Allow ImageMagick conversion of deeply nested extracted pages, including when temporary storage is on the NAS.

## 0.9.7 - Separate Run history window

### Fixes

- Open Run history in a separate process so a history-window failure does not close ComicRack.
- Report history startup failures and save diagnostics for troubleshooting.
- Preserve unsaved options and require an explicit start when preparing a new test from history.

## 0.9.6 - Dark table headers

### Fixes

- Replace bright table headers and unused header space with muted grey in dark mode. Light mode retains normal Windows headers.

## 0.9.5 - Dark window frames and tabs

### Fixes

- Use dark title bars and subdued window borders where Windows supports them.
- Remove bright tab borders in dark mode.

## 0.9.4 - History navigation

### Fixes

- Close the options dialog before opening history, then restore unsaved choices when returning.
- Improve window ownership and history diagnostics while investigating intermittent crashes. Further isolation followed in 0.9.7.

## 0.9.3 - Softer dark controls

### Fixes

- Replace bright dropdowns, buttons and tab backgrounds with darker shades.
- Keep disabled labels readable and preserve normal keyboard controls.
- Improve control initialization when opening nested windows.

## 0.9.2 - Appearance and setup

### Features

- Add remembered dark mode across plugin windows.
- Add search, wrapping and clearer headings to the technical report viewer, preserving all saved and copied details.

### Changes

- Check WinRAR availability during setup and explain that it is needed only for CBR output.
- Clarify Pillow's validation/preview requirement and update workflow screenshots and smart-list recipes.

## 0.9.1 - Workflow and long runs

### Features

- Add WebPStatus and WebPReason values for ready, completed, copied, skipped and failed books.
- Add setup checks, a pre-run storage summary and review of interrupted attempts.
- Add an optional Keep PC awake setting during processing.

### Changes

- Show extraction, page conversion, rebuilding, validation and replacement stages during processing.
- Preserve completed-work recognition across compatible updates.

### Fixes

- Prevent retries while a helper is active, files have changed or unresolved output/recovery files remain.
- Limit the wait for free-space checks on remote storage so the interface does not wait indefinitely.

## 0.9.0 - Pre-release testing

### Changes

- Add MIT licensing, third-party notices, GitHub documentation and contributor guidance.
- Reserve 1.0.0 for the first public stable release.

### Fixes

- Update quality-test speed and remaining-time estimates after each successful quality pass.
- Reduce nested history-window work and add diagnostics while investigating ComicRack crashes.

## 0.8.0 - Performance and batch recovery

### Features

- Add 1/2/4 page workers while processing books one at a time.
- Save per-book progress to resume matching work, recognize size-policy skips and review interrupted output.
- Add source throughput, rough remaining time and stage timings to reports.
- Add contributor guides and keep personal/generated files out of source packages.

### Changes

- Avoid extra ZIP compression of already compressed images and combine archive validation work.
- Begin converting books without first scanning the entire batch.

### Fixes

- Repair ComicRack paths when replacement changes a book's extension.
- Identify leftover temporary files when cleanup fails and request a safe stop.

## 0.7.0 - Run history

### Features

- Reopen reports and retained previews, or prepare a new quality comparison from saved settings.
- Save run summaries alongside text reports and list reports even when a summary is missing or damaged.
- Open history from options or a standalone library action without selecting comics.

### Changes

- Keep previews by default when reopening saved results, with an explicit deletion option.

### Fixes

- Give reports unique names so runs started in the same second cannot overwrite one another.

## 0.6.0 - Core workflow and previews

### Features

- Analyze selected CBZ/CBR books, create converted copies or replace originals after validation.
- Offer Q60-Q90 with ImageMagick as the default encoder.
- Compare Q60/Q70/Q75/Q80/Q90 on up to three sampled books.
- Add a full-screen viewer with linked scrolling, mouse-wheel shortcuts and color-managed previews.
- Remember settings, stop safely and save partial-run reports.
- Optionally delete previews when results close, keeping text reports.
- Separate release files from development tools and test assets.
