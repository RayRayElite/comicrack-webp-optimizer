# Known destination conflicts must stop before conversion or new pending records.
def test_destination_conflicts():
    names = ['REPORT_DIR', 'SETTINGS_PATH', 'OptionsForm', 'ProgressForm', 'ReportForm', '_find_archive_tool', '_find_python_tool', '_scan_book', '_run_conversion_helper', '_write_book_checkpoint']
    saved = dict((name, globals()[name]) for name in names)
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Destination Conflicts', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    source, destination = Path.Combine(root, 'same.cbr'), Path.Combine(root, 'same.cbz')
    File.WriteAllText(source, 'Original CBR fixture'); File.WriteAllText(destination, 'Existing CBZ fixture')
    class Book(object):
        FilePath, Caption, FileSize = source, 'Generated CBR', FileInfo(source).Length
    options = {'run_mode': 'Replace Originals', 'cbr_mode': CBR_MODE_VALUES[0], 'create_backup': False, 'resume_completed': False, 'work_dir': ''}
    reports = []
    class Options(object):
        def __init__(self): self.options = dict(options)
        def ShowDialog(self): return DialogResult.OK
    class Report(object):
        def __init__(self, text, path, **kwargs):
            self.retry_request = None
            reports.append(text)
        def Dispose(self): pass
        def ShowDialog(self): pass
    def forbidden(*args, **kwargs): raise AssertionError('Conversion/checkpoint started despite known destination conflict')
    NativeProgress = ProgressForm
    def hidden_progress():
        progress = NativeProgress(); progress.Opacity = 0; progress.ShowInTaskbar = False
        return progress
    try:
        globals().update(REPORT_DIR=Path.Combine(root, 'Reports'), SETTINGS_PATH=Path.Combine(root, 'settings.xml'), OptionsForm=Options, ReportForm=Report, ProgressForm=hidden_progress)
        globals()['_find_archive_tool'] = lambda: 'generated-tool'
        globals()['_find_python_tool'] = lambda: 'generated-python'
        globals()['_scan_book'] = lambda book, tool: {'file_path': source, 'caption': 'Generated CBR', 'archive_type': 'cbr', 'file_size': FileInfo(source).Length, 'eligible': True, 'image_format': 'JPG'}
        globals()['_run_conversion_helper'] = globals()['_write_book_checkpoint'] = forbidden
        _run_phase_two([Book()])
        assert 'DESTINATION_EXISTS' in reports[-1] and 'Converted Books: 0' in reports[-1]
        assert not Directory.Exists(Path.Combine(REPORT_DIR, 'Checkpoints'))
        assert not File.Exists(source + '.webp-recovery.txt')
        assert File.ReadAllText(source) == 'Original CBR fixture' and File.ReadAllText(destination) == 'Existing CBZ fixture'
        # Guard a destination that exists by finalization time, preserving output.
        temporary = Path.Combine(root, 'validated-temp.cbz'); File.WriteAllText(temporary, 'Retained converted fixture')
        result = _finalize_replacement(source, {'STATUS': 'OK', 'OUTPUT_PATH': temporary}, options)
        assert result['ERROR_CODE'] == 'DESTINATION_EXISTS'
        assert File.Exists(temporary) and not File.Exists(source + '.webp-recovery.txt')
        assert _replacement_destination_conflict(source, {'run_mode': 'Create WebP Copies', 'cbr_mode': CBR_MODE_VALUES[0]}) is None
    finally:
        globals().update(saved)
    print('PASS: destination conflict before worker/checkpoint, unchanged source/destination, retained late-conflict output, no misleading recovery file and unaffected copy mode')
test_destination_conflicts()


def test_readonly_replacement_and_failure_evidence():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Replacement Access', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    source, converted = Path.Combine(root, 'source.cbz'), Path.Combine(root, 'converted.cbz')
    File.WriteAllText(source, 'Original fixture'); File.WriteAllText(converted, 'Converted fixture')
    options = {'run_mode': 'Replace Originals', 'create_backup': False, 'cbr_mode': CBR_MODE_VALUES[0]}
    File.SetAttributes(source, File.GetAttributes(source) | FileAttributes.ReadOnly)
    original_attributes = File.GetAttributes(source)
    try:
        denied = False
        try: File.Replace(converted, source, None)
        except System.UnauthorizedAccessException: denied = True
        assert denied, 'Native read-only destination did not reproduce access denied'
        problem = _replacement_source_problem(source, options)
        assert problem['ERROR_CODE'] == 'SOURCE_ARCHIVE_READ_ONLY'
        assert _replacement_source_problem(source, {'run_mode': 'Create WebP Copies'}) is None
        helper = {'STATUS': 'OK', 'OUTPUT_PATH': converted, 'TIME_ENCODE_SECONDS': '1.25', 'OUTPUT_SIZE': '17'}
        result = _finalize_replacement(source, helper, options)
        assert result['ERROR_CODE'] == 'SOURCE_ARCHIVE_READ_ONLY'
        assert result['TIME_ENCODE_SECONDS'] == '1.25' and result['OUTPUT_SIZE'] == '17'
        assert not File.Exists(source + '.webp-recovery.txt')
        assert File.GetAttributes(source) == original_attributes
        assert File.ReadAllText(source) == 'Original fixture' and File.ReadAllText(converted) == 'Converted fixture'
    finally:
        File.SetAttributes(source, original_attributes & ~FileAttributes.ReadOnly)
    held = File.Open(source, System.IO.FileMode.Open, System.IO.FileAccess.Read, System.IO.FileShare.None)
    try:
        result = _finalize_replacement(source, helper, options)
        assert result['STATUS'] == 'ERROR'
        assert result['ERROR_CODE'] in ['REPLACEMENT_FILE_LOCKED', 'REPLACEMENT_ACCESS_DENIED'], result
        assert result['ERROR_STAGE'] == 'replacing original archive'
        assert result['TIME_ENCODE_SECONDS'] == '1.25' and result['OUTPUT_SIZE'] == '17'
        assert 'HRESULT:' in result['ERROR_DETAIL']
        assert File.Exists(source + '.webp-recovery.txt') and File.Exists(converted)
    finally: held.Dispose()
    assert File.ReadAllText(source) == 'Original fixture'
    print('PASS: native read-only access-denied reproduction, early protection without flag changes/journal, unaffected copy, locked-file diagnosis and retained encode evidence')

