"""Generated cache/resource tests. Never access or replace collection originals."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import performance_support as perf

root = BASE / 'Development/Test Environment/Performance Support' / uuid.uuid4().hex
root.mkdir(parents=True)
source = root / 'original.bin'
source.write_bytes(os.urandom(2 * 1048576))
before = perf.file_hash(source)

def cache():
    job = perf.Prefetch(source, root, 256)
    job.thread.join()
    record = job.finish(True)
    assert record, job.warning
    return record

record = cache()
path, reused = perf.cached_input(record, source, root)
assert reused and perf.file_hash(path) == before
source.write_bytes(b'changed')
assert perf.cached_input(record, source, root) == (source, False)
perf.cleanup_cache(record, root)
perf.cleanup_cache(record, root)  # Idempotent only for an exact owned identity.
record = cache()
archive = Path(record).parent / 'archive.bin'
archive.write_bytes(b'corrupt')
try:
    perf.cached_input(record, source, root)
except RuntimeError as error:
    assert 'checksum' in str(error)
else:
    raise AssertionError('Corrupt cache accepted')
unrelated = Path(record).parent / 'do-not-delete.txt'
unrelated.write_text('unrelated')
try:
    perf.cleanup_cache(record, root)
except RuntimeError:
    pass
else:
    raise AssertionError('Unknown cache content deleted')
assert unrelated.exists() and archive.exists()
unrelated.unlink()
perf.cleanup_cache(record, root)
for invalid in [root / 'manifest.json', root / ('webp_prefetch_' + 'z' * 32) / 'manifest.json', root.parent / ('webp_prefetch_' + 'a' * 32) / 'manifest.json']:
    try:
        perf.cleanup_cache(invalid, root)
    except RuntimeError:
        pass
    else:
        raise AssertionError('Broad/invalid cleanup accepted')

# Budget skips and active-copy cancellation leave no incomplete cache behind.
job = perf.Prefetch(source, root, 0)
job.thread.join()
assert not job.finish(True) and job.warning
source.write_bytes(os.urandom(8 * 1048576))
job = perf.Prefetch(source, root, 256)
job.cancel.set()
assert not job.finish(False)
assert not list(root.glob('webp_prefetch_*'))

# A real child performs CPU and file I/O. Short-lived counters survive retirement.
perf.TRACKER = perf.ResourceTracker()
script = 'import sys,time; from pathlib import Path; p=Path(sys.argv[1]); p.write_bytes(bytes(8*1048576)); p.read_bytes(); end=time.perf_counter()+.4\nwhile time.perf_counter()<end: sum(range(20000))'
perf.run_tool([sys.executable, '-c', script, str(root / 'child.bin')], check=True, capture_output=True)
values = perf.TRACKER.finish()
perf.TRACKER = None
assert 0 < float(values['RESOURCE_CPU_AVG_PERCENT']) <= 100
assert float(values['RESOURCE_RAM_PEAK_MB']) > 0
assert float(values['RESOURCE_WRITE_MBPS']) > 0
assert float(values['RESOURCE_READ_MBPS']) > 0
print('PASS: resource sampling/retired child counters, cache hash/source guards, strict cleanup, budget and cancellation')

# Real helper-to-helper handoff: source identity remains the original path.
import zipfile
from PIL import Image
page = root / 'page.jpg'
Image.effect_noise((512, 768), 30).convert('RGB').save(page, quality=95)
first, second = root / 'first.cbz', root / 'second.cbz'
for target in (first, second):
    with zipfile.ZipFile(target, 'x') as archive:
        for index in range(24):
            archive.write(page, '%03d.jpg' % index)
originals = {p: perf.file_hash(p) for p in (first, second)}
tool = BASE.parent.parent / 'ComicRackCE_nightly/Resources/7z.exe'
def convert(source, output, extra):
    command = [sys.executable, str(BASE / 'webp_convert_helper.py'), '--archive-path', str(source), '--archive-tool', str(tool), '--output-path', str(output), '--archive-type', 'cbz', '--quality-mode', 'Q75', '--size-policy', 'Keep All Results', '--work-dir', str(root), '--page-workers', '4'] + extra
    done = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert done.returncode == 0, (done.stdout, done.stderr)
    values = dict(line.split('=', 1) for line in done.stdout.splitlines() if '=' in line)
    assert values['STATUS'] == 'OK' and 'CLEANUP_WARNING' not in values
    return values
values = convert(first, root / 'first-output.cbz', ['--prefetch-next', str(second)])
assert values['PREFETCH_NEXT_READY'] == 'Yes'
record = values['PREFETCH_RECORD']
values = convert(second, root / 'second-output.cbz', ['--prefetch-record', record])
assert values['PREFETCH_CLEANED_RECORD'] == record
assert values['PREFETCH_USED'] == 'Yes' and not Path(record).parent.exists()
assert all(perf.file_hash(p) == digest for p, digest in originals.items())
assert not list(root.glob('webp_prefetch_*')) and not list(root.glob('webp_optimizer_*'))
print('PASS: real two-helper cached extraction, unchanged originals, validation and complete cache/work cleanup')
print(root)
