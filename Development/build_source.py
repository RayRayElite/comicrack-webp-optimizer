"""Export a reviewable GitHub source tree without local data or vendor binaries.

The ZIP root is the future repository root, unlike the manual-install ZIP.
Do not recursively copy the development workspace: it contains private comics,
reports, test outputs and build archives. All additions here are deliberate.
"""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

sys.dont_write_bytecode = True
from build_release import RUNTIME_FILES, MAGICK_LICENSE_FILES

BASE = Path(__file__).resolve().parent.parent
SOURCE_FILES = RUNTIME_FILES + MAGICK_LICENSE_FILES + [
    '.gitignore', '.gitattributes', '.github/ISSUE_TEMPLATE/bug_report.md',
    '.github/PULL_REQUEST_TEMPLATE.md',
    'Development/README.md', 'Development/build_release.py',
    'Development/build_source.py', 'Development/audit_release.py',
    'Development/build_encoder.py', 'Development/package_encoder.py', 'Development/inspect_pe.py',
    'Development/test_bundled_encoder.py', 'Development/encoder_sources.json', 'Development/ENCODER_BUILD.md', 'Development/quality_lab.html',
    'Development/quality_lab.py', 'Development/render_ui.ps1',
    'Development/run_sample_tests.py', 'Development/test_batch.py',
    'Development/test_color_fidelity.py', 'Development/test_encoders.py',
    'Development/test_filesystem.ps1', 'Development/test_history.py',
    'Development/test_packaged_release.py', 'Development/test_performance.py',
    'Development/test_quality_lab.cjs', 'Development/test_runtime_features.py',
    'Development/test_safety.py', 'Development/test_trial_helper.py',
    'Development/test_archive_discovery.py', 'Development/test_source_package.py', 'Development/test_preview_difference.py',
    'Development/test_release_features.py',
    'Development/test_long_paths.py',
    'Development/test_performance_support.py', 'Development/test_performance_ui.py',
]


def main():
    """Write a new versioned source ZIP and verify its contents and hashes."""
    version = re.search(r'^Version\s*=\s*(\S+)', (BASE / 'Package.ini').read_text(), re.MULTILINE).group(1)
    assert len(SOURCE_FILES) == len(set(SOURCE_FILES)), 'Duplicate source member'
    for name in SOURCE_FILES:
        if not (BASE / name).is_file():
            raise FileNotFoundError('Missing source file: ' + name)
        assert Path(name).suffix.lower() not in {'.exe', '.dll', '.cbz', '.cbr'}
        assert not name.startswith(('Reports/', 'Releases/', 'Development/Test Environment/'))
    release = BASE / 'Releases'
    release.mkdir(exist_ok=True)
    target = release / ('WebPOptimizer-' + version + '-source.zip')
    manifest_path = target.with_suffix('.manifest.json')
    if target.exists() or manifest_path.exists():
        raise FileExistsError('Source build already exists; use a new version or archive the prior draft.')
    manifest = {'version': version, 'repository': 'https://github.com/RayRayElite/comicrack-webp-optimizer', 'files': []}
    with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in SOURCE_FILES:
            data = (BASE / name).read_bytes()
            archive.writestr(name, data)
            manifest['files'].append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) == set(SOURCE_FILES)
        assert archive.testzip() is None
        for entry in manifest['files']:
            assert hashlib.sha256(archive.read(entry['path'])).hexdigest() == entry['sha256']
    manifest['archive_sha256'] = hashlib.sha256(target.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Source:', target)
    print('PASS: explicit source-only contents, CRC and hashes; personal/generated data and vendor binaries excluded')


if __name__ == '__main__':
    main()
