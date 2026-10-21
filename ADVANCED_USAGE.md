# Advanced usage and troubleshooting

Start with the [quick start in the README](README.md#quick-start). This guide keeps the storage, report and recovery details available when you need them.

## Preview storage and cleanup

Preview files are saved in `Reports/QualityTests/<run-id>` inside this plugin folder. PNGs are lossless display copies of decoded WebP pixels and retain color profiles; captions use actual WebP sizes. These PNGs can be much larger than the WebPs.

**Delete this run's preview images when closing this results window** is checked by default. Leave it checked to remove that run's JPEG/WebP/PNG samples and manifest when closing results, including with X. Uncheck it to keep the run; the preference is remembered. Closing only the comparison popup does not delete previews, so you can reopen it from results. Text reports are retained. Cleanup failures show the remaining folder path. An app/process crash can leave previews behind for manual cleanup later.

This option only deletes the current generated run under `Reports/QualityTests`; it does not clear older runs, source comics, reports or backups.

## Storage, stopping and reports

Storage & advanced lets you choose a temporary work folder. Blank uses each source directory. Final comic output remains beside the source. Temporary space is still required even when replacing without a retained backup.

**Stop after current book** finishes the active book safely, then saves a partial-run report. During a quality test, it finishes all five quality passes for that book. Later books are marked not processed. Closing the progress window requests the same safe stop.

The results screen shows weighted total reductions and per-book outcomes; full details are in Technical report. Central text reports and structured `.run.xml` history records are kept in `Reports`. You can also save full run reports beside source files. Copy/test results and retained backups do not themselves reclaim the displayed savings from disk.

Options are remembered in `settings.xml` when starting a run. Restore defaults resets the dialog; Cancel leaves saved options unchanged.

## Performance and large batches

**Performance & resume → Concurrent pages** offers 1, 2 or 4 encoders within the active book. One is the conservative default. Try two first, then compare four on a small selection. More workers need more RAM, especially for large scanned pages. Book processing remains sequential, and safe stopping still waits for the active book. ImageMagick's internal thread count is limited to one per encoder when multiple page workers are selected.

For NAS collections, choose a local **Temporary storage** folder on Storage & advanced. Extraction and page conversion then use the local drive; the original still comes from the NAS and final output is staged beside it. Local work storage is optional. Blank continues to use each source folder. Ensure both locations have space for the active book; you do not need room for temporary copies of the entire collection.

Normal copy/replace runs scan one book immediately before processing it, avoiding a full-selection scan before conversion begins. Quality comparisons still inspect the selection to choose spaced eligible samples, then run all five quality levels fresh.

CBZ creation stores already compressed JPEG/PNG/WebP members directly and compresses XML/text. Validation checks member CRCs, hashes and image decoding in one archive-read pass. Image encoding quality and metadata checks are retained; ZIP storage can make an archive slightly larger than additionally deflating those same image bytes.

The progress window shows source MB/s and a rough remaining-time estimate after a completed conversion. Progress and ETA use cached ComicRack sizes when available and fall back to book count when sizes are unavailable. Progress advances at book boundaries; it does not measure individual page completion. Quality tests show speed after the first successful quality pass and estimate the remaining passes across the sampled books. Their throughput counts each quality pass separately. Eligibility, page complexity and NAS conditions can change the estimate. It does not scan the whole NAS just to calculate an ETA. Technical reports include stage timings; totals include extraction, encoding, rebuilding and validation, with scan and replacement timings listed separately for normal runs.

### Continuing after a stop or restart

Leave **Resume completed books with matching settings and unchanged files** enabled. Select the original batch or its remaining books in ComicRack, review the same conversion choices, then start. There is no background scheduler or automatic selection of old sources.

Before each normal conversion, a pending checkpoint is saved under `Reports/Checkpoints`; successful completion is saved after replacement/library-update calls. Records include paths and measured results. Matching completed files are skipped without encoding again, and resumed work is not counted as newly reclaimed space. Books previously rejected by the same size policy are also recognized. Failed attempts are retried only when they leave no ambiguous output or recovery record.

Resume checks source/output sizes and modification timestamps, conversion settings and the installed implementation revision. These are conservative identity checks, not full content hashes or file locks. Changing worker count or work storage does not invalidate completed work; changing quality, resize, encoder, CBR handling, size policy, backup choice or plugin implementation does. Keep the records if you want resume recognition. Older runs made before checkpoint support cannot be reconstructed as checkpoints from their reports.

A completed CBR-to-CBZ checkpoint can recognize the new path and repair a selected old library path if the old file is missing and the recorded final file is unchanged. An unfinished attempt, corrupt checkpoint or unresolved replacement recovery record is reported for inspection; its output is never automatically installed or deleted. An unknown interrupted attempt requires review even if its output does not exist yet: a helper may still be encoding after ComicRack closes. Pending-attempt checks also apply when you disable completed-book reuse or change conversion settings. Do not start concurrent optimizer sessions against the same files.

For an interrupted attempt, the report identifies its pending XML and planned output. Confirm that its helper/encoder has stopped and inspect the source, output and any replacement recovery record first. Once the attempt is resolved, remove only that pending XML and its policy XML (the `policyRecord` attribute gives the exact path), then retry the selected book. Keep completed checkpoints. Merely clearing a checkpoint does not repair a failed replacement or remove leftover work files.

If temporary cleanup fails, the report identifies the remaining work folder and processing stops after the active book. A force-close or crash can leave temporary pages and outputs; checkpoints do not automatically purge them or guarantee recovery from every network/power failure. Final text reports are still written on completion or graceful stop; per-book checkpoint XML provides durable completed-work records between those points. Preview cleanup does not delete checkpoints.

For your first large run, use a manageable batch with your chosen worker count and local storage, then inspect timings and free space. Copy mode and retained backups keep the originals, so they do not reclaim the reported savings.

## Replacement recovery

Replacement preserves recoverable files on failure and writes a `<source>.webp-recovery.txt` record before changing filenames. If an operation fails, inspect the report and named source/converted/rollback paths before retrying. An unresolved recovery record blocks another replacement. CBR-to-CBZ replacement refuses to overwrite an existing CBZ. Recovery is not a guarantee against every power-loss or network failure.

Start with a small disposable selection before a large replacement batch. Earlier local/NAS and reader workflow tests passed for the development installation; clean-machine installation and broader environments remain to be verified.

## Folder layout

| Location | Purpose | Included in release ZIP? |
|---|---|---|
| Root Python files, icons, package metadata and docs | Plugin runtime and user instructions | Yes |
| `Magick` | Bundled encoder, dependencies and supplied license | Yes |
| `quality_estimates.txt` | Reference sample reductions | Yes |
| `settings.xml` | Your saved choices | No |
| `Reports` | Your run reports and optional previews | No |
| `Development` | Tests, fixtures, calibration lab and implementation history | No |
| `Releases` | Generated distribution ZIP and checksum manifest | No |

Development commands and packaging instructions are in `Development/README.md`.

## Run history

Open **Run history** from Optimize Archives, or use the standalone **WebP Optimizer Run History** library action without selecting comics. Viewing history does not require Python, 7-Zip or an encoder to be available.

History lists date, action, processed-book count, run status, measured reduction and preview status. Open results reopens the native report; Open previews reopens retained native comparison images. Refresh updates the list after filesystem changes. Available means usable native preview images exist; Removed means a recorded cleanup removed them; Unavailable means files are missing, incomplete or from an older HTML-only run. A dash means no preview folder was recorded. Deleting previews removes only the selected run's generated preview folder and preserves the report.

**Historical results always start with Delete previews on close unchecked**, regardless of the default for new results. Reviewing old results will not delete their images. You may explicitly check the box or use Delete previews in history to remove them.

New runs save a `.run.xml` file beside the text report, including summary data, relevant options and source paths. Missing or damaged records fall back to the text report header; old reports therefore remain visible with whatever data is available. XML records contain personal paths and are excluded from release packages along with all Reports content. The history list reads only short headers for legacy reports rather than loading entire detailed reports.

From history opened through Optimize Archives, **Prepare new test** fills in recorded encoder/CBR/work-folder choices, selects Test savings & quality and enables preview retention. It does not convert anything or automatically reselect old files. Review the current ComicRack selection and settings, then explicitly start a new run. Source files may have changed since the old run, so results are recorded separately. The standalone library history view is for reviewing/deleting previews; open history through Optimize Archives to prepare a new test.

If a preview folder was removed, the report can still reopen but those images cannot be recovered from the report alone. Run a new comparison to recreate them. Report history is retained until its files are explicitly removed; there is no automatic report purge.

If opening history fails, check `Reports/history-diagnostic.log` for the last recorded stage. The current 0.9 path defers opening/loading and guards repeated clicks; the reported ComicRack stack overflow still needs confirmation in the live application after restarting.
