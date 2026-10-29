def test_results_review():
    theme_before = globals().get("_DARK_MODE")
    settings_before = globals()["SETTINGS_PATH"]
    preferences_root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Results Preferences', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(preferences_root)
    globals()["SETTINGS_PATH"] = Path.Combine(preferences_root, 'settings.xml')
    _save_settings({'unrelated_setting': 'preserve me'})
    text = "WebP Optimizer Conversion Report\r\nGenerated: generated\r\nRun Mode: Create WebP Copies\r\nConverted Books: 2\r\nFailed: 1\r\nSkipped: 1\r\n\r\nPer-Book Conversion Results\r\n---------------------------\r\n"
    blocks = [('Zeta', 'OK', '9.5%', 'converted'), ('Alpha', 'ERROR', '-', 'source problem'), ('Beta', 'SKIPPED', '-', 'size policy'), ('Gamma', 'OK', '80.0%', 'converted')]
    for title, status, percent, note in blocks:
        text += title + '\r\n  Source: generated-' + title + '.cbz\r\n  Conversion Status: ' + status + '\r\n  Savings: ' + percent + '\r\n  Notes: ' + note + '\r\n  Technical diagnostic: keep full evidence ' + title + '\r\n\r\n'
    form = ReportForm(text, 'generated-report.txt')
    form.Opacity = 0; form.ShowInTaskbar = False; form.Show(); Application.DoEvents()
    try:
        listing = form._results_list
        assert listing.Items.Count == 4
        assert listing.Top >= form._result_tools.Height, (listing.Top, form._result_tools.Height)
        form._errors_first(None, None)
        assert listing.Items[0].Text == 'Alpha'
        form._sort_results(0, True)
        assert [i.Text for i in listing.Items] == ['Alpha', 'Beta', 'Gamma', 'Zeta']
        form._sort_results(2, False)
        assert [i.Text for i in listing.Items][:2] == ['Gamma', 'Zeta']
        form._sort_results(2, True)
        assert [i.Text for i in listing.Items][:2] == ['Zeta', 'Gamma']
        error = next(i for i in listing.Items if i.Text == 'Alpha')
        error.Selected = True; Application.DoEvents()
        selected = form._selected_result_text()
        assert 'keep full evidence Alpha' in selected and 'keep full evidence Beta' not in selected
        form._errors_first(None, None)
        assert 'keep full evidence Alpha' in form._selected_result_text()
        error = next(i for i in listing.Items if i.Text == 'Alpha')
        form._result_colors.Checked = True
        _set_ui_theme(True, form)
        assert error.ForeColor.R > error.ForeColor.G
        assert next(i for i in listing.Items if i.Text == 'Beta').ForeColor.G > 100
        _set_ui_theme(False, form)
        assert error.ForeColor.R > error.ForeColor.G
        form._result_colors.Checked = False
        assert error.ForeColor == listing.ForeColor
        assert form._report_text == text
        detail = ResultDetailsForm(selected)
        try:
            assert 'keep full evidence Alpha' in detail._reader.Text
            assert detail._text == selected
        finally:
            detail.Dispose()
        render = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Review')
        Directory.CreateDirectory(render)
        _set_ui_theme(True, form); form._result_colors.Checked = True
        bitmap = Bitmap(form.Width, form.Height)
        form.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, form.Width, form.Height))
        bitmap.Save(Path.Combine(render, 'results-review-dark.png'), System.Drawing.Imaging.ImageFormat.Png); bitmap.Dispose()
        settings, warning = _load_settings()
        assert settings['results_errors_first'] == settings['results_status_colors'] == 'True'
        assert settings['unrelated_setting'] == 'preserve me'
        unchanged = File.ReadAllText(SETTINGS_PATH)
        reopened = ReportForm(text, 'generated-history.txt', historical=True)
        try:
            assert reopened._errors_first_checkbox.Checked and reopened._result_colors.Checked
            assert reopened._sort_column == 1 and reopened._sort_ascending
            assert File.ReadAllText(SETTINGS_PATH) == unchanged, 'Opening results rewrote preferences'
            reopened._errors_first_checkbox.Checked = False
            reopened._result_colors.Checked = False
        finally:
            reopened.Dispose()
        disabled = ReportForm(text, 'generated-next-run.txt')
        try:
            assert not disabled._errors_first_checkbox.Checked and not disabled._result_colors.Checked
            assert disabled._sort_column == -1
            disabled._sort_results(0, False)
        finally:
            disabled.Dispose()
        sorted_again = ReportForm(text, 'generated-next-run.txt')
        try:
            assert sorted_again._sort_column == 0 and not sorted_again._sort_ascending
        finally:
            sorted_again.Dispose()

    finally:
        form.Close(); form.Dispose()
        globals()["_DARK_MODE"] = theme_before
        globals()["SETTINGS_PATH"] = settings_before
    print('PASS: semantic errors-first/text/numeric sorts, selection after sorting, one-entry full evidence, details reader, optional dark/light colors and unchanged report text and saved preferences across current/history/reopened windows')
