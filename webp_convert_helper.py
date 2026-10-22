# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""WebP Optimizer single-archive worker (CPython 3, Pillow and external tools).

Invoked by WebPOptimizer.py; this module has no ComicRack/WinForms dependency.
It extracts into work storage, converts JPEGs, rebuilds and validates a new
archive, and emits KEY=value results. It never replaces the source archive.
Search [Hxx] markers and read ARCHITECTURE.md before changing the protocol.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import deque
import time
import threading
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import performance_support as perf

from PIL import Image, ImageCms, features


# ===========================================================================
# [H01] CLI contract and shared image policy
# ===========================================================================
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
SCRIPT_DIR = Path(__file__).resolve().parent
ENCODER_THREAD_LIMIT = None


def build_parser():
    """Define the CLI consumed by the IronPython adapter; coordinate changes with P07."""
    parser = argparse.ArgumentParser(description="WebP Optimizer conversion helper")
    parser.add_argument("--archive-path", required=True)
    parser.add_argument("--archive-tool", required=True)
    parser.add_argument("--quality-mode", required=True)
    parser.add_argument("--output-path", required=True)
    parser.add_argument("--archive-type", required=True)
    parser.add_argument("--comicinfo-path", required=False, default="")
    parser.add_argument("--comicbook-path", required=False, default="")
    parser.add_argument("--size-policy", required=False, default="Only If Smaller")
    parser.add_argument("--rar-tool", required=False, default="")
    parser.add_argument("--encoder-backend", required=False, default="ImageMagick (Recommended)")
    parser.add_argument("--work-dir", default="", help="Temporary work folder; blank uses source directory")
    parser.add_argument("--preview-dir", default="", help="Retain three JPEG/WebP page pairs for a quality trial")
    parser.add_argument("--resize-mode", required=False, default="No Resize")
    parser.add_argument("--page-workers", type=int, choices=perf.WORKERS, default=1, help="Bounded concurrent page encoders; books remain sequential")
    parser.add_argument("--resource-profile", choices=("Normal", "Background"), default="Normal")
    parser.add_argument("--metrics", action="store_true", help="Measure helper and explicitly launched child processes")
    parser.add_argument("--prefetch-next", default="", help="Optionally cache one next source during encoding")
    parser.add_argument("--prefetch-record", default="", help="Owned cache manifest from the preceding helper")
    parser.add_argument("--prefetch-budget-mb", type=int, choices=(256, 512, 1024), default=256)
    return parser


# ===========================================================================
# [H02] Quality parsing and explicit encoder discovery
# ===========================================================================
def quality_options(mode):
    """Convert Q-level/legacy labels into encoder options, not a savings percentage."""
    mode = (mode or "").strip().lower()
    if mode == "lossless":
        return {"lossless": True, "quality": 100, "method": 6}
    digits = "".join([character for character in mode if character.isdigit()])
    if digits:
        quality = max(1, min(100, int(digits)))
        return {"quality": quality, "method": 6}
    return {"quality": 75, "method": 6}


def find_tool(candidates):
    """Resolve explicit paths or PATH entries without installing dependencies."""
    for candidate in candidates:
        if not candidate:
            continue
        if os.path.isabs(candidate) and os.path.exists(candidate):
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


def find_magick_tool():
    """Prefer the bundled ImageMagick executable, then supported external locations."""
    candidates = [
        str(SCRIPT_DIR / "Magick" / "magick.exe"),
        str(SCRIPT_DIR / "ImageMagick" / "magick.exe"),
        str(SCRIPT_DIR / "Tools" / "Magick" / "magick.exe"),
        str(SCRIPT_DIR / "Tools" / "ImageMagick" / "magick.exe"),
        str(SCRIPT_DIR / "bin" / "magick.exe"),
        "magick.exe",
        "magick",
    ]
    return find_tool(candidates)


def find_cwebp_tool():
    """Locate optional standalone cwebp binaries."""
    candidates = [
        str(SCRIPT_DIR / "libwebp" / "bin" / "cwebp.exe"),
        str(SCRIPT_DIR / "Tools" / "libwebp" / "cwebp.exe"),
        str(SCRIPT_DIR / "cwebp.exe"),
        "cwebp.exe",
        "cwebp",
    ]
    return find_tool(candidates)


def resolve_encoder_backend(requested_backend):
    """Resolve exactly the selected encoder or raise; never silently fall back."""
    normalized = (requested_backend or "ImageMagick (Recommended)").strip().lower()
    if normalized in {"imagemagick (recommended)", "imagemagick", "imagemagick (cbx-style)"}:
        tool = find_magick_tool()
        if not tool:
            raise RuntimeError("Selected encoder ImageMagick is unavailable. Restore the bundled Magick/magick.exe or explicitly choose another encoder in Storage & advanced. No fallback was used.")
        return "ImageMagick (Recommended)", tool
    if normalized == "cwebp":
        tool = find_cwebp_tool()
        if not tool:
            raise RuntimeError("Selected encoder cwebp is unavailable. Install cwebp or explicitly choose ImageMagick/Pillow. No fallback was used.")
        return "cwebp", tool
    if normalized == "pillow":
        if not features.check("webp"):
            raise RuntimeError("Selected encoder Pillow has no WebP support. Install a WebP-enabled Pillow or explicitly choose another encoder. No fallback was used.")
        return "Pillow", None
    raise RuntimeError("Unsupported encoder choice: " + str(requested_backend) + ". Choose ImageMagick, cwebp or Pillow explicitly. No fallback was used.")


