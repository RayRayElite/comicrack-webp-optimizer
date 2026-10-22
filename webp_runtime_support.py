# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""IronPython support for the native adapter: setup, storage, power and recovery.

Loaded explicitly into WebPOptimizer.py's namespace after its definitions, so
the same ComicRack objects, paths and test seams are used without a second
module instance. Keep Python 2 syntax here. The CPython worker is separate.
"""

# [S01] Workflow custom values: image content and work status are independent.
def _book_custom(book, key):
    try:
        return _safe_unicode(book.GetCustomValue(key))
    except Exception:
        return ""


def _set_workflow_status(book, status, reason, source):
    """Only annotate the existing library entry; never relink copies or tests."""
    try:
        values = {"WebPStatus": status, "WebPReason": _safe_unicode(reason), "WebPSourceStamp": _checkpoint_signature(source)}
        for key, value in values.items():
            if _book_custom(book, key) != value:
                book.SetCustomValue(key, value)
    except Exception:
        pass  # Metadata support varies; archive safety must not depend on labels.


def _legacy_size_policy_reason(reason):
    """Recognize only messages emitted by older size-policy decisions."""
    return (reason == "Converted output was not smaller than the source archive."
            or (reason.startswith("Converted output saved only ") and reason.endswith("% which is below the required 3.00% threshold."))
            or (reason.startswith("Converted output grew by ") and reason.endswith("% which exceeds the allowed 1.00% growth threshold."))
            or reason == "Previously rejected by the same size policy; unchanged source was not encoded again.")


def _status_after_scan(book, result):
    source = _safe_unicode(result.get("file_path", ""))
    image_format = result.get("image_format", "")
    if image_format in ["ERROR", "MISSING", "UNSUPPORTED", "NO_IMAGES"] or result.get("status") == "No image pages":
        status = "Needs attention"
    else:
        old = _book_custom(book, "WebPStatus")
        output_exists = old != "Copy created" or File.Exists(_book_custom(book, "WebPOutput"))
        signature = _checkpoint_signature(source)
        if old in ["Completed", "Skipped", "Skipped - size policy", "Copy created"] and output_exists and signature and _book_custom(book, "WebPSourceStamp") == signature:
            previous_reason = _book_custom(book, "WebPReason")
            if old == "Skipped" and _legacy_size_policy_reason(previous_reason):
                _set_workflow_status(book, "Skipped - size policy", previous_reason, source)
            return  # Keep a prior unchanged outcome visible until an explicit retry.
        status = "Already WebP" if image_format == "WEBP" else ("Ready" if result.get("eligible") else "Skipped")
    _set_workflow_status(book, status, result.get("notes", ""), source)


def _status_after_conversion(book, scan, result, options):
    """Tests do not complete a source; copies leave ImageFormat unchanged."""
    if options.get("run_mode") == "Test savings & quality" or result.get("STATUS") == "NOT_PROCESSED":
        return
    status, reason = result.get("STATUS"), result.get("SKIP_REASON", "")
    if status == "ERROR":
        label = "Needs attention"
    elif status == "OK" or (reason == "RESUMED" and result.get("OUTPUT_PATH")):
        label = "Completed" if options.get("run_mode") == "Replace Originals" else "Copy created"
    elif reason == "SIZE_POLICY" or (reason == "RESUMED" and result.get("RESUMED_SKIP_REASON") == "SIZE_POLICY"):
        label = "Skipped - size policy"
    elif scan.get("image_format") == "WEBP":
        label = "Already WebP"
    elif scan.get("image_format") in ["ERROR", "MISSING", "UNSUPPORTED", "NO_IMAGES"]:
        label = "Needs attention"
    else:
        label = "Skipped"
    source = result.get("OUTPUT_PATH", "") if label == "Completed" else scan.get("file_path", "")
    _set_workflow_status(book, label, result.get("MESSAGE", scan.get("notes", "")), source)
    try:
        book.SetCustomValue("WebPOutput", _safe_unicode(result.get("OUTPUT_PATH", "")) if label in ["Completed", "Copy created"] else "")
    except Exception:
        pass


# [S02] Windows APIs. Keep requests on the UI thread and restore prior flags.
_NATIVE_TYPE = None


def _compile_native_bridge():
    """Compile once on the host thread; avoid IronPython delegate binding on workers."""
    global _NATIVE_TYPE
    clr.AddReference("Microsoft.CSharp")
    from Microsoft.CSharp import CSharpCodeProvider
    from System.CodeDom.Compiler import CompilerParameters, TempFileCollection
    cache = Path.Combine(REPORT_DIR, "RuntimeCache")
    _ensure_directory(cache)
    parameters = CompilerParameters()
    parameters.GenerateInMemory = True
    parameters.TempFiles = TempFileCollection(cache, False)
    parameters.ReferencedAssemblies.Add("System.dll")
    parameters.ReferencedAssemblies.Add("System.Drawing.dll")
    parameters.ReferencedAssemblies.Add("System.Windows.Forms.dll")
    provider = CSharpCodeProvider()
    try:
        result = provider.CompileAssemblyFromSource(parameters, File.ReadAllText(Path.Combine(SCRIPT_DIR, "NativeWindows.cs")))
        if result.Errors.HasErrors:
            raise Exception("Windows API bridge could not compile: " + _safe_unicode(result.Errors[0]))
        _NATIVE_TYPE = result.CompiledAssembly.GetType("WebPOptimizerRuntime.NativeWindows")
    finally:
        provider.Dispose()
        parameters.TempFiles.Delete()


def _native_call(method, arguments):
    if _NATIVE_TYPE is None:
        _compile_native_bridge()
    # Invoke on the calling thread: execution-state requests are thread-local.
    return _NATIVE_TYPE.GetMethod(method).Invoke(None, System.Array[System.Object](arguments))


def _begin_keep_awake(options):
    """Prevent idle system sleep only; do not force the display on or change plans."""
    if not options.get("keep_awake", False):
        return None
    previous = long(_native_call("SetThreadExecutionState", [System.UInt32(0x80000001)]))
    if not previous:
        raise Exception("Windows could not enable Keep PC awake. Uncheck it to continue without the request.")
    return previous


def _end_keep_awake(previous):
    if previous is not None:
        # Restore the thread's former requirements, including any host request.
        if not _native_call("SetThreadExecutionState", [System.UInt32(previous | 0x80000000)]):
            raise Exception("Windows could not restore its previous execution state.")


def _available_space(folder):
    """Bound local/UNC space queries so a disconnected share cannot freeze the UI."""
    try:
        free = long(_native_call("DiskFreeBounded", [System.String(folder)]))
        return free if free >= 0 else None
    except Exception:
        return None


# [S03] Pre-run estimates use cached library sizes, not a second NAS-wide scan.
def _preflight_summary(books, options):
    mode = options.get("run_mode", "Analyze Only")
    rows, volumes, unknown = [], {}, 0
    counts = {}
    largest = 0L
    for book in books:
        source = _safe_unicode(getattr(book, "FilePath", ""))
        try:
            size = max(0L, long(getattr(book, "FileSize", 0) or 0))
        except Exception:
            size = 0L
        unknown += int(size == 0)
        largest = max(largest, size)
        status = _book_custom(book, "WebPStatus") or "Not checked"
        counts[status] = counts.get(status, 0) + 1
        if source:
            folder = Path.GetDirectoryName(Path.GetFullPath(source))
            key = Path.GetPathRoot(folder).lower()
            group = volumes.setdefault(key, {"folder": folder, "bytes": 0L, "largest": 0L, "retained": 0L, "budget": 0L})
            group["bytes"] += size
            group["largest"] = max(group["largest"], size)
    rows += [("Action", mode), ("Selected books", str(len(books))),
             ("Latest analysis", "; ".join(key + ": " + str(counts[key]) for key in sorted(counts))),
             ("Quality / encoder", options.get("quality_mode", QUALITY_MODE_VALUES[0]) + " / " + options.get("encoder_backend", ENCODER_BACKEND_VALUES[0])),
             ("Temporary storage", options.get("work_dir", "") or "Beside each source"),
             ("Keep PC awake", "Yes (display may turn off)" if options.get("keep_awake") else "No")]
    warnings = []
    if mode != "Analyze Only":
        retain = mode == "Create WebP Copies" or (mode == "Replace Originals" and options.get("create_backup"))
        rows.append(("Originals retained", "Yes — copies/backups do not reclaim disk space" if retain else ("Unchanged during quality tests" if mode == "Test savings & quality" else "No permanent backup selected")))
        for group in volumes.values():
            group["retained"] = group["bytes"] if retain else 0L
            group["budget"] = group["largest"] * (3 if options.get("create_backup") else 2)
            if not options.get("work_dir"):
                group["budget"] += group["largest"] * 4
        if options.get("work_dir"):
            folder = Path.GetFullPath(options["work_dir"])
            key = Path.GetPathRoot(folder).lower()
            group = volumes.setdefault(key, {"folder": folder, "bytes": 0L, "largest": 0L, "retained": 0L, "budget": 0L})
            group["budget"] += largest * 4
        for key in sorted(volumes):
            group = volumes[key]
            free = _available_space(group["folder"])
            rows += [("Volume " + key, "Free " + (_format_size(free) if free is not None else "unavailable")),
                     ("  Extra space scenario", _format_size(group["retained"]) + " retained + " + _format_size(group["budget"]) + " active-book budget")]
            if free is None:
                warnings.append("Free space could not be checked for " + key)
            elif free < group["retained"] + group["budget"]:
                warnings.append("The same-size output scenario exceeds free space on " + key + ". Use smaller batches or review copy/backup storage.")
        if mode == "Test savings & quality":
            warnings.append("Quality tests process up to three books. Storage budgets above are conservative; retained preview PNGs need additional space.")
        if unknown:
            warnings.append(str(unknown) + " cached book sizes are unavailable; storage estimates are incomplete.")
    return rows, warnings


class PreflightForm(Form):
    """Review storage consequences before starting; estimates are not promises."""
    def __init__(self, books, options):
        self.Text = "WebP Optimizer - Review this batch"
        self.Font = Font("Segoe UI", 9.0)
        self.BackColor = Color.White
        self.ClientSize = Size(860, 640)
        self.StartPosition = FormStartPosition.CenterParent
        self.AutoScaleMode = AutoScaleMode.Font
        self.FormBorderStyle, self.MaximizeBox = FormBorderStyle.FixedDialog, False
        _ui_label(self, "Ready to process this selection?", 24, 20, 800, 34, True)
        listing = _new_listview()
        listing.View = View.Details
        listing.Location, listing.Size = Point(24, 74), Size(812, 350)
        listing.Columns.Add("Setting", 205)
        listing.Columns.Add("Details", 580)
        rows, warnings = _preflight_summary(books, options)
        for name, value in rows:
            item = ListViewItem(name)
            item.SubItems.Add(value)
            listing.Items.Add(item)
        self.Controls.Add(listing)
        note = TextBox()
        note.ReadOnly, note.Multiline, note.ScrollBars = True, True, System.Windows.Forms.ScrollBars.Vertical
        note.Location, note.Size = Point(24, 440), Size(812, 130)
        note.Text = "\r\n".join(warnings + ["Storage assumes outputs equal source sizes, using cached analysis. Actual savings vary; per-book space checks still apply. Mount points/aliases and retained previews may need more space."])
        self.Controls.Add(note)
        self._proceed = Button()
        self._proceed.Text, self._proceed.DialogResult = "Start batch", DialogResult.OK
        self._proceed.Location, self._proceed.Size = Point(584, 592), Size(120, 32)
        cancel = Button()
        cancel.Text, cancel.DialogResult = "Cancel", DialogResult.Cancel
        cancel.Location, cancel.Size = Point(716, 592), Size(120, 32)
        self.Controls.Add(self._proceed)
        self.Controls.Add(cancel)
        self.AcceptButton, self.CancelButton = self._proceed, cancel


def _confirm_batch(books, options):
    form = PreflightForm(books, options)
    try:
        return form.ShowDialog() == DialogResult.OK
    finally:
        form.Dispose()


# [S04] Setup diagnostics and archive inspection share the CPython bridge.
def _diagnostic_worker(arguments):
    python = _find_python_tool()
    if not python:
        return {"STATUS": "ERROR", "CHECK_MESSAGE": "Python 3 was not found. Install Python 3.9+ with the py launcher or PATH enabled, then install Pillow with: py -3 -m pip install Pillow"}
    info = ProcessStartInfo()
    info.FileName = python
    info.Arguments = ("-3 " if python == "py" else "") + _quote_argument(HELPER_SCRIPT) + " " + " ".join(_quote_argument(arg) for arg in arguments)
    info.UseShellExecute, info.CreateNoWindow = False, True
    info.RedirectStandardOutput = info.RedirectStandardError = True
    process = Process()
    process.StartInfo = info
    try:
        output, errors = _wait_for_process(process)
        result = _parse_helper_output(output)
        if process.ExitCode != 0 or result.get("STATUS") != "OK":
            result["STATUS"] = "ERROR"
            result["CHECK_MESSAGE"] = result.get("CHECK_MESSAGE", "") or (errors[-2000:] if errors else "The diagnostic worker failed.")
            if "PIL" in errors or "Pillow" in errors:
                result["CHECK_MESSAGE"] += "\nInstall Pillow for this Python: py -3 -m pip install Pillow"
        return result
    except Exception, ex:
        return {"STATUS": "ERROR", "CHECK_MESSAGE": _safe_unicode(ex)}
    finally:
        process.Dispose()


def _setup_checks_core(options):
    """Use small generated files only; report exactly which storage was tested."""
    archive = _find_archive_tool() or ""
    if options.get("run_mode") == "Analyze Only":
        if not archive:
            return {"STATUS": "ERROR", "CHECK_MESSAGE": "7-Zip missing. Restore ComicRack's Resources archive tool."}
        info = ProcessStartInfo()
        info.FileName, info.Arguments = archive, "i"
        info.UseShellExecute, info.CreateNoWindow = False, True
        info.RedirectStandardOutput = info.RedirectStandardError = True
        process = Process()
        process.StartInfo = info
        try:
            _wait_for_process(process)
            if process.ExitCode:
                raise Exception("7-Zip could not start correctly")
            _ensure_directory(REPORT_DIR)
            probe = Path.Combine(REPORT_DIR, "setup-" + System.Guid.NewGuid().ToString("N") + ".tmp")
            try:
                _write_text_file(probe, "Setup write check")
            finally:
                if File.Exists(probe):
                    File.Delete(probe)
            return {"STATUS": "OK", "CHECK_ARCHIVE_TOOL": "OK | 7-Zip runs", "CHECK_STORAGE": "OK | Reports folder is writable", "CHECK_MESSAGE": "Analyze Only does not need Python or an encoder. Choose a conversion action to check those dependencies."}
        except Exception, ex:
            return {"STATUS": "ERROR", "CHECK_MESSAGE": _safe_unicode(ex)}
        finally:
            process.Dispose()
    work = options.get("work_dir", "") or options.get("_setup_default_work_dir", "") or Path.Combine(REPORT_DIR, "SetupChecks")
    args = ["--check-setup", "--encoder-backend", options.get("encoder_backend", ENCODER_BACKEND_VALUES[0]), "--archive-tool", archive, "--work-dir", work]
    if _is_cbr_rebuild_mode(options):
        args += ["--require-rar", "--rar-tool", _find_rar_tool() or ""]
    return _diagnostic_worker(args)


class SetupForm(Form):
    def __init__(self, options):
        self._options, self._busy = options, False
        self.Text = "WebP Optimizer - Check setup"
        self.Font, self.BackColor = Font("Segoe UI", 9.0), Color.White
        self.ClientSize = Size(780, 470)
        self.StartPosition = FormStartPosition.CenterParent
        self.AutoScaleMode = AutoScaleMode.Font
        self.FormBorderStyle, self.MaximizeBox = FormBorderStyle.FixedDialog, False
        _ui_label(self, "Check this workflow", 24, 20, 730, 34, True)
        _ui_label(self, "Checks use disposable files. Nothing is installed automatically and no comic is changed.", 24, 64, 730, 44)
        self._text = TextBox()
        self._text.Multiline, self._text.ReadOnly = True, True
        self._text.ScrollBars = System.Windows.Forms.ScrollBars.Vertical
        self._text.Location, self._text.Size = Point(24, 120), Size(732, 280)
        self.Controls.Add(self._text)
        self._close = Button()
        self._close.Text = "Close"
        self._close.Location, self._close.Size = Point(636, 420), Size(120, 32)
        self._close.Click += self._close_clicked
        self.Controls.Add(self._close)
        self.FormClosing += self._closing
        self.Shown += self._shown

    def _shown(self, sender, event):
        self.BeginInvoke(System.Windows.Forms.MethodInvoker(self._run))

    def _run(self):
        self._busy, self._close.Enabled = True, False
        self._text.Text = "Checking prerequisites and temporary storage..."
        try:
            result = _setup_checks(self._options)
            self._text.Text = ("Setup passed" if result.get("STATUS") == "OK" else "Setup needs attention") + "\r\n\r\n" + "\r\n\r\n".join(key.replace("CHECK_", "").replace("_", " ") + ": " + _safe_unicode(result[key]) for key in sorted(result) if key.startswith("CHECK_"))
        except Exception, ex:
            self._text.Text = "Setup check failed: " + _safe_unicode(ex)
        finally:
            self._busy, self._close.Enabled = False, True

    def _closing(self, sender, event):
        event.Cancel = self._busy

    def _close_clicked(self, sender, event):
        self.Close()


# [S05] Recovery: inspect archives; archive resolved tracking records, not comics.
def _read_checkpoint(path):
    document = XmlDocument()
    document.XmlResolver = None
    document.Load(path)
    if document.DocumentElement.Name != "Checkpoint" or document.DocumentElement.GetAttribute("version") not in ["1", "2"]:
        raise Exception("Unsupported checkpoint: " + path)
    return document


def _recovery_paths(item):
    paths = [("Source", item.get("source", "")), ("Converted", item.get("output", ""))]
    journal = item.get("source", "") + ".webp-recovery.txt"
    if File.Exists(journal):
        fields = {}
        for line in File.ReadAllLines(journal):
            if ": " in line:
                key, value = line.split(": ", 1)
                if key in ["Source", "Converted", "Final", "Rollback", "Backup"]:
                    fields[key] = value
        if not all(fields.get(key) for key in ["Source", "Converted", "Final", "Rollback"]):
            raise Exception("Recovery note is incomplete; inspect it manually: " + journal)
        if Path.GetFullPath(fields["Source"]).lower() != Path.GetFullPath(item["source"]).lower():
            raise Exception("Recovery note points to a different source; manual review is required")
        if item.get("output") and Path.GetFullPath(fields["Converted"]).lower() != Path.GetFullPath(item["output"]).lower():
            raise Exception("Checkpoint and recovery note disagree about the converted output")
        paths[1] = ("Converted", fields["Converted"])
        paths += [(key, fields[key]) for key in ["Final", "Rollback", "Backup"] if fields.get(key)]
    return paths


def _load_recovery_items(books):
    records, sources = [], set()
    pending = Path.Combine(Path.Combine(REPORT_DIR, "Checkpoints"), "Pending")
    if Directory.Exists(pending):
        for path in Directory.GetFiles(pending, "*.xml"):
            try:
                root = _read_checkpoint(path).DocumentElement
                source = _safe_unicode(root.GetAttribute("source"))
                if Path.GetFullPath(path).lower() != Path.GetFullPath(_pending_checkpoint_path(source)).lower():
                    raise Exception("Pending record does not match its source key")
                records.append({"source": source, "output": _safe_unicode(root.GetAttribute("output")), "pending": path, "policy": _safe_unicode(root.GetAttribute("policyRecord")), "updated": _safe_unicode(root.GetAttribute("updated")), "workerPid": root.GetAttribute("workerPid"), "workerStart": root.GetAttribute("workerStart")})
                sources.add(source.lower())
            except Exception, ex:
                records.append({"source": path, "error": _safe_unicode(ex), "pending": path})
    for book in books:
        source = _safe_unicode(getattr(book, "FilePath", ""))
        if source and source.lower() not in sources and File.Exists(source + ".webp-recovery.txt"):
            records.append({"source": source, "output": "", "pending": "", "policy": "", "updated": "Recovery note beside selected source"})
    return records


def _worker_is_running(item):
    """Compare PID and start time to avoid mistaking a reused PID for the helper."""
    if not item.get("workerPid"):
        return False  # The explicit user confirmation still applies to old records.
    try:
        process = Process.GetProcessById(int(item["workerPid"]))
    except System.ArgumentException:
        return False
    try:
        return not process.HasExited and str(process.StartTime.ToUniversalTime().Ticks) == item.get("workerStart")
    finally:
        process.Dispose()


def _check_recovery_item(item):
    item.pop("checked", None)
    item.pop("snapshot", None)
    if item.get("error"):
        raise Exception(item["error"])
    if _worker_is_running(item):
        raise Exception("The recorded helper is still running. Wait for it to finish before resolving this attempt.")
    paths = _recovery_paths(item)
    snapshot = dict((path, _checkpoint_signature(path)) for role, path in paths if path)
    checks = {}
    work = Path.Combine(REPORT_DIR, "RecoveryChecks")
    for role, path in paths:
        if not path or not File.Exists(path):
            checks[role] = "Missing"
            continue
        result = _diagnostic_worker(["--check-archive", path, "--archive-tool", _find_archive_tool() or "", "--work-dir", work])
        checks[role] = result.get("CHECK_MESSAGE", "Check failed")
        if result.get("STATUS") == "OK":
            checks[role + "Valid"] = True
    if any(_checkpoint_signature(path) != signature for path, signature in snapshot.items()):
        raise Exception("A file changed during inspection. Check again before resolving.")
    item["checked"], item["snapshot"] = checks, snapshot
    return checks


def _safe_tracking_path(path):
    """Accept only generated checkpoint XML directly under our checkpoint tree."""
    full = Path.GetFullPath(path)
    root = Path.GetFullPath(Path.Combine(REPORT_DIR, "Checkpoints")).rstrip("\\/")
    parent = Path.GetDirectoryName(full)
    leaf = Path.GetFileNameWithoutExtension(full)
    bucket = Path.GetFileName(parent)
    hexadecimal = lambda text: len(text) == 64 and all(c in "0123456789abcdef" for c in text.lower())
    if Path.GetDirectoryName(parent).lower() != root.lower() or not hexadecimal(leaf) or (bucket != "Pending" and not hexadecimal(bucket)) or Path.GetExtension(full).lower() != ".xml":
        raise Exception("Refusing a tracking record outside generated checkpoints: " + full)
    current = full
    while current and Path.GetFullPath(current).lower().startswith(Path.GetFullPath(REPORT_DIR).lower()):
        if (File.Exists(current) or Directory.Exists(current)) and (File.GetAttributes(current) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
            raise Exception("Redirected tracking paths cannot be archived")
        if Path.GetFullPath(current).lower() == Path.GetFullPath(REPORT_DIR).lower():
            break
        current = Path.GetDirectoryName(current)
    return full


def _allow_recovery_retry(item, confirmed_stopped):
    """Allow retry only with a checked source and no unresolved converted/rollback file.

    No comic archive is changed. Records and a resolved recovery note are moved
    to an audit folder, keeping the pending index until the final move succeeds.
    """
    if not confirmed_stopped or _worker_is_running(item):
        raise Exception("Confirm that the previous helper/encoder has stopped")
    checked, snapshot = item.get("checked", {}), item.get("snapshot", {})
    if not checked.get("SourceValid"):
        raise Exception("Check files first; the source must be readable before retrying")
    paths = _recovery_paths(item)
    current = dict((path, _checkpoint_signature(path)) for role, path in paths if path)
    if current != snapshot:
        raise Exception("Files changed since the check. Check files again.")
    source = item["source"]
    for role, path in paths:
        if role in ["Converted", "Rollback"] and path and File.Exists(path):
            raise Exception("Review and resolve the " + role.lower() + " file first: " + path + ". No comic files will be deleted by this screen.")
        if role == "Final" and path.lower() != source.lower() and File.Exists(path):
            raise Exception("A final archive already exists. Resolve/relink this replacement before retrying.")
    records = []
    for key in ["policy", "pending"]:
        if item.get(key) and File.Exists(item[key]):
            path = _safe_tracking_path(item[key])
            root = _read_checkpoint(path).DocumentElement
            if Path.GetFullPath(root.GetAttribute("source")).lower() != Path.GetFullPath(source).lower():
                raise Exception("Tracking record belongs to a different source")
            fresh = {"workerPid": root.GetAttribute("workerPid"), "workerStart": root.GetAttribute("workerStart")}
            if _worker_is_running(fresh):
                raise Exception("The helper is still running; retry cannot be allowed")
            records.append(path)
    # Validate every metadata target before moving any of them.
    journal = source + ".webp-recovery.txt"
    if File.Exists(journal):
        if (File.GetAttributes(journal) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
            raise Exception("Redirected recovery note cannot be archived")
        records.insert(max(0, len(records) - 1), journal)
    if not records:
        raise Exception("No tracking records remain; refresh the recovery list")
    folder = Path.Combine(Path.Combine(REPORT_DIR, "ResolvedAttempts"), System.Guid.NewGuid().ToString("N"))
    for parent in [REPORT_DIR, Path.Combine(REPORT_DIR, "ResolvedAttempts")]:
        if Directory.Exists(parent) and (File.GetAttributes(parent) & FileAttributes.ReparsePoint) == FileAttributes.ReparsePoint:
            raise Exception("Redirected recovery destinations cannot be used")
    _ensure_directory(folder)
    _write_text_file(Path.Combine(folder, "Resolution.txt"), "Retry allowed after explicit review.\r\nSource: " + source + "\r\n" + "\r\n".join(role + ": " + path for role, path in paths))
    for index, path in enumerate(records):
        File.Move(path, Path.Combine(folder, str(index) + "-" + Path.GetFileName(path)))
    return folder


def _record_worker_started(source, options, process):
    """Add child identity after launch; retain conservative pending state on failure."""
    for path in [_checkpoint_path(source, options), _pending_checkpoint_path(source)]:
        if not File.Exists(path):
            continue
        document = _read_checkpoint(path)
        document.DocumentElement.SetAttribute("workerPid", str(process.Id))
        document.DocumentElement.SetAttribute("workerStart", str(process.StartTime.ToUniversalTime().Ticks))
        temporary = path + "." + System.Guid.NewGuid().ToString("N") + ".tmp"
        try:
            document.Save(temporary)
            File.Replace(temporary, path, None)
        finally:
            if File.Exists(temporary):
                File.Delete(temporary)


class RecoveryForm(Form):
    def __init__(self, books):
        self._books, self._busy, self._items = books, False, []
        self.Text = "WebP Optimizer - Interrupted work"
        self.Font, self.BackColor = Font("Segoe UI", 9.0), Color.White
        self.ClientSize = Size(1020, 680)
        self.StartPosition = FormStartPosition.CenterParent
        self.AutoScaleMode = AutoScaleMode.Font
        self.FormBorderStyle, self.MaximizeBox = FormBorderStyle.FixedDialog, False
        _ui_label(self, "Review interrupted work", 24, 20, 970, 34, True)
        _ui_label(self, "Check archive readability and open the relevant folder. Comic files are never automatically installed or deleted here.", 24, 62, 970, 40)
        self._list = _new_listview()
        self._list.View, self._list.FullRowSelect, self._list.MultiSelect = View.Details, True, False
        self._list.HideSelection = False
        self._list.Location, self._list.Size = Point(24, 110), Size(972, 180)
        for title, width in [("Source / record", 320), ("Location", 430), ("Updated", 200)]:
            self._list.Columns.Add(title, width)
        self._list.SelectedIndexChanged += self._selected
        self.Controls.Add(self._list)
        self._paths = _new_listview()
        self._paths.View, self._paths.FullRowSelect, self._paths.MultiSelect = View.Details, True, False
        self._paths.Location, self._paths.Size = Point(24, 310), Size(972, 170)
        for title, width in [("File", 100), ("Path", 680), ("Size / state", 170)]:
            self._paths.Columns.Add(title, width)
        self.Controls.Add(self._paths)
        self._note = _ui_label(self, "Select an attempt, then Check files. Readability does not prove visual quality or intended output identity.", 24, 494, 972, 80)
        self._confirmed = _new_checkbox()
        self._confirmed.Text = "I have confirmed that the previous helper and encoders have stopped."
        self._confirmed.Location, self._confirmed.Size = Point(24, 580), Size(950, 28)
        self.Controls.Add(self._confirmed)
        self._buttons = {}
        for index, (title, handler) in enumerate([("Check files", self._check), ("Open folder", self._open_folder), ("Allow retry", self._retry), ("Refresh", self._refresh_clicked), ("Close", self._close_clicked)]):
            button = Button()
            button.Text = title
            button.Location, button.Size = Point(24 + index * 196, 628), Size(180, 32)
            button.Click += handler
            self.Controls.Add(button)
            self._buttons[title] = button
        self._confirmed.CheckedChanged += self._update_actions
        self.FormClosing += self._closing
        self.Shown += self._shown

    def _update_actions(self, sender=None, event=None):
        record = self._current()
        available = record is not None and not self._busy
        self._buttons["Check files"].Enabled = available
        self._buttons["Open folder"].Enabled = available
        self._buttons["Allow retry"].Enabled = available and bool(record.get("checked", {}).get("SourceValid")) and bool(self._confirmed.Checked)
        self._confirmed.Enabled = not self._busy

    def _shown(self, sender, event):
        self.BeginInvoke(System.Windows.Forms.MethodInvoker(self._refresh_safe))

    def _refresh_safe(self):
        try:
            self._refresh()
        except Exception, ex:
            self._note.Text = "Recovery list could not be loaded: " + _safe_unicode(ex)

    def _current(self):
        return self._list.SelectedItems[0].Tag if self._list.SelectedItems.Count else None

    def _refresh(self):
        self._items = _load_recovery_items(self._books)
        self._list.Items.Clear()
        for record in self._items:
            item = ListViewItem(Path.GetFileName(record.get("source", "")))
            item.SubItems.Add(Path.GetDirectoryName(record.get("source", "")))
            item.SubItems.Add(record.get("updated", "Needs inspection"))
            item.Tag = record
            self._list.Items.Add(item)
        self._selected(None, None)
        if not self._items:
            self._note.Text = "No pending attempts found. Recovery notes beside currently selected books are also checked."

    def _selected(self, sender, event):
        self._paths.Items.Clear()
        self._confirmed.Checked = False
        record = self._current()
        self._update_actions()
        if not record:
            return
        try:
            if record.get("error"):
                self._note.Text = record["error"]
                return
            self._note.Text = "Check files before allowing retry. Resolve leftover converted/final/rollback files first; backups can remain."
            for role, path in _recovery_paths(record):
                if not path:
                    continue
                item = ListViewItem(role)
                item.SubItems.Add(path)
                item.SubItems.Add(_format_size(FileInfo(path).Length) if File.Exists(path) else "Missing")
                item.Tag = path
                self._paths.Items.Add(item)
        except Exception, ex:
            self._note.Text = _safe_unicode(ex)

    def _check(self, sender, event):
        record = self._current()
        if not record or self._busy:
            return
        self._busy = True
        self._update_actions()
        self._list.Enabled = False
        try:
            self._note.Text = "Checking archive integrity and decoding pages..."
            result = _check_recovery_item(record)
            self._note.Text = " | ".join(key + ": " + _safe_unicode(value) for key, value in result.items() if not key.endswith("Valid"))
        except Exception, ex:
            self._note.Text = _safe_unicode(ex)
        finally:
            self._busy = False
            self._list.Enabled = True
            self._update_actions()

    def _open_folder(self, sender, event):
        if self._busy:
            return
        try:
            record = self._current()
            path = self._paths.SelectedItems[0].Tag if self._paths.SelectedItems.Count else (record.get("source", "") if record else "")
            if path:
                folder = Path.GetDirectoryName(Path.GetFullPath(path))
                if Directory.Exists(folder):
                    Process.Start("explorer.exe", _quote_argument(folder))
        except Exception, ex:
            MessageBox.Show("Could not open the folder: " + _safe_unicode(ex), "WebP Optimizer")

    def _retry(self, sender, event):
        record = self._current()
        if not record or self._busy:
            return
        try:
            folder = _allow_recovery_retry(record, bool(self._confirmed.Checked))
            self._refresh()
            self._note.Text = "Tracking records archived in " + folder + ". Select the book and start a new run to retry; nothing starts automatically."
        except Exception, ex:
            MessageBox.Show(_safe_unicode(ex), "Retry needs attention")

    def _refresh_clicked(self, sender, event):
        if not self._busy:
            self._refresh_safe()

    def _close_clicked(self, sender, event):
        if not self._busy:
            self.Close()

    def _closing(self, sender, event):
        event.Cancel = self._busy


# [S07] Process-isolated history. Never construct the browser in ComicRack.
def _history_runtime_directory():
    candidates = []
    for assembly in System.AppDomain.CurrentDomain.GetAssemblies():
        if assembly.GetName().Name == "IronPython" and assembly.Location:
            candidates.append(Path.GetDirectoryName(assembly.Location))
    process = Process.GetCurrentProcess()
    try:
        candidates.append(Path.GetDirectoryName(process.MainModule.FileName))
    finally:
        process.Dispose()
    candidates.append(Path.Combine(ROOT_DIR, "ComicRackCE_nightly"))
    for folder in candidates:
        if all(File.Exists(Path.Combine(folder, name)) for name in ["IronPython.dll", "Microsoft.Dynamic.dll", "Microsoft.Scripting.dll"]):
            return folder
    raise Exception("History could not locate ComicRack's IronPython runtime DLLs. No in-process fallback was attempted.")


def _open_history_external(allow_retest=True, dark=None, self_test="", test_reports=""):
    """Wait for an independent STA process; exchange only whitelisted XML choices."""
    if dark is None:
        dark = _DARK_MODE if _DARK_MODE is not None else _load_settings()[0].get("dark_mode", "False").lower() == "true"
    folder = Path.Combine(SCRIPT_DIR, "Reports", "HistorySessions")
    _ensure_directory(folder)
    session = System.Guid.NewGuid().ToString("N")
    request_path = Path.Combine(folder, session + ".request.xml")
    response_path = Path.Combine(folder, session + ".response.xml")
    document = XmlDocument()
    root = document.CreateElement("HistorySession")
    root.SetAttribute("runtime", _history_runtime_directory())
    root.SetAttribute("allowRetest", str(bool(allow_retest)))
    root.SetAttribute("dark", str(bool(dark)))
    if self_test:
        if self_test not in ["close", "retest", "fail"]:
            raise Exception("Unknown history self-test")
        root.SetAttribute("testReports", test_reports)
    document.AppendChild(root)
    document.Save(request_path)
    process = Process()
    try:
        info = ProcessStartInfo()
        info.FileName = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System), "WindowsPowerShell", "v1.0", "powershell.exe")
        info.Arguments = "-NoProfile -NonInteractive -STA -WindowStyle Hidden -ExecutionPolicy Bypass -File " + _quote_argument(Path.Combine(SCRIPT_DIR, "history_host.ps1")) + " -RequestPath " + _quote_argument(request_path)
        if self_test:
            info.Arguments += " -SelfTest " + self_test
        info.UseShellExecute, info.CreateNoWindow = False, True
        info.WindowStyle = System.Diagnostics.ProcessWindowStyle.Hidden
        info.RedirectStandardOutput = info.RedirectStandardError = True
        process.StartInfo = info
        _history_trace("Launching independent history helper")
        output, errors = _wait_for_process(process)
        _history_trace("History helper exited: " + str(process.ExitCode))
        if process.ExitCode != 0 or not File.Exists(response_path):
            details = "Exit code: " + str(process.ExitCode) + "\r\n" + errors + "\r\n" + output
            _write_text_file(Path.Combine(REPORT_DIR, "history-helper-error.log"), details[-32768:])
            raise Exception("The separate history window closed unexpectedly. ComicRack is still running. See Reports/history-helper-error.log.")
        response = XmlDocument()
        response.XmlResolver = None
        response.Load(response_path)
        result = response.DocumentElement
        if result.Name != "HistoryResult" or result.GetAttribute("status") not in ["closed", "prepared"]:
            raise Exception("Invalid history helper response")
        if result.GetAttribute("status") == "closed":
            return None
        if not allow_retest:
            raise Exception("Unexpected retest response from read-only history")
        choices = {}
        for value in result.SelectNodes("Value"):
            key = _safe_unicode(value.GetAttribute("key"))
            if key in ["encoder_backend", "cbr_mode", "page_workers", "work_dir"]:
                choices[key] = _safe_unicode(value.GetAttribute("value"))
        return {"options": choices}
    finally:
        process.Dispose()
        # Exact files from this session only; never remove a directory or report.
        for path in [request_path, response_path, response_path + ".tmp"]:
            try:
                if File.Exists(path):
                    File.Delete(path)
            except Exception:
                pass


# Sequential options/history navigation avoids nested modal host callbacks.
def _choose_options_with_history(books):
    draft = None
    while True:
        options_form = OptionsForm()
        options_form._selection_books = books
        try:
            if draft is not None:
                options_form._restore_draft(draft)
            choice = options_form.ShowDialog()
            if choice == DialogResult.OK:
                return options_form.options
            if choice not in [DialogResult.Retry, DialogResult.Yes]:
                return None
            draft = options_form._collect_options()
            # Preserve the checkbox preference even while replacement is disabled.
            draft["create_backup"] = bool(options_form._backup_checkbox.Checked)
        finally:
            if hasattr(options_form, "Dispose"):
                options_form.Dispose()
        if choice == DialogResult.Yes:
            try:
                chosen = _run_performance_test(books, draft)
                if chosen:
                    draft["page_workers"] = chosen
            except Exception, ex:
                MessageBox.Show("Benchmark could not finish: " + _safe_unicode(ex), "Worker benchmark")
            continue
        _history_trace("Options returned and disposed; opening independent history")
        try:
            retest = _open_history_external(True, draft.get("dark_mode", False))
            if retest is not None:
                recorded = retest["options"]
                for key in ["encoder_backend", "cbr_mode", "page_workers", "work_dir"]:
                    if key in recorded:
                        draft[key] = recorded[key]
                draft["run_mode"] = "Test savings & quality"
                draft["keep_test_previews"] = True
        except Exception, ex:
            _history_trace("Top-level history failed: " + _safe_unicode(ex))
            MessageBox.Show("Could not open run history: " + _safe_unicode(ex) + "\nSee Reports/history-diagnostic.log.", "WebP Optimizer")
        _history_trace("History returned; restoring options draft")


# [S06] Optional native dark palette and lossless technical-report reader.
_DARK_MODE = None


def _new_themed_control(type_name):
    """Use CLR subclasses where Windows ignores normal palette properties."""
    if _NATIVE_TYPE is None:
        _compile_native_bridge()
    return System.Activator.CreateInstance(_NATIVE_TYPE.Assembly.GetType("WebPOptimizerRuntime." + type_name))


def _new_combo():
    return _new_themed_control("ThemeComboBox")


def _new_listview():
    return _new_themed_control("ThemeListView")


def _new_tabs():
    return _new_themed_control("ThemeTabs")


def _new_checkbox():
    return _new_themed_control("ThemeCheckBox")


def _update_caption_theme(form):
    """Update only this window, without forcing handles or changing system settings."""
    if form.IsDisposed or not form.IsHandleCreated:
        return
    try:
        form._caption_result = int(_native_call("ThemeCaption", [form.Handle, System.Boolean(form._caption_dark)]))
    except Exception:
        form._caption_result = 0  # Unsupported frame attributes must never block UI.


def _set_ui_theme(dark, form):
    """Recolor plugin controls only; retain original colors for light-mode restore."""
    global _DARK_MODE
    _DARK_MODE = dark
    form._caption_dark = dark
    if not hasattr(form, "_caption_hooked"):
        def refresh_caption(sender, event):
            _update_caption_theme(form)
        form.HandleCreated += refresh_caption
        form.Shown += refresh_caption
        form._caption_hooked = True
    _update_caption_theme(form)
    if not hasattr(form, "_theme_original"):
        form._theme_original = {}
    pending = [form]
    while pending:
        control = pending.pop()
        pending.extend(list(control.Controls))
        if isinstance(control, PictureBox):
            continue  # Never modify comic pixels or comparison rendering.
        if control not in form._theme_original:
            form._theme_original[control] = (control.BackColor, control.ForeColor)
        if dark:
            control.BackColor = Color.FromArgb(39, 42, 47) if isinstance(control, (TextBox, RichTextBox, ListView, ComboBox, Button)) else Color.FromArgb(28, 30, 34)
            control.ForeColor = Color.FromArgb(218, 223, 229)
        else:
            control.BackColor, control.ForeColor = form._theme_original[control]
        if hasattr(control, "Dark"):
            control.Dark = dark
        if isinstance(control, Button):
            if not hasattr(form, "_theme_button_styles"):
                form._theme_button_styles = {}
            if control not in form._theme_button_styles:
                form._theme_button_styles[control] = control.FlatStyle
            control.FlatStyle = System.Windows.Forms.FlatStyle.Flat if dark else form._theme_button_styles[control]
            control.FlatAppearance.BorderColor = Color.FromArgb(72, 78, 87) if dark else System.Drawing.SystemColors.ControlDark
            control.FlatAppearance.MouseOverBackColor = Color.FromArgb(49, 55, 64) if dark else Color.Empty
            control.FlatAppearance.MouseDownBackColor = Color.FromArgb(58, 69, 80) if dark else Color.Empty
            control.UseVisualStyleBackColor = not dark
        if isinstance(control, ListView):
            control.GridLines = not dark


def _setup_checks(options):
    """Report optional WinRAR in every mode; require it only for CBR rebuilding."""
    result = _setup_checks_core(options)
    if "CHECK_RAR" not in result:
        rar = _find_rar_tool()
        result["CHECK_RAR"] = ("Available | " + rar if rar else "Not found | Optional: install WinRAR only to rebuild CBR output")
    result["CHECK_CBR_INPUT"] = "CBR reading and CBR-to-CBZ use 7-Zip; WinRAR is needed only for CBR output"
    return result


def _add_report_reader(form, page):
    """Search/wrap/color the original text; saving and copying remain lossless."""
    toolbar = Panel()
    toolbar.Dock, toolbar.Height = DockStyle.Top, 42
    _ui_label(toolbar, "Find", 10, 11, 38, 22)
    search = TextBox()
    search.Location, search.Size = Point(50, 9), Size(240, 25)
    toolbar.Controls.Add(search)
    find = Button()
    find.Text = "Find next"
    find.Location, find.Size = Point(300, 7), Size(100, 28)
    toolbar.Controls.Add(find)
    wrap = _new_checkbox()
    wrap.Text, wrap.Checked = "Wrap long lines", True
    wrap.Location, wrap.Size = Point(418, 9), Size(165, 25)
    toolbar.Controls.Add(wrap)
    notice = _ui_label(toolbar, "", 590, 11, 250, 22)
    def find_next(sender, event):
        text = _safe_unicode(form._report_box.Text)
        needle = _safe_unicode(search.Text)
        if not needle:
            return
        start = form._report_box.SelectionStart + form._report_box.SelectionLength
        at = text.lower().find(needle.lower(), start)
        if at < 0:
            at = text.lower().find(needle.lower())
        notice.Text = "No match" if at < 0 else ""
        if at >= 0:
            form._report_box.Select(at, len(needle))
            form._report_box.ScrollToCaret()
            form._report_box.Focus()
    def set_wrap(sender, event):
        form._report_box.WordWrap = bool(wrap.Checked)
    find.Click += find_next
    wrap.CheckedChanged += set_wrap
    page.Controls.Add(toolbar)
    toolbar.BringToFront()
    form._report_search, form._report_find, form._report_wrap = search, find, wrap
    # Highlight labels and section headings without rewriting or truncating text.
    offset = 0
    heading_font = Font("Consolas", 9.0, FontStyle.Bold)
    for line in _safe_unicode(form._report_box.Text).splitlines(True):
        stripped = line.strip()
        if stripped and (not line[:1].isspace()):
            length = line.find(":") + 1 if ":" in line else len(line.rstrip())
            form._report_box.Select(offset, length)
            form._report_box.SelectionFont = heading_font
        offset += len(line)
    heading_font.Dispose()
    form._report_box.Select(0, 0)


def _install_theme_constructors():
    """Apply palette after construction, including dialogs opened from history."""
    def install(cls):
        original = cls.__init__
        def themed(self, *args, **kwargs):
            original(self, *args, **kwargs)
            dark = _DARK_MODE
            if dark is None:
                dark = _load_settings()[0].get("dark_mode", "False").lower() == "true"
            _set_ui_theme(dark, self)
            if cls is OptionsForm:
                def restore_preview(sender, event):
                    global _DARK_MODE
                    _DARK_MODE = _load_settings()[0].get("dark_mode", "False").lower() == "true"
                self.FormClosed += restore_preview
        cls.__init__ = themed
    for cls in [PerformanceSetupForm, PerformanceResultsForm, OptionsForm, ProgressForm, QualityPreviewForm, RunHistoryForm, ReportForm, PreflightForm, SetupForm, RecoveryForm]:
        install(cls)

# Performance dialogs share the adapter namespace, like this support module.
exec compile(File.ReadAllText(Path.Combine(SCRIPT_DIR, "webp_performance_ui.py")), "webp_performance_ui.py", "exec")

# Compile before entering nested modal/click stacks, which can have little stack left.
_compile_native_bridge()
_install_theme_constructors()