test_results_review()


def test_results_large_collection_and_retry():
    previous_settings = globals()['SETTINGS_PATH']
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Results Scale', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    globals()['SETTINGS_PATH'] = Path.Combine(root, 'settings.xml')
    _save_settings({})
    clock = Stopwatch.StartNew()
    count = 125001
    text = 'WebP Optimizer Analysis Report\r\nBooks Scanned: ' + str(count) + '\r\n\r\nPer-Book Results\r\n----------------\r\n'
    text += ''.join('Book {0:06d}\r\n  File: C:\\generated\\{0}.cbz\r\n  Status: {1}\r\n  Notes: {2}\r\n\r\n'.format(i, 'ERROR' if i == count - 1 else 'Already WebP', 'find-this-failure' if i == count - 1 else 'Already WebP') for i in range(count))
    form = ReportForm(text, Path.Combine(root, 'generated.txt'), historical=True)
    try:
        assert len(form._records) == count
        assert form._results_list.Items.Count == 250
        assert not form._technical_loaded and form._report_box.TextLength == 0
        form._filter_combo.SelectedIndex = 1
        assert form._results_list.Items.Count == 1 and form._results_list.Items[0].Text == 'Book 125000'
        form._filter_combo.SelectedIndex = 0
        form._result_search.Text = 'find-this-failure'; form._search_results(None, None)
        assert len(form._visible_records) == 1
        form._result_search.Text = ''; form._search_results(None, None)
        form._sort_results(0, False)
        assert form._results_list.Items[0].Text == 'Book 125000'
        form._next_page(None, None)
        assert form._results_list.Items[0].Text == 'Book 124750'
        assert form._page_index == 1
        form._previous_page(None, None)
        assert form._results_list.Items[0].Text == 'Book 125000'
        assert form._report_text == text
        assert not form._retry_button.Enabled
        print('PASS: 125,001-book report: bounded 250 native rows, filters/search, global sorting/paging and lazy technical text; {0:.2f}s including generation/review'.format(clock.Elapsed.TotalSeconds))
    finally:
        form.Close(); form.Dispose()
    class Book(object):
        def __init__(self, path): self.FilePath = path
    options = {'run_mode': 'Replace Originals', 'quality_mode': QUALITY_MODE_VALUES[0], 'page_workers': '12', 'create_backup': False, 'prefetch_record': 'must-not-reuse'}
    books = [Book('C:\\generated\\failed.cbz'), Book('C:\\generated\\ok.cbz')]
    text = 'Generated report\r\nRun Mode: Replace Originals\r\n\r\nPer-Book Conversion Results\r\n---\r\nFailed\r\n  Source: C:\\generated\\failed.cbz\r\n  Conversion Status: ERROR\r\n  Notes: needs review\r\nGood\r\n  Source: C:\\generated\\ok.cbz\r\n  Conversion Status: OK\r\n'
    form = ReportForm(text, Path.Combine(root, 'retry.txt'), retry_books=books, run_options=options)
    try:
        form.ShowInTaskbar = False; form.Opacity = 0; form.Show(); Application.DoEvents()
        form._results_list.Items[0].Selected = True; form._results_list.Items[1].Selected = True
        form._retry_selected(None, None)
        chosen, draft = form.retry_request
        assert chosen == books[:1] and draft['run_mode'] == 'Replace Originals'
        assert draft['page_workers'] == '12' and draft['create_backup'] is False
        assert 'prefetch_record' not in draft
        assert options['prefetch_record'] == 'must-not-reuse'
    finally:
        form.Dispose()
    dialog = ResultDetailsForm('private path', editable=True, setup_options={'run_mode': 'Analyze Only'})
    old_setup = globals()['_setup_checks']
    try:
        globals()['_setup_checks'] = lambda options: {'STATUS': 'OK', 'CHECK_MESSAGE': 'generated setup result'}
        assert not dialog._reader.ReadOnly
        dialog._reader.Text = 'redacted before copying'
        dialog._collect_setup(None, None)
        assert 'generated setup result' in dialog._reader.Text
        assert 'private path' not in dialog._reader.Text
    finally:
        globals()['_setup_checks'] = old_setup
        dialog.Dispose()
        globals()['SETTINGS_PATH'] = previous_settings
    assert _result_display_status({'Conversion Status': 'SKIPPED', 'Skip Reason': 'SIZE_POLICY'}) == 'Not smaller'
    assert _result_display_status({'Conversion Status': 'SKIPPED', 'Skip Reason': 'SIZE_POLICY', '_size_policy': 'At Least 3% Smaller'}) == 'Size target not met'
    assert _result_category({'Conversion Status': 'SKIPPED', 'Skip Reason': 'ARCHIVE_ERROR'}) == 'Errors'
    assert _result_display_status({'Conversion Status': 'SKIPPED', 'Source ImageFormat': 'MISSING'}) == 'Source needs attention'
    assert 'Not recorded' in _result_settings_text({})
    print('PASS: failed-only retry captures original books/options without starting work, strips cache state, editable support review and setup checks')

