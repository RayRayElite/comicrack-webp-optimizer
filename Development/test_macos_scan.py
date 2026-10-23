# Native adapter scan must match worker page discovery without writing library tags.
def test_macos_sidecar_scan():
    assert _is_macos_sidecar('__MACOSX/._001.jpg')
    assert _is_macos_sidecar(r'folder\__MACOSX\._001.png')
    assert not _is_macos_sidecar('._legitimate.jpg')
    assert not _is_macos_sidecar('__MACOSX/actual-page.jpg')
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Metadata Scan', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    path = Path.Combine(root, 'generated.cbz')
    File.WriteAllText(path, 'Read-only mocked listing fixture')
    class Book(object):
        FilePath = path
        Caption = 'Generated'
    saved = globals()['_run_archive_list']
    try:
        globals()['_run_archive_list'] = lambda tool, archive: (0, 'Path = 001.jpg\nSize = 10\n\nPath = __MACOSX/._001.png\nSize = 32\n\n', '')
        result = _scan_book(Book(), 'unused-tool')
        assert result['image_count'] == 1 and result['jpg_count'] == 1 and result['png_count'] == 0, result
        assert result['image_format'] == 'JPG' and result['eligible'], result
    finally:
        globals()['_run_archive_list'] = saved
    print('PASS: native scan excludes only __MACOSX/._ sidecars, keeps real/root-dot image names and matches JPEG eligibility')
test_macos_sidecar_scan()
