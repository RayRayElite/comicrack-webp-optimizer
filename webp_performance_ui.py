# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""[B01-B04] Native performance tests; executed in the adapter's namespace.

Tests reuse the real converter and validator, but never call replacement,
checkpoint or library-tag writers. Only the exact generated outputs are removed.
"""
PAGE_WORKER_VALUES = ["1", "2", "4", "6", "8", "10", "12"]


def _cleanup_prefetch(python_tool, options):
    """Ask CPython to validate the owned cache path before deleting its files."""
    info = ProcessStartInfo()
    info.FileName = python_tool
    info.Arguments = ("-3 " if python_tool == "py" else "") + _quote_argument(HELPER_SCRIPT)
    info.Arguments += " --cleanup-prefetch " + _quote_argument(options["prefetch_record"])
    info.Arguments += " --work-dir " + _quote_argument(options["work_dir"])
    info.UseShellExecute, info.CreateNoWindow = False, True
    info.RedirectStandardOutput, info.RedirectStandardError = True, True
    process = Process()
    process.StartInfo = info
    try:
        output, error = _wait_for_process(process)
        if process.ExitCode != 0:
            raise Exception("Cache cleanup failed: " + _safe_unicode(error))
        options["prefetch_record"] = ""
    finally:
        process.Dispose()


class PerformanceSetupForm(Form):
    # [B01] Explicit quick/thorough choice; fixed quality, no preview files.
    def __init__(self, options):
        self.Text = "Benchmark your PC and storage"
        self.ClientSize = Size(700, 310)
        self.StartPosition = FormStartPosition.CenterScreen
        _ui_label(self, "Find a useful worker count", 24, 20, 650, 32, True)
        _ui_label(self, "Select unconverted JPEG comics. Up to 3 eligible books are tested at every worker count, using your current quality, encoder and temporary folder. Originals and ComicRack tags stay unchanged.", 24, 64, 650, 62)
        self._repeats = _ui_combo(self, "Test length", ["Quick - one pass", "Thorough - three rotated passes"], 144)
        self._repeats.SelectedIndex = 0
        _ui_label(self, "Quick runs make up to 21 full conversions; thorough runs up to 63. Caches and other apps affect results. Temporary archives are validated, then deleted after every test.", 24, 190, 650, 52)
        start, cancel = Button(), Button()
        start.Text, cancel.Text = "Start benchmark", "Cancel"
        start.Location, start.Size = Point(390, 262), Size(145, 32)
        cancel.Location, cancel.Size = Point(546, 262), Size(125, 32)
        start.DialogResult, cancel.DialogResult = DialogResult.OK, DialogResult.Cancel
        self.Controls.Add(start)
        self.Controls.Add(cancel)


class PerformanceResultsForm(Form):
    # [B02] At-a-glance totals with the complete raw report on another tab.
    def __init__(self, summaries, report, path, recommended):
        self.Text = "Worker benchmark results"
        self.ClientSize = Size(1120, 650)
        self.StartPosition = FormStartPosition.CenterScreen
        self.applied_workers = None
        _ui_label(self, "Fastest measured: " + recommended + " workers" if recommended else "Benchmark incomplete - no recommendation", 24, 20, 1070, 34, True)
        _ui_label(self, "Measured full conversion throughput, including validation. RAM is a sampled process estimate; process I/O is not physical disk or NAS traffic. CPU is a percentage of the whole PC.", 24, 64, 1070, 48)
        tabs = _new_tabs()
        tabs.Location, tabs.Size = Point(20, 128), Size(1080, 440)
        overview, details = TabPage("Measurements"), TabPage("Full report")
        tabs.TabPages.Add(overview)
        tabs.TabPages.Add(details)
        table = _new_listview()
        table.Dock, table.View = DockStyle.Fill, View.Details
        for title, width in [("Workers", 65), ("Tests", 65), ("MB/s", 75), ("Pages/s", 75), ("CPU avg", 80), ("RAM MB", 85), ("Read MB/s*", 100), ("Write MB/s*", 100), ("Longest stage", 135), ("Result", 220)]:
            table.Columns.Add(title, width)
        for row in summaries:
            item = ListViewItem(row[0])
            for value in row[1:]:
                item.SubItems.Add(_safe_unicode(value))
            table.Items.Add(item)
        overview.Controls.Add(table)
        text = TextBox()
        text.Multiline, text.ReadOnly, text.WordWrap = True, True, False
        text.ScrollBars = System.Windows.Forms.ScrollBars.Both
        text.Dock, text.Text = DockStyle.Fill, report
        details.Controls.Add(text)
        self.Controls.Add(tabs)
        _ui_label(self, "* Logical I/O, including cached/temp activity. Reports: " + path, 24, 578, 720, 54)
        apply, close = Button(), Button()
        apply.Text, apply.Enabled = "Use " + (recommended or "-") + " workers", bool(recommended)
        apply.Location, apply.Size = Point(770, 594), Size(180, 34)
        def accept(sender, event):
            self.applied_workers = recommended
            self.Close()
        apply.Click += accept
        close.Text, close.DialogResult = "Close", DialogResult.Cancel
        close.Location, close.Size = Point(964, 594), Size(130, 34)
        self.Controls.Add(apply)
        self.Controls.Add(close)


def _performance_summary(measurements, expected):
    """[B03] Compare complete equal workloads only; never recommend partial runs."""
    rows, candidates = [], []
    for worker in PAGE_WORKER_VALUES:
        trials = [r for r in measurements if r["workers"] == worker]
        good = [r for r in trials if r.get("STATUS") == "OK"]
        complete = len(good) == expected and len(trials) == expected
        seconds = sum(float(r.get("TIME_TOTAL_SECONDS", "0")) for r in good)
        rate = sum(float(r.get("SOURCE_SIZE", "0")) for r in good) / 1048576.0 / seconds if seconds else 0.0
        pages = sum(float(r.get("CONVERTED_PAGES", "0")) for r in good) / seconds if seconds else 0.0
        def weighted(key):
            return "{0:.1f}".format(sum(float(r.get(key, "0")) * float(r.get("TIME_TOTAL_SECONDS", "0")) for r in good) / seconds) if seconds and all(key in r for r in good) else "n/a"
        ram = "{0:.0f}".format(max(float(r.get("RESOURCE_RAM_PEAK_MB", "0")) for r in good)) if good else "n/a"
        stages = [(sum(float(r.get("TIME_" + stage + "_SECONDS", "0")) for r in good), stage.lower()) for stage in ["EXTRACT", "ENCODE", "REBUILD", "VALIDATE"]]
        status = "Complete" if complete else "Incomplete / failed"
        if complete:
            candidates.append((rate, worker))
        rows.append([worker, str(len(good)) + "/" + str(expected), "{0:.2f}".format(rate), "{0:.2f}".format(pages), weighted("RESOURCE_CPU_AVG_PERCENT"), ram, weighted("RESOURCE_READ_MBPS"), weighted("RESOURCE_WRITE_MBPS"), max(stages)[1] if good else "-", status])
    # Compare only when every worker count completed the identical workload.
    return rows, max(candidates)[1] if len(candidates) == len(PAGE_WORKER_VALUES) else ""


def _run_performance_test(books, options):
    """[B04] Sequential disposable trials; Stop finishes the active test archive."""
    python, archive_tool = _find_python_tool(), _find_archive_tool()
    if not books or not python or not archive_tool:
        MessageBox.Show("Select unconverted JPEG comics and check Python/7-Zip setup first.", "Worker benchmark")
        return None
    setup = PerformanceSetupForm(options)
    _set_ui_theme(bool(options.get("dark_mode", False)), setup)
    try:
        if setup.ShowDialog() != DialogResult.OK:
            return None
        repeats = 1 if setup._repeats.SelectedIndex == 0 else 3
    finally:
        setup.Dispose()
    progress = ProgressForm()
    progress.Show()
    samples, measurements = [], []
    awake = None
    try:
        awake = _begin_keep_awake(options)
        total = len(books)
        # Try spaced selections first; continue looking if these are ineligible.
        order = sorted(set([0, total // 2, total - 1]))
        order.extend(i for i in range(total) if i not in order)
        for index in order:
            if len(samples) == 3 or progress.stop_requested:
                break
            progress.update_state(0, "Finding JPEG sample books", _safe_unicode(getattr(books[index], "Caption", "")), index + 1, total, 0)
            result = _scan_book(books[index], archive_tool)
            if result.get("eligible") and result.get("image_format") == "JPG":
                info = FileInfo(result["file_path"])
                result["benchmark_signature"] = (info.Length, info.LastWriteTimeUtc.Ticks)
                samples.append((books[index], result))
        if not samples:
            MessageBox.Show("No eligible JPEG-only sample books found. Choose originals rather than already converted WebP books.", "Worker benchmark")
            return None
        count = len(samples) * repeats * len(PAGE_WORKER_VALUES)
        progress.set_batch([book for _ in range(repeats * len(PAGE_WORKER_VALUES)) for book, result in samples])
        progress._unit = "benchmark trials finished"
        for repeat in range(repeats):
            # Rotate order across thorough passes to reduce order/cache bias.
            offset = (repeat * 2) % len(PAGE_WORKER_VALUES)
            order = PAGE_WORKER_VALUES[offset:] + PAGE_WORKER_VALUES[:offset]
            for workers in order:
                for book, result in samples:
                    if progress.stop_requested:
                        break
                    trial = dict(options)
                    trial.update({"run_mode": "Test savings & quality", "size_policy": "Keep All Results", "page_workers": workers, "_measure_resources": True, "_progress_form": progress, "prefetch_record": "", "prefetch_next": "", "preview_dir": ""})
                    # Output location matches real runs, even when work storage is local.
                    trial["trial_output_path"] = Path.Combine(Path.GetDirectoryName(result["file_path"]), "webp_perf_" + System.Guid.NewGuid().ToString("N") + _get_output_extension(result, trial))
                    if _is_cbr_rebuild_mode(trial):
                        trial["rar_tool"] = _find_rar_tool() or ""
                    progress.update_state(int(len(measurements) * 100.0 / count), "Testing " + workers + " workers - pass " + str(repeat + 1), result.get("caption", ""), len(measurements) + 1, count, len(measurements))
                    if progress.stop_requested:
                        break
                    try:
                        measured = _run_conversion_helper(python, archive_tool, result, trial, book)
                    except Exception, ex:
                        measured = {"STATUS": "ERROR", "MESSAGE": _safe_unicode(ex)}
                    finally:
                        # Exact caller-generated output only; never delete sources.
                        output = trial["trial_output_path"]
                        if File.Exists(output):
                            try:
                                File.Delete(output)
                            except Exception, ex:
                                progress.stop_requested = True
                                measured = {"STATUS": "ERROR", "MESSAGE": "Remove benchmark output manually: " + output + ". " + _safe_unicode(ex)}
                    if measured.get("STATUS") == "OK" and measured.get("SOURCE_SIGNATURE") != result.get("benchmark_signature"):
                        measured["STATUS"] = "ERROR"
                        measured["MESSAGE"] = "Source changed between benchmark passes; results excluded."
                    measured.update({"workers": workers, "pass": str(repeat + 1), "source": result.get("file_path", "")})
                    measurements.append(measured)
                    progress.record_work(measured)
                    if measured.get("STATUS") != "OK" or measured.get("CLEANUP_WARNING"):
                        progress.stop_requested = True
                if progress.stop_requested:
                    break
            if progress.stop_requested:
                break
    finally:
        progress.finish()
        _end_keep_awake(awake)
    rows, recommended = _performance_summary(measurements, len(samples) * repeats)
    report = ["WebP Optimizer worker benchmark", "Generated: " + DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"), "Quality: " + options.get("quality_mode", QUALITY_MODE_VALUES[0]), "Encoder: " + options.get("encoder_backend", ENCODER_BACKEND_VALUES[0]), "Resize: " + options.get("resize_mode", "No Resize"), "Temporary folder: " + (options.get("work_dir") or "Beside each source"), "PC priority: " + options.get("resource_profile", "Normal"), "Recommended workers: " + (recommended or "None - incomplete benchmark"), "", "CPU is normalized across all logical processors. RAM/private commit are sampled aggregates of helper and directly launched tools, and can include shared pages. Short peaks may be missed. Logical process read/write counters include cached activity and do not measure physical disks or network traffic.", "Longest stage identifies where this sample spent time; it does not prove a hardware bottleneck. Encoding can be CPU-limited; extraction/rebuild can be storage-limited. Low CPU alone is not proof. Caches, antivirus and other applications affect runs. Rerun on representative originals before choosing settings.", ""]
    for row in rows:
        report.append(" | ".join(row))
    for index, measured in enumerate(measurements):
        report.extend(["", "Trial " + str(index + 1)])
        for key in sorted(measured):
            report.append(_safe_unicode(key) + ": " + _safe_unicode(measured[key]))
    folder = Path.Combine(REPORT_DIR, "PerformanceTests", System.Guid.NewGuid().ToString("N"))
    _ensure_directory(folder)
    path = Path.Combine(folder, "report.txt")
    report = "\r\n".join(report)
    _write_text_file(path, report)
    csv = ["Workers,Tests,MB/s,Pages/s,CPU average %,RAM peak MB,Logical read MB/s,Logical write MB/s,Longest stage,Result"]
    csv.extend(",".join('"' + _safe_unicode(value).replace('"', '""') + '"' for value in row) for row in rows)
    _write_text_file(Path.Combine(folder, "summary.csv"), "\r\n".join(csv))
    form = PerformanceResultsForm(rows, report, path, recommended)
    try:
        form.ShowDialog()
        return form.applied_workers
    finally:
        form.Dispose()