test_results_large_collection_and_retry()


def test_retry_guards_and_outer_loop():
    saved_settings = globals()['SETTINGS_PATH']
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Retry Guards', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root)
    globals()['SETTINGS_PATH'] = Path.Combine(root, 'settings.xml'); _save_settings({})
    class Book(object): FilePath = 'C:\\generated\\changed.cbz'
    book = Book()
    text = 'Report\r\n\r\nPer-Book Results\r\n---\r\nChanged\r\n  File: C:\\generated\\original.cbz\r\n  Status: ERROR\r\n'
    form = ReportForm(text, Path.Combine(root, 'report.txt'), retry_books=[book], run_options={'run_mode': 'Analyze Only'})
    original_message = globals()['MessageBox']
    messages = []
    class Messages(object):
        @staticmethod
        def Show(*args): messages.append(args[0]); return DialogResult.OK
    try:
        globals()['MessageBox'] = Messages
        form.ShowInTaskbar = False; form.Opacity = 0; form.Show(); Application.DoEvents()
        form._results_list.Items[0].Selected = True
        form._retry_selected(None, None)
        assert form.retry_request is None and messages and 'changed or is invalid' in messages[-1]
        book.FilePath = 'C:\\generated\\bad|path.cbz'
        form._retry_selected(None, None)
        assert form.retry_request is None and len(messages) == 2
    finally:
        globals()['MessageBox'] = original_message
        form.Close(); form.Dispose()
        globals()['SETTINGS_PATH'] = saved_settings
    original_runner, active_before = globals()['_run_phase_two'], globals()['_RUN_ACTIVE']
    calls = []
    def runner(books, options=None):
        calls.append((books, options))
        return ([book], {'run_mode': 'Analyze Only'}) if len(calls) == 1 else None
    try:
        globals()['_run_phase_two'] = runner; globals()['_RUN_ACTIVE'] = False
        webp_optimizer_phase_one([book])
        assert len(calls) == 2 and calls[0][1] is None
        assert calls[1][1]['run_mode'] == 'Analyze Only'
        assert not globals()['_RUN_ACTIVE']
    finally:
        globals()['_run_phase_two'], globals()['_RUN_ACTIVE'] = original_runner, active_before
    print('PASS: changed/invalid retry paths rejected without work; repeat flow returns through public hook without recursive modal runs')

test_retry_guards_and_outer_loop()


