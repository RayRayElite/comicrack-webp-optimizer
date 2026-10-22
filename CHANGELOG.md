# Release notes

## 1.0.0 - 2026-10-22

First public stable release of WebP Optimizer for ComicRack Community Edition.

- Analyze CBZ/CBR archives and populate ImageFormat, WebPStatus and WebPReason for smart-list workflows.
- Convert eligible JPEG pages at Q60-Q90 with validated copy or replacement, metadata/reading-progress preservation and optional backups. Existing WebP pages are not recompressed.
- Compare five quality levels in a native viewer with synchronized zoom/scroll, pixel inspection and optional RGB measurements/8x difference heatmap.
- Support 1-12 page workers, measured worker benchmarks, local temporary storage, Background priority and optional bounded prefetch. Conservative defaults remain Q80, original dimensions, one worker, Normal priority and prefetch off.
- Include safe stopping, matching completed-work recognition, interrupted-work review, reports/history, preview cleanup, dark mode and remembered settings.
- Bundle a minimal static Windows x64 ImageMagick encoder with matching third-party notices and pinned build provenance. Python/Pillow remain separately installed prerequisites; WinRAR is needed only for CBR output.
- Include reviewed user/contributor documentation and sample UI screenshots. Installation packages exclude personal reports/settings, comic fixtures and compiler tools.

Validated with generated archive/native UI/package checks and user testing of copy/replacement, NAS, CBR-to-CBZ and reader workflows. This does not establish compatibility with every installation or source image.

## Development history

The entries below are pre-release milestones. Earlier local 1.x filenames were internal numbering, not previous public stable releases.

## 0.9.13 - 2026-10-22

Final authorized feature before the 1.0 candidate acceptance pass:

- Optional full-resolution preview difference analysis: mean absolute RGB change, RMS error, maximum channel change, signed RGB brightness estimate and changed-pixel percentage.
- An explicitly amplified 8x difference heatmap and synchronized coordinate/RGB inspector work with the existing zoom/scroll controls.
- Analysis runs off the UI thread on detached color-managed bitmap snapshots, with no extra files, dependencies or normal conversion overhead. Page/quality changes release results; closing abandons the job safely. Matching dimensions and a 16-million-pixel memory limit are enforced.
- Known identical/localized changes and real asynchronous viewer lifecycle are covered by native tests. These diagnostics measure pixel changes, not perceptual quality percentages.
- Refresh release documentation, shorten the README landing page, preserve smart-list screenshots in Advanced Usage and update build/contributor guidance for the final feature set.

## 0.9.12 - Self-contained encoder and redistribution materials (prerelease)

- Bundle a minimal static ImageMagick 7.1.2-34 Q8 Windows x64 build with JPEG/WebP/Little CMS. Remove the need to ship loose Microsoft Visual C++/OpenMP DLLs or the large optional delegate set. Python/Pillow remain prerequisites.
- Include exact upstream license/notice files, required JPEG attribution, WebP patent grant, MinGW notices and GCC runtime linking exception, with pinned input and binary/license hashes and a documented build recipe.
- Reject mismatched encoder provenance, changed license files and unexpected non-system DLL imports during packaging. Preserve the old encoder/DLLs privately for comparison.
- Replace two legacy icons of undocumented origin with original MIT-licensed vector-based artwork.
- Candidate comparisons produced 20/20 byte-identical outputs against the old encoder across RGB/gray/CMYK/Adobe RGB, Q60-Q90 and resize; helper/archive concurrency checks also passed. Final live acceptance remains required; no 1.0 release is published by this preparation.

## 0.9.11 - Feature freeze and release-readiness audit (prerelease)

- Freeze the 1.0 feature set; no conversion behavior, defaults or checkpoint policy changes.
- Record live confirmation that normal replacement retains the same ComicRack entry after restart. The earlier manually restored-file path problem is not a reproduced normal-replacement defect.
- Refresh installation/performance documentation and prepare a plugin-only packaging option with upstream encoder prerequisites, alongside local bundled-tools testing drafts.
- Add repeatable artifact audits for exact allowlists, current file contents, versions, CRCs and SHA-256 manifests. Fresh-user installation acceptance and bundled-binary redistribution review remain explicit release gates.

## 0.9.10 - Prefetch comparison follow-up (prerelease)

- Avoid a redundant Python cleanup process after each consumed cache when the conversion worker acknowledges cleanup of that exact manifest. Missing acknowledgements retain guarded fallback cleanup; safe-stop cleanup remains.
- Include per-book prefetch usage, next-cache readiness, manifest cleanup acknowledgements and fallback notes in conversion reports, plus summary counts for caches used/prepared.
- Keep prefetch optional and disabled by default. Live copy-mode comparisons showed only a nominal benefit; repeat the same workload with this startup overhead removed before deciding whether to retain the feature.

