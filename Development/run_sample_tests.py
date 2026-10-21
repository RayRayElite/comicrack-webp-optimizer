"""Non-destructive sample checks. Run with Python 3; outputs stay in Test Environment."""
import argparse
import hashlib
import html
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid
import zipfile

from PIL import Image
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webp_convert_helper as helper

BASE = Path(__file__).resolve().parent.parent


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def replacement_checks():
    # Execute the actual IronPython function with an in-memory .NET filesystem
    # adapter. Failures are injected at the filesystem boundary.
    import types
    source = (BASE / 'WebPOptimizer.py').read_text(encoding='utf-8')
    function = source.split('def _finalize_replacement(', 1)[1].split('\ndef _extract_report_summary_items', 1)[0]
    function = ('def _finalize_replacement(' + function).replace('except Exception, ex:', 'except Exception as ex:')
    outcomes = []
    for case in ('same', 'same_failure', 'extension', 'move_failure', 'rollback_failure', 'collision', 'cleanup_failure', 'backup', 'pending_recovery', 'source_changed'):
        files = {'book.cbr': b'original', 'temp.cbz': b'converted'}
        same = case in ('same', 'same_failure', 'backup')
        final = 'book.cbr' if same else 'book.cbz'
        if case == 'collision':
            files[final] = b'existing'

        if case == 'pending_recovery':
            files['book.cbr.webp-recovery.txt'] = b'pending'

        class Files:
            Exists = staticmethod(lambda p: p in files)

            @staticmethod
            def Copy(src, dst, overwrite):
                if dst in files and not overwrite:
                    raise OSError('exists')
                files[dst] = files[src]

            @staticmethod
            def Move(src, dst):
                if (case in ('move_failure', 'rollback_failure') and src == 'temp.cbz') or (case == 'rollback_failure' and '.webp-rollback-' in src):
                    raise OSError('injected rename failure')
                if dst in files:
                    raise OSError('exists')
                files[dst] = files.pop(src)

            @staticmethod
            def Replace(src, dst, backup):
                if case == 'same_failure':
                    raise OSError('injected replacement failure')
                files[dst] = files.pop(src)

            @staticmethod
            def Delete(path):
                if case == 'cleanup_failure':
                    raise OSError('injected cleanup failure')
                del files[path]

        ns = dict(FileInfo=lambda p: types.SimpleNamespace(Length=20, LastWriteTimeUtc=types.SimpleNamespace(Ticks=2)), _write_text_file=lambda p, text: files.__setitem__(p, text.encode()), File=Files, Path=types.SimpleNamespace(GetFullPath=str, GetExtension=lambda p: '.cbr'),
                  System=types.SimpleNamespace(Guid=types.SimpleNamespace(NewGuid=lambda: types.SimpleNamespace(ToString=lambda _: 'test'))),
                  _safe_unicode=str, _build_final_replace_path=lambda *args: final,
                  _build_backup_path=lambda p: p + '.backup')
        exec(function, ns)
        helper_result = {'STATUS': 'OK', 'OUTPUT_PATH': 'temp.cbz'}
        if case == 'source_changed':
            helper_result['SOURCE_SIGNATURE'] = (10, 1)
        result = ns['_finalize_replacement']('book.cbr', helper_result, {'create_backup': case == 'backup'})
        failed = case in ('same_failure', 'move_failure', 'rollback_failure', 'collision', 'pending_recovery', 'source_changed')
        assert result['STATUS'] == ('ERROR' if failed else 'OK'), (case, result)
        if failed:
            assert b'original' in files.values() and files['temp.cbz'] == b'converted', case
        else:
            assert files[final] == b'converted', case
        if case == 'collision':
            assert files[final] == b'existing'
        if case == 'pending_recovery':
            assert files['book.cbr.webp-recovery.txt'] == b'pending'
        if case == 'backup':
            assert files['book.cbr.backup'] == b'original'
        outcomes.append(case)
    return outcomes


def compare_archives(source, output):
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(output) as converted:
        expected = {}
        dimensions = {}
        for name in original.namelist():
            if name.endswith('/'):
                continue
            suffix = Path(name).suffix.lower()
            target = str(Path(name).with_suffix('.webp')).replace('\\', '/') if suffix in ('.jpg', '.jpeg') else name
            expected[target] = name
            if suffix in helper.IMAGE_EXTENSIONS:
                with Image.open(io.BytesIO(original.read(name))) as image:
                    dimensions[target] = image.size
        assert set(converted.namelist()) == set(expected), 'Manifest mismatch'
        assert converted.testzip() is None
        for target, name in expected.items():
            if target in dimensions:
                with Image.open(io.BytesIO(converted.read(target))) as image:
                    image.load()
                    assert image.size == dimensions[target], target
            if Path(name).suffix.lower() not in ('.jpg', '.jpeg'):
                assert original.read(name) == converted.read(target), name
        # Compare filename ordering after reversing extension substitution.
        old_order = sorted((n for n in expected.values() if Path(n).suffix.lower() in helper.IMAGE_EXTENSIONS), key=str.casefold)
        new_order = [expected[n] for n in sorted(dimensions, key=str.casefold)]
        assert old_order == new_order, 'Page filename order changed'
        return len(dimensions)