# ===========================================================================
# [H03] Resize math and acceptance policy
# ===========================================================================
def calculate_resize_dimensions(width, height, resize_mode):
    """Return target dimensions or None; supported policies never enlarge pages."""
    mode = (resize_mode or "No Resize").strip().lower()
    if not mode or mode == "no resize":
        return None

    digits = "".join([character for character in mode if character.isdigit()])
    if not digits:
        return None

    if "fit larger edge" in mode:
        limit = int(digits)
        largest_edge = max(width, height)
        if largest_edge <= limit:
            return None
        scale = float(limit) / float(largest_edge)
    elif "scale pages to" in mode:
        scale = float(int(digits)) / 100.0
        if scale >= 1.0:
            return None
    else:
        return None

    resized_width = max(1, int(round(width * scale)))
    resized_height = max(1, int(round(height * scale)))
    if resized_width == width and resized_height == height:
        return None
    return resized_width, resized_height


def describe_resize(original_size, resized_size, resize_mode):
    """Produce a compact report label for the applied dimensions."""
    if not resized_size or resized_size == original_size:
        return "No Resize"
    return "{0} ({1}x{2} -> {3}x{4})".format(
        resize_mode,
        original_size[0],
        original_size[1],
        resized_size[0],
        resized_size[1],
    )


def evaluate_size_policy(source_size, output_size, policy):
    """Return (keep, reason, savings_percent), allowing explicit growth policies."""
    if source_size <= 0:
        return True, "", 0.0

    normalized = (policy or "Only If Smaller").strip().lower()
    saved_bytes = source_size - output_size
    savings_percent = (saved_bytes * 100.0) / float(source_size)

    if "keep all" in normalized:
        return True, "", savings_percent
    if "allow up to 1% growth" in normalized:
        if output_size <= int(source_size * 1.01):
            return True, "", savings_percent
        return False, "Converted output grew by {0:.2f}% which exceeds the allowed 1.00% growth threshold.".format(-savings_percent), savings_percent
    if "at least 3% smaller" in normalized:
        if savings_percent >= 3.0:
            return True, "", savings_percent
        return False, "Converted output saved only {0:.2f}% which is below the required 3.00% threshold.".format(savings_percent), savings_percent
    if output_size < source_size:
        return True, "", savings_percent
    return False, "Converted output was not smaller than the source archive.", savings_percent


