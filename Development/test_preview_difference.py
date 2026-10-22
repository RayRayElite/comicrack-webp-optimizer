# Copyright (c) 2026 RayRayElite; SPDX-License-Identifier: MIT
# Executed in the native IronPython harness, with the real CLR bridge and viewer.
method = _NATIVE_TYPE.Assembly.GetType('WebPOptimizerRuntime.PreviewDifference').GetMethod('Analyze')
def difference(a, b):
    return method.Invoke(None, System.Array[System.Object]([a, b]))
a, b = Bitmap(2, 2), Bitmap(2, 2)
try:
    for x in range(2):
        for y in range(2):
            a.SetPixel(x, y, Color.FromArgb(100, 100, 100))
            b.SetPixel(x, y, Color.FromArgb(100, 100, 100))
    d = difference(a, b)
    assert d.MeanAbsolute == d.RootMeanSquare == d.ChangedPercent == 0
    assert d.Heatmap.GetPixel(0, 0).R == 0
    d.Dispose()
    b.SetPixel(1, 0, Color.FromArgb(110, 100, 100))
    d = difference(a, b)
    assert abs(d.MeanAbsolute - 10.0/12) < .000001
    assert abs(d.RootMeanSquare - (100.0/12)**.5) < .000001
    assert d.ChangedPercent == 25 and d.MaximumChannelDifference == 10
    assert abs(d.BrightnessShift - .5315) < .000001
    assert d.Heatmap.GetPixel(1, 0).R == 80
    assert d.Heatmap.GetPixel(0, 0).R == 0
    d.Dispose()
    # A uniform darkening must report the right sign, not cancel into an
    # absolute error. Large changes must saturate the labeled heatmap safely.
    for x in range(2):
        for y in range(2):
            b.SetPixel(x, y, Color.FromArgb(90, 90, 90))
    d = difference(a, b)
    assert d.MeanAbsolute == 10 and d.RootMeanSquare == 10
    assert abs(d.BrightnessShift + 10) < .000001
    assert d.ChangedPercent == 100
    d.Dispose()
    b.SetPixel(0, 0, Color.White)
    d = difference(a, b)
    assert d.Heatmap.GetPixel(0, 0).R == 255
    d.Dispose()
    small = Bitmap(1, 1)
    try:
        try:
            difference(a, small)
            raise AssertionError('Mismatched dimensions accepted')
        except System.Reflection.TargetInvocationException:
            pass
    finally:
        small.Dispose()
finally:
    a.Dispose(); b.Dispose()
# Existing harness generated five-quality files. Nothing writes to those assets.
v = QualityPreviewForm(real_options['trial_preview_root'])
v.Opacity = 0
v.ShowInTaskbar = False
v.WindowState = FormWindowState.Normal
v.Show()
Application.DoEvents()
v._analyze_difference(None, None)
assert not v._quality.Enabled
clock = Stopwatch.StartNew()
while v._analysis_worker is not None and clock.Elapsed.TotalSeconds < 30:
    Application.DoEvents()
    System.Threading.Thread.CurrentThread.Join(10)
assert v._analysis_worker is None, 'Analysis did not complete'
assert v._difference is not None, v._measurements.Text
assert v._quality.Enabled and v._show_difference.Enabled
v._show_difference.Checked = True
assert v._pictures[1].Image is v._difference.Heatmap
v._zoom.SelectedItem = '200% - enlarged pixels'
event = System.Windows.Forms.MouseEventArgs(getattr(System.Windows.Forms.MouseButtons, "None"), 0, 4, 6, 0)
v._inspect_pixel(v._pictures[1], event)
assert 'Pixel (2, 3)' in v._pixel_reading.Text, v._pixel_reading.Text
# Render the actual diagnostic controls for layout review.
v._zoom.SelectedIndex = 0
Application.DoEvents()
bitmap = Bitmap(v.Width, v.Height)
v.DrawToBitmap(bitmap, System.Drawing.Rectangle(0, 0, v.Width, v.Height))
bitmap.Save(Path.Combine(render_dir, 'preview-differences.png'), System.Drawing.Imaging.ImageFormat.Png)
bitmap.Dispose()
v._show_difference.Checked = False
assert v._pictures[1].Image is v._images[1]
v._quality.SelectedItem = 'Q60'
assert v._difference is None and not v._show_difference.Enabled
# Closing with a job in flight must not retain a result or touch disposed images.
v._analyze_difference(None, None)
v.Close()
clock.Restart()
while v._analysis_worker is not None and clock.Elapsed.TotalSeconds < 30:
    Application.DoEvents()
    System.Threading.Thread.CurrentThread.Join(10)
assert v._analysis_worker is None and v._difference is None
v.Dispose()
print('PASS: exact identical/localized RGB metrics, heatmap location/amplification, dimension rejection, async viewer analysis, zoom-independent pixel inspection, page cleanup and close-during-analysis')
