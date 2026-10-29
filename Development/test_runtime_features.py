"""Executed by render_ui.ps1 inside ComicRack's IronPython runtime, on test fixtures only."""
test_root = Path.Combine(render_dir, "runtime-" + System.Guid.NewGuid().ToString("N"))
Directory.CreateDirectory(test_root)
original_globals = dict((name, globals()[name]) for name in ["SETTINGS_PATH", "REPORT_DIR", "OptionsForm", "ProgressForm", "ReportForm", "_find_archive_tool", "_find_python_tool", "_scan_book", "_set_scan_custom_values", "_run_conversion_helper", "_finalize_replacement", "_update_book_file_path", "_set_converted_custom_values", "_write_comicinfo_temp_file", "_write_comicbook_temp_file"])
try:
    SETTINGS_PATH = Path.Combine(test_root, "settings.xml")
    assert _load_settings() == ({}, "")
    form = OptionsForm()
    form._mode_combo.SelectedItem = "Replace Originals"
    form._quality_combo.SelectedItem = "Q75 - Space Saver"
    form._backup_checkbox.Checked = False
    form._reports_checkbox.Checked = True
    form._work_text.Text = u"D:\\Media & Comics\\caf\u00e9"
    form._save(None, None)
    form.Dispose()
    restored = OptionsForm()
    assert restored._mode_combo.SelectedItem == "Replace Originals"
    assert restored._quality_combo.SelectedItem == "Q75 - Space Saver"
    assert not restored._backup_checkbox.Checked
    assert restored._reports_checkbox.Checked
    assert restored._work_text.Text == u"D:\\Media & Comics\\caf\u00e9"
    before_cancel = File.ReadAllText(SETTINGS_PATH)
    restored._reset_settings(None, None)
    assert restored._mode_combo.SelectedItem == "Analyze Only"
    assert restored._quality_combo.SelectedItem == "Q80 - Balanced (Recommended)"
    restored._cancel(None, None)
    restored.Dispose()
    assert File.ReadAllText(SETTINGS_PATH) == before_cancel
    for legacy in ['Auto (Prefer ImageMagick / CBX-style)', 'ImageMagick (CBX-style)', 'ImageMagick (Tuned)']:
        _save_settings({'encoder_backend': legacy})
        migrated = OptionsForm()
        assert migrated._encoder_combo.SelectedItem == 'ImageMagick (Recommended)'
        assert migrated._encoder_combo.Items.Count == 3
        assert 'No automatic fallback' in migrated._settings_note.Text
        migrated.Dispose()
    _save_settings({"run_mode": "Bogus mode", "quality_mode": "Bogus quality"})
    unknown = OptionsForm()
    assert unknown._mode_combo.SelectedItem == "Analyze Only"
    unknown.Dispose()
    _write_text_file(SETTINGS_PATH, "broken XML")
    bad = OptionsForm()
    assert "could not be read" in bad._settings_note.Text
    bad.Dispose()
    print("PASS: settings round trip, Unicode/XML escaping, restore defaults, cancel preserves settings, invalid values and corrupt file fallback")

    # A real child process floods both pipes; a Windows timer must remain responsive.
    progress = ProgressForm()
    progress.Opacity = 0
    progress.ShowInTaskbar = False
    progress.Show()
    progress.update_state(45, "Converting and validating archives", "Test book", 1, 3, 0)
    click_timer = Timer()
    click_timer.Interval = 100
    def click_stop(sender, event):
        click_timer.Stop()
        state_while_running.append(not process.HasExited)
        progress._request_stop(None, None)
    click_timer.Tick += click_stop
    click_timer.Start()
    info = ProcessStartInfo()
    info.FileName = "powershell.exe"
    info.Arguments = '-NoProfile -Command "1..2000 | ForEach-Object { [Console]::Out.WriteLine(\'output\'); [Console]::Error.WriteLine(\'error\') }; Start-Sleep -Milliseconds 600"'
    info.UseShellExecute = False
    info.CreateNoWindow = True
    info.RedirectStandardOutput = True
    info.RedirectStandardError = True
    process = Process()
    process.StartInfo = info
    state_while_running = []
    output, error = _wait_for_process(process)
    assert process.ExitCode == 0
    assert output.count("output") == 2000 and error.count("error") == 2000
    assert progress.stop_requested and not progress._stop_button.Enabled
    assert state_while_running == [True]
    bitmap = Bitmap(progress.Width, progress.Height)
    progress.DrawToBitmap(bitmap, Rectangle(0, 0, progress.Width, progress.Height))
    bitmap.Save(Path.Combine(render_dir, "progress-stopping.png"), ImageFormat.Png)
    bitmap.Dispose()
    progress.finish()
    click_timer.Dispose()
    process.Dispose()
    print("PASS: UI stop event received while real child runs; both pipes drained; child finishes normally")

    state = {}
    class TestBook(object):
        def __init__(self, index):
            self.Caption = "Book " + str(index)
            self.FilePath = "book" + str(index) + ".cbz"
    books = [TestBook(i) for i in range(3)]
    class TestOptions(object):
        def __init__(self):
            self.options = {"run_mode": "Replace Originals", "quality_mode": "Q80", "cbr_mode": CBR_MODE_VALUES[0], "create_backup": False}
        def ShowDialog(self):
            return DialogResult.OK
    class TestProgress(object):
        def __init__(self):
            self.stop_requested = state["scenario"] == "before_scan"
            state["progress"] = self
        def Show(self):
            pass
        def finish(self):
            state["finished"] = True
        def update_state(self, percent, status, detail, *args):
            if state["scenario"] == "before_convert" and "Converting" in status:
                self.stop_requested = True
    class TestReport(object):
        def Dispose(self): pass
        def __init__(self, text, path, **kwargs):
            self.retry_request = None
            state["report"] = text
        def ShowDialog(self):
            pass
    def scan(book, tool):
        state["scans"] += 1
        if state["scenario"] == "during_scan":
            state["progress"].stop_requested = True
        return {"caption": book.Caption, "file_path": book.FilePath, "eligible": True, "archive_type": "cbz", "image_format": "JPG"}
    def convert(*args):
        state["events"].append("convert")
        if state["scenario"] == "during_convert":
            state["progress"].stop_requested = True
        return {"STATUS": "OK", "SOURCE_SIZE": "100", "OUTPUT_SIZE": "50", "OUTPUT_PATH": "fake.cbz"}
    def finalize(source, result, options):
        state["events"].append("replace")
        return result
    def metadata(*args):
        state["events"].append("metadata")
    OptionsForm, ProgressForm, ReportForm = TestOptions, TestProgress, TestReport
    _find_archive_tool = lambda: "unused-tool"
    _find_python_tool = lambda: "unused-python"
    _scan_book = scan
    _set_scan_custom_values = lambda *args: None
    _run_conversion_helper = convert
    _finalize_replacement = finalize
    _update_book_file_path = lambda *args: None
    _set_converted_custom_values = metadata
    REPORT_DIR = test_root
    for scenario, expected in [("before_scan", 0), ("during_scan", 0), ("before_convert", 0), ("during_convert", 1), ("completed", 3)]:
        state.clear()
        state.update(scenario=scenario, scans=0, events=[])
        _run_phase_two(books)
        assert state["events"] == ["convert", "replace", "metadata"] * expected, (scenario, state)
        assert "Not Processed: " + str(3 - expected) in state["report"]
        assert "Failed: 0" in state["report"]
        assert state["finished"]
        if expected < 3:
            assert "Run Status: Stopped by user" in state["report"]
        else:
            assert "Run Status: Completed" in state["report"]
    state.clear()
    state.update(scenario="during_scan", scans=0, events=[])
    _run_phase_one(books)
    assert state["scans"] == 1
    assert "Not Processed: 2" in state["report"] and "Book 2" in state["report"]
    print("PASS: stop before scan, during scan, before conversion, during conversion, normal completion and analyze-only stop; active conversion still finalizes and updates metadata")
    # Trial mode uses the same two-pass helper boundary, never replacement.
    candidates = [{'eligible': True, 'archive_type': 'cbz'} for unused in range(7)]
    assert _trial_sample_indices(candidates, {}) == set([0, 3, 6])
    candidates[0] = {'eligible': False}
    assert _trial_sample_indices(candidates, {}) == set([1, 3, 6])
    assert _trial_sample_indices(candidates[:2], {}) == set([1])
    def trial_helper(python, tool, result, options, book):
        quality = options['quality_mode']
        assert options['size_policy'] == 'Keep All Results'
        assert options['resize_mode'] == 'No Resize'
        state['events'].append(quality)
        state['progress'].stop_requested = True
        output = Path.Combine(test_root, quality + '.cbz')
        _write_text_file(output, 'disposable trial')
        return {'STATUS': 'OK', 'OUTPUT_PATH': output, 'SOURCE_SIZE': '100', 'OUTPUT_SIZE': '50' if quality == 'Q75' else '60', 'SAVINGS_PERCENT': '50' if quality == 'Q75' else '40'}
    _run_conversion_helper = trial_helper
    state.clear()
    state.update(scenario='completed', scans=0, events=[])
    progress = TestProgress()
    progress._status_label = Label()
    measured = _run_quality_trial('unused', 'unused', candidates[1], {'run_mode': 'Test savings & quality', 'work_dir': test_root}, books[0], progress)
    assert state['events'] == TRIAL_QUALITY_LEVELS
    assert measured['STATUS'] == 'OK' and progress.stop_requested
    assert not File.Exists(Path.Combine(test_root, 'Q75.cbz'))
    for quality in TRIAL_QUALITY_LEVELS:
        assert not File.Exists(Path.Combine(test_root, quality + '.cbz'))
    comparison = _build_quality_trial_report([{'caption': 'Book'}], [measured], 'tool', {})
    assert 'Q75 Reduction: 50.00%' in comparison and 'Q80 Reduction: 40.00%' in comparison
    measured['Q75']['STATUS'] = 'ERROR'
    measured['STATUS'] = 'ERROR'
    failed_comparison = _build_quality_trial_report([{'caption': 'Book'}], [measured], 'tool', {})
    assert 'Q75 Reduction: Not measured' in failed_comparison
    assert 'Q80 Reduction: Not measured' in failed_comparison
    assert 'Failed: 1' in failed_comparison
    # Native rendering of the new comparison report and trial controls.
    TrialOptions = original_globals['OptionsForm']
    trial_options = TrialOptions()
    trial_options._mode_combo.SelectedItem = 'Test savings & quality'
    assert not trial_options._quality_combo.Enabled
    assert not trial_options._resize_combo.Enabled
    assert not trial_options._size_policy_combo.Enabled
    trial_options.Opacity = 0
    trial_options.ShowInTaskbar = False
    trial_options.Show()
    Application.DoEvents()
    assert trial_options._preview_checkbox.Visible
    bitmap = Bitmap(trial_options.Width, trial_options.Height)
    trial_options.DrawToBitmap(bitmap, Rectangle(0, 0, trial_options.Width, trial_options.Height))
    bitmap.Save(Path.Combine(render_dir, 'quality-trial-options.png'), ImageFormat.Png)
    bitmap.Dispose()
    trial_options.Close()
    trial_options.Dispose()
    TrialReport = original_globals['ReportForm']
    comparison_form = TrialReport(comparison, 'test-report')
    comparison_form.Opacity = 0
    comparison_form.ShowInTaskbar = False
    comparison_form.Show()
    Application.DoEvents()
    bitmap = Bitmap(comparison_form.Width, comparison_form.Height)
    comparison_form.DrawToBitmap(bitmap, Rectangle(0, 0, comparison_form.Width, comparison_form.Height))
    bitmap.Save(Path.Combine(render_dir, 'quality-trial.png'), ImageFormat.Png)
    bitmap.Dispose()
    comparison_form.Close()
    print('PASS: spaced sampling, five quality overrides, all passes finish after stop, cleanup, paired-only aggregates and comparison UI')
    preview_parent = Path.Combine(REPORT_DIR, 'QualityTests')
    Directory.CreateDirectory(preview_parent)
    cleanup_root = Path.Combine(preview_parent, System.Guid.NewGuid().ToString('N'))
    untouched = Path.Combine(preview_parent, System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(cleanup_root)
    Directory.CreateDirectory(untouched)
    _write_text_file(Path.Combine(cleanup_root, 'sample.png'), 'generated placeholder')
    _write_text_file(Path.Combine(untouched, 'keep.txt'), 'other run')
    try:
        _delete_trial_previews(preview_parent)
        assert False, 'Deleted parent preview folder'
    except Exception:
        assert Directory.Exists(preview_parent)
    try:
        _delete_trial_previews(test_root)
        assert False, 'Deleted a folder outside preview root'
    except Exception:
        assert Directory.Exists(test_root)
    cleanup_text = comparison.replace('Run Mode: Test savings & quality', 'Run Mode: Test savings & quality\r\nPreview Folder: ' + cleanup_root)
    cleanup_report = Path.Combine(test_root, 'cleanup-report.txt')
    _write_text_file(cleanup_report, cleanup_text)
    _save_settings({'delete_test_previews_on_close': True})
    cleanup_form = TrialReport(cleanup_text, cleanup_report)
    cleanup_form.Opacity = 0
    cleanup_form.ShowInTaskbar = False
    cleanup_form.Show()
    Application.DoEvents()
    assert cleanup_form._delete_previews_checkbox.Checked
    bitmap = Bitmap(cleanup_form.Width, cleanup_form.Height)
    cleanup_form.DrawToBitmap(bitmap, Rectangle(0, 0, cleanup_form.Width, cleanup_form.Height))
    bitmap.Save(Path.Combine(render_dir, 'preview-cleanup.png'), ImageFormat.Png)
    bitmap.Dispose()
    cleanup_form.Close()
    cleanup_form.Dispose()
    assert not Directory.Exists(cleanup_root)
    assert Directory.Exists(untouched)
    assert File.Exists(cleanup_report)
    assert 'Preview cleanup: Deleted' in File.ReadAllText(cleanup_report)
    kept_text = comparison.replace('Run Mode: Test savings & quality', 'Run Mode: Test savings & quality\r\nPreview Folder: ' + untouched)
    kept_form = TrialReport(kept_text, cleanup_report)
    kept_form.Opacity = 0
    kept_form.ShowInTaskbar = False
    kept_form.Show()
    kept_form._delete_previews_checkbox.Checked = False
    kept_form.Close()
    kept_form.Dispose()
    assert Directory.Exists(untouched)
    assert _load_settings()[0]['delete_test_previews_on_close'] == 'False'
    print('PASS: delete-on-close removes only the selected generated preview run, preserves report/other runs, rejects broad/outside targets and remembers keep preference')
    fixture_root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Trial Helper Checks')
    fixtures = [folder for folder in Directory.GetDirectories(fixture_root) if File.Exists(Path.Combine(folder, 'results.json'))]
    assert fixtures, 'Run test_trial_helper.py first to create a generated-comic fixture'
    source = Path.Combine(fixtures[0], 'original.cbz')
    def temp_metadata(book, root_name):
        path = Path.Combine(test_root, System.Guid.NewGuid().ToString('N') + '.xml')
        _write_text_file(path, '<' + root_name + '/>')
        return path
    _write_comicinfo_temp_file = lambda book: temp_metadata(book, 'ComicInfo')
    _write_comicbook_temp_file = lambda book: temp_metadata(book, 'ComicBook')
    _run_conversion_helper = original_globals['_run_conversion_helper']
    real_progress = original_globals['ProgressForm']()
    real_progress.Opacity = 0
    real_progress.ShowInTaskbar = False
    real_progress.Show()
    real_options = {'run_mode': 'Test savings & quality', 'encoder_backend': 'ImageMagick (Recommended)', 'cbr_mode': CBR_MODE_VALUES[0], 'work_dir': test_root, 'keep_test_previews': True, 'trial_preview_root': Path.Combine(test_root, 'real-previews')}
    Directory.CreateDirectory(real_options['trial_preview_root'])
    source_before = File.ReadAllBytes(source)
    real_measurement = _run_quality_trial(original_globals['_find_python_tool'](), original_globals['_find_archive_tool'](), {'file_path': source, 'archive_type': 'cbz'}, real_options, books[0], real_progress)
    real_progress.finish()
    assert real_measurement['STATUS'] == 'OK', real_measurement
    assert list(File.ReadAllBytes(source)) == list(source_before)
    for quality in TRIAL_QUALITY_LEVELS:
        assert File.Exists(real_measurement[quality]['PREVIEW_PATH'])
        assert not File.Exists(real_measurement[quality]['OUTPUT_PATH'])
    viewer = QualityPreviewForm(real_options['trial_preview_root'])
    viewer.Opacity = 0
    viewer.ShowInTaskbar = False
    viewer.WindowState = FormWindowState.Normal
    viewer.ClientSize = Size(1400, 900)
    viewer.Show()
    Application.DoEvents()
    assert len(viewer._entries) == 3
    assert viewer._quality.Items.Count == 5
    assert len(viewer._images) == 2
    for quality in TRIAL_QUALITY_LEVELS:
        viewer._quality.SelectedItem = quality
        assert quality in viewer._captions[1].Text
        assert len(viewer._images) == 2
    viewer._zoom.SelectedItem = "100% - actual pixels"
    assert viewer._pictures[0].Width == viewer._images[0].Width
    viewer._zoom.SelectedItem = "200% - enlarged pixels"
    assert viewer._pictures[0].Width == viewer._images[0].Width * 2
    viewer._page.SelectedIndex = 1
    assert len(viewer._images) == 2
    viewer._zoom.SelectedIndex = 0
    bitmap = Bitmap(viewer.Width, viewer.Height)
    viewer.DrawToBitmap(bitmap, Rectangle(0, 0, viewer.Width, viewer.Height))
    bitmap.Save(Path.Combine(render_dir, 'native-quality-preview.png'), ImageFormat.Png)
    bitmap.Dispose()
    viewer._toggle_fullscreen(None, None)
    assert viewer._fullscreen
    viewer._toggle_fullscreen(None, None)
    assert not viewer._fullscreen
    viewer.Close()
    assert not viewer._images
    viewer.Dispose()
    print('PASS: native viewer page and five-quality selection, actual-pixel zoom, enlarged zoom, full-screen toggle and image disposal')
    real_page_folder = Path.Combine(render_dir, 'Real Page Preview')
    if Directory.Exists(real_page_folder):
        large_viewer = QualityPreviewForm(real_page_folder)
        large_viewer.Opacity = 0
        large_viewer.ShowInTaskbar = False
        large_viewer.WindowState = FormWindowState.Normal
        large_viewer.ClientSize = Size(1400, 900)
        large_viewer.Show()
        Application.DoEvents()
        large_viewer._zoom.SelectedItem = "100% - actual pixels"
        large_viewer._panels[0].AutoScrollPosition = Point(100, 250)
        large_viewer._left_scroll(None, None)
        assert large_viewer._panels[0].AutoScrollPosition == large_viewer._panels[1].AutoScrollPosition
        # Detached bitmaps must not keep the preview files locked.
        entry = large_viewer._entries[0]['variants']['Q80']
        handle = File.Open(entry['converted'], System.IO.FileMode.Open, System.IO.FileAccess.Read, getattr(System.IO.FileShare, "None"))
        handle.Close()
        large_viewer._wheel_input(large_viewer._panels[0], -120, getattr(Keys, 'None'))
        assert large_viewer._panels[0].AutoScrollPosition == large_viewer._panels[1].AutoScrollPosition
        assert abs(large_viewer._panels[0].AutoScrollPosition.Y) > 250
        large_viewer._wheel_input(large_viewer._panels[1], -120, Keys.Shift)
        assert large_viewer._panels[0].AutoScrollPosition == large_viewer._panels[1].AutoScrollPosition
        assert abs(large_viewer._panels[1].AutoScrollPosition.X) > 100
        large_viewer._wheel_input(large_viewer._panels[0], 120, Keys.Control)
        assert large_viewer._scale == 1.25
        assert large_viewer._pictures[0].Size == large_viewer._pictures[1].Size
        large_viewer._wheel_input(large_viewer._panels[1], -120, Keys.Control)
        assert large_viewer._scale == 1.0
        from System.Windows.Forms import HandledMouseEventArgs, MouseButtons
        wheel_event = HandledMouseEventArgs(getattr(MouseButtons, 'None'), 0, 0, 0, -120)
        large_viewer._panels[0].OnMouseWheel(wheel_event)
        assert wheel_event.Handled
        assert large_viewer._panels[0].AutoScrollPosition == large_viewer._panels[1].AutoScrollPosition
        large_viewer._zoom.SelectedIndex = 0
        Application.DoEvents()
        large_viewer._images[1].Save(Path.Combine(render_dir, 'native-decoded-preview.png'), ImageFormat.Png)
        _write_text_file(Path.Combine(render_dir, 'native-decoded-source.txt'), large_viewer._entries[0]['variants']['Q80']['converted'])
        bitmap = Bitmap(large_viewer.Width, large_viewer.Height)
        large_viewer.DrawToBitmap(bitmap, Rectangle(0, 0, large_viewer.Width, large_viewer.Height))
        bitmap.Save(Path.Combine(render_dir, 'native-real-page-preview.png'), ImageFormat.Png)
        bitmap.Dispose()
        large_viewer.Close()
        large_viewer.Dispose()
        print('PASS: full-resolution comic-page rendering, synchronized scroll positions and no preview file locks')
    print('PASS: real IronPython-to-helper five-quality conversion, metadata injection, retained previews, trial-archive cleanup and unchanged generated source')
    color_root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Color Checks')
    if Directory.Exists(color_root):
        color_files = Directory.GetFiles(color_root, 'ImageMagick.png', SearchOption.AllDirectories)
        if len(color_files):
            unmanaged = DrawingImage.FromFile(color_files[0], False)
            managed = DrawingImage.FromFile(color_files[0], True)
            raw_bitmap = Bitmap(unmanaged)
            managed_bitmap = Bitmap(managed)
            try:
                differences = 0
                for xstep in range(1, 8):
                    for ystep in range(1, 8):
                        x = int(raw_bitmap.Width * xstep / 8)
                        y = int(raw_bitmap.Height * ystep / 8)
                        differences += raw_bitmap.GetPixel(x, y).ToArgb() != managed_bitmap.GetPixel(x, y).ToArgb()
                assert differences > 0, 'Adobe RGB test did not exercise embedded-profile color management'
                print('PASS: native color-managed loading honors embedded Adobe RGB profile (differs from unmanaged loading)')
            finally:
                raw_bitmap.Dispose()
                managed_bitmap.Dispose()
                unmanaged.Dispose()
                managed.Dispose()
finally:
    globals().update(original_globals)
