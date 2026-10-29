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

Checkpoint schema 2 uses an explicit compatibility marker. Bump CHECKPOINT_POLICY_VERSION when conversion semantics make prior results incompatible; do not tie it to display text or maintenance timestamps. Pending attempts remain independently indexed. Recovery checks require unchanged snapshots and no known active helper before archiving tracking records; archives themselves are never deleted or installed by this UI. The reviewer supports multi-selection: each record is checked and resolved independently, selection changes clear the shared helper-stopped confirmation, and partial failures remain available in batch details. Results can open the reviewer with matching paths focused. Only current-run results can prepare a retry, matching successfully cleared paths back to captured ComicRack book references; historical reports cannot reconstruct library selections. Preparing returns to the normal options and preflight flow and does not start conversion.

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


## Extracted attributes and AppleDouble attachments

H04 normalizes only Windows read-only bits inside owned extraction storage, refusing redirected/outside paths. Main cleanup retries a read-only removal within the same boundary; unrelated permissions remain failures. No source archive attributes/ACLs change.

The adapter `_is_macos_sidecar` and worker `is_macos_sidecar` share a narrow path rule: `__MACOSX` directory component plus `._` basename prefix. These members retain their names/content as attachments and participate in manifest/hash/CRC checks, while image decoding/page counts skip them. Keep scan, worker discovery, output validation and read-only recovery checks aligned. Generated regressions live in test_archive_edge_cases.py and test_macos_scan.py.


## Atomic XML record writes

P02 `_save_xml_atomic` owns checkpoint, worker-identity, history and settings writes. It creates parent folders, opens a short unique same-folder temporary file exclusively, saves through FileStream and flushes before Move/Replace. The final record's path/schema is unchanged. Existing records remain in place on failure; cleanup cannot mask the original error. Diagnostics name the operation and both path lengths. Do not restore target-name-plus-GUID temporary paths or fall back to deleting a durable record before replacement. Native `test_checkpoint_io.py` covers path geometry, characters and actual file locks.


## Structured page failure explanations

H06 PageProcessingError carries ERROR_CODE, ERROR_PAGE, ERROR_STAGE, ERROR_ACTION and ERROR_DETAIL alongside an actionable MESSAGE. explain_page_failure checks environmental exceptions first, then performs a strict source load only after a page error. A readable source does not become a corruption claim merely because an encoder failed. Raw diagnostics are escaped onto one protocol line. The main worker emits these fields; P09 includes them in normal/per-quality technical reports while result rows and workflow reasons use MESSAGE. Successful image bytes and checkpoint compatibility are unchanged. Tests: test_error_explanations.py and native test_error_reports.py.


## Results review and path/Unicode transport

P17 stores each result row with its original per-book lines and stable index in Tag. ResultRowComparer sorts statuses semantically and reductions numerically, keeping missing measurements last. ResultDetailsForm is read-only and copies/saves only the selected block with report context. Color toggling changes row foregrounds only; S06 reapplies them after theme changes. No report/history/checkpoint content changes on sorting or color toggles.

P03 _quote_argument implements Windows argv backslash-before-quote rules. _normalize_work_directory removes paired outer quotes, expands environment variables and validates the selected folder without rewriting comic names. Python stdout/stderr and matching .NET readers use UTF-8; 7-Zip name output explicitly uses -sccUTF-8. Keep both ends coordinated. Generated tests cover native Windows argv, trailing slashes, quoted folders, cp1252 environment/Unicode archives and archive-header/collision diagnostics.


## Result preferences and replacement destination preflight

P17 stores results_errors_first/results_status_colors/results_sort_column/results_sort_ascending in the existing settings XML, merging other keys. Restore runs under a guard to avoid writes during construction/theme application; only explicit toggle/sort changes save. Sort columns use displayed base names rather than indices so different report types can ignore unavailable columns safely. Tests redirect SETTINGS_PATH and restore it afterward.

_replacement_destination_conflict returns a structured DESTINATION_EXISTS before normal conversion starts for extension-changing replacement. The runner must not start a helper or write new pending checkpoints for known conflicts; any owned prefetch cache is cleaned through existing guarded logic. _finalize_replacement rechecks to cover races and retains converted output when a late conflict appears. Existing source/destination and older pending/recovery records are not resolved automatically.