def test_dark_defaults_and_not_processed():
    original_settings = globals()['SETTINGS_PATH']
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Dark Defaults', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(root); globals()['SETTINGS_PATH'] = Path.Combine(root, 'settings.xml')
    try:
        form = OptionsForm()
        try: assert form._dark_checkbox.Checked
        finally: form.Dispose()
        _save_settings({'dark_mode': 'False'})
        form = OptionsForm()
        try: assert not form._dark_checkbox.Checked
        finally: form.Dispose()
        assert _result_category({'Conversion Status': 'NOT_PROCESSED'}) == 'Not processed'
        assert _result_category({'Status': 'Not processed'}) == 'Not processed'
        assert _result_category({'Conversion Status': 'SKIPPED'}) == 'Skipped'
        assert _result_display_status({'Conversion Status': 'NOT_PROCESSED'}) == 'Not processed'
        text = 'Report\r\nRun Status: Stopped by user\r\n\r\nPer-Book Results\r\n---\r\nUntouched\r\n  Status: Not processed\r\nSkipped\r\n  Status: SKIPPED\r\n'
        form = ReportForm(text, Path.Combine(root, 'generated.txt'))
        try:
            form._filter_combo.SelectedIndex = 4
            assert form._results_list.Items.Count == 1 and form._results_list.Items[0].Text == 'Untouched'
            form._filter_combo.SelectedIndex = 2
            assert form._results_list.Items.Count == 1 and form._results_list.Items[0].Text == 'Skipped'
        finally: form.Dispose()
    finally: globals()['SETTINGS_PATH'] = original_settings
    print('PASS: new-install dark default, saved light preference and distinct Not processed versus Skipped filters')

test_dark_defaults_and_not_processed()


def test_ui_audit_conventions():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Audit')
    Directory.CreateDirectory(root)
    options = OptionsForm()
    try:
        assert options._dark_checkbox.Parent == options
        assert options._dark_checkbox.Bottom < options._tabs.Top
        assert options._quality_combo.AccessibleName == 'Encoder quality level'
        assert options.CancelButton == options._cancel_button
    finally: options.Dispose()
    form = ResultDetailsForm('Generated details', editable=True)
    try:
        assert form.CancelButton is not None
        _set_ui_theme(True, form)
        button = next(c for panel in form.Controls if isinstance(panel, Panel) for c in panel.Controls if isinstance(c, Button))
        assert button.GetType().Name == 'ThemeButton' and button.Dark
        button.Enabled = False
        bitmap = Bitmap(button.Width, button.Height)
        try:
            button.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, button.Width, button.Height))
            readable = 0
            for y in range(bitmap.Height):
                for x in range(bitmap.Width):
                    pixel = bitmap.GetPixel(x, y)
                    if pixel.R >= 140 and pixel.G >= 145 and pixel.B >= 150: readable += 1
            assert readable > 5, 'Disabled dark button label is not readable'
            bitmap.Save(Path.Combine(root, 'disabled-button-dark.png'), System.Drawing.Imaging.ImageFormat.Png)
        finally: bitmap.Dispose()
        _set_ui_theme(False, form)
        assert not button.Dark
    finally: form.Dispose()
    setup = PerformanceSetupForm({})
    try:
        assert setup.AcceptButton is not None and setup.CancelButton is not None
        assert setup._repeats.Right <= setup.ClientSize.Width - 20
        assert not setup.MaximizeBox
    finally: setup.Dispose()
    results = PerformanceResultsForm([], 'Generated benchmark report', 'generated.txt', '4')
    try:
        tabs = next(c for c in results.Controls if isinstance(c, TabControl))
        buttons = [c for c in results.Controls if isinstance(c, Button)]
        height = tabs.Height
        results.ClientSize = Size(1280, 780)
        results.PerformLayout()
        assert tabs.Height > height
        assert all(c.Bottom <= results.ClientSize.Height for c in buttons)
        assert results.CancelButton is not None
    finally: results.Dispose()
    report = ReportForm('Generated report\r\nBooks Scanned: 0\r\n', Path.Combine(root, 'report.txt'))
    try:
        report.ShowInTaskbar = False; report.Opacity = 0; report.Show(); Application.DoEvents()
        assert report._results_list.ShowItemToolTips
        event = System.Windows.Forms.KeyEventArgs(System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.F)
        # Invoke the real protected key route so shared dialog behavior is exercised.
        method = clr.GetClrType(Control).GetMethod('OnKeyDown', System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.NonPublic)
        method.Invoke(report, System.Array[System.Object]([event]))
        assert report._result_search.Focused and event.SuppressKeyPress
        report._tabs.SelectedIndex = 1; Application.DoEvents()
        event = System.Windows.Forms.KeyEventArgs(System.Windows.Forms.Keys.Control | System.Windows.Forms.Keys.F)
        method.Invoke(report, System.Array[System.Object]([event]))
        assert report._report_search.Focused
    finally: report.Close(); report.Dispose()
    print('PASS: visible theme switch, accessible labels, readable disabled dark buttons, Escape/default actions, benchmark fit/resize, table hints and contextual Ctrl+F')