## 0.9.9 - Measured performance choices (prerelease)

- Expand page workers to 1, 2, 4, 6, 8, 10 and 12; retain the one-worker default and existing completion-checkpoint compatibility.
- Add native quick/thorough worker benchmarks at fixed quality with full conversion throughput, process CPU, estimated RAM, logical I/O and stage timings. Apply recommendations explicitly; tests keep originals and library values unchanged.
- Add remembered Normal/Background CPU priority and opt-in bounded local prefetch of one next compressed archive, with cache checksums, source guards and exact cleanup.
- Overlap ZIP hash/decode validation within the selected worker and buffer budgets while retaining manifest, CRC, content and image-decode checks. CBR checks stay unchanged.
- Generated 24-page conversions at all seven counts produced identical encoded members and preserved ICC profiles/attachments. Cache handoff, cancellation, corruption, cleanup and native benchmark checks cover disposable fixtures only; real ComicRack/NAS acceptance remains required.

## 0.9.8 - Long filenames and explicit size-policy skips

- ImageMagick uses binary input/output file handles to avoid filename API limits on long extracted paths, including NAS-only temporary storage. Encoder settings, ICC handling and page names remain unchanged.
- Manifest errors retain strict rejection and now list expected/actual counts plus every missing, unexpected and duplicate member.
- WebPStatus distinguishes `Skipped - size policy` from other `Skipped` outcomes. Unchanged legacy size-policy outcomes migrate during Analyze Only, without encoding; checkpoint reuse preserves the distinct reason.
- Optional smart list for informational size-policy skips documented. The Ready conversion list is unchanged.
- Generated >300-character Unicode/bracket-path checks verify identical encoded bytes, profile/dimensions, exclusive output creation and unchanged source data. Existing completed-work compatibility remains unchanged.
- No concurrency, GPU or prefetch changes in this build. Older ambiguous outputs still require explicit recovery review.

## 0.9.7 - Isolate history from ComicRack

- New live diagnostic evidence places the recurring ComicRack failure during history-record loading; earlier in-process navigation changes did not resolve it.
- Both history entry points now use an independent hidden-console STA PowerShell/IronPython host. History, historical reports and retained previews stay outside ComicRack's process; there is no in-process fallback.
- Prepare new test returns only whitelisted settings through a per-session XML result. Unsaved options, current selection and explicit-start behavior are preserved.
- Helper startup failures and abnormal exits are reported without terminating the caller. Exact request/response files are cleaned; failure details go to Reports/history-helper-error.log.
- Ten real helper launches, Unicode retest round trip, forced abrupt helper exit followed by successful reopening, unchanged settings/reports and no-parent-browser checks passed.
- Live ComicRack confirmation is still required; no claim that the original runtime fault itself has been diagnosed or repaired.

## 0.9.6 - Dark table headers

- Results, history, preflight and recovery tables use muted grey column headers with readable text and subdued separators, including unused header space.
- Native row rendering/selection and column interaction remain intact; light mode restores the normal Windows header.
- Header pixel checks cover the empty strip and resizing, alongside existing history and UI regressions.

## 0.9.5 - Dark window frames and tab edges

- Dark mode now requests a dark Windows title bar for each plugin dialog, with muted grey caption/border colors where supported. Light mode restores system defaults.
- Repaint native tab-header bevels in subdued grey after Windows' paint pass, including the selected-tab border.
- Caption updates follow window handle creation/recreation without replacing window procedures, changing system preferences or altering history navigation.
- Native dark/light caption readback and style-change checks added; unsupported Windows attributes are ignored safely.

## 0.9.4 - History navigation crash mitigation

- Run history returns from and disposes the options dialog before opening history; closing history restores unsaved choices without starting a run or saving settings.
- Prepare new test still restores recorded choices for the current selection.
- Owned report dialogs use a passive CLR handle owner instead of subclassing the parent's window procedure with NativeWindow.AssignHandle.
- Bounded append diagnostics retain the opening sequence and process name/ID instead of overwriting the last stage.
- Ten repeated small-stack navigation cycles, settings/draft preservation and owned-report regression checks. The intermittent live ComicRack crash remains awaiting user confirmation after restart.

## 0.9.3 - Softer dark controls

- Dark dropdown faces and popup items, including disabled fields, replace Windows' bright native fill while preserving normal selection/keyboard behavior.
- Flat buttons use subdued borders and hover/pressed shades; disabled checkbox labels remain readable against charcoal backgrounds.
- Dark tab headers and frames remove bright native strips. Light mode retains standard Windows rendering.
- Initialize CLR controls before nested modal callbacks; regression checks cover disabled/active palettes and small-stack history opening.

