"""Generated regressions for archived read-only flags and AppleDouble attachments.
Never opens production comics or retained failure folders.
"""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import uuid
import zipfile
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("helper", BASE / "webp_convert_helper.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
root = BASE / "Development/Test Environment/Archive Edge Cases" / uuid.uuid4().hex
root.mkdir(parents=True)
tool = BASE.parents[1] / "ComicRackCE_nightly/Resources/7z.exe"
assert tool.is_file()
image = io.BytesIO(); h.Image.new("RGB", (192, 288), "navy").save(image, "JPEG")
sidecar = bytes.fromhex("0005160700020000") + b"generated AppleDouble metadata"
source = root / "readonly-with-sidecar.cbz"
with zipfile.ZipFile(source, "w") as z:
    for name, data in [("001.jpg", image.getvalue()), ("002.jpg", image.getvalue()),
                       ("ComicInfo.xml", b"<ComicInfo><Title>Old</Title></ComicInfo>"),
                       ("note.txt", b"Keep this attachment"),
                       ("__MACOSX/._001.jpg", sidecar), ("__MACOSX/._other.png", sidecar)]:
        entry = zipfile.ZipInfo(name, (2025, 1, 1, 12, 0, 0)); entry.create_system = 0; entry.external_attr = 0x21
        z.writestr(entry, data)
# Prove this fixture really reproduces archived DOS read-only attributes.
raw_extract = root / "raw-readonly-extraction"; raw_extract.mkdir()
extraction = subprocess.run([str(tool), "x", "-y", str(source), "-o" + str(raw_extract)], capture_output=True, text=True)
assert extraction.returncode == 0, extraction.stderr
assert (raw_extract / "001.jpg").stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
h.prepare_extracted_storage(str(raw_extract))
assert not ((raw_extract / "001.jpg").stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY)
h.cleanup_temporary_storage(str(raw_extract))
os.chmod(source, stat.S_IREAD)
before = hashlib.sha256(source.read_bytes()).hexdigest()
metadata = root / "metadata.xml"; metadata.write_text("<ComicInfo><Title>Injected</Title></ComicInfo>")
assert h.inspect_archive(str(source), str(tool), str(root)) == 2
for workers in [1, 12]:
    output = root / ("output-%d.cbz" % workers)
    work = root / ("work-%d" % workers); work.mkdir()
    preview = root / ("preview-%d" % workers)
    command = [sys.executable, str(BASE / "webp_convert_helper.py"), "--archive-path", str(source),
               "--archive-tool", str(tool), "--archive-type", "cbz", "--output-path", str(output),
               "--quality-mode", "Q75", "--size-policy", "Keep All Results", "--work-dir", str(work),
               "--comicinfo-path", str(metadata), "--page-workers", str(workers), "--preview-dir", str(preview)]
    run = subprocess.run(command, capture_output=True, text=True)
    assert run.returncode == 0 and "STATUS=OK" in run.stdout, (run.stdout, run.stderr)
    assert "TOTAL_PAGES=2" in run.stdout and "CONVERTED_PAGES=2" in run.stdout
    assert "CLEANUP_WARNING" not in run.stdout and not list(work.iterdir())
    assert len(list(preview.glob("page_*.jpg"))) == 2
    with zipfile.ZipFile(output) as z:
        assert z.testzip() is None
        assert {"001.webp", "002.webp", "ComicInfo.xml", "note.txt", "__MACOSX/._001.jpg", "__MACOSX/._other.png"} == set(z.namelist())
        assert z.read("__MACOSX/._001.jpg") == sidecar and z.read("__MACOSX/._other.png") == sidecar
        assert z.read("note.txt") == b"Keep this attachment"
        assert b"Injected" in z.read("ComicInfo.xml")
    assert h.inspect_archive(str(output), str(tool), str(root)) == 2
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert source.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
# Reconstruct expected staging and prove attachment hashes/CRCs still matter.
staged = root / "staged"; staged.mkdir()
assert h.run_extract(str(tool), str(root / "output-1.cbz"), str(staged))[0] == 0
changed = root / "tampered.cbz"
with zipfile.ZipFile(root / "output-1.cbz") as original, zipfile.ZipFile(changed, "w") as z:
    for name in original.namelist():
        z.writestr(name, b"changed" if name == "__MACOSX/._001.jpg" else original.read(name))
try:
    h.validate_output(str(changed), str(tool), str(staged))
except RuntimeError as ex:
    assert "content mismatch" in str(ex)
else:
    raise AssertionError("Metadata attachment hash mismatch ignored")
corrupt = root / "crc-error.cbz"
raw = bytearray((root / "output-1.cbz").read_bytes())
with zipfile.ZipFile(root / "output-1.cbz") as z:
    info = z.getinfo("__MACOSX/._001.jpg")
    off = info.header_offset
    name_len, extra_len = struct.unpack_from("<HH", raw, off + 26)
    raw[off + 30 + name_len + extra_len] ^= 1
corrupt.write_bytes(raw)
try:
    h.inspect_archive(str(corrupt), str(tool), str(root))
except zipfile.BadZipFile:
    pass
else:
    raise AssertionError("Metadata CRC failure ignored")
# A genuine corrupt page must still fail; a root-level ._ filename is not skipped.
for name in ["003.jpg", "._legitimate.jpg"]:
    bad = root / "bad"; bad.mkdir(exist_ok=True)
    (bad / name).write_bytes(b"not an image")
    assert str(bad / name) in h.walk_page_files(bad)
    try:
        h.convert_pages(h.walk_page_files(bad), "Q75", "Pillow", "No Resize")
    except Exception:
        pass
    else:
        raise AssertionError("Corrupt page silently skipped")
    (bad / name).unlink()
# Cleanup handles a new readonly work file without granting permissions outside.
owned = root / "readonly-cleanup"; owned.mkdir(); page = owned / "read-only.txt"
page.write_bytes(b"temporary"); os.chmod(page, stat.S_IREAD)
h.cleanup_temporary_storage(str(owned)); assert not owned.exists()
outside = root / "outside.txt"; outside.write_bytes(b"must not change"); os.chmod(outside, stat.S_IREAD)
try:
    h._clear_temporary_readonly(str(outside), str(staged))
except RuntimeError:
    pass
else:
    raise AssertionError("Outside-root permission change allowed")
assert outside.stat().st_file_attributes & stat.FILE_ATTRIBUTE_READONLY
os.chmod(outside, stat.S_IWRITE)
(root / "results.json").write_text(json.dumps({"status": "PASS", "source_sha256": before, "workers": [1, 12]}, indent=2))
print("PASS: read-only JPEG/XML/attachments, 1/12-worker conversion/previews, unchanged sources, preserved AppleDouble hashes/CRCs, strict corrupt-image rejection and scoped read-only cleanup")
