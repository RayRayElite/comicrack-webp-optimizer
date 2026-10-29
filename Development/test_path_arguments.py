# Actual Windows argv and UTF-8 transport, including a trailing folder slash.
def test_path_arguments():
    cases = [u'D:\\Folder with spaces\\', u'\\\\server\\share\\folder\\', u'caf\u00e9 \u1d57\u02b0 # []', u'X\u00b2 issue \u00bd \u2014 \u6f22', 'quoted "value"', '', 'tail']
    python = _find_python_tool()
    info = ProcessStartInfo(); info.FileName = python
    program = "import sys;sys.stdout.reconfigure(encoding='utf-8');sys.stdout.write('\\n'.join(sys.argv[1:]))"
    info.Arguments = ('-3 ' if python == 'py' else '') + '-c ' + _quote_argument(program) + ' ' + ' '.join(_quote_argument(value) for value in cases)
    info.UseShellExecute, info.CreateNoWindow = False, True
    info.RedirectStandardOutput, info.RedirectStandardError = True, True
    info.StandardOutputEncoding = info.StandardErrorEncoding = Encoding.UTF8
    process = Process(); process.StartInfo = info
    try:
        output, errors = _wait_for_process(process)
        assert process.ExitCode == 0, errors
        assert output.splitlines() == cases, (output, cases)
    finally:
        process.Dispose()
    expected = Path.GetFullPath(u'D:\\Folder with spaces\\')
    assert _normalize_work_directory('"' + expected + '"') == expected
    assert _normalize_work_directory('') == ''
    for value in ['D:\\bad|folder', 'D:\\bad"folder', 'file:///D:/Folder', 'relative/folder', 'D:\\bad\nfolder']:
        try:
            _normalize_work_directory(value)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid folder accepted: ' + repr(value))
    try:
        _run_performance_test([], {'work_dir': 'D:\\bad|folder'})
    except ValueError:
        pass
    else:
        raise AssertionError('Benchmark accepted invalid temporary folder')
    check = _setup_checks({'run_mode': 'Create WebP Copies', 'work_dir': 'D:\\bad|folder'})
    assert check['STATUS'] == 'ERROR' and 'Temporary storage' in check['CHECK_MESSAGE']
    fixtures = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Unicode Archive Errors')
    if Directory.Exists(fixtures):
        sources = [p for p in Directory.GetFiles(fixtures, '*.cbz', SearchOption.AllDirectories) if Path.GetFileName(p).startswith('source-')]
        if sources:
            code, listing, errors = _run_archive_list(_find_archive_tool(), sources[0])
            assert code == 0 and u'page-\u6f22.jpg' in listing, (listing, errors)
    print('PASS: actual Windows argv round-trip with trailing slashes, quotes and Unicode; pasted folder quotes accepted and invalid/relative paths explained')
test_path_arguments()