## 0.9.2 - Presentation and setup clarity

- Optional remembered dark mode across native plugin dialogs; comic pixels remain unchanged.
- Technical report reader adds wrapping, search with next-match navigation and bold field/section labels without removing details from saved/copied reports.
- Setup reports WinRAR availability for every mode and distinguishes 7-Zip CBR input from optional WinRAR CBR output.
- Clarified that Pillow currently supplies validation and color-managed preview support for every conversion backend, in addition to its optional encoder.
- Updated quick-start workflow screenshots and all five smart-list recipes.

## 0.9.1 — Workflow and long-run testing

- `WebPStatus` and `WebPReason` custom values distinguish actionable work, completed replacements, retained copies, skipped books and problems without changing `ImageFormat` semantics.
- Tools & recovery tab checks selected workflow dependencies with disposable files and reviews interrupted attempts through read-only archive/page validation.
- Guarded Allow retry archives resolved tracking records, preserves media and refuses active helpers, changed files or unresolved outputs/rollback files.
- Pre-run selection/storage summary explains copy/backup retention and conservative per-volume budgets before work begins. Remote free-space queries have a bounded UI wait.
- Live extraction, page-encoding, rebuild, validation and replacement stages in the processing window; progress callbacks run on the UI thread.
- Versioned conversion-policy checkpoints survive compatible updates and display-label changes. Legacy pending attempts remain reviewable; older completed records without verified policy metadata are not guessed or migrated.
- Optional remembered Keep PC awake setting prevents idle sleep during processing and restores previous thread requirements on completion, stop or error. The display may turn off.
- Native support code split into a documented IronPython module and a small in-memory Windows API bridge. Generated-fixture tests cover accepted/cancelled startup, setup failures, recovery protections, live progress and power-state restoration.
- Remains pre-release. Live history confirmation, backed-up collection testing and NAS testing precede 1.0 and the Reddit announcement.

## 0.9.0 — Pre-release testing

- History opening deferred until the options click returns; a concrete CLR dialog owner, re-entry/refresh guards and deferred loading reduce nested UI work. Last-stage history diagnostics added. Live confirmation of the reported ComicRack stack-overflow crash is still required.
- Quality-test speed and rough ETA now update after each successful quality pass and cover remaining sampled passes. Added an actual three-book/fifteen-pass native regression test.
- RayRayElite author credit, MIT licensing for plugin code, third-party notices and source-only GitHub packaging.
- GitHub README with project origin, acknowledgements and contribution guidance; private release checklist and first-person Reddit announcement draft.
- Public release numbering reset: 0.9.0 for testing, 1.0.0 reserved for the first stable release.

## 0.8.0 — Performance and batch recovery

- Configurable 1/2/4 page workers within a sequential book workflow; explicit encoder behavior and color profiles retained.
- CBZ image members stored without extra ZIP compression; member CRC/hash/decoding validation consolidated into one archive-read pass.
- Normal runs scan and convert each book in turn instead of scanning the complete selection first.
- Per-book pending/completed checkpoints, matching-file resume, size-policy skip reuse and extension-change library-path repair.
- Policy-independent interrupted-output checks; ambiguous outputs and recovery records require inspection.
- Performance & resume options, source throughput, rough ETA and stage timings in reports.
- Temporary cleanup failures identify remaining work storage and request a safe stop.
- Contributor guides, searchable runtime sections and function documentation; personal/generated files excluded from Git by local ignore rules.
- Generated-comic worker benchmarks and native interruption/resume regression coverage.

## 0.7.0 — Run history

- Run history opens prior reports and available native previews.
- Historical results preserve previews by default; previews can be deleted explicitly.
- New runs save structured XML history records alongside text reports.
- Legacy text reports remain discoverable, including when an XML record is missing or damaged.
- Prepare a new quality comparison from recorded settings for review against the current selection.
- History is available from the options window and a standalone library action without requiring selected comics or conversion dependencies.
- Unique report filenames prevent same-second runs from overwriting one another.

## 0.6.0 — Core workflow and previews

- Selected-book analysis, copy and validated replacement for CBZ/CBR sources.
- Q60–Q90 conversion choices with explicit ImageMagick default.
- Q60/Q70/Q75/Q80/Q90 quality trials on up to three spaced eligible books.
- Native full-screen comparison, synchronized scrolling and modifier-wheel controls.
- ICC profile retention and color-managed previews.
- Remembered settings, safe stopping and partial-run reports.
- Optional preview deletion when the results window closes; text reports retained.
- Runtime-only release packaging; development tools and test assets separated.

This package still needs a clean-machine install check. Automated/native fixture tests and earlier user workflow checks do not establish compatibility with every ComicRack installation or NAS.
