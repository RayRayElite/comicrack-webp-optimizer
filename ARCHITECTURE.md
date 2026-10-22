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
| P15 | Comparison viewer, synchronized navigation, pixel inspector and optional difference analysis |
| P16 | RunHistoryForm: review and prepare another test |
| P17 | ReportForm: results, details and preview ownership |
| P18 | Run orchestration |
| P19 | ComicRack hook metadata and entry points |
| P20 | Atomic per-book checkpoints and selected-file resume |
| P21 | Load native runtime and performance support modules |

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

P13 returns DialogResult.Retry when history is requested. S06's controller disposes options before launching the independent history host, then recreates options from the unsaved draft. Owned report dialogs use a passive CLR IWin32Window handle; they never subclass the parent window procedure. P16 defers record loading until the dialog is shown and suppresses selection updates while populating rows. Normal failures are contained, and Reports/history-diagnostic.log retains bounded append entries with process identity. A stack overflow cannot be caught as an ordinary Python exception. The user has confirmed history working after process isolation; isolated tests do not establish behavior in every live host.

## Helper communication

The CLI in `build_parser()` is the input contract. The worker writes `KEY=value` lines to stdout; `_parse_helper_output()` splits at the first equals sign and retains fields as strings. Keep stdout for this protocol. Diagnostics belong on stderr or in explicit result fields.

Worker outcomes include `OK`, `SKIPPED` and `ERROR`. The adapter also represents books not processed after a stop. Check both process completion and structured results when changing error handling. Coordinate new arguments or result fields between P07 and H01/H09, and update tests that consume them.

`--page-workers` accepts 1, 2, 4, 6, 8, 10 or 12. H06 preflights all page collisions before dispatching bounded thread workers. Each worker owns distinct temporary page paths; executor shutdown waits for active work even on an error. ImageMagick's internal thread limit is set for multi-worker CLI runs to avoid multiplying encoder thread pools. No ComicRack APIs run on worker threads. Encoded members must stay identical across concurrency settings.

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

Checkpoint XML is separate from run-history XML. P20 partitions completed records by conversion policy and explicit CHECKPOINT_POLICY_VERSION. Paths are hashed for record names, but record contents are personal. Pending records also have a policy-independent index so changing quality cannot bypass an unfinished-attempt check. Missing output does not prove an orphan helper has exited; unknown pending attempts always require review. A normally returned failed helper with no output/recovery journal can be marked retryable. Writes use temporary files and same-path replacement. Successful completion is recorded after library-update calls; extension changes create a final-path alias. Resume verifies file size/mtime identities and can relink an old selected path after a completed extension change. It never auto-selects books, installs an uncertain output or counts historical savings again. A checkpoint write failure prevents new work or stops after active-book completion. Keep this distinct from the source-side replacement recovery journal.

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

## Native runtime support

P21 explicitly loads `webp_runtime_support.py` into the adapter namespace. This IronPython 2 source shares the adapter's UI helpers and test seams: S01 workflow labels, S02 Windows APIs, S03 pre-run review, S04 setup diagnostics and S05 interrupted-work review. Keep it compatible with Python 2; the conversion worker remains CPython 3.

`NativeWindows.cs` is compiled in memory during support initialization. Its bounded C# background query handles potentially slow disk-space I/O without Python delegates. Sleep requests execute on the calling UI thread because Windows execution state is thread-local. Compiler temporary files are cleaned from Reports/RuntimeCache.

The worker emits `PROGRESS=STAGE|done|total`; the adapter queues events and updates controls on its UI flow. Progress messages are excluded from terminal result parsing. Setup/archive diagnostic modes reuse actual encoding and validation, without modifying source archives.

Checkpoint schema 2 uses an explicit compatibility marker. Bump CHECKPOINT_POLICY_VERSION when conversion semantics make prior results incompatible; do not tie it to display text or maintenance timestamps. Pending attempts remain independently indexed. Recovery checks require unchanged snapshots and no known active helper before archiving tracking records; archives themselves are never deleted or installed by this UI.

S06 applies an optional dark palette after each native dialog is constructed, keeping original control colors for reversal and leaving picture pixels alone. Constructor wrappers also cover dialogs opened from run history. Theme preference is a normal saved option; an unsaved preview is reset when options close. The technical reader uses RichTextBox for formatting/search/wrapping, while the authoritative report string remains unchanged for copying and saving. Native RichTextBox content may be absent from DrawToBitmap test renders; tests separately assert complete text and selection navigation.

The bridge also supplies ThemeComboBox, ThemeCheckBox and ThemeTabs. Windows ignores several palette properties on themed/disabled native controls, so these subclasses repaint faces, items and labels without replacing selection, keyboard or accessibility behavior. Light mode returns to standard rendering. The bridge compiles during support initialization, before entering nested modal callbacks; this avoids cold compiler binding on a nearly exhausted click stack. Buttons use standard flat styling with subdued borders and hover/pressed colors.

Title-bar styling uses DwmSetWindowAttribute on each plugin HWND (dark framing and optional caption/text/border COLORREFs), with HRESULT capability probing and safe fallback. HandleCreated/Shown refresh the current per-form preference without forcing early HWND creation or installing a window-procedure hook. Light mode resets custom colors to DWMWA_COLOR_DEFAULT. ThemeTabs repaints native header bevels after the native paint pass, preserving standard tab selection. Reference: https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute

ThemeListView handles the child header's NM_CUSTOMDRAW notifications (including reflected WM_NOTIFY) inside the CLR ListView subclass. PREPAINT fills the full row and requests item drawing; ITEMPREPAINT draws cells and returns CDRF_SKIPDEFAULT to suppress native white fills; POSTPAINT repaints the unused strip after Windows finishes drawing. It reads native header item rectangles so widths/reordering/scrolling stay aligned. Row rendering remains native, without OwnerDraw or a header-window NativeWindow hook. Dark mode includes empty header space; light mode passes notifications through normally. Reference: https://learn.microsoft.com/en-us/windows/win32/api/commctrl/ns-commctrl-nmcustomdraw

## Independent history host (0.9.7)

S07 locates the installed ComicRack IronPython runtime, writes a GUID-scoped request and launches history_host.ps1 with a hidden console and STA apartment. history_host.py runs in the adapter namespace inside that process. The parent never constructs RunHistoryForm; only the child loads history records and historical report/preview dialogs. Startup/abrupt-exit failures produce an ordinary parent error, with no in-process fallback. The processing run guard remains held while waiting.

IPC contains allow-retest/theme flags and the runtime location. Responses allow only encoder_backend, cbr_mode, page_workers and work_dir, parsed as XML with external resolution disabled. Request/response paths are exact generated files under Reports/HistorySessions; cleanup never removes a directory or comic. The helper script validates the request filename/location. Current selection and ComicRack library objects never cross the process boundary. History preview deletion remains explicit and uses the existing guarded cleanup.

The host loads the installation's existing CLR DLL bytes using the same isolated bootstrap as the test harness; no vendor runtime is copied into the release. A process-scoped execution-policy option supports the local launcher without editing machine/user policy. render_ui.ps1 -HistoryHostSmoke exercises true child termination and subsequent reopening, Unicode retest choices, exact cleanup and unchanged reports/settings. -ModalHistorySmoke now performs ten independent helper launches while verifying draft restoration and zero parent-browser construction.

ImageMagick transport uses binary stdin/stdout (`-` / `webp:-`) backed by Python-opened file handles, rather than absolute encoder filenames. This handles Windows/UNC long paths without loading an entire compressed page into a Python bytes buffer. Output is created exclusively. Q/resize/profile settings are identical; generated regression checks compare complete encoded bytes against the old short-path CLI. This transport/status/diagnostic change keeps CHECKPOINT_POLICY_VERSION unchanged so previous valid completions are reusable.

Manifest diagnostics JSON-escape complete filename lists to keep one-line helper protocol framing intact. Validation still rejects missing/extra/duplicate members before integrity/image checks; no transient-looking names are silently ignored. S01 distinguishes size-policy status during direct conversion/resume and upgrades only recognized legacy reasons with unchanged source stamps during analysis.

## Performance modules

`performance_support.py` is CPython-only: measured helper/child CPU, memory and logical I/O; CPU priority; and a bounded SHA-256-checked prefetch cache. Child tools are registered explicitly rather than discovered by name. Cache deletion validates the exact generated identity and refuses redirects or unknown files.

`webp_performance_ui.py` runs in the IronPython adapter namespace. B01 configures quick/thorough tests; B02 displays results; B03 compares complete equal workloads; B04 orchestrates disposable trials. It never calls library-tag, checkpoint or replacement writers. Options closes before opening these dialogs, preserving the history isolation pattern. Benchmark outputs are removed even when conversion fails; raw text/CSV measurements remain.

H08 reads ZIP members serially for CRC validation, then queues hash/decode checks with both worker and compressed-buffer limits. It joins all validators before temporary work cleanup. Page encoders have already joined, so these pools never multiply the selected worker budget.


## Preview difference diagnostics

[P15] in WebPOptimizer.py owns the controls, zoom-coordinate mapping and UI-thread completion polling. NativeWindows.cs contains PreviewDifference (row-buffer RGB metrics and heatmap) and PreviewDifferenceJob (snapshot ownership, background work and abandoned-result cleanup). Comparison uses the same detached color-managed bitmaps as the viewer, never screenshots. Results live only for the active pair; no disk cache or metadata writes occur. Brightness is an encoded-RGB weighted estimate, not linear luminance, Delta E or SSIM. Development/test_preview_difference.py covers known changes and native lifecycle.

## Encoder build and release ownership

The normal runtime ZIP includes the reviewed static Windows x64 ImageMagick encoder. Python/Pillow and optional external tools remain prerequisites. Development/encoder_sources.json pins upstream build inputs; build_encoder.py compiles in an isolated workspace; package_encoder.py stages exact notices and provenance; inspect_pe.py checks imported DLLs. Magick/build-info.json identifies the adopted binary and legal-file hashes. See [the encoder recipe](Development/ENCODER_BUILD.md).

Development/build_release.py owns the runtime allowlist, including NativeWindows.cs and all encoder notices. build_source.py exports the contributor tree without vendor executables/private data. audit_release.py checks artifacts against current source and manifests. New files must be added to the correct allowlists. Compiler workspaces, old binaries and private release-prep notes never enter those exports.
