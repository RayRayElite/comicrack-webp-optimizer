# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""IronPython entry point loaded into the adapter's independent UI namespace.

Only reports/previews are accessed. No ComicRack object or archive conversion
is exposed to this process. Self-test modes exercise the real process boundary.
"""


def _history_host_main(request_path, self_test=""):
    global REPORT_DIR, _DARK_MODE
    document = XmlDocument()
    document.XmlResolver = None
    document.Load(request_path)
    request = document.DocumentElement
    if request.Name != "HistorySession":
        raise Exception("Invalid history request")
    if self_test == "fail":
        Environment.Exit(91)  # Verify abrupt failure cannot terminate the caller.
    if self_test and request.GetAttribute("testReports"):
        test_root = Path.GetFullPath(Path.Combine(SCRIPT_DIR, "Development", "Test Environment")).rstrip("\\/") + "\\"
        override = Path.GetFullPath(request.GetAttribute("testReports"))
        if not override.lower().startswith(test_root.lower()):
            raise Exception("Self-test reports must remain in the development fixture folder")
        REPORT_DIR = override
    _DARK_MODE = request.GetAttribute("dark") == "True"
    form, timer = None, None
    try:
        _history_trace("Independent history host starting")
        form = RunHistoryForm(allow_retest=request.GetAttribute("allowRetest") == "True")
        if self_test:
            form.Opacity, form.ShowInTaskbar = 0, False
            timer = Timer()
            timer.Interval = 250
            def finish_test(sender, event):
                timer.Stop()
                if self_test == "retest" and form._list.Items.Count:
                    form._list.Items[0].Selected = True
                    form._prepare_test(None, None)
                else:
                    form.Close()
            timer.Tick += finish_test
            timer.Start()
        form.ShowDialog()
        response = XmlDocument()
        root = response.CreateElement("HistoryResult")
        root.SetAttribute("status", "prepared" if form.retest is not None else "closed")
        response.AppendChild(root)
        if form.retest is not None:
            for key in ["encoder_backend", "cbr_mode", "page_workers", "work_dir"]:
                if key in form.retest.get("options", {}):
                    value = response.CreateElement("Value")
                    value.SetAttribute("key", key)
                    value.SetAttribute("value", _safe_unicode(form.retest["options"][key]))
                    root.AppendChild(value)
        response_path = request_path.replace(".request.xml", ".response.xml")
        response.Save(response_path + ".tmp")
        File.Move(response_path + ".tmp", response_path)
        _history_trace("Independent history host closed normally")
    finally:
        if timer is not None:
            timer.Dispose()
        if form is not None:
            form.Dispose()
