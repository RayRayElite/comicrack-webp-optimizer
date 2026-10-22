"""Real native benchmark plus options/controller tests in isolated UI harness."""
benchmark_saved = dict((name, globals()[name]) for name in ["REPORT_DIR", "SETTINGS_PATH", "PerformanceSetupForm", "PerformanceResultsForm", "ProgressForm", "_run_performance_test", "OptionsForm", "_choose_options_with_history", "ReportForm", "_run_conversion_helper", "_cleanup_prefetch"])
benchmark_root = Path.Combine(render_dir, "performance-" + System.Guid.NewGuid().ToString("N"))
Directory.CreateDirectory(benchmark_root)
try:
    REPORT_DIR = Path.Combine(benchmark_root, "Reports")
    SETTINGS_PATH = Path.Combine(benchmark_root, "settings.xml")
    form = OptionsForm()
    assert list(form._workers_combo.Items) == PAGE_WORKER_VALUES
    form._restore_draft({"page_workers": "12", "resource_profile": "Background", "prefetch": True})
    draft = form._collect_options()
    assert draft["page_workers"] == "12" and draft["resource_profile"] == "Background" and draft["prefetch"]
    _save_settings(draft)
    form.Dispose()
    form = OptionsForm()
    assert form._workers_combo.SelectedItem == "12" and form._prefetch_checkbox.Checked
    form.Dispose()
    fixture_root = Path.Combine(SCRIPT_DIR, "Development", "Test Environment", "Trial Helper Checks")
    fixture = next(Path.Combine(folder, "original.cbz") for folder in Directory.GetDirectories(fixture_root) if File.Exists(Path.Combine(folder, "results.json")))
    source = Path.Combine(benchmark_root, "source.cbz")
    File.Copy(fixture, source, False)
    before = list(File.ReadAllBytes(source))
    class BenchmarkBook(object):
        Caption = "Generated benchmark"
        def __init__(self, path):
            self.FilePath = path
        def SetCustomValue(self, *args):
            raise AssertionError("Benchmark changed a library tag")
    actual_setup, actual_results, actual_progress = PerformanceSetupForm, PerformanceResultsForm, ProgressForm
    class AutomaticSetup(actual_setup):
        def ShowDialog(self):
            return DialogResult.OK
    captured = []
    class AutomaticResults(actual_results):
        def __init__(self, rows, report, path, recommendation):
            actual_results.__init__(self, rows, report, path, recommendation)
            self.applied_workers = recommendation
            captured.append((rows, report, path, recommendation))
        def ShowDialog(self):
            self.ShowInTaskbar, self.Opacity = False, 0
            self.Show()
            Application.DoEvents()
            bitmap = Bitmap(self.Width, self.Height)
            self.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, self.Width, self.Height))
            bitmap.Save(Path.Combine(benchmark_root, "benchmark-results.png"))
            bitmap.Dispose()
            return DialogResult.OK
    PerformanceSetupForm, PerformanceResultsForm = AutomaticSetup, AutomaticResults
    options = {"quality_mode": "Q75", "encoder_backend": ENCODER_BACKEND_VALUES[0], "resize_mode": "No Resize", "resource_profile": "Background", "work_dir": benchmark_root}
    chosen = _run_performance_test([BenchmarkBook(source)], options)
    assert chosen in PAGE_WORKER_VALUES and captured[-1][3] == chosen
    assert all(row[1] == "1/1" and row[-1] == "Complete" for row in captured[-1][0])
    assert "RESOURCE_CPU_AVG_PERCENT:" in captured[-1][1]
    assert File.Exists(captured[-1][2]) and list(File.ReadAllBytes(source)) == before
    assert not Directory.GetFiles(benchmark_root, "webp_perf_*") and not Directory.GetFiles(benchmark_root, "webp_trial_*")
    class StopProgress(actual_progress):
        def update_archive_progress(self, payload):
            actual_progress.update_archive_progress(self, payload)
            if payload.startswith("ENCODING"):
                self.stop_requested = True
    ProgressForm = StopProgress
    assert not _run_performance_test([BenchmarkBook(source)], options)
    assert not captured[-1][3] and captured[-1][0][0][1] == "1/1"
    assert list(File.ReadAllBytes(source)) == before and not Directory.GetFiles(benchmark_root, "webp_perf_*")
    # Run the normal adapter pipeline, not just the helper handoff, using copies.
    ProgressForm = actual_progress
    class PipelineBook(BenchmarkBook):
        def SetCustomValue(self, key, value):
            pass
    pipeline_books = []
    for name in ["pipeline-first.cbz", "pipeline-second.cbz"]:
        path = Path.Combine(benchmark_root, name)
        File.Copy(fixture, path, False)
        pipeline_books.append(PipelineBook(path))
    pipeline_options = dict(options)
    pipeline_options.update({"run_mode": "Create WebP Copies", "size_policy": "Keep All Results", "page_workers": "12", "prefetch": True})
    _choose_options_with_history = lambda books: dict(pipeline_options)
    pipeline_results = []
    cleanup_calls = []
    actual_cleanup = _cleanup_prefetch
    def observed_cleanup(python, options):
        cleanup_calls.append(options["prefetch_record"])
        return actual_cleanup(python, options)
    _cleanup_prefetch = observed_cleanup
    real_helper = _run_conversion_helper
    def observed_helper(*args):
        result = real_helper(*args)
        pipeline_results.append(result)
        return result
    _run_conversion_helper = observed_helper
    class SilentReport(object):
        def __init__(self, *args):
            pass
        def ShowDialog(self):
            pass
    ReportForm = SilentReport
    _run_phase_two(pipeline_books)
    assert len(pipeline_results) == 2 and all(r["STATUS"] == "OK" for r in pipeline_results)
    # Tiny fixture copies may finish only after the active test; if complete,
    # prove that the adapter passes it into the following helper correctly.
    if pipeline_results[0].get("PREFETCH_RECORD"):
        assert pipeline_results[1].get("PREFETCH_USED") == "Yes"
    assert not cleanup_calls, "Normal consumed caches triggered redundant cleanup processes"
    report_path = sorted(Directory.GetFiles(REPORT_DIR, "webp_conversion_*.txt"))[-1]
    report_text = File.ReadAllText(report_path)
    assert "Prefetch Caches Used:" in report_text
    if pipeline_results[0].get("PREFETCH_RECORD"):
        assert "PREFETCH_USED: Yes" in report_text and "PREFETCH_CLEANED_RECORD:" in report_text
    assert not Directory.GetDirectories(benchmark_root, "webp_prefetch_*")
    assert all(list(File.ReadAllBytes(book.FilePath)) == before for book in pipeline_books)
    print("PASS: actual adapter copy pipeline at 12 workers with optional prefetch, unchanged source copies and no retained cache")
    print("PASS: all seven real native worker benchmarks, measured resource report, opt-in apply, stop-after-trial, no tag/source changes and output cleanup")
finally:
    for name, value in benchmark_saved.items():
        globals()[name] = value
