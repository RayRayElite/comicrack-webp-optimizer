# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""WebP Optimizer native adapter (ComicRack IronPython / Python 2 syntax).

ComicRack discovers the #@ hook blocks at the bottom of this file. This module
owns selection, WinForms UI, library metadata, reports and source replacement.
Image/archive processing lives in webp_convert_helper.py under CPython 3.
Search the stable [Pxx] section markers; see ARCHITECTURE.md and CONTRIBUTING.md.
Do not import Pillow or Python-3-only syntax here.
"""

import clr

clr.AddReference("System")
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")
clr.AddReference("System.Xml")

import System
from System import DateTime, Environment
from System.Diagnostics import Process, ProcessStartInfo, Stopwatch
from System.Drawing import Color, Font, FontStyle, Point, Size, Bitmap, Image as DrawingImage
from System.IO import Directory, File, FileInfo, Path, SearchOption, FileAttributes, StreamReader
from System.Security import SecurityElement
from System.Text import Encoding, StringBuilder
from System.Xml import XmlDocument
from System.Windows.Forms import AnchorStyles, Application, Button, CheckBox, Clipboard, ComboBox, DialogResult, Form, FormBorderStyle, FormStartPosition, FolderBrowserDialog, Label, ListView, ListViewItem, MessageBox, MessageBoxButtons, MessageBoxIcon, ProgressBar, TextBox, View, Panel, TabControl, TabPage, DockStyle, AutoScaleMode, Timer, SplitContainer, PictureBox, PictureBoxSizeMode, FormWindowState, Keys, Control, ControlStyles, RichTextBox, RichTextBoxScrollBars


# ===========================================================================
# [P01] Runtime paths and public option values
# ===========================================================================
SCRIPT_DIR = FileInfo(__file__).DirectoryName
ROOT_DIR = Directory.GetParent(SCRIPT_DIR).Parent.FullName
REPORT_DIR = Path.Combine(SCRIPT_DIR, "Reports")
HELPER_SCRIPT = Path.Combine(SCRIPT_DIR, "webp_convert_helper.py")
SETTINGS_PATH = Path.Combine(SCRIPT_DIR, "settings.xml")
IMAGE_FORMAT_KEY = "ImageFormat"
ARCHIVE_TYPE_KEY = "ArchiveContainer"
IMAGE_EXTENSIONS = set([".jpg", ".jpeg", ".png", ".webp"])
RUN_MODE_VALUES = ["Analyze Only", "Create WebP Copies", "Replace Originals", "Test savings & quality"]
QUALITY_MODE_VALUES = ["Q80 - Balanced (Recommended)", "Q75 - Space Saver", "Q70 - High Efficiency", "Q60", "Q65", "Q85", "Q90"]

ENCODER_BACKEND_VALUES = ["ImageMagick (Recommended)", "cwebp", "Pillow"]
RESIZE_MODE_VALUES = ["No Resize", "Fit Larger Edge To 2560px", "Fit Larger Edge To 1920px", "Fit Larger Edge To 1600px", "Scale Pages To 75%", "Scale Pages To 66%", "Scale Pages To 50%"]
CBR_MODE_VALUES = ["Convert CBR sources to CBZ output", "Keep original CBR files (skip conversion)", "Rebuild CBR sources as CBR output (requires WinRAR)"]
SIZE_POLICY_VALUES = ["Only If Smaller", "At Least 3% Smaller", "Allow Up To 1% Growth", "Keep All Results"]
TRIAL_QUALITY_LEVELS = ["Q60", "Q70", "Q75", "Q80", "Q90"]
BENCHMARK_SAMPLE_LIMIT = 3
CHECKPOINT_POLICY_VERSION = "jpeg-webp-1"
_RUN_ACTIVE = False


# ===========================================================================
# [P02] Text, XML and presentation utilities
# ===========================================================================
def _safe_unicode(value):
    """Normalize CLR/Python values to IronPython Unicode without failing the UI."""
    if value is None:
        return u""
    try:
        return unicode(value)
    except Exception:
        try:
            return unicode(str(value), "utf-8", "ignore")
        except Exception:
            return u""


def _ensure_directory(path):
    """Create a runtime directory on demand; callers choose its scope."""
    if not Directory.Exists(path):
        Directory.CreateDirectory(path)


def _write_text_file(path, content):
    """Write a UTF-8 text artifact using the .NET filesystem API."""
    File.WriteAllText(path, _safe_unicode(content), Encoding.UTF8)


def _escape_xml(value):
    """Escape a value with the CLR XML utility, treating None as empty."""
    escaped = SecurityElement.Escape(_safe_unicode(value))
    return escaped or u""


def _escape_xml_text(value):
    """Escape XML element text; attribute escaping is handled separately."""
    text = _safe_unicode(value)
    text = text.replace(u"&", u"&amp;")
    text = text.replace(u"<", u"&lt;")
    text = text.replace(u">", u"&gt;")
    return text


def _escape_xml_attribute(value):
    """Escape a value for a double-quoted XML attribute."""
    text = _escape_xml_text(value)
    text = text.replace(u'"', u"&quot;")
    text = text.replace(u"'", u"&apos;")
    return text


def _quote_argument(value):
    """Quote one argument for ProcessStartInfo.Arguments, not for a shell."""
    return '"{0}"'.format(_safe_unicode(value).replace('"', '\\"'))


def _join_report_lines(lines):
    """Use Windows/.NET line endings for reports and XML text builders."""
    return Environment.NewLine.join([_safe_unicode(line) for line in lines])


def _format_size(value):
    """Format bytes with base-1024 units for the native UI."""
    try:
        size_bytes = float(value)
    except Exception:
        size_bytes = 0.0

    if size_bytes < 0:
        size_bytes = 0.0

    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    while size_bytes >= 1024.0 and unit_index < len(units) - 1:
        size_bytes /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return "{0:.0f} {1}".format(size_bytes, units[unit_index])
    return "{0:.2f} {1}".format(size_bytes, units[unit_index])


# ===========================================================================
# [P03] Dependency discovery and responsive subprocess I/O
# ===========================================================================
def _find_archive_tool():
    """Locate ComicRack resource executables; do not install tooling."""
    candidates = [
        Path.Combine(System.AppDomain.CurrentDomain.BaseDirectory, "Resources", "7z64.exe"),
        Path.Combine(System.AppDomain.CurrentDomain.BaseDirectory, "Resources", "7z.exe"),
        Path.Combine(System.AppDomain.CurrentDomain.BaseDirectory, "Resources", "7za.exe"),
        Path.Combine(ROOT_DIR, "ComicRackCE_nightly", "Resources", "7z64.exe"),
        Path.Combine(ROOT_DIR, "ComicRackCE_nightly", "Resources", "7z.exe"),
        Path.Combine(ROOT_DIR, "ComicRackCE_nightly", "Resources", "7za64.exe"),
        Path.Combine(ROOT_DIR, "ComicRackCE_nightly", "Resources", "7za.exe"),
        Path.Combine(ROOT_DIR, "Resources", "7z64.exe"),
        Path.Combine(ROOT_DIR, "Resources", "7z.exe"),
        Path.Combine(ROOT_DIR, "Resources", "7za64.exe"),
        Path.Combine(ROOT_DIR, "Resources", "7za.exe"),
    ]
    for candidate in candidates:
        if File.Exists(candidate):
            return candidate
    return None


def _find_python_tool():
    """Find Python 3.9+, without treating a Python 2 install as a valid worker."""
    for candidate in ["py", "python"]:
        process = None
        try:
            info = ProcessStartInfo()
            info.FileName = candidate
            info.Arguments = "-3 --version" if candidate == "py" else "--version"
            info.UseShellExecute, info.CreateNoWindow = False, True
            info.RedirectStandardOutput = info.RedirectStandardError = True
            process = Process()
            process.StartInfo = info
            output, errors = _wait_for_process(process)
            version = (output + errors).strip().split(" ")[-1].split(".")
            if process.ExitCode == 0 and len(version) >= 2 and int(version[0]) == 3 and int(version[1]) >= 9:
                return candidate
        except Exception:
            pass
        finally:
            if process is not None:
                process.Dispose()
    return None


def _can_start_process(file_name, arguments):
    """Probe a process for dependency discovery without opening a console."""
    try:
        info = ProcessStartInfo()
        info.FileName = file_name
        info.Arguments = arguments
        info.UseShellExecute = False
        info.RedirectStandardOutput = True
        info.RedirectStandardError = True
        info.CreateNoWindow = True
        process = Process()
        process.StartInfo = info
        process.Start()
        process.StandardOutput.ReadToEnd()
        process.StandardError.ReadToEnd()
        process.WaitForExit()
        return True
    except Exception:
        return False


def _find_rar_tool():
    """Find optional WinRAR tooling used only for true CBR output."""
    candidates = []
    for candidate in ["rar.exe", "rar"]:
        candidates.append(candidate)

    for base_path in [Environment.GetEnvironmentVariable("ProgramFiles"), Environment.GetEnvironmentVariable("ProgramFiles(x86)")]:
        if not base_path:
            continue
        candidates.append(Path.Combine(base_path, "WinRAR", "Rar.exe"))

    for candidate in candidates:
        if (candidate.lower().endswith(".exe") and File.Exists(candidate)) or candidate in ["rar.exe", "rar"]:
            if _can_start_process(candidate, ""):
                return candidate
    return None


def _is_cbr_rebuild_mode(options):
    """Identify the explicit CBR-output option, independent of source type."""
    return _safe_unicode(options.get("cbr_mode", "")) == "Rebuild CBR sources as CBR output (requires WinRAR)"


def _get_output_extension(result, options):
    """Resolve CBZ/CBR output from the source scan and run options."""
    archive_type = _safe_unicode(result.get("archive_type", ""))
    if archive_type == "cbr" and _is_cbr_rebuild_mode(options):
        return ".cbr"
    return ".cbz"


def _wait_for_process(process, on_progress=None, on_started=None):
    """Drain stdout/stderr asynchronously while pumping WinForms events.

    Worker callbacks only append text; UI work stays on the calling thread.
    Never kill the child for a boundary-stop request: finish its active book."""
    output = StringBuilder()
    errors = StringBuilder()
    pending_progress = System.Collections.Concurrent.ConcurrentQueue[System.String]()
    def deliver_progress():
        latest = None
        while not pending_progress.IsEmpty:
            ok, message = pending_progress.TryDequeue()
            if ok:
                latest = message
        if latest is not None and on_progress is not None:
            try:
                on_progress(_safe_unicode(latest))
            except Exception, ex:
                errors.AppendLine("Progress display error: " + _safe_unicode(ex))
    def receive_output(sender, event):
        if event.Data is not None:
            if event.Data.startswith("PROGRESS="):
                pending_progress.Enqueue(event.Data[9:])
            else:
                output.AppendLine(event.Data)
    def receive_error(sender, event):
        if event.Data is not None:
            errors.AppendLine(event.Data)
    process.OutputDataReceived += receive_output
    process.ErrorDataReceived += receive_error
    process.Start()
    process.BeginOutputReadLine()
    process.BeginErrorReadLine()
    if on_started is not None:
        try:
            on_started(process)
        except Exception, ex:
            errors.AppendLine("Worker identity could not be recorded: " + _safe_unicode(ex))
    while not process.WaitForExit(100):
        deliver_progress()
        Application.DoEvents()
    process.WaitForExit()  # Flush asynchronous output callbacks.
    deliver_progress()
    Application.DoEvents()
    return _safe_unicode(output.ToString()), _safe_unicode(errors.ToString())


def _run_archive_list(tool_path, archive_path):
    """Ask 7-Zip for a technical listing without extracting archive contents."""
    info = ProcessStartInfo()
    info.FileName = tool_path
    info.Arguments = 'l -ba -slt "{0}"'.format(_safe_unicode(archive_path))
    info.UseShellExecute = False
    info.RedirectStandardOutput = True
    info.RedirectStandardError = True
    info.CreateNoWindow = True

    process = Process()
    process.StartInfo = info
    try:
        output_text, error_text = _wait_for_process(process)
        return process.ExitCode, _safe_unicode(output_text), _safe_unicode(error_text)
    finally:
        process.Dispose()  # Release native handles promptly in long selections.


# ===========================================================================
# [P04] Archive scanning and eligibility classification
# ===========================================================================
def _parse_archive_listing(output_text, archive_path):
    """Turn the 7-Zip technical listing into per-member dictionaries."""
    entries = []
    current = {}
    archive_name = Path.GetFileName(_safe_unicode(archive_path))

    for raw_line in output_text.splitlines():
        line = _safe_unicode(raw_line).strip()
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue

        if " = " not in line:
            continue

        key, value = line.split(" = ", 1)
        if key == "Path" and current:
            entries.append(current)
            current = {}
        current[key] = value

    if current:
        entries.append(current)

    filtered = []
    for entry in entries:
        entry_path = _safe_unicode(entry.get("Path", ""))
        if not entry_path:
            continue
        if entry_path == _safe_unicode(archive_path) or entry_path == archive_name:
            continue
        if _safe_unicode(entry.get("Folder", "")).strip() == "+":
            continue
        filtered.append(entry)
    return filtered


def _classify_image_format(counts):
    """Reduce supported page-extension counts to a smart-list label."""
    if counts["webp"] > 0 and counts["jpg"] == 0 and counts["jpeg"] == 0 and counts["png"] == 0:
        return "WEBP"
    if counts["jpg"] + counts["jpeg"] > 0 and counts["png"] == 0 and counts["webp"] == 0:
        return "JPG"
    if counts["png"] > 0 and counts["jpg"] == 0 and counts["jpeg"] == 0 and counts["webp"] == 0:
        return "PNG"
    if counts["jpg"] + counts["jpeg"] + counts["png"] + counts["webp"] == 0:
        return "NO_IMAGES"
    return "MIXED"


def _scan_book(book, tool_path):
    """Return one scan-result dictionary without converting comic files.

    Keys include file_path, archive_type, counts, eligible and skip_reason.
    The caller owns ComicRack custom-value updates and later write actions."""
    file_path = _safe_unicode(getattr(book, "FilePath", ""))
    result = {
        "caption": _safe_unicode(getattr(book, "Caption", "")) or _safe_unicode(getattr(book, "FileNameWithExtension", "")),
        "file_path": file_path,
        "file_name": _safe_unicode(getattr(book, "FileNameWithExtension", "")) or Path.GetFileName(file_path),
        "archive_type": Path.GetExtension(file_path).lower().lstrip("."),
        "file_size": long(getattr(book, "FileSize", 0) or 0),
        "status": "",
        "image_format": "",
        "image_count": 0,
        "jpg_count": 0,
        "png_count": 0,
        "webp_count": 0,
        "eligible": False,
        "strategy": "",
        "skip_reason": "",
        "notes": "",
    }

    if not file_path or not File.Exists(file_path):
        result["status"] = "Missing file"
        result["image_format"] = "MISSING"
        result["strategy"] = "Restore or relink the missing source file before conversion."
        result["skip_reason"] = "MISSING"
        result["notes"] = "Book file could not be found on disk."
        return result

    if result["archive_type"] not in ["cbz", "cbr"]:
        result["status"] = "Unsupported archive"
        result["image_format"] = "UNSUPPORTED"
        result["strategy"] = "Skip unsupported archive types."
        result["skip_reason"] = "UNSUPPORTED"
        result["notes"] = "Only CBZ and CBR are analyzed in Phase 1."
        return result

    exit_code, output_text, error_text = _run_archive_list(tool_path, file_path)
    if exit_code != 0:
        result["status"] = "Archive read error"
        result["image_format"] = "ERROR"
        result["strategy"] = "Fix archive readability before conversion."
        result["skip_reason"] = "ARCHIVE_ERROR"
        result["notes"] = error_text or "Archive listing tool returned an error."
        return result

    counts = {
        "jpg": 0,
        "jpeg": 0,
        "png": 0,
        "webp": 0,
    }
    entries = _parse_archive_listing(output_text, file_path)
    for entry in entries:
        entry_path = _safe_unicode(entry.get("Path", ""))
        extension = Path.GetExtension(entry_path).lower()
        if extension not in IMAGE_EXTENSIONS:
            continue
        counts[extension.lstrip(".")] += 1

    result["jpg_count"] = counts["jpg"] + counts["jpeg"]
    result["png_count"] = counts["png"]
    result["webp_count"] = counts["webp"]
    result["image_count"] = result["jpg_count"] + result["png_count"] + result["webp_count"]
    result["image_format"] = _classify_image_format(counts)

    if result["image_format"] == "WEBP":
        result["status"] = "Already WebP"
        result["strategy"] = "No conversion needed."
        result["notes"] = "Archive already appears to be fully WebP."
    elif result["image_format"] == "JPG":
        result["status"] = "Eligible"
        result["eligible"] = True
        result["strategy"] = "Convert all JPEG pages to WebP."
        result["notes"] = "Archive is JPEG-only and is a strong conversion candidate."
    elif result["image_format"] == "PNG":
        result["status"] = "PNG-only"
        result["strategy"] = "Leave PNG-only archives unchanged."
        result["skip_reason"] = "PNG_ONLY"
        result["notes"] = "Archive contains only PNG pages. This workflow is tuned for JPEG-to-WebP conversion."
    elif result["jpg_count"] > 0 and result["png_count"] > result["jpg_count"]:
        result["status"] = "PNG-heavy mixed"
        result["strategy"] = "Prefer leaving PNG-heavy mixed archives unchanged."
        result["skip_reason"] = "PNG_HEAVY"
        result["notes"] = "Archive contains more PNG pages than JPEG pages, so it is skipped by default to avoid weak gains on loss-sensitive pages."
    elif result["jpg_count"] > 0 and (result["png_count"] > 0 or result["webp_count"] > 0):
        result["status"] = "Mixed JPEG-led"
        result["eligible"] = True
        result["strategy"] = "Convert JPEG pages to WebP and preserve PNG/WebP pages."
        result["notes"] = "Archive contains mixed page types. Only JPEG pages will be converted."
    elif result["image_format"] == "MIXED":
        result["status"] = "Mixed"
        result["strategy"] = "Review the archive manually before conversion."
        result["notes"] = "Archive contains a mix of page image types without clear JPEG conversion value."
    else:
        result["status"] = "No image pages"
        result["strategy"] = "No supported image pages were detected."
        result["skip_reason"] = "NO_IMAGES"
        result["notes"] = "No supported comic page images were detected in the archive."

    return result


# ===========================================================================
# [P05] Output, staging and backup path policies
# ===========================================================================
def _build_copy_output_path(source_path):
    """Legacy CBZ-only copy naming helper; active code uses the result variant."""
    directory = Path.GetDirectoryName(_safe_unicode(source_path))
    base_name = Path.GetFileNameWithoutExtension(_safe_unicode(source_path))
    output_path = Path.Combine(directory, base_name + " [WebP].cbz")
    if not File.Exists(output_path):
        return output_path

    stamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
    return Path.Combine(directory, base_name + " [WebP] " + stamp + ".cbz")


def _build_copy_output_path_for_result(result, options):
    """Choose an unused sibling filename for retained copy output."""
    source_path = _safe_unicode(result.get("file_path", ""))
    directory = Path.GetDirectoryName(source_path)
    base_name = Path.GetFileNameWithoutExtension(source_path)
    extension = _get_output_extension(result, options)
    output_path = Path.Combine(directory, base_name + " [WebP]" + extension)
    if not File.Exists(output_path):
        return output_path

    stamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
    return Path.Combine(directory, base_name + " [WebP] " + stamp + extension)


def _build_benchmark_output_path(source_path):
    """Legacy single-path benchmark naming; active trials use the result variant."""
    benchmark_dir = Path.Combine(Path.GetTempPath(), "WebPOptimizerBenchmarks")
    _ensure_directory(benchmark_dir)
    base_name = Path.GetFileNameWithoutExtension(_safe_unicode(source_path))
    stamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
    return Path.Combine(benchmark_dir, base_name + " [Benchmark] " + stamp + ".cbz")


def _build_benchmark_output_path_for_result(result, options):
    """Create a unique trial archive path in selected work or source storage."""
    source_path = _safe_unicode(result.get("file_path", ""))
    directory = options.get("work_dir", "") or Path.GetDirectoryName(source_path)
    _ensure_directory(directory)
    return Path.Combine(directory, "webp_trial_" + System.Guid.NewGuid().ToString("N") + _get_output_extension(result, options))


def _build_replace_temp_output_path(source_path):
    """Legacy CBZ-only staging path helper; retained for compatibility."""
    directory = Path.GetDirectoryName(_safe_unicode(source_path))
    base_name = Path.GetFileNameWithoutExtension(_safe_unicode(source_path))
    stamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
    return Path.Combine(directory, base_name + " [WebP Replace Temp] " + stamp + ".cbz")


def _build_replace_temp_output_path_for_result(result, options):
    """Stage converted output beside its source for the later replacement step."""
    source_path = _safe_unicode(result.get("file_path", ""))
    directory = Path.GetDirectoryName(source_path)
    base_name = Path.GetFileNameWithoutExtension(source_path)
    stamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
    return Path.Combine(directory, base_name + " [WebP Replace Temp] " + stamp + _get_output_extension(result, options))


def _build_backup_path(source_path):
    """Choose an original-backup path, adding a timestamp when needed."""
    source_path = _safe_unicode(source_path)
    backup_path = source_path + ".pre-webp-backup"
    if not File.Exists(backup_path):
        return backup_path
    stamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
    return source_path + ".pre-webp-backup." + stamp


def _build_final_replace_path(source_path, archive_type, cbr_mode):
    """Keep the source name unless a CBR is being migrated to CBZ."""
    source_path = _safe_unicode(source_path)
    archive_type = _safe_unicode(archive_type).lower()
    if archive_type == "cbr" and _safe_unicode(cbr_mode) == "Convert CBR sources to CBZ output":
        return Path.ChangeExtension(source_path, ".cbz")
    return source_path


# ===========================================================================
# [P06] ComicRack metadata normalization and XML export
# ===========================================================================
def _get_book_property(book, property_name, default_value=None):
    """Read a possibly unavailable ComicRack property with a safe default."""
    try:
        return getattr(book, property_name)
    except Exception:
        return default_value


def _normalize_text_value(value):
    """Normalize optional ComicRack text for metadata export."""
    text = _safe_unicode(value).strip()
    if not text or text == "-1":
        return u""
    return text


def _normalize_int_value(value):
    """Convert an optional numeric property into XML-ready integer text."""
    try:
        number = int(value)
    except Exception:
        return u""
    if number < 0:
        return u""
    return unicode(number)


def _normalize_float_value(value):
    """Convert an optional numeric property into XML-ready decimal text."""
    try:
        number = float(value)
    except Exception:
        return u""
    if number <= 0:
        return u""
    return _safe_unicode(number)


def _normalize_yes_no_value(value):
    """Normalize boolean-like values for comic metadata XML."""
    text = _safe_unicode(value).strip().lower()
    if not text:
        return u""
    if text == "unknown":
        return u""
    if text in ["true", "1", "yes"]:
        return u"Yes"
    if text in ["false", "0", "no"]:
        return u"No"
    return _safe_unicode(value)


def _append_xml_element(lines, element_name, value):
    """Append a nonempty, escaped metadata element to the XML line buffer."""
    text = _normalize_text_value(value)
    if not text:
        return
    lines.append(u"  <{0}>{1}</{0}>".format(element_name, _escape_xml_text(text)))


def _append_xml_raw_element(lines, element_name, value):
    """Append already-formatted XML content; callers must own escaping."""
    text = _safe_unicode(value).strip()
    if not text:
        return
    lines.append(u"  <{0}>{1}</{0}>".format(element_name, text))


def _format_datetime_value(value):
    """Normalize CLR/date-like values for metadata date fields."""
    if value is None:
        return u""
    try:
        text = _safe_unicode(value.ToString("o"))
        text = text.replace(u".0000000Z", u"Z")
        text = text.replace(u".0000000+", u"+")
        text = text.replace(u".0000000-", u"-")
        if text.endswith(u".0000000"):
            text = text[:-8]
        return text
    except Exception:
        pass
    text = _safe_unicode(value).strip()
    if not text or text == "-1":
        return u""
    return text


def _build_custom_values_store(book):
    """Export ComicRack custom values into its XML storage representation."""
    pairs = []
    try:
        for pair in book.GetCustomValues():
            key = _safe_unicode(pair.Key).strip()
            value = _safe_unicode(pair.Value).strip()
            if not key:
                continue
            if key in [IMAGE_FORMAT_KEY, ARCHIVE_TYPE_KEY]:
                continue
            pairs.append(key + "=" + value)
    except Exception:
        return u""
    if not pairs:
        return u""
    return u"," + u",".join(pairs)


def _append_page_metadata(lines, book):
    """Export page/bookmark metadata using the existing page ordering."""
    try:
        pages = _get_book_property(book, "Pages", None)
        if not pages:
            return
        first_page = None
        for page in pages:
            first_page = page
            break
        if first_page is None:
            return

        image_index = _normalize_int_value(_get_book_property(first_page, "Image", 0)) or u"0"
        width = _normalize_int_value(_get_book_property(first_page, "ImageWidth", -1))
        height = _normalize_int_value(_get_book_property(first_page, "ImageHeight", -1))
        page_type = _normalize_text_value(_get_book_property(first_page, "Type", u"FrontCover")) or u"FrontCover"

        attributes = [u'Image="{0}"'.format(_escape_xml_attribute(image_index))]
        if width:
            attributes.append(u'ImageWidth="{0}"'.format(_escape_xml_attribute(width)))
        if height:
            attributes.append(u'ImageHeight="{0}"'.format(_escape_xml_attribute(height)))
        if page_type:
            attributes.append(u'Type="{0}"'.format(_escape_xml_attribute(page_type)))

        lines.append(u"  <Pages>")
        lines.append(u"    <Page {0} />".format(u" ".join(attributes)))
        lines.append(u"  </Pages>")
    except Exception:
        pass


def _append_standard_metadata(lines, book):
    """Map ComicRack properties to the supported comic metadata elements."""
    string_fields = [
        ("Title", _get_book_property(book, "Title", None)),
        ("Series", _get_book_property(book, "Series", None)),
        ("Number", _get_book_property(book, "Number", None)),
        ("Count", _get_book_property(book, "Count", None)),
        ("Volume", _normalize_int_value(_get_book_property(book, "Volume", _get_book_property(book, "ShadowVolume", -1)))),
        ("SeriesGroup", _get_book_property(book, "SeriesGroup", None)),
        ("Summary", _get_book_property(book, "Summary", None)),
        ("Notes", _get_book_property(book, "Notes", None)),
        ("Year", _normalize_int_value(_get_book_property(book, "Year", -1))),
        ("Month", _normalize_int_value(_get_book_property(book, "Month", -1))),
        ("Day", _normalize_int_value(_get_book_property(book, "Day", -1))),
        ("Writer", _get_book_property(book, "Writer", None)),
        ("Penciller", _get_book_property(book, "Penciller", None)),
        ("Inker", _get_book_property(book, "Inker", None)),
        ("Colorist", _get_book_property(book, "Colorist", None)),
        ("Letterer", _get_book_property(book, "Letterer", None)),
        ("CoverArtist", _get_book_property(book, "CoverArtist", None)),
        ("Editor", _get_book_property(book, "Editor", None)),
        ("Publisher", _get_book_property(book, "Publisher", None)),
        ("Web", _get_book_property(book, "Web", None)),
        ("PageCount", _normalize_int_value(_get_book_property(book, "PageCount", -1))),
        ("Format", _get_book_property(book, "Format", None)),
        ("MainCharacterOrTeam", _get_book_property(book, "MainCharacterOrTeam", None)),
        ("AlternateSeries", _get_book_property(book, "AlternateSeries", None)),
        ("AlternateNumber", _get_book_property(book, "AlternateNumber", None)),
        ("AlternateCount", _get_book_property(book, "AlternateCount", None)),
        ("Imprint", _get_book_property(book, "Imprint", None)),
        ("Genre", _get_book_property(book, "Genre", None)),
        ("Tags", _get_book_property(book, "Tags", None)),
        ("Characters", _get_book_property(book, "Characters", None)),
        ("Teams", _get_book_property(book, "Teams", None)),
        ("Locations", _get_book_property(book, "Locations", None)),
        ("ScanInformation", _get_book_property(book, "ScanInformation", None)),
        ("StoryArc", _get_book_property(book, "StoryArc", None)),
        ("LanguageISO", _get_book_property(book, "LanguageISO", None)),
        ("AgeRating", _get_book_property(book, "AgeRating", None)),
        ("BlackAndWhite", _normalize_yes_no_value(_get_book_property(book, "BlackAndWhite", None))),
        ("Manga", _normalize_yes_no_value(_get_book_property(book, "Manga", None))),
        ("SeriesComplete", _normalize_yes_no_value(_get_book_property(book, "SeriesComplete", None))),
        ("CommunityRating", _normalize_float_value(_get_book_property(book, "CommunityRating", -1))),
    ]

    for element_name, value in string_fields:
        _append_xml_element(lines, element_name, value)

    _append_page_metadata(lines, book)

    trailing_fields = [
        ("Imprint", _get_book_property(book, "Imprint", None)),
        ("Genre", _get_book_property(book, "Genre", None)),
        ("Tags", _get_book_property(book, "Tags", None)),
        ("Characters", _get_book_property(book, "Characters", None)),
        ("Teams", _get_book_property(book, "Teams", None)),
        ("Locations", _get_book_property(book, "Locations", None)),
        ("ScanInformation", _get_book_property(book, "ScanInformation", None)),
        ("StoryArc", _get_book_property(book, "StoryArc", None)),
        ("LanguageISO", _get_book_property(book, "LanguageISO", None)),
        ("AgeRating", _get_book_property(book, "AgeRating", None)),
        ("BlackAndWhite", _normalize_yes_no_value(_get_book_property(book, "BlackAndWhite", None))),
        ("Manga", _normalize_yes_no_value(_get_book_property(book, "Manga", None))),
        ("SeriesComplete", _normalize_yes_no_value(_get_book_property(book, "SeriesComplete", None))),
        ("CommunityRating", _normalize_float_value(_get_book_property(book, "CommunityRating", -1))),
    ]
    for element_name, value in trailing_fields:
        _append_xml_element(lines, element_name, value)


def _build_comicinfo_xml(book):
    """Serialize standard comic metadata from the current library entry."""
    lines = [u'<?xml version="1.0"?>', u'<ComicInfo xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">']
    _append_standard_metadata(lines, book)
    lines.append(u"</ComicInfo>")
    return u"\n".join(lines)


def _build_comicbook_xml(book):
    """Serialize the ComicRack-specific metadata wrapper for the helper."""
    lines = [u'<?xml version="1.0"?>', u'<ComicBook xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">']
    _append_standard_metadata(lines, book)
    _append_xml_element(lines, "Added", _format_datetime_value(_get_book_property(book, "AddedTime", None)))
    _append_xml_element(lines, "Released", _format_datetime_value(_get_book_property(book, "ReleasedTime", None)))
    enable_proposed = _normalize_text_value(_safe_unicode(_get_book_property(book, "EnableProposed", False)).lower())
    if enable_proposed:
        _append_xml_raw_element(lines, "EnableProposed", enable_proposed)
    custom_values_store = _build_custom_values_store(book)
    if custom_values_store:
        _append_xml_element(lines, "CustomValuesStore", custom_values_store)
    lines.append(u"</ComicBook>")
    return u"\n".join(lines)


def _write_comicinfo_temp_file(book):
    """Write a short-lived ComicInfo input; the helper bridge removes it later."""
    file_name = u"webp_optimizer_comicinfo_{0}.xml".format(_safe_unicode(DateTime.Now.Ticks))
    path = Path.Combine(Path.GetTempPath(), file_name)
    _write_text_file(path, _build_comicinfo_xml(book))
    return path


def _write_comicbook_temp_file(book):
    """Write a short-lived ComicBook input; the helper bridge removes it later."""
    file_name = u"webp_optimizer_comicbook_{0}.xml".format(_safe_unicode(DateTime.Now.Ticks))
    path = Path.Combine(Path.GetTempPath(), file_name)
    _write_text_file(path, _build_comicbook_xml(book))
    return path


# ===========================================================================
# [P07] IronPython to CPython helper protocol
# ===========================================================================
def _parse_helper_output(output_text):
    """Parse newline-delimited KEY=value records, splitting at the first equals."""
    result = {}
    for raw_line in _safe_unicode(output_text).splitlines():
        line = _safe_unicode(raw_line).strip()
        if not line or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def _run_conversion_helper(python_tool, tool_path, result, options, book):
    """Export metadata, launch CPython and return its result plus bridge fields.

    Numeric helper values arrive as strings. SOURCE_SIGNATURE is a local
    size/mtime tuple, not a wire field or cryptographic source fingerprint."""
    run_mode = _safe_unicode(options.get("run_mode", RUN_MODE_VALUES[0]))
    if run_mode == "Replace Originals":
        output_path = _build_replace_temp_output_path_for_result(result, options)
    elif run_mode == "Test savings & quality":
        output_path = options.get("trial_output_path", "") or _build_benchmark_output_path_for_result(result, options)
    else:
        output_path = _build_copy_output_path_for_result(result, options)
    output_path = options.get("checkpoint_output_path", "") or output_path
    source_info = FileInfo(_safe_unicode(result.get("file_path", "")))
    source_signature = (source_info.Length, source_info.LastWriteTimeUtc.Ticks)
    comicinfo_path = _write_comicinfo_temp_file(book)
    comicbook_path = _write_comicbook_temp_file(book)
    rar_tool = options.get("rar_tool", "") if _is_cbr_rebuild_mode(options) else ""

    info = ProcessStartInfo()
    info.FileName = python_tool
    extra_args = "-3 " if python_tool == "py" else ""
    info.Arguments = extra_args + "{0} --archive-path {1} --archive-tool {2} --quality-mode {3} --output-path {4} --archive-type {5} --comicinfo-path {6} --comicbook-path {7} --size-policy {8} --rar-tool {9} --encoder-backend {10} --resize-mode {11}".format(
        _quote_argument(HELPER_SCRIPT),
        _quote_argument(result.get("file_path", "")),
        _quote_argument(tool_path),
        _quote_argument(options.get("quality_mode", QUALITY_MODE_VALUES[0])),
        _quote_argument(output_path),
        _quote_argument(result.get("archive_type", "cbz")),
        _quote_argument(comicinfo_path),
        _quote_argument(comicbook_path),
        _quote_argument(options.get("size_policy", SIZE_POLICY_VALUES[0])),
        _quote_argument(rar_tool),
        _quote_argument(options.get("encoder_backend", ENCODER_BACKEND_VALUES[0])),
        _quote_argument(options.get("resize_mode", RESIZE_MODE_VALUES[0])))
    info.Arguments += " --resource-profile " + _quote_argument(options.get("resource_profile", "Normal"))
    if options.get("_measure_resources", False):
        info.Arguments += " --metrics"
    for key in ["prefetch_next", "prefetch_record"]:
        if options.get(key):
            info.Arguments += " --" + key.replace("_", "-") + " " + _quote_argument(options[key])
    info.Arguments += " --page-workers " + _quote_argument(options.get("page_workers", "1"))
    info.Arguments += " --work-dir " + _quote_argument(options.get("work_dir", ""))
    if options.get("preview_dir", ""):
        info.Arguments += " --preview-dir " + _quote_argument(options["preview_dir"])
    info.UseShellExecute = False
    info.RedirectStandardOutput = True
    info.RedirectStandardError = True
    info.CreateNoWindow = True

    process = None
    try:
        process = Process()
        process.StartInfo = info
        progress = options.get("_progress_form")
        callback = progress.update_archive_progress if progress is not None and hasattr(progress, "update_archive_progress") else None
        started = (lambda child: _record_worker_started(_safe_unicode(result.get("file_path", "")), options, child)) if options.get("checkpoint_output_path") else None
        output_text, error_text = _wait_for_process(process, callback, started)

        helper_result = _parse_helper_output(output_text)
        helper_result["SOURCE_SIGNATURE"] = source_signature
        helper_result["exit_code"] = str(process.ExitCode)
        if process.ExitCode != 0 and helper_result.get("STATUS") == "OK":
            helper_result["STATUS"] = "ERROR"
            helper_result["MESSAGE"] = "Worker exited with an error after reporting success; output requires inspection. " + _safe_unicode(error_text)
        helper_result["stderr"] = _safe_unicode(error_text)
        helper_result["requested_output_path"] = output_path
        return helper_result
    finally:
        try:
            if comicinfo_path and File.Exists(comicinfo_path):
                File.Delete(comicinfo_path)
        except Exception:
            pass
        try:
            if comicbook_path and File.Exists(comicbook_path):
                File.Delete(comicbook_path)
        except Exception:
            pass
        if process is not None:
            process.Dispose()


# ===========================================================================
# [P08] Library updates and recoverable source replacement
# ===========================================================================
def _set_scan_custom_values(book, result):
    """Update scan labels on the selected ComicRack entry, not the archive."""
    try:
        book.SetCustomValue(IMAGE_FORMAT_KEY, _safe_unicode(result.get("image_format", "")))
    except Exception:
        pass

    _status_after_scan(book, result)


def _set_converted_custom_values(book, final_path, helper_result):
    """Apply output labels only when a replacement is accepted by the caller."""
    try:
        book.SetCustomValue(IMAGE_FORMAT_KEY, _safe_unicode(helper_result.get("OUTPUT_IMAGE_FORMAT", "WEBP")))
    except Exception:
        pass
    try:
        book.SetCustomValue(ARCHIVE_TYPE_KEY, Path.GetExtension(_safe_unicode(final_path)).lstrip(".").upper())
    except Exception:
        pass


def _update_book_file_path(book, final_output_path):
    """Relink an existing entry after a successful extension-changing replacement."""
    try:
        current_path = _safe_unicode(getattr(book, "FilePath", ""))
        final_output_path = _safe_unicode(final_output_path)
        if not current_path or not final_output_path:
            return
        if Path.GetFullPath(current_path).lower() == Path.GetFullPath(final_output_path).lower():
            return
        book.FilePath = final_output_path
    except Exception:
        pass


def _delete_file_if_exists(path):
    """Delete a caller-owned file when present; do not use for broad cleanup."""
    if path and File.Exists(path):
        File.Delete(path)


def _finalize_replacement(source_path, helper_result, options):
    """Install validated output while retaining recoverable files on failure.

    Same-path replacement uses File.Replace; extension changes need two
    renames and a rollback path. The recovery record is not a transaction
    journal with guaranteed power-loss durability. Never delete-then-move."""
    temp_output_path = _safe_unicode(helper_result.get("OUTPUT_PATH", "")) or _safe_unicode(helper_result.get("requested_output_path", ""))
    if not temp_output_path or not File.Exists(temp_output_path):
        return {
            "STATUS": "ERROR",
            "MESSAGE": "Converted temporary file was not found for replacement.",
        }

    final_output_path = _build_final_replace_path(source_path, Path.GetExtension(source_path).lower().lstrip("."), options.get("cbr_mode", ""))
    create_backup = bool(options.get("create_backup", False))
    backup_path = ""

    rollback_path = source_path + ".webp-rollback-" + System.Guid.NewGuid().ToString("N")
    same_path = Path.GetFullPath(source_path).lower() == Path.GetFullPath(final_output_path).lower()
    journal_path = source_path + ".webp-recovery.txt"
    try:
        if helper_result.get("SOURCE_SIGNATURE", None) is not None:
            current_info = FileInfo(source_path)
            if (current_info.Length, current_info.LastWriteTimeUtc.Ticks) != helper_result["SOURCE_SIGNATURE"]:
                raise Exception("Source archive changed; refusing replacement.")
        if File.Exists(journal_path):
            raise Exception("Unresolved recovery record exists: " + journal_path)
        if not same_path and File.Exists(final_output_path):
            raise Exception("Destination already exists; refusing to overwrite: " + final_output_path)
        if create_backup:
            backup_path = _build_backup_path(source_path)
            File.Copy(source_path, backup_path, False)

        _write_text_file(journal_path, "WebP replacement recovery record\nSource: " + source_path + "\nConverted: " + temp_output_path + "\nFinal: " + final_output_path + "\nRollback: " + rollback_path + "\nBackup: " + backup_path + "\nInspect these paths before retrying; do not delete an available original.\n")
        if same_path:
            # Same-directory replacement: never fall back to delete-then-move.
            File.Replace(temp_output_path, source_path, None)
        else:
            # Extension changes need two renames. Keep the source recoverable.
            File.Move(source_path, rollback_path)
            try:
                File.Move(temp_output_path, final_output_path)
            except Exception:
                File.Move(rollback_path, source_path)
                raise
            try:
                File.Delete(rollback_path)
            except Exception:
                helper_result["RECOVERY_PATH"] = rollback_path

        if not File.Exists(rollback_path):
            try:
                File.Delete(journal_path)
            except Exception:
                helper_result["RECOVERY_PATH"] = journal_path
        helper_result["OUTPUT_PATH"] = final_output_path
        helper_result["FINAL_OUTPUT_PATH"] = final_output_path
        if backup_path:
            helper_result["BACKUP_PATH"] = backup_path
        helper_result["MESSAGE"] = "Replaced original archive successfully."
        if helper_result.get("RECOVERY_PATH", ""):
            helper_result["MESSAGE"] += " Temporary original could not be removed: " + rollback_path
        return helper_result
    except Exception, ex:
        # Retain both the converted output and any recovery file on failure.
        return {
            "STATUS": "ERROR",
            "MESSAGE": "Replace step failed; retained available files for recovery. Record: " + journal_path + ". " + _safe_unicode(ex),
            "OUTPUT_PATH": temp_output_path,
            "BACKUP_PATH": backup_path,
            "RECOVERY_PATH": rollback_path if File.Exists(rollback_path) else "",
        }


# ===========================================================================
# [P09] Reports, sampling and five-quality test orchestration
# ===========================================================================
def _extract_report_summary_items(report_text):
    """Read the header before the first blank line; retain legacy field names."""
    summary_items = []
    lines = _safe_unicode(report_text).splitlines()
    if not lines:
        return summary_items
    summary_items.append(("Report", lines[0].strip()))
    for line in lines[1:]:
        text = _safe_unicode(line).strip()
        if not text:
            break
        if ": " not in text:
            continue
        key, value = text.split(": ", 1)
        summary_items.append((key, value))
    return summary_items


def _get_skip_reason_count(conversion_results, reason_code):
    """Count a specific skip code without treating it as an error."""
    count = 0
    for conversion_result in conversion_results:
        if _safe_unicode(conversion_result.get("SKIP_REASON", "")) == reason_code:
            count += 1
    return count


def _build_analysis_report(results, tool_path):
    """Render scans, eligibility counts and per-book analysis as plain text."""
    lines = []
    lines.append("WebP Optimizer Analysis Report")
    lines.append("Generated: " + _safe_unicode(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")))
    lines.append("Archive Tool: " + _safe_unicode(tool_path))
    lines.append("Books Scanned: " + str(len([r for r in results if r.get("status", "") != "Not processed"])))

    eligible_count = 0
    already_webp_count = 0
    mixed_count = 0
    error_count = 0
    missing_count = 0
    png_only_count = 0
    png_heavy_count = 0
    for result in results:
        image_format = _safe_unicode(result.get("image_format", ""))
        status = _safe_unicode(result.get("status", ""))
        if image_format == "JPG":
            eligible_count += 1
        elif image_format == "WEBP":
            already_webp_count += 1
        elif image_format == "MIXED":
            mixed_count += 1
        elif image_format == "ERROR":
            error_count += 1
        elif image_format == "MISSING":
            missing_count += 1
        if status == "PNG-only":
            png_only_count += 1
        elif status == "PNG-heavy mixed":
            png_heavy_count += 1

    lines.append("JPEG-only Candidates: " + str(eligible_count))
    lines.append("Already WebP: " + str(already_webp_count))
    lines.append("Mixed Archives: " + str(mixed_count))
    lines.append("PNG-only Archives: " + str(png_only_count))
    lines.append("PNG-heavy Mixed Archives: " + str(png_heavy_count))
    lines.append("Missing Files: " + str(missing_count))
    lines.append("Errors: " + str(error_count))
    lines.append("")
    lines.append("Per-Book Results")
    lines.append("----------------")

    for result in results:
        lines.append(_safe_unicode(result.get("caption", "")))
        lines.append("  File: " + _safe_unicode(result.get("file_path", "")))
        lines.append("  Archive Type: " + _safe_unicode(result.get("archive_type", "")).upper())
        lines.append("  ImageFormat: " + _safe_unicode(result.get("image_format", "")))
        lines.append("  Status: " + _safe_unicode(result.get("status", "")))
        lines.append("  Strategy: " + _safe_unicode(result.get("strategy", "")))
        lines.append("  Images: total={0}, jpg={1}, png={2}, webp={3}".format(
            result.get("image_count", 0),
            result.get("jpg_count", 0),
            result.get("png_count", 0),
            result.get("webp_count", 0)))
        lines.append("  Size: {0}".format(_format_size(result.get("file_size", 0))))
        lines.append("  Notes: " + _safe_unicode(result.get("notes", "")))
        lines.append("")

    return _join_report_lines(lines)


def _trial_sample_indices(results, options):
    """Select up to three spaced eligible indices in current selection order."""
    eligible = [i for i, r in enumerate(results) if r.get("eligible", False) and not (r.get("archive_type", "") == "cbr" and options.get("cbr_mode", "") == CBR_MODE_VALUES[1])]
    if len(eligible) <= BENCHMARK_SAMPLE_LIMIT:
        return set(eligible)
    return set([eligible[0], eligible[(len(eligible) - 1) // 2], eligible[-1]])


def _run_quality_trial(python_tool, tool_path, result, options, book, progress_form):
    """Measure all configured quality passes for one source and clean trial archives.

    Deliberately do not stop between qualities: the active-book boundary
    includes every pass. Preview assets are separate from disposable CBZ/CBR."""
    trials = []
    for quality in TRIAL_QUALITY_LEVELS:
        trial_options = dict(options)
        trial_options.update({"quality_mode": quality, "size_policy": "Keep All Results", "resize_mode": "No Resize"})
        trial_options["trial_output_path"] = _build_benchmark_output_path_for_result(result, options)
        if options.get("keep_test_previews", False):
            trial_options["preview_dir"] = Path.Combine(options["trial_preview_root"], System.Guid.NewGuid().ToString("N") + "-" + quality)
        progress_form._status_label.Text = "Testing " + quality + " - conversion and validation"
        if hasattr(progress_form, "begin_quality_pass"):
            progress_form.begin_quality_pass(quality)
        clock = Stopwatch.StartNew()
        try:
            trial = _run_conversion_helper(python_tool, tool_path, result, trial_options, book)
        except Exception, ex:
            trial = {"STATUS": "ERROR", "MESSAGE": "Quality trial failed: " + _safe_unicode(ex)}
        clock.Stop()
        trial["SECONDS"] = "{0:.1f}".format(clock.Elapsed.TotalSeconds)
        if trial.get("CLEANUP_WARNING"):
            trial["MESSAGE"] = _safe_unicode(trial.get("MESSAGE", "")) + " " + _safe_unicode(trial["CLEANUP_WARNING"])
            progress_form.stop_requested = True
        path = _safe_unicode(trial.get("OUTPUT_PATH", "")) or _safe_unicode(trial.get("requested_output_path", "")) or trial_options["trial_output_path"]
        if path and File.Exists(path):
            try:
                File.Delete(path)
            except Exception, ex:
                trial["STATUS"] = "ERROR"
                trial["MESSAGE"] = "Trial archive cleanup failed; remove manually: " + path + ". " + _safe_unicode(ex)
        trials.append(trial)
        if hasattr(progress_form, "record_quality_pass"):
            progress_form.record_quality_pass(trial)
    for trial in trials[1:]:
        if trials[0].get("SOURCE_SIGNATURE", None) != trial.get("SOURCE_SIGNATURE", None):
            trial["STATUS"] = "ERROR"
            trial["MESSAGE"] = "Source archive changed between quality passes; comparison excluded."
    paired = all([r.get("STATUS", "") == "OK" for r in trials])
    result = dict(zip(TRIAL_QUALITY_LEVELS, trials))
    result.update({"STATUS": "OK" if paired else "ERROR", "MESSAGE": "Original unchanged. All five trial archives removed." if paired else "One or more quality trials failed; see trial details."})
    return result


def _build_quality_trial_report(results, measurements, tool_path, options):
    """Compare byte-weighted totals over the same fully successful sample books."""
    paired = [m for m in measurements if m.get("STATUS", "") == "OK"]
    attempted = [m for m in measurements if "Q60" in m]
    lines = ["WebP Optimizer Quality Trial", "Generated: " + _safe_unicode(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")), "Run Mode: Test savings & quality", "Encoder Backend: " + options.get("encoder_backend", ENCODER_BACKEND_VALUES[0]), "Resize Mode: No Resize", "Books Scanned: " + str(len([r for r in results if r.get("status", "") != "Not processed"])), "Compared Books: " + str(len(paired)), "Failed: " + str(len(attempted) - len(paired)), "Skipped: " + str(len([m for m in measurements if m.get("STATUS", "") == "SKIPPED"])), "Sampling: First, middle and last eligible entries in selection order; at most 3 books. Not a representative collection estimate."]
    for quality in TRIAL_QUALITY_LEVELS:
        source_bytes = sum([long(m[quality].get("SOURCE_SIZE", "0")) for m in paired])
        output_bytes = sum([long(m[quality].get("OUTPUT_SIZE", "0")) for m in paired])
        reduction = "{0:.2f}%".format(100.0 * (source_bytes - output_bytes) / source_bytes) if source_bytes else "Not measured"
        lines += [quality + " Reduction: " + reduction, quality + " Source Size: " + _format_size(source_bytes), quality + " Output Size: " + _format_size(output_bytes), quality + " Time: {0:.1f} seconds".format(sum([float(m[quality].get("SECONDS", "0")) for m in attempted]))]
    lines += ["Timing Scope: End-to-end helper time including extraction, encoding, metadata, rebuild and validation. Separate passes can be affected by filesystem caching.", "Savings Scope: Byte-weighted, using only books where all five qualities succeeded. Originals unchanged. Trial archive cleanup failures are listed per book. Negative reduction means growth."]
    if options.get("keep_test_previews", False):
        lines.append("Preview Folder: " + options.get("trial_preview_root", ""))
    lines += ["", "Per-Book Conversion Results", "---------------------------"]
    for result, measured in zip(results, measurements):
        lines += [_safe_unicode(result.get("caption", "")), "  Source: " + _safe_unicode(result.get("file_path", "")), "  Conversion Status: " + measured.get("STATUS", ""), "  Notes: " + measured.get("MESSAGE", "")]
        for quality in TRIAL_QUALITY_LEVELS:
            if quality in measured:
                trial = measured[quality]
                lines += ["  " + quality + " Savings: " + trial.get("SAVINGS_PERCENT", "Not measured") + ("%" if "SAVINGS_PERCENT" in trial else ""), "  " + quality + " Time: " + trial.get("SECONDS", "0") + " s", "  " + quality + " Status: " + trial.get("STATUS", ""), "  " + quality + " Detail: " + trial.get("MESSAGE", "")]
                for key in sorted(trial):
                    if key.startswith("TIME_") and key.endswith("_SECONDS"):
                        lines.append("  " + quality + " " + key + ": " + _safe_unicode(trial[key]))
                if trial.get("PREVIEW_PATH", ""):
                    lines.append("  " + quality + " Preview: " + trial["PREVIEW_PATH"])
        lines.append("")
    return _join_report_lines(lines)


def _build_conversion_report(results, conversion_results, tool_path, options):
    """Summarize accepted outputs, skips, failures and per-book details."""
    lines = []
    lines.append("WebP Optimizer Conversion Report")
    lines.append("Generated: " + _safe_unicode(DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss")))
    lines.append("Archive Tool: " + _safe_unicode(tool_path))
    lines.append("Run Mode: " + _safe_unicode(options.get("run_mode", "")))
    lines.append("Quality Mode: " + _safe_unicode(options.get("quality_mode", "")))
    lines.append("Encoder Backend: " + _safe_unicode(options.get("encoder_backend", ENCODER_BACKEND_VALUES[0])))
    lines.append("Resize Mode: " + _safe_unicode(options.get("resize_mode", RESIZE_MODE_VALUES[0])))
    lines.append("CBR Handling: " + _safe_unicode(options.get("cbr_mode", "")))
    if _safe_unicode(options.get("rar_tool", "")):
        lines.append("RAR Tool: " + _safe_unicode(options.get("rar_tool", "")))
    lines.append("Create Backup: " + ("Yes" if bool(options.get("create_backup", False)) else "No"))
    lines.append("Size Policy: " + _safe_unicode(options.get("size_policy", SIZE_POLICY_VALUES[0])))
    lines.append("Checkpoint Storage: " + Path.Combine(REPORT_DIR, "Checkpoints"))
    lines.append("Concurrent Pages: " + _safe_unicode(options.get("page_workers", "1")))
    lines.append("PC Priority: " + _safe_unicode(options.get("resource_profile", "Normal")))
    lines.append("Prefetch Requested: " + ("Yes (local work folder required; 256 MB limit)" if options.get("prefetch") else "No"))
    lines.append("Prefetch Caches Used: " + str(len([r for r in conversion_results if r.get("PREFETCH_USED") == "Yes"])))
    lines.append("Prefetch Next Caches Prepared: " + str(len([r for r in conversion_results if r.get("PREFETCH_NEXT_READY") == "Yes"])))
    lines.append("Resumed Completed Books: " + str(_get_skip_reason_count(conversion_results, "RESUMED")))
    lines.append("Temporary Work Folder: " + (_safe_unicode(options.get("work_dir", "")) or "Beside each source"))
    lines.append("Reports Beside Sources: " + ("Yes" if options.get("reports_beside_sources", False) else "No"))
    lines.append("Books Scanned: " + str(len([r for r in results if r.get("status", "") != "Not processed"])))

    converted_count = 0
    skipped_count = 0
    failed_count = 0
    not_processed_count = 0
    total_source_size = 0L
    total_output_size = 0L

    for conversion_result in conversion_results:
        status = _safe_unicode(conversion_result.get("STATUS", ""))
        if status == "OK":
            converted_count += 1
            try:
                total_source_size += long(conversion_result.get("SOURCE_SIZE", "0"))
                total_output_size += long(conversion_result.get("OUTPUT_SIZE", "0"))
            except Exception:
                pass
        elif status == "NOT_PROCESSED":
            not_processed_count += 1
        elif status == "SKIPPED":
            skipped_count += 1
        else:
            failed_count += 1

    lines.append("Not Processed: " + str(not_processed_count))
    lines.append("Converted Books: " + str(converted_count))
    lines.append("Skipped: " + str(skipped_count))
    lines.append("Failed: " + str(failed_count))
    lines.append("Skipped By Size Policy: " + str(_get_skip_reason_count(conversion_results, "SIZE_POLICY")))
    lines.append("Skipped PNG-heavy: " + str(_get_skip_reason_count(conversion_results, "PNG_HEAVY")))
    lines.append("Skipped PNG-only: " + str(_get_skip_reason_count(conversion_results, "PNG_ONLY")))
    lines.append("Skipped CBR By Option: " + str(_get_skip_reason_count(conversion_results, "CBR_OPTION")))
    lines.append("Skipped Outside Benchmark Sample: " + str(_get_skip_reason_count(conversion_results, "BENCHMARK_LIMIT")))
    for key, label in [("TIME_SCAN_SECONDS", "Archive Scan Time"), ("TIME_EXTRACT_SECONDS", "Extraction Time"), ("TIME_ENCODE_SECONDS", "Encoding Time"), ("TIME_REBUILD_SECONDS", "Archive Rebuild Time"), ("TIME_VALIDATE_SECONDS", "Validation Time"), ("TIME_REPLACE_SECONDS", "Replacement Time")]:
        seconds = sum([float(item.get("scan_seconds", "0")) for item in results]) if key == "TIME_SCAN_SECONDS" else sum([float(item.get(key, "0")) for item in conversion_results])
        lines.append(label + ": {0:.1f} seconds".format(seconds))
    if total_source_size > 0:
        lines.append("Total Source Size: " + _format_size(total_source_size))
        lines.append("Total Output Size: " + _format_size(total_output_size))
        delta = total_source_size - total_output_size
        lines.append("Total Saved: " + (("-" if delta < 0 else "") + _format_size(abs(delta))))
        lines.append("Overall Reduction: {0:.2f}%".format(100.0 * (total_source_size - total_output_size) / total_source_size))
        lines.append("Savings Scope: Successfully converted books only; weighted by source bytes.")
        lines.append("Storage Note: Copy/benchmark modes and retained backups do not reclaim the reported savings from disk.")
        if converted_count > 0:
            lines.append("Average Saved Per Output: " + _format_size(long(max(0, total_source_size - total_output_size) / converted_count)))
    lines.append("")

    lines.append("Per-Book Conversion Results")
    lines.append("---------------------------")
    for index in range(len(results)):
        result = results[index]
        conversion_result = conversion_results[index]
        lines.append(_safe_unicode(result.get("caption", "")))
        lines.append("  Source: " + _safe_unicode(result.get("file_path", "")))
        lines.append("  Source ImageFormat: " + _safe_unicode(result.get("image_format", "")))
        lines.append("  Strategy: " + _safe_unicode(result.get("strategy", "")))
        lines.append("  Conversion Status: " + _safe_unicode(conversion_result.get("STATUS", "ERROR")))
        if conversion_result.get("OUTPUT_PATH", ""):
            lines.append("  Output: " + _safe_unicode(conversion_result.get("OUTPUT_PATH", "")))
        if conversion_result.get("BACKUP_PATH", ""):
            lines.append("  Backup: " + _safe_unicode(conversion_result.get("BACKUP_PATH", "")))
        if conversion_result.get("OUTPUT_IMAGE_FORMAT", ""):
            lines.append("  Output ImageFormat: " + _safe_unicode(conversion_result.get("OUTPUT_IMAGE_FORMAT", "")))
        if conversion_result.get("ENCODER_BACKEND_USED", ""):
            lines.append("  Encoder Backend Used: " + _safe_unicode(conversion_result.get("ENCODER_BACKEND_USED", "")))
        if conversion_result.get("RESIZE_APPLIED", ""):
            lines.append("  Resize Applied: " + _safe_unicode(conversion_result.get("RESIZE_APPLIED", "")))
        if conversion_result.get("CONVERTED_PAGES", "") or conversion_result.get("TOTAL_PAGES", ""):
            lines.append("  Pages Converted: {0}/{1}".format(_safe_unicode(conversion_result.get("CONVERTED_PAGES", "0")), _safe_unicode(conversion_result.get("TOTAL_PAGES", "0"))))
        if conversion_result.get("SOURCE_SIZE", "") and conversion_result.get("OUTPUT_SIZE", ""):
            lines.append("  Sizes: source={0}, output={1}".format(
                _format_size(conversion_result.get("SOURCE_SIZE", "0")),
                _format_size(conversion_result.get("OUTPUT_SIZE", "0"))))
        if conversion_result.get("SAVINGS_PERCENT", ""):
            lines.append("  Savings: " + _safe_unicode(conversion_result.get("SAVINGS_PERCENT", "0")) + "%")
        if conversion_result.get("COMICINFO_EMBEDDED", "") or conversion_result.get("COMICBOOK_EMBEDDED", ""):
            lines.append("  Embedded Metadata: ComicInfo={0}, ComicBook={1}".format(
                _safe_unicode(conversion_result.get("COMICINFO_EMBEDDED", "Unknown")),
                _safe_unicode(conversion_result.get("COMICBOOK_EMBEDDED", "Unknown"))))
        for key in sorted(conversion_result):
            if (key.startswith("TIME_") and key.endswith("_SECONDS")) or key.startswith("PREFETCH_"):
                lines.append("  " + key + ": " + _safe_unicode(conversion_result[key]))
        if conversion_result.get("CHECKPOINT_WARNING"):
            lines.append("  Checkpoint warning: " + _safe_unicode(conversion_result["CHECKPOINT_WARNING"]))
        message = _safe_unicode(conversion_result.get("MESSAGE", "")) or _safe_unicode(conversion_result.get("stderr", ""))
        if message:
            lines.append("  Notes: " + message)
        lines.append("")

    return _join_report_lines(lines)


# ===========================================================================
# [P10] Structured run history and legacy report discovery
# ===========================================================================
def _report_header(path):
    """Read a bounded legacy header instead of loading a potentially huge report."""
    reader = StreamReader(path, Encoding.UTF8, True)
    lines = []
    try:
        for index in range(100):
            line = reader.ReadLine()
            if line is None or (index > 0 and not line.strip()):
                break
            lines.append(_safe_unicode(line))
    finally:
        reader.Close()
    return dict(_extract_report_summary_items(_join_report_lines(lines)))


def _preview_state(folder, previous=""):
    """Derive availability from manifests/images; retain known removal state."""
    if not folder:
        return "-"
    try:
        if Directory.Exists(folder):
            for manifest in Directory.GetFiles(folder, "preview.xml", SearchOption.AllDirectories):
                document = XmlDocument()
                document.XmlResolver = None
                try:
                    document.Load(manifest)
                    for page in document.DocumentElement.SelectNodes("Page"):
                        original = _safe_unicode(page.GetAttribute("original"))
                        converted = _safe_unicode(page.GetAttribute("converted"))
                        if Path.GetFileName(original) == original and Path.GetFileName(converted) == converted and File.Exists(Path.Combine(Path.GetDirectoryName(manifest), original)) and File.Exists(Path.Combine(Path.GetDirectoryName(manifest), converted)):
                            return "Available"
                except Exception:
                    continue
            return "Unavailable"
        return "Removed" if previous == "Removed" else "Unavailable"
    except Exception:
        return "Unavailable"


def _save_run_record(report_path, text, options=None, results=None, preview_state=None):
    """Atomically update an XML sidecar, preserving options/sources on cleanup.

    The adjacent text report remains usable without this record. Personal
    source paths stay in Reports and must never enter a release archive."""
    record_path = Path.ChangeExtension(report_path, ".run.xml")
    document = XmlDocument()
    document.XmlResolver = None
    if File.Exists(record_path):
        try:
            document.Load(record_path)
            if document.DocumentElement.Name != "Run":
                raise Exception("Invalid run record")
        except Exception:
            document.RemoveAll()
    if document.DocumentElement is None:
        document.AppendChild(document.CreateElement("Run"))
    root = document.DocumentElement
    root.SetAttribute("version", "1")
    root.SetAttribute("report", Path.GetFileName(report_path))
    summary = dict(_extract_report_summary_items(text))
    root.SetAttribute("generated", summary.get("Generated", ""))
    root.SetAttribute("mode", summary.get("Run Mode", "Analyze Only"))
    status = summary.get("Run Status", "Completed")
    if summary.get("Failed", summary.get("Errors", "0")) != "0":
        status = "Stopped with failures" if "Stopped" in status else "Completed with failures"
    root.SetAttribute("status", status)
    root.SetAttribute("books", summary.get("Books Processed", summary.get("Books Scanned", "0")))
    reductions = " | ".join([q + " " + summary[q + " Reduction"] for q in TRIAL_QUALITY_LEVELS if q + " Reduction" in summary])
    root.SetAttribute("savings", reductions or summary.get("Overall Reduction", "Not recorded"))
    root.SetAttribute("previewFolder", summary.get("Preview Folder", ""))
    root.SetAttribute("previewState", preview_state or _preview_state(summary.get("Preview Folder", ""), _safe_unicode(root.GetAttribute("previewState"))))
    if options is not None:
        old = root.SelectSingleNode("Options")
        if old is not None:
            root.RemoveChild(old)
        parent = document.CreateElement("Options")
        root.AppendChild(parent)
        for key in ["quality_mode", "encoder_backend", "resize_mode", "cbr_mode", "size_policy", "work_dir", "reports_beside_sources", "page_workers"]:
            if key in options:
                node = document.CreateElement("Setting")
                node.SetAttribute("key", key)
                node.SetAttribute("value", _safe_unicode(options[key]))
                parent.AppendChild(node)
    if results is not None:
        old = root.SelectSingleNode("Sources")
        if old is not None:
            root.RemoveChild(old)
        parent = document.CreateElement("Sources")
        root.AppendChild(parent)
        for result in results:
            node = document.CreateElement("Book")
            node.SetAttribute("path", _safe_unicode(result.get("file_path", "")))
            node.SetAttribute("caption", _safe_unicode(result.get("caption", "")))
            parent.AppendChild(node)
    temporary = record_path + "." + System.Guid.NewGuid().ToString("N") + ".tmp"
    try:
        document.Save(temporary)
        if File.Exists(record_path):
            File.Replace(temporary, record_path, None)
        else:
            File.Move(temporary, record_path)
    finally:
        if File.Exists(temporary):
            File.Delete(temporary)


def _record_run_safely(report_path, text, options=None, results=None, preview_state=None):
    """Keep a history-write failure from discarding an already saved text report."""
    try:
        _save_run_record(report_path, text, options, results, preview_state)
    except Exception, ex:
        MessageBox.Show("The text report was saved, but its history record could not be updated: " + _safe_unicode(ex), "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Warning)


def _load_run_history():
    """List central text reports, preferring sidecars and tolerating legacy records."""
    if not Directory.Exists(REPORT_DIR):
        return []
    records = []
    for path in sorted(list(Directory.GetFiles(REPORT_DIR, "webp_*.txt")), reverse=True):
        record = {"path": path, "options": {}, "sources": []}
        try:
            document = XmlDocument()
            document.XmlResolver = None
            document.Load(Path.ChangeExtension(path, ".run.xml"))
            root = document.DocumentElement
            if root.Name != "Run":
                raise Exception("Invalid record")
            for key in ["generated", "mode", "status", "books", "savings", "previewFolder", "previewState"]:
                record[key] = _safe_unicode(root.GetAttribute(key))
            for node in root.SelectNodes("Options/Setting"):
                record["options"][_safe_unicode(node.GetAttribute("key"))] = _safe_unicode(node.GetAttribute("value"))
            record["sources"] = [_safe_unicode(node.GetAttribute("path")) for node in root.SelectNodes("Sources/Book")]
        except Exception:
            try:
                summary = _report_header(path)
                record.update({"generated": summary.get("Generated", ""), "mode": summary.get("Run Mode", "Analyze Only"), "status": summary.get("Run Status", "Legacy report"), "books": summary.get("Books Processed", summary.get("Books Scanned", "-")), "savings": summary.get("Overall Reduction", "Not recorded"), "previewFolder": summary.get("Preview Folder", ""), "previewState": ""})
                if summary.get("Failed", summary.get("Errors", "0")) != "0":
                    record["status"] += " - failures"
                reductions = " | ".join([q + " " + summary[q + " Reduction"] for q in TRIAL_QUALITY_LEVELS if q + " Reduction" in summary])
                record["savings"] = reductions or record["savings"]
                record["options"] = dict([(target, summary[key]) for key, target in [("Encoder Backend", "encoder_backend"), ("Resize Mode", "resize_mode"), ("CBR Handling", "cbr_mode")] if key in summary])
            except Exception:
                record.update({"generated": Path.GetFileName(path), "mode": "Unreadable report", "status": "Unavailable", "books": "-", "savings": "-", "previewFolder": "", "previewState": ""})
        record["previewState"] = _preview_state(record.get("previewFolder", ""), record.get("previewState", ""))
        records.append(record)
    return records


# ===========================================================================
# [P11] Preview retention, persisted settings and run summaries
# ===========================================================================
def _delete_trial_previews(folder):
    """Delete exactly one generated GUID run under Reports/QualityTests.

    Reject parent/outside paths and reparse points before recursive deletion.
    This function must never accept a comic source folder as a cleanup target."""
    # Delete only one generated run directly inside this plugin's preview root.
    root = Path.GetFullPath(Path.Combine(REPORT_DIR, "QualityTests")).rstrip("\\/")
    target = Path.GetFullPath(folder).rstrip("\\/")
    leaf = Path.GetFileName(target)
    if Path.GetDirectoryName(target).lower() != root.lower() or len(leaf) != 32 or any([c not in "0123456789abcdefABCDEF" for c in leaf]):
        raise Exception("Refusing preview cleanup outside a generated QualityTests run: " + target)
    if not Directory.Exists(target):
        return
    if Directory.Exists(REPORT_DIR) and (File.GetAttributes(REPORT_DIR) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
        raise Exception("Reports folder is redirected; preview cleanup refused.")
    # Refuse junctions/symlinks instead of traversing redirected folders.
    pending = [target]
    if Directory.Exists(root) and (File.GetAttributes(root) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
        raise Exception("Preview root is a redirected folder; cleanup refused.")
    while pending:
        current = pending.pop()
        if (File.GetAttributes(current) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
            raise Exception("Preview run contains a redirected folder; cleanup refused.")
        for child in Directory.GetDirectories(current):
            pending.append(child)
        for child in Directory.GetFiles(current):
            if (File.GetAttributes(child) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
                raise Exception("Preview run contains a redirected file; cleanup refused.")
    Directory.Delete(target, True)


def _load_settings():
    """Read optional settings XML; corrupt/unknown content falls back in the UI."""
    if not File.Exists(SETTINGS_PATH):
        return {}, ""
    try:
        document = XmlDocument()
        document.XmlResolver = None
        document.Load(SETTINGS_PATH)
        if document.DocumentElement.Name != "WebPOptimizerSettings":
            raise Exception("Unexpected settings format")
        values = {}
        for node in document.DocumentElement.SelectNodes("Setting"):
            values[_safe_unicode(node.GetAttribute("key"))] = _safe_unicode(node.GetAttribute("value"))
        return values, ""
    except Exception, ex:
        return {}, "Saved settings could not be read; using defaults. " + _safe_unicode(ex)


def _save_settings(values):
    """Persist choices through a temporary XML file and same-path replacement."""
    document = XmlDocument()
    root = document.CreateElement("WebPOptimizerSettings")
    root.SetAttribute("version", "1")
    document.AppendChild(root)
    for key, value in values.items():
        node = document.CreateElement("Setting")
        node.SetAttribute("key", key)
        node.SetAttribute("value", _safe_unicode(value))
        root.AppendChild(node)
    temporary = SETTINGS_PATH + "." + System.Guid.NewGuid().ToString("N") + ".tmp"
    try:
        document.Save(temporary)
        if File.Exists(SETTINGS_PATH):
            File.Replace(temporary, SETTINGS_PATH, None)
        else:
            File.Move(temporary, SETTINGS_PATH)
    finally:
        if File.Exists(temporary):
            File.Delete(temporary)


def _unprocessed_book(book):
    """Represent an untouched book when a stop prevents its scan/conversion."""
    return {"caption": _safe_unicode(getattr(book, "Caption", "")), "file_path": _safe_unicode(getattr(book, "FilePath", "")), "status": "Not processed", "image_format": "", "notes": "Run stopped before this book was processed."}


def _run_report_status(text, selected, processed, stopped):
    """Insert selected/processed counts without duplicating Not Processed fields."""
    lines = text.splitlines()
    at = lines.index("") if "" in lines else len(lines)
    lines = [line for line in lines if not line.startswith("Not Processed: ")]
    at = lines.index("") if "" in lines else len(lines)
    lines[at:at] = ["Run Status: " + ("Stopped by user" if stopped else "Completed"), "Books Selected: " + str(selected), "Books Processed: " + str(processed), "Not Processed: " + str(selected - processed)]
    return _join_report_lines(lines)


def _copy_reports_to_sources(report_text, report_path, results, options):
    """Optionally copy the full report to distinct source folders without overwrite."""
    if not options.get("reports_beside_sources", False):
        return report_text
    folders = set([Path.GetDirectoryName(_safe_unicode(r.get("file_path", ""))) for r in results if r.get("file_path", "")])
    warnings = []
    for folder in folders:
        try:
            target = Path.Combine(folder, Path.GetFileName(report_path))
            if Path.GetFullPath(target).lower() != Path.GetFullPath(report_path).lower():
                File.Copy(report_path, target, False)
        except Exception, ex:
            warnings.append("Could not save report beside source: " + folder + " - " + _safe_unicode(ex))
    if warnings:
        report_text += "\r\nReport storage warnings\r\n" + "\r\n".join(warnings)
        _write_text_file(report_path, report_text)
    return report_text


# ===========================================================================
# [P12] Shared native UI construction helpers
# ===========================================================================
def _ui_label(parent, text, x, y, width, height=24, heading=False):
    """Build a consistently styled WinForms label and attach it to its parent."""
    label = Label()
    label.Text = text
    label.Location = Point(x, y)
    label.Size = Size(width, height)
    label.Font = Font("Segoe UI", 12.0 if heading else 9.0, FontStyle.Bold if heading else FontStyle.Regular)
    label.ForeColor = Color.FromArgb(26, 71, 74) if heading else Color.FromArgb(48, 57, 63)
    parent.Controls.Add(label)
    return label


def _ui_combo(parent, title, values, y):
    """Build an anchored, selection-only options dropdown."""
    _ui_label(parent, title, 24, y + 4, 172)
    combo = _new_combo()
    combo.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList
    combo.Items.AddRange(System.Array[System.Object](values))
    combo.SelectedIndex = 0
    combo.Location = Point(204, y)
    combo.Size = Size(490, 28)
    combo.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
    parent.Controls.Add(combo)
    return combo


# ===========================================================================
# [P13] Options UI and remembered settings
# ===========================================================================
class OptionsForm(Form):
    """User choices and history access; save preferences only when starting a run."""
    def __init__(self):
        self._history_opening = False
        self._selection_books = []
        self.Text = "WebP Optimizer"
        self.Font = Font("Segoe UI", 9.0)
        self.AutoScaleMode = AutoScaleMode.Font
        self.ClientSize = Size(760, 670)
        self.MinimumSize = Size(776, 709)
        self.StartPosition = FormStartPosition.CenterParent
        self.BackColor = Color.White
        _ui_label(self, "Make room for more comics.", 24, 18, 700, 34, True)
        _ui_label(self, "Choose your workflow, then tune quality and storage. Only selected books are processed.", 24, 56, 700, 30)
        self._tabs = _new_tabs()
        self._tabs.Location = Point(16, 96)
        self._tabs.Size = Size(728, 508)
        self._tabs.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
        self.Controls.Add(self._tabs)
        basic = TabPage("Workflow & quality")
        advanced = TabPage("Storage & advanced")
        performance = TabPage("Performance & resume")
        tools_page = TabPage("Tools & recovery")
        for page in [basic, advanced, performance, tools_page]:
            page.Size = Size(720, 480)
            page.BackColor = Color.White
            page.AutoScroll = True
            self._tabs.TabPages.Add(page)
        self._mode_combo = _ui_combo(basic, "Action", RUN_MODE_VALUES, 24)
        self._quality_combo = _ui_combo(basic, "Encoder quality level", QUALITY_MODE_VALUES, 80)
        self._quality_note = _ui_label(basic, "", 204, 120, 480, 85)
        self._resize_combo = _ui_combo(basic, "Page dimensions", RESIZE_MODE_VALUES, 218)
        self._size_policy_combo = _ui_combo(basic, "Keep converted result", SIZE_POLICY_VALUES, 272)
        self._backup_checkbox = _new_checkbox()
        self._backup_checkbox.Text = "Keep an original backup after replacement"
        self._backup_checkbox.Checked = True
        self._backup_checkbox.Location = Point(204, 326)
        self._backup_checkbox.Size = Size(490, 26)
        basic.Controls.Add(self._backup_checkbox)
        self._preview_checkbox = _new_checkbox()
        self._preview_checkbox.Text = "Keep preview pages for visual comparison (uses extra space)"
        self._preview_checkbox.Location = Point(204, 326)
        self._preview_checkbox.Size = Size(490, 32)
        basic.Controls.Add(self._preview_checkbox)
        self._action_note = _ui_label(basic, "", 24, 372, 660, 82)
        self._encoder_combo = _ui_combo(advanced, "Encoder", ENCODER_BACKEND_VALUES, 24)
        self._cbr_combo = _ui_combo(advanced, "CBR output", CBR_MODE_VALUES, 78)
        _ui_label(advanced, "Temporary storage", 24, 138, 650, 28, True)
        self._work_text = TextBox()
        self._work_text.Location = Point(24, 178)
        self._work_text.Size = Size(558, 26)
        self._work_text.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right
        advanced.Controls.Add(self._work_text)
        browse = Button()
        browse.Text = "Browse..."
        browse.Location = Point(594, 176)
        browse.Size = Size(100, 30)
        browse.Anchor = AnchorStyles.Top | AnchorStyles.Right
        browse.Click += self._browse_work
        advanced.Controls.Add(browse)
        _ui_label(advanced, "Leave blank to work beside each source. Choose a local folder for extraction and encoding. Final archives stay beside their source.", 24, 216, 660, 52)
        _ui_label(advanced, "Run reports", 24, 290, 650, 28, True)
        self._reports_checkbox = _new_checkbox()
        self._reports_checkbox.Text = "Also save this run's report beside the selected source files"
        self._reports_checkbox.Location = Point(24, 330)
        self._reports_checkbox.Size = Size(660, 28)
        advanced.Controls.Add(self._reports_checkbox)
        _ui_label(advanced, "A full report is copied to each distinct source folder. A central copy is always kept in the plugin's Reports folder, including benchmark runs.", 24, 368, 660, 58)
        self._workers_combo = _ui_combo(performance, "Concurrent pages", ["1", "2", "4", "6", "8", "10", "12"], 24)
        self._profile_combo = _ui_combo(performance, "PC priority", ["Normal", "Background"], 68)
        _ui_label(performance, "More workers use more RAM. Background lowers CPU priority; it does not limit disk/network traffic. Books still finish one at a time.", 24, 110, 660, 42)
        benchmark = Button()
        benchmark.Text = "Benchmark worker counts"
        benchmark.Location, benchmark.Size = Point(24, 160), Size(220, 34)
        benchmark.Click += self._show_performance
        performance.Controls.Add(benchmark)
        _ui_label(performance, "Tests 1, 2, 4, 6, 8, 10 and 12 at the chosen quality on up to 3 JPEG books. Temporary outputs are deleted; originals and library tags stay unchanged.", 260, 158, 424, 48)
        self._prefetch_checkbox = _new_checkbox()
        self._prefetch_checkbox.Text = "Prefetch one next archive into local temporary storage (up to 256 MB)"
        self._prefetch_checkbox.Location, self._prefetch_checkbox.Size = Point(24, 222), Size(660, 30)
        performance.Controls.Add(self._prefetch_checkbox)
        _ui_label(performance, "Optional; requires a local temporary folder. Adds read traffic during encoding. Larger books use normal processing. Disable if the source drive is busy.", 24, 258, 660, 44)
        self._resume_checkbox = _new_checkbox()
        self._resume_checkbox.Text = "Resume completed books with matching settings and unchanged files"
        self._resume_checkbox.Location, self._resume_checkbox.Size = Point(24, 320), Size(660, 30)
        performance.Controls.Add(self._resume_checkbox)
        _ui_label(performance, "Select the original batch again to resume. Pending outputs need review. Worker count, priority and temporary storage do not invalidate completed work.", 24, 358, 660, 42)
        self._awake_checkbox = _new_checkbox()
        self._awake_checkbox.Text = "Keep PC awake while processing (the screen may turn off)"
        self._awake_checkbox.Location, self._awake_checkbox.Size = Point(24, 424), Size(660, 36)
        performance.Controls.Add(self._awake_checkbox)
        _ui_label(tools_page, "Check your setup", 24, 24, 660, 30, True)
        _ui_label(tools_page, "Check the selected workflow's tools and temporary storage using disposable files. Choose a conversion action to check Python, Pillow and the encoder.", 24, 70, 660, 66)
        check_setup = Button()
        check_setup.Text = "Check setup"
        check_setup.Location, check_setup.Size = Point(24, 144), Size(180, 34)
        check_setup.Click += self._show_setup
        tools_page.Controls.Add(check_setup)
        _ui_label(tools_page, "Interrupted work", 24, 230, 660, 30, True)
        _ui_label(tools_page, "Review pending attempts, check source/output readability and open their folders. Allow retry only after the files are resolved and the prior helper has stopped.", 24, 274, 660, 74)
        recovery = Button()
        recovery.Text = "Review interrupted work"
        recovery.Location, recovery.Size = Point(24, 364), Size(230, 34)
        recovery.Click += self._show_recovery
        tools_page.Controls.Add(recovery)
        self._dark_checkbox = _new_checkbox()
        self._dark_checkbox.Text = "Dark mode"
        self._dark_checkbox.Location, self._dark_checkbox.Size = Point(24, 444), Size(660, 30)
        self._dark_checkbox.CheckedChanged += self._theme_changed
        tools_page.Controls.Add(self._dark_checkbox)
        self._settings_note = _ui_label(advanced, "", 24, 430, 660, 44)
        reset = Button()
        reset.Text = "Restore defaults"
        reset.Location = Point(24, 622)
        reset.Size = Size(140, 32)
        reset.Anchor = AnchorStyles.Bottom | AnchorStyles.Left
        reset.Click += self._reset_settings
        self.Controls.Add(reset)
        history = Button()
        history.Text = "Run history"
        history.Location = Point(176, 622)
        history.Size = Size(130, 32)
        history.Anchor = AnchorStyles.Bottom | AnchorStyles.Left
        history.Click += self._show_history
        self.Controls.Add(history)
        self._ok_button = Button()
        self._ok_button.Location = Point(510, 622)
        self._ok_button.Size = Size(110, 32)
        self._ok_button.Anchor = AnchorStyles.Bottom | AnchorStyles.Right
        self._ok_button.Click += self._save
        self._ok_button.BackColor = Color.FromArgb(26, 71, 74)
        self._ok_button.ForeColor = Color.White
        self._cancel_button = Button()
        self._cancel_button.Text = "Cancel"
        self._cancel_button.Location = Point(632, 622)
        self._cancel_button.Size = Size(110, 32)
        self._cancel_button.Anchor = AnchorStyles.Bottom | AnchorStyles.Right
        self._cancel_button.Click += self._cancel
        self.Controls.Add(self._ok_button)
        self.Controls.Add(self._cancel_button)
        self.AcceptButton = self._ok_button
        self.CancelButton = self._cancel_button
        self._mode_combo.SelectedIndexChanged += self._mode_changed
        self._quality_combo.SelectedIndexChanged += self._mode_changed
        self._encoder_combo.SelectedIndexChanged += self._mode_changed
        self._resize_combo.SelectedIndexChanged += self._mode_changed
        self._restore_settings()
        self._apply_mode_state()

    def _restore_settings(self, defaults=False):
        values, warning = ({}, "") if defaults else _load_settings()
        migrated_encoder = values.get("encoder_backend", "") in ["Auto (Prefer ImageMagick / CBX-style)", "ImageMagick (CBX-style)", "ImageMagick (Tuned)"]
        if values.get("run_mode", "") == "Benchmark Sample (First 3 Eligible)":
            values["run_mode"] = "Test savings & quality"
        if migrated_encoder:
            values["encoder_backend"] = ENCODER_BACKEND_VALUES[0]
        for key, control in [("run_mode", self._mode_combo), ("quality_mode", self._quality_combo), ("encoder_backend", self._encoder_combo), ("resize_mode", self._resize_combo), ("cbr_mode", self._cbr_combo), ("size_policy", self._size_policy_combo), ("page_workers", self._workers_combo), ("resource_profile", self._profile_combo)]:
            control.SelectedIndex = 0
            if values.get(key, "") in list(control.Items):
                control.SelectedItem = values[key]
        self._prefetch_checkbox.Checked = values.get("prefetch", "False").lower() == "true"
        self._dark_checkbox.Checked = values.get("dark_mode", "False").lower() == "true"
        self._awake_checkbox.Checked = values.get("keep_awake", "False").lower() == "true"
        self._resume_checkbox.Checked = values.get("resume_completed", "True").lower() == "true"
        self._backup_checkbox.Checked = values.get("create_backup", "True").lower() == "true"
        self._preview_checkbox.Checked = values.get("keep_test_previews", "False").lower() == "true"
        self._reports_checkbox.Checked = values.get("reports_beside_sources", "False").lower() == "true"
        self._work_text.Text = values.get("work_dir", "")
        self._settings_note.Text = warning or ("Previous encoder choice updated to explicit ImageMagick. No automatic fallback. Settings save when you start a run." if migrated_encoder else "Settings are remembered when you start a run. Selected encoders never fall back automatically.")

    def _theme_changed(self, sender, event):
        _set_ui_theme(bool(self._dark_checkbox.Checked), self)

    def _reset_settings(self, sender, event):
        self._restore_settings(True)
        self._apply_mode_state()

    def _show_performance(self, sender, event):
        # Dispose options first, just as history does; avoid nested modal stacks.
        self.DialogResult = DialogResult.Yes
        self.Close()

    def _show_history(self, sender, event):
        """Return to the controller before opening history: never nest this dialog."""
        if self._history_opening:
            return
        self._history_opening = True
        _history_trace("History requested; closing options before opening history")
        self.DialogResult = DialogResult.Retry
        self.Close()

    def _restore_draft(self, values):
        """Restore unsaved choices when returning from history, without writing settings."""
        for key, control in [("run_mode", self._mode_combo), ("quality_mode", self._quality_combo), ("encoder_backend", self._encoder_combo), ("resize_mode", self._resize_combo), ("cbr_mode", self._cbr_combo), ("size_policy", self._size_policy_combo), ("page_workers", self._workers_combo), ("resource_profile", self._profile_combo)]:
            if values.get(key, "") in list(control.Items):
                control.SelectedItem = values[key]
        for key, control in [("create_backup", self._backup_checkbox), ("keep_test_previews", self._preview_checkbox), ("reports_beside_sources", self._reports_checkbox), ("resume_completed", self._resume_checkbox), ("keep_awake", self._awake_checkbox), ("dark_mode", self._dark_checkbox), ("prefetch", self._prefetch_checkbox)]:
            if key in values:
                control.Checked = bool(values[key])
        self._work_text.Text = values.get("work_dir", "")
        self._apply_mode_state()
        _set_ui_theme(bool(self._dark_checkbox.Checked), self)

    def _browse_work(self, sender, event):
        dialog = FolderBrowserDialog()
        dialog.Description = "Temporary extraction and conversion storage"
        if dialog.ShowDialog() == DialogResult.OK:
            self._work_text.Text = dialog.SelectedPath
        dialog.Dispose()

    def _apply_mode_state(self):
        mode = _safe_unicode(self._mode_combo.SelectedItem)
        analyze = mode == "Analyze Only"
        trial = mode == "Test savings & quality"
        for control in [self._quality_combo, self._resize_combo, self._size_policy_combo, self._encoder_combo, self._cbr_combo, self._work_text]:
            control.Enabled = not analyze
        self._workers_combo.Enabled = not analyze
        self._resume_checkbox.Enabled = not analyze and not trial
        self._quality_combo.Enabled = not analyze and not trial
        self._size_policy_combo.Enabled = not analyze and not trial
        self._resize_combo.Enabled = not analyze and not trial
        self._backup_checkbox.Visible = not trial
        self._preview_checkbox.Visible = trial
        self._backup_checkbox.Enabled = mode == "Replace Originals"
        self._ok_button.Text = "Analyze" if analyze else "Start run"
        notes = {"Analyze Only": "Inspect selected archives and update ImageFormat for smart lists. No comic files are converted.", "Create WebP Copies": "Keep the original and create a separate WebP archive. The existing library entry continues to point to the original; no disk space is reclaimed.", "Replace Originals": "Validate the new archive before replacing the source. Uncheck backup to avoid a permanent duplicate. Temporary working space is still required.", "Test savings & quality": "Compare Q60, Q70, Q75, Q80 and Q90 on up to 3 eligible books spaced through your selection, with no resize. Five full conversions per sampled book take extra time. Trial archives are deleted; originals stay unchanged."}
        self._action_note.Text = notes.get(mode, "")
        quality = _safe_unicode(self._quality_combo.SelectedItem)
        key = "Lossless" if quality == "Lossless" else quality.split(" ")[0].lstrip("Q")
        estimate = "Sample estimate not available yet."
        try:
            for line in File.ReadAllLines(Path.Combine(SCRIPT_DIR, "quality_estimates.txt")):
                fields = _safe_unicode(line).split("|")
                if fields[0] == key and len(fields) == 4:
                    measured = float(fields[1])
                    change = fields[1] + "% reduction" if measured >= 0 else str(abs(measured)) + "% larger"
                    estimate = "Measured sample: " + change + " combined (page reduction range " + fields[2] + "% to " + fields[3] + "%)."
        except Exception:
            pass
        if not _safe_unicode(self._encoder_combo.SelectedItem) in [ENCODER_BACKEND_VALUES[0]] or _safe_unicode(self._resize_combo.SelectedItem) != "No Resize":
            estimate = "Sample estimate unavailable for this encoder/resize combination."
        self._quality_note.Text = ("This test compares Q60, Q70, Q75, Q80 and Q90 at original dimensions. The report shows actual results for this small sample, not a prediction for your whole collection." if trial else estimate + "\nBased on bundled JPEG page samples, ImageMagick, no resize. Actual book savings vary. Q is an encoder level, not a percentage.")

    def _mode_changed(self, sender, event):
        self._apply_mode_state()

    def _collect_options(self):
        """Read controls without saving settings or starting a run."""
        return {
            "run_mode": _safe_unicode(self._mode_combo.SelectedItem),
            "quality_mode": _safe_unicode(self._quality_combo.SelectedItem),
            "encoder_backend": _safe_unicode(self._encoder_combo.SelectedItem),
            "resize_mode": _safe_unicode(self._resize_combo.SelectedItem),
            "cbr_mode": _safe_unicode(self._cbr_combo.SelectedItem),
            "create_backup": self._backup_checkbox.Enabled and bool(self._backup_checkbox.Checked),
            "size_policy": _safe_unicode(self._size_policy_combo.SelectedItem),
            "work_dir": _safe_unicode(self._work_text.Text).strip(),
            "reports_beside_sources": bool(self._reports_checkbox.Checked),
            "keep_test_previews": bool(self._preview_checkbox.Checked),
            "page_workers": _safe_unicode(self._workers_combo.SelectedItem),
            "resource_profile": _safe_unicode(self._profile_combo.SelectedItem),
            "prefetch": bool(self._prefetch_checkbox.Checked),
            "dark_mode": bool(self._dark_checkbox.Checked),
            "keep_awake": bool(self._awake_checkbox.Checked),
            "resume_completed": bool(self._resume_checkbox.Checked),
        }

    def _show_setup(self, sender, event):
        options = self._collect_options()
        if self._selection_books and not options.get("work_dir"):
            options["_setup_default_work_dir"] = Path.GetDirectoryName(_safe_unicode(getattr(self._selection_books[0], "FilePath", "")))
        form = SetupForm(options)
        try:
            _show_owned_dialog(form, self)
        finally:
            form.Dispose()

    def _show_recovery(self, sender, event):
        form = RecoveryForm(self._selection_books)
        try:
            _show_owned_dialog(form, self)
        finally:
            form.Dispose()

    def _save(self, sender, event):
        self.options = self._collect_options()
        self.options["_show_preflight"] = True
        remembered = dict(_load_settings()[0])
        remembered.update(dict((key, value) for key, value in self.options.items() if not key.startswith("_")))
        remembered["create_backup"] = bool(self._backup_checkbox.Checked)
        try:
            _save_settings(remembered)
        except Exception, ex:
            MessageBox.Show("This run can continue, but settings could not be saved: " + _safe_unicode(ex), "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        self.DialogResult = DialogResult.OK
        self.Close()

    def _cancel(self, sender, event):
        _set_ui_theme(_load_settings()[0].get("dark_mode", "False").lower() == "true", self)
        self.DialogResult = DialogResult.Cancel
        self.Close()


# ===========================================================================
# [P14] Progress UI and safe stop requests
# ===========================================================================
class ProgressForm(Form):
    """UI-thread progress, elapsed time and a deferred active-book stop request."""
    def __init__(self):
        self.stop_requested = False
        self._finished = False
        self._completed = 0
        self._total = 0
        self._unit = "books processed"
        self._work_bytes = 0.0
        self._work_seconds = 0.0
        self._work_books = 0
        self._batch_sizes = []
        self._batch_prefix = [0]
        self._quality_sizes = []
        self._quality_completed = 0
        self._active_started = 0.0
        self._clock = Stopwatch.StartNew()
        self.Font = Font("Segoe UI", 9.0)
        self.AutoScaleMode = AutoScaleMode.Font
        self.BackColor = Color.White
        self.Text = "WebP Optimizer - Processing selection"
        self.ClientSize = Size(700, 414)
        self.FormBorderStyle = FormBorderStyle.FixedDialog
        self.StartPosition = FormStartPosition.CenterParent
        self.MinimizeBox = True
        self.MaximizeBox = False
        self._status_label = _ui_label(self, "Preparing your selection", 24, 22, 650, 34, True)
        self._detail_label = _ui_label(self, "", 24, 68, 650, 48)
        self._detail_label.AutoEllipsis = True
        self._stage_label = _ui_label(self, "", 24, 120, 650, 24)
        self._count_label = _ui_label(self, "", 24, 150, 650, 26)
        self._progress_bar = ProgressBar()
        self._progress_bar.Location = Point(24, 188)
        self._progress_bar.Size = Size(650, 18)
        self.Controls.Add(self._progress_bar)
        self._time_label = _ui_label(self, "Elapsed 00:00", 24, 224, 650, 26)
        self._rate_label = _ui_label(self, "Speed and rough ETA appear after the first converted book.", 24, 256, 650, 42)
        self._stop_note = _ui_label(self, "Stopping finishes the active book, including validation and replacement. Remaining books stay untouched.", 24, 304, 650, 42)
        self._stop_button = Button()
        self._stop_button.Text = "Stop after current book"
        self._stop_button.Location = Point(450, 366)
        self._stop_button.Size = Size(224, 32)
        self._stop_button.Click += self._request_stop
        self.Controls.Add(self._stop_button)
        self.FormClosing += self._closing
        self.FormClosed += self._closed
        self._timer = Timer()
        self._timer.Interval = 1000
        self._timer.Tick += self._tick
        self._timer.Start()

    def _request_stop(self, sender, event):
        self.stop_requested = True
        self._stop_button.Enabled = False
        self._stop_button.Text = "Stop requested"
        self._stop_note.Text = "Stop requested. Finishing the active book safely, then saving a partial-run report."

    def _closing(self, sender, event):
        if not self._finished:
            event.Cancel = True
            self._request_stop(sender, event)

    def _closed(self, sender, event):
        self._timer.Stop()
        self._timer.Dispose()
        self._clock.Stop()

    def finish(self):
        self._finished = True
        self.Close()

    def set_batch(self, books):
        """Use ComicRack's cached sizes; do not stat an entire NAS before starting."""
        self._batch_sizes = []
        self._batch_prefix = [0]
        for book in books:
            try:
                self._batch_sizes.append(max(0, long(getattr(book, "FileSize", 0))))
            except Exception:
                self._batch_sizes.append(0)
            self._batch_prefix.append(self._batch_prefix[-1] + self._batch_sizes[-1])

    def record_work(self, result):
        """Estimate from completed real conversions, never quick skips or resumed work."""
        if result.get("STATUS") != "OK":
            return
        seconds = float(result.get("TIME_WORKER_SECONDS", result.get("TIME_TOTAL_SECONDS", "0"))) + float(result.get("TIME_REPLACE_SECONDS", "0"))
        if seconds <= 0:
            return
        self._work_bytes += float(result.get("SOURCE_SIZE", "0"))
        self._work_seconds += seconds
        self._work_books += 1
        self._completed += 1
        self._active_started = self._clock.Elapsed.TotalSeconds
        self._update_batch_percent(self._completed)
        self._tick(None, None)

    def set_quality_batch(self, sampled_results):
        """Plan five full passes per sampled book, independently of selection size."""
        self._quality_sizes = [max(0, long(result.get("file_size", 0))) for result in sampled_results for quality in TRIAL_QUALITY_LEVELS]
        self._quality_completed = 0
        self._rate_label.Text = "Quality-test speed and rough ETA appear after the first successful quality pass."

    def begin_quality_pass(self, quality):
        """Start a fresh countdown for the active pass without altering safe-stop rules."""
        self._active_started = self._clock.Elapsed.TotalSeconds
        self._status_label.Text = "Testing " + quality + " - conversion and validation"

    def record_quality_pass(self, result):
        """Feed timing after every attempted pass; five passes are one safe-stop book."""
        if not self._quality_sizes:
            return
        self._quality_completed += 1
        seconds = float(result.get("SECONDS", "0"))
        if result.get("STATUS") == "OK" and seconds > 0:
            self._work_seconds += seconds
            self._work_bytes += float(result.get("SOURCE_SIZE", "0"))
            self._work_books += 1
        self._active_started = self._clock.Elapsed.TotalSeconds
        self._progress_bar.Value = min(100, 45 + int(55.0 * self._quality_completed / len(self._quality_sizes)))
        self._count_label.Text = "{0} of {1} quality passes complete | {2}% of scan/test phases".format(self._quality_completed, len(self._quality_sizes), self._progress_bar.Value)
        self._tick(None, None)
        self.Refresh()
        Application.DoEvents()

    def _update_batch_percent(self, completed):
        """Weight progress by cached source bytes when every size is known."""
        if not self._total:
            return
        if self._batch_sizes and all([size > 0 for size in self._batch_sizes]):
            percent = int(100.0 * self._batch_prefix[min(completed, len(self._batch_sizes))] / self._batch_prefix[-1])
            basis = "source bytes"
        else:
            percent = int(100.0 * completed / self._total)
            basis = "books"
        self._progress_bar.Value = max(0, min(100, percent))
        self._count_label.Text = "Book {0} of {1} | {2}% complete ({3})".format(min(completed + 1, self._total), self._total, self._progress_bar.Value, basis)

    def _tick(self, sender, event):
        elapsed = int(self._clock.Elapsed.TotalSeconds)
        self._time_label.Text = "Elapsed {0:02d}:{1:02d}  |  {2} {3}".format(elapsed // 60, elapsed % 60, self._completed, self._unit)
        if self._quality_sizes:
            self._time_label.Text = "Elapsed {0:02d}:{1:02d} | {2}/{3} quality passes finished".format(elapsed // 60, elapsed % 60, self._quality_completed, len(self._quality_sizes))
            if self._work_books and self._work_seconds > 0:
                remaining = self._quality_sizes[self._quality_completed:]
                rate = self._work_bytes / self._work_seconds
                seconds = sum(remaining) / rate if rate > 0 and all([size > 0 for size in remaining]) else len(remaining) * self._work_seconds / self._work_books
                seconds = max(0, seconds - max(0, self._clock.Elapsed.TotalSeconds - self._active_started))
                minutes = int(seconds / 60)
                self._rate_label.Text = "Test speed {0:.2f} source MB/s per quality pass | Rough ETA {1}h {2:02d}m for remaining test passes.".format(rate / (1024 * 1024), minutes // 60, minutes % 60)
            return
        if self._batch_sizes and self._work_seconds > 0 and self._work_bytes > 0:
            remaining = self._batch_sizes[self._completed:]
            rate = self._work_bytes / self._work_seconds
            if all([size > 0 for size in remaining]):
                seconds = sum(remaining) / rate
                basis = "source bytes"
            else:
                seconds = len(remaining) * self._work_seconds / self._work_books
                basis = "book count; sizes unavailable"
            if self._unit == "books processed" and self._completed < self._total:
                seconds = max(0, seconds - max(0, self._clock.Elapsed.TotalSeconds - self._active_started))
            minutes = int(seconds / 60)
            self._rate_label.Text = "{0:.2f} source MB/s | Rough ETA {1}h {2:02d}m ({3}). Skips and book complexity affect estimates.".format(rate / (1024 * 1024), minutes // 60, minutes % 60, basis)

    def update_archive_progress(self, message):
        """Apply worker records on the UI thread; never change batch/quality counts."""
        parts = message.split("|")
        if len(parts) != 3:
            return
        try:
            completed, total = int(parts[1]), int(parts[2])
        except ValueError:
            return
        labels = {"EXTRACTING": "Extracting archive", "ENCODING": "Encoding pages", "REBUILDING": "Building converted archive", "VALIDATING": "Validating archive and pages", "CLEANUP": "Cleaning temporary files", "REPLACING": "Replacing original and updating library"}
        if parts[0] not in labels:
            return
        text = labels[parts[0]]
        if parts[0] == "ENCODING" and total > 0:
            text = "Encoding page {0} of {1}".format(max(0, min(completed, total)), total)
        self._stage_label.Text = text
        self.Refresh()

    def update_state(self, percent, status_text, detail_text, current=0, total=0, completed=0):
        if current != self._completed + 1 or status_text.startswith("Converting"):
            self._active_started = self._clock.Elapsed.TotalSeconds
        self._completed = completed
        self._total = total
        self._unit = "books scanned" if "Scanning" in status_text else "books processed"
        self._progress_bar.Value = max(0, min(100, int(percent)))
        self._stage_label.Text = "Reading archive listing" if "Scanning" in status_text else "Preparing this book"
        self._status_label.Text = _safe_unicode(status_text)
        self._detail_label.Text = _safe_unicode(detail_text)
        self._count_label.Text = "Book {0} of {1}  |  {2}% of batch complete".format(current, total, self._progress_bar.Value)
        if self._quality_sizes:
            self._progress_bar.Value = min(100, 45 + int(55.0 * self._quality_completed / len(self._quality_sizes)))
            self._count_label.Text = "{0} of {1} quality passes complete | {2}% of scan/test phases".format(self._quality_completed, len(self._quality_sizes), self._progress_bar.Value)
        elif self._batch_sizes:
            self._update_batch_percent(completed)
        self._tick(None, None)
        self.Refresh()
        Application.DoEvents()


# ===========================================================================
# [P15] Native comparison, color management, scrolling and zoom
# ===========================================================================
class PreviewScrollPanel(Panel):
    """Route wheel input explicitly so both comparison panes remain synchronized."""
    def __init__(self):
        Panel.__init__(self)
        self.wheel_handler = None
        self.SetStyle(ControlStyles.Selectable, True)
        self.TabStop = True

    def OnMouseWheel(self, event):
        # Handle scrolling ourselves: Panel's native wheel path does not emit
        # the same Scroll events as dragging its scrollbars.
        if self.wheel_handler is not None:
            if hasattr(event, "Handled"):
                event.Handled = True
            self.wheel_handler(self, event.Delta, Control.ModifierKeys)
        else:
            Panel.OnMouseWheel(self, event)


class QualityPreviewForm(Form):
    """Load two detached, color-managed bitmaps at a time from retained manifests.

    PNGs represent decoded WebP pixels; size captions use the original WebP
    byte count. Release image objects when switching pages or closing."""
    def __init__(self, preview_folder):
        self.Text = "WebP Optimizer - Compare quality"
        self.Font = Font("Segoe UI", 10.0)
        self.BackColor = Color.White
        self.ClientSize = Size(1400, 900)
        self.MinimumSize = Size(1240, 650)
        self.WindowState = FormWindowState.Maximized
        self.StartPosition = FormStartPosition.CenterParent
        self.KeyPreview = True
        self._syncing = False
        self._updating = False
        self._images = []
        self._fullscreen = False
        self._scale = 1.0
        self._entries = []
        self._difference = None
        self._analysis_worker = None
        self._analysis_timer = Timer()
        self._analysis_timer.Interval = 75
        self._analysis_timer.Tick += self._analysis_completed
        grouped = {}
        for manifest in Directory.GetFiles(preview_folder, "preview.xml", SearchOption.AllDirectories):
            document = XmlDocument()
            document.XmlResolver = None
            document.Load(manifest)
            root = document.DocumentElement
            quality = _safe_unicode(root.GetAttribute("quality"))
            if quality not in TRIAL_QUALITY_LEVELS:
                continue
            for node in root.SelectNodes("Page"):
                key = (_safe_unicode(root.GetAttribute("source")) or _safe_unicode(root.GetAttribute("book")), _safe_unicode(node.GetAttribute("id")))
                if key not in grouped:
                    entry = {"title": _safe_unicode(root.GetAttribute("book")) + " / " + _safe_unicode(node.GetAttribute("title")), "variants": {}}
                    grouped[key] = entry
                    self._entries.append(entry)
                original = _safe_unicode(node.GetAttribute("original"))
                converted = _safe_unicode(node.GetAttribute("converted"))
                if Path.GetFileName(original) != original or Path.GetFileName(converted) != converted:
                    raise Exception("Invalid preview image path")
                grouped[key]["variants"][quality] = {"original": Path.Combine(Path.GetDirectoryName(manifest), original), "converted": Path.Combine(Path.GetDirectoryName(manifest), converted), "original_bytes": long(node.GetAttribute("originalBytes")), "webp_bytes": long(node.GetAttribute("webpBytes"))}
        if not self._entries:
            raise Exception("No native preview images found. Enable Keep preview pages and run a new quality test; older HTML-only previews cannot be shown here.")
        toolbar = Panel()
        toolbar.Dock = DockStyle.Top
        toolbar.Height = 112
        self.Controls.Add(toolbar)
        _ui_label(toolbar, "Compare against the original", 20, 12, 650, 28, True)
        self._page = _new_combo()
        self._page.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList
        self._page.Location = Point(20, 56)
        self._page.Size = Size(600, 30)
        self._page.DropDownWidth = 900
        for entry in self._entries:
            self._page.Items.Add(entry["title"])
        toolbar.Controls.Add(self._page)
        self._quality = _new_combo()
        self._quality.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList
        self._quality.Location = Point(636, 56)
        self._quality.Size = Size(104, 30)
        toolbar.Controls.Add(self._quality)
        self._zoom = _new_combo()
        self._zoom.DropDownStyle = System.Windows.Forms.ComboBoxStyle.DropDownList
        self._zoom.Location = Point(756, 56)
        self._zoom.Size = Size(190, 30)
        self._zoom.Items.AddRange(System.Array[System.Object](["Fit whole page", "25%", "50%", "75%", "100% - actual pixels", "125%", "150%", "200% - enlarged pixels", "300%", "400%"]))
        self._zoom.SelectedIndex = 0
        toolbar.Controls.Add(self._zoom)
        full = Button()
        full.Text = "Full screen (F11)"
        full.Location = Point(1000, 56)
        full.Size = Size(180, 30)
        full.Anchor = AnchorStyles.Top | AnchorStyles.Right
        full.Click += self._toggle_fullscreen
        toolbar.Controls.Add(full)
        footer = Panel()
        footer.Dock = DockStyle.Bottom
        footer.Height = 166
        self.Controls.Add(footer)
        _ui_label(footer, "Wheel: scroll both | Ctrl+wheel: zoom | Shift+wheel: horizontal | 100%: actual pixels | F11: full screen | Esc: return", 20, 10, 1280)
        self._analyze = Button()
        self._analyze.Text = "Analyze differences"
        self._analyze.Location = Point(20, 40)
        self._analyze.Size = Size(180, 30)
        self._analyze.Click += self._analyze_difference
        footer.Controls.Add(self._analyze)
        self._show_difference = CheckBox()
        self._show_difference.Text = "Show amplified difference (8x)"
        self._show_difference.Location = Point(220, 42)
        self._show_difference.Size = Size(310, 28)
        self._show_difference.Enabled = False
        self._show_difference.CheckedChanged += self._toggle_difference
        footer.Controls.Add(self._show_difference)
        self._measurements = _ui_label(footer, "Optional full-page RGB measurements. Black heatmap = identical; orange = difference, amplified 8x.", 20, 77, 1300, 28)
        self._measurements.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
        self._pixel_reading = _ui_label(footer, "Hover either image to inspect matching full-resolution pixels. Values use the color-managed display RGB space.", 20, 108, 1300, 42)
        self._pixel_reading.Anchor = AnchorStyles.Left | AnchorStyles.Right | AnchorStyles.Top
        self._split = SplitContainer()
        self._split.Size = Size(1400, 740)
        self._split.SplitterDistance = 698
        self._split.Dock = DockStyle.Fill
        self.Controls.Add(self._split)
        self._split.BringToFront()
        self._panels = []
        self._pictures = []
        self._captions = []
        for parent in [self._split.Panel1, self._split.Panel2]:
            caption = Label()
            caption.Dock = DockStyle.Top
            caption.Height = 42
            caption.Padding = System.Windows.Forms.Padding(12)
            caption.BackColor = Color.FromArgb(235, 242, 239)
            parent.Controls.Add(caption)
            panel = PreviewScrollPanel()
            panel.wheel_handler = self._wheel_input
            panel.Dock = DockStyle.Fill
            panel.AutoScroll = True
            panel.BackColor = Color.FromArgb(30, 37, 40)
            parent.Controls.Add(panel)
            panel.BringToFront()
            picture = PictureBox()
            picture.Location = Point(0, 0)
            picture.SizeMode = PictureBoxSizeMode.StretchImage
            panel.Controls.Add(picture)
            picture.MouseMove += self._inspect_pixel
            picture.MouseEnter += self._focus_preview
            panel.MouseEnter += self._focus_preview
            self._captions.append(caption)
            self._panels.append(panel)
            self._pictures.append(picture)
        self._panels[0].Scroll += self._left_scroll
        self._panels[1].Scroll += self._right_scroll
        self._page.SelectedIndexChanged += self._page_changed
        self._quality.SelectedIndexChanged += self._load_pair
        self._zoom.SelectedIndexChanged += self._resize_images
        self._split.SplitterMoved += self._resize_images
        self.Resize += self._resize_images
        self.KeyDown += self._key_down
        self.FormClosed += self._release_images
        self._page.SelectedIndex = 0

    def _page_changed(self, sender, event):
        selected = _safe_unicode(self._quality.SelectedItem) if self._quality.SelectedIndex >= 0 else "Q80"
        self._updating = True
        self._quality.Items.Clear()
        for quality in TRIAL_QUALITY_LEVELS:
            if quality in self._entries[self._page.SelectedIndex]["variants"]:
                self._quality.Items.Add(quality)
        self._quality.SelectedItem = selected if selected in list(self._quality.Items) else self._quality.Items[0]
        self._updating = False
        self._load_pair(None, None)

    def _release_images(self, sender, event):
        # A running job owns independent snapshots. Completion disposes its result
        # if this form was closed; the worker never touches a live UI bitmap.
        self._analysis_timer.Stop()
        if self._analysis_worker is not None:
            self._analysis_worker.Dispose()
            self._analysis_worker = None
        if sender is self or self.IsDisposed or self.Disposing:
            self._analysis_timer.Dispose()
        self._show_difference.Checked = False
        self._show_difference.Enabled = False
        if self._difference is not None:
            self._difference.Dispose()
            self._difference = None
        self._measurements.Text = "Analyze this page for full-resolution RGB differences (not a quality percentage)."
        for picture in self._pictures:
            picture.Image = None
        for image in self._images:
            image.Dispose()
        self._images = []

    def _load_pair(self, sender, event):
        if self._updating or self._page.SelectedIndex < 0 or self._quality.SelectedIndex < 0:
            return
        self._release_images(None, None)
        quality = _safe_unicode(self._quality.SelectedItem)
        entry = self._entries[self._page.SelectedIndex]["variants"][quality]
        try:
            for key in ["original", "converted"]:
                source = DrawingImage.FromFile(entry[key], True)
                try:
                    self._images.append(Bitmap(source))
                finally:
                    source.Dispose()
            for picture, image in zip(self._pictures, self._images):
                picture.Image = image
            reduction = 100.0 * (entry["original_bytes"] - entry["webp_bytes"]) / entry["original_bytes"]
            self._captions[0].Text = "Original JPEG  |  " + _format_size(entry["original_bytes"])
            self._captions[1].Text = quality + " WebP  |  " + _format_size(entry["webp_bytes"]) + "  |  {0:.1f}% reduction".format(reduction)
            self._converted_caption = self._captions[1].Text
            self._pixel_reading.Text = "Hover either image to inspect matching color-managed RGB pixels."
            self._resize_images(None, None)
            for panel in self._panels:
                panel.AutoScrollPosition = Point(0, 0)
        except Exception, ex:
            self._release_images(None, None)
            self._captions[1].Text = "Preview could not be loaded: " + _safe_unicode(ex)

    def _inspect_pixel(self, sender, event):
        if len(self._images) != 2:
            return
        x = min(self._images[0].Width - 1, max(0, int(event.X * self._images[0].Width / float(sender.Width))))
        y = min(self._images[0].Height - 1, max(0, int(event.Y * self._images[0].Height / float(sender.Height))))
        if self._images[0].Size != self._images[1].Size:
            self._pixel_reading.Text = "Pixel inspection requires matching image dimensions."
            return
        a, b = [image.GetPixel(x, y) for image in self._images]
        self._pixel_reading.Text = "Pixel ({0}, {1}) | Original RGB ({2}, {3}, {4}) | WebP RGB ({5}, {6}, {7}) | Change ({8:+d}, {9:+d}, {10:+d})".format(x, y, a.R, a.G, a.B, b.R, b.G, b.B, int(b.R)-a.R, int(b.G)-a.G, int(b.B)-a.B)

    def _toggle_difference(self, sender, event):
        if len(self._images) != 2:
            return
        showing = self._show_difference.Checked and self._difference is not None
        self._pictures[1].Image = self._difference.Heatmap if showing else self._images[1]
        self._captions[1].Text = "DIFFERENCE: maximum RGB channel change x8 (clipped); black = identical" if showing else self._converted_caption

    def _analyze_difference(self, sender, event):
        if len(self._images) != 2 or self._analysis_worker is not None:
            return
        if self._images[0].Size != self._images[1].Size:
            self._measurements.Text = "Analysis requires matching dimensions; resized pages are not measured."
            return
        if long(self._images[0].Width) * self._images[0].Height > 16000000:
            self._measurements.Text = "Page exceeds the 16-million-pixel analysis memory limit."
            return
        if self._difference is not None:
            self._show_difference.Checked = True
            return
        try:
            job_type = _NATIVE_TYPE.Assembly.GetType("WebPOptimizerRuntime.PreviewDifferenceJob")
            self._analysis_worker = System.Activator.CreateInstance(job_type)
            self._analysis_worker.Start(self._images[0], self._images[1])
        except Exception, ex:
            if self._analysis_worker is not None:
                self._analysis_worker.Dispose()
                self._analysis_worker = None
            self._measurements.Text = "Analysis could not start: " + _safe_unicode(ex)
            return
        self._analyze.Enabled = self._page.Enabled = self._quality.Enabled = False
        self._measurements.Text = "Analyzing full-resolution pixels... You can still zoom and scroll."
        self._analysis_timer.Start()

    def _analysis_completed(self, sender, event):
        # WinForms Timer runs on the UI thread even in an embedded host without
        # a SynchronizationContext. C# owns and cleans all worker snapshots.
        job = self._analysis_worker
        if job is None or not job.Done:
            return
        self._analysis_timer.Stop()
        self._analysis_worker = None
        self._analyze.Enabled = self._page.Enabled = self._quality.Enabled = True
        if job.Error:
            self._measurements.Text = "Analysis failed: " + _safe_unicode(job.Error)
            job.Dispose()
            return
        self._difference = job.TakeResult()
        job.Dispose()
        d = self._difference
        self._measurements.Text = "RGB /255: mean change {0:.3f} | RMS {1:.3f} | max {2} | brightness shift {3:+.3f} | changed {4:.2f}% (not visibility)".format(d.MeanAbsolute, d.RootMeanSquare, d.MaximumChannelDifference, d.BrightnessShift, d.ChangedPercent)
        self._show_difference.Enabled = True

    def _resize_images(self, sender, event):
        if not self._images:
            return
        width, height = self._images[0].Width, self._images[0].Height
        if self._zoom.SelectedIndex == 0:
            scale = min([1.0] + [min(float(max(1, panel.ClientSize.Width - 20)) / width, float(max(1, panel.ClientSize.Height - 20)) / height) for panel in self._panels])
        else:
            scale = float(_safe_unicode(self._zoom.SelectedItem).split("%")[0]) / 100.0
        self._scale = scale
        for panel, picture in zip(self._panels, self._pictures):
            panel.AutoScrollPosition = Point(0, 0)
            picture.Size = Size(max(1, int(width * scale)), max(1, int(height * scale)))
            picture.Location = Point(max(0, (panel.ClientSize.Width - picture.Width) // 2), max(0, (panel.ClientSize.Height - picture.Height) // 2))

    def _focus_preview(self, sender, event):
        panel = sender if sender in self._panels else sender.Parent
        panel.Focus()

    def _wheel_input(self, panel, delta, modifiers):
        if not self._images or delta == 0:
            return
        if (modifiers & Keys.Control) == Keys.Control:
            # Preserve the same image point at each viewport center when zooming.
            image = self._pictures[self._panels.index(panel)]
            center_x = (panel.ClientSize.Width / 2.0 - image.Left) / self._scale
            center_y = (panel.ClientSize.Height / 2.0 - image.Top) / self._scale
            levels = [25, 50, 75, 100, 125, 150, 200, 300, 400]
            current = self._scale * 100.0
            choices = [level for level in levels if level > current + 0.01] if delta > 0 else [level for level in levels if level < current - 0.01]
            if not choices:
                return
            level = min(choices) if delta > 0 else max(choices)
            for index in range(1, self._zoom.Items.Count):
                if _safe_unicode(self._zoom.Items[index]).startswith(str(level) + "%"):
                    self._zoom.SelectedIndex = index
                    break
            for target, picture in zip(self._panels, self._pictures):
                target.AutoScrollPosition = Point(max(0, int(center_x * self._scale - target.ClientSize.Width / 2.0)), max(0, int(center_y * self._scale - target.ClientSize.Height / 2.0)))
            return
        amount = int(round(float(delta) / 120.0 * 96.0))
        x, y = abs(panel.AutoScrollPosition.X), abs(panel.AutoScrollPosition.Y)
        if (modifiers & Keys.Shift) == Keys.Shift:
            x = max(0, x - amount)
        else:
            y = max(0, y - amount)
        panel.AutoScrollPosition = Point(x, y)
        target = self._panels[1] if panel is self._panels[0] else self._panels[0]
        self._sync_scroll(panel, target)

    def _sync_scroll(self, source, target):
        if self._syncing:
            return
        self._syncing = True
        try:
            target.AutoScrollPosition = Point(abs(source.AutoScrollPosition.X), abs(source.AutoScrollPosition.Y))
        finally:
            self._syncing = False

    def _left_scroll(self, sender, event):
        self._sync_scroll(self._panels[0], self._panels[1])

    def _right_scroll(self, sender, event):
        self._sync_scroll(self._panels[1], self._panels[0])

    def _toggle_fullscreen(self, sender, event):
        self._fullscreen = not self._fullscreen
        self.WindowState = FormWindowState.Normal
        self.FormBorderStyle = getattr(FormBorderStyle, "None") if self._fullscreen else FormBorderStyle.Sizable
        self.WindowState = FormWindowState.Maximized

    def _key_down(self, sender, event):
        if event.KeyCode == Keys.F11:
            self._toggle_fullscreen(None, None)
            event.Handled = True
        elif event.KeyCode == Keys.Escape:
            if self._fullscreen:
                self._toggle_fullscreen(None, None)
            else:
                self.Close()
            event.Handled = True


# ===========================================================================
# [P16] History browser and explicit preview deletion
# ===========================================================================
def _history_trace(message):
    """Bounded append log: retain the actual sequence and distinguish test hosts."""
    process = None
    try:
        _ensure_directory(REPORT_DIR)
        path = Path.Combine(REPORT_DIR, "history-diagnostic.log")
        if File.Exists(path) and FileInfo(path).Length > 65536:
            _write_text_file(path, File.ReadAllText(path)[-32768:])
        process = Process.GetCurrentProcess()
        line = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff") + " [" + process.ProcessName + " pid=" + str(process.Id) + "] " + message
        File.AppendAllText(path, line + "\r\n", Encoding.UTF8)
    except Exception:
        pass
    finally:
        if process is not None:
            process.Dispose()


def _show_owned_dialog(dialog, owner):
    """Pass a concrete CLR window owner across the IronPython modal boundary."""
    owner_type = _NATIVE_TYPE.Assembly.GetType("WebPOptimizerRuntime.WindowOwner")
    native_owner = System.Activator.CreateInstance(owner_type, System.Array[System.Object]([owner.Handle]))
    return dialog.ShowDialog(native_owner)



class RunHistoryForm(Form):
    """Browse old reports/previews without starting conversions automatically."""
    def __init__(self, allow_retest=True):
        self._refreshing = False
        self._records = []
        self.retest = None
        self._allow_retest = allow_retest
        self.Text = "WebP Optimizer - Run history"
        self.Font = Font("Segoe UI", 9.0)
        self.BackColor = Color.White
        self.ClientSize = Size(1180, 680)
        self.MinimumSize = Size(1196, 580)
        self.StartPosition = FormStartPosition.CenterParent
        _ui_label(self, "Your previous runs", 24, 20, 1100, 32, True)
        _ui_label(self, "Reopen results or retained previews. Reviewing a historical report preserves previews by default.", 24, 62, 1100, 30)
        self._list = _new_listview()
        self._list.Location = Point(24, 108)
        self._list.Size = Size(1132, 420)
        self._list.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
        self._list.View = View.Details
        self._list.FullRowSelect = True
        self._list.MultiSelect = False
        self._list.HideSelection = False
        for title, width in [("Date", 160), ("Action", 190), ("Books", 65), ("Status", 180), ("Reduction", 350), ("Previews", 105)]:
            self._list.Columns.Add(title, width)
        self.Controls.Add(self._list)
        self._detail = _ui_label(self, "", 24, 544, 1130, 66)
        self._detail.Anchor = AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
        self._buttons = {}
        actions = [("Open results", self._open_results), ("Open previews", self._open_previews), ("Delete previews", self._delete_previews), ("Prepare new test", self._prepare_test), ("Refresh", self._refresh_clicked), ("Close", self._close_history)]
        for index, (title, handler) in enumerate(actions):
            button = Button()
            button.Text = title
            button.Location = Point(24 + index * 188, 628)
            button.Size = Size(176, 32)
            button.Anchor = AnchorStyles.Bottom | AnchorStyles.Left
            button.Click += handler
            self.Controls.Add(button)
            self._buttons[title] = button
        self._list.SelectedIndexChanged += self._selected_changed
        self._list.DoubleClick += self._open_results
        self._selected_changed(None, None)
        self._detail.Text = "Loading run history..."
        self.Shown += self._on_shown

    def _on_shown(self, sender, event):
        self.BeginInvoke(System.Windows.Forms.MethodInvoker(self._refresh_safe))

    def _refresh_safe(self):
        """Contain ordinary load/event errors and avoid recursive refresh events."""
        if self.IsDisposed or self.Disposing or self._refreshing:
            return
        try:
            _history_trace("Loading history records")
            self._refresh()
            _history_trace("History ready: " + str(len(self._records)) + " records")
        except Exception, ex:
            self._detail.Text = "History could not be loaded: " + _safe_unicode(ex)
            _history_trace(self._detail.Text)
            MessageBox.Show(self._detail.Text + "\nSee Reports/history-diagnostic.log.", "WebP Optimizer")

    def _selected(self):
        return self._list.SelectedItems[0].Tag if self._list.SelectedItems.Count else None

    def _refresh(self):
        if self._refreshing:
            return
        self._refreshing = True
        self._list.BeginUpdate()
        try:
            current = self._selected()
            old_path = current["path"] if current else ""
            self._list.Items.Clear()
            self._records = _load_run_history()
            for record in self._records:
                item = ListViewItem(record.get("generated", ""))
                for key in ["mode", "books", "status", "savings", "previewState"]:
                    item.SubItems.Add(record.get(key, ""))
                item.Tag = record
                self._list.Items.Add(item)
                if record["path"] == old_path:
                    item.Selected = True
            if not self._records:
                self._detail.Text = "No reports yet. Complete an analysis, conversion or quality test to create history."
        finally:
            self._refreshing = False
            self._list.EndUpdate()
        self._selected_changed(None, None)
        if not self._records:
            self._detail.Text = "No reports yet. Complete an analysis, conversion or quality test to create history."

    def _selected_changed(self, sender, event):
        if self._refreshing:
            return
        record = self._selected()
        self._buttons["Open results"].Enabled = record is not None
        self._buttons["Open previews"].Enabled = record is not None and record.get("previewState", "") == "Available"
        self._buttons["Delete previews"].Enabled = record is not None and bool(record.get("previewFolder", "")) and Directory.Exists(record.get("previewFolder", ""))
        self._buttons["Prepare new test"].Enabled = self._allow_retest and record is not None and record.get("mode", "") == "Test savings & quality"
        if not record:
            self._detail.Text = "Select a run to view its results and preview status."
        if record:
            self._detail.Text = record["path"] + "\nPreview status: " + record.get("previewState", "-") + ". Preparing a test uses the current ComicRack selection; sources and settings must be reviewed."
            if not self._allow_retest:
                self._detail.Text += " To prepare a test, open history from Optimize Archives."

    def _open_results(self, sender, event):
        record = self._selected()
        if not record:
            return
        try:
            form = ReportForm(File.ReadAllText(record["path"]), record["path"], historical=True)
            try:
                _show_owned_dialog(form, self)
            finally:
                form.Dispose()
        except Exception, ex:
            MessageBox.Show("Could not reopen this report: " + _safe_unicode(ex), "WebP Optimizer")
        self._refresh_safe()

    def _open_previews(self, sender, event):
        record = self._selected()
        if not record:
            return
        try:
            form = QualityPreviewForm(record["previewFolder"])
            try:
                _show_owned_dialog(form, self)
            finally:
                form.Dispose()
        except Exception, ex:
            MessageBox.Show("Preview images are unavailable: " + _safe_unicode(ex), "WebP Optimizer")
        self._refresh_safe()

    def _delete_previews(self, sender, event):
        record = self._selected()
        if not record:
            return
        answer = MessageBox.Show("Delete only this run's preview images? The text report and original comics will remain.", "Delete previews", MessageBoxButtons.YesNo, MessageBoxIcon.Question)
        if answer != DialogResult.Yes:
            return
        try:
            _delete_trial_previews(record["previewFolder"])
            text = File.ReadAllText(record["path"]) + "\r\nPreview cleanup: Deleted from run history.\r\n"
            _write_text_file(record["path"], text)
            _record_run_safely(record["path"], text, preview_state="Removed")
        except Exception, ex:
            MessageBox.Show("Preview deletion failed: " + _safe_unicode(ex), "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        self._refresh_safe()

    def _prepare_test(self, sender, event):
        record = self._selected()
        if record and self._allow_retest:
            self.retest = record
            self.DialogResult = DialogResult.OK
            self.Close()

    def _refresh_clicked(self, sender, event):
        self._refresh_safe()

    def _close_history(self, sender, event):
        self.Close()


# ===========================================================================
# [P17] Results UI and preview lifecycle
# ===========================================================================
class ReportForm(Form):
    """Render results and own preview cleanup when this results window closes.

    Historical windows preserve previews by default; closing only the native
    comparison must not delete images needed by this results window."""
    def __init__(self, report_text, report_path, historical=False):
        self._historical = historical
        self._report_text = report_text
        self._report_path = report_path
        self._summary_items = _extract_report_summary_items(report_text)
        self._report_title = self._summary_items[0][1] if self._summary_items else "WebP Optimizer Report"
        self._build()

    def _build(self):
        self.Text = "WebP Optimizer - Run results"
        self.Font = Font("Segoe UI", 9.0)
        self.AutoScaleMode = AutoScaleMode.Font
        self.ClientSize = Size(1060, 710)
        self.MinimumSize = Size(900, 600)
        self.StartPosition = FormStartPosition.CenterParent
        self.BackColor = Color.White
        summary = dict(self._summary_items)
        converted = summary.get("Converted Books", summary.get("Converted Copies", "0"))
        failed = summary.get("Failed", summary.get("Errors", "0"))
        analyzed = "Run Mode" not in summary
        trial_mode = summary.get("Run Mode", "") == "Test savings & quality"
        title = "Quality comparison complete" if trial_mode else ("Analysis complete" if analyzed else "Conversion complete")
        if summary.get("Run Status", "") == "Stopped by user":
            title = "Run stopped - completed work is saved"
        if failed != "0":
            title = "Run finished - review failures"
        elif "Report storage warnings" in self._report_text:
            title = "Run complete - report storage needs attention"
        _ui_label(self, title, 24, 18, 980, 34, True)
        if trial_mode:
            headline = "   |   ".join([q + ": " + summary.get(q + " Reduction", "-") for q in TRIAL_QUALITY_LEVELS])
        elif analyzed:
            headline = "Scanned " + summary.get("Books Scanned", "0") + " books"
        else:
            headline = summary.get("Total Saved", "0 MB") + " saved  |  " + summary.get("Overall Reduction", "0.00%" if converted == "0" else "Not recorded") + " reduction"
        self._headline = _ui_label(self, headline, 24, 64, 1000, 42, True)
        self._headline.Font = Font("Segoe UI", 15.0 if trial_mode else 22.0, FontStyle.Bold)
        counts = converted + " converted     " + summary.get("Skipped", "0") + " skipped     " + failed + " failed     " + summary.get("Not Processed", "0") + " not processed"
        if trial_mode:
            counts = summary.get("Compared Books", "0") + " books compared     " + summary.get("Skipped", "0") + " not sampled/ineligible     " + failed + " failed     " + summary.get("Not Processed", "0") + " not processed"
        elif analyzed:
            counts = summary.get("JPEG-only Candidates", "0") + " JPEG-only candidates     " + summary.get("Already WebP", "0") + " already WebP     " + failed + " errors     " + summary.get("Missing Files", "0") + " missing     " + summary.get("Not Processed", "0") + " not processed"
        _ui_label(self, counts, 24, 116, 1000, 28)
        sizes = "Before " + summary.get("Total Source Size", "-") + "    >    After " + summary.get("Total Output Size", "-")
        if trial_mode:
            sizes = "   |   ".join([q + ": " + summary.get(q + " Time", "-") for q in TRIAL_QUALITY_LEVELS])
        _ui_label(self, sizes if not analyzed else "Use ImageFormat smart lists to find conversion candidates.", 24, 150, 1000, 26)
        note = "Reduction covers successful conversions only, weighted by original archive size."
        if summary.get("Run Mode", "") != "Replace Originals" or summary.get("Create Backup", "No") == "Yes":
            note += " Copies, benchmarks and retained backups do not reclaim these bytes from disk."
        if trial_mode:
            note = "Actual reductions for paired successful sample books, not a collection prediction. Originals unchanged. Optional previews are retained; inspect any failures for cleanup warnings."
        if trial_mode and summary.get("Preview Folder", ""):
            note = "Measured sample only. Originals unchanged. The cleanup option below applies to this run, not the text report."
        if "Report storage warnings" in self._report_text:
            note = "Some source-folder reports could not be saved. The central report is available; see Technical report for details."
        _ui_label(self, note if not analyzed else "Open Technical report for individual format counts and scan notes.", 24, 184, 1000, 26 if trial_mode and summary.get("Preview Folder", "") else 46)
        self._tabs = _new_tabs()
        self._tabs.Location = Point(16, 240)
        self._tabs.Size = Size(1028, 400)
        self._tabs.Anchor = AnchorStyles.Top | AnchorStyles.Bottom | AnchorStyles.Left | AnchorStyles.Right
        self.Controls.Add(self._tabs)
        books = TabPage("Book results")
        technical = TabPage("Technical report")
        self._tabs.TabPages.Add(books)
        self._tabs.TabPages.Add(technical)
        listing = _new_listview()
        listing.Dock = DockStyle.Fill
        listing.View = View.Details
        listing.FullRowSelect = True
        listing.GridLines = False
        columns = ([("Book", 280), ("Result", 80)] + [(q + " reduction", 112) for q in TRIAL_QUALITY_LEVELS] + [("Details", 320)]) if trial_mode else [("Book", 410), ("Result", 100), ("Reduction", 90), ("Details", 360)]
        for title, width in columns:
            listing.Columns.Add(title, width)
        current = None
        in_books = False
        records = []
        for line in self._report_text.splitlines():
            if line.startswith("Preview cleanup") or line == "Report storage warnings":
                break
            if line in ["Per-Book Conversion Results", "Per-Book Analysis", "Per-Book Results"]:
                in_books = True
                continue
            if not in_books or not line.strip() or line.startswith("---"):
                continue
            if not line.startswith(" "):
                current = {"book": line}
                records.append(current)
            elif current is not None and ": " in line:
                key, separator, value = line.strip().partition(":")
                current[key] = value.strip()
        for record in records:
            item = ListViewItem(record.get("book", ""))
            item.SubItems.Add(record.get("Conversion Status", record.get("Status", "")))
            if trial_mode:
                for key in [q + " Savings" for q in TRIAL_QUALITY_LEVELS]:
                    item.SubItems.Add(record.get(key, "-"))
            else:
                item.SubItems.Add(record.get("Savings", "-"))
            item.SubItems.Add(record.get("Notes", ""))
            listing.Items.Add(item)
        books.Controls.Add(listing)
        self._report_box = RichTextBox()
        self._report_box.Dock = DockStyle.Fill
        self._report_box.Multiline = True
        self._report_box.ReadOnly = True
        self._report_box.ScrollBars = RichTextBoxScrollBars.Both
        self._report_box.WordWrap = True
        self._report_box.Font = Font("Consolas", 9.0)
        self._report_box.Text = self._report_text
        technical.Controls.Add(self._report_box)
        _add_report_reader(self, technical)
        if summary.get("Preview Folder", ""):
            self._preview_folder = summary["Preview Folder"]
            self._delete_previews_checkbox = _new_checkbox()
            self._delete_previews_checkbox.Text = "Delete this run's preview images when closing this results window"
            self._delete_previews_checkbox.Checked = False if self._historical else _load_settings()[0].get("delete_test_previews_on_close", "True").lower() == "true"
            self._delete_previews_checkbox.Location = Point(24, 212)
            self._delete_previews_checkbox.Size = Size(940, 26)
            self.Controls.Add(self._delete_previews_checkbox)
            self.FormClosing += self._closing_results
            preview_button = Button()
            preview_button.Text = "Open previews"
            preview_button.Enabled = _preview_state(self._preview_folder) == "Available"
            self._delete_previews_checkbox.Enabled = Directory.Exists(self._preview_folder)
            preview_button.Location = Point(500, 660)
            preview_button.Size = Size(160, 32)
            preview_button.Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            preview_button.Click += self._open_trial_previews
            self.Controls.Add(preview_button)
        _ui_label(self, "Central report saved in plugin Reports folder", 24, 666, 450, 24).Anchor = AnchorStyles.Bottom | AnchorStyles.Left
        for text, x, handler in [("Copy report", 680, self._copy_report), ("Open report", 802, self._open_report), ("Close", 924, self._close)]:
            button = Button()
            button.Text = text
            button.Location = Point(x, 660)
            button.Size = Size(112, 32)
            button.Anchor = AnchorStyles.Bottom | AnchorStyles.Right
            button.Click += handler
            self.Controls.Add(button)

    def _closing_results(self, sender, event):
        if self._historical and not self._delete_previews_checkbox.Checked:
            return
        try:
            settings, warning = _load_settings()
            settings["delete_test_previews_on_close"] = str(bool(self._delete_previews_checkbox.Checked))
            _save_settings(settings)
        except Exception, ex:
            MessageBox.Show("Could not remember preview cleanup preference: " + _safe_unicode(ex), "WebP Optimizer")
        if not self._delete_previews_checkbox.Checked:
            return
        try:
            _delete_trial_previews(self._preview_folder)
            message = "Preview cleanup: Deleted when results closed. " + self._preview_folder
        except Exception, ex:
            message = "Preview cleanup failed; retained files may remain at " + self._preview_folder + ": " + _safe_unicode(ex)
            MessageBox.Show(message, "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Warning)
        self._report_text += "\r\n" + message + "\r\n"
        try:
            _write_text_file(self._report_path, self._report_text)
            _record_run_safely(self._report_path, self._report_text, preview_state="Removed" if not Directory.Exists(self._preview_folder) else "Available")
        except Exception:
            pass

    def _open_trial_previews(self, sender, event):
        try:
            viewer = QualityPreviewForm(self._preview_folder)
            try:
                viewer.ShowDialog(self)
            finally:
                viewer.Dispose()
        except Exception:
            MessageBox.Show("Could not open previews: " + self._preview_folder, "WebP Optimizer")

    def _copy_report(self, sender, event):
        del sender
        del event
        try:
            Clipboard.SetText(_safe_unicode(self._report_text))
        except Exception:
            MessageBox.Show("Could not copy the report text.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Warning)

    def _open_report(self, sender, event):
        del sender
        del event
        try:
            Process.Start(_safe_unicode(self._report_path))
        except Exception:
            MessageBox.Show("Could not open the report file.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Warning)

    def _close(self, sender, event):
        del sender
        del event
        self.Close()


# ===========================================================================
# [P20] Durable per-book checkpoints (normal copy/replace runs only)
# ===========================================================================
def _checkpoint_signature(file_path):
    """Cheap file identity for resume, not a content hash or concurrent-write lock."""
    if not file_path:
        return ""
    info = FileInfo(file_path)
    if not info.Exists:
        return ""
    return str(info.Length) + ":" + str(info.LastWriteTimeUtc.Ticks)


def _checkpoint_hash(text):
    """Make deterministic path-safe keys without putting personal paths in names."""
    digest = System.Security.Cryptography.SHA256.Create()
    try:
        return System.BitConverter.ToString(digest.ComputeHash(Encoding.UTF8.GetBytes(text))).Replace("-", "").ToLowerInvariant()
    finally:
        digest.Dispose()


def _checkpoint_path(source, options):
    """Separate records by conversion intent and an explicit compatibility version."""
    defaults = {"run_mode": "Create WebP Copies", "quality_mode": QUALITY_MODE_VALUES[0],
                "encoder_backend": ENCODER_BACKEND_VALUES[0], "resize_mode": RESIZE_MODE_VALUES[0],
                "cbr_mode": CBR_MODE_VALUES[0], "size_policy": SIZE_POLICY_VALUES[0], "create_backup": False}
    values = dict((key, _safe_unicode(options.get(key, defaults[key]))) for key in defaults)
    values["quality_mode"] = "".join(c for c in values["quality_mode"] if c.isdigit()) or "80"
    values["encoder_backend"] = values["encoder_backend"].split(" (")[0].lower()
    policy = "\n".join([key + "=" + values[key] for key in sorted(defaults)])
    revision = "policy:" + CHECKPOINT_POLICY_VERSION
    folder = Path.Combine(Path.Combine(REPORT_DIR, "Checkpoints"), _checkpoint_hash(policy + "\n" + revision))
    return Path.Combine(folder, _checkpoint_hash(Path.GetFullPath(source).lower()) + ".xml")


def _pending_checkpoint_path(source):
    """Index unfinished work independently of quality/policy changes."""
    folder = Path.Combine(Path.Combine(REPORT_DIR, "Checkpoints"), "Pending")
    return Path.Combine(folder, _checkpoint_hash(Path.GetFullPath(source).lower()) + ".xml")


def _write_book_checkpoint(result, options, output_path, state, conversion=None):
    """Atomically journal intent before work, then completion after library updates.

    A pending output is never automatically deleted or installed on resume.
    Write failures propagate: do not start another book without durable state.
    """
    source = _safe_unicode(result.get("file_path", ""))
    source_signature = _checkpoint_signature(source)
    if not source_signature and state == "pending":
        return  # A missing source is handled by scanning; no useful intent to save.
    document = XmlDocument()
    root = document.CreateElement("Checkpoint")
    document.AppendChild(root)
    root.SetAttribute("policyRecord", _checkpoint_path(source, options))
    for key, value in [("version", "2"), ("compatibility", CHECKPOINT_POLICY_VERSION), ("state", state), ("source", source),
                       ("sourceSignature", source_signature), ("output", output_path),
                       ("outputSignature", _checkpoint_signature(output_path)),
                       ("updated", DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss"))]:
        root.SetAttribute(key, _safe_unicode(value))
    policy_values = dict((key, options[key]) for key in ["run_mode", "quality_mode", "encoder_backend", "resize_mode", "cbr_mode", "size_policy", "create_backup"] if key in options)
    for name, values in [("Scan", result), ("Result", conversion or {}), ("Options", policy_values)]:
        parent = document.CreateElement(name)
        root.AppendChild(parent)
        for key, value in values.items():
            node = document.CreateElement("Value")
            node.SetAttribute("key", _safe_unicode(key))
            node.SetAttribute("value", _safe_unicode(value))
            parent.AppendChild(node)
    targets = [_checkpoint_path(source, options)]
    if state == "pending":
        targets.append(_pending_checkpoint_path(source))
    if state == "completed" and options.get("run_mode") == "Replace Originals" and output_path.lower() != source.lower():
        targets.append(_checkpoint_path(output_path, options))
    for target in targets:
        _ensure_directory(Path.GetDirectoryName(target))
        temporary = target + "." + System.Guid.NewGuid().ToString("N") + ".tmp"
        try:
            document.Save(temporary)
            if File.Exists(target):
                File.Replace(temporary, target, None)
            else:
                File.Move(temporary, target)
        finally:
            if File.Exists(temporary):
                File.Delete(temporary)
    if state in ["completed", "skipped", "retryable"] and File.Exists(_pending_checkpoint_path(source)):
        File.Delete(_pending_checkpoint_path(source))


def _resume_book_checkpoint(source, options):
    """Return a verified completed record, or flag an ambiguous interrupted output.

    Only explicitly selected files are considered. Changed/missing files do not
    qualify as completed. Corrupt records fail visibly instead of being ignored.
    """
    if File.Exists(source + ".webp-recovery.txt"):
        raise Exception("Unresolved replacement recovery record: " + source + ".webp-recovery.txt")
    pending_path = _pending_checkpoint_path(source)
    if File.Exists(pending_path):
        pending = XmlDocument()
        pending.XmlResolver = None
        pending.Load(pending_path)
        if pending.DocumentElement.Name != "Checkpoint" or pending.DocumentElement.GetAttribute("state") != "pending":
            raise Exception("Invalid pending checkpoint: " + pending_path)
        unfinished = _safe_unicode(pending.DocumentElement.GetAttribute("output"))
        # A crashed parent can leave a still-running encoder before its archive
        # exists. Absence of output is not evidence that restarting is safe.
        raise Exception("Interrupted attempt needs inspection, including any still-running helper. Checkpoint: " + pending_path + "; planned output: " + unfinished)
    target = _checkpoint_path(source, options)
    if not File.Exists(target):
        return None
    document = XmlDocument()
    document.XmlResolver = None
    document.Load(target)
    root = document.DocumentElement
    if root.Name != "Checkpoint" or root.GetAttribute("version") != "2" or root.GetAttribute("compatibility") != CHECKPOINT_POLICY_VERSION:
        raise Exception("Unsupported checkpoint: " + target)
    output = _safe_unicode(root.GetAttribute("output"))
    if root.GetAttribute("state") not in ["pending", "completed", "skipped", "retryable"]:
        raise Exception("Invalid checkpoint state: " + target)
    if root.GetAttribute("state") == "pending":
        raise Exception("Interrupted attempt needs inspection. Checkpoint: " + target + "; planned output: " + output)
    if root.GetAttribute("state") == "retryable":
        if File.Exists(output):
            raise Exception("Unexpected output after failed attempt needs inspection: " + output)
        return None
    original = _safe_unicode(root.GetAttribute("source"))
    expected = root.GetAttribute("sourceSignature") if source.lower() == original.lower() else root.GetAttribute("outputSignature")
    # A completed extension change may precede ComicRack's database save.
    # Permit repairing that selected old entry only when its old path is gone
    # and the installed final file still has the recorded identity.
    repair_relink = (root.GetAttribute("state") == "completed" and options.get("run_mode") == "Replace Originals"
                     and source.lower() == original.lower() and output.lower() != source.lower() and not File.Exists(source))
    if not repair_relink and (not expected or _checkpoint_signature(source) != expected):
        return None
    if root.GetAttribute("state") == "completed" and (not root.GetAttribute("outputSignature") or _checkpoint_signature(output) != root.GetAttribute("outputSignature")):
        return None
    scan = dict((_safe_unicode(n.GetAttribute("key")), _safe_unicode(n.GetAttribute("value"))) for n in root.SelectNodes("Scan/Value"))
    scan["file_path"] = source
    scan["status"] = "Resumed completed book"
    scan["scan_seconds"] = "0"
    message = "Previously completed with matching settings and unchanged file signatures; not converted again."
    if root.GetAttribute("state") == "skipped":
        message = "Previously rejected by the same size policy; unchanged source was not encoded again."
        output = ""
    stored = dict((_safe_unicode(n.GetAttribute("key")), _safe_unicode(n.GetAttribute("value"))) for n in root.SelectNodes("Result/Value"))
    return scan, {"STATUS": "SKIPPED", "SKIP_REASON": "RESUMED", "RESUMED_SKIP_REASON": stored.get("SKIP_REASON", "SIZE_POLICY" if root.GetAttribute("state") == "skipped" else ""), "OUTPUT_PATH": output, "MESSAGE": message,
                  "OUTPUT_IMAGE_FORMAT": stored.get("OUTPUT_IMAGE_FORMAT", "WEBP") if output else scan.get("image_format", "")}


# ===========================================================================
# [P18] Selected-book analysis and conversion workflows
# ===========================================================================
def _run_phase_one(books, options=None):
    """Analyze captured books, honoring stops between scans and saving partial results."""
    if not books or len(books) == 0:
        MessageBox.Show("Select one or more books in ComicRack before running WebP Optimizer.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Information)
        return

    tool_path = _find_archive_tool()
    if not tool_path:
        MessageBox.Show("Could not find 7-Zip analysis tooling. Expected to find 7za in the ComicRack resources or ComicRackCE_nightly resources folder.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Error)
        return

    _ensure_directory(REPORT_DIR)
    progress_form = ProgressForm()
    progress_form.Show()
    results = []

    awake = None
    try:
        awake = _begin_keep_awake(options or {})
        total = len(books)
        for index in range(total):
            if progress_form.stop_requested:
                break
            book = books[index]
            percent = int((index * 100.0) / total)
            progress_form.update_state(percent, "Scanning archives", _safe_unicode(getattr(book, "Caption", "")) or _safe_unicode(getattr(book, "FileNameWithExtension", "")), index + 1, total, index)
            if progress_form.stop_requested:
                break
            result = _scan_book(book, tool_path)
            _set_scan_custom_values(book, result)
            results.append(result)

        timestamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
        report_path = Path.Combine(REPORT_DIR, "webp_analysis_{0}_{1}.txt".format(timestamp, System.Guid.NewGuid().ToString("N")[:8]))
        scanned_count = len(results)
        for index in range(scanned_count, total):
            results.append(_unprocessed_book(books[index]))
        report_text = _build_analysis_report(results, tool_path)
        report_text = _run_report_status(report_text, total, scanned_count, progress_form.stop_requested and scanned_count < total)
        _write_text_file(report_path, report_text)
        report_text = _copy_reports_to_sources(report_text, report_path, results, options or {})
        _record_run_safely(report_path, report_text, options or {}, results)
    finally:
        try:
            progress_form.finish()
        finally:
            _end_keep_awake(awake)

    report_form = ReportForm(report_text, report_path)
    report_form.ShowDialog()


def _run_phase_two(books):
    """Show options/history, then scan and process only the captured selection.

    Options open before dependency checks so history needs neither selected
    books nor a working conversion toolchain. Stop checks bracket each book."""
    options = _choose_options_with_history(books)
    if options is None:
        return
    if not books or len(books) == 0:
        MessageBox.Show("Select books before starting a run. Run history is available without selecting books.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Information)
        return

    if options.get("_show_preflight"):
        if not _confirm_batch(books, options):
            return
        setup_options = dict(options)
        if books and not options.get("work_dir"):
            setup_options["_setup_default_work_dir"] = Path.GetDirectoryName(_safe_unicode(getattr(books[0], "FilePath", "")))
        setup = _setup_checks(setup_options)
        if setup.get("STATUS") != "OK":
            MessageBox.Show("Setup needs attention before this batch can start.\n" + setup.get("CHECK_MESSAGE", "Open Tools & recovery > Check setup for details."), "WebP Optimizer")
            return

    tool_path = _find_archive_tool()
    if not tool_path:
        MessageBox.Show("Could not find 7-Zip tooling. Expected to find a 7z or 7za executable in the ComicRack resources or ComicRackCE_nightly resources folder.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Error)
        return

    if _safe_unicode(options.get("run_mode", "")) == "Analyze Only":
        _run_phase_one(books, options)
        return

    python_tool = _find_python_tool()
    if not python_tool:
        MessageBox.Show("Could not find a Python 3 runtime for the WebP conversion helper.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Error)
        return

    if not File.Exists(HELPER_SCRIPT):
        MessageBox.Show("The WebP conversion helper script is missing: " + HELPER_SCRIPT, "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Error)
        return

    rar_tool = None
    if _is_cbr_rebuild_mode(options):
        rar_tool = _find_rar_tool()
        if not rar_tool:
            MessageBox.Show("WinRAR rar.exe is required for the selected CBR rebuild mode, but it could not be found on this machine.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Error)
            return
        options["rar_tool"] = rar_tool

    _ensure_directory(REPORT_DIR)
    progress_form = ProgressForm()
    progress_form.Show()
    options["_progress_form"] = progress_form
    results = []
    conversion_results = []
    total = len(books)
    benchmark_mode = _safe_unicode(options.get("run_mode", "")) == "Test savings & quality"
    if not benchmark_mode and hasattr(progress_form, "set_batch"):
        progress_form.set_batch(books)
    if benchmark_mode and options.get("keep_test_previews", False):
        options["trial_preview_root"] = Path.Combine(REPORT_DIR, "QualityTests", System.Guid.NewGuid().ToString("N"))
        _ensure_directory(options["trial_preview_root"])

    awake = None
    try:
        awake = _begin_keep_awake(options)
        if benchmark_mode:
            for index in range(total):
                book = books[index]
                if progress_form.stop_requested:
                    break
                percent = int((index * 45.0) / total)
                progress_form.update_state(percent, "Scanning archives", _safe_unicode(getattr(book, "Caption", "")) or _safe_unicode(getattr(book, "FileNameWithExtension", "")), index + 1, total, index)
                if progress_form.stop_requested:
                    break
                result = _scan_book(book, tool_path)
                _set_scan_custom_values(book, result)
                results.append(result)

            scanned_count = len(results)
            for index in range(scanned_count, total):
                results.append(_unprocessed_book(books[index]))
        else:
            results = [_unprocessed_book(book) for book in books]
        trial_indices = _trial_sample_indices(results, options) if benchmark_mode else set()
        if benchmark_mode and hasattr(progress_form, "set_quality_batch"):
            progress_form.set_quality_batch([results[i] for i in sorted(trial_indices)])
        for index in range(total):
            book = books[index]
            result = results[index]
            if not benchmark_mode and not progress_form.stop_requested:
                progress_form.update_state(int(index * 100.0 / total), "Scanning current archive", _safe_unicode(getattr(book, "Caption", "")), index + 1, total, index)
                if not progress_form.stop_requested:
                    source = _safe_unicode(getattr(book, "FilePath", ""))
                    try:
                        # Pending attempts are checked even with completed-book reuse disabled.
                        resumed = _resume_book_checkpoint(source, options)
                        if resumed is not None and options.get("resume_completed", True):
                            results[index], reused = resumed
                            if options.get("run_mode") == "Replace Originals" and reused.get("OUTPUT_PATH"):
                                _update_book_file_path(book, reused["OUTPUT_PATH"])
                                _set_converted_custom_values(book, reused["OUTPUT_PATH"], reused)
                            _status_after_conversion(book, results[index], reused, options)
                            conversion_results.append(reused)
                            continue
                    except Exception, ex:
                        results[index] = {"caption": _safe_unicode(getattr(book, "Caption", "")), "file_path": source, "status": "Checkpoint needs inspection"}
                        _set_workflow_status(book, "Needs attention", _safe_unicode(ex), source)
                        conversion_results.append({"STATUS": "ERROR", "MESSAGE": _safe_unicode(ex)})
                        continue
                    scan_clock = Stopwatch.StartNew()
                    result = _scan_book(book, tool_path)
                    result["scan_seconds"] = str(scan_clock.Elapsed.TotalSeconds)
                    results[index] = result
                    _set_scan_custom_values(book, result)
            if progress_form.stop_requested:
                conversion_results.append({"STATUS": "NOT_PROCESSED", "MESSAGE": "Run stopped before this book was processed."})
                continue
            percent = 45 + int((index * 55.0) / total) if benchmark_mode else int(index * 100.0 / total)
            progress_form.update_state(percent, "Converting and validating archives", _safe_unicode(result.get("caption", "")), index + 1, total, index)
            if progress_form.stop_requested:
                conversion_results.append({"STATUS": "NOT_PROCESSED", "MESSAGE": "Run stopped before this book was processed."})
                continue

            if not result.get("eligible", False):
                if not benchmark_mode:
                    _status_after_conversion(book, result, {"STATUS": "SKIPPED", "MESSAGE": result.get("notes", "")}, options)
                conversion_results.append({
                    "STATUS": "SKIPPED",
                    "SKIP_REASON": _safe_unicode(result.get("skip_reason", "NOT_ELIGIBLE")),
                    "MESSAGE": _safe_unicode(result.get("notes", "")) or _safe_unicode(result.get("status", "Not eligible")),
                })
                continue

            if _safe_unicode(result.get("archive_type", "")) == "cbr" and _safe_unicode(options.get("cbr_mode", "")) == "Keep original CBR files (skip conversion)":
                _set_workflow_status(book, "Skipped", "CBR left unchanged by the selected option", result.get("file_path", ""))
                conversion_results.append({
                    "STATUS": "SKIPPED",
                    "SKIP_REASON": "CBR_OPTION",
                    "MESSAGE": "CBR source left unchanged by the selected run option.",
                })
                continue

            if benchmark_mode and index not in trial_indices:
                conversion_results.append({
                    "STATUS": "SKIPPED",
                    "SKIP_REASON": "BENCHMARK_LIMIT",
                    "MESSAGE": "Not one of the up to 3 eligible books spaced through this selection.",
                })
                continue

            if benchmark_mode:
                conversion_results.append(_run_quality_trial(python_tool, tool_path, result, options, book, progress_form))
                continue

            attempt_options = dict(options)
            if options.get("prefetch") and options.get("work_dir") and index + 1 < total and not progress_form.stop_requested:
                attempt_options["prefetch_next"] = _safe_unicode(getattr(books[index + 1], "FilePath", ""))
            planned_output = _build_replace_temp_output_path_for_result(result, options) if options.get("run_mode") == "Replace Originals" else _build_copy_output_path_for_result(result, options)
            attempt_options["checkpoint_output_path"] = planned_output
            _write_book_checkpoint(result, options, planned_output, "pending")
            worker_clock = Stopwatch.StartNew()
            helper_result = _run_conversion_helper(python_tool, tool_path, result, attempt_options, book)
            # The consumed cache normally disappears inside the helper. Also clean
            # after early rejection (for example an output-path collision).
            old_cache = options.get("prefetch_record", "")
            options["prefetch_record"] = helper_result.get("PREFETCH_RECORD", "")
            # An exact worker acknowledgement avoids a second Python startup.
            # Older/failed workers without this acknowledgement still use the
            # guarded cleanup helper; never assume missing stdout means cleanup.
            if old_cache and helper_result.get("PREFETCH_CLEANED_RECORD", "") != old_cache:
                try:
                    _cleanup_prefetch(python_tool, {"prefetch_record": old_cache, "work_dir": options.get("work_dir", "")})
                except Exception, ex:
                    helper_result["CLEANUP_WARNING"] = _safe_unicode(ex) + " Cache: " + old_cache
            helper_result["TIME_WORKER_SECONDS"] = "{0:.3f}".format(worker_clock.Elapsed.TotalSeconds)
            helper_result["TIME_SCAN_SECONDS"] = result.get("scan_seconds", "0")
            if helper_result.get("CLEANUP_WARNING"):
                helper_result["MESSAGE"] = _safe_unicode(helper_result.get("MESSAGE", "")) + " " + _safe_unicode(helper_result["CLEANUP_WARNING"])
                progress_form.stop_requested = True
            if _safe_unicode(helper_result.get("STATUS", "")) != "OK" and not _safe_unicode(helper_result.get("MESSAGE", "")):
                helper_result["MESSAGE"] = _safe_unicode(helper_result.get("stderr", "")) or "Conversion helper failed."

            if _safe_unicode(helper_result.get("STATUS", "")) == "OK" and _safe_unicode(options.get("run_mode", "")) == "Replace Originals":
                if hasattr(progress_form, "update_archive_progress"):
                    progress_form.update_archive_progress("REPLACING|0|0")
                replace_clock = Stopwatch.StartNew()
                helper_result = _finalize_replacement(_safe_unicode(result.get("file_path", "")), helper_result, options)
                helper_result["TIME_REPLACE_SECONDS"] = "{0:.3f}".format(replace_clock.Elapsed.TotalSeconds)

            if _safe_unicode(helper_result.get("STATUS", "")) == "OK" and _safe_unicode(options.get("run_mode", "")) == "Replace Originals":
                _update_book_file_path(book, _safe_unicode(helper_result.get("OUTPUT_PATH", "")))
                _set_converted_custom_values(book, _safe_unicode(helper_result.get("OUTPUT_PATH", "")), helper_result)
            if helper_result.get("STATUS") == "OK" or (helper_result.get("STATUS") == "SKIPPED" and helper_result.get("SKIP_REASON") == "SIZE_POLICY"):
                try:
                    checkpoint_state = "completed" if helper_result.get("STATUS") == "OK" else "skipped"
                    _write_book_checkpoint(result, options, _safe_unicode(helper_result.get("OUTPUT_PATH", "")), checkpoint_state, helper_result)
                except Exception, ex:
                    helper_result["CHECKPOINT_WARNING"] = _safe_unicode(ex)
                    progress_form.stop_requested = True
            elif not File.Exists(planned_output) and not File.Exists(_safe_unicode(result.get("file_path", "")) + ".webp-recovery.txt"):
                try:
                    # Only a normally returned helper proves its child workers
                    # have exited; a crashed/interrupted call remains pending.
                    _write_book_checkpoint(result, options, planned_output, "retryable", helper_result)
                except Exception, ex:
                    helper_result["CHECKPOINT_WARNING"] = _safe_unicode(ex)
                    progress_form.stop_requested = True
            _status_after_conversion(book, result, helper_result, options)
            conversion_results.append(helper_result)
            if hasattr(progress_form, "record_work"):
                progress_form.record_work(helper_result)

        timestamp = _safe_unicode(DateTime.Now.ToString("yyyyMMdd_HHmmss"))
        report_path = Path.Combine(REPORT_DIR, "webp_conversion_{0}_{1}.txt".format(timestamp, System.Guid.NewGuid().ToString("N")[:8]))
        report_text = _build_quality_trial_report(results, conversion_results, tool_path, options) if benchmark_mode else _build_conversion_report(results, conversion_results, tool_path, options)
        processed = len([r for r in conversion_results if r.get("STATUS", "") != "NOT_PROCESSED"])
        report_text = _run_report_status(report_text, total, processed, progress_form.stop_requested and processed < total)
        _write_text_file(report_path, report_text)
        report_text = _copy_reports_to_sources(report_text, report_path, results, options or {})
        _record_run_safely(report_path, report_text, options or {}, results)
    finally:
        try:
            try:
                if options.get("prefetch_record"):
                    _cleanup_prefetch(python_tool, options)
            except Exception, ex:
                MessageBox.Show("Temporary prefetch cleanup needs attention: " + _safe_unicode(ex) + "\nCache: " + options.get("prefetch_record", ""), "WebP Optimizer")
            finally:
                progress_form.finish()
        finally:
            _end_keep_awake(awake)

    report_form = ReportForm(report_text, report_path)
    report_form.ShowDialog()


# [P21] Native support definitions share this adapter namespace deliberately.
_SUPPORT_SCRIPT = Path.Combine(SCRIPT_DIR, "webp_runtime_support.py")
exec compile(File.ReadAllText(_SUPPORT_SCRIPT), _SUPPORT_SCRIPT, "exec")


# ===========================================================================
# [P19] ComicRack-discovered public entry points; keep hook metadata intact
# ===========================================================================
#@Name Optimize Archives
#@Key webp-optimizer-phase1
#@Hook Books
#@Image webp.png
#@Description Analyzer and archive converter for selected CBZ/CBR books. Writes ImageFormat custom values, preserves embedded metadata, and supports sample benchmarking.
def webp_optimizer_phase_one(books):
    """ComicRack Books hook: capture selection and guard UI re-entrancy."""
    global _RUN_ACTIVE
    if _RUN_ACTIVE:
        MessageBox.Show("A WebP Optimizer run is already active. Finish or stop it before starting another.", "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Information)
        return
    _RUN_ACTIVE = True
    try:
        _run_phase_two(list(books) if books else [])
    except Exception, ex:
        MessageBox.Show(_safe_unicode(ex), "WebP Optimizer", MessageBoxButtons.OK, MessageBoxIcon.Error)
    finally:
        _RUN_ACTIVE = False


#@Name WebP Optimizer Run History
#@Key webp-optimizer-history
#@Hook Library
#@Image webp.png
#@Description Reopen previous WebP Optimizer results and retained previews without selecting comics.
def webp_optimizer_history(books):
    """ComicRack Library hook: open read-only/history actions without a selection."""
    global _RUN_ACTIVE
    if _RUN_ACTIVE:
        MessageBox.Show("Finish or stop the active run before opening history from the library menu.", "WebP Optimizer")
        return
    _RUN_ACTIVE = True
    try:
        _history_trace("Opening standalone independent history")
        _open_history_external(allow_retest=False)
    except Exception, ex:
        _history_trace("Independent history failed: " + _safe_unicode(ex))
        MessageBox.Show(_safe_unicode(ex), "WebP Optimizer")
    finally:
        _RUN_ACTIVE = False
