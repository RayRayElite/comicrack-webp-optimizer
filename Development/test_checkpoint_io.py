# Actual IronPython/.NET atomic XML I/O; generated files only.
def test_checkpoint_io():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'CheckpointIO-' + System.Guid.NewGuid().ToString('N')[:8])
    Directory.CreateDirectory(root)
    folder = Path.Combine(root, 'p' * max(1, 180 - len(root) - 1))
    target = Path.Combine(folder, 'b' * 64 + '.xml')
    old_temp = target + '.' + 'c' * 32 + '.tmp'
    short_temp = Path.Combine(folder, 'wo-' + 'c' * 32 + '.tmp')
    assert len(old_temp) > 260 and len(short_temp) < 260 and len(target) < 260
    document = XmlDocument()
    document.LoadXml('<Checkpoint version="2" state="pending" />')
    _save_xml_atomic(document, target, 'generated checkpoint')
    saved = XmlDocument(); saved.Load(target)
    assert saved.DocumentElement.GetAttribute('state') == 'pending'
    document.DocumentElement.SetAttribute('state', 'completed')
    _save_xml_atomic(document, target, 'generated checkpoint')
    saved.Load(target)
    assert saved.DocumentElement.GetAttribute('state') == 'completed'
    assert not Directory.GetFiles(folder, '*.tmp')
    # Hash/percent/Unicode in real directory names must not become a URI.
    special = Path.Combine(root, u'hash # percent % caf\u00e9', 'record.xml')
    document.DocumentElement.SetAttribute('label', u'caf\u00e9 & test')
    _save_xml_atomic(document, special, 'special path')
    saved.Load(special)
    assert saved.DocumentElement.GetAttribute('label') == u'caf\u00e9 & test'
    # Existing completed records survive failed replacement and no temp remains.
    before = File.ReadAllText(target)
    handle = File.Open(target, System.IO.FileMode.Open, System.IO.FileAccess.Read, getattr(System.IO.FileShare, 'None'))
    try:
        try:
            _save_xml_atomic(document, target, 'locked checkpoint')
        except Exception, ex:
            message = _safe_unicode(ex)
            assert 'locked checkpoint' in message and 'replacing existing record' in message and 'characters' in message, message
        else:
            raise AssertionError('Locked checkpoint was overwritten')
    finally:
        handle.Dispose()
    assert File.ReadAllText(target) == before
    assert not Directory.GetFiles(folder, '*.tmp')
    # An actual parent-path problem must surface with useful diagnostics.
    blocker = Path.Combine(root, 'file-not-folder')
    File.WriteAllText(blocker, 'retain me')
    try:
        _save_xml_atomic(document, Path.Combine(blocker, 'child.xml'), 'blocked checkpoint')
    except Exception, ex:
        message = _safe_unicode(ex)
        assert 'creating parent folder' in message and 'blocked checkpoint' in message and 'Original error' in message
    else:
        raise AssertionError('Invalid parent accepted')
    assert File.ReadAllText(blocker) == 'retain me'
    print('PASS: short same-folder XML temp paths, pending/completed replacement, hash/percent/Unicode paths, locked-target preservation, failed-write cleanup and actionable stage/path diagnostics')
test_checkpoint_io()