test_ui_audit_conventions()


def render_ui_audit_matrix():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Audit')
    Directory.CreateDirectory(root)
    original_report, original_settings = globals()['REPORT_DIR'], globals()['SETTINGS_PATH']
    globals()['REPORT_DIR'] = Path.Combine(root, 'Isolated Reports')
    Directory.CreateDirectory(REPORT_DIR)
    globals()['SETTINGS_PATH'] = Path.Combine(root, 'isolated-settings.xml')
    _save_settings({'dark_mode': 'True'})
    options = {'run_mode': 'Create WebP Copies', 'quality_mode': QUALITY_MODE_VALUES[0], 'encoder_backend': ENCODER_BACKEND_VALUES[0], 'page_workers': '4', 'create_backup': False}
    report = 'WebP Optimizer Conversion Report\r\nRun Mode: Create WebP Copies\r\nConverted Books: 1\r\nSkipped: 0\r\nFailed: 1\r\nTotal Saved: 40 MB\r\nOverall Reduction: 50.00%\r\nElapsed Time: 12 seconds\r\n\r\nPer-Book Conversion Results\r\n---\r\nGenerated successful book\r\n  Conversion Status: OK\r\n  Savings: 50.0%\r\nGenerated failed book\r\n  Conversion Status: ERROR\r\n  Notes: Generated failure for UI review\r\n'
    factories = [('options', lambda: OptionsForm()), ('results', lambda: ReportForm(report, Path.Combine(REPORT_DIR, 'generated.txt'))), ('details', lambda: ResultDetailsForm('Generated details\r\nSuggested action: inspect the named page.')), ('support', lambda: ResultDetailsForm('Review and redact before sharing.\r\nGenerated support information.', editable=True, setup_options=options)), ('benchmark-setup', lambda: PerformanceSetupForm(options)), ('benchmark-results', lambda: PerformanceResultsForm([['4','3','2.5','5','30%','512','4','2','Encoding','Complete']], 'Generated benchmark report', 'generated.txt', '4')), ('preflight', lambda: PreflightForm([], options)), ('setup', lambda: SetupForm(options)), ('recovery', lambda: RecoveryForm([])), ('history', lambda: RunHistoryForm(False)), ('progress', lambda: ProgressForm())]
    try:
        for dark in [True, False]:
            for name, factory in factories:
                form = factory()
                try:
                    if name == 'setup': form._text.Text = 'Generated setup passed\r\nPython/Pillow, encoder and storage checks are shown here.'
                    if name == 'progress': form._finished = True
                    _set_ui_theme(dark, form)
                    # Create real native child handles, but detach automatic checks
                    # so this visual matrix uses generated content only.
                    if name in ['setup', 'recovery']: form.Shown -= form._shown
                    if name == 'history': form.Shown -= form._on_shown
                    form.Opacity = 0; form.ShowInTaskbar = False
                    form.Show(); form.PerformLayout(); Application.DoEvents()
                    if name == 'progress':
                        form.update_state(45, 'Converting your collection', 'Generated sample comic - issue 12', 12, 26, 11)
                        form.update_archive_progress('ENCODING|18|32')
                    if name in ['history', 'recovery']: form._refresh_safe()
                    bitmap = Bitmap(form.Width, form.Height)
                    try:
                        form.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, form.Width, form.Height))
                        bitmap.Save(Path.Combine(root, name + ('-dark.png' if dark else '-light.png')), System.Drawing.Imaging.ImageFormat.Png)
                    finally: bitmap.Dispose()
                finally:
                    if name == 'progress': form.finish()
                    else: form.Close()
                    form.Dispose()
    finally:
        globals()['REPORT_DIR'], globals()['SETTINGS_PATH'] = original_report, original_settings
    print('PASS: dark/light UI audit renders for options, results, details/support, benchmark setup/results, preflight, setup, recovery, history and progress; no source files or real run records used')

