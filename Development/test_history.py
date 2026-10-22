"""Native-runtime history tests, with an isolated report store."""
saved_history_globals = dict((name, globals()[name]) for name in ['REPORT_DIR', 'SETTINGS_PATH', 'OptionsForm', 'RunHistoryForm', '_open_history_external', '_find_archive_tool', '_find_python_tool'])
try:
    REPORT_DIR = Path.Combine(render_dir, 'history-' + System.Guid.NewGuid().ToString('N'))
    SETTINGS_PATH = Path.Combine(REPORT_DIR, 'settings.xml')
    Directory.CreateDirectory(REPORT_DIR)
    preview = Path.Combine(REPORT_DIR, 'QualityTests', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(preview)
    pixel = Bitmap(40, 60)
    pixel.Save(Path.Combine(preview, 'original.jpg'), ImageFormat.Jpeg)
    pixel.Save(Path.Combine(preview, 'converted.png'), ImageFormat.Png)
    pixel.Dispose()
    _write_text_file(Path.Combine(preview, 'preview.xml'), '<Preview quality="Q80" book="Fixture" source="fixture.cbz"><Page id="0" title="Page 1" original="original.jpg" converted="converted.png" originalBytes="100" webpBytes="50"/></Preview>')
    text = 'WebP Optimizer Quality Trial\r\nGenerated: 2026-10-21 12:00:00\r\nRun Mode: Test savings &amp; quality\r\nBooks Scanned: 3\r\nBooks Processed: 3\r\nRun Status: Completed\r\nFailed: 0\r\nQ80 Reduction: 50.00%\r\nPreview Folder: ' + preview + '\r\n\r\nPer-Book Conversion Results\r\nFixture\r\n  Conversion Status: OK\r\n'
    text = text.replace('&amp;', '&')
    report_path = Path.Combine(REPORT_DIR, 'webp_conversion_20261021_120000.txt')
    _write_text_file(report_path, text)
    options = {'encoder_backend': 'ImageMagick (Recommended)', 'work_dir': u'D:\\Comics & Tests\\caf\u00e9', 'cbr_mode': CBR_MODE_VALUES[0]}
    _save_run_record(report_path, text, options, [{'file_path': 'fixture.cbz', 'caption': 'Fixture'}])
    records = _load_run_history()
    assert len(records) == 1
    assert records[0]['previewState'] == 'Available'
    assert records[0]['options']['work_dir'] == options['work_dir']
    assert records[0]['sources'] == ['fixture.cbz']
    _save_settings({'delete_test_previews_on_close': True})
    historical = ReportForm(text + "\r\nPreview cleanup: Previously retained.\r\n", report_path, historical=True)
    historical.Opacity = 0
    historical.ShowInTaskbar = False
    historical.Show()
    assert not historical._delete_previews_checkbox.Checked
    assert historical._tabs.TabPages[0].Controls[0].Items.Count == 1
    historical.Close()
    historical.Dispose()
    assert Directory.Exists(preview)
    assert _load_settings()[0]['delete_test_previews_on_close'] == 'True'
    legacy = Path.Combine(REPORT_DIR, 'webp_analysis_20261020_120000.txt')
    _write_text_file(legacy, 'Legacy analysis\r\nGenerated: 2026-10-20 12:00:00\r\nBooks Scanned: 2\r\nErrors: 0\r\n\r\n')
    assert len(_load_run_history()) == 2
    _write_text_file(Path.ChangeExtension(legacy, '.run.xml'), 'invalid XML')
    assert len(_load_run_history()) == 2
    assert [r for r in _load_run_history() if r['path'] == legacy][0]['mode'] == 'Analyze Only'
    history = RunHistoryForm()
    history.Opacity = 0
    history.ShowInTaskbar = False
    history.Show()
    Application.DoEvents()
    assert history._list.Items.Count == 2
    history._list.Items[0].Selected = True
    history._selected_changed(None, None)
    assert history._buttons['Open previews'].Enabled
    assert history._buttons['Prepare new test'].Enabled
    bitmap = Bitmap(history.Width, history.Height)
    history.DrawToBitmap(bitmap, Rectangle(0, 0, history.Width, history.Height))
    bitmap.Save(Path.Combine(render_dir, 'run-history.png'), ImageFormat.Png)
    bitmap.Dispose()
    history._prepare_test(None, None)
    assert history.retest['options']['work_dir'] == options['work_dir']
    history.Dispose()
    _delete_trial_previews(preview)
    _save_run_record(report_path, text, preview_state='Removed')
    deleted = [r for r in _load_run_history() if r['path'] == report_path][0]
    assert deleted['previewState'] == 'Removed'
    assert deleted['sources'] == ['fixture.cbz']
    assert deleted['options']['work_dir'] == options['work_dir']
    missing_text = text.replace(preview, Path.Combine(REPORT_DIR, 'missing-previews'))
    missing_report = Path.Combine(REPORT_DIR, 'webp_conversion_20261022_120000.txt')
    _write_text_file(missing_report, missing_text)
    _save_run_record(missing_report, missing_text)
    assert [r for r in _load_run_history() if r['path'] == missing_report][0]['previewState'] == 'Unavailable'
    class HistoryOnlyOptions(object):
        def ShowDialog(self):
            return DialogResult.Cancel
    OptionsForm = HistoryOnlyOptions
    def forbidden_dependency_probe():
        raise Exception('History-only entry checked conversion dependencies')
    _find_archive_tool = forbidden_dependency_probe
    _find_python_tool = forbidden_dependency_probe
    _run_phase_two([])
    # Controller protocol: retry returns a draft, retest changes only the
    # intended choices, and no new run or settings write happens automatically.
    transitions = []
    class NavigationOptions(object):
        def __init__(self):
            self._backup_checkbox = CheckBox()
            self._backup_checkbox.Checked = True
            self.options = {"run_mode": "Analyze Only"}
        def ShowDialog(self):
            transitions.append('options')
            return DialogResult.Retry if transitions.count('options') == 1 else DialogResult.Cancel
        def _collect_options(self):
            return {"quality_mode": "Q75", "run_mode": "Replace Originals", "work_dir": "draft", "dark_mode": True}
        def _restore_draft(self, values):
            assert transitions == ['options', 'options-disposed', 'history', 'history-disposed']
            assert values['run_mode'] == 'Test savings & quality'
            assert values['quality_mode'] == 'Q75' and values['work_dir'] == 'recorded'
            assert values['keep_test_previews'] and values['create_backup'] and values['dark_mode']
        def Dispose(self):
            transitions.append('options-disposed')
    class NavigationHistory(object):
        retest = {"options": {"work_dir": "recorded", "encoder_backend": ENCODER_BACKEND_VALUES[0]}}
        def ShowDialog(self):
            transitions.append('history')
        def Dispose(self):
            transitions.append('history-disposed')
    OptionsForm = NavigationOptions
    def fake_external(allow_retest=True, dark=None):
        transitions.extend(['history', 'history-disposed'])
        return NavigationHistory.retest
    _open_history_external = fake_external
    before = File.ReadAllText(SETTINGS_PATH)
    assert _choose_options_with_history([]) is None
    assert File.ReadAllText(SETTINGS_PATH) == before
    print('PASS: sequential navigation disposes options first, restores retest/draft choices and leaves settings unchanged')
    print('PASS: structured history, legacy/corrupt-record fallback, preview states, safe historical close, settings/source retention, retest preparation and no-selection history-only entry')
finally:
    globals().update(saved_history_globals)
