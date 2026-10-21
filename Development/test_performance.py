"""Generated-comic benchmark plus concurrency, byte-fidelity and CRC regressions.

This is a repeatable local comparison, not a prediction for NAS collections.
All artifacts stay in Development/Test Environment; sources are never replaced.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
from unittest.mock import patch
import zipfile

from PIL import Image, ImageCms, ImageDraw

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('helper', BASE / 'webp_convert_helper.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
root = BASE / 'Development/Test Environment/Performance Checks' / uuid.uuid4().hex
root.mkdir(parents=True)
profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
source = root / 'generated.cbz'
with zipfile.ZipFile(source, 'x') as archive:
    for index in range(8):
        image = Image.linear_gradient('L').resize((1200, 1800)).convert('RGB')
        draw = ImageDraw.Draw(image)
        for panel in range(6):
            x, y = (panel % 2) * 600 + 12, (panel // 2) * 600 + 12
            draw.rectangle((x, y, x + 575, y + 575), fill=(50 + index * 20, 80 + panel * 20, 180), outline='black', width=8)
            for line in range(45):
                draw.line((x + 12, y + line * 12, x + 540, y + 200 + line * 8), fill=(line * 5, 180, 80), width=2)
            draw.ellipse((x + 50, y + 20, x + 460, y + 130), fill='white', outline='black', width=4)
            draw.text((x + 100, y + 50), 'Generated comic benchmark', fill='black')
        page = root / ('page%02d.jpg' % index)
        image.save(page, quality=95, icc_profile=profile)
        archive.write(page, page.name)
    archive.writestr('ComicInfo.xml', '<ComicInfo><Title>Benchmark</Title></ComicInfo>')
    archive.writestr('notes.txt', 'Unchanged attachment')
original_hash = hashlib.sha256(source.read_bytes()).hexdigest()
measurements = []
reference = None
for workers in (1, 2, 4):
    output = root / ('workers%d.cbz' % workers)
    command = [sys.executable, str(BASE / 'webp_convert_helper.py'),
               '--archive-path', str(source), '--archive-tool', str(BASE.parent.parent / 'ComicRackCE_nightly/Resources/7z.exe'),
               '--output-path', str(output), '--archive-type', 'cbz', '--quality-mode', 'Q80',
               '--size-policy', 'Keep All Results', '--work-dir', str(root), '--page-workers', str(workers)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    assert result.returncode == 0, (result.stdout, result.stderr)
    values = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    assert values['STATUS'] == 'OK' and values['PAGE_WORKERS'] == str(workers)
    assert all(float(values['TIME_' + key + '_SECONDS']) >= 0 for key in ['EXTRACT', 'ENCODE', 'REBUILD', 'VALIDATE', 'CLEANUP', 'TOTAL'])
    with zipfile.ZipFile(output) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
        for entry in archive.infolist():
            assert entry.compress_type == (zipfile.ZIP_STORED if entry.filename.endswith('.webp') else zipfile.ZIP_DEFLATED)
        for name, data in members.items():
            if name.endswith('.webp'):
                import io
                with Image.open(io.BytesIO(data)) as page:
                    page.load()
                    assert page.size == (1200, 1800) and page.info['icc_profile'] == profile
        if reference is None:
            reference = members
        else:
            assert members == reference, 'Concurrency changed encoded archive member bytes'
    measurements.append({'workers': workers, 'bytes': output.stat().st_size, 'timings': values})
    print('Workers %d: total %ss, encode %ss' % (workers, values['TIME_TOTAL_SECONDS'], values['TIME_ENCODE_SECONDS']), flush=True)
assert hashlib.sha256(source.read_bytes()).hexdigest() == original_hash
assert not list(root.glob('webp_optimizer_*'))

# A real failed helper must still emit timings, clean work storage and leave source intact.
broken = root / 'broken.cbz'
with zipfile.ZipFile(broken, 'x') as archive:
    archive.writestr('001.jpg', b'not an image')
broken_before = broken.read_bytes()
failed_command = list(command)
failed_command[failed_command.index('--archive-path') + 1] = str(broken)
failed_command[failed_command.index('--output-path') + 1] = str(root / 'failed-output.cbz')
failed = subprocess.run(failed_command, capture_output=True, text=True, timeout=120)
assert failed.returncode != 0 and 'STATUS=ERROR' in failed.stdout and 'TIME_TOTAL_SECONDS=' in failed.stdout
assert broken.read_bytes() == broken_before and not (root / 'failed-output.cbz').exists()
assert not list(root.glob('webp_optimizer_*'))

# Compare archive compression policies over identical encoded member bytes.
compression = []
for label, kind in [('deflate_all', zipfile.ZIP_DEFLATED), ('store_images', None)]:
    output = root / (label + '.cbz')
    started = time.perf_counter()
    with zipfile.ZipFile(output, 'x') as archive:
        for name, data in reference.items():
            archive.writestr(name, data, compress_type=kind if kind is not None else (zipfile.ZIP_STORED if name.endswith('.webp') else zipfile.ZIP_DEFLATED))
    compression.append({'policy': label, 'seconds': time.perf_counter() - started, 'bytes': output.stat().st_size})

# CRC verification must survive removal of the redundant testzip pass.
verify_root = root / 'verify'
verify_root.mkdir()
(verify_root / 'notes.txt').write_text('Original payload')
bad = root / 'bad-crc.cbz'
with zipfile.ZipFile(bad, 'x', compression=zipfile.ZIP_STORED) as archive:
    archive.write(verify_root / 'notes.txt', 'notes.txt')
data = bytearray(bad.read_bytes())
offset = data.index(b'Original payload')
data[offset] ^= 1
bad.write_bytes(data)
try:
    h.validate_output(bad, '', verify_root)
except zipfile.BadZipFile:
    pass
else:
    raise AssertionError('Corrupt CRC accepted')

# All submitted encoders must finish before work cleanup on a page failure.
failure_root = root / 'failure'
failure_root.mkdir()
paths = []
for index in range(4):
    path = failure_root / ('%d.jpg' % index)
    Image.new('RGB', (32, 48), 'white').save(path)
    paths.append(str(path))
finished = []
real_encode = h.encode_with_pillow
def fail_one(path, *args):
    try:
        if Path(path).stem == '0':
            raise RuntimeError('Injected page failure')
        time.sleep(.02)
        return real_encode(path, *args)
    finally:
        finished.append(path)
with patch.object(h, 'encode_with_pillow', side_effect=fail_one):
    try:
        h.convert_pages(paths, 'Q80', 'Pillow', 'No Resize', 4)
    except RuntimeError as error:
        assert 'Injected' in str(error)
    else:
        raise AssertionError('Worker error swallowed')
assert len(finished) == 4
with patch.object(h, 'encode_with_pillow') as encoder:
    # Existing converted target is rejected before starting even the first page.
    collision = failure_root / 'collision.jpg'
    Image.new('RGB', (32, 48), 'white').save(collision)
    collision.with_suffix('.webp').write_bytes(b'existing')
    try:
        h.convert_pages([str(collision)], 'Q80', 'Pillow', 'No Resize', 4)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Collision accepted')
    encoder.assert_not_called()
(root / 'results.json').write_text(json.dumps({'source_sha256': original_hash, 'workers': measurements, 'compression': compression}, indent=2), encoding='utf-8')
print('PASS: bounded workers, identical ICC/encoded bytes, stored images, timings, source preservation, CRC rejection and failure shutdown')
print(root)