render_ui_audit_matrix()


def test_inherited_theme_roundtrip():
    original_settings = globals()['SETTINGS_PATH']
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Audit')
    globals()['SETTINGS_PATH'] = Path.Combine(root, 'theme-roundtrip-settings.xml')
    _save_settings({'dark_mode': 'True'})
    form = OptionsForm()
    try:
        form.ShowInTaskbar = False; form.Opacity = 0; form.Show(); Application.DoEvents()
        for repeat in range(3):
            form._dark_checkbox.Checked = False; Application.DoEvents()
            pending = [form]
            while pending:
                control = pending.pop(); pending.extend(list(control.Controls))
                if isinstance(control, (Label, CheckBox, Button)):
                    assert control.BackColor != Color.FromArgb(28, 30, 34), (control.Text, control.BackColor)
                    assert control.ForeColor != Color.FromArgb(218, 223, 229), (control.Text, control.ForeColor)
            assert form._ok_button.ForeColor.GetBrightness() < 0.5
            if repeat == 2:
                bitmap = Bitmap(form.Width, form.Height)
                try:
                    form.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, form.Width, form.Height))
                    bitmap.Save(Path.Combine(root, 'options-restored-light.png'), System.Drawing.Imaging.ImageFormat.Png)
                finally: bitmap.Dispose()
            form._dark_checkbox.Checked = True; Application.DoEvents()
    finally:
        form.Close(); form.Dispose(); globals()['SETTINGS_PATH'] = original_settings
    print('PASS: dark-default options restore readable light colors for all labels/checks/buttons through three real toggle cycles')

test_inherited_theme_roundtrip()


def test_design_disclosures_and_hierarchy():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Audit')
    report = 'Report\r\nRun Mode: Create WebP Copies\r\n\r\nPer-Book Results\r\n---\r\nFailed page\r\n  Conversion Status: ERROR\r\n  Notes: The source page could not be read.\r\n  Suggested action: Restore a verified source.\r\n'
    form = ReportForm(report, Path.Combine(root, 'design.txt'))
    try:
        form.ShowInTaskbar = False; form.Opacity = 0; form.Show(); Application.DoEvents()
        form._results_list.Items[0].Selected = True; Application.DoEvents()
        assert 'The source page' in form._selection_explanation.Text
        assert 'Restore a verified source.' in form._selection_explanation.Text
        assert form._selection_heading.Text.startswith('ERROR')
        assert form.AcceptButton.Text == 'Review 1 error'
        assert not next(c for c in form.Controls if isinstance(c, Button) and c.Text == 'Open report').Visible
        assert [i.Text for i in form._more_menu.Items] == ['Review interrupted work', 'Run settings', 'Support information', 'About these results', 'Open report folder', 'Open report file', 'Copy full report']
        more = next(c for c in form._result_tools.Controls if isinstance(c, Button) and c.Text == 'More...')
        more.PerformClick(); Application.DoEvents()
        assert form._more_menu.Visible
        assert all(i.Enabled for i in form._more_menu.Items)
        form._more_menu.Close()
        form.AcceptButton.PerformClick()
        assert form._filter_combo.SelectedIndex == 1
        assert form._report_text == report
    finally: form.Close(); form.Dispose()
    options = OptionsForm()
    try:
        options.ShowInTaskbar = False; options.Opacity = 0; options.Show(); Application.DoEvents()
        options._mode_combo.SelectedItem = 'Replace Originals'
        assert options._ok_button.Text == 'Replace originals'
        assert options._backup_checkbox.Visible
        assert 'Based on bundled JPEG' in options._quality_estimate_detail
        assert 'Based on bundled JPEG' not in options._quality_note.Text
        assert options._mode_combo.Parent.Tag == 'surface'
        assert options._quality_about.Enabled
        for dark in [False, True, False]:
            _set_ui_theme(dark, options)
            assert options._quality_about.ForeColor.GetBrightness() < .5 if not dark else options._quality_about.Dark
    finally: options.Close(); options.Dispose()
    print('PASS: visual hierarchy, inline error/next-step disclosure, full More menu access, contextual error action, concise quality estimate and explicit replacement action')

test_design_disclosures_and_hierarchy()


