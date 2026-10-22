# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""Generated long-path/Unicode stream fidelity and manifest diagnostic checks."""
from pathlib import Path
import hashlib
import subprocess
import sys
import uuid
import warnings
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webp_convert_helper as h

root = Path(__file__).parent / 'Test Environment' / 'Long Path Checks' / uuid.uuid4().hex
root.mkdir(parents=True)
long_root = root
while len(str(long_root)) < 300:
    long_root /= 'nested archive directory with a long descriptive name'
long_root.mkdir(parents=True)
source = long_root / 'page_[cover]_caf\u00e9.jpg'
short = root / 'reference.jpg'
profile = h.ImageCms.ImageCmsProfile(h.ImageCms.createProfile('sRGB')).tobytes()
image = h.Image.linear_gradient('L').resize((96, 144)).convert('RGB')
image.save(short, quality=95, icc_profile=profile)
source.write_bytes(short.read_bytes())
original = hashlib.sha256(source.read_bytes()).hexdigest()
tool = h.find_magick_tool()
assert tool
h.ENCODER_THREAD_LIMIT = 1
for quality, resize in [(60, 'No Resize'), (75, 'No Resize'), (80, 'Scale Pages To 75%')]:
    options = {'quality': quality}
    baseline = root / ('baseline-' + str(quality) + '.webp')
    command = [tool, '-limit', 'thread', '1', str(short), '+profile', 'exif', '+profile', 'xmp']
    dimensions = h.calculate_resize_dimensions(96, 144, resize)
    if dimensions:
        command += ['-resize', '%dx%d' % dimensions]
    command += ['-quality', str(quality), str(baseline)]
    run = subprocess.run(command, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    output = source.with_name('quality-' + str(quality) + '.webp')
    h.encode_with_magick(tool, str(source), str(output), options, resize, 'ImageMagick (Recommended)')
    assert output.read_bytes() == baseline.read_bytes(), 'Stream transport changed encoder bytes'
    with h.Image.open(output) as decoded:
        decoded.load()
        assert decoded.format == 'WEBP' and decoded.size == (dimensions or (96, 144))
        assert decoded.info.get('icc_profile') == profile
    try:
        h.encode_with_magick(tool, str(source), str(output), options, resize, 'ImageMagick (Recommended)')
    except FileExistsError:
        pass
    else:
        raise AssertionError('Existing staged output overwritten')
assert hashlib.sha256(source.read_bytes()).hexdigest() == original
pages = root / 'manifest'
pages.mkdir()
(pages / '001.webp').write_bytes((root / 'baseline-75.webp').read_bytes())
(pages / 'notes.txt').write_text('Preserve attachment')
archive = root / 'manifest.cbz'
h.rebuild_cbz(pages, archive)
h.validate_output(archive, '', pages)
with warnings.catch_warnings():
    warnings.simplefilter('ignore', UserWarning)
    with zipfile.ZipFile(archive, 'a') as z:
        z.writestr('001.webp', (pages / '001.webp').read_bytes())
        z.writestr('unexpected.txt', 'Unexpected member')
(pages / 'new-staging-file.txt').write_text('Simulate a staging entry appearing after rebuild')
try:
    h.validate_output(archive, '', pages)
except RuntimeError as error:
    message = str(error)
    for required in ['Missing from output (1)', 'new-staging-file.txt', 'unexpected in output (1)', 'unexpected.txt', 'duplicate members (1)', '001.webp']:
        assert required in message, message
else:
    raise AssertionError('Manifest mismatch accepted')
assert '\n' not in h.manifest_mismatch(['file\nwith newline'], [], 'Output archive')
print('PASS: >300-character Unicode/bracket paths, identical encoder bytes/ICC/dimensions, exclusive output creation, unchanged source and full manifest diagnostics')
print(root)
