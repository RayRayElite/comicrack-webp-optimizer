"""Build a clean manual-install ZIP from an explicit runtime allowlist."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import zipfile

BASE = Path(__file__).resolve().parent.parent
RUNTIME_FILES = [
    'Package.ini', 'WebPOptimizer.py', 'webp_runtime_support.py',
    'webp_convert_helper.py', 'performance_support.py', 'webp_performance_ui.py', 'NativeWindows.cs', 'history_host.ps1', 'history_host.py',
    'webp.png', 'webpoptimizer.png', 'quality_estimates.txt',
    'docs/images/webp-optimizer-icon.svg',
    'README.md', 'ADVANCED_USAGE.md', 'ARCHITECTURE.md', 'CONTRIBUTING.md',
    'CHANGELOG.md', 'requirements.txt', 'LICENSE', 'THIRD_PARTY_NOTICES.md',
    'docs/images/guru-cleanup-workflow.png',
    'docs/images/smart-list-image-format-check.png',
    'docs/images/smart-list-image-format-errors.png',
    'docs/images/smart-list-convert-to-webp.png',
    'docs/images/smart-list-webp-skipped-review.png',
    'docs/images/smart-list-webp-copies-created.png',
    'docs/images/quality-test-savings-results.png',
    'docs/images/quality-comparison-q80-full-page.jpg',
    'docs/images/difference-heatmap-q80-actual-pixels.jpg',
    'docs/images/options-quality-test.png',
    'docs/images/quality-test-progress.png',
    'docs/images/options-performance-and-resume.png',
    'docs/images/run-history-dark-mode.png',
    'docs/images/options-tools-and-recovery.png',
]
MAGICK_LICENSE_FILES = [
    'Magick/magick_License.txt', 'Magick/NOTICE.txt', 'Magick/BUILD.md', 'Magick/build-info.json',
    'Magick/licenses/libjpeg-turbo-LICENSE.md', 'Magick/licenses/libjpeg-turbo-README.ijg',
    'Magick/licenses/libwebp-COPYING.txt', 'Magick/licenses/libwebp-PATENTS.txt', 'Magick/licenses/libwebp-AUTHORS.txt',
    'Magick/licenses/lcms2-LICENSE.txt', 'Magick/licenses/MinGW-w64-runtime.txt',
    'Magick/licenses/GCC-RUNTIME-EXCEPTION.txt', 'Magick/licenses/GCC-GPL-3.0.txt', 'Magick/licenses/LGPL-2.1.txt',
]
VENDOR_FILES = ['Magick/magick.exe'] + MAGICK_LICENSE_FILES


def verify_encoder():
    """Reject stale binaries/notices or unexpected non-system DLL dependencies."""
    from inspect_pe import imports
    from package_encoder import SYSTEM_DLLS
    info = json.loads((BASE / 'Magick/build-info.json').read_text(encoding='utf-8'))
    binary = BASE / 'Magick/magick.exe'
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == info['binary_sha256'], 'Encoder provenance mismatch'
    assert set(imports(binary)['dlls']) <= SYSTEM_DLLS, 'Unexpected encoder DLL dependency'
    for relative, digest in info['license_files'].items():
        assert hashlib.sha256((BASE / 'Magick' / relative).read_bytes()).hexdigest() == digest, 'Encoder license changed: ' + relative
    return info



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plugin-only', action='store_true', help='Exclude encoder executables and DLLs; install tools separately from upstream')
    args = parser.parse_args()
    version = re.search(r'^Version\s*=\s*(\S+)', (BASE / 'Package.ini').read_text(), re.MULTILINE).group(1)
    encoder = None if args.plugin_only else verify_encoder()
    files = RUNTIME_FILES + ([] if args.plugin_only else VENDOR_FILES)
    for name in files:
        if not (BASE / name).is_file():
            raise FileNotFoundError('Required release file missing: ' + name)
    release = BASE / 'Releases'
    release.mkdir(exist_ok=True)
    archive_path = release / ('WebPOptimizer-' + version + ('-plugin-only' if args.plugin_only else '') + '.zip')
    manifest_path = archive_path.with_suffix('.manifest.json')
    if archive_path.exists() or manifest_path.exists():
        raise FileExistsError('Release already exists; use a new package version or move the prior build into Development.')
    manifest = {'version': version, 'install_folder': 'WebP Optimizer',
                'profile': 'plugin-only' if args.plugin_only else 'bundled-minimal-imagemagick',
                'encoder_sha256': encoder['binary_sha256'] if encoder else None,
                'files': []}
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