## Results scale, retry and support information

P17 retains parsed report records separately from native ListView rows. Filters/search operate on the records, sorting covers the entire matching set, and only 250 rows are materialized per page. Status classification uses original report fields; friendly labels never change stored status or library values. Search is debounced and its timer/tooltip are disposed with the form. Summary extraction reads only the header. Technical text is loaded on first tab activation (including a tab selected before Show), with per-heading formatting disabled above one million characters. The authoritative report remains intact.

Current-run results receive captured book references and an options snapshot. Retry returns only selected error records whose original paths still match those references. It strips transient cache/progress state and closes results. The public hook loops back to options without recursive modal execution; preflight, setup, pending-work and overwrite safeguards run normally. History windows have no live library references and cannot initiate this retry route. New history records whitelist additional settings for accurate review; unknown historical settings are never inferred as safe defaults.

Support information is prepared locally in an editable details window. Dependency discovery is explicitly separate from the optional functional setup check. Copy/save reads the edited text, not its unredacted initial value. No publishing or automatic clipboard action occurs. Setup checks use the existing disposable-file checks and block closing the details window while those checks are active.

Development/test_results_review.py includes a generated 125,001-book scale test, global paging/sorting/filtering checks, failed-only retry preparation and editable support/setup behavior. It does not claim throughput or memory acceptance for conversion of a real collection that size.


## Shared UI conventions

S06 `_polish_dialog` applies Segoe UI/Font autoscaling, spatial tab order, accessible field names, contextual Ctrl+F, table hover hints and a CancelButton only for review/cancel windows. Existing busy FormClosing guards remain authoritative; progress retains its safe-stop route. Normal windows fit the current screen working area only within their minimum sizes. Benchmark setup has a deliberate fixed size; benchmark result tabs and footer actions resize with the window.

`ThemeButton` inherits the native Button behavior and accessibility. Only dark painting is customized for readable disabled labels, hover/pressed states, default/focus outlines and keyboard focus cues; light mode uses base rendering. All runtime button factories share this implementation. Text/table border styles are saved independently and restored when leaving dark mode. Comic picture pixels are never themed.


## Presentation hierarchy and result selection lifecycle

S07 `_compose_dialog_design` groups existing controls into action/outcome surfaces, introduces muted supporting text and disclosure menus, and lays out an inline selected-book explanation. It runs after original construction and before shared keyboard/theme setup. `_DIALOG_TYPES` retains actual dialog identities even when diagnostic harnesses replace public factories. No encoding/checkpoint policy lives in this layer. Surfaces and muted roles are restored explicitly in both palettes; newly created buttons/labels have explicit light baselines to avoid inheriting a dark parent during construction.

ThemeMenu keeps standard ToolStrip interaction with an optional dark color table. Secondary tools remain reachable via More; menu enabled states are checked when opening. Disposal releases menus with their owner. Primary dark buttons use a restrained teal fill; comic pixels are never themed.

Native list selection events can arrive while rows are being cleared, detached or disposed. P17 `_selected_result_rows` rejects missing Tag/record data and disposed/refreshing state; actions and inline explanations share this snapshot. `_render_result_page` suppresses selection reactions until the table rebuild completes. A regression injects a missing Tag on a selected native row, filters/rebuilds and closes the selected report; no data repair or report rewriting is involved.


The same S07 surfaces cover secondary options tabs and preview chrome. Preflight stores a read-only options/count snapshot solely to describe the review consequence; it does not bypass the existing confirmation. Setup updates its readiness heading while retaining complete diagnostic text and an explicit clipboard action. Recovery hints explain availability without changing retry guards. The temporary-folder field has its own subdued border, retaining the original TextBox/text validation path. Performance layout keeps all original controls visible within the tab.


P06 records original Windows read-only state as read_only (Yes/No/Unknown); P08 applies WebPReadOnly independently from format/workflow status. Missing/inaccessible files must never be labeled writable. Normal conversion/resume refreshes the current source/final-path flag, while tests retain the analysis value. Attribute detection does not change flags or ACLs. The value is a scan snapshot, not a live smart-list filesystem query.
