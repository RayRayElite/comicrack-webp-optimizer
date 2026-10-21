# Code map

Start with the user workflow in [README.md](README.md), then use this map to find the implementation. Section IDs are searchable comments in the source; function names are better references than line numbers as the files grow.

## Two Python runtimes

`WebPOptimizer.py` runs inside ComicRack's IronPython environment using Python 2 syntax and .NET WinForms. It owns selection, user interaction, ComicRack metadata, reports and replacement of originals.

`webp_convert_helper.py` is a separate CPython 3 process. It uses Pillow and external archive/encoder tools to produce and validate one new archive. It does not replace the original. Do not import it into the ComicRack script or add Python 3 syntax to the adapter.

## Native adapter: WebPOptimizer.py

| Marker | Responsibility |
|---|---|
| P01 | Paths, option labels, quality levels and run guard |
| P02 | Unicode, XML and display utilities |
| P03 | Dependency discovery and external process execution |
| P04 | Archive listing and eligibility analysis |
| P05 | Output paths and collision policies |
| P06 | ComicRack metadata access and serialization |
| P07 | Helper arguments and result protocol |
| P08 | Library updates and validated source replacement |
| P09 | Report summaries and quality-test comparisons |
| P10 | Report headers and persistent run history |
| P11 | Preview cleanup, settings and summary utilities |
| P12 | Shared WinForms construction helpers |
| P13 | OptionsForm: choices, defaults and remembered settings |
| P14 | ProgressForm: progress and safe-stop requests |
| P15 | PreviewScrollPanel and comparison viewer |
| P16 | RunHistoryForm: review and prepare another test |
| P17 | ReportForm: results, details and preview ownership |
| P18 | Run orchestration |
| P19 | ComicRack hook metadata and entry points |
| P20 | Atomic per-book checkpoints and selected-file resume |

## Conversion worker: webp_convert_helper.py

| Marker | Responsibility |
|---|---|
| H01 | Command-line arguments and shared image policy |
| H02 | Quality parsing and tool selection |
| H03 | Resize and output-size policies |
| H04 | Extraction and page discovery |
| H05 | Encoder implementations and color handling |
| H06 | Page conversion |
| H07 | Archive rebuilding and metadata |
| H08 | Output validation |
| H09 | Structured results and worker entry point |

## One run, from selection to report

1. The ComicRack hook opens options for the selected books. Starting saves settings and establishes the run guard.
2. Normal conversion runs inspect and process one archive at a time, checking completed-work records before scanning. Quality trials inspect the selection first to choose spaced eligible books. Analysis-only runs update filtering values without conversion.
3. For conversion, the adapter supplies source/output paths, options and metadata to the worker as command-line arguments.
4. The worker extracts into temporary storage, converts JPEG pages, rebuilds an archive and validates it. Existing WebP and other preserved files are not recompressed by the JPEG conversion step.
5. The adapter records the result. Copy mode retains a separate output; replacement mode installs validated output and updates the existing library entry. Quality-test mode measures all five levels and removes test archives while optionally retaining page previews.
6. The adapter saves a text report and structured history record, then opens results. Preview deletion belongs to results/history, not the comparison popup.

Process output is drained asynchronously while the UI pumps events. Callbacks collect output; UI work stays in the adapter's UI flow. The run guard prevents event pumping from starting another conversion run. Stop requests finish the active book; quality tests finish its five passes before stopping. This is cooperative stopping, not process termination.

Quality progress is planned from the sampled books, with five pass sizes per book. P09 calls P14's begin/record methods for every pass; only successful timed passes feed throughput. ETA covers remaining comparison passes and is independent of the full selection count. Keep the active-book stop boundary even when pumping events between qualities.

History opening from P13 is queued with BeginInvoke, guarded against repeated clicks, and passes a concrete CLR NativeWindow owner to modal dialogs. P16 defers record loading until the dialog is shown and suppresses selection updates while populating rows. Normal failures are contained, and Reports/history-diagnostic.log records the last stage. A stack overflow cannot be caught as an ordinary Python exception; passing isolated modal tests is not proof that a live-host crash is resolved.

## Helper communication

The CLI in `build_parser()` is the input contract. The worker writes `KEY=value` lines to stdout; `_parse_helper_output()` splits at the first equals sign and retains fields as strings. Keep stdout for this protocol. Diagnostics belong on stderr or in explicit result fields.

