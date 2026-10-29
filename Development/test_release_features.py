"""Native 0.9.1 checks: statuses, compatibility, setup, recovery and power.

Executed only in render_ui.ps1's isolated IronPython namespace. Media inputs
are generated fixture copies. Power flag/failure cases are mocked, followed by
a brief real acquire/restore check. No power-plan settings are changed.
"""
features_saved = dict((name, globals()[name]) for name in ["REPORT_DIR", "SETTINGS_PATH", "_native_call", "_available_space", "CHECKPOINT_POLICY_VERSION", "HELPER_SCRIPT", "_find_python_tool", "_find_rar_tool", "OptionsForm", "ProgressForm", "ReportForm", "_scan_book", "_write_comicinfo_temp_file", "_write_comicbook_temp_file", "_setup_checks", "_NATIVE_TYPE", "_DARK_MODE"])
features_root = Path.Combine(render_dir, "release-features-" + System.Guid.NewGuid().ToString("N"))
Directory.CreateDirectory(features_root)
try:
    REPORT_DIR = Path.Combine(features_root, "Reports")
    SETTINGS_PATH = Path.Combine(features_root, "settings.xml")
    fixture_root = Path.Combine(SCRIPT_DIR, "Development", "Test Environment", "Trial Helper Checks")
    fixture = next(Path.Combine(folder, "original.cbz") for folder in Directory.GetDirectories(fixture_root) if File.Exists(Path.Combine(folder, "results.json")))
    source = Path.Combine(features_root, "source.cbz")
    File.Copy(fixture, source, False)
    source_bytes = list(File.ReadAllBytes(source))
    class FeatureBook(object):
        def __init__(self, path):
            self.FilePath, self.Caption, self.PagesRead = path, "Generated comic", 12
            self.FileSize = FileInfo(path).Length
            self.values = {}
        def GetCustomValue(self, key):
            return self.values.get(key, "")
        def SetCustomValue(self, key, value):
            self.values[key] = value
    book = FeatureBook(source)
    scan = {"file_path": source, "image_format": "JPG", "eligible": True, "notes": "JPEG pages", "archive_type": "cbz", "caption": "Generated comic"}
    policy = {"run_mode": "Create WebP Copies", "quality_mode": "Q80", "encoder_backend": ENCODER_BACKEND_VALUES[0], "size_policy": "Keep All Results", "page_workers": "2"}
    _set_scan_custom_values(book, scan)
    assert book.values["ImageFormat"] == "JPG" and book.values["WebPStatus"] == "Ready"
    _status_after_conversion(book, scan, {"STATUS": "SKIPPED", "SKIP_REASON": "SIZE_POLICY", "MESSAGE": "Not smaller"}, policy)
    assert book.values["WebPStatus"] == "Skipped - size policy"
    _set_scan_custom_values(book, scan)
    assert book.values["WebPStatus"] == "Skipped - size policy"
    # Upgrade an unchanged pre-0.9.8 size skip during analysis, without encoding.
    book.values["WebPStatus"] = "Skipped"
    book.values["WebPReason"] = "Converted output was not smaller than the source archive."
    _status_after_scan(book, scan)
    assert book.values["WebPStatus"] == "Skipped - size policy"
    book.values["WebPStatus"] = "Skipped"
    book.values["WebPReason"] = "CBR left unchanged by the selected option"
    _status_after_scan(book, scan)
    assert book.values["WebPStatus"] == "Skipped"
    _status_after_conversion(book, scan, {"STATUS": "SKIPPED", "SKIP_REASON": "RESUMED", "RESUMED_SKIP_REASON": "SIZE_POLICY", "OUTPUT_PATH": ""}, policy)
    assert book.values["WebPStatus"] == "Skipped - size policy"
    File.SetLastWriteTimeUtc(source, DateTime.UtcNow.AddMinutes(2))
    _set_scan_custom_values(book, scan)
    assert book.values["WebPStatus"] == "Ready"
    _status_after_conversion(book, scan, {"STATUS": "OK", "OUTPUT_PATH": "copy.cbz"}, policy)
    assert book.values["WebPStatus"] == "Copy created" and book.values["ImageFormat"] == "JPG"
    before = dict(book.values)
    _status_after_conversion(book, scan, {"STATUS": "OK"}, {"run_mode": "Test savings & quality"})
    assert book.values == before
    _status_after_conversion(book, scan, {"STATUS": "ERROR", "MESSAGE": "Read error"}, policy)
    assert book.values["WebPStatus"] == "Needs attention"
    assert book.PagesRead == 12 and book.FilePath == source
    _status_after_scan(book, {"file_path": source, "image_format": "WEBP"})
    assert book.values["WebPStatus"] == "Already WebP"
    _status_after_scan(book, {"file_path": source, "image_format": "PNG", "notes": "PNG only"})
    assert book.values["WebPStatus"] == "Skipped"

    key = _checkpoint_path(source, policy)
    HELPER_SCRIPT = "A different installation path and timestamp"
    assert _checkpoint_path(source, policy) == key
    HELPER_SCRIPT = features_saved["HELPER_SCRIPT"]
    relabeled = dict(policy)
    relabeled["quality_mode"] = "Q80 - New display wording"
    assert _checkpoint_path(source, relabeled) == key
    CHECKPOINT_POLICY_VERSION = "incompatible-conversion-policy"
    assert _checkpoint_path(source, policy) != key
    CHECKPOINT_POLICY_VERSION = features_saved["CHECKPOINT_POLICY_VERSION"]
    _write_book_checkpoint(scan, policy, "", "skipped", {"STATUS": "SKIPPED", "SKIP_REASON": "SIZE_POLICY"})
    document = _read_checkpoint(key)
    assert document.DocumentElement.GetAttribute("version") == "2"
    assert document.DocumentElement.SelectNodes("Options/Value").Count > 0
    assert _resume_book_checkpoint(source, relabeled) is not None
    print("PASS: workflow status preserves content/reading progress, copy/test semantics, unchanged skips, changed-file refresh and stable explicit checkpoint compatibility")

    # Exercise the actual in-memory Windows bridge and 64-bit space result.
    free = _available_space(features_root)
    assert free is not None and free > 0
    _available_space = lambda path: 1L
    rows, warnings = _preflight_summary([book], policy)
    assert any("exceeds free space" in warning for warning in warnings)
    assert any("retained" in value for name, value in rows if name.strip() == "Extra space scenario")
    analysis_rows, analysis_warnings = _preflight_summary([book], {"run_mode": "Analyze Only"})
    assert not analysis_warnings
    _available_space = features_saved["_available_space"]

    flags = []
    def fake_native(method, arguments):
        assert method == "SetThreadExecutionState"
        flags.append(long(arguments[0]))
        return 0x80000002L  # Simulate an existing host display request.
    _native_call = fake_native
    assert _begin_keep_awake({}) is None and not flags
    previous = _begin_keep_awake({"keep_awake": True})
    _end_keep_awake(previous)
    assert flags == [0x80000001L, 0x80000002L]
    # Restoration must happen even if archive scanning raises unexpectedly.
    class FailProgress(object):
        stop_requested = False
        def Show(self):
            pass
        def update_state(self, *args):
            pass
        def finish(self):
            flags.append("closed")
    def bad_scan(*args):
        raise Exception("Injected scan exception")
    ProgressForm, _scan_book = FailProgress, bad_scan
    flags[:] = []
    try:
        _run_phase_one([book], {"keep_awake": True})
    except Exception, ex:
        assert "Injected scan" in _safe_unicode(ex)
    else:
        raise AssertionError("Injected exception missing")
    assert flags == [0x80000001L, "closed", 0x80000002L]
    ProgressForm, _scan_book = features_saved["ProgressForm"], features_saved["_scan_book"]
    _native_call = features_saved["_native_call"]
    previous = _begin_keep_awake({"keep_awake": True})
    try:
        assert previous is not None
    finally:
        _end_keep_awake(previous)
    print("PASS: quota-aware free-space bridge, retention warnings, optional keep-awake flags and prior-state restoration on exceptions")

    test_options = dict(policy)
    test_options["work_dir"] = features_root
    checked = _setup_checks(test_options)
    assert checked["STATUS"] == "OK", checked
    assert "Encoded and decoded" in checked["CHECK_ENCODER"]
    bad = dict(test_options)
    bad["encoder_backend"] = "Missing encoder"
    assert _setup_checks(bad)["STATUS"] == "ERROR"
    _find_python_tool = lambda: None
    assert "Python 3" in _setup_checks(test_options)["CHECK_MESSAGE"]
    assert _setup_checks({"run_mode": "Analyze Only"})["STATUS"] == "OK"
    _find_python_tool = features_saved["_find_python_tool"]
    _find_rar_tool = lambda: None
    bad = dict(test_options)
    bad["cbr_mode"] = CBR_MODE_VALUES[2]
    assert "WinRAR" in _setup_checks(bad)["CHECK_MESSAGE"]
    _find_rar_tool = features_saved["_find_rar_tool"]
    assert list(File.ReadAllBytes(source)) == source_bytes
    assert not list(Directory.GetDirectories(features_root, "setup_check_*"))
    print("PASS: generated setup checks, actual encoder/7-Zip execution, missing Python/encoder/WinRAR instructions and analysis without Python")

    # Cancellation must happen before setup probes or any comic processing.
    class CancelOptions(object):
        def __init__(self):
            self.options = dict(policy)
            self.options["_show_preflight"] = True
        def ShowDialog(self):
            return DialogResult.OK
    def forbidden_setup(options):
        raise Exception("Setup ran after preflight cancellation")
    cancel_timer = Timer()
    cancel_timer.Interval = 100
    def cancel_preflight(sender, event):
        for form in list(Application.OpenForms):
            if isinstance(form, PreflightForm):
                cancel_timer.Stop()
                form.DialogResult = DialogResult.Cancel
                form.Close()
    cancel_timer.Tick += cancel_preflight
    OptionsForm, _setup_checks = CancelOptions, forbidden_setup
    cancel_timer.Start()
    try:
        _run_phase_two([book])
    finally:
        cancel_timer.Stop()
        cancel_timer.Dispose()
        OptionsForm, _setup_checks = features_saved["OptionsForm"], features_saved["_setup_checks"]
    assert list(File.ReadAllBytes(source)) == source_bytes

    # A real stdout reader delivers page records on the UI thread, not the
    # asynchronous pipe callback thread, and leaves terminal results intact.
    messages, threads = [], []
    ui_thread = System.Threading.Thread.CurrentThread.ManagedThreadId
    info = ProcessStartInfo()
    info.FileName = "powershell.exe"
    info.Arguments = '-NoProfile -Command "[Console]::Out.WriteLine(\'PROGRESS=ENCODING|1|3\'); Start-Sleep -Milliseconds 250; [Console]::Out.WriteLine(\'PROGRESS=ENCODING|3|3\'); [Console]::Out.WriteLine(\'STATUS=OK\')"'
    info.UseShellExecute, info.CreateNoWindow = False, True
    info.RedirectStandardOutput = info.RedirectStandardError = True
    child = Process()
    child.StartInfo = info
    def received(message):
        messages.append(message)
        threads.append(System.Threading.Thread.CurrentThread.ManagedThreadId)
    try:
        output_text, error_text = _wait_for_process(child, received)
        assert child.ExitCode == 0 and "STATUS=OK" in output_text
        assert "PROGRESS=" not in output_text
        assert messages[0] == "ENCODING|1|3" and messages[-1] == "ENCODING|3|3"
        assert all(thread == ui_thread for thread in threads)
    finally:
        child.Dispose()
    print("PASS: cancel-before-work, real pipe progress delivered on the UI thread and actual Windows keep-awake acquire/restore")

    # Follow the accepted preflight path all the way through a real conversion.
    pipeline_source = Path.Combine(features_root, "pipeline.cbz")
    File.Copy(fixture, pipeline_source, False)
    pipeline_book = FeatureBook(pipeline_source)
    pipeline_before = list(File.ReadAllBytes(pipeline_source))
    class StartOptions(object):
        def __init__(self):
            self.options = dict(policy)
            self.options["_show_preflight"] = True
        def ShowDialog(self):
            return DialogResult.OK
    reports = []
    class CaptureReport(object):
        def Dispose(self): pass
        def __init__(self, text, path, **kwargs):
            self.retry_request = None
            reports.append(text)
        def ShowDialog(self):
            pass
    live_stages = []
    def HiddenProgress():
        progress = features_saved["ProgressForm"]()
        progress.Opacity, progress.ShowInTaskbar = 0, False
        real_update = progress.update_archive_progress
        def update(message):
            live_stages.append(message)
            real_update(message)
        progress.update_archive_progress = update
        return progress
    accept_timer = Timer()
    accept_timer.Interval = 100
    def accept_preflight(sender, event):
        for form in list(Application.OpenForms):
            if isinstance(form, PreflightForm):
                accept_timer.Stop()
                form.DialogResult = DialogResult.OK
                form.Close()
    accept_timer.Tick += accept_preflight
    OptionsForm, ProgressForm, ReportForm = StartOptions, HiddenProgress, CaptureReport
    _write_comicinfo_temp_file, _write_comicbook_temp_file = lambda *args: "", lambda *args: ""
    accept_timer.Start()
    try:
        _run_phase_two([pipeline_book])
    finally:
        accept_timer.Stop()
        accept_timer.Dispose()
        OptionsForm, ProgressForm, ReportForm = features_saved["OptionsForm"], features_saved["ProgressForm"], features_saved["ReportForm"]
        _write_comicinfo_temp_file, _write_comicbook_temp_file = features_saved["_write_comicinfo_temp_file"], features_saved["_write_comicbook_temp_file"]
    assert "Converted Books: 1" in reports[-1] and live_stages
    assert pipeline_book.values["WebPStatus"] == "Copy created" and pipeline_book.values["ImageFormat"] == "JPG"
    assert pipeline_book.PagesRead == 12 and list(File.ReadAllBytes(pipeline_source)) == pipeline_before
    assert File.Exists(Path.Combine(features_root, "pipeline [WebP].cbz"))
    print("PASS: accepted preflight -> setup -> live progress -> actual copy -> workflow status/checkpoint/report, with unchanged source")

    output = Path.Combine(features_root, "interrupted-output.cbz")
    _write_book_checkpoint(scan, policy, output, "pending")
    record = next(item for item in _load_recovery_items([book]) if item["source"] == source)
    checks = _check_recovery_item(record)
    assert checks["SourceValid"]
    try:
        _allow_recovery_retry(record, False)
    except Exception:
        pass
    else:
        raise AssertionError("Retry allowed without helper-stop confirmation")
    folder = _allow_recovery_retry(record, True)
    assert Directory.Exists(folder) and File.Exists(Path.Combine(folder, "Resolution.txt"))
    assert not File.Exists(_pending_checkpoint_path(source)) and not File.Exists(key)
    assert list(File.ReadAllBytes(source)) == source_bytes

    # Existing output is kept and blocks retry. Resolve it by moving it, then recheck.
    _write_book_checkpoint(scan, policy, output, "pending")
    File.Copy(source, output, False)
    record = next(item for item in _load_recovery_items([book]) if item["source"] == source)
    assert _check_recovery_item(record)["ConvertedValid"]
    try:
        _allow_recovery_retry(record, True)
    except Exception, ex:
        assert "converted" in _safe_unicode(ex)
    else:
        raise AssertionError("Existing output was discarded or silently accepted")
    kept = Path.Combine(features_root, "kept-output.cbz")
    File.Move(output, kept)
    try:
        _allow_recovery_retry(record, True)
    except Exception, ex:
        assert "changed" in _safe_unicode(ex)
    else:
        raise AssertionError("Stale readability check accepted")
    _check_recovery_item(record)
    _allow_recovery_retry(record, True)
    assert File.Exists(kept)

    # A live helper identity blocks checks even after the confirmation box is ticked.
    _write_book_checkpoint(scan, policy, output, "pending")
    current_process = Process.GetCurrentProcess()
    _record_worker_started(source, policy, current_process)
    current_process.Dispose()
    record = next(item for item in _load_recovery_items([book]) if item["source"] == source)
    try:
        _check_recovery_item(record)
    except Exception, ex:
        assert "still running" in _safe_unicode(ex)
    else:
        raise AssertionError("Active helper ignored")
    # Write a fresh controlled pending record with no active worker.
    _write_book_checkpoint(scan, policy, output, "pending")
    record = next(item for item in _load_recovery_items([book]) if item["source"] == source)
    _check_recovery_item(record)
    outside = Path.Combine(features_root, "unrelated.xml")
    _write_text_file(outside, "keep this file")
    record["policy"] = outside
    try:
        _allow_recovery_retry(record, True)
    except Exception, ex:
        assert "outside" in _safe_unicode(ex)
    else:
        raise AssertionError("Outside tracking path accepted")
    assert File.ReadAllText(outside) == "keep this file" and File.Exists(_pending_checkpoint_path(source))
    print("PASS: read-only recovery validation, confirmed retry, archived records, retained outputs, stale-check rejection, active helper detection and out-of-scope metadata protection")

    # Legacy source-side recovery notes also expose the converted/rollback paths.
    legacy_source = Path.Combine(features_root, "legacy.cbz")
    File.Copy(fixture, legacy_source, False)
    legacy_output = Path.Combine(features_root, "legacy-converted.cbz")
    rollback = legacy_source + ".webp-rollback-test"
    journal = legacy_source + ".webp-recovery.txt"
    _write_text_file(journal, "WebP replacement recovery record\nSource: " + legacy_source + "\nConverted: " + legacy_output + "\nFinal: " + legacy_source + "\nRollback: " + rollback + "\nBackup: \n")
    legacy = next(item for item in _load_recovery_items([FeatureBook(legacy_source)]) if item["source"] == legacy_source)
    assert ("Converted", legacy_output) in _recovery_paths(legacy)
    _check_recovery_item(legacy)
    _allow_recovery_retry(legacy, True)
    assert not File.Exists(journal) and File.Exists(legacy_source)

    # Render all new dialogs and the live stage display without interacting with media.
    def render_feature(form, name):
        form.Opacity, form.ShowInTaskbar = 0, False
        form.Show()
        Application.DoEvents()
        bitmap = Bitmap(form.Width, form.Height)
        form.DrawToBitmap(bitmap, Rectangle(0, 0, form.Width, form.Height))
        bitmap.Save(Path.Combine(render_dir, name + ".png"), ImageFormat.Png)
        bitmap.Dispose()
        form.Close()
        form.Dispose()
    render_feature(PreflightForm([book], policy), "preflight")
    render_feature(SetupForm({"run_mode": "Analyze Only"}), "setup")
    render_feature(RecoveryForm([book]), "recovery")
    progress = ProgressForm()
    progress.update_state(0, "Converting and validating archives", "Generated comic", 1, 2, 0)
    progress.update_archive_progress("ENCODING|18|42")
    assert progress._stage_label.Text == "Encoding page 18 of 42"
    assert progress._completed == 0 and progress._detail_label.Text == "Generated comic"
    progress.update_archive_progress("bad record")
    assert progress._stage_label.Text == "Encoding page 18 of 42"
    progress._finished = True
    render_feature(progress, "live-page-progress")
    form = OptionsForm()
    form._awake_checkbox.Checked = True
    form._save(None, None)
    form.Dispose()
    form = OptionsForm()
    assert form._awake_checkbox.Checked
    form._reset_settings(None, None)
    assert not form._awake_checkbox.Checked
    form.Dispose()
    print("PASS: native setup/preflight/recovery renders, live page display and remembered opt-in power setting")
    # Actual native controls: theme round trip, retained text and search/wrap.
    form = OptionsForm()
    form._dark_checkbox.Checked = False
    light = form.BackColor
    form._dark_checkbox.Checked = True
    assert form.BackColor == Color.FromArgb(28, 30, 34)
    assert form._collect_options()["dark_mode"]
    form._save(None, None)
    form.Dispose()
    form = OptionsForm()
    assert form._dark_checkbox.Checked
    assert form._mode_combo.Dark and form._quality_combo.Dark
    assert not form._quality_combo.Enabled
    assert form._ok_button.FlatStyle == System.Windows.Forms.FlatStyle.Flat
    assert form._backup_checkbox.Dark
    render_feature(form, "dark-workflow-disabled")
    form = OptionsForm()
    form._mode_combo.SelectedIndex = 1
    assert form._quality_combo.Enabled
    render_feature(form, "dark-workflow-enabled")
    form = OptionsForm()
    form._tabs.SelectedIndex = 3
    render_feature(form, "dark-options")
    technical_text = "Generated report\r\nGenerated: today\r\n\r\nPer-book results\r\n  Source: " + ("long-path/" * 30) + "\r\n  Notes: Needle first; needle second; Unicode \u00e9\r\n"
    form = ReportForm(technical_text, Path.Combine(features_root, "reader.txt"))
    form._tabs.SelectedIndex = 1
    form.Opacity, form.ShowInTaskbar = 0, False
    form.Show()
    Application.DoEvents()
    assert form._report_box.Text.splitlines() == technical_text.splitlines()
    assert form._report_box.WordWrap
    form._report_wrap.Checked = False
    assert not form._report_box.WordWrap
    form._report_search.Text = "needle"
    form._report_find.PerformClick()
    first = form._report_box.SelectionStart
    assert form._report_box.SelectedText.lower() == "needle"
    form._report_find.PerformClick()
    assert form._report_box.SelectionStart > first
    assert form._report_text == technical_text
    form._report_wrap.Checked = True
    render_feature(form, "dark-technical-report")
    form = OptionsForm()
    form._dark_checkbox.Checked = False
    assert form.BackColor == light
    form.Dispose()
    form = OptionsForm()
    form.Opacity, form.ShowInTaskbar = 0, False
    form.Show()
    Application.DoEvents()
    form._dark_checkbox.Checked = True
    caption_state = int(_native_call("CaptionThemeState", [form.Handle]))
    assert caption_state in [-1, 1], caption_state
    form._dark_checkbox.Checked = False
    assert int(_native_call("CaptionThemeState", [form.Handle])) in [-1, 0]
    form._dark_checkbox.Checked = True
    # Fullscreen/style changes may recreate handles; the recreated caption stays dark.
    form.FormBorderStyle = FormBorderStyle.Sizable
    Application.DoEvents()
    assert int(_native_call("CaptionThemeState", [form.Handle])) in [-1, 1]
    form.Dispose()
    print("PASS: native title-bar dark/light readback and handle/style-change restoration")
    form = ReportForm("Generated table test\r\nBooks Scanned: 1\r\n", "generated-table.txt", historical=True)
    form.Opacity, form.ShowInTaskbar = 0, False
    _set_ui_theme(True, form)
    form.Show()
    Application.DoEvents()
    table = form._tabs.TabPages[0].Controls[0]
    table.Items.Add(ListViewItem("Generated row"))
    table.Items[0].Selected = True
    assert table.Dark and not table.OwnerDraw
    def assert_header_color(expected):
        table.Refresh()
        Application.DoEvents()
        pixels = Bitmap(table.Width, table.Height)
        try:
            table.DrawToBitmap(pixels, Rectangle(0, 0, table.Width, table.Height))
            for x in [4, table.Columns[0].Width + 4, table.ClientSize.Width - 10]:
                color = pixels.GetPixel(x, 6)
                assert (color.R, color.G, color.B) == expected, (x, color.R, color.G, color.B)
        finally:
            pixels.Dispose()
    assert_header_color((43, 47, 54))  # Includes the unused strip after the last column.
    width = table.Columns[0].Width
    table.Columns[0].Width = width + 12
    assert_header_color((43, 47, 54))
    assert table.Items[0].Selected
    _set_ui_theme(False, form)
    assert not table.Dark and table.Columns[0].Width == width + 12
    _set_ui_theme(True, form)
    render_feature(form, "dark-book-table")
    print("PASS: actual header pixels including empty tail stay grey after resize; native row selection and light-mode restore retained")
    _find_rar_tool = lambda: None
    optional_rar = _setup_checks({"run_mode": "Analyze Only"})
    assert optional_rar["STATUS"] == "OK"
    assert "Optional" in optional_rar["CHECK_RAR"] and "7-Zip" in optional_rar["CHECK_CBR_INPUT"]
    print("PASS: remembered dark palette/light restore, lossless technical reader/search/wrap and optional WinRAR reporting")

finally:
    globals().update(features_saved)
