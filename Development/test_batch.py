"""Native checkpoint/resume and streaming integration checks on generated comics.

Executed in the actual IronPython namespace by render_ui.ps1. No library or
production comic is touched; all records and outputs use an isolated Reports.
"""
batch_saved = dict((key, globals()[key]) for key in ["REPORT_DIR", "SETTINGS_PATH", "OptionsForm", "ProgressForm", "ReportForm", "_scan_book", "_run_conversion_helper", "_set_scan_custom_values", "_write_comicinfo_temp_file", "_write_comicbook_temp_file", "_write_book_checkpoint"])
batch_root = Path.Combine(render_dir, "batch-" + System.Guid.NewGuid().ToString("N"))
Directory.CreateDirectory(batch_root)
try:
    REPORT_DIR = Path.Combine(batch_root, "Reports")
    SETTINGS_PATH = Path.Combine(batch_root, "settings.xml")
    policy = {"run_mode": "Create WebP Copies", "quality_mode": "Q80", "encoder_backend": ENCODER_BACKEND_VALUES[0], "size_policy": "Keep All Results", "page_workers": "2", "resume_completed": True}
    source = Path.Combine(batch_root, "source.cbz")
    output = Path.Combine(batch_root, "output.cbz")
    _write_text_file(source, "unchanged synthetic source")
    _write_text_file(output, "validated synthetic output")
    scan = {"file_path": source, "caption": u"Checkpoint caf\u00e9 & test", "eligible": True}
    _write_book_checkpoint(scan, policy, output, "completed", {"STATUS": "OK"})
    resumed = _resume_book_checkpoint(source, policy)
    assert resumed[0]["caption"] == scan["caption"]
    assert resumed[1]["SKIP_REASON"] == "RESUMED"
    changed = dict(policy)
    changed["quality_mode"] = "Q75"
    assert _resume_book_checkpoint(source, changed) is None
    workers = dict(policy)
    workers["page_workers"] = "4"
    assert _resume_book_checkpoint(source, workers) is not None
    File.SetLastWriteTimeUtc(source, DateTime.UtcNow.AddMinutes(3))
    assert _resume_book_checkpoint(source, policy) is None
    _write_book_checkpoint(scan, policy, output, "completed", {"STATUS": "OK"})
    _write_text_file(output, "output changed")
    assert _resume_book_checkpoint(source, policy) is None
    _write_book_checkpoint(scan, policy, output, "pending")
    try:
        _resume_book_checkpoint(source, changed)
    except Exception, ex:
        assert "inspection" in _safe_unicode(ex)
    else:
        raise AssertionError("Changed quality bypassed interrupted-output guard")
    try:
        _resume_book_checkpoint(source, policy)
    except Exception, ex:
        assert "inspection" in _safe_unicode(ex)
    else:
        raise AssertionError("Pending output was silently reused")
    File.Delete(output)
    try:
        _resume_book_checkpoint(source, policy)
    except Exception, ex:
        assert "inspection" in _safe_unicode(ex)
    else:
        raise AssertionError("Missing output incorrectly proved that a helper had exited")
    _write_book_checkpoint(scan, policy, output, "retryable", {"STATUS": "ERROR"})
    assert _resume_book_checkpoint(source, policy) is None
    _write_text_file(source + ".webp-recovery.txt", "Unresolved replacement")
    try:
        _resume_book_checkpoint(source, policy)
    except Exception:
        pass
    else:
        raise AssertionError("Pending recovery record ignored")
    File.Delete(source + ".webp-recovery.txt")
    _write_book_checkpoint(scan, policy, "", "skipped", {"STATUS": "SKIPPED", "SKIP_REASON": "SIZE_POLICY"})
    assert "size policy" in _resume_book_checkpoint(source, policy)[1]["MESSAGE"]
    # CBR -> CBZ completion must also be found under ComicRack's new path.
    replacement = dict(policy)
    replacement["run_mode"] = "Replace Originals"
    _write_text_file(output, "installed cbz")
    _write_book_checkpoint(scan, replacement, output, "completed", {"STATUS": "OK"})
    File.Delete(source)
    assert _resume_book_checkpoint(output, replacement) is not None
    assert _resume_book_checkpoint(source, replacement) is not None
    target = _checkpoint_path(output, replacement)
    _write_text_file(target, "corrupt XML")
    try:
        _resume_book_checkpoint(output, replacement)
    except Exception:
        pass
    else:
        raise AssertionError("Corrupt checkpoint ignored")
    print("PASS: durable checkpoint identity, changed policy/source/output, worker-independent reuse, pending ambiguity, recovery records, extension alias and corrupt XML")

    # A fresh options dialog round-trips the new settings, with no real settings touched.
    form = OptionsForm()
    form._workers_combo.SelectedItem = "4"
    form._resume_checkbox.Checked = False
    form._save(None, None)
    form.Dispose()
    form = OptionsForm()
    assert form._workers_combo.SelectedItem == "4" and not form._resume_checkbox.Checked
    form._reset_settings(None, None)
    assert form._workers_combo.SelectedItem == "1" and form._resume_checkbox.Checked
    form.Dispose()

    class BatchBook(object):
        def __init__(self, path):
            self.FilePath, self.Caption = path, Path.GetFileName(path)
            self.FileSize = FileInfo(path).Length
    class BatchOptions(object):
        def __init__(self):
            self.options = dict(policy)
        def ShowDialog(self):
            return DialogResult.OK
    batch_reports = []
    class BatchReport(object):
        def __init__(self, text, path):
            batch_reports.append(text)
        def ShowDialog(self):
            pass
    NativeProgress = ProgressForm
    def BatchProgress():
        progress = NativeProgress()
        progress.Opacity = 0
        progress.ShowInTaskbar = False
        return progress
    fixture_root = Path.Combine(SCRIPT_DIR, "Development", "Test Environment", "Trial Helper Checks")
    fixture = next(Path.Combine(folder, "original.cbz") for folder in Directory.GetDirectories(fixture_root) if File.Exists(Path.Combine(folder, "results.json")))
    books = []
    for name in ["first.cbz", "second.cbz"]:
        path = Path.Combine(batch_root, name)
        File.Copy(fixture, path, False)
        books.append(BatchBook(path))
    events = []
    real_scan, real_helper = _scan_book, _run_conversion_helper
    def batch_scan(book, tool):
        events.append("scan " + book.Caption)
        return real_scan(book, tool)
    def batch_helper(python, tool, result, options, book):
        events.append("convert " + book.Caption)
        return real_helper(python, tool, result, options, book)
    OptionsForm, ProgressForm, ReportForm = BatchOptions, BatchProgress, BatchReport
    _scan_book, _run_conversion_helper = batch_scan, batch_helper
    _set_scan_custom_values = lambda *args: None
    _write_comicinfo_temp_file = lambda *args: ""
    _write_comicbook_temp_file = lambda *args: ""
    _run_phase_two(books)
    assert events == ["scan first.cbz", "convert first.cbz", "scan second.cbz", "convert second.cbz"], events
    assert "Concurrent Pages: 2" in batch_reports[-1] and "TIME_ENCODE_SECONDS" in batch_reports[-1]
    assert "Converted Books: 2" in batch_reports[-1]
    events[:] = []
    _run_phase_two(books)
    assert events == []
    assert "Resumed Completed Books: 2" in batch_reports[-1] and "Converted Books: 0" in batch_reports[-1]
    assert len(Directory.GetFiles(batch_root, "* [WebP]*.cbz")) == 2

    # Interrupt the session after book one; retry must reuse book one and finish book two.
    interrupted = []
    for name in ["third.cbz", "fourth.cbz"]:
        path = Path.Combine(batch_root, name)
        File.Copy(fixture, path, False)
        interrupted.append(BatchBook(path))
    def interrupt_second(python, tool, result, options, book):
        if book.Caption == "fourth.cbz":
            raise Exception("Injected session interruption")
        return batch_helper(python, tool, result, options, book)
    _run_conversion_helper = interrupt_second
    try:
        _run_phase_two(interrupted)
    except Exception, ex:
        assert "Injected session" in _safe_unicode(ex)
    else:
        raise AssertionError("Interruption did not occur")
    events[:] = []
    _run_conversion_helper = batch_helper
    _run_phase_two(interrupted)
    assert events == []
    assert "needs inspection" in batch_reports[-1] and "Resumed Completed Books: 1" in batch_reports[-1]
    # In this injected failure no process was launched; simulate explicit review
    # by clearing only its two known records inside the isolated test directory.
    File.Delete(_pending_checkpoint_path(interrupted[1].FilePath))
    File.Delete(_checkpoint_path(interrupted[1].FilePath, policy))
    _run_phase_two(interrupted)
    assert events == ["scan fourth.cbz", "convert fourth.cbz"], events
    assert "Resumed Completed Books: 1" in batch_reports[-1]
    assert len(Directory.GetFiles(batch_root, "* [WebP]*.cbz")) == 4
    # A checkpoint write failure must prevent starting a new conversion.
    real_write = _write_book_checkpoint
    fail_path = Path.Combine(batch_root, "checkpoint-failure.cbz")
    File.Copy(fixture, fail_path, False)
    def refuse_checkpoint(*args):
        raise Exception("Injected checkpoint write failure")
    _write_book_checkpoint = refuse_checkpoint
    events[:] = []
    try:
        _run_phase_two([BatchBook(fail_path)])
    except Exception, ex:
        assert "checkpoint write failure" in _safe_unicode(ex)
    else:
        raise AssertionError("Conversion started without durable intent")
    assert events == ["scan checkpoint-failure.cbz"]
    _write_book_checkpoint = real_write
    # Cleanup failure finishes the active book and stops before the next one.
    cleanup_books = []
    for name in ["cleanup-first.cbz", "cleanup-second.cbz"]:
        path = Path.Combine(batch_root, name)
        File.Copy(fixture, path, False)
        cleanup_books.append(BatchBook(path))
    def warn_cleanup(*args):
        result = batch_helper(*args)
        result["CLEANUP_WARNING"] = "Injected temporary cleanup failure"
        return result
    _run_conversion_helper = warn_cleanup
    _run_phase_two(cleanup_books)
    assert "Not Processed: 1" in batch_reports[-1] and "Injected temporary cleanup failure" in batch_reports[-1]
    _run_conversion_helper = batch_helper
    progress = NativeProgress()
    progress.Opacity = 0
    progress.ShowInTaskbar = False
    progress.Show()
    progress.set_batch(books)
    progress.update_state(0, "Converting and validating archives", "first", 1, 2, 0)
    progress.record_work({"STATUS": "OK", "TIME_WORKER_SECONDS": "10", "SOURCE_SIZE": str(books[0].FileSize)})
    assert "source MB/s" in progress._rate_label.Text and "Rough ETA" in progress._rate_label.Text
    assert "source bytes" in progress._rate_label.Text
    assert progress._progress_bar.Value == 50
    bitmap = Bitmap(progress.Width, progress.Height)
    progress.DrawToBitmap(bitmap, Rectangle(0, 0, progress.Width, progress.Height))
    bitmap.Save(Path.Combine(render_dir, "progress-performance.png"), ImageFormat.Png)
    bitmap.Dispose()
    progress.finish()
    print("PASS: native worker settings, streaming scan/convert ordering, actual two-worker conversions, no-duplicate resume after interruption, stage reports and throughput/ETA")
    # Exercise the actual three-book, five-quality orchestration, not just a
    # standalone estimator: this caught the missing quality-mode feed in 0.8.
    policy["run_mode"] = "Test savings & quality"
    observed_quality = []
    def QualityProgress():
        progress = BatchProgress()
        original_record = progress.record_quality_pass
        def record(trial):
            original_record(trial)
            observed_quality.append((progress._quality_completed, progress._rate_label.Text))
        progress.record_quality_pass = record
        return progress
    ProgressForm = QualityProgress
    _run_phase_two(books + interrupted[:1])
    assert len(observed_quality) == 15
    assert observed_quality[0][0] == 1 and "Test speed" in observed_quality[0][1]
    assert "remaining test passes" in observed_quality[4][1]
    assert observed_quality[-1][0] == 15
    assert "Compared Books: 3" in batch_reports[-1]
    progress = NativeProgress()
    progress.set_quality_batch([{"file_size": 100}, {"file_size": 200}, {"file_size": 300}])
    for unused in range(5):
        progress.record_quality_pass({"STATUS": "OK", "SOURCE_SIZE": "100", "SECONDS": "10"})
    progress.update_state(68, "Converting and validating archives", "Middle sampled book", 4, 7, 3)
    assert progress._progress_bar.Value == 63
    assert "5 of 15" in progress._count_label.Text
    progress.finish()
    print("PASS: actual three-book quality test shows speed/ETA after pass one and updates through all fifteen passes")
finally:
    globals().update(batch_saved)
