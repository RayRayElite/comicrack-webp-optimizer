"""Build a clean manual-install ZIP from an explicit runtime allowlist."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

BASE = Path(__file__).resolve().parent.parent
RUNTIME_FILES = [
    'Package.ini', 'WebPOptimizer.py', 'webp_convert_helper.py',
    'webp.png', 'webpoptimizer.png', 'quality_estimates.txt',
    'README.md', 'ADVANCED_USAGE.md', 'ARCHITECTURE.md', 'CONTRIBUTING.md',
    'CHANGELOG.md', 'requirements.txt', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
    'docs/images/guru-cleanup-workflow.png',
    'docs/images/smart-list-image-format-check.png',
    'docs/images/smart-list-image-format-errors.png',
    'docs/images/smart-list-convert-to-webp.png',
]
VENDOR_FILES = [
    'Magick/magick.exe', 'Magick/magick_License.txt',
    'Magick/msvcp140.dll', 'Magick/vcomp140.dll', 'Magick/vcruntime140.dll',
]


def main():
    version = re.search(r'^Version\s*=\s*(\S+)', (BASE / 'Package.ini').read_text(), re.MULTILINE).group(1)
    files = RUNTIME_FILES + VENDOR_FILES
    for name in files:
        if not (BASE / name).is_file():
            raise FileNotFoundError('Required release file missing: ' + name)
    release = BASE / 'Releases'
    release.mkdir(exist_ok=True)
    archive_path = release / ('WebPOptimizer-' + version + '.zip')
    manifest_path = archive_path.with_suffix('.manifest.json')
    if archive_path.exists() or manifest_path.exists():
        raise FileExistsError('Release already exists; use a new package version or move the prior build into Development.')
    manifest = {'version': version, 'install_folder': 'WebP Optimizer', 'files': []}
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in files:
            content = (BASE / name).read_bytes()
            archive.writestr('WebP Optimizer/' + name, content)
            manifest['files'].append({'path': name, 'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()})
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == {'WebP Optimizer/' + name for name in files}
        for entry in manifest['files']:
            assert hashlib.sha256(archive.read('WebP Optimizer/' + entry['path'])).hexdigest() == entry['sha256']
    manifest['archive_sha256'] = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Release:', archive_path)
    print('PASS: explicit runtime-only contents, CRC integrity and member hashes; development, reports, previews and personal settings excluded')


if __name__ == '__main__':
    main()
