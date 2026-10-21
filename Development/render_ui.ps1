param([switch]$ModalHistorySmoke, [int]$HistoryStackBytes = 0)
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
if ($ModalHistorySmoke) {
    $scope.SetVariable('history_stack_bytes', $HistoryStackBytes)
    $engine.Execute(@'
def run_modal_smoke():
    owner = OptionsForm()
    owner.Opacity = 0
    owner.ShowInTaskbar = False
    owner.Show()
    Application.DoEvents()
    modal_timer = Timer()
    modal_timer.Interval = 200
    seen = []
    def close_history(sender, event):
        for form in list(Application.OpenForms):
            if isinstance(form, RunHistoryForm):
                seen.append(form._list.Items.Count)
                print('MODAL: populated history with ' + str(form._list.Items.Count) + ' real reports')
                form.Close()
    modal_timer.Tick += close_history
    modal_timer.Start()
    click_timer = Timer()
    click_timer.Interval = 100
    clicked = []
    def drive_options(sender, event):
        if not clicked:
            clicked.append(True)
            button = next(control for control in owner.Controls if isinstance(control, Button) and control.Text == 'Run history')
            print('MODAL: actual button click inside modal options')
            button.PerformClick()
            button.PerformClick()  # The queued path must reject re-entry.
        elif not owner._history_opening:
            click_timer.Stop()
            owner.Close()
    click_timer.Tick += drive_options
    click_timer.Start()
    owner.Hide()
    owner.ShowDialog()
    modal_timer.Dispose()
    click_timer.Dispose()
    assert len(seen) == 1, seen
    assert not owner._history_opening
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
    webp_optimizer_history([])
    hook_timer.Dispose()
if history_stack_bytes:
    from System.Threading import Thread, ThreadStart, ApartmentState
    worker = Thread(ThreadStart(run_modal_smoke), history_stack_bytes)
    worker.SetApartmentState(ApartmentState.STA)
    worker.Start()
    worker.Join()
else:
    run_modal_smoke()
print('PASS: owned modal history with real read-only reports')
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
for name, index in [('options', 0), ('storage', 1), ('performance', 2)]:
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
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_history.py')), 'test_history.py', 'exec')
    exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, 'Development', 'test_batch.py')), 'test_batch.py', 'exec')
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