# ===========================================================================
# [H04] Archive extraction and page discovery
# ===========================================================================
def run_extract(archive_tool, archive_path, target_dir):
    """Extract into caller-owned work storage and return the 7-Zip exit/output tuple."""
    command = [archive_tool, "x", "-y", archive_path, f"-o{target_dir}"]
    result = perf.run_tool(command, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def walk_page_files(root_dir):
    """Return sorted supported page paths, leaving other archive members untouched."""
    page_files = []
    for current_root, _, files in os.walk(root_dir):
        for file_name in files:
            full_path = os.path.join(current_root, file_name)
            extension = Path(file_name).suffix.lower()
            if extension in IMAGE_EXTENSIONS:
                page_files.append(full_path)
    page_files.sort()
    return page_files


# ===========================================================================
# [H05] Encoder adapters and color-profile handling
# ===========================================================================
def encode_with_pillow(file_path, webp_path, options, resize_mode):
    """Encode one staged page, preserving ICC interpretation and optional dimensions."""
    with Image.open(file_path) as image:
        original_size = image.size
        resized_size = calculate_resize_dimensions(original_size[0], original_size[1], resize_mode)
        working_image = image
        if resized_size:
            working_image = image.resize(resized_size, Image.Resampling.LANCZOS)
        save_image = working_image.convert("RGB") if working_image.mode not in ("RGB", "RGBA") else working_image
        profile = image.info.get("icc_profile")
        if profile and image.mode == "CMYK":
            import io
            target_profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB"))
            save_image = ImageCms.profileToProfile(working_image, ImageCms.ImageCmsProfile(io.BytesIO(profile)), target_profile, outputMode="RGB")
            profile = target_profile.tobytes()
        pillow_options = {"method": options.get("method", 6)}
        if profile:
            pillow_options["icc_profile"] = profile
        if options.get("lossless"):
            pillow_options["lossless"] = True
            pillow_options["quality"] = options.get("quality", 100)
        else:
            pillow_options["quality"] = options.get("quality", 75)
        save_image.save(webp_path, "WEBP", **pillow_options)
        return describe_resize(original_size, resized_size, resize_mode)


def encode_with_magick(tool_path, file_path, webp_path, options, resize_mode, backend_name):
    """Run ImageMagick explicitly; retain ICC while removing EXIF/XMP metadata."""
    with Image.open(file_path) as image:
        original_size = image.size
    resized_size = calculate_resize_dimensions(original_size[0], original_size[1], resize_mode)

    # Keep ICC color interpretation; strip unrelated image metadata only.
    command = [tool_path]
    if ENCODER_THREAD_LIMIT:
        command.extend(["-limit", "thread", str(ENCODER_THREAD_LIMIT)])
    command.extend(["-", "+profile", "exif", "+profile", "xmp"])
    if resized_size:
        command.extend(["-resize", "{0}x{1}".format(resized_size[0], resized_size[1])])
    if options.get("lossless"):
        command.extend(["-quality", "100", "-define", "webp:lossless=true"])
    else:
        command.extend(["-quality", str(options.get("quality", 75))])
        # ImageMagick otherwise silently switches Q100 to lossless.
        if options.get("quality") == 100:
            command.extend(["-define", "webp:lossless=false"])
    # Pass file handles, not filenames, across the encoder boundary. Python can
    # open long Unicode/UNC paths that ImageMagick's filename API rejects.
    # Explicit WebP stdout keeps the same encoding/profile settings, without
    # buffering a whole page in Python or requiring local temporary storage.
    command.append("webp:-")
    with open(file_path, "rb") as incoming, open(webp_path, "xb") as outgoing:
        result = perf.run_tool(command, stdin=incoming, stdout=outgoing, stderr=subprocess.PIPE)
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip() or "ImageMagick failed to encode a page."
        raise RuntimeError("ImageMagick failed for " + file_path + ": " + detail)
    return describe_resize(original_size, resized_size, resize_mode)


def encode_with_cwebp(tool_path, file_path, webp_path, options, resize_mode):
    """Run the optional libwebp CLI with the chosen quality and ICC retention."""
    with Image.open(file_path) as image:
        original_size = image.size
    resized_size = calculate_resize_dimensions(original_size[0], original_size[1], resize_mode)

    command = [tool_path]
    if options.get("lossless"):
        command.extend(["-lossless", "-z", "9"])
    else:
        command.extend([
            "-q", str(options.get("quality", 75)),
            "-preset", "photo",
            "-m", "6",
            "-sns", "80",
            "-af",
            "-sharp_yuv",
            "-mt",
            "-metadata", "icc",
        ])
    if resized_size:
        command.extend(["-resize", str(resized_size[0]), str(resized_size[1]), "-resize_mode", "down_only"])
    command.extend([file_path, "-o", webp_path])
    result = perf.run_tool(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "cwebp failed to encode a page.").strip())
    return describe_resize(original_size, resized_size, resize_mode)


# ===========================================================================
# [H06] Staged-page conversion and collision checks
# ===========================================================================
def convert_pages(page_files, mode, encoder_backend, resize_mode, page_workers=1, progress=None):
    """Encode independent staged JPEGs with bounded concurrency and full validation.

    Preflight every target before starting any worker. Only temporary pages are
    modified. Executor shutdown waits for all active workers even on failure,
    so the caller can safely remove work storage after an exception.
    """
    if page_workers not in perf.WORKERS:
        raise ValueError("Page workers must be 1, 2 or 4")
    options = quality_options(mode)
    backend_name, backend_tool = resolve_encoder_backend(encoder_backend)
    sources = [p for p in page_files if Path(p).suffix.lower() in {".jpg", ".jpeg"}]
    targets = set()
    for source in sources:
        target = str(Path(source).with_suffix(".webp"))
        key = target.casefold()
        if key in targets or os.path.exists(target):
            raise RuntimeError("Page name collision: " + target)
        targets.add(key)

    completed = [0]
    progress_lock = threading.Lock()

    def encode_page(file_path):
        webp_path = str(Path(file_path).with_suffix(".webp"))
        if backend_name == "ImageMagick (Recommended)":
            applied = encode_with_magick(backend_tool, file_path, webp_path, options, resize_mode, backend_name)
        elif backend_name == "cwebp":
            applied = encode_with_cwebp(backend_tool, file_path, webp_path, options, resize_mode)
        else:
            applied = encode_with_pillow(file_path, webp_path, options, resize_mode)
        with Image.open(webp_path) as converted:
            converted.load()
            with Image.open(file_path) as original:
                expected = calculate_resize_dimensions(*original.size, resize_mode) or original.size
            if converted.format != "WEBP" or converted.size != expected:
                raise RuntimeError("Converted page format or dimensions do not match: " + webp_path)
        os.remove(file_path)
        with progress_lock:
            completed[0] += 1
            if progress:
                progress("ENCODING", completed[0], len(sources))
        return applied

    # Threads coordinate subprocesses/Pillow work; never start parallel books.
    # ImageMagick's own threads are bounded below to avoid workers x CPU threads.
    if page_workers == 1:
        applied = [encode_page(path) for path in sources]
    else:
        with ThreadPoolExecutor(max_workers=page_workers) as executor:
            applied = list(executor.map(encode_page, sources))
    resized = [value for value in applied if value != "No Resize"]
    return {"converted_count": len(sources), "resized_count": len(resized),
            "resize_summary": resized[-1] if resized else "No Resize",
            "backend_used": backend_name}