def test_transient_selection_notifications():
    root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Audit')
    text = 'Report\r\n\r\nPer-Book Results\r\n---\r\nGenerated error\r\n  Status: ERROR\r\n  Notes: Generated selection lifecycle fixture.\r\n'
    form = ReportForm(text, Path.Combine(root, 'selection.txt'))
    try:
        form.Opacity = 0; form.ShowInTaskbar = False; form.Show(); Application.DoEvents()
        item = form._results_list.Items[0]
        item.Selected = True; Application.DoEvents()
        tag = item.Tag
        item.Tag = None
        form._result_selection_changed(None, None)
        assert form._selected_result_text() == ''
        assert not form._retry_button.Enabled and not any(b.Enabled for b in form._entry_buttons)
        form._apply_result_colors()
        item.Tag = tag
        form._result_selection_changed(None, None)
        assert 'Generated error' in form._selected_result_text()
        form._filter_combo.SelectedIndex = 3
        assert form._results_list.Items.Count == 0
        form._filter_combo.SelectedIndex = 0
        assert form._results_list.Items.Count == 1
        form._results_list.Items[0].Selected = True
        form.Close(); Application.DoEvents()
        form._result_selection_changed(None, None)
        assert form._selected_result_rows() == []
    finally: form.Dispose()
    print('PASS: missing row Tag, deselection/filter rebuild and close-time selection notifications are harmless; valid selection recovers')

test_transient_selection_notifications()


def test_remaining_screen_design():
    form = OptionsForm()
    try:
        form.ShowInTaskbar = False; form.Opacity = 0; form.Show(); Application.DoEvents()
        form._tabs.SelectedIndex = 1; Application.DoEvents()
        assert form._encoder_combo.Parent.Tag == 'surface'
        assert form._work_text.Parent.Parent.Tag == 'surface'
        assert form._reports_checkbox.Parent.Tag == 'surface'
        form._work_text.Text = 'C:\\Generated Temp'
        assert form._collect_options()['work_dir'] == 'C:\\Generated Temp'
        form._tabs.SelectedIndex = 2; Application.DoEvents()
        assert form._workers_combo.Parent.Tag == 'surface'
        assert form._awake_checkbox.Bottom <= form._tabs.TabPages[2].ClientSize.Height
        assert not form._tabs.TabPages[2].VerticalScroll.Visible
        form._tabs.SelectedIndex = 3; Application.DoEvents()
        assert sum(1 for c in form._tabs.TabPages[3].Controls if isinstance(c, Panel) and c.Tag == 'surface') == 2
        _set_ui_theme(True, form)
        for tab, name in [(1, 'storage'), (2, 'performance'), (3, 'tools')]:
            form._tabs.SelectedIndex = tab; Application.DoEvents()
            bitmap = Bitmap(form.Width, form.Height)
            try:
                form.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, form.Width, form.Height))
                bitmap.Save(Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'UI Audit', name + '-dark.png'), System.Drawing.Imaging.ImageFormat.Png)
            finally: bitmap.Dispose()
        for dark in [False, True, False]:
            _set_ui_theme(dark, form)
            assert form._work_text.Text == 'C:\\Generated Temp'
    finally: form.Close(); form.Dispose()
    review = PreflightForm([], {'run_mode': 'Replace Originals', 'create_backup': False})
    try:
        card = next(c for c in review.Controls if isinstance(c, Panel) and c.Tag == 'surface')
        assert any('No permanent backup selected' in c.Text and c.Tag == 'warning' for c in card.Controls)
    finally: review.Dispose()
    recovery = RecoveryForm([])
    try:
        assert recovery._retry_hint.Text == 'Choose attempts to begin.'
        assert not recovery._buttons['Allow retry'].Enabled
    finally: recovery.Dispose()
    setup = SetupForm({'run_mode': 'Analyze Only'})
    try:
        assert any(isinstance(c, Button) and c.Text == 'Copy check results' for c in setup.Controls)
    finally: setup.Dispose()
    print('PASS: remaining options groups, visible pace controls without scrolling, editable storage field, explicit unbacked replacement review, recovery hints and setup-copy access')

test_remaining_screen_design()


