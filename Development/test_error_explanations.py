"""Explain page failures without blaming valid input; generated cases only."""
import errno
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
import uuid
import zipfile
sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("helper", BASE / "webp_convert_helper.py")
h = importlib.util.module_from_spec(spec); spec.loader.exec_module(h)
root = BASE / "Development/Test Environment/Error Explanations" / uuid.uuid4().hex
root.mkdir(parents=True)
good = root / "valid.jpg"; h.Image.new("RGB", (64, 96), "navy").save(good)
bad = root / "broken.jpg"; bad.write_bytes(bytes.fromhex("ffd8ffd9"))
# A source decode failure must name the member, retain evidence and give an action.
try:
    h.convert_pages([str(bad)], "Q75", "Pillow", "No Resize", page_root=str(root))
except h.PageProcessingError as error:
    assert error.fields["ERROR_CODE"] == "SOURCE_IMAGE_UNREADABLE"
    assert error.fields["ERROR_PAGE"] == "broken.jpg"
    assert "Source decode check" in error.fields["ERROR_DETAIL"]
    assert "restore a clean" in error.fields["ERROR_ACTION"]
    assert "Original archive was not replaced" in str(error)
else:
    raise AssertionError("Unreadable source accepted")
# Encoder-only failure must not be mislabeled as source corruption.
with patch.object(h, "encode_with_pillow", side_effect=RuntimeError("Injected encoder fault\nraw detail")):
    try:
        h.convert_pages([str(good)], "Q75", "Pillow", "No Resize")
    except h.PageProcessingError as error:
        assert error.fields["ERROR_CODE"] == "ENCODER_ERROR"
        assert "passed a decode check" in str(error)
        assert "Injected encoder fault\\nraw detail" in error.fields["ERROR_DETAIL"]
        assert "\n" not in error.fields["ERROR_DETAIL"]
    else:
        raise AssertionError("Encoder failure swallowed")
for error, expected in [(PermissionError("locked"), "FILE_ACCESS_ERROR"),
                        (OSError(errno.ENOSPC, "full"), "DISK_SPACE_ERROR"),
                        (MemoryError("memory"), "MEMORY_ERROR"),
                        (FileNotFoundError("missing"), "FILE_NOT_FOUND"),
                        (h.Image.DecompressionBombError("too big"), "IMAGE_SAFETY_LIMIT")]:
    described = h.explain_page_failure(error, str(good), "encoding source image")
    assert described.fields["ERROR_CODE"] == expected
    assert described.fields["ERROR_CODE"] != "SOURCE_IMAGE_UNREADABLE"
# Source is fine but output is broken: preserve the distinction.
def invalid_output(source, target, *args):
    Path(target).write_bytes(b"not a WebP")
    return "No Resize"
with patch.object(h, "encode_with_pillow", side_effect=invalid_output):
    try:
        h.convert_pages([str(good)], "Q75", "Pillow", "No Resize")
    except h.PageProcessingError as error:
        assert error.fields["ERROR_CODE"] == "OUTPUT_IMAGE_INVALID"
    else:
        raise AssertionError("Invalid output accepted")
good.with_suffix(".webp").unlink()
# Real worker protocol must carry the classification, raw diagnostic and page.
source = root / "broken-comic.cbz"
with zipfile.ZipFile(source, "w") as z:
    z.writestr("pages/013.jpg", bad.read_bytes())
before = hashlib.sha256(source.read_bytes()).hexdigest()
tool = BASE.parents[1] / "ComicRackCE_nightly/Resources/7z.exe"
work = root / "work"; work.mkdir()
output = root / "output.cbz"
command = [sys.executable, str(BASE / "webp_convert_helper.py"), "--archive-path", str(source),
           "--archive-tool", str(tool), "--archive-type", "cbz", "--output-path", str(output),
           "--quality-mode", "Q75", "--encoder-backend", "Pillow", "--work-dir", str(work)]
run = subprocess.run(command, capture_output=True, text=True)
fields = dict(line.split("=", 1) for line in run.stdout.splitlines() if "=" in line)
assert run.returncode == 1 and fields["STATUS"] == "ERROR", (run.stdout, run.stderr)
assert fields["ERROR_CODE"] == "SOURCE_IMAGE_UNREADABLE", fields
assert fields["ERROR_PAGE"].replace("\\", "/") == "pages/013.jpg"
assert "Source image problem" in fields["MESSAGE"]
assert fields["ERROR_DETAIL"] and fields["ERROR_ACTION"]
assert not output.exists() and not list(work.iterdir())
assert hashlib.sha256(source.read_bytes()).hexdigest() == before
(root / "results.json").write_text(json.dumps({"status": "PASS", "worker_fields": fields}, indent=2))
print("PASS: source/encoder/output/access/disk/memory/safety categories, preserved one-line diagnostics, real worker page/action protocol, unchanged source and clean failure shutdown")
