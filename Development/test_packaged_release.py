"""Smoke-test the clean manual-install bundle without installing it."""
import hashlib
import re
import json
from pathlib import Path
import subprocess
import sys
import uuid
import zipfile

BASE = Path(__file__).resolve().parent.parent
version = re.search(r'^Version\s*=\s*(\S+)', (BASE / 'Package.ini').read_text(), re.MULTILINE).group(1)
archive_path = BASE / 'Releases' / ('WebPOptimizer-' + version + '.zip')
manifest = json.loads(archive_path.with_suffix('.manifest.json').read_text(encoding='utf-8'))
root = BASE / 'Development/Test Environment/Packaging Checks' / uuid.uuid4().hex
root.mkdir(parents=True)
with zipfile.ZipFile(archive_path) as archive:
    assert archive.testzip() is None
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
result = subprocess.run(command, capture_output=True, text=True, timeout=120)
assert result.returncode == 0 and 'STATUS=OK' in result.stdout, (result.stdout, result.stderr)
assert 'ENCODER_BACKEND_USED=ImageMagick (Recommended)' in result.stdout
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
with zipfile.ZipFile(root / 'converted.cbz') as output:
    assert output.testzip() is None
(root / 'results.json').write_text(json.dumps({'status': 'PASS', 'archive_sha256': manifest['archive_sha256'], 'helper_output': result.stdout}, indent=2), encoding='utf-8')
print('PASS: clean release extracted, bundled ImageMagick used, generated comic converted and validated; no installed plugin or original comic changed')