def test_bulk_recovery_controls():
    saved = dict((key, globals()[key]) for key in ['_load_recovery_items', '_check_recovery_item', '_allow_recovery_retry'])
    records = [dict(source='C:\\generated\\' + name + '.cbz', updated='Generated') for name in ['ready', 'active', 'retained', 'unselected']]
    checked, retried, allowed = [], [], []
    def load(books): return [r for r in records if r['source'] not in allowed]
    def check(record):
        checked.append(record['source']); record.pop('checked', None)
        if 'active' in record['source']: raise Exception('Recorded helper is still running')
        record['checked'] = {'SourceValid': True, 'Source': 'Generated source validated'}
        return record['checked']
    def allow(record, confirmed):
        retried.append(record['source'])
        assert confirmed
        if not record.get('checked', {}).get('SourceValid'): raise Exception('Check files first')
        if 'retained' in record['source']: raise Exception('Retained converted output must be resolved')
        allowed.append(record['source']); return 'generated-audit-folder'
    globals().update(_load_recovery_items=load, _check_recovery_item=check, _allow_recovery_retry=allow)
    form = RecoveryForm([], allow_prepare=True)
    try:
        form.Opacity = 0; form.ShowInTaskbar = False; form.Show(); Application.DoEvents()
        form._refresh_safe(); form._select_all(None, None)
        assert len(form._selected_records()) == 4
        form._list.Items[3].Selected = False; Application.DoEvents()
        assert len(form._selected_records()) == 3
        form._check(None, None)
        assert checked == [r['source'] for r in records[:3]]
        assert not form._confirmed.Checked
        assert 'still running' in form._batch_details
        form._confirmed.Checked = True
        form._retry(None, None)
        assert retried == [r['source'] for r in records[:3]]
        assert allowed == [records[0]['source']]
        assert len(form._list.Items) == 3
        assert 'Retained converted output' in form._batch_details and 'Check files first' in form._batch_details
        assert '1 retries allowed; 2 remain blocked' in form._note.Text
        assert not form._confirmed.Checked
        assert form._buttons['Prepare retry'].Enabled
        form._prepare_retry(None, None)
        assert form.retry_sources == allowed
    finally:
        form.Dispose(); globals().update(saved)
    print('PASS: bulk selection/check/confirmation, partial allow-retry, active/unchecked and retained-output blocks, untouched unselected records and prepare-only cleared sources')


def test_report_recovery_route():
    saved_recovery, saved_show = globals()['RecoveryForm'], globals()['_show_owned_dialog']
    captures = []
    class Book(object): FilePath = 'C:\\generated\\blocked.cbz'
    class Recovery(object):
        def __init__(self, books, **kwargs):
            captures.append(([book.FilePath for book in books], kwargs))
            self.retry_sources = [Book.FilePath] if kwargs.get('allow_prepare') else []
        def Dispose(self): pass
    globals()['RecoveryForm'] = Recovery
    globals()['_show_owned_dialog'] = lambda *args: None
    text = 'Report\r\nRun Mode: Replace Originals\r\n\r\nPer-Book Results\r\n---\r\nBlocked\r\n  Source: C:\\generated\\blocked.cbz\r\n  Conversion Status: ERROR\r\n  Notes: Interrupted work needs inspection; pending output retained.\r\n'
    form = ReportForm(text, 'generated.txt', retry_books=[Book()], run_options={'run_mode': 'Replace Originals', 'create_backup': False})
    try:
        form.Opacity = 0; form.ShowInTaskbar = False; form.Show(); Application.DoEvents()
        form._results_list.Items[0].Selected = True; Application.DoEvents()
        assert form._recovery_button.Visible
        form._open_interrupted_work(None, None)
        assert captures[-1][0] == [Book.FilePath] and captures[-1][1]['allow_prepare']
        assert form.retry_request[0][0].FilePath == Book.FilePath
        assert form.retry_request[1]['create_backup'] is False
    finally: form.Dispose()
    historical = ReportForm(text, 'generated-history.txt', historical=True)
    try:
        historical._open_interrupted_work(None, None)
        assert not captures[-1][1]['allow_prepare'] and historical.retry_request is None
    finally:
        historical.Dispose(); globals()['RecoveryForm'], globals()['_show_owned_dialog'] = saved_recovery, saved_show
    print('PASS: contextual report recovery link, focused source paths, prepared current-run retry and no historical auto-selection')

test_bulk_recovery_controls()
test_report_recovery_route()