def previews(source, run):
    folder = run / 'previews'
    folder.mkdir()
    rows = []
    backend, tool = helper.resolve_encoder_backend('ImageMagick (Recommended)')
    with zipfile.ZipFile(source) as archive:
        pages = sorted(n for n in archive.namelist() if Path(n).suffix.lower() in ('.jpg', '.jpeg'))
        indices = sorted(set((0, len(pages) // 2, len(pages) - 1))) if pages else []
        for number, index in enumerate(indices):
            name = pages[index]
            original = folder / ('page%d.jpg' % number)
            original.write_bytes(archive.read(name))
            with Image.open(original) as image:
                width, height = image.size
            options = [('Original', original.name, original.stat().st_size)]
            for quality in (75, 85, 90, 95):
                output = original.with_name('page%d-q%d.webp' % (number, quality))
                settings = helper.quality_options(str(quality) + '%')
                if backend.startswith('ImageMagick'):
                    helper.encode_with_magick(tool, str(original), str(output), settings, 'No Resize', backend)
                elif backend == 'cwebp':
                    helper.encode_with_cwebp(tool, str(original), str(output), settings, 'No Resize')
                else:
                    helper.encode_with_pillow(str(original), str(output), settings, 'No Resize')
                options.append(('Q%d' % quality, output.name, output.stat().st_size))
            cells = ''.join('<figure><figcaption>%s Â· %.1f KB</figcaption><a href="%s"><img src="%s"></a></figure>' % (label, size / 1024, filename, filename) for label, filename, size in options)
            rows.append('<h2>%s â€” %d Ã— %d</h2><div class="row">%s</div>' % (html.escape(name), width, height, cells))
    (folder / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>WebP quality samples</title><style>body{background:#181818;color:#eee;font:16px system-ui;margin:24px}.row{display:flex;overflow:auto;gap:16px}figure{margin:0;flex:0 0 420px}img{width:420px}figcaption{padding:12px 0}a{color:inherit}</style><h1>Original and WebP quality samples</h1><p>Encoder: ' + html.escape(backend) + '. Dimensions unchanged. Click any image for the full-resolution file; browser scaling can conceal artifacts. Compare lettering, gradients, linework and dark areas. Quality numbers are encoder settings, not guarantees.</p>' + ''.join(rows), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limit', type=int, default=3)
    args = parser.parse_args()
    originals = BASE / 'Development' / 'Test Environment' / 'Original Test Comics'
    sources = sorted(originals.rglob('*.cbz'))
    if not sources or args.limit < 1:
        raise SystemExit('No samples found or invalid limit')
    run = BASE / 'Development' / 'Test Environment' / 'Runs' / (time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6])
    run.mkdir(parents=True)
    # Avoid writing any helper extraction outside this plugin folder.
    work = run / 'work'
    work.mkdir()
    env = dict(os.environ, TEMP=str(work), TMP=str(work))
    report = {'source_hashes_before': {str(p.relative_to(originals)): digest(p) for p in sources}, 'replacement_cases': replacement_checks(), 'conversions': []}
    archive_tool = BASE.parent.parent / 'ComicRackCE_nightly' / 'Resources' / '7z.exe'
    try:
        for number, source in enumerate(sources[:args.limit]):
            output = run / ('converted_%02d.cbz' % number)
            command = [sys.executable, str(BASE / 'webp_convert_helper.py'), '--work-dir', str(work), '--archive-path', str(source), '--output-path', str(output), '--archive-tool', str(archive_tool), '--archive-type', 'cbz', '--quality-mode', '85%', '--size-policy', 'Keep All Results', '--resize-mode', 'No Resize']
            result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=1800)
            entry = {'source': str(source.relative_to(originals)), 'returncode': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
            report['conversions'].append(entry)
            assert result.returncode == 0 and 'STATUS=OK' in result.stdout, entry
            entry['pages_verified'] = compare_archives(source, output)
            entry['savings_percent'] = round(100 * (1 - output.stat().st_size / source.stat().st_size), 2)
            print(json.dumps(entry), flush=True)
        previews(sources[0], run)
        report['status'] = 'PASS'
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error'] = repr(exc)
        raise
    finally:
        report['source_hashes_after'] = {str(p.relative_to(originals)): digest(p) for p in sources}
        report['originals_unchanged'] = report['source_hashes_before'] == report['source_hashes_after']
        (run / 'results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print('Report:', run / 'results.json', flush=True)
        assert report['originals_unchanged'], 'Source hashes changed'


if __name__ == '__main__':
    main()
