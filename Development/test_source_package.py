"""Review the GitHub export without installing it or touching any comic files."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

sys.dont_write_bytecode = True
from build_source import SOURCE_FILES

base = Path(__file__).resolve().parent.parent
version = re.search(r'^Version\s*=\s*(\S+)', (base / 'Package.ini').read_text(), re.MULTILINE).group(1)
target = base / 'Releases' / ('WebPOptimizer-' + version + '-source.zip')
manifest = json.loads(target.with_suffix('.manifest.json').read_text(encoding='utf-8'))
assert hashlib.sha256(target.read_bytes()).hexdigest() == manifest['archive_sha256']
with zipfile.ZipFile(target) as archive:
    assert archive.testzip() is None
    assert len(archive.namelist()) == len(set(archive.namelist()))
    assert set(archive.namelist()) == set(SOURCE_FILES)
    for name in archive.namelist():
        assert not name.startswith(('Reports/', 'Releases/', 'Development/Test Environment/', 'Development/Release Prep/', 'Development/Build Archives/'))
        assert Path(name).suffix.lower() not in {'.exe', '.dll', '.cbz', '.cbr'}
        assert name != 'settings.xml'
    assert b'Copyright (c) 2026 RayRayElite' in archive.read('LICENSE')
    assert b'RayRayElite/comicrack-webp-optimizer' in archive.read('README.md')
    assert b'RayRayElite' in archive.read('Package.ini')
    assert 'Magick/magick_License.txt' in archive.namelist()
    assert '.github/ISSUE_TEMPLATE/bug_report.md' in archive.namelist()
    assert '.github/PULL_REQUEST_TEMPLATE.md' in archive.namelist()
    for entry in manifest['files']:
        assert hashlib.sha256(archive.read(entry['path'])).hexdigest() == entry['sha256']
print('PASS: source export author/license/version, exact allowlist, CRC/hashes, contribution templates and exclusion of comics/personal data/vendor binaries')
