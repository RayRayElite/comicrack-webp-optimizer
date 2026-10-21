# Release notes

The first public stable release is planned as **1.0.0**. Entries below are pre-release development milestones. Earlier local 1.x artifact names were internal numbering and have been superseded by this 0.x history.

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
