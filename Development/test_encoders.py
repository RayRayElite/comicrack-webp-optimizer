"""Explicit encoder selection checks; writes tiny generated images only."""
from pathlib import Path
import sys
from unittest.mock import patch
import uuid
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webp_convert_helper as h

assert h.build_parser().get_default('encoder_backend') == 'ImageMagick (Recommended)'
with patch.object(h, 'find_magick_tool', return_value=None), patch.object(h, 'find_cwebp_tool', return_value='available-cwebp'):
    try:
        h.resolve_encoder_backend('ImageMagick (Recommended)')
    except RuntimeError as error:
        assert 'No fallback' in str(error)
    else:
        raise AssertionError('Silently fell back from missing ImageMagick')
with patch.object(h, 'find_cwebp_tool', return_value=None):
    try:
        h.resolve_encoder_backend('cwebp')
    except RuntimeError as error:
        assert 'No fallback' in str(error)
    else:
        raise AssertionError('Silently fell back from missing cwebp')
with patch.object(h.features, 'check', return_value=False):
    try:
        h.resolve_encoder_backend('Pillow')
    except RuntimeError:
        pass
    else:
        raise AssertionError('Accepted Pillow without WebP')
for name in ['Auto (Prefer ImageMagick / CBX-style)', 'ImageMagick (Tuned)', 'Typo']:
    try:
        h.resolve_encoder_backend(name)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Accepted removed or unknown encoder: ' + name)
folder = Path(__file__).resolve().parent / 'Test Environment' / 'Encoder Checks' / uuid.uuid4().hex
folder.mkdir(parents=True)
for backend in ['ImageMagick (Recommended)', 'Pillow']:
    original = folder / (backend.split()[0] + '.jpg')
    h.Image.new('RGB', (32, 48), 'white').save(original)
    result = h.convert_pages([str(original)], 'Q80', backend, 'No Resize')
    assert result['backend_used'] == backend
    with h.Image.open(original.with_suffix('.webp')) as image:
        image.load()
        assert image.size == (32, 48) and image.format == 'WEBP'
print('PASS: explicit defaults, missing tools, no fallback, removed choices, and real ImageMagick/Pillow conversions')
