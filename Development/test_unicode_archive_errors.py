"""Generated regressions for Unicode protocol and actionable archive failures."""
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import uuid
import zipfile
from PIL import Image
BASE = Path(__file__).resolve().parent.parent
root = BASE / "Development/Test Environment/Unicode Archive Errors" / uuid.uuid4().hex
root.mkdir(parents=True)
tool = BASE.parents[1] / "ComicRackCE_nightly/Resources/7z.exe"
page = io.BytesIO(); Image.new("RGB", (64, 96), "navy").save(page, "JPEG")
source = root / "source-\u1d57\u02b0-\u6f22.cbz"
with zipfile.ZipFile(source, "w") as z:z.writestr("page-\u6f22.jpg", page.getvalue())
work = root / 'work'; work.mkdir()
def run(source, output):
    environment = dict(os.environ, PYTHONIOENCODING="cp1252")
    command = [sys.executable, str(BASE / 'webp_convert_helper.py'), '--archive-path', str(source), '--archive-tool', str(tool),
               '--archive-type', 'cbz', '--quality-mode', 'Q75', '--size-policy', 'Keep All Results', '--output-path', str(output), '--work-dir', str(work)]
    result = subprocess.run(command, env=environment, capture_output=True, encoding='utf-8', errors='strict')
    return result, dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
before = hashlib.sha256(source.read_bytes()).hexdigest()
output = root / 'converted-\u1d57\u02b0-\u6f22.cbz'
result, fields = run(source, output)
assert result.returncode == 0 and fields['STATUS']=='OK', (result.stdout, result.stderr)
assert fields['OUTPUT_PATH']==str(output)
with zipfile.ZipFile(output) as z:assert z.namelist()==['page-\u6f22.webp'] and z.testzip() is None
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
# Broken local-header filename with valid directory entry: do not discard a page.
bad = root/'bad-header.cbz'
with zipfile.ZipFile(bad,'w') as z:z.writestr('001.jpg',page.getvalue())
raw=bytearray(bad.read_bytes());raw[30]=ord('X');bad.write_bytes(raw)
result, bad_fields=run(bad,root/'must-not-exist.cbz')
assert result.returncode==1 and bad_fields['ERROR_CODE']=='ARCHIVE_HEADERS_ERROR', (result.stdout,result.stderr)
assert 'Source archive header problem' in bad_fields['MESSAGE']
assert 'Headers Error' in bad_fields['ERROR_DETAIL']
assert not (root/'must-not-exist.cbz').exists()
# Valid mixed-image archive with output name collision: retain both originals.
collision=root/'collision.cbz'; webp=io.BytesIO();Image.new('RGB',(64,96),'navy').save(webp,'WEBP')
with zipfile.ZipFile(collision,'w') as z:
 z.writestr('001.jpg',page.getvalue());z.writestr('001.webp',webp.getvalue())
original_hash=hashlib.sha256(collision.read_bytes()).hexdigest()
result, collision_fields=run(collision,root/'collision-output.cbz')
assert result.returncode==1 and 'Page name collision' in collision_fields['MESSAGE']
assert '001.jpg' in collision_fields['MESSAGE'] and '001.webp' in collision_fields['MESSAGE']
assert hashlib.sha256(collision.read_bytes()).hexdigest()==original_hash
assert not (root/'collision-output.cbz').exists() and not list(work.iterdir())
(root/'results.json').write_text(json.dumps({'status':'PASS','unicode_source':str(source),'source_sha256':before,'headers_error':bad_fields,'collision':collision_fields},indent=2),encoding='utf-8')
print('PASS: Unicode archive/member/output paths despite cp1252 environment, complete UTF-8 protocol, header diagnostics, collision guidance, unchanged sources and cleanup')