test_readonly_replacement_and_failure_evidence()


def test_readonly_stops_before_worker():
    names = ['REPORT_DIR', 'SETTINGS_PATH', 'OptionsForm', 'ProgressForm', 'ReportForm', '_find_archive_tool', '_find_python_tool', '_scan_book', '_run_conversion_helper', '_write_book_checkpoint']
    saved = dict((name, globals()[name]) for name in names)
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'ReadOnly Preflight', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    source = Path.Combine(root, 'source.cbz'); File.WriteAllText(source, 'Original fixture')
    File.SetAttributes(source, FileAttributes.ReadOnly)
    class Book(object): FilePath, Caption, FileSize = source, 'Generated read-only archive', 16
    options = {'run_mode': 'Replace Originals', 'create_backup': False, 'resume_completed': False, 'work_dir': ''}
    reports = []
    class Options(object):
        def __init__(self): self.options = dict(options)
        def ShowDialog(self): return DialogResult.OK
    class Report(object):
        def __init__(self, text, path, **kwargs): reports.append(text); self.retry_request = None
        def ShowDialog(self): pass
        def Dispose(self): pass
    native_progress = ProgressForm
    def progress():
        form = native_progress(); form.Opacity = 0; form.ShowInTaskbar = False
        return form
    def forbidden(*args, **kwargs): raise AssertionError('Read-only source reached conversion or checkpoint creation')
    try:
        globals().update(REPORT_DIR=Path.Combine(root, 'Reports'), SETTINGS_PATH=Path.Combine(root, 'settings.xml'), OptionsForm=Options, ReportForm=Report, ProgressForm=progress)
        globals()['_find_archive_tool'] = lambda: 'generated-tool'
        globals()['_find_python_tool'] = lambda: 'generated-python'
        globals()['_scan_book'] = lambda book, tool: {'file_path': source, 'caption': book.Caption, 'archive_type': 'cbz', 'eligible': True, 'image_format': 'JPG'}
        globals()['_run_conversion_helper'] = globals()['_write_book_checkpoint'] = forbidden
        _run_phase_two([Book()])
        assert 'SOURCE_ARCHIVE_READ_ONLY' in reports[-1] and 'Failed: 1' in reports[-1]
        assert not Directory.Exists(Path.Combine(REPORT_DIR, 'Checkpoints'))
        assert File.GetAttributes(source) & FileAttributes.ReadOnly
        assert not File.Exists(source + '.webp-recovery.txt')
    finally:
        File.SetAttributes(source, FileAttributes.Normal)
        globals().update(saved)
    print('PASS: orchestration rejects a read-only original before worker/checkpoint creation without altering its protection')

test_readonly_stops_before_worker()


def test_readonly_library_field():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'ReadOnly Field', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root); source = Path.Combine(root, 'source.cbz'); File.WriteAllText(source, 'Generated fixture')
    class Book(object):
        def __init__(self): self.values = {}
        def SetCustomValue(self, key, value): self.values[key] = value
        def GetCustomValue(self, key): return self.values.get(key, '')
    book = Book()
    scan = {'file_path': source, 'image_format': 'JPG', 'eligible': True, 'notes': 'Generated scan'}
    _set_scan_custom_values(book, scan)
    assert book.values['WebPReadOnly'] == 'No' and book.values['ImageFormat'] == 'JPG'
    assert book.values['WebPStatus'] == 'Ready'
    File.SetAttributes(source, FileAttributes.ReadOnly)
    try:
        scan.pop('read_only', None); _set_scan_custom_values(book, scan)
        assert book.values['WebPReadOnly'] == 'Yes'
        assert File.GetAttributes(source) & FileAttributes.ReadOnly
        assert 'Original read-only: Yes' in _build_analysis_report([scan], 'generated')
    finally: File.SetAttributes(source, FileAttributes.Normal)
    scan.pop('read_only', None); _set_scan_custom_values(book, scan)
    assert book.values['WebPReadOnly'] == 'No'
    # Completed-work reuse must refresh attributes without relying on an archive scan.
    File.SetAttributes(source, FileAttributes.ReadOnly)
    try:
        _status_after_conversion(book, scan, {'STATUS': 'SKIPPED', 'SKIP_REASON': 'RESUMED', 'OUTPUT_PATH': source}, {'run_mode': 'Replace Originals'})
        assert book.values['WebPReadOnly'] == 'Yes'
    finally: File.SetAttributes(source, FileAttributes.Normal)
    scan = {'file_path': Path.Combine(root, 'missing.cbz'), 'image_format': 'MISSING'}
    _set_scan_custom_values(book, scan)
    assert book.values['WebPReadOnly'] == 'Unknown'
    print('PASS: WebPReadOnly Yes/No/Unknown, field refresh after external changes/resume, preserved workflow labels and unchanged original attributes')

test_readonly_library_field()
