# Advanced usage and troubleshooting

Start with the [quick start in the README](README.md#quick-start). This guide keeps the storage, report and recovery details available when you need them.

Jump to: [Python/Pillow setup](#install-python-and-pillow-on-windows) | [Plugin folder](#installation-folder-and-missing-scripts-folder) | [Smart lists](#comicrack-guru-cleanup-lists) | [Quality and actions](#actions-and-quality-settings) | [Pixel diagnostics](#quality-comparisons-and-pixel-diagnostics) | [Preview cleanup](#preview-storage-and-cleanup) | [Performance](#performance-and-large-batches) | [Resume](#continuing-after-a-stop-or-restart) | [Recovery](#replacement-recovery) | [History](#run-history) | [Setup](#setup-space-and-sleep) | [Error reference](#error-reference)

## Install Python and Pillow on Windows

Python runs the conversion helper. Pillow is a Python package used for page validation and preview support; it is required even when ImageMagick does the encoding. You do not need a code editor, development environment or virtual environment for this setup. Analyze Only does not require Python/Pillow.

### 1. Download and install Python

Save your work and close ComicRack, including any tray instance.

1. Open the [official Python Windows downloads page](https://www.python.org/downloads/windows/) and select **Latest Python 3 Release**.
2. Download **Windows installer (64-bit)** from that release's files. Choose the normal installer, rather than the Install Manager or embeddable package.
3. Open the downloaded `.exe`, tick **Add python.exe to PATH**, then choose **Install Now**. Keep the default pip and Python launcher options enabled.
4. When installation finishes, close the installer.

This installs Python through a normal setup window; no installation commands are needed. Use the same Windows account that runs ComicRack. If you already have Python 3.9 or newer, you can keep it and continue with Pillow.

### 2. Open Command Prompt

Click **Start**, type **Command Prompt**, and open it. This is only needed to install Pillow and check the setup. A normal prompt looks like `C:\Users\YourName>`; you do not need to change folders.

Paste each command below separately and press Enter. Use Command Prompt, not a Python window showing `>>>`. If you see `>>>`, type `exit()` and press Enter to leave Python. Do not type the prompt symbols themselves.

### 3. Install Pillow

In the same Command Prompt, run these commands one at a time:

```bat
py -3 -m pip install --upgrade pip
```

```bat
py -3 -m pip install --upgrade Pillow
```

Wait for each to finish. The Pillow command should end with **Successfully installed** or **Requirement already satisfied**. Pillow is installed into the Python selected by `py -3`, matching the plugin's preferred launcher. These commands follow [Pillow's pip installation instructions](https://pillow.readthedocs.io/en/stable/installation/basic-installation.html).

### 4. Check that both work

Run:

```bat
py -3 --version
```

You should see `Python 3.x.x`, with a version of at least 3.9. Then run:

```bat
py -3 -c "from PIL import Image, ImageCms; print('Pillow is working')"
```

You should see **Pillow is working**, without an error traceback. Do not continue past installation errors; use the troubleshooting table below.

### 5. Restart ComicRack and check setup

Finish [installing the plugin folder](#installation-folder-and-missing-scripts-folder), then start ComicRack again. Select a disposable test comic, open **Optimize Archives**, choose **Create WebP Copies**, and open **Tools & recovery > Check setup**. Selecting a conversion action checks Python/Pillow and the encoder; Analyze Only deliberately does not check those conversion dependencies.

### If a command fails

| What you see | What to do |
|---|---|
| `py` is not recognized | Close Command Prompt and open a new one after installing Python. If it still fails, try `python --version` and use the alternative commands below, or rerun the Python installer to enable its launcher/PATH options. |
| `py install` reports it cannot open a file named `install` | That command requires Python Install Manager. It is unnecessary with the normal installer above. Continue with the Pillow commands once `py -3 --version` works. |
| `No module named pip` | Run `py -3 -m ensurepip --upgrade`, then repeat step 3. |
| `No module named PIL` | Repeat the Pillow command in step 3 using `py -3`, then repeat the verification. The install name is **Pillow**; the import name is **PIL**. |
| The command works but the plugin still cannot find Python | Fully close/restart ComicRack after installation so it inherits the updated environment. Run Check setup with a conversion action selected; include its exact error if asking for help. |

If your working Python installation only responds to `python` rather than `py -3`, use `python` in place of `py -3` for the pip and verification commands. Confirm `python --version` reports Python 3.9+ first; the plugin also supports that command. Avoid installing Pillow into a separate virtual environment that ComicRack does not use.

## Installation folder and missing Scripts folder

For a normal installed copy of ComicRack CE, use the current Windows user's folder:

```text
%APPDATA%\cYo\ComicRack Community Edition\Scripts
```

Press Win+R and paste `%APPDATA%\cYo\ComicRack Community Edition` to open the parent, even when AppData is hidden. Start ComicRack CE once first. If **Scripts** is missing, create that folder yourself; it need not already exist on a fresh installation. Extract the download's **WebP Optimizer** folder into it, with `WebPOptimizer.py`, `Package.ini`, the other runtime files and `Magick` directly inside that plugin folder. Restart ComicRack afterward.

Do not put the ZIP itself in Scripts or add an extra nesting level such as `Scripts\WebP Optimizer\WebP Optimizer`. Use the CE folder named **ComicRack Community Edition**, not the **ComicRack** folder. Preserve your existing settings and Reports when updating.

ComicRack CE also supports a Scripts folder in its program installation directory, as described in its [upstream installation guidance](https://github.com/maforget/ComicRackCE#plugins). Prefer the per-user AppData location for a normal installation because the plugin writes settings, reports and checkpoints beside its code. A Program Files installation may restrict those writes. Do not install duplicate copies in both locations.

For portable or alternate-configuration installations, the active data location can differ. Check the active ComicRack configuration rather than creating folders at guessed paths. If the plugin does not appear after restart, check **Edit > Preferences > Scripts** for script availability/enabling and confirm the extracted layout above. This plugin is a manual ZIP installation; the Script Packages installer expects a `.crplugin` file.

## ComicRack Guru cleanup lists

I added these after **1.8 Convert to CBZ** in the Guru workflow's **01 - Clean Up** section. Search **Library** and choose **Custom Value** for each rule. Enter the field names and values below exactly; leave the value empty where it says blank. Use the normal **is** operator without negating it.

| Smart list | Match | Rules | Shows |
|---|---|---|---|
| **1.9 Run Image Format Check** | All | `ImageFormat` **is** blank | New books waiting for analysis. |
| **1.10 ImageFormat Errors** | **Any** | `ImageFormat` **is** `ERROR`; `WebPStatus` **is** `Needs attention` | Analysis or conversion problems to investigate. |
| **1.11 Convert To WebP** | All | `WebPStatus` **is** `Ready` | Eligible books waiting for conversion. |
| **1.12 WebP Skipped - Review** | All | `WebPStatus` **is** `Skipped` | Other skips, such as PNG eligibility or the selected CBR option. Check `WebPReason`. |
| **1.13 WebP Copies Created** | All | `WebPStatus` **is** `Copy created` | Originals with separate converted outputs; optional if you only replace originals. |

**Optional: Read-only comics**: Match All; Custom Value `WebPReadOnly` is `Yes`. Run Analyze Only on the intended books first. `No` means the flag was absent; `Unknown` means the file was unavailable or its attributes could not be read. This value is a snapshot: reanalyze after changing attributes. It is separate from ImageFormat and WebPStatus, and does not change files automatically.

To gather comics from individual subfolders in Explorer, open their common parent folder and search `ext:cbz OR ext:cbr` with **All subfolders** selected. Wait for the search to finish, select the intended comic files in the results, then press **Alt+Enter** for Properties and clear **Read-only**. Ctrl+A selects every search result, so use it only if you intend to make all those files writable. For a mixed selection, click the Read-only box until it is empty, then Apply. This changes the selected files' attribute, not their comic contents. Existing interrupted outputs/recovery records still need review.

**Optional: 1.14 WebP Size Policy Skips**: Match All; Custom Value `WebPStatus` is `Skipped - size policy`. These books did not meet the savings threshold for the settings tested and do not need repair. Keep this as an informational list outside cleanup if you prefer. They can still be explicitly retried with different quality/policy choices.

For existing size-policy skips, select them from **1.12** and run **Analyze Only** once. Unchanged books with a recognized saved size-policy reason receive the new status without being converted again. **1.11** remains `WebPStatus is Ready`; its rule does not change.

**Important:** use **Match Any** for **1.10** so either rule can flag a problem. All the other lists use **Match All**. Use `WebPStatus is Ready` for **1.11**, as shown above.

Run **Analyze Only** on new books from **1.9**. After conversion, the status moves books out of **1.11**: successful replacements become `Completed`, copies become `Copy created`, and skipped/problem books appear in their review lists. Quality tests leave the workflow status unchanged.

`ImageFormat` describes the source pages; `WebPStatus` tracks work on the book. For example, creating a WebP copy leaves the original's `ImageFormat` unchanged. See [workflow status](ADVANCED_USAGE.md#workflow-status) for more detail.

![ComicRack Guru cleanup workflow showing analysis, errors, conversion, skipped review and copies created after Convert to CBZ](docs/images/guru-cleanup-workflow.png)

<details>
<summary>Smart-list setup screenshots</summary>

**1.9 Run Image Format Check**: Match All; ImageFormat is blank.

![Run Image Format Check smart list: match all, Custom Value ImageFormat is blank](docs/images/smart-list-image-format-check.png)

**1.10 ImageFormat Errors**: Match Any; ImageFormat is ERROR or WebPStatus is Needs attention.

![ImageFormat Errors smart list: match any, ImageFormat is ERROR or WebPStatus is Needs attention](docs/images/smart-list-image-format-errors.png)

**1.11 Convert To WebP**: Match All; WebPStatus is Ready.

![Convert To WebP smart list: match all, WebPStatus is Ready](docs/images/smart-list-convert-to-webp.png)

**1.12 WebP Skipped - Review**: Match All; WebPStatus is Skipped.

![WebP Skipped review smart list: match all, WebPStatus is Skipped](docs/images/smart-list-webp-skipped-review.png)

**1.13 WebP Copies Created**: Match All; WebPStatus is Copy created.

![WebP Copies Created smart list: match all, WebPStatus is Copy created](docs/images/smart-list-webp-copies-created.png)

</details>

## Actions and quality settings

Start with the action card in Workflow & quality, then adjust Quality & output. The quality estimate is a short guide; **About this estimate** explains the sample and its limitations. The start button names the selected action, and the pre-run review remains required.

| Action | Behavior |
|---|---|
| Analyze Only | Inspect archives and update the image-format/workflow custom values; no conversion |
| Create WebP Copies | Keep the original and its library path; create separate converted output |
| Replace Originals | Validate the output, install it and update the existing library entry; optional retained original backup |
| Test savings & quality | Run Q60/Q70/Q75/Q80/Q90 on up to three eligible books spread through selection order; leave originals and workflow tags unchanged |

The quality dropdown offers Q60 through Q90. Q80 is the default; Q75 favors space savings. Reference estimates come from JPEG-page samples, not the selected library or whole-book predictions. No Resize and Only If Smaller are the defaults. The other size policies can require at least 3% savings, allow up to 1% growth, or retain all results.

ImageMagick is the recommended/default encoder. cwebp and Pillow are optional alternatives with different encoding implementations; selecting one requires that encoder to be available. There is no silent fallback. Pillow remains required for conversion validation regardless of the selected encoder. Existing WebP pages and preserved non-JPEG members are not re-encoded by the JPEG step. PNG-only/PNG-heavy archives are intentionally skipped.

CBR handling can convert to CBZ, skip CBR sources, or rebuild CBR using separately installed WinRAR. 7-Zip reads/extracts CBR input. CBR-to-CBZ replacement retains the existing ComicRack entry while changing its file path.

## Quality comparisons and pixel diagnostics

Enable Keep preview pages for a Test savings & quality run, then open previews from results. Choose a page and quality in the maximized native viewer. Each sampled book runs five complete conversions, so a quality test takes longer than one normal conversion.

| Control | Behavior |
|---|---|
| Mouse wheel | Scroll both panes vertically |
| Shift + wheel | Scroll both horizontally |
| Ctrl + wheel | Zoom both around the viewport center |
| 100% zoom | Show actual image pixels |
| F11 / Escape | Toggle full screen / return to window, then report |
| Hover either image | Read original and converted RGB at the matching image coordinate |
| Analyze differences | Calculate measurements for the current full-resolution pair in the background |
| Show amplified difference (8x) | Replace the right pane with a difference heatmap; uncheck to restore the WebP preview |

The heatmap uses the largest absolute RGB-channel change at each pixel, multiplied by eight and clipped to the display range. Black means identical RGB values; orange highlights changes. Amplification deliberately makes small differences easier to see and is not the normal appearance of the converted page.

| Measurement | Meaning |
|---|---|
| Mean change | Average absolute RGB channel difference, on a 0-255 scale |
| RMS | Root mean square RGB error; larger errors receive more weight |
| Max | Largest single-channel difference anywhere on the page |
| Brightness shift | Signed weighted encoded-RGB brightness estimate; positive means brighter on average, negative darker |
| Changed pixels | Percentage with any RGB difference, however small; not the percentage visibly damaged |

Measurements use the same detached, color-managed full-resolution bitmaps as the viewer, not screenshots or scaled pane pixels. Zoom does not change the measurements. They establish where/how RGB pixels differ, not a percentage of quality retained or a guarantee that a reader will notice a change. Brightness is an RGB estimate, not linear luminance, Delta E or SSIM; page averages can hide local differences, so use the heatmap and pixel inspector as well.

Analysis is optional, requires matching dimensions and supports up to 16 million pixels per page to limit memory use. It adds no work to normal archive conversion and no extra files or packages. Results are cached only for the active page/quality and released when switching or closing. A running job owns separate snapshots and discards its result if the viewer closes. Previews from saved runs can be analyzed if their native image pairs remain available.

<details>
<summary>Example: Q80 comparison and amplified differences</summary>

![Original JPEG and Q80 WebP shown side by side at full-page fit](docs/images/quality-comparison-q80-full-page.jpg)

The comparison shows the original on the left and the converted Q80 page on the right. The size caption is for this page; whole-book savings are reported separately.

![Original beside the 8x amplified Q80 difference heatmap at actual-pixel zoom](docs/images/difference-heatmap-q80-actual-pixels.jpg)

The orange view exaggerates RGB changes; it is not the appearance of the converted page. The coordinate inspector and full-page measurements remain available below the images. These screenshots illustrate the controls, not a lossless or perceptually identical result. JPEG screenshots are not suitable inputs for measuring encoder accuracy; use the live viewer's retained image pairs.

</details>

## Preview storage and cleanup

Preview files are saved in `Reports/QualityTests/<run-id>` inside this plugin folder. PNGs are lossless display copies of decoded WebP pixels and retain color profiles; captions use actual WebP sizes. These PNGs can be much larger than the WebPs.

**Delete this run's preview images when closing this results window** is checked by default. Leave it checked to remove that run's JPEG/WebP/PNG samples and manifest when closing results, including with X. Uncheck it to keep the run; the preference is remembered. Closing only the comparison popup does not delete previews, so you can reopen it from results. Text reports are retained. Cleanup failures show the remaining folder path. An app/process crash can leave previews behind for manual cleanup later.

This option only deletes the current generated run under `Reports/QualityTests`; it does not clear other runs, source comics, reports or backups.

## Storage, stopping and reports

Storage & advanced lets you choose a temporary work folder. Blank uses each source directory. Final comic output remains beside the source. Temporary space is still required even when replacing without a retained backup.

**Stop after current book** finishes the active book safely, then saves a partial-run report. During a quality test, it finishes all five quality passes for that book. Later books are marked not processed. Closing the progress window requests the same safe stop.

The results screen shows weighted total reductions and per-book outcomes; full details are in Technical report. Central text reports and structured `.run.xml` history records are kept in `Reports`. You can also save full run reports beside source files. Copy/test results and retained backups do not themselves reclaim the displayed savings from disk.

Options are remembered in `settings.xml` when starting a run. Restore defaults resets the dialog; Cancel leaves saved options unchanged.

<details>
<summary>Example: quality-test options and progress</summary>

![Quality-test action with preview retention enabled](docs/images/options-quality-test.png)

The quality test measures all five levels, even when a single-quality preset is shown in a disabled field.

![Quality test encoding a page with Stop after current book available](docs/images/quality-test-progress.png)

Speed and ETA appear after the first successful quality pass; stopping finishes all five passes for the active book.

</details>

## Performance and large batches

**Performance & resume > Concurrent pages** offers 1, 2, 4, 6, 8, 10 or 12 page encoders within the active book. One remains the conservative default. More workers need more RAM, especially for large scanned pages. Encoding and validation use the same worker budget at different stages. ZIP validation retains every member/CRC/hash/decode check and bounds pending compressed buffers to 64 MiB, except a single larger member. CBR validation remains sequential.

**Benchmark worker counts** tests all seven counts at your chosen quality, encoder and dimensions on up to 3 eligible JPEG-only books spaced through the selection. Quick performs one pass (up to 21 conversions); Thorough performs three passes in rotated order (up to 63). Each complete output is validated and deleted, without replacing originals, changing library tags or writing completion checkpoints. Output is staged beside each source, matching normal runs; temporary extraction uses your chosen folder. Stop finishes the active trial archive, then saves the partial results. Only a complete comparison receives a recommendation. Clicking **Use > workers** changes the options draft; starting a run saves that choice.

Results show full-run source MB/s, converted pages/s, average CPU, sampled peak RAM, logical process read/write MB/s and the longest stage. Full raw measurements, including stage times, CPU peaks and private commit, are retained in `Reports/PerformanceTests/<run-id>/report.txt`, with a `summary.csv`. Open these files directly to revisit a benchmark. CPU is normalized across all logical processors; RAM sums the helper and directly launched tools and can double-count shared pages. Short peaks may be missed. Process I/O includes cached and temporary activity: it is **not** physical drive or network throughput. Caching and other programs affect comparisons; rerun on representative originals before choosing a large-batch setting. The longest stage is a clue, not proof of a particular hardware bottleneck.

**PC priority > Background** lowers CPU scheduling priority for the helper and its tools. It does not cap RAM or throttle disk/network activity. Normal is suitable when dedicating the PC to conversion; choose workers independently in either mode.

**Prefetch one next archive** is optional and off by default. It requires an explicitly chosen local fixed-drive temporary folder (mapped/UNC network drives are excluded). During encoding it copies at most one next compressed archive, up to 256 MiB, with an additional 128 MiB free-space reserve. Larger books use normal processing. Cache reuse checks source size/mtime and a SHA-256 checksum; source identity, replacement guards and checkpoints still refer to the original. The consumed cache is removed after extraction before another is started. The worker acknowledges the exact cleaned manifest, avoiding another Python cleanup launch; missing acknowledgements retain guarded fallback cleanup. Reports include caches used/prepared totals and per-book `PREFETCH_*` fields, including usage, next-cache readiness, cleanup acknowledgements and fallback notes. Safe stop cleans a completed unused cache; unfinished copies are cancelled after the active read. Cleanup failures stop further books and identify remaining files. An app crash can leave a `webp_prefetch_<id>` folder in the chosen temporary location for manual review/cleanup. Prefetch adds simultaneous source reads and may hurt a busy drive, so compare with it off and on.

GPU encoding is not available in the bundled backends. ImageMagick's optional OpenCL operations do not provide a WebP GPU encoder; adding a GPU switch would not accelerate this workflow. See [ImageMagick OpenCL](https://imagemagick.org/opencl/) and [nvImageCodec's codec/backend table](https://github.com/NVIDIA/nvImageCodec).

For NAS collections, choose a local **Temporary storage** folder on Storage & advanced. Extraction and page conversion then use the local drive; the original still comes from the NAS and final output is staged beside it. Local work storage is optional. Blank continues to use each source folder. Ensure both locations have space for the active book; you do not need room for temporary copies of the entire collection.

Normal copy/replace runs scan one book immediately before processing it, avoiding a full-selection scan before conversion begins. Quality comparisons still inspect the selection to choose spaced eligible samples, then run all five quality levels fresh.

CBZ creation stores already compressed JPEG/PNG/WebP members directly and compresses XML/text. Validation checks member CRCs, hashes and image decoding in one archive-read pass. Image encoding quality and metadata checks are retained; ZIP storage can make an archive slightly larger than additionally deflating those same image bytes.

The progress window shows source MB/s and a rough remaining-time estimate after a completed conversion. Progress and ETA use cached ComicRack sizes when available and fall back to book count when sizes are unavailable. The batch bar advances at book boundaries; the stage label separately shows extraction, encoded-page counts, rebuilding, validation and replacement. Quality tests show speed after the first successful quality pass and estimate the remaining passes across the sampled books. Their throughput counts each quality pass separately. Eligibility, page complexity and NAS conditions can change the estimate. It does not scan the whole NAS just to calculate an ETA. Technical reports include stage timings; totals include extraction, encoding, rebuilding and validation, with scan and replacement timings listed separately for normal runs.

<details>
<summary>Example: performance and resume options</summary>

![Concurrent page workers, priority, benchmark, prefetch, resume and keep-awake controls](docs/images/options-performance-and-resume.png)

This capture shows the tester's settings, including 12 workers. New-install defaults remain one worker, Normal priority, prefetch off and completed-book recognition on; choose workers using your own benchmark.

</details>

### Continuing after a stop or restart

Leave **Resume completed books with matching settings and unchanged files** enabled. Select the original batch or its remaining books in ComicRack, review the same conversion choices, then start. There is no background scheduler or automatic selection of old sources.

Before each normal conversion, a pending checkpoint is saved under `Reports/Checkpoints`; successful completion is saved after replacement/library-update calls. Records include paths and measured results. Matching completed files are skipped without encoding again, and resumed work is not counted as newly reclaimed space. Books previously rejected by the same size policy are also recognized. Failed attempts are retried only when they leave no ambiguous output or recovery record.

Resume checks source/output sizes and modification timestamps, conversion settings and an explicit conversion-policy compatibility version. These are conservative identity checks, not full content hashes or file locks. Changing worker count or work storage does not invalidate completed work; changing quality, resize, encoder, CBR handling, size policy, backup choice or an incompatible conversion-policy version does. Compatible maintenance updates preserve completed-work recognition. Keep the records if you want resume recognition. Reports alone cannot reconstruct missing checkpoints.

A completed CBR-to-CBZ checkpoint can recognize the new path and repair a selected old library path if the old file is missing and the recorded final file is unchanged. An unfinished attempt, corrupt checkpoint or unresolved replacement recovery record is reported for inspection; its output is never automatically installed or deleted. An unknown interrupted attempt requires review even if its output does not exist yet: a helper may still be encoding after ComicRack closes. Pending-attempt checks also apply when you disable completed-book reuse or change conversion settings. Do not start concurrent optimizer sessions against the same files.

For an interrupted attempt, open **Tools & recovery > Review interrupted work**. Select the attempt and choose **Check files**. Stop any remaining helper/encoder, inspect the named files, and resolve leftover converted/rollback files before checking again. Confirm that processing has stopped, then use **Allow retry** only when enabled. This archives tracking records and a resolved recovery note; it does not delete or install comic archives or start a conversion. Select the book and start a new run yourself.

Use interrupted-work review for pending records. Completed records need compatible conversion-policy metadata for resume recognition; incompatible records may require a fresh check/conversion.

If temporary cleanup fails, the report identifies the remaining work folder and processing stops after the active book. A force-close or crash can leave temporary pages and outputs; checkpoints do not automatically purge them or guarantee recovery from every network/power failure. Final text reports are still written on completion or graceful stop; per-book checkpoint XML provides durable completed-work records between those points. Preview cleanup does not delete checkpoints.

For your first large run, use a manageable batch with your chosen worker count and local storage, then inspect timings and free space. Copy mode and retained backups keep the originals, so they do not reclaim the reported savings.

## Replacement recovery

Replacement preserves recoverable files on failure and writes a `<source>.webp-recovery.txt` record before changing filenames. If an operation fails, inspect the report and named source/converted/rollback paths before retrying. An unresolved recovery record blocks another replacement. CBR-to-CBZ replacement refuses to overwrite an existing CBZ. Recovery is not a guarantee against every power-loss or network failure.

To review multiple interrupted attempts:

1. From a relevant error in the results, select the book and choose **Review interrupted work**. You can also use **More > Review interrupted work**, or open it from **Tools & recovery**.
2. Select the attempts you want to review, or choose **Select all**, and choose **Check files**. Use **Batch details** to see the findings for each attempt.
3. Once you have verified that the previous helpers and encoders have stopped, check the confirmation box and choose **Allow retry**. Each attempt is checked independently; the summary identifies those allowed and those still blocked.
4. From a current run?s results, **Prepare retry** opens the options for the successfully cleared books. Review the settings and explicitly start the run. From saved history or the options window, select the cleared books in ComicRack and start a new run yourself.

An active helper, changed files, or a retained converted/rollback output can still block an attempt. Review the paths and batch details; the tool does not delete or install retained archives to force a retry. Clear any read-only protection separately if replacement is intended.

Start with a small disposable selection before a large replacement batch. Earlier local/NAS and reader workflow tests passed for the development installation; clean-machine installation and broader environments remain to be verified.

## Folder layout

| Location | Purpose | Included in release ZIP? |
|---|---|---|
| Root Python files, icons, package metadata and docs | Plugin runtime and user instructions | Yes |
| `Magick` | Static Windows x64 ImageMagick encoder, build identity and matching license notices | Yes |
| `quality_estimates.txt` | Reference sample reductions | Yes |
| `settings.xml` | Your saved choices | No |
| `Reports` | Your run reports and optional previews | No |
| `Development` | Tests, fixtures, calibration lab and implementation history | No |
| `Releases` | Generated distribution ZIP and checksum manifest | No |

Development commands and packaging instructions are in `Development/README.md`.

## Run history

Open **Run history** from Optimize Archives, or use the standalone **WebP Optimizer Run History** library action without selecting comics. Viewing history does not require Python, 7-Zip or an encoder to be available.

History lists date, action, processed-book count, run status, measured reduction and preview status. Open results reopens the native report; Open previews reopens retained native comparison images. Refresh updates the list after filesystem changes. Available means usable native preview images exist; Removed means a recorded cleanup removed them; Unavailable means files are missing, incomplete or without native preview data. A dash means no preview folder was recorded. Deleting previews removes only the selected run's generated preview folder and preserves the report.

**Historical results always start with Delete previews on close unchecked**, regardless of the default for new results. Reviewing old results will not delete their images. You may explicitly check the box or use **More > Delete retained previews** in history to remove them.

New runs save a `.run.xml` file beside the text report, including summary data, relevant options and source paths. Missing or damaged records fall back to the text report header; saved reports remain visible with whatever data is available. XML records contain personal paths and are excluded from release packages along with all Reports content. The history list reads only short headers when no XML summary is available rather than loading entire detailed reports.

From history opened through Optimize Archives, **Prepare new test** fills in recorded encoder/CBR/work-folder choices, selects Test savings & quality and enables preview retention. It does not convert anything or automatically reselect old files. Review the current ComicRack selection and settings, then explicitly start a new run. Source files may have changed since the old run, so results are recorded separately. The standalone library history view is for reviewing/deleting previews; open history through Optimize Archives to prepare a new test.

If a preview folder was removed, the report can still reopen but those images cannot be recovered from the report alone. Run a new comparison to recreate them. Report history is retained until its files are explicitly removed; there is no automatic report purge.

If opening history fails, check `Reports/history-diagnostic.log` for the recorded opening sequence and process identity. History and its report/preview windows run in a separate process. A helper failure returns an error and restores options. Check `Reports/history-helper-error.log` for startup/exit errors. This separation isolates the history windows; include these logs if a problem recurs.

<details>
<summary>Example: run history</summary>

![Run history listing quality comparisons, copy and replacement results with preview availability](docs/images/run-history-dark-mode.png)

These are separate development runs, not one combined collection result. Select a row to enable its available actions. Removed previews cannot be reopened without running another comparison.

</details>

## Workflow status

Analyze the library after updating to populate these custom values. `ImageFormat` describes the source pages; `WebPStatus` describes the work outcome, and `WebPReason` explains it.

| WebPStatus | Meaning |
|---|---|
| Ready | Analysis found eligible pages |
| Completed | Replacement completed or was recognized from a matching checkpoint |
| Copy created | A separate converted output exists; the source remains unchanged |
| Already WebP | Source pages are already WebP |
| Skipped - size policy | Converted output did not meet the chosen savings/growth threshold; no repair needed |
| Skipped | Other intentional skips, including PNG eligibility or the selected CBR option; inspect WebPReason |
| Needs attention | Analysis/conversion failed or requires review |

Unchanged prior outcomes survive analysis. An explicit conversion can retry a skipped book with different choices. Quality comparisons do not mark the source completed. These labels are workflow aids; file checks still control replacement and resume safety.

## Setup, space and sleep

Check setup shows whether the selected workflow is ready. **Copy check results** copies its complete findings for troubleshooting. The batch-review screen highlights whether originals stay in place or will be replaced, including whether a permanent backup is selected.

**Tools & recovery > Check setup** tests the prerequisites for the currently selected mode. Conversion checks perform a tiny real encode/decode and archive test in temporary storage. Analyze-only checks do not require Python. Nothing is installed automatically.

The pre-run summary uses cached ComicRack file sizes and a conservative storage scenario, not a full library rescan. Unknown sizes, unavailable shares, unusually large extracted pages and preview PNGs can make the estimate incomplete. Review both source and temporary-drive space.

**Keep PC awake** requests that Windows avoid automatic idle sleep during processing and restores the thread's previous request when the run ends or stops. It does not keep the display on, change your power plan or prevent manual sleep/shutdown. It is off by default.

<details>
<summary>Example: setup and recovery controls</summary>

![Tools and recovery tab with Check setup, Review interrupted work and Dark mode controls](docs/images/options-tools-and-recovery.png)

</details>

## Appearance and technical reports

**Ctrl+F** focuses search in Book results or the technical report. **Escape** closes review windows or cancels options; active processing still uses its safe-stop controls. Hover over a table entry to inspect clipped text.

Dark mode is the default when no preference has been saved. Use the **Dark mode** switch in the options header to turn it off for light mode; your choice is remembered. Restore defaults also selects dark mode.

Use the **Dark mode** switch in the options header to preview the palette. It is remembered when starting a run; Cancel or closing options discards the unsaved choice. Comic image pixels and color management are unchanged. Windows title bars also follow dark mode. Supported Windows versions use a muted grey caption; Windows 10 may use its native dark caption shade. Unsupported frame attributes leave the system appearance intact. Tab borders use subdued grey.

The **Technical report** tab preserves the complete report and adds bold labels, **Find next** and **Wrap long lines**. Search continues from the selection and wraps to the beginning. **More > Copy full report** and **More > Open report file** use the full original text, including every path and diagnostic field.

Setup always reports whether WinRAR is available. Missing WinRAR is informational for analysis and CBZ output; selecting CBR rebuilding makes it a requirement and exercises a generated CBR. 7-Zip supplies CBR reading/extraction.

Pillow is currently a conversion requirement even with ImageMagick or cwebp: it supplies image decoding/dimension validation and color-profile-aware preview support. Selecting ImageMagick still uses ImageMagick for encoding; Pillow's encoder is an optional alternative. Analyze Only does not need Pillow or Python.

History uses the Windows PowerShell installed with Windows and the IronPython DLLs from your ComicRack installation. No extra Python package is required for history. The console is hidden; the native browser and previews remain visible. Startup may take a couple of seconds. The child receives no ComicRack objects and cannot start an archive conversion. Prepare new test returns settings for your existing selection; review them and explicitly start a run.

Temporary history-session XML files under Reports/HistorySessions are removed when the caller finishes, including after a helper failure. Reports and retained previews follow their existing retention rules. The launcher uses a process-scoped PowerShell execution-policy option; it does not change your saved system policy. Enforced organization policies may still prevent startup, which is reported without falling back into ComicRack's process.

## Size-policy skips and long filenames

`Skipped - size policy` is informational for the quality and size policy tested, not a claim that a book can never be reduced. PNG-only/PNG-heavy books and CBRs skipped by option continue to use `Skipped`; errors use `Needs attention`. Keep the generic skipped-review list separate from the optional size-policy list. Analyze Only upgrades recognized size-policy messages only while the source stamp remains unchanged; it does not re-encode the book.

ImageMagick now receives page data through file handles, so deeply nested extracted names can be converted without requiring a local work folder. Original archive names/member names remain intact. Manifest mismatches still stop conversion; diagnostics now name all missing, unexpected and duplicate members. No mismatch is automatically ignored or installed.

A failed run can leave a pending converted archive. New code does not delete or install it. Inspect the named files using the recovery workflow, resolve any old temporary output, then explicitly allow retry after confirming its worker has stopped.

Comic artwork visible in the example screenshots belongs to its respective creators and publishers. The plugin MIT license does not apply to that artwork.

## 7-Zip is installed but reported missing

The discovery-location issue is fixed from **1.0.1**. The plugin searches ComicRack Resources, standard Program Files locations, both Windows registry views and PATH.

Install 7-Zip, restart ComicRack and run **Tools & recovery > Check setup**. Custom portable installations need their folder on PATH. Keep `7z.exe` with the companion files supplied by its installer. Setup performs a real tool check; if it still fails, read the diagnostic for missing dependencies or access problems. 7-Zip is not bundled with this plugin.

## Read-only extracted pages and macOS metadata

Failures caused by archived read-only attributes are fixed from **1.0.2**. Only generated extracted work files are made writable; the original comic and its permissions/ACLs remain unchanged. A different permission or file-lock problem still produces an error rather than being ignored.

Image-looking `__MACOSX/._*` entries are AppleDouble sidecars by naming convention. They are preserved as attachments, excluded from page counts and image decoding, and still checked for byte identity and CRC integrity. This is deliberately narrow: normal images, including root-level `._` names or actual image files inside `__MACOSX`, keep normal validation.

After updating and restarting ComicRack, retry the failed books. Reanalyze if their image-format/eligibility counts included sidecars. Completed books with unchanged files/settings can still be recognized by resume. If an interrupted attempt has a pending checkpoint or recovery record, use Review interrupted work before retrying; the update does not silently delete retained work folders or resolve ambiguous outputs.

## Checkpoint XML temporary-path errors

A `.xml.<random>.tmp` file is an intermediate journal file, not a file users should create. It may be absent because creation failed or because it was removed during error cleanup. Do not create dummy checkpoint files, delete all checkpoints or disable safety tracking to bypass a failed write.

The excessive temporary-filename suffix issue is fixed from **1.0.2**, which uses short same-folder temporary names. A final checkpoint path that is itself too long, a missing parent folder or an inaccessible folder can still fail. The error identifies the write stage and path lengths. Existing records are retained when a write fails, and conversion is blocked where durable tracking is required.

Use the documented writable per-user Scripts folder and avoid duplicate/nested installations. Check that the Checkpoints parent folders have not been removed while ComicRack is running. If asking for help, include the full error and path (redact your username, preserving the approximate path length). Changing the comic temporary work folder does not relocate checkpoint files.

## Understanding page-conversion failures

The results explain failed pages in the results row and `WebPReason`, including the page name and a next step. Technical reports retain Failure category, Affected page, Failed step, Suggested action and Technical diagnostic. Quality tests retain the same evidence for each failed quality pass.

- **Source image unreadable:** an additional decode check could not load the source page. The image may be damaged, malformed or unsupported; inspect that page and restore a clean original if needed. A valid ZIP/CRC test does not prove every image inside is decodable.
- **Encoder or converted-output failure:** the source passed a decode check, so source corruption is not confirmed. Check encoder setup or share the technical diagnostic.
- **Access, missing file, disk space or memory:** address the named environment/storage problem; these are not labeled image corruption.
- **Image-size safety limit:** inspect the unusually large dimensions. This does not establish a damaged page.

The tool stops rather than silently dropping a page, creating a blank substitute or installing an unvalidated archive. It does not automatically repair source images or enable tolerant decoding. A worker page failure occurs before replacement; retain original files and follow interrupted-work review if required. Share technical fields when reporting an unexplained failure, with personal paths redacted.

## Sort results and share one entry

The outcome summary comes first. **Review errors** filters to failures, while selecting a book shows its explanation and suggested next step below the table. View entry retains the complete evidence. Secondary settings, support and report actions are grouped under **More**.

Choose **All**, **Errors**, **Skipped**, **Converted**, **Not processed** or **Other** to filter results; each option shows its total count. **Not processed** means the run stopped before those books were processed; it is separate from skips. **Other** includes outcomes such as eligible analysis candidates. Search matches book titles, source paths and notes. Results display 250 books per page; **Previous** and **Next** move through matches, and sorting applies to the whole filtered list. The complete saved report is unchanged. The Technical report tab loads its text when opened; very large reports omit decorative heading formatting to reduce delays.

The completion summary shows counts, overall savings and elapsed time where recorded. **Not smaller** (or **Size target not met** for other size policies) means the output did not meet the chosen savings requirement, not that the source needs repair. **Already WebP**, **Previously completed** and **Skipped by settings** explain other common skips; read Details for the exact reason.

**Retry selected** is available for failed books in the current run's results. Use Ctrl/Shift to select multiple rows on a page, then choose Retry selected. Successful books in a mixed selection are excluded. Results close and options reopen with the run's settings for review; nothing starts until you explicitly start and confirm the batch. Pending attempts still require **Review interrupted work**, available from relevant errors, the results More menu, or Tools & recovery. If paths changed, reselect the intended books in ComicRack. Saved history windows do not carry live ComicRack book references, so retry from there by selecting the affected books in ComicRack and opening Optimize Archives.

**More > Run settings** shows the recorded action, quality, encoder, dimensions, workers, temporary folder and backup choice. Missing settings are labeled Not recorded. **More > Open report folder** opens the report's location in results or history.

**More > Support information** prepares versions, recorded settings, dependency discovery and the selected book's error. The window is editable: remove personal paths or other private information before using Copy details or Save details. **Run setup checks** optionally adds functional dependency checks using disposable files; it does not convert a comic. Nothing is uploaded or sent automatically. Include your ComicRack version manually if it cannot be detected. Share the reviewed details in [GitHub Issues](https://github.com/RayRayElite/comicrack-webp-optimizer/issues) or the Reddit announcement thread.

Click a Book results column header to sort; click it again to reverse direction. Reduction columns sort numerically, with unmeasured values last. **Errors first** brings failures/missing-file results to the top without removing other entries.

Select one row and choose **View entry**, or double-click it, for the complete per-book block and report context. **Copy entry** copies only that book. The details window also offers **Copy details** and **Save details...** as UTF-8 text. Category, affected page, suggested action and raw technical evidence remain included where the report recorded them. Redact personal paths before posting publicly.

**Status colors** is an optional remembered toggle: green for successful/eligible results, yellow for skips and red for failures/missing files; not-processed or unknown states stay neutral. Colors adapt to dark/light mode. Status text remains visible, and sorting/coloring does not modify the saved report or ComicRack library values. **Errors first**, status colors and the last column/direction are saved when changed and restored for new results and history windows. Turning Errors first off restores the original report order; sorting a different column clears that toggle. A saved column absent from another report type is ignored.

## Illegal character in path and Unicode names

Do not rename files merely because they contain spaces, apostrophes, brackets, accents, superscripts or other valid Unicode characters. An illegal-character message needs the exact path and diagnostic to identify its cause.

Version 1.1.0 fixes Windows command-line escaping for paths ending in a backslash, accepts Explorer-style paired quotes around a temporary-folder path, and explains invalid Windows folder characters before starting a run. Use **Browse** for Temporary storage. Do not paste a web `file://` URL or literal placeholder text as a Windows folder path. Keep the complete error/path for diagnosis if it persists.

A separate `charmap codec can't encode characters` failure is a tool text-encoding issue, not evidence of a damaged comic. Explicit UTF-8 protocol/tool output handles these names. A failed run may already have built an output before reporting failed, so preserve retained outputs and follow interrupted-work review rather than deleting tracking records or blindly retrying.

## Archive headers, page-name collisions and interrupted attempts

**Archive header errors:** test the original with 7-Zip. Mismatched directory/local-header filenames or invalid compressed data need a verified clean backup/replacement or a separately reviewed recovery copy. The tool must not silently omit the failed member or install a partially extracted book.

**CBR-to-CBZ destination already exists:** a same-named CBZ blocks replacement even if the selected CBR is readable. The tool checks this before encoding or writing new pending records. Inspect both files; if the existing CBZ is the intended book, use its library entry instead. Do not delete either copy solely to bypass the error. The finalization guard remains for a destination created while conversion was running; that case retains the converted temporary output for review. Failed runs may retain outputs/pending records and still require the recovery workflow.

**Page-name collision:** a JPEG can share a basename with an existing WebP (or another JPEG extension), making conversion target the same `.webp` name. This is not necessarily corruption: both pages may be readable. Inspect whether they are duplicates or distinct pages and rename/repack appropriately while preserving intended page order. The tool refuses to overwrite or drop either page automatically.

**Interrupted attempt needs inspection:** this is a safety guard, not a corruption verdict. Use **Tools & recovery > Review interrupted work > Check files**; confirm the previous worker has stopped and inspect named outputs/recovery files before using **Allow retry** when enabled. Missing output alone does not prove a helper stopped. Do not remove checkpoints to bypass the review.

## Error reference

Use the **message or error code** below to find the likely cause and next step. This covers known tool errors and common Windows/decoder failures, not every possible third-party message. An error does **not** automatically mean the comic is corrupt. If yours is not listed, [copy the error from the tool and report it](#if-the-message-is-not-listed).

Open **Technical report** for the affected book and read any Suggested action, Failed step and Technical diagnostic fields. The results screen also provides **Errors first**, **View entry** and **Copy entry**. Structured codes are included where applicable; you can also find a failure by its message.

Keep files named in a replacement/recovery error until you have checked them. Do not bypass a failure by deleting checkpoints, dropping a page, disabling validation or creating a missing `.tmp` file yourself.

Jump within this reference: [Setup](#setup-and-dependency-errors) | [Paths and storage](#paths-access-and-storage) | [Archives and pages](#archive-and-page-problems) | [Recovery](#replacement-resume-and-recovery-guards) | [History and previews](#history-previews-and-display) | [Skips](#skips-and-incomplete-runs-are-not-necessarily-errors) | [Other messages](#if-the-message-is-not-listed)

### Setup and dependency errors

| Message / symptom | Why it happens | What to do |
|---|---|---|
| 7-Zip missing / could not find 7-Zip tooling | The tool is absent or not discovered. | The discovery-location issue is fixed from 1.0.1. Install standalone 7-Zip or restore ComicRack's resource tools, restart ComicRack and run Check setup. Keep executable/companion files together. See [7-Zip discovery](#7-zip-is-installed-but-reported-missing). |
| 7-Zip could not start/test the generated archive | An executable was found, but execution or its generated test failed. | Read the full diagnostic. Check the installation, companion DLLs, temporary-folder access and security-software history. Reinstalling unrelated tools will not fix a permission or storage error. |
| Python missing / Python 3 required / `py` not recognized | A supported interpreter is not visible to ComicRack. | Follow [Python/Pillow setup](#install-python-and-pillow-on-windows), verify the commands, then fully restart ComicRack. |
| `install` unavailable / cannot open file named `install` | The Python launcher does not support Install Manager commands. | If `py -3 --version` already reports 3.9+, skip runtime installation and install Pillow. Otherwise use the normal Python installer in the setup guide. |
| `No module named PIL` / Pillow missing / no WebP decoding support | Pillow is missing from the interpreter used by the plugin, or its build lacks required support. | Run the guide's Pillow installation and verification commands using the same `py -3` or `python` interpreter. It is required for validation even with ImageMagick. |
| Selected encoder unavailable / unsupported encoder choice | The chosen backend is missing or a saved choice is incompatible. | Restore the bundle's Magick folder or explicitly select an available encoder. Review restored defaults if necessary. No silent encoder fallback is used. |
| WinRAR missing / CBR rebuild failed | CBR output needs the separate `rar.exe`; other failures can be access/storage problems. | Choose CBR-to-CBZ if CBR output is unnecessary, or install WinRAR and rerun Check setup. Missing WinRAR does not prevent CBR input or CBZ output. Inspect raw diagnostics for other rebuild failures. |
| Plugin does not appear | Wrong folder, extra nesting, scripts disabled or no restart. | Check the [exact installation layout](#installation-folder-and-missing-scripts-folder), enable scripts if needed and restart. A manual ZIP is not a `.crplugin` installer. |

### Paths, access and storage

A **read-only original archive** is different from read-only pages stored inside an archive. The tool handles read-only extracted work files, but does not remove protection from your original CBZ/CBR. If you intend to replace a protected original, open that file's **Properties** in Explorer and clear **Read-only**. Create WebP Copies leaves the protected original in place. Existing interrupted attempts and retained outputs still require recovery review; clearing the flag does not resolve them automatically.

| Message / code | Why it happens | What to do |
|---|---|---|
| Illegal character in path / invalid temporary folder / Windows filename syntax error | A malformed folder entry, pasted URL/quotes or argument handling can be involved. | Use Browse to choose a subfolder such as `D:\ComicTemp`, without manually adding quotes or a trailing slash. Version 1.1.0 fixes trailing-backslash quoting and normalizes paired outer folder quotes. Do not rename valid spaces, brackets, apostrophes or Unicode names. See [path troubleshooting](#illegal-character-in-path-and-unicode-names). |
| Path too long / could not find part of a checkpoint `.xml...tmp` path / could not save checkpoint | Excessive folder depth, a missing parent or an inaccessible folder; the missing `.tmp` itself is not proof of the cause. | The excessive temporary-name issue is fixed from 1.0.2. Check the failed step/path lengths and the writable per-user installation layout. Preserve Reports/Checkpoints before relocating an installation. Changing comic temporary storage does not move checkpoints. If a book already converted before the warning, inspect its final state before retrying. See [checkpoint paths](#checkpoint-xml-temporary-path-errors). |
| `'charmap' codec can't encode characters` | A tool output-encoding bug can reject characters outside the PC's console code page. | Update to version 1.1.0 for the UTF-8 transport fix. Do not rename the comic to work around valid Unicode. Inspect any retained output through recovery: the run may have built it before reporting failed. |
| Missing file / `FILE_NOT_FOUND` / book file could not be found on disk | A share is offline, a library path is stale, or a required file/tool disappeared. | Verify the exact path in Explorer and ComicRack, reconnect the share or rescan/relink as appropriate. Avoid manually overwriting/moving files repeatedly while benchmarking. Check setup if a tool is missing. |
| Original comic archive is read-only / `SOURCE_ARCHIVE_READ_ONLY` | The original CBZ/CBR has Windows Read-only protection, preventing replacement. This is not an image-corruption verdict. | Clear Read-only in that original file's Properties only if replacement is intended, or use Create WebP Copies. Review any pending attempts/retained outputs before retrying. The tool does not change original flags automatically. |
| `REPLACEMENT_ACCESS_DENIED` / `REPLACEMENT_FILE_LOCKED` | Windows blocked the named replacement step through access restrictions or a file lock. Encoding may already have succeeded. | Inspect Failed step, Suggested action and Technical diagnostic. Keep the original, converted output and recovery record; resolve the access/lock problem and use interrupted-work review. |
| Access denied / `FILE_ACCESS_ERROR` / sharing violation / WinError 5 | Permissions, a file lock or security software. | The archived read-only attribute issue is fixed from 1.0.2. Check the named file and folder access; close programs holding it open. Review a specific security-software event if present. Do not assume image damage or broadly disable security protection. |
| `DISK_SPACE_ERROR` / insufficient temporary/output staging space | The working or output volume lacks the required space, sometimes based on a conservative estimate. | Free space on both locations, including preview/backups/output space. Local temporary storage reduces NAS work but final archives are still staged beside their sources. |
| `MEMORY_ERROR` / out of memory | Concurrent large pages exceed available memory. | Reduce concurrent page workers and close other memory-heavy apps. Test a smaller selection. More workers are not always faster. |
| Temporary work folder could not be removed / `TEMP_CLEANUP_ERROR` / cleanup warning | A temporary file is locked, protected or inaccessible. | Confirm processing has stopped, inspect the exact generated folder and resolve the lock/access issue. Remove only verified unused work files, not an entire source folder. Cleanup warnings may stop later books. |
| Redirected temporary member / temporary attribute change outside root refused | Extracted paths redirect outside their owned work area or fail its safety checks. | Keep the source, inspect a separate copy and report the member name. Do not bypass the boundary check or change permissions on the redirected target. |
| Could not save settings/report/history / report storage warning | Its destination is missing, unwritable, full or otherwise unavailable. | Inspect the exact destination and original error. Prefer the per-user installation folder. A source-folder report-copy warning may leave a valid central report; check it before rerunning already completed conversions. |

### Archive and page problems

| Message / code | Why it happens | What to do |
|---|---|---|
| Headers Error / `ARCHIVE_HEADERS_ERROR` | The archive reader found invalid member/header structure. Possible causes include mismatched local/directory names and damaged compressed data. | Test the original archive with 7-Zip. Restore a verified good copy or investigate recovery on a separate copy. Do not skip the failed member. |
| CRC failed / Data Error / archive integrity test failed | Member data does not pass integrity checks, or decompression cannot complete. | Test the original independently. If repeatable, restore a good archive; check storage/network health if unrelated files begin failing too. A failure alone does not identify which device caused the damage. |
| `ARCHIVE_EXTRACTION_ERROR` / could not extract archive | Extraction failed; corruption, unsupported/encrypted content, access or storage problems are possible. | Read the technical diagnostic before deciding the cause. Open/test the archive manually; confirm it can be extracted without a password into accessible storage. |
| Source image problem / `SOURCE_IMAGE_UNREADABLE` / cannot identify image / broken data stream / Truncated File Read / JPEG datastream contains no image | The page cannot be decoded; image data may be damaged, malformed or unsupported. ZIP CRC success does not establish valid image content. | Inspect the named original page and restore a clean page/archive if needed. Some readers tolerate malformed data, so opening in one reader is not conclusive. Do not silently substitute a blank page or enable tolerant decoding. |
| `PAGE_PROCESSING_ERROR` / source check inconclusive | Processing failed and the follow-up source check could not establish the cause. | Keep the original and share the complete technical diagnostic; do not assume a damaged comic. |
| `SOURCE_READ_ERROR` | The page could not be read from storage; image corruption has not been established. | Check access, share availability and the raw I/O error. Retry only after resolving the read problem. |
| `ENCODER_ERROR` / `OUTPUT_IMAGE_INVALID` / converted format or dimensions do not match | An encoder/output step failed even though a source decode check succeeded, or output validation rejected the result. | Keep the original. Check the selected encoder/setup, review the diagnostic and report a reproducible case. Do not treat this as a confirmed corrupt source. |
| `IMAGE_SAFETY_LIMIT` / decompression-bomb error | The decoder rejects unusually large image dimensions as a safety measure. | Inspect the source dimensions. This does not mean the image is corrupt; do not disable the protection blindly. Share dimensions and the error for review. |
| Page name collision | Two inputs would use the same WebP name, such as `001.jpg` plus `001.webp` or `001.jpeg`. Both may be readable. | Inspect duplicates versus distinct pages, then rename/repack a separate copy while preserving intended page order. The tool must not overwrite or drop either page automatically. |
| Duplicate archive member names / missing, unexpected or duplicate output members / page count changed | Archive names are ambiguous or staged/output contents do not match the expected book. | Keep the original and failed-output diagnostics. Inspect names/counts in a separate copy. Report unexpected output changes; do not bypass the manifest check. |
| Output member content mismatch | Preserved/staged bytes differ from the rebuilt archive. | Do not use that output as a replacement. Retain the original and diagnostic for investigation; this is not proof that the original comic was corrupt. |
| Error naming `__MACOSX/._...jpg` | AppleDouble metadata was mistaken for an image page. | Misidentification of these sidecars is fixed from 1.0.2. Those known sidecars are preserved as attachments with integrity checks; normal image failures still require investigation. |

### Replacement, resume and recovery guards

| Message / symptom | Why it happens | What to do |
|---|---|---|
| Interrupted attempt needs inspection / pending checkpoint | The tool cannot safely establish that earlier work finished. It is not a corruption verdict. | Open Tools & recovery > Review interrupted work > Check files. Confirm the helper stopped and inspect named files. Use Allow retry only when enabled. Keep tracking records; missing output alone does not establish that work stopped. |
| Helper still running / files changed since check / Check files first | A retry would race active work or rely on stale inspection results. | Wait for or resolve the earlier process, then check files again. Do not run concurrent optimizer sessions against the same comic. |
| Source archive changed during conversion/inspection | Another action changed the input while it was being read. | Stop concurrent editing/sync/restoration of that comic, confirm the intended source, then retry through recovery if required. |
| `DESTINATION_EXISTS` / destination/output already exists / refusing to overwrite | A copy, final CBZ or retained output occupies the planned path. | Inspect both files and decide which to keep/relink using the [recovery guide](#replacement-recovery). Do not delete the existing file merely to silence the guard. |
| Replace step failed / unresolved recovery record | Filename replacement or library update did not finish normally. | Preserve source, converted/rollback files and the `.webp-recovery.txt` record. Follow [replacement recovery](#replacement-recovery); do not repeatedly rerun replacement. |
| Converted temporary file not found / worker exited with an error after reporting success | Expected output is missing or the worker's final outcome is inconsistent. | Preserve tracking records and inspect actual source/output state. Check storage/security events and report the complete diagnostic before retrying. |
| Invalid/unsupported checkpoint or record belongs to another source | Tracking data is damaged, incompatible or does not describe the selected file. | Preserve the record, verify the selected path and use supported recovery review. Do not edit XML or delete all checkpoints to force a run. |
| Prefetch checksum/identity mismatch / unsafe or redirected cache refused | A cache changed, no longer matches its source, or fails a safety-boundary check. | Stop and inspect the named cache/source; disable optional prefetch for a later controlled test if needed. Do not weaken cache checks or delete unrelated folders. |

### History, previews and display

| Message / symptom | Why it happens | What to do |
|---|---|---|
| Separate history window closed unexpectedly / history runtime not found | The independent host could not start/load, policy blocked it, or it failed. | Fully restart ComicRack and confirm its installation files. Share `Reports/history-diagnostic.log` and `Reports/history-helper-error.log` if present; include the plugin/ComicRack versions. |
| Previews unavailable / no native preview images | Samples were deleted, retention was disabled, files are incomplete, or the report has no native preview data. | The text report remains usable. Run a new quality comparison with Keep preview pages enabled. Deleted previews cannot be reconstructed from the report alone. |
| Preview cleanup failed / redirected folder refused | A lock, permission issue or unsafe target prevented deletion. | Close viewers, verify the exact generated preview-run folder, and resolve access. Do not broaden cleanup to source comics or all Reports. |
| Difference analysis requires matching dimensions / exceeds 16 million pixels | The pair is not comparable pixel-for-pixel or exceeds the preview-analysis memory limit. | Use original-dimension comparison pairs or inspect visually. This limit affects optional diagnostics, not a corruption verdict or normal conversion policy. |
| Could not copy/save selected details | Clipboard or destination access failed. | Retry copying, select/copy text manually, or choose a writable save destination. The original report remains available. |

### Skips and incomplete runs are not necessarily errors

| Outcome | Meaning and next step |
|---|---|
| Skipped - size policy / output not smaller | The tested quality/policy did not meet the savings threshold. No repair is needed. Leave it or explicitly test different settings. |
| Already WebP / resumed completed book | No new conversion is needed for the recognized content/settings. Historical savings are not counted as newly reclaimed space. |
| PNG-only/PNG-heavy / CBR skipped by option / unsupported type | The archive is outside the selected/current conversion policy. Review the reason/options; this does not establish corruption. |
| No supported image pages | The archive may contain unsupported formats or no actual pages. Inspect its contents before changing anything. |
| Outside sample / not sampled | A quality or worker test intentionally selected only a few eligible books. |
| Not processed / stopped by user | The active work finished at its safe stopping point; later books were untouched. Reselect the batch with compatible resume settings to continue. |

### If the message is not listed

If your error is not listed here, select the failed book in **Book results** and choose **Copy entry**. You can also open **View entry** and choose **Copy details**. Paste the copied error into a comment on the tool's Reddit announcement post or a new [GitHub issue](https://github.com/RayRayElite/comicrack-webp-optimizer/issues).

Include your plugin/ComicRack versions, what action you were running, encoder/quality, worker count, and whether the comics and temporary folder are local or on a NAS. Redact personal paths before posting, but preserve unusual filename characters and approximate path length when relevant. Keep the original comic and any recovery records or retained outputs until the failure has been investigated.