def classify_output(page_files):
    """Classify remaining staged image extensions for ComicRack custom values."""
    counts = {"jpg": 0, "jpeg": 0, "png": 0, "webp": 0}
    for file_path in page_files:
        suffix = Path(file_path).suffix.lower().lstrip(".")
        if suffix in counts:
            counts[suffix] += 1

    jpg_total = counts["jpg"] + counts["jpeg"]
    png_total = counts["png"]
    webp_total = counts["webp"]
    if webp_total > 0 and jpg_total == 0 and png_total == 0:
        return "WEBP"
    if jpg_total > 0 and png_total == 0 and webp_total == 0:
        return "JPG"
    if png_total > 0 and jpg_total == 0 and webp_total == 0:
        return "PNG"
    if jpg_total + png_total + webp_total == 0:
        return "NO_IMAGES"
    return "MIXED"


# ===========================================================================
# [H07] Archive reconstruction and metadata injection
# ===========================================================================
def rebuild_cbz(root_dir, output_path):
    """Create a new ZIP exclusively; never truncate an existing destination."""
    with zipfile.ZipFile(output_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for current_root, _, files in os.walk(root_dir):
            files.sort()
            for file_name in files:
                full_path = os.path.join(current_root, file_name)
                relative_path = os.path.relpath(full_path, root_dir)
                # WebP/JPEG/PNG are already compressed. Store image bytes directly;
                # deflate XML/text without spending CPU recompressing image data.
                compression = zipfile.ZIP_STORED if Path(file_name).suffix.lower() in IMAGE_EXTENSIONS else zipfile.ZIP_DEFLATED
                archive.write(full_path, relative_path, compress_type=compression)


def rebuild_cbr(root_dir, output_path, rar_tool):
    """Create a real RAR output using optional WinRAR, not a ZIP with a CBR suffix."""
    if not rar_tool:
        raise RuntimeError("WinRAR rar.exe was not provided for CBR rebuild.")

    relative_paths = []
    for current_root, _, files in os.walk(root_dir):
        files.sort()
        for file_name in files:
            full_path = os.path.join(current_root, file_name)
            relative_paths.append(os.path.relpath(full_path, root_dir))

    if not relative_paths:
        raise RuntimeError("No files were available to build the CBR archive.")

    if os.path.exists(output_path):
        raise FileExistsError("Refusing to overwrite existing output: " + output_path)

    command = [rar_tool, "a", "-idq", output_path] + relative_paths
    result = perf.run_tool(command, capture_output=True, text=True, cwd=root_dir)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or result.stdout or "WinRAR failed to build the CBR archive.").strip())


def rebuild_output(root_dir, output_path, rar_tool):
    """Dispatch by the requested output extension."""
    extension = Path(output_path).suffix.lower()
    if extension == ".cbr":
        rebuild_cbr(root_dir, output_path, rar_tool)
        return
    rebuild_cbz(root_dir, output_path)


def inject_comicinfo(root_dir, comicinfo_path):
    """Replace the staged ComicInfo.xml with metadata exported by ComicRack."""
    if not comicinfo_path:
        return False
    if not os.path.exists(comicinfo_path):
        return False

    target_path = os.path.join(root_dir, "ComicInfo.xml")
    if os.path.exists(target_path):
        os.remove(target_path)
    shutil.copy2(comicinfo_path, target_path)
    return True


def inject_comicbook(root_dir, comicbook_path):
    """Replace the staged ComicBook.xml with the exported library metadata."""
    if not comicbook_path:
        return False
    if not os.path.exists(comicbook_path):
        return False

    target_path = os.path.join(root_dir, "ComicBook.xml")
    if os.path.exists(target_path):
        os.remove(target_path)
    shutil.copy2(comicbook_path, target_path)
    return True


def validate_embedded_metadata(output_path, archive_tool):
    """Report metadata-file presence; this is not metadata semantic validation."""
    comicinfo_embedded = False
    comicbook_embedded = False
    extension = Path(output_path).suffix.lower()
    if extension == ".cbz":
        with zipfile.ZipFile(output_path, "r") as archive:
            names = set(archive.namelist())
            comicinfo_embedded = "ComicInfo.xml" in names
            comicbook_embedded = "ComicBook.xml" in names
        return comicinfo_embedded, comicbook_embedded

    result = perf.run_tool([archive_tool, "l", "-ba", output_path], capture_output=True, text=True)
    listing = result.stdout or ""
    comicinfo_embedded = "ComicInfo.xml" in listing
    comicbook_embedded = "ComicBook.xml" in listing
    return comicinfo_embedded, comicbook_embedded