Worker outcomes include `OK`, `SKIPPED` and `ERROR`. The adapter also represents books not processed after a stop. Check both process completion and structured results when changing error handling. Coordinate new arguments or result fields between P07 and H01/H09, and update tests that consume them.

`--page-workers` accepts 1, 2 or 4. H06 preflights all page collisions before dispatching bounded thread workers. Each worker owns distinct temporary page paths; executor shutdown waits for active work even on an error. ImageMagick's internal thread limit is set for multi-worker CLI runs to avoid multiplying encoder thread pools. No ComicRack APIs run on worker threads. Encoded members must stay identical across concurrency settings.

`TIME_*_SECONDS` fields are emitted through cleanup, including on conversion errors. Wait for process exit and drain all output rather than treating the first STATUS line as the end. CRC verification happens during member reads in H08; do not restore a redundant full testzip pass or remove CRC/hash/decoding checks. H07 stores compressed image members directly and deflates other members.

## Files and ownership

| Artifact | Owner and lifetime |
|---|---|
| Source comic | Adapter controls replacement; worker reads it |
| Extracted pages | Worker temporary storage, cleaned when work ends |
| New archive | Retained as copy, installed as replacement, or removed after a quality test |
| Metadata input files | Adapter supplies them to the worker and cleans temporary inputs |
| settings.xml | Remembered local choices; not distributed |
| Reports/*.txt | Retained human-readable reports |
| Reports/*.run.xml | Structured history, options and personal source paths |
| Reports/Checkpoints | Per-book intent, completed results and size-policy skips; personal paths |
| Reports/QualityTests/run-id | Optional JPEG/WebP/PNG samples and preview manifests |
| Recovery record beside source | Replacement recovery information; inspect after a failure |

The history XML is versioned. Missing or damaged records fall back to bounded reads of legacy report headers. Report labels used by legacy parsing are compatibility-sensitive. Settings currently store some display labels, so renaming options requires considering migration rather than just changing visible text.

Checkpoint XML is separate from run-history XML. P20 partitions completed records by conversion policy and implementation file signatures. Paths are hashed for record names, but record contents are personal. Pending records also have a policy-independent index so changing quality cannot bypass an unfinished-attempt check. Missing output does not prove an orphan helper has exited; unknown pending attempts always require review. A normally returned failed helper with no output/recovery journal can be marked retryable. Writes use temporary files and same-path replacement. Successful completion is recorded after library-update calls; extension changes create a final-path alias. Resume verifies file size/mtime identities and can relink an old selected path after a completed extension change. It never auto-selects books, installs an uncertain output or counts historical savings again. A checkpoint write failure prevents new work or stops after active-book completion. Keep this distinct from the source-side replacement recovery journal.

Preview PNGs are lossless decoded WebP display assets, with color profiles retained. The viewer loads images with color management. Display scaling, profiles and reader behavior can still affect visual comparisons; use 100% for pixel inspection. Preview cleanup accepts only a direct generated run directory under `Reports/QualityTests` and rejects unsafe targets. Reports survive preview cleanup.

## Safety boundaries to preserve

- Never remove a source before a validated replacement is available. Same-path replacement and extension-changing replacement have different rollback paths in `_finalize_replacement()`.
- Keep output collision checks, recovery records and source size/mtime checks. Size/mtime checks are not a file lock or a guarantee against every concurrent edit or network failure.
- Preserve metadata and unchanged archive members. Validate page names, counts, dimensions and archive contents before reporting success.
- Keep copy/test modes from relinking the existing library entry. Only replacement should update its source path.
- Keep test preview cleanup separate from archive and report cleanup. Do not broaden its accepted directory scope.
- Treat weighted savings as total bytes saved divided by comparable source bytes, not an average of individual percentages. Copy/test savings are potential savings until originals are replaced.

## Common extension points

| Change | Read and update together |
|---|---|
| New quality or preset | P01/P13, H02, estimates and quality-test labels/tests |
| New encoder | P01/P03/P07, H02/H05, profile preservation and encoder tests |
| New remembered option | P11/P13, worker CLI if needed, history serialization and defaults |
| New report metric | P09/P10/P17, history parsing and weighted calculations |
| Preview interaction | P15; preserve synchronized views and image disposal |
| New release file | Development/build_release.py explicit allowlist |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and verification limits.
