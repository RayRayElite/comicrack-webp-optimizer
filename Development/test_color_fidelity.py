"""Check color-profile retention and preview pixels on copied sample images."""
from pathlib import Path
import sys
import io
import uuid
from PIL import Image, ImageCms
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webp_convert_helper as helper

base = Path(__file__).resolve().parent.parent
source = base / 'Development/Test Environment/Quality Lab/20261021_085900/sample_00.jpg'
root = base / 'Development/Test Environment/Color Checks' / uuid.uuid4().hex
root.mkdir(parents=True)
with Image.open(source) as original:
    profile = original.info['icc_profile']
    assert 'Adobe RGB' in ImageCms.getProfileName(ImageCms.ImageCmsProfile(io.BytesIO(profile)))
for backend in ['ImageMagick (Recommended)', 'Pillow']:
    output = root / (backend.split()[0] + '.webp')
    if backend.startswith('ImageMagick'):
        helper.encode_with_magick(helper.find_magick_tool(), str(source), str(output), helper.quality_options('Q60'), 'No Resize', backend)
    else:
        helper.encode_with_pillow(str(source), str(output), helper.quality_options('Q60'), 'No Resize')
    with Image.open(output) as encoded:
        assert encoded.info.get('icc_profile') == profile, backend
        encoded.save(output.with_suffix('.png'), 'PNG', icc_profile=encoded.info['icc_profile'])
        expected = encoded.convert('RGB').tobytes()
    with Image.open(output.with_suffix('.png')) as displayed:
        assert displayed.info.get('icc_profile') == profile
        assert displayed.convert('RGB').tobytes() == expected
print('PASS: Adobe RGB profile survives actual Q60 ImageMagick/Pillow output and lossless PNG preview, with identical decoded WebP/PNG pixels')
