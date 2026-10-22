param([switch]$HistoryHostSmoke, [switch]$TableHeaderSmoke, [switch]$ModalHistorySmoke, [int]$HistoryStackBytes = 0)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
$pluginRoot = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path (Split-Path (Split-Path $pluginRoot -Parent) -Parent) 'ComicRackCE_nightly'
foreach ($dll in @('Microsoft.Scripting.dll', 'Microsoft.Dynamic.dll', 'IronPython.dll')) {
    [System.Reflection.Assembly]::Load([System.IO.File]::ReadAllBytes((Join-Path $runtime $dll))) | Out-Null
}
[System.AppDomain]::CurrentDomain.add_AssemblyResolve({ param($sender, $eventArgs)
    $assemblyPath = Join-Path $runtime (($eventArgs.Name.Split(',')[0]) + '.dll')
    if ([System.IO.File]::Exists($assemblyPath)) { return [System.Reflection.Assembly]::Load([System.IO.File]::ReadAllBytes($assemblyPath)) }
    return $null
})
$engine = [IronPython.Hosting.Python]::CreateEngine()
$scope = $engine.CreateScope()
$scope.SetVariable('plugin_path', [string](Join-Path $pluginRoot 'WebPOptimizer.py'))
$scope.SetVariable('plugin_source', [System.IO.File]::ReadAllText((Join-Path $pluginRoot 'WebPOptimizer.py')))
$engine.Execute(@'
try:
    __file__ = plugin_path
    exec compile(plugin_source, str(__file__), 'exec')
except:
    import sys
    tb = sys.exc_info()[2]
    while tb is not None:
        print(tb.tb_frame.f_code.co_filename, tb.tb_lineno)
        tb = tb.tb_next
    raise
'@, $scope) | Out-Null
if ($HistoryHostSmoke) {
    $engine.Execute(@'
fixture = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'History Process Checks', System.Guid.NewGuid().ToString('N'))
Directory.CreateDirectory(fixture)
text = 'Generated quality test\r\nGenerated: 2026-10-22 00:00:00\r\nRun Mode: Test savings & quality\r\nBooks Scanned: 1\r\nRun Status: Completed\r\n'
path = Path.Combine(fixture, 'webp_conversion_generated.txt')
choices = {'encoder_backend': ENCODER_BACKEND_VALUES[0], 'cbr_mode': CBR_MODE_VALUES[0], 'page_workers': '2', 'work_dir': u'D:\\Generated & Tests\\caf\u00e9'}
_write_text_file(path, text)
_save_run_record(path, text, choices)
original_form = RunHistoryForm
def forbidden_parent_browser(*args, **kwargs):
    raise Exception('History browser was constructed inside the calling process')
RunHistoryForm = forbidden_parent_browser
settings_before = File.ReadAllText(SETTINGS_PATH) if File.Exists(SETTINGS_PATH) else None
sessions = Path.Combine(SCRIPT_DIR, 'Reports', 'HistorySessions')
before = set(Directory.GetFiles(sessions)) if Directory.Exists(sessions) else set()
try:
    assert _open_history_external(False, True, self_test='close', test_reports=fixture) is None
    prepared = _open_history_external(True, True, self_test='retest', test_reports=fixture)
    assert prepared['options'] == choices, prepared
    try:
        _open_history_external(False, self_test='fail')
    except Exception, ex:
        assert 'separate history window' in _safe_unicode(ex)
    else:
        raise AssertionError('Forced child failure was accepted')
    # The same caller must still open another independent browser after that exit.
    assert _open_history_external(False, False, self_test='close', test_reports=fixture) is None
    assert set(Directory.GetFiles(sessions)) == before
    assert (File.ReadAllText(SETTINGS_PATH) if File.Exists(SETTINGS_PATH) else None) == settings_before
    assert File.ReadAllText(path) == text
    print('PASS: real process isolation, abrupt child exit contained, next launch succeeds, Unicode retest round trip, exact session cleanup, unchanged reports/settings and no parent browser')
finally:
    RunHistoryForm = original_form
'@, $scope) | Out-Null
    exit
}
if ($TableHeaderSmoke) {
    $engine.Execute(@'
from System.Drawing import Rectangle
from System.Drawing.Imaging import ImageFormat
form = ReportForm('Generated header test\r\nBooks Scanned: 0\r\n', 'generated-header.txt', historical=True)
form.Opacity, form.ShowInTaskbar = 0, False
table = form._tabs.TabPages[0].Controls[0]
table.Items.Add(ListViewItem('Generated row'))
_set_ui_theme(True, form)
form.Show()
Application.DoEvents()
pixels = Bitmap(table.Width, table.Height)
table.DrawToBitmap(pixels, Rectangle(0, 0, table.Width, table.Height))
color = pixels.GetPixel(table.ClientSize.Width - 10, 6)
print('HEADER PIXEL: ' + str(color))
for x in [4, table.Columns[0].Width + 4, table.ClientSize.Width - 10]:
    sample = pixels.GetPixel(x, 6)
    assert (sample.R, sample.G, sample.B) == (43, 47, 54), (x, sample)
pixels.Save(Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Review', 'dark-header-focused.png'), ImageFormat.Png)
pixels.Dispose()
form.Close()
form.Dispose()
assert (color.R, color.G, color.B) == (43, 47, 54)
print('PASS: native table header including empty tail uses the dark palette')
'@, $scope) | Out-Null
    exit
}
if ($ModalHistorySmoke) {
    $scope.SetVariable('history_stack_bytes', $HistoryStackBytes)
    $engine.Execute(@'
def run_modal_smoke():
    timer = Timer()
    timer.Interval = 100
    seen, owners, failures = [], [], []
    expected_quality = QUALITY_MODE_VALUES[1]
    settings_before = File.ReadAllText(SETTINGS_PATH) if File.Exists(SETTINGS_PATH) else None
    def drive(sender, event):
        try:
            forms = list(Application.OpenForms)
            histories = [form for form in forms if isinstance(form, RunHistoryForm)]
            options = [form for form in forms if isinstance(form, OptionsForm)]
            assert not (histories and options), 'Options remained open under history'
            if histories:
                form = histories[0]
                if not form._records:
                    return
                assert owners[-1].IsDisposed
                seen.append(form._list.Items.Count)
                print('MODAL: sequential history cycle ' + str(len(seen)))
                form.Close()
            elif options:
                form = options[0]
                form.Opacity, form.ShowInTaskbar = 0, False
                if len(seen) >= 10:
                    assert form._quality_combo.SelectedItem == expected_quality
                    assert not form._backup_checkbox.Checked
                    assert form._dark_checkbox.Checked
                    timer.Stop()
                    form._cancel(None, None)
                elif form not in owners:
                    if not owners:
                        form._quality_combo.SelectedItem = expected_quality
                        form._backup_checkbox.Checked = False
                        form._dark_checkbox.Checked = True
                    else:
                        assert form._quality_combo.SelectedItem == expected_quality
                        assert not form._backup_checkbox.Checked
                        assert form._dark_checkbox.Checked
                    owners.append(form)
                    button = next(control for control in form.Controls if isinstance(control, Button) and control.Text == 'Run history')
                    button.PerformClick()
                    form._show_history(None, None)
        except Exception, ex:
            failures.append(_safe_unicode(ex))
            timer.Stop()
            for form in list(Application.OpenForms):
                form.Close()
    real_external = _open_history_external
    def automatic_external(allow_retest=True, dark=None):
        assert not any(isinstance(form, OptionsForm) for form in Application.OpenForms)
        assert owners[-1].IsDisposed
        result = real_external(allow_retest, dark, self_test='close')
        seen.append(1)
        print('ISOLATED: history process cycle ' + str(len(seen)))
        return result
    globals()['_open_history_external'] = automatic_external
    timer.Tick += drive
    timer.Start()
    try:
        assert _choose_options_with_history([]) is None
    finally:
        timer.Dispose()
        globals()['_open_history_external'] = real_external
    assert not failures, failures
    assert len(seen) == 10, seen
    assert (File.ReadAllText(SETTINGS_PATH) if File.Exists(SETTINGS_PATH) else None) == settings_before
    print('MODAL: passive owner report dialog')
    owner = RunHistoryForm(allow_retest=False)
    owner.Opacity, owner.ShowInTaskbar = 0, False
    owner.Show()
    child = ReportForm('Generated history-owner test\r\nBooks Scanned: 0\r\n', 'generated-owner-test.txt', historical=True)
    child.Opacity, child.ShowInTaskbar = 0, False
    close_timer = Timer()
    close_timer.Interval = 100
    def close_child(sender, event):
        close_timer.Stop()
        child.Close()
    close_timer.Tick += close_child
    close_timer.Start()
    try:
        _show_owned_dialog(child, owner)
        assert not owner.IsDisposed
    finally:
        close_timer.Dispose()
        child.Dispose()
        owner.Close()
        owner.Dispose()
    print('MODAL: opening standalone library action')
    hook_timer = Timer()
    hook_timer.Interval = 200
    def close_standalone(sender, event):
        for form in list(Application.OpenForms):
            if isinstance(form, RunHistoryForm):
                hook_timer.Stop()
                form.Close()
    hook_timer.Tick += close_standalone
    hook_timer.Start()
    globals()['_open_history_external'] = lambda allow_retest=False: real_external(allow_retest, self_test='close')
    try:
        webp_optimizer_history([])
    finally:
        globals()['_open_history_external'] = real_external
        hook_timer.Dispose()
if history_stack_bytes:
    from System.Threading import Thread, ThreadStart, ApartmentState
    worker = Thread(ThreadStart(run_modal_smoke), history_stack_bytes)
    worker.SetApartmentState(ApartmentState.STA)
    worker.Start()
    worker.Join()
else:
    run_modal_smoke()
print('PASS: ten independent history processes, draft preservation, no in-process browser, standalone history and unchanged settings')
'@, $scope) | Out-Null
    exit
}
$renderDir = Join-Path $PSScriptRoot 'Test Environment/UI Review'
[System.IO.Directory]::CreateDirectory($renderDir) | Out-Null
$scope.SetVariable('render_dir', [string]$renderDir)
$engine.Execute(@'
from System.Drawing import Bitmap, Rectangle
from System.Drawing.Imaging import ImageFormat
Application.EnableVisualStyles()
SETTINGS_PATH = Path.Combine(render_dir, 'isolated-settings-' + System.Guid.NewGuid().ToString('N') + '.xml')
options = OptionsForm()
assert options._quality_combo.SelectedItem == 'Q80 - Balanced (Recommended)'
assert options._quality_combo.Enabled == False
options._mode_combo.SelectedItem = 'Replace Originals'
assert options._quality_combo.Enabled and options._backup_checkbox.Enabled
assert options._quality_combo.Items.Count == 7
assert 'Lossless' not in list(options._quality_combo.Items)
options._quality_combo.SelectedItem = 'Q90'
assert 'Measured sample' in options._quality_note.Text
options._quality_combo.SelectedItem = 'Q80 - Balanced (Recommended)'
options._encoder_combo.SelectedItem = 'Pillow'
assert 'unavailable' in options._quality_note.Text
options._encoder_combo.SelectedIndex = 0
options.Opacity = 0
options.ShowInTaskbar = False
options.Show()
Application.DoEvents()
for name, index in [('options', 0), ('storage', 1), ('performance', 2), ('tools', 3)]:
    options._tabs.SelectedIndex = index
    options.CreateControl()
    options.PerformLayout()
    Application.DoEvents()
    bitmap = Bitmap(options.Width, options.Height)
    options.DrawToBitmap(bitmap, Rectangle(0, 0, options.Width, options.Height))
    bitmap.Save(Path.Combine(render_dir, name + '.png'), ImageFormat.Png)
    bitmap.Dispose()
options.Dispose()
synthetic_results = [{'caption': 'Small', 'file_path': 'small.cbz'}, {'caption': 'Large', 'file_path': 'large.cbz'}, {'caption': 'Skipped', 'file_path': 'skip.cbz'}]
synthetic_conversions = [{'STATUS': 'OK', 'SOURCE_SIZE': '100', 'OUTPUT_SIZE': '50'}, {'STATUS': 'OK', 'SOURCE_SIZE': '900', 'OUTPUT_SIZE': '810'}, {'STATUS': 'SKIPPED'}]
weighted = _build_conversion_report(synthetic_results, synthetic_conversions, 'tool', {'run_mode': 'Replace Originals'})
assert 'Overall Reduction: 14.00%' in weighted
assert 'Converted Books: 2' in weighted
grown = _build_conversion_report([synthetic_results[0]], [{'STATUS': 'OK', 'SOURCE_SIZE': '100', 'OUTPUT_SIZE': '120'}], 'tool', {})
assert 'Overall Reduction: -20.00%' in grown and 'Total Saved: -20 B' in grown
copy_root = Path.Combine(render_dir, 'report-copy-' + System.Guid.NewGuid().ToString('N'))
Directory.CreateDirectory(copy_root)
central = Path.Combine(copy_root, 'central.txt')
target_folder = Path.Combine(copy_root, 'sources')
Directory.CreateDirectory(target_folder)
_write_text_file(central, weighted)
copied = _copy_reports_to_sources(weighted, central, [{'file_path': Path.Combine(target_folder, 'book.cbz')}], {'reports_beside_sources': True})
assert File.ReadAllText(Path.Combine(target_folder, 'central.txt')) == weighted
assert copied == weighted
collision = _copy_reports_to_sources(weighted, central, [{'file_path': Path.Combine(target_folder, 'book.cbz')}], {'reports_beside_sources': True})
assert 'Report storage warnings' in collision
print('PASS: defaults, conditional controls, estimates, weighted totals, growth, source report copy and collision handling')
report_text = File.ReadAllText(Path.Combine(REPORT_DIR, 'webp_conversion_20261021_084135.txt'))
report_text = report_text.replace('Total Saved: 50.44 MB', 'Total Saved: 50.44 MB\r\nOverall Reduction: 53.31%')
report = ReportForm(report_text, 'sample-report.txt')
report.Opacity = 0
report.ShowInTaskbar = False
report.Show()
Application.DoEvents()
report.CreateControl()
report.PerformLayout()
bitmap = Bitmap(report.Width, report.Height)
report.DrawToBitmap(bitmap, Rectangle(0, 0, report.Width, report.Height))
bitmap.Save(Path.Combine(render_dir, 'report.png'), ImageFormat.Png)
bitmap.Dispose()
report.Dispose()
try:
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_runtime_features.py')), 'test_runtime_features.py', 'exec')
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_preview_difference.py')), 'test_preview_difference.py', 'exec')
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_history.py')), 'test_history.py', 'exec')
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_batch.py')), 'test_batch.py', 'exec')
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_release_features.py')), 'test_release_features.py', 'exec')
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_performance_ui.py')), 'test_performance_ui.py', 'exec')
except:
    import sys
    tb = sys.exc_info()[2]
    while tb is not None:
        print(tb.tb_frame.f_code.co_filename, tb.tb_lineno)
        tb = tb.tb_next
    raise
print('PASS: actual IronPython form construction and offscreen renders')
'@, $scope) | Out-Null
Write-Output $renderDir
