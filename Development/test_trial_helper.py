"""Exercise actual trial-helper outputs and preview preservation on generated pages."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageCms

base = Path(__file__).resolve().parent.parent
root = base / 'Development' / 'Test Environment' / 'Trial Helper Checks' / uuid.uuid4().hex
root.mkdir(parents=True)
source = root / 'original.cbz'
profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
with zipfile.ZipFile(source, 'w') as archive:
    for index in range(5):
        page = root / ('page%d.jpg' % index)
        Image.new('RGB', (64, 96), (index * 30, 50, 100)).save(page, icc_profile=profile)
        archive.write(page, page.name)
    archive.writestr('ComicInfo.xml', '<ComicInfo><Title>Trial fixture</Title></ComicInfo>')
before = hashlib.sha256(source.read_bytes()).hexdigest()
for quality in [60, 70, 75, 80, 90]:
    output = root / ('q%d.cbz' % quality)
    previews = root / ('q%d-previews' % quality)
    command = [sys.executable, str(base / 'webp_convert_helper.py'), '--archive-path', str(source), '--archive-tool', str(base.parent.parent / 'ComicRackCE_nightly/Resources/7z.exe'), '--output-path', str(output), '--archive-type', 'cbz', '--quality-mode', 'Q%d' % quality, '--size-policy', 'Keep All Results', '--work-dir', str(root), '--preview-dir', str(previews)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0 and 'STATUS=OK' in result.stdout, (result.stdout, result.stderr)
    assert (previews / 'preview.xml').is_file()
    assert len(list(previews.glob('*.jpg'))) == 3
    assert len(list(previews.glob('*.webp'))) == 3
    assert len(list(previews.glob('*.png'))) == 3
    assert (previews / 'preview.xml').is_file()
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        assert len([n for n in archive.namelist() if n.endswith('.webp')]) == 5
        assert 'ComicInfo.xml' in archive.namelist()
        for entry in ET.parse(previews / 'preview.xml').getroot():
            name = str(Path(entry.attrib['title']).with_suffix('.webp'))
            assert archive.read(name) == (previews / Path(entry.attrib['converted']).with_suffix('.webp')).read_bytes()
    for page in previews.glob('*.webp'):
        with Image.open(page) as image:
            image.load()
            assert image.size == (64, 96)
            assert image.info.get('icc_profile') == profile
            with Image.open(page.with_suffix('.png')) as displayed:
                assert displayed.convert('RGB').tobytes() == image.convert('RGB').tobytes()
                assert displayed.info.get('icc_profile') == profile
    output.unlink()
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
assert not list(root.glob('webp_optimizer_*'))
(root / 'results.json').write_text(json.dumps({'status': 'PASS', 'original_sha256': before, 'qualities': [60, 70, 75, 80, 90], 'previews_per_quality': 3}), encoding='utf-8')
print('PASS: actual five-quality helper runs, metadata, preview pairs, archive deletion, extraction cleanup and unchanged original')
