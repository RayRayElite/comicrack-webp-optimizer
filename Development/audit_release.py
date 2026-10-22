"""Verify release artifacts against the current explicit source/runtime lists.

Writes a local audit under Release Prep, never publishes. Passing these checks
does not substitute for live installation acceptance or binary license review.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

sys.dont_write_bytecode = True
from build_release import RUNTIME_FILES, VENDOR_FILES, verify_encoder
from build_source import SOURCE_FILES

BASE = Path(__file__).resolve().parent.parent


def inspect(name, expected, prefix=''):
    path = BASE / 'Releases' / name
    manifest = json.loads(path.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest['archive_sha256'], name
    assert {r['path'] for r in manifest['files']} == set(expected), 'Manifest allowlist differs'
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, name
        assert len(archive.namelist()) == len(set(archive.namelist())), 'Duplicate ZIP entries'
        assert set(archive.namelist()) == {prefix + n for n in expected}, 'Unexpected/missing files'
        for entry in manifest['files']:
            content = archive.read(prefix + entry['path'])
            assert content == (BASE / entry['path']).read_bytes(), 'Stale artifact: ' + entry['path']
            assert hashlib.sha256(content).hexdigest() == entry['sha256'], entry['path']
    return {'artifact': name, 'sha256': manifest['archive_sha256'], 'files': len(expected), 'status': 'PASS'}


def main():
    version = re.search(r'^Version\s*=\s*(\S+)', (BASE / 'Package.ini').read_text(), re.M).group(1)
    readme = (BASE / 'README.md').read_text(encoding='utf-8')
    assert ('Current development build: ' + version in readme or 'Current release: ' + version in readme)
    assert '## ' + version + ' ' in (BASE / 'CHANGELOG.md').read_text(encoding='utf-8')
    for name in SOURCE_FILES:
        assert Path(name).suffix.lower() not in {'.exe', '.dll', '.cbz', '.cbr'}
        assert not name.startswith(('Reports/', 'Releases/', 'Development/Test Environment/', 'Development/Release Prep/'))
    results = [inspect('WebPOptimizer-' + version + '.zip', RUNTIME_FILES + VENDOR_FILES, 'WebP Optimizer/'),
               inspect('WebPOptimizer-' + version + '-plugin-only.zip', RUNTIME_FILES, 'WebP Optimizer/'),
               inspect('WebPOptimizer-' + version + '-source.zip', SOURCE_FILES)]
    report = {'version': version, 'technical_artifact_checks': 'PASS', 'artifacts': results,
              'public_release': 'GitHub publication is verified separately; this audit validates local artifacts only',
              'bundled_tools': 'Minimal static encoder: pinned sources, license/notice hashes and system-only DLL imports verified; old Microsoft DLLs excluded',
              'encoder': verify_encoder(),
              'evidence_limit': 'Local package extraction and tests use this PC; not a fresh Windows VM or new user installation.'}
    target = BASE / 'Development/Release Prep/release-audit.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    for result in results:
        print('PASS:', result['artifact'], '- exact current contents, manifest SHA-256, CRC and exclusions')
    print('PASS: local artifact audit; GitHub publication is a separate verification step')


if __name__ == '__main__':
    main()
