# Native report presentation: actionable row, complete technical evidence.
def test_error_reports():
    message = 'Source image problem: this page cannot be decoded; its data may be damaged, malformed or unsupported. Page: pages/013.jpg. Restore a clean page/archive. Original archive was not replaced.'
    failure = {'STATUS': 'ERROR', 'MESSAGE': message, 'ERROR_CODE': 'SOURCE_IMAGE_UNREADABLE',
               'ERROR_PAGE': 'pages/013.jpg', 'ERROR_STAGE': 'encoding source image',
               'ERROR_ACTION': 'Restore a clean page/archive.', 'ERROR_DETAIL': 'raw decoder evidence: premature end marker'}
    scan = {'caption': 'Generated damaged-page fixture', 'file_path': 'generated.cbz', 'image_format': 'JPG', 'eligible': True}
    options = {'run_mode': 'Create WebP Copies', 'quality_mode': 'Q75'}
    report = _build_conversion_report([scan], [failure], 'generated tool', options)
    for label in ['Failure category: SOURCE_IMAGE_UNREADABLE', 'Affected page: pages/013.jpg', 'Failed step:', 'Suggested action:', 'Technical diagnostic: raw decoder evidence']:
        assert label in report, label
    form = ReportForm(report, 'generated-report.txt')
    try:
        def lists(control):
            found = [control] if isinstance(control, ListView) else []
            for child in control.Controls:
                found += lists(child)
            return found
        rows = [row for listing in lists(form) for row in listing.Items]
        assert len(rows) == 1
        assert message in rows[0].SubItems[3].Text
        assert 'raw decoder evidence' not in rows[0].SubItems[3].Text
        assert 'raw decoder evidence' in form._report_text
    finally:
        form.Dispose()
    trial = dict((quality, dict(failure)) for quality in TRIAL_QUALITY_LEVELS)
    trial.update({'STATUS': 'ERROR', 'MESSAGE': message})
    quality_report = _build_quality_trial_report([scan], [trial], 'generated tool', options)
    assert 'Q75 Affected page: pages/013.jpg' in quality_report
    assert 'Q75 Technical diagnostic: raw decoder evidence' in quality_report
    print('PASS: conversion/quality reports retain structured failure evidence and show only actionable explanation in the result row')
test_error_reports()
