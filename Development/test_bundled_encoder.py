"""Check a staged encoder without installing it or touching collection files.

Use --tool for the candidate and optionally --reference-tool for the previous
encoder. Source/output hashes and pixel comparisons are recorded under the
development test folder; differing legacy output is evidence to review.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid
import zipfile

from PIL import Image, ImageCms, ImageDraw, ImageChops, ImageStat

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import webp_convert_helper as helper
from inspect_pe import imports

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--tool', type=Path, default=BASE / 'Magick/magick.exe')
parser.add_argument('--reference-tool', type=Path)
args = parser.parse_args()
root = BASE / 'Development/Test Environment/Bundled Encoder' / uuid.uuid4().hex
root.mkdir(parents=True)
tool = args.tool.resolve()
dependencies = imports(tool)
allowed = {'advapi32.dll', 'bcrypt.dll', 'gdi32.dll', 'kernel32.dll', 'msvcrt.dll', 'ole32.dll', 'shell32.dll', 'user32.dll', 'ws2_32.dll', 'ntdll.dll', 'comdlg32.dll', 'urlmon.dll'}
assert set(dependencies['dlls']) <= allowed, dependencies
environment = os.environ.copy()
environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
version = subprocess.run([str(tool), '-version'], capture_output=True, text=True, check=True, env=environment).stdout
assert 'jpeg' in version and 'webp' in version and 'lcms' in version
assert 'OpenMP' not in version and 'Zero-configuration' in version
sources = []
profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
image = Image.linear_gradient('L').resize((1200, 1800)).convert('RGB')
draw = ImageDraw.Draw(image)
for index in range(24):
    y = index * 70
    draw.rectangle((25, y, 1175, y + 55), fill=(index * 10, 180, 70), outline='black', width=3)
for name, mode, icc in [('rgb', 'RGB', profile), ('gray', 'L', None), ('cmyk', 'CMYK', None)]:
    path = root / (name + '.jpg')
    image.convert(mode).save(path, quality=95, icc_profile=icc)
    sources.append(path)
# Include the existing private Adobe RGB sample when present, without exporting it.
adobe = BASE / 'Development/Test Environment/Quality Lab/20261021_085900/sample_00.jpg'
if adobe.exists():
    target = root / 'adobe.jpg'
    shutil.copyfile(adobe, target)
    sources.append(target)
source_hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
comparisons = []
for source in sources:
    with Image.open(source) as original:
        size, icc = original.size, original.info.get('icc_profile')
    for quality, resize in [('Q60', 'No Resize'), ('Q75', 'No Resize'), ('Q80', 'No Resize'), ('Q90', 'No Resize'), ('Q80', 'Scale Pages To 50%')]:
        label = source.stem + '-' + quality + ('-resize' if resize != 'No Resize' else '')
        output = root / (label + '.webp')
        helper.encode_with_magick(str(tool), str(source), str(output), helper.quality_options(quality), resize, 'ImageMagick (Recommended)')
        with Image.open(output) as encoded:
            encoded.load()
            expected = helper.calculate_resize_dimensions(*size, resize) or size
            assert encoded.size == expected and encoded.info.get('icc_profile') == icc
            pixels = encoded.convert('RGB')
        row = {'sample': label, 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}
        if args.reference_tool:
            reference = root / (label + '-reference.webp')
            helper.encode_with_magick(str(args.reference_tool.resolve()), str(source), str(reference), helper.quality_options(quality), resize, 'ImageMagick (Recommended)')
            with Image.open(reference) as legacy:
                legacy.load()
                diff = ImageChops.difference(pixels, legacy.convert('RGB'))
                row.update(bytes_identical=output.read_bytes() == reference.read_bytes(),
                           pixels_identical=diff.getbbox() is None,
                           maximum_channel_difference=max(high for low, high in diff.getextrema()),
                           rms_difference=ImageStat.Stat(diff).rms)
        comparisons.append(row)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest() == digest for p, digest in source_hashes.items())

# Run the real helper with only this staged encoder and its static dependencies.
stage = root / 'stage'
(stage / 'Magick').mkdir(parents=True)
shutil.copyfile(tool, stage / 'Magick/magick.exe')
for name in ['webp_convert_helper.py', 'performance_support.py']:
    shutil.copyfile(BASE / name, stage / name)
archive = root / 'original.cbz'
with zipfile.ZipFile(archive, 'x') as out:
    for index, path in enumerate(sources):
        out.write(path, '%03d.jpg' % index)
    out.writestr('ComicInfo.xml', '<ComicInfo><Title>Generated bundle test</Title></ComicInfo>')
    out.writestr('notes.txt', 'Unchanged attachment')
original_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
reference_members = None
trials = []
for workers in (1, 4, 12):
    output = root / ('archive-workers-%d.cbz' % workers)
    command = [sys.executable, str(stage / 'webp_convert_helper.py'), '--archive-path', str(archive), '--archive-tool', str(BASE.parent.parent / 'ComicRackCE_nightly/Resources/7z.exe'), '--quality-mode', 'Q75', '--output-path', str(output), '--archive-type', 'cbz', '--size-policy', 'Keep All Results', '--work-dir', str(root), '--page-workers', str(workers)]
    done = subprocess.run(command, capture_output=True, text=True, env=environment, timeout=180)
    assert done.returncode == 0 and 'STATUS=OK' in done.stdout, (done.stdout, done.stderr)
    assert 'CLEANUP_WARNING' not in done.stdout
    trials.append(done.stdout)
    with zipfile.ZipFile(output) as encoded:
        assert encoded.testzip() is None
        members = {name: encoded.read(name) for name in encoded.namelist()}
        assert members['notes.txt'] == b'Unchanged attachment'
        assert reference_members is None or members == reference_members
        reference_members = members
assert hashlib.sha256(archive.read_bytes()).hexdigest() == original_hash
assert not list(root.glob('webp_optimizer_*'))
(root / 'results.json').write_text(json.dumps({'dependencies': dependencies, 'version': version, 'comparisons': comparisons, 'helper_trials': trials}, indent=2), encoding='utf-8')
print('PASS: system-DLL-only candidate, RGB/gray/CMYK/available Adobe RGB, Q60-Q90, resize, ICC, real helper workers 1/4/12, metadata/attachments and unchanged sources')
if args.reference_tool:
    print('Legacy comparisons:', sum(r['bytes_identical'] for r in comparisons), 'of', len(comparisons), 'byte-identical;', sum(r['pixels_identical'] for r in comparisons), 'pixel-identical')
print(root)
