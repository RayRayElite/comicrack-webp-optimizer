"""Smoke-test the clean manual-install bundle without installing it."""
import argparse
import os
import hashlib
import re
import json
from pathlib import Path
import subprocess
import sys
import uuid
import zipfile

BASE = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--plugin-only', action='store_true')
args = parser.parse_args()
version = re.search(r'^Version\s*=\s*(\S+)', (BASE / 'Package.ini').read_text(), re.MULTILINE).group(1)
archive_path = BASE / 'Releases' / ('WebPOptimizer-' + version + ('-plugin-only' if args.plugin_only else '') + '.zip')
manifest = json.loads(archive_path.with_suffix('.manifest.json').read_text(encoding='utf-8'))
root = BASE / 'Development/Test Environment/Packaging Checks' / uuid.uuid4().hex
root.mkdir(parents=True)
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
    assert not any(Path(name).name.lower() in {'msvcp140.dll', 'vcomp140.dll', 'vcruntime140.dll'} for name in archive.namelist())
    if args.plugin_only:
        assert not any(Path(name).suffix.lower() in {'.exe', '.dll'} for name in archive.namelist())
    for name in archive.namelist():
        target = (root / name).resolve()
        assert target.is_relative_to(root.resolve()), 'Unsafe archive path'
    archive.extractall(root)
assert hashlib.sha256(archive_path.read_bytes()).hexdigest() == manifest['archive_sha256']
plugin = root / 'WebP Optimizer'
fixtures = BASE / 'Development/Test Environment/Trial Helper Checks'
source = next(folder / 'original.cbz' for folder in fixtures.iterdir() if (folder / 'results.json').is_file())
before = hashlib.sha256(source.read_bytes()).hexdigest()
command = [sys.executable, str(plugin / 'webp_convert_helper.py'), '--archive-path', str(source), '--archive-tool', str(BASE.parent.parent / 'ComicRackCE_nightly/Resources/7z.exe'), '--output-path', str(root / 'converted.cbz'), '--archive-type', 'cbz', '--quality-mode', 'Q80', '--size-policy', 'Keep All Results', '--work-dir', str(root)]
environment = os.environ.copy()
environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
if args.plugin_only:
    # Simulate an explicitly installed external encoder without copying its
    # binaries into the package. This is not a fresh-Windows installation test.
    environment['PATH'] = str(BASE / 'Magick') + os.pathsep + environment.get('PATH', '')
result = subprocess.run(command, capture_output=True, text=True, timeout=120, env=environment)
assert result.returncode == 0 and 'STATUS=OK' in result.stdout, (result.stdout, result.stderr)
assert 'ENCODER_BACKEND_USED=ImageMagick (Recommended)' in result.stdout
if not args.plugin_only:
    from inspect_pe import imports
    from package_encoder import SYSTEM_DLLS
    assert set(imports(plugin / 'Magick/magick.exe')['dlls']) <= SYSTEM_DLLS
    info = json.loads((plugin / 'Magick/build-info.json').read_text())
    assert hashlib.sha256((plugin / 'Magick/magick.exe').read_bytes()).hexdigest() == info['binary_sha256']
    for relative, digest in info['license_files'].items():
        assert hashlib.sha256((plugin / 'Magick' / relative).read_bytes()).hexdigest() == digest
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
with zipfile.ZipFile(root / 'converted.cbz') as output:
    assert output.testzip() is None
(root / 'results.json').write_text(json.dumps({'status': 'PASS', 'archive_sha256': manifest['archive_sha256'], 'helper_output': result.stdout}, indent=2), encoding='utf-8')
print('PASS: clean package extracted, ' + ('external' if args.plugin_only else 'bundled') + ' ImageMagick used, generated comic converted and validated; no installed plugin or original comic changed')
