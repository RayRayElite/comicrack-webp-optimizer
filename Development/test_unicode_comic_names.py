# Native integration tests use generated copies only, never collection originals.
def test_unicode_comic_names():
    names = ['REPORT_DIR', 'SETTINGS_PATH', 'OptionsForm', 'ProgressForm', 'ReportForm', '_write_comicinfo_temp_file', '_write_comicbook_temp_file']
    saved = dict((name, globals()[name]) for name in names)
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Unicode Comic Names', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    fixtures = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Trial Helper Checks')
    fixture = next(Path.Combine(folder, 'original.cbz') for folder in Directory.GetDirectories(fixtures) if File.Exists(Path.Combine(folder, 'results.json')))
    original = list(File.ReadAllBytes(fixture))
    titles = [u'X\u00b2 Issue \u00bd', u'Caf\u00e9 \u2014 L\u2019histoire', u'\u6f22\u5b57 \u03a9 [#1]', u'Comic \U0001f4da']
    class Book(object):
        def __init__(self, path):
            self.FilePath, self.Caption, self.FileSize, self.PagesRead = path, Path.GetFileName(path), FileInfo(path).Length, 7
            self.values = {}
        def GetCustomValue(self, key): return self.values.get(key, '')
        def SetCustomValue(self, key, value): self.values[key] = value
    books = []
    for title in titles:
        folder = Path.Combine(root, title)
        Directory.CreateDirectory(folder)
        source = Path.Combine(folder, title + '.cbz')
        File.Copy(fixture, source, False)
        books.append(Book(source))
    reports = []
    class Report(object):
        def __init__(self, text, path, **kwargs): self.retry_request = None; reports.append(text)
        def ShowDialog(self): pass
        def Dispose(self): pass
    native_progress = ProgressForm
    def hidden_progress():
        progress = native_progress(); progress.Opacity = 0; progress.ShowInTaskbar = False
        return progress
    options = {'run_mode': 'Create WebP Copies', 'quality_mode': 'Q80', 'encoder_backend': ENCODER_BACKEND_VALUES[0], 'size_policy': 'Keep All Results', 'page_workers': '2', 'create_backup': False, 'resume_completed': False, 'work_dir': '', 'cbr_mode': CBR_MODE_VALUES[0]}
    class Options(object):
        def __init__(self): self.options = dict(options)
        def ShowDialog(self): return DialogResult.OK
    try:
        globals().update(REPORT_DIR=Path.Combine(root, 'Reports'), SETTINGS_PATH=Path.Combine(root, 'settings.xml'), OptionsForm=Options, ProgressForm=hidden_progress, ReportForm=Report)
        globals()['_write_comicinfo_temp_file'] = globals()['_write_comicbook_temp_file'] = lambda *args: ''
        for book in books:
            scan = _scan_book(book, _find_archive_tool())
            assert scan.get('eligible') and scan.get('image_format') == 'JPG', (book.FilePath, scan)
        _run_phase_two(books)
        assert 'Converted Books: 4' in reports[-1], reports[-1]
        for book in books:
            copy = Path.Combine(Path.GetDirectoryName(book.FilePath), Path.GetFileNameWithoutExtension(book.FilePath) + ' [WebP].cbz')
            assert File.Exists(copy), copy
            assert list(File.ReadAllBytes(book.FilePath)) == original
            scan = _scan_book(Book(copy), _find_archive_tool())
            assert scan.get('image_format') == 'WEBP', scan
        options['run_mode'] = 'Replace Originals'
        _run_phase_two(books)
        assert 'Converted Books: 4' in reports[-1], reports[-1]
        for book in books:
            assert book.PagesRead == 7 and File.Exists(book.FilePath)
            scan = _scan_book(book, _find_archive_tool())
            assert scan.get('image_format') == 'WEBP', scan
            assert not File.Exists(book.FilePath + '.webp-recovery.txt')
        print('PASS: generated CBZs with superscript, fraction, accent, em dash, curly apostrophe, CJK, Greek and emoji in folder and filename: real scan, copy and replace, output scans, unchanged copy sources and preserved book references')
        print('Fixture folder: ' + root)
    finally:
        globals().update(saved)
test_unicode_comic_names()

