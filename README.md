# WebP Optimizer

Make room in your comic collection from inside **ComicRack Community Edition**. Analyze selected CBZ/CBR archives, compare image quality, and convert eligible JPEG pages to WebP. Replace originals without keeping permanent duplicates, or create separate copies if you prefer.

**By RayRayElite · Current development build: 0.9.0 · First public stable release planned: 1.0.0**

[Downloads](https://github.com/RayRayElite/comicrack-webp-optimizer/releases) · [Report a bug](https://github.com/RayRayElite/comicrack-webp-optimizer/issues) · [Contribute](CONTRIBUTING.md)

## Why I built it

I was downloading WebP versions of the weekly comic bundles from GetComics and noticed how much smaller they were than the JPEG versions. With a collection over 1 TB and a nearly full comic drive, the potential savings were hard to ignore. Keeping a second copy of everything wasn't practical: I needed a way to convert the books I already had, validate the result, and replace each original without retaining a permanent duplicate.

I already organize my collection in ComicRack CE using public_fred's ComicRack Guru method, so integrating this into that workflow felt like the obvious choice. WebP Optimizer grew from that need. The copy and backup options are there for people with different storage preferences.

## What it does

- Analyze selected books and label their image format for smart-list filtering.
- Convert eligible JPEG pages at Q60–Q90, with **Q80 and original dimensions** as defaults.
- Create copies or replace originals after archive validation; preserve the existing library entry and metadata during replacement.
- Convert CBR to CBZ, skip CBR input, or optionally rebuild CBR with WinRAR.
- Compare Q60/Q70/Q75/Q80/Q90 on up to three books in a native full-screen viewer.
- Use local or source-folder temporary storage, one/two/four page workers, safe stopping and completed-work recognition.
- Review savings, timings, prior reports and retained previews from run history.

Q is an encoder setting, not a percentage of quality retained or space saved. Savings depend on the original pages; already-WebP pages are not recompressed. Temporary space is still needed when replacing without a backup. Start with disposable copies while testing a new setup.

For contributors: start with [Contributing](CONTRIBUTING.md) and the [code map](ARCHITECTURE.md). The runtime source has searchable section IDs and function descriptions; development tools and tests live in [Development](Development/README.md).

## Requirements

- Windows with ComicRack Community Edition and scripting enabled.
- Python 3.9 or newer available as `py` or `python`, with Pillow installed: `py -3 -m pip install Pillow`.
- ComicRack's 7-Zip executable accessible in its Resources folder or a supported portable resources location.
- The supplied `Magick` folder for the default ImageMagick encoder.
- WinRAR `rar.exe` only if rebuilding CBR output. CBR-to-CBZ does not require WinRAR.

## Install

The release ZIP is a manual-install bundle, not a `.crplugin` installer. Close ComicRack, extract its `WebP Optimizer` folder into your ComicRack CE `Scripts` folder, then restart ComicRack. Keep the contents of `Magick` together. For an existing installation, retain your `settings.xml` and `Reports` folder; the release bundle does not contain replacements for them.

Source checkouts exclude encoder executables and Microsoft DLLs. To run/build from source, obtain the appropriate ImageMagick distribution from its upstream project and provide the encoder expected by the plugin. Review [third-party notices](THIRD_PARTY_NOTICES.md) before distributing a binary bundle. The current 0.9 source is for testing; public binary downloads are planned for the 1.0 release.

## Quick start

1. **Analyze your library first.** Select all books in ComicRack's Library, open **Optimize Archives**, choose **Analyze Only**, then click **Analyze**. This adds the `ImageFormat` custom value used by the smart lists below; it does not convert your comics.
2. **Set up the cleanup lists below.** These show books waiting for analysis, analysis errors and books that aren't fully WebP.
3. **Compare a small sample.** Select a few disposable test comics, open **Optimize Archives**, choose **Test savings & quality**, enable **Keep preview pages**, and start. Click **Open previews** in the results to compare quality levels.
4. **Choose how to convert.** Select books from **1.11 Convert To WebP**, open **Optimize Archives** again, and choose **Create WebP Copies** or **Replace Originals**. Decide whether to keep an original backup.
5. **Start converting.** Choose your quality level—**Q80**, **No Resize** and **Only If Smaller** are good starting settings—then click **Start run** and review the results.

**Where to find it:** **Optimize Archives** is the **green square button in the top toolbar**, or right-click your selected books and find it under **Automations**.

### ComicRack Guru cleanup lists

I added these after **1.8 Convert to CBZ** in the Guru workflow's **01 - Clean Up** section. Each list uses **Match All**, searches **Library**, and checks **Custom Value → ImageFormat**.

| Smart list | Rules | Shows |
|---|---|---|
| **1.9 Run Image Format Check** | `ImageFormat` **is** blank | Books that still need Analyze Only. |
| **1.10 ImageFormat Errors** | `ImageFormat` **is** `ERROR` | Books whose archive could not be read during analysis. |
| **1.11 Convert To WebP** | `ImageFormat` **is not** `WEBP` **and is not** blank | Analyzed books that aren't fully WebP. |

For **1.11**, use the rule's **not/negate** toggle for both rows, as shown below. Run Analyze Only on new books from **1.9** to keep the lists up to date. Some books in **1.11**, such as PNG-only archives, may be skipped by the converter; check the results for the reason.

![ComicRack Guru cleanup order with image-format analysis, errors and WebP conversion after Convert to CBZ](docs/images/guru-cleanup-workflow.png)

<details>
<summary>Smart-list setup screenshots</summary>

**1.9 Run Image Format Check** — ImageFormat is blank.

![Run Image Format Check smart list: match all, Custom Value ImageFormat is blank](docs/images/smart-list-image-format-check.png)

**1.10 ImageFormat Errors** — ImageFormat is ERROR.

![ImageFormat Errors smart list: match all, Custom Value ImageFormat is ERROR](docs/images/smart-list-image-format-errors.png)

**1.11 Convert To WebP** — ImageFormat is not WebP and is not blank.

![Convert To WebP smart list: match all, negate ImageFormat is WebP and negate ImageFormat is blank](docs/images/smart-list-convert-to-webp.png)

</details>

## Choose an action

Select books in ComicRack and run **Optimize Archives**.

| Action | Result |
|---|---|
| Analyze Only | Inspect archives and set `ImageFormat` for smart-list filtering. |
| Create WebP Copies | Create separate CBZ/CBR output; keep the source and existing library path. |
| Replace Originals | Validate new output before replacement. Optional original backup. |
| Test savings & quality | Compare Q60/Q70/Q75/Q80/Q90 on up to three eligible books spread through selection order. Original archives remain unchanged. |

Q80 is the balanced default; Q75 prioritizes space. Q is an encoder quality level, not a percentage of quality retained or storage saved. Estimates are measured reference JPEG-page samples, not collection-wide promises. **No Resize** is the default. **Only If Smaller** avoids retaining larger conversion outputs.

ImageMagick is the explicit default. cwebp and Pillow are optional advanced choices; a missing selected encoder produces an error rather than falling back. PNG-only/PNG-heavy books are skipped by the current JPEG-focused rules. Existing WebP pages are not recompressed.

## Quality comparisons

Enable **Keep preview pages** when starting a quality test, then click **Open previews** on the results screen. The native viewer starts maximized and shows the original beside a selectable quality level.

- Wheel: scroll both panes vertically.
- Shift+wheel: scroll both horizontally.
- Ctrl+wheel: zoom both; use 100% to inspect actual image pixels.
- F11: toggle full screen. Escape: return to the window, then to the report.

Quality tests run five conversions per sampled book, so they take longer than a normal conversion.

## Preview storage and cleanup

Previews are stored in the plugin's `Reports/QualityTests` folder. By default, they are deleted when you close the results window. Uncheck **Delete this run's preview images when closing this results window** to keep them for later.

Closing just the comparison viewer keeps the previews available until you close results. Your text reports are kept either way.

## Storage, stopping and reports

- **Temporary storage:** leave blank to work beside each comic, or choose a local folder when using a NAS. Converted archives stay beside their source. Either option needs temporary free space.
- **Stopping:** click **Stop after current book** to finish safely and save a report. Quality tests finish all five quality levels for the active book.
- **Reports:** results show total savings and individual book outcomes. Reports are kept in `Reports`; you can also save them beside the comics.

Settings are remembered when you start a run. Copies and retained backups keep the originals, so they do not reclaim the displayed savings.

## Performance and large batches

In **Performance & resume**, try **2 concurrent pages** for faster conversion, then compare **4** on a small batch. More workers use more memory; the default is **1**. Books are processed one at a time.

For NAS collections, local temporary storage can reduce network traffic. Start with a manageable batch and check free space before increasing its size.

The progress window shows speed and a rough ETA after the first conversion, or the first successful quality pass during a test.

### Continuing after a stop or restart

Keep **Resume completed books with matching settings and unchanged files** enabled. Select your batch again, use the same conversion settings, and start. Recognized completed books are skipped.

If an interrupted attempt needs inspection, follow the report before retrying. See [recovery and resume details](ADVANCED_USAGE.md#continuing-after-a-stop-or-restart) for troubleshooting.

## If a replacement fails

Keep the files and recovery record named in the report until you have checked them. Read the [recovery guide](ADVANCED_USAGE.md#replacement-recovery) before retrying.

## Run history

Click **Run history** in the options window to reopen reports and any previews you kept. You can also open **WebP Optimizer Run History** from ComicRack's library actions without selecting books.

From history you can reopen results, delete saved previews, or use **Prepare new test** to reuse settings for your current selection. Opening an old report keeps its previews unless you explicitly delete them. Deleted previews need a new test to recreate them.

## More help

See [advanced usage and troubleshooting](ADVANCED_USAGE.md) for storage locations, resume rules, report details and recovery steps. Developer instructions are in [CONTRIBUTING.md](CONTRIBUTING.md).

## Contributing and license

Bug reports, workflow feedback and pull requests are welcome. I'd especially appreciate testing across different NAS setups, page types and ComicRack workflows. Read [CONTRIBUTING.md](CONTRIBUTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md) to find the code sections and relevant tests. Please remove personal paths from shared reports and use generated/disposable fixtures.

The plugin code and documentation are licensed under [MIT](LICENSE), copyright 2026 RayRayElite. You can use, modify and redistribute the code under those terms; contributions back to this repository are welcome. ImageMagick and other third-party components retain their own licenses. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Acknowledgements

- **GetComics**, whose smaller weekly WebP bundles inspired the project.
- **[maforget and the ComicRack CE contributors](https://github.com/maforget/ComicRackCE)**, for maintaining ComicRack Community Edition.
- **public_fred**, creator of the ComicRack Guru organization method used in my workflow.
- **ImageMagick Studio LLC and contributors**, for the image-processing tools used by the recommended encoder.

## AI disclosure

This project was created with the help of **GPT 6.1 Sol**, which assisted with coding, debugging, documentation and testing during development.