# ===========================================================================
# [H08] Rebuilt-archive and decoded-image validation
# ===========================================================================
def manifest_mismatch(expected, actual, label):
    """Explain the exact difference without weakening manifest validation.

    JSON escapes control characters so a filename cannot inject protocol lines.
    Keep all names/counts: transient staging entries must remain diagnosable.
    """
    import json
    from collections import Counter
    expected, actual = list(expected), list(actual)
    missing = sorted(set(expected) - set(actual))
    extra = sorted(set(actual) - set(expected))
    duplicates = sorted(name for name, count in Counter(actual).items() if count > 1)
    return (label + " file manifest does not match. Expected " + str(len(expected)) + " files; found " + str(len(actual))
            + ". Missing from output (" + str(len(missing)) + "): " + json.dumps(missing, ensure_ascii=True)
            + "; unexpected in output (" + str(len(extra)) + "): " + json.dumps(extra, ensure_ascii=True)
            + "; duplicate members (" + str(len(duplicates)) + "): " + json.dumps(duplicates, ensure_ascii=True))


def validate_output(output_path, archive_tool, root_dir, workers=1):
    """Check staged/output member identity, integrity and supported image decoding.

    CBZ uses exact member hashes plus CRC checks; CBR is tested, extracted
    again and compared. Validation does not prove subjective visual quality."""
    expected = {}
    for current, _, files in os.walk(root_dir):
        for name in files:
            path = Path(current) / name
            expected[path.relative_to(root_dir).as_posix()] = path
    if Path(output_path).suffix.lower() == ".cbz":
        with zipfile.ZipFile(output_path) as archive:
            names = [entry.filename for entry in archive.infolist() if not entry.is_dir()]
            if len(names) != len(set(names)) or set(names) != set(expected):
                raise RuntimeError(manifest_mismatch(expected, names, "Output archive"))
            # One ZIP reader verifies CRCs. A bounded queue overlaps decoding/hash
            # work; at most 64 MiB of compressed buffers and `workers` tasks wait.
            # Encoding has already joined, so this reuses the same worker budget.
            import hashlib
            import io
            def verify(name, path, data):
                if hashlib.sha256(data).digest() != bytes.fromhex(perf.file_hash(path)):
                    raise RuntimeError("Output member content mismatch: " + name)
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    with Image.open(io.BytesIO(data)) as image:
                        image.load()
            pending, buffered = deque(), 0
            with ThreadPoolExecutor(max_workers=workers) as executor:
                for name, path in expected.items():
                    size = archive.getinfo(name).file_size
                    while pending and (len(pending) >= workers or buffered + size > 64 * 1048576):
                        future, used = pending.popleft()
                        future.result()
                        buffered -= used
                    data = archive.read(name)  # CRC failure still aborts validation.
                    pending.append((executor.submit(verify, name, path, data), len(data)))
                    buffered += len(data)
                for future, _ in pending:
                    future.result()

    else:
        result = perf.run_tool([archive_tool, "t", output_path], capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError("Output CBR integrity check failed.")
        with tempfile.TemporaryDirectory(prefix="webp_verify_") as verified:
            code, _, _ = run_extract(archive_tool, output_path, verified)
            if code != 0:
                raise RuntimeError("Could not verify output CBR.")
            actual = {p.relative_to(verified).as_posix(): p for p in Path(verified).rglob("*") if p.is_file()}
            if set(actual) != set(expected):
                raise RuntimeError(manifest_mismatch(expected, actual, "Output CBR"))
            for name, path in actual.items():
                if path.read_bytes() != expected[name].read_bytes():
                    raise RuntimeError("Output member content mismatch: " + name)
                if path.suffix.lower() in IMAGE_EXTENSIONS:
                    with Image.open(path) as image:
                        image.load()


# ===========================================================================
# [H09] Machine-readable results and single-archive orchestration
# ===========================================================================
def print_result(data):
    """Write KEY=value records to stdout; keep ordinary diagnostics off this channel."""
    for key, value in data.items():
        print(f"{key}={value}")


# [H10] Read-only recovery checks and generated-fixture setup diagnostics
_PROGRESS_LOCK = threading.Lock()


def emit_progress(stage, completed=0, total=0):
    """Emit bounded progress records; the adapter applies them on its UI thread."""
    with _PROGRESS_LOCK:
        print("PROGRESS=%s|%d|%d" % (stage, completed, total), flush=True)


def inspect_archive(archive_path, archive_tool, work_dir):
    """Read/test all members and decode supported images without changing input.

    Readability does not prove that an output belongs to an interrupted job or
    has the intended subjective quality. Recovery never installs it automatically.
    """
    import io
    path = Path(archive_path)
    before = path.stat()
    count = 0
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            names = [item.filename.casefold() for item in members]
            if len(names) != len(set(names)):
                raise RuntimeError("Duplicate archive member names")
            for item in members:
                data = archive.read(item)  # Verifies CRC, including non-image members.
                if Path(item.filename).suffix.lower() in IMAGE_EXTENSIONS:
                    with Image.open(io.BytesIO(data)) as image:
                        image.load()
                    count += 1
    else:
        if not archive_tool:
            raise RuntimeError("7-Zip is required to check this non-ZIP archive")
        checked = perf.run_tool([archive_tool, "t", str(path)], capture_output=True, text=True, timeout=120)
        if checked.returncode:
            raise RuntimeError("Archive integrity test failed: " + (checked.stderr or checked.stdout)[-2000:])
        with tempfile.TemporaryDirectory(prefix="recovery_check_", dir=work_dir) as expanded:
            code, _, error = run_extract(archive_tool, str(path), expanded)
            if code:
                raise RuntimeError("Recovery extraction failed: " + error[-2000:])
            for page in walk_page_files(expanded):
                with Image.open(page) as image:
                    image.load()
                count += 1
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError("Archive changed during inspection")
    if count == 0:
        raise RuntimeError("No supported image pages found")
    return count


def diagnostics_main(argv):
    """Check setup with disposable files, or inspect an existing archive read-only."""
    parser = argparse.ArgumentParser(description="WebP Optimizer diagnostics")
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--check-setup", action="store_true")
    modes.add_argument("--check-archive")
    parser.add_argument("--encoder-backend", default="ImageMagick (Recommended)")
    parser.add_argument("--archive-tool", default="")
    parser.add_argument("--rar-tool", default="")
    parser.add_argument("--require-rar", action="store_true")
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args(argv)
    root = Path(args.work_dir)
    checks = {}
    try:
        root.mkdir(parents=True, exist_ok=True)
        if args.check_archive:
            count = inspect_archive(args.check_archive, args.archive_tool, str(root))
            print_result({"STATUS": "OK", "CHECK_MESSAGE": "Readable archive; %d supported image pages. Visual quality and job identity require review." % count})
            return 0
        checks["CHECK_PYTHON"] = "OK | Python " + sys.version.split()[0]
        import PIL
        checks["CHECK_PILLOW"] = "OK | Pillow " + PIL.__version__
        if not features.check("webp"):
            raise RuntimeError("Pillow has no WebP decoding support. Install a WebP-enabled Pillow: py -3 -m pip install --upgrade Pillow")
        with tempfile.TemporaryDirectory(prefix="setup_check_", dir=root) as temporary:
            temporary = Path(temporary)
            checks["CHECK_STORAGE"] = "OK | Created temporary files in " + str(root)
            original = temporary / "probe.jpg"
            Image.new("RGB", (32, 48), (40, 80, 120)).save(original)
            # Exercise the selected encoder and decoding, not just PATH discovery.
            converted = convert_pages([str(original)], "Q80", args.encoder_backend, "No Resize")
            checks["CHECK_ENCODER"] = "OK | Encoded and decoded a test page with " + converted["backend_used"]
            sample = temporary / "probe.cbz"
            with zipfile.ZipFile(sample, "x") as archive:
                archive.write(original.with_suffix(".webp"), "probe.webp")
            if not args.archive_tool:
                raise RuntimeError("7-Zip missing. Restore ComicRack's Resources/7z.exe or 7za.exe")
            tested = perf.run_tool([args.archive_tool, "t", str(sample)], capture_output=True, text=True, timeout=30)
            if tested.returncode:
                raise RuntimeError("7-Zip could not test the generated archive")
            checks["CHECK_ARCHIVE_TOOL"] = "OK | 7-Zip tested a generated CBZ"
            if args.require_rar:
                if not args.rar_tool:
                    raise RuntimeError("WinRAR rar.exe is required for the selected CBR rebuild option")
                rar = temporary / "probe.cbr"
                # Build only a dedicated page folder, never the diagnostics folder itself.
                pages = temporary / "pages"
                pages.mkdir()
                shutil.copy2(original.with_suffix(".webp"), pages / "probe.webp")
                rebuild_cbr(pages, rar, args.rar_tool)
                inspect_archive(rar, args.archive_tool, str(temporary))
                checks["CHECK_RAR"] = "OK | WinRAR created a readable test CBR"
        print_result(dict(checks, STATUS="OK"))
        return 0
    except Exception as error:
        print_result(dict(checks, STATUS="ERROR", CHECK_MESSAGE=str(error)))
        return 1


def main():
    """Process one archive into a distinct output and emit a machine-readable result.

    Work is temporary; retained preview assets live outside it. The caller
    owns final source replacement, library updates and trial-output cleanup."""
    if "--check-setup" in sys.argv[1:] or "--check-archive" in sys.argv[1:]:
        return diagnostics_main(sys.argv[1:])
    if "--cleanup-prefetch" in sys.argv[1:]:
        parser = argparse.ArgumentParser()
        parser.add_argument("--cleanup-prefetch", required=True)
        parser.add_argument("--work-dir", required=True)
        cleanup = parser.parse_args()
        perf.cleanup_cache(cleanup.cleanup_prefetch, cleanup.work_dir)
        return 0
    global ENCODER_THREAD_LIMIT
    args = build_parser().parse_args()
    ENCODER_THREAD_LIMIT = 1 if args.page_workers > 1 else None
    started = time.perf_counter()
    timings = {}
    stage = "PREPARE"
    stage_started = started
    source_path = os.path.abspath(args.archive_path)
    output_path = os.path.abspath(args.output_path)
    if os.path.normcase(source_path) == os.path.normcase(output_path) or os.path.exists(output_path):
        print_result({"STATUS": "ERROR", "MESSAGE": "Output must be a new path distinct from the source."})
        return 1
    work_root = Path(args.work_dir).resolve() if args.work_dir else Path(source_path).parent
    work_root.mkdir(parents=True, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="webp_optimizer_", dir=work_root)
    source_size = os.path.getsize(source_path) if os.path.exists(source_path) else 0

    prefetch = None
    keep_prefetch = False
    if args.metrics:
        perf.TRACKER = perf.ResourceTracker()
    try:
        perf.set_priority(args.resource_profile)
        resolve_encoder_backend(args.encoder_backend)
        required = source_size * 4
        if zipfile.is_zipfile(source_path):
            with zipfile.ZipFile(source_path) as archive:
                required = max(required, sum(entry.file_size for entry in archive.infolist()) * 3)
        if shutil.disk_usage(work_root).free < required + 64 * 1024 * 1024:
            raise RuntimeError("Insufficient temporary working space (conservative estimate).")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(Path(output_path).parent).free < source_size * 2 + 64 * 1024 * 1024:
            raise RuntimeError("Insufficient output staging space (conservative estimate).")
        source_stat = os.stat(source_path)
        timings[stage] = time.perf_counter() - stage_started
        stage, stage_started = "EXTRACT", time.perf_counter()
        emit_progress("EXTRACTING")
        extraction_source = source_path
        if args.prefetch_record:
            extraction_source, reused = perf.cached_input(args.prefetch_record, source_path, work_root)
            print_result({"PREFETCH_USED": "Yes" if reused else "No"})
        code, _, stderr = run_extract(args.archive_tool, extraction_source, temp_dir)
        if code != 0:
            print_result({
                "STATUS": "ERROR",
                "MESSAGE": stderr.strip() or "Could not extract archive.",
                "SOURCE_SIZE": source_size,
            })
            return 1

        if args.prefetch_record:
            perf.cleanup_cache(args.prefetch_record, work_root)
            print_result({"PREFETCH_CLEANED_RECORD": args.prefetch_record})
            args.prefetch_record = ""
        # Discover pages only after extraction succeeded; preserve non-image members.
        page_files = walk_page_files(temp_dir)
        if not page_files:
            print_result({
                "STATUS": "SKIPPED",
                "MESSAGE": "No supported image pages were found in the archive.",
                "SOURCE_SIZE": source_size,
                "TOTAL_PAGES": 0,
                "CONVERTED_PAGES": 0,
            })
            return 0

        preview_pages = []
        if args.preview_dir:
            candidates = [p for p in page_files if Path(p).suffix.lower() in {".jpg", ".jpeg"}]
            if candidates:
                preview_root = Path(args.preview_dir)
                preview_root.mkdir(parents=True, exist_ok=False)
                for number, index in enumerate(sorted({0, len(candidates) // 2, max(0, len(candidates) - 4)})):
                    original = preview_root / ("page_%d.jpg" % number)
                    shutil.copyfile(candidates[index], original)
                    preview_pages.append((candidates[index], original))
        timings[stage] = time.perf_counter() - stage_started
        stage, stage_started = "ENCODE", time.perf_counter()
        emit_progress("ENCODING", 0, len([p for p in page_files if Path(p).suffix.lower() in {".jpg", ".jpeg"}]))
        if args.prefetch_next and args.work_dir and perf.local_storage(work_root):
            prefetch = perf.Prefetch(args.prefetch_next, work_root, args.prefetch_budget_mb)
        elif args.prefetch_next:
            print_result({"PREFETCH_NOTE": "Prefetch requires an explicitly chosen local fixed-drive temporary folder"})
        conversion_summary = convert_pages(page_files, args.quality_mode, args.encoder_backend, args.resize_mode, args.page_workers, emit_progress)
        timings[stage] = time.perf_counter() - stage_started
        stage, stage_started = "REBUILD", time.perf_counter()
        updated_pages = walk_page_files(temp_dir)
        if len(updated_pages) != len(page_files):
            raise RuntimeError("Page count changed during conversion.")
        inject_comicinfo(temp_dir, args.comicinfo_path)
        inject_comicbook(temp_dir, args.comicbook_path)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        emit_progress("REBUILDING")
        rebuild_output(temp_dir, output_path, args.rar_tool)
        timings[stage] = time.perf_counter() - stage_started
        stage, stage_started = "VALIDATE", time.perf_counter()
        emit_progress("VALIDATING")
        validate_output(output_path, args.archive_tool, temp_dir, args.page_workers)
        output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        keep_result, keep_message, savings_percent = evaluate_size_policy(source_size, output_size, args.size_policy)
        keep_prefetch = True
        if not keep_result:
            if os.path.exists(output_path):
                os.remove(output_path)
            print_result({
                "STATUS": "SKIPPED",
                "SOURCE_SIZE": source_size,
                "OUTPUT_SIZE": output_size,
                "SIZE_DELTA": source_size - output_size,
                "SAVINGS_PERCENT": f"{savings_percent:.2f}",
                "TOTAL_PAGES": len(updated_pages),
                "CONVERTED_PAGES": conversion_summary["converted_count"],
                "OUTPUT_IMAGE_FORMAT": classify_output(updated_pages),
                "ENCODER_BACKEND_USED": conversion_summary["backend_used"],
                "RESIZE_APPLIED": conversion_summary["resize_summary"],
                "SKIP_REASON": "SIZE_POLICY",
                "MESSAGE": keep_message,
            })
            return 0
        current_stat = os.stat(source_path)
        if (source_stat.st_size, source_stat.st_mtime_ns) != (current_stat.st_size, current_stat.st_mtime_ns):
            raise RuntimeError("Source archive changed during conversion; replacement is not permitted.")
        comicinfo_embedded, comicbook_embedded = validate_embedded_metadata(output_path, args.archive_tool)
        timings[stage] = time.perf_counter() - stage_started
        stage, stage_started = "PREVIEW", time.perf_counter()
        preview_index = ""
        if preview_pages:
            manifest = ET.Element("Preview", book=Path(source_path).name, source=source_path, quality=args.quality_mode)
            for number, (source_page, original) in enumerate(preview_pages):
                converted = original.with_suffix(".webp")
                shutil.copyfile(Path(source_page).with_suffix(".webp"), converted)
                with Image.open(converted) as preview_image:
                    preview_image.load()
                    preview_image.save(converted.with_suffix(".png"), "PNG", icc_profile=preview_image.info.get("icc_profile"))
                    width, height = preview_image.size
                ET.SubElement(manifest, "Page", id=str(number), title=Path(source_page).name, original=original.name, converted=converted.with_suffix(".png").name, width=str(width), height=str(height), originalBytes=str(original.stat().st_size), webpBytes=str(converted.stat().st_size))
            ET.ElementTree(manifest).write(str(Path(args.preview_dir) / "preview.xml"), encoding="utf-8", xml_declaration=True)
            preview_index = str(Path(args.preview_dir) / "preview.xml")
        print_result({
            "STATUS": "OK",
            "OUTPUT_PATH": output_path,
            "PREVIEW_PATH": preview_index,
            "SOURCE_SIZE": source_size,
            "OUTPUT_SIZE": output_size,
            "SIZE_DELTA": source_size - output_size,
            "SAVINGS_PERCENT": f"{savings_percent:.2f}",
            "TOTAL_PAGES": len(updated_pages),
            "CONVERTED_PAGES": conversion_summary["converted_count"],
            "OUTPUT_IMAGE_FORMAT": classify_output(updated_pages),
            "OUTPUT_ARCHIVE_TYPE": Path(output_path).suffix.lower().lstrip("."),
            "ENCODER_BACKEND_USED": conversion_summary["backend_used"],
            "RESIZE_APPLIED": conversion_summary["resize_summary"],
            "COMICINFO_EMBEDDED": "Yes" if comicinfo_embedded else "No",
            "COMICBOOK_EMBEDDED": "Yes" if comicbook_embedded else "No",
            "MESSAGE": "Created converted output with embedded ComicInfo metadata.",
        })
        return 0
    except Exception as exc:
        keep_prefetch = False
        print_result({
            "STATUS": "ERROR",
            "MESSAGE": str(exc),
            "SOURCE_SIZE": source_size,
        })
        return 1
    finally:
        timings[stage] = time.perf_counter() - stage_started
        emit_progress("CLEANUP")
        cleanup_started = time.perf_counter()
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(temp_dir):
            print_result({"CLEANUP_WARNING": "Temporary work folder could not be fully removed: " + temp_dir})
        if args.prefetch_record:
            try:
                perf.cleanup_cache(args.prefetch_record, work_root)
                print_result({"PREFETCH_CLEANED_RECORD": args.prefetch_record})
            except Exception as error:
                print_result({"CLEANUP_WARNING": "Consumed cache needs review: " + str(error)})
        if prefetch:
            try:
                record = prefetch.finish(keep_prefetch)
                print_result({"PREFETCH_NEXT_READY": "Yes" if record else "No"})
                if record:
                    print_result({"PREFETCH_RECORD": record})
                if prefetch.warning:
                    print_result({"PREFETCH_NOTE": prefetch.warning})
                elif not record:
                    print_result({"PREFETCH_NOTE": "Next cache incomplete or discarded; normal source processing will be used"})
            except Exception as error:
                print_result({"CLEANUP_WARNING": "Prefetch cleanup needs review: " + str(error)})
        if perf.TRACKER:
            print_result(perf.TRACKER.finish())
            perf.TRACKER = None
        timings["CLEANUP"] = time.perf_counter() - cleanup_started
        print_result({"TIME_" + key + "_SECONDS": f"{value:.3f}" for key, value in timings.items()})
        print_result({"TIME_TOTAL_SECONDS": f"{time.perf_counter() - started:.3f}", "PAGE_WORKERS": args.page_workers})


if __name__ == "__main__":
    sys.exit(main())
