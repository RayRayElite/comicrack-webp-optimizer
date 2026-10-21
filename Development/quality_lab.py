"""Build a local, rateable quality comparison. Never changes source archives."""
import argparse
import json
from pathlib import Path
import sys
import statistics
import time
import zipfile
from PIL import Image
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import webp_convert_helper as helper

BASE = Path(__file__).resolve().parent.parent
LEVELS = [60, 65, 70, 75, 80, 85, 90, 95, 100, 'Lossless']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--books', type=int, default=3)
    args = parser.parse_args()
    sources = sorted((BASE / 'Development' / 'Test Environment' / 'Original Test Comics').rglob('*.cbz'))[:args.books]
    if not sources or args.books < 1:
        raise SystemExit('No sample books selected')
    output = BASE / 'Development' / 'Test Environment' / 'Quality Lab' / time.strftime('%Y%m%d_%H%M%S')
    output.mkdir(parents=True)
    backend, tool = helper.resolve_encoder_backend('ImageMagick (Recommended)')
    data = {'encoder': backend, 'resize': 'No Resize', 'levels': LEVELS, 'pages': [], 'summary': {}}
    for book, source in enumerate(sources):
        with zipfile.ZipFile(source) as archive:
            names = sorted(n for n in archive.namelist() if Path(n).suffix.lower() in ('.jpg', '.jpeg'))
            # Cover, interior and late interior; avoid selecting only advertising back covers.
            indices = sorted(set((0, len(names) // 2, max(0, len(names) - 4)))) if names else []
            for index in indices:
                number = len(data['pages'])
                original = output / ('sample_%02d.jpg' % number)
                original.write_bytes(archive.read(names[index]))
                with Image.open(original) as image:
                    dimensions = image.size
                page = {'id': number, 'book': source.name, 'page': names[index], 'original': original.name,
                        'original_bytes': original.stat().st_size, 'width': dimensions[0], 'height': dimensions[1], 'variants': {}}
                for level in LEVELS:
                    path = output / ('sample_%02d_q%s.webp' % (number, level))
                    options = helper.quality_options('Q%s' % level if isinstance(level, int) else level)
                    if backend.startswith('ImageMagick'):
                        helper.encode_with_magick(tool, str(original), str(path), options, 'No Resize', backend)
                    elif backend == 'cwebp':
                        helper.encode_with_cwebp(tool, str(original), str(path), options, 'No Resize')
                    else:
                        helper.encode_with_pillow(str(original), str(path), options, 'No Resize')
                    with Image.open(path) as encoded:
                        encoded.load()
                        assert encoded.size == dimensions
                    page['variants'][str(level)] = {'file': path.name, 'bytes': path.stat().st_size,
                        'saved_percent': round(100 * (1 - path.stat().st_size / original.stat().st_size), 2)}
                data['pages'].append(page)
                print('Encoded', number + 1, source.name, names[index], flush=True)
    for level in LEVELS:
        values = [p['variants'][str(level)]['saved_percent'] for p in data['pages']]
        before = sum(p['original_bytes'] for p in data['pages'])
        after = sum(p['variants'][str(level)]['bytes'] for p in data['pages'])
        data['summary'][str(level)] = {'saved_percent': round(100 * (1 - after / before), 2),
                                     'min': min(values), 'max': max(values), 'median': statistics.median(values)}
    (output / 'measurements.json').write_text(json.dumps(data, indent=2), encoding='utf-8')
    template = (BASE / 'Development' / 'quality_lab.html').read_text(encoding='utf-8')
    (output / 'index.html').write_text(template.replace('/*DATA*/{}', json.dumps(data).replace('<', '\\u003c')), encoding='utf-8')
    # A compact, local measurement table consumed by the ComicRack options dialog.
    lines = ['# Sample JPEG page savings; %s; No Resize; %d pages from %d books. Not a whole-book prediction.' % (backend, len(data['pages']), len(sources))]
    for level in LEVELS:
        entry = data['summary'][str(level)]
        lines.append('%s|%.1f|%.1f|%.1f' % (level, entry['saved_percent'], entry['min'], entry['max']))
    (BASE / 'quality_estimates.txt').write_text('\n'.join(lines), encoding='utf-8')
    print('Quality lab:', output / 'index.html', flush=True)


if __name__ == '__main__':
    main()
