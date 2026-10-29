// Copyright (c) 2026 RayRayElite
// SPDX-License-Identifier: MIT
// Small, in-memory CLR bridge for APIs unavailable directly through IronPython.
using System;
using System.Runtime.InteropServices;

namespace WebPOptimizerRuntime {
    public static class NativeWindows {
        [DllImport("kernel32.dll", SetLastError = true)]
        public static extern uint SetThreadExecutionState(uint flags);

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool GetDiskFreeSpaceEx(string path, out ulong available,
                                                      out ulong total, out ulong free);

        [DllImport("dwmapi.dll")]
        private static extern int DwmSetWindowAttribute(IntPtr window, int attribute, ref int value, int size);
        [DllImport("dwmapi.dll")]
        private static extern int DwmGetWindowAttribute(IntPtr window, int attribute, out int value, int size);

        // Supported attributes are probed by HRESULT, never by manifest-sensitive
        // OS version checks. Windows 10 can accept dark framing but not custom colors.
        public static int ThemeCaption(IntPtr window, bool dark) {
            int flags = 0, value = dark ? 1 : 0;
            try {
                int result = DwmSetWindowAttribute(window, 20, ref value, 4);
                if (result < 0) result = DwmSetWindowAttribute(window, 19, ref value, 4);
                if (result >= 0) flags |= 1;
                value = dark ? 0x00362F2B : -1; // COLORREF: muted grey caption.
                if (DwmSetWindowAttribute(window, 35, ref value, 4) >= 0) flags |= 2;
                value = dark ? 0x00E5DFDA : -1;
                DwmSetWindowAttribute(window, 36, ref value, 4);
                value = dark ? 0x00574E48 : -1;
                DwmSetWindowAttribute(window, 34, ref value, 4);
            } catch (DllNotFoundException) { } catch (EntryPointNotFoundException) { }
            return flags;
        }

        public static int CaptionThemeState(IntPtr window) {
            try {
                int value;
                return DwmGetWindowAttribute(window, 20, out value, 4) >= 0 ? value : -1;
            } catch (DllNotFoundException) { return -1; } catch (EntryPointNotFoundException) { return -1; }
        }

        // Keep slow network I/O off the host thread. No Python callbacks run here.
        public static long DiskFreeBounded(string path) {
            long answer = -1;
            var worker = new System.Threading.Thread(delegate() {
                try {
                    string candidate = System.IO.Path.GetFullPath(path);
                    while (!String.IsNullOrEmpty(candidate) && !System.IO.Directory.Exists(candidate))
                        candidate = System.IO.Path.GetDirectoryName(candidate.TrimEnd('\\', '/'));
                    if (!String.IsNullOrEmpty(candidate))
                        answer = DiskFree(candidate.TrimEnd('\\', '/') + "\\");
                } catch { answer = -1; }
            });
            worker.IsBackground = true;
            worker.Start();
            return worker.Join(2000) ? answer : -1;
        }

        public static long DiskFree(string path) {
            ulong available, total, free;
            if (!GetDiskFreeSpaceEx(path, out available, out total, out free))
                return -1;
            return available > long.MaxValue ? long.MaxValue : (long)available;
        }
    }

    // Native disabled button text is almost black on dark backgrounds.
    // Keep the real Button behavior/accessibility; customize only dark painting.
    public sealed class ThemeButton : System.Windows.Forms.Button {
        private bool dark, hover, pressed;
        public bool Dark { get { return dark; } set { dark = value; Invalidate(); } }
        protected override void OnPaint(System.Windows.Forms.PaintEventArgs e) {
            if (!dark) { base.OnPaint(e); return; }
            bool primary = FindForm() != null && FindForm().AcceptButton == this;
            var back = Enabled && primary ? System.Drawing.Color.FromArgb(36, 104, 110) : System.Drawing.Color.FromArgb(39, 42, 47);
            if (Enabled && pressed) back = System.Drawing.Color.FromArgb(58, 69, 80);
            else if (Enabled && hover) back = System.Drawing.Color.FromArgb(49, 55, 64);
            e.Graphics.Clear(back);
            var border = Enabled && (Focused || primary) ? System.Drawing.Color.FromArgb(103, 149, 164) : System.Drawing.Color.FromArgb(72, 78, 87);
            using (var pen = new System.Drawing.Pen(border)) e.Graphics.DrawRectangle(pen, 0, 0, Width - 1, Height - 1);
            var fore = Enabled ? System.Drawing.Color.FromArgb(218, 223, 229) : System.Drawing.Color.FromArgb(151, 159, 169);
            var flags = System.Windows.Forms.TextFormatFlags.HorizontalCenter | System.Windows.Forms.TextFormatFlags.VerticalCenter | System.Windows.Forms.TextFormatFlags.EndEllipsis;
            if (!ShowKeyboardCues) flags |= System.Windows.Forms.TextFormatFlags.HidePrefix;
            System.Windows.Forms.TextRenderer.DrawText(e.Graphics, Text, Font, ClientRectangle, fore, flags);
            if (Focused && ShowFocusCues) System.Windows.Forms.ControlPaint.DrawFocusRectangle(e.Graphics, System.Drawing.Rectangle.Inflate(ClientRectangle, -4, -4), fore, back);
        }
        protected override void OnMouseEnter(EventArgs e) { hover = true; base.OnMouseEnter(e); Invalidate(); }
        protected override void OnMouseLeave(EventArgs e) { hover = false; pressed = false; base.OnMouseLeave(e); Invalidate(); }
        protected override void OnMouseDown(System.Windows.Forms.MouseEventArgs e) { pressed = true; base.OnMouseDown(e); Invalidate(); }
        protected override void OnMouseUp(System.Windows.Forms.MouseEventArgs e) { pressed = false; base.OnMouseUp(e); Invalidate(); }
        protected override void OnEnabledChanged(EventArgs e) { base.OnEnabledChanged(e); Invalidate(); }
        protected override void OnGotFocus(EventArgs e) { base.OnGotFocus(e); Invalidate(); }
        protected override void OnLostFocus(EventArgs e) { base.OnLostFocus(e); Invalidate(); }
    }

    public sealed class ThemeMenu : System.Windows.Forms.ContextMenuStrip {
        private bool dark;
        private sealed class Palette : System.Windows.Forms.ProfessionalColorTable {
            public override System.Drawing.Color ToolStripDropDownBackground { get { return System.Drawing.Color.FromArgb(39,42,47); } }
            public override System.Drawing.Color MenuItemSelected { get { return System.Drawing.Color.FromArgb(55,70,78); } }
            public override System.Drawing.Color MenuItemBorder { get { return System.Drawing.Color.FromArgb(72,78,87); } }
            public override System.Drawing.Color MenuBorder { get { return System.Drawing.Color.FromArgb(72,78,87); } }
            public override System.Drawing.Color ImageMarginGradientBegin { get { return ToolStripDropDownBackground; } }
            public override System.Drawing.Color ImageMarginGradientMiddle { get { return ToolStripDropDownBackground; } }
            public override System.Drawing.Color ImageMarginGradientEnd { get { return ToolStripDropDownBackground; } }
        }
        public bool Dark { get { return dark; } set {
            dark = value;
            Renderer = value ? new System.Windows.Forms.ToolStripProfessionalRenderer(new Palette()) : new System.Windows.Forms.ToolStripProfessionalRenderer();
            BackColor = value ? System.Drawing.Color.FromArgb(39,42,47) : System.Drawing.SystemColors.Menu;
            ForeColor = value ? System.Drawing.Color.FromArgb(218,223,229) : System.Drawing.SystemColors.MenuText;
            foreach (System.Windows.Forms.ToolStripItem item in Items) item.ForeColor = ForeColor;
        } }
    }

    // Native combo themes ignore BackColor for disabled/closed dropdown faces.
    // Keep standard keyboard/dropdown behavior and repaint only that face.
    public sealed class ThemeComboBox : System.Windows.Forms.ComboBox {
        private bool dark;
        public bool Dark {
            get { return dark; }
            set {
                dark = value;
                DrawMode = value ? System.Windows.Forms.DrawMode.OwnerDrawFixed : System.Windows.Forms.DrawMode.Normal;
                FlatStyle = value ? System.Windows.Forms.FlatStyle.Flat : System.Windows.Forms.FlatStyle.Standard;
                Invalidate();
            }
        }
        protected override void OnDrawItem(System.Windows.Forms.DrawItemEventArgs e) {
            if (!dark) { base.OnDrawItem(e); return; }
            bool selected = (e.State & System.Windows.Forms.DrawItemState.Selected) != 0;
            var back = selected ? System.Drawing.Color.FromArgb(50, 72, 80) : System.Drawing.Color.FromArgb(39, 42, 47);
            var fore = Enabled ? System.Drawing.Color.FromArgb(218, 223, 229) : System.Drawing.Color.FromArgb(151, 159, 169);
            using (var brush = new System.Drawing.SolidBrush(back)) e.Graphics.FillRectangle(brush, e.Bounds);
            string text = e.Index >= 0 ? GetItemText(Items[e.Index]) : Text;
            System.Windows.Forms.TextRenderer.DrawText(e.Graphics, text, Font, e.Bounds, fore,
                System.Windows.Forms.TextFormatFlags.Left | System.Windows.Forms.TextFormatFlags.VerticalCenter | System.Windows.Forms.TextFormatFlags.EndEllipsis);
        }
        protected override void WndProc(ref System.Windows.Forms.Message m) {
            base.WndProc(ref m);
            if (dark && (m.Msg == 0x000F || m.Msg == 0x0317 || m.Msg == 0x0318) && IsHandleCreated) {
                using (var graphics = m.Msg == 0x000F ? System.Drawing.Graphics.FromHwnd(Handle) : System.Drawing.Graphics.FromHdc(m.WParam)) {
                    var bounds = ClientRectangle;
                    var back = System.Drawing.Color.FromArgb(39, 42, 47);
                    var fore = Enabled ? System.Drawing.Color.FromArgb(218, 223, 229) : System.Drawing.Color.FromArgb(151, 159, 169);
                    using (var brush = new System.Drawing.SolidBrush(back)) graphics.FillRectangle(brush, bounds);
                    using (var pen = new System.Drawing.Pen(Focused ? System.Drawing.Color.FromArgb(103, 149, 164) : System.Drawing.Color.FromArgb(72, 78, 87)))
                        graphics.DrawRectangle(pen, 0, 0, bounds.Width - 1, bounds.Height - 1);
                    int arrowWidth = Math.Max(22, bounds.Height);
                    var textBounds = new System.Drawing.Rectangle(7, 1, Math.Max(0, bounds.Width - arrowWidth - 9), bounds.Height - 2);
                    System.Windows.Forms.TextRenderer.DrawText(graphics, Text, Font, textBounds, fore,
                        System.Windows.Forms.TextFormatFlags.Left | System.Windows.Forms.TextFormatFlags.VerticalCenter | System.Windows.Forms.TextFormatFlags.EndEllipsis);
                    int x = bounds.Width - arrowWidth / 2, y = bounds.Height / 2;
                    using (var pen = new System.Drawing.Pen(fore)) graphics.DrawLines(pen, new [] {
                        new System.Drawing.Point(x - 4, y - 2), new System.Drawing.Point(x, y + 2), new System.Drawing.Point(x + 4, y - 2) });
                }
            }
        }
        protected override void OnEnabledChanged(EventArgs e) { base.OnEnabledChanged(e); Invalidate(); }
    }

    // Paint disabled labels ourselves: Windows otherwise forces near-black text.
    public sealed class ThemeCheckBox : System.Windows.Forms.CheckBox {
        private bool dark;
        public bool Dark { get { return dark; } set { dark = value; Invalidate(); } }
        protected override void OnPaint(System.Windows.Forms.PaintEventArgs e) {
            if (!dark) { base.OnPaint(e); return; }
            e.Graphics.Clear(BackColor);
            int side = Math.Max(12, Math.Min(16, Font.Height));
            int y = (Height - side) / 2;
            var fore = Enabled ? System.Drawing.Color.FromArgb(218, 223, 229) : System.Drawing.Color.FromArgb(151, 159, 169);
            using (var brush = new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(39, 42, 47))) e.Graphics.FillRectangle(brush, 1, y, side, side);
            using (var pen = new System.Drawing.Pen(System.Drawing.Color.FromArgb(91, 101, 114))) e.Graphics.DrawRectangle(pen, 1, y, side, side);
            if (Checked) using (var pen = new System.Drawing.Pen(fore, 2)) e.Graphics.DrawLines(pen, new [] {
                new System.Drawing.Point(4, y + side / 2), new System.Drawing.Point(7, y + side - 4), new System.Drawing.Point(side - 2, y + 4) });
            var textBounds = new System.Drawing.Rectangle(side + 7, 0, Math.Max(0, Width - side - 7), Height);
            System.Windows.Forms.TextRenderer.DrawText(e.Graphics, Text, Font, textBounds, fore,
                System.Windows.Forms.TextFormatFlags.Left | System.Windows.Forms.TextFormatFlags.VerticalCenter | System.Windows.Forms.TextFormatFlags.WordBreak);
            if (Focused && ShowFocusCues) System.Windows.Forms.ControlPaint.DrawFocusRectangle(e.Graphics, textBounds, fore, BackColor);
        }
    }


    public sealed class ThemeTabs : System.Windows.Forms.TabControl {
        private bool dark;
        public bool Dark {
            get { return dark; }
            set { dark = value; DrawMode = value ? System.Windows.Forms.TabDrawMode.OwnerDrawFixed : System.Windows.Forms.TabDrawMode.Normal; Invalidate(); }
        }
        protected override void OnDrawItem(System.Windows.Forms.DrawItemEventArgs e) {
            if (!dark) { base.OnDrawItem(e); return; }
            var back = e.Index == SelectedIndex ? System.Drawing.Color.FromArgb(43, 50, 58) : System.Drawing.Color.FromArgb(32, 35, 40);
            using (var brush = new System.Drawing.SolidBrush(back)) e.Graphics.FillRectangle(brush, e.Bounds);
            System.Windows.Forms.TextRenderer.DrawText(e.Graphics, TabPages[e.Index].Text, Font, e.Bounds,
                System.Drawing.Color.FromArgb(218, 223, 229), System.Windows.Forms.TextFormatFlags.HorizontalCenter | System.Windows.Forms.TextFormatFlags.VerticalCenter);
        }
        protected override void WndProc(ref System.Windows.Forms.Message m) {
            base.WndProc(ref m);
            if (dark && (m.Msg == 0x000F || m.Msg == 0x0317 || m.Msg == 0x0318) && IsHandleCreated) {
                using (var graphics = m.Msg == 0x000F ? System.Drawing.Graphics.FromHwnd(Handle) : System.Drawing.Graphics.FromHdc(m.WParam)) {
                    var page = DisplayRectangle;
                    // Native tab painting adds white bevels after owner drawing.
                    // Repaint the complete header row after the native pass.
                    using (var brush = new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(28, 30, 34)))
                        graphics.FillRectangle(brush, 0, 0, Width, Math.Max(0, page.Top - 3));
                    for (int i = 0; i < TabCount; i++) {
                        var rect = GetTabRect(i);
                        var fill = i == SelectedIndex ? System.Drawing.Color.FromArgb(43, 50, 58) : System.Drawing.Color.FromArgb(32, 35, 40);
                        using (var brush = new System.Drawing.SolidBrush(fill)) graphics.FillRectangle(brush, rect);
                        using (var border = new System.Drawing.Pen(System.Drawing.Color.FromArgb(72, 78, 87)))
                            graphics.DrawRectangle(border, rect.X, rect.Y, Math.Max(0, rect.Width - 1), Math.Max(0, rect.Height - 1));
                        System.Windows.Forms.TextRenderer.DrawText(graphics, TabPages[i].Text, Font, rect,
                            System.Drawing.Color.FromArgb(218, 223, 229), System.Windows.Forms.TextFormatFlags.HorizontalCenter | System.Windows.Forms.TextFormatFlags.VerticalCenter | System.Windows.Forms.TextFormatFlags.NoPrefix);
                    }
                    using (var pen = new System.Drawing.Pen(System.Drawing.Color.FromArgb(48, 53, 60), 4))
                        graphics.DrawRectangle(pen, 2, page.Top - 2, Math.Max(0, Width - 4), Math.Max(0, Height - page.Top));
                }
            }
        }
    }


    // Passive owner handle: never subclasses the parent's window procedure.
    public sealed class WindowOwner : System.Windows.Forms.IWin32Window {
        private readonly IntPtr handle;
        public WindowOwner(IntPtr handle) { this.handle = handle; }
        public IntPtr Handle { get { return handle; } }
    }


    // Header custom draw leaves all row rendering/selection with Windows.
    // Paint the whole header, including empty space after the last column.
    public sealed class ThemeListView : System.Windows.Forms.ListView {
        [StructLayout(LayoutKind.Sequential)]
        private struct Header { public IntPtr window; public UIntPtr id; public int code; }
        [StructLayout(LayoutKind.Sequential)]
        private struct Rect { public int left, top, right, bottom; }
        [StructLayout(LayoutKind.Sequential)]
        private struct CustomDraw {
            public Header header; public uint stage; public IntPtr dc; public Rect rect;
            public UIntPtr item; public uint state; public IntPtr parameter;
        }
        [DllImport("user32.dll", EntryPoint = "SendMessageW")]
        private static extern IntPtr SendMessage(IntPtr window, int message, IntPtr wparam, IntPtr lparam);
        [DllImport("user32.dll", EntryPoint = "SendMessageW")]
        private static extern IntPtr GetItemRect(IntPtr window, int message, IntPtr index, ref Rect rect);
        [DllImport("user32.dll")]
        private static extern bool GetClientRect(IntPtr window, out Rect rect);
        [DllImport("user32.dll")]
        private static extern bool InvalidateRect(IntPtr window, IntPtr rect, bool erase);
        private bool dark;
        public bool Dark {
            get { return dark; }
            set {
                dark = value;
                Invalidate();
                if (IsHandleCreated) {
                    IntPtr header = SendMessage(Handle, 0x101F, IntPtr.Zero, IntPtr.Zero);
                    if (header != IntPtr.Zero) InvalidateRect(header, IntPtr.Zero, true);
                }
            }
        }
        protected override void WndProc(ref System.Windows.Forms.Message m) {
            if (dark && (m.Msg == 0x004E || m.Msg == 0x204E) && m.LParam != IntPtr.Zero) {
                var notification = (Header)Marshal.PtrToStructure(m.LParam, typeof(Header));
                if (notification.code == -12 && notification.window == SendMessage(Handle, 0x101F, IntPtr.Zero, IntPtr.Zero)) {
                    var draw = (CustomDraw)Marshal.PtrToStructure(m.LParam, typeof(CustomDraw));
                    if (draw.stage == 2) { // CDDS_POSTPAINT: native headers can repaint their unused tail last.
                        Rect client;
                        GetClientRect(notification.window, out client);
                        int right = 0;
                        for (int i = 0; i < Columns.Count; i++) {
                            Rect item = new Rect();
                            if (GetItemRect(notification.window, 0x1207, new IntPtr(i), ref item) != IntPtr.Zero) right = Math.Max(right, item.right);
                        }
                        if (right < client.right) {
                            using (var graphics = System.Drawing.Graphics.FromHdc(draw.dc))
                            using (var fill = new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(43, 47, 54)))
                                graphics.FillRectangle(fill, right, client.top, client.right - right, client.bottom - client.top);
                        }
                        m.Result = IntPtr.Zero;
                        return;
                    }
                    if (draw.stage == 1 || draw.stage == 0x10001) { // Header background and individual cells.
                        Rect client;
                        GetClientRect(notification.window, out client);
                        using (var graphics = System.Drawing.Graphics.FromHdc(draw.dc))
                        using (var fill = new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(43, 47, 54)))
                        using (var border = new System.Drawing.Pen(System.Drawing.Color.FromArgb(72, 78, 87))) {
                            graphics.FillRectangle(fill, client.left, client.top, client.right - client.left, client.bottom - client.top);
                            for (int i = 0; i < Columns.Count; i++) {
                                Rect item = new Rect();
                                if (GetItemRect(notification.window, 0x1207, new IntPtr(i), ref item) == IntPtr.Zero) continue;
                                graphics.DrawLine(border, item.right - 1, item.top, item.right - 1, item.bottom - 1);
                                var bounds = new System.Drawing.Rectangle(item.left + 7, item.top, Math.Max(0, item.right - item.left - 14), item.bottom - item.top);
                                var flags = System.Windows.Forms.TextFormatFlags.VerticalCenter | System.Windows.Forms.TextFormatFlags.EndEllipsis | System.Windows.Forms.TextFormatFlags.NoPrefix;
                                if (Columns[i].TextAlign == System.Windows.Forms.HorizontalAlignment.Right) flags |= System.Windows.Forms.TextFormatFlags.Right;
                                else if (Columns[i].TextAlign == System.Windows.Forms.HorizontalAlignment.Center) flags |= System.Windows.Forms.TextFormatFlags.HorizontalCenter;
                                System.Windows.Forms.TextRenderer.DrawText(graphics, Columns[i].Text, Font, bounds, System.Drawing.Color.FromArgb(218, 223, 229), flags);
                            }
                            graphics.DrawLine(border, 0, client.bottom - 1, client.right, client.bottom - 1);
                        }
                        m.Result = new IntPtr(draw.stage == 1 ? 0x30 : 4); // Request cells and final paint; skip each native white cell fill.
                        return;
                    }
                }
            }
            base.WndProc(ref m);
        }
    }

}

// [DIFF] Full-resolution preview diagnostics. Inputs are detached, color-managed
// display bitmaps, never screenshots or scaled PictureBox surfaces. Row buffers
// bound working memory; no original/preview file is modified by this analysis.
namespace WebPOptimizerRuntime {
    public sealed class PreviewDifference : IDisposable {
        public System.Drawing.Bitmap Heatmap;
        public double MeanAbsolute, RootMeanSquare, BrightnessShift, ChangedPercent;
        public int MaximumChannelDifference;
        public long Pixels;
        public void Dispose() { if (Heatmap != null) { Heatmap.Dispose(); Heatmap = null; } }
        public static PreviewDifference Analyze(System.Drawing.Bitmap original, System.Drawing.Bitmap converted) {
            if (original.Size != converted.Size) throw new ArgumentException("Images must have identical dimensions; resized comparisons are not measured.");
            var result = new PreviewDifference();
            result.Pixels = (long)original.Width * original.Height;
            if (result.Pixels > 16000000) throw new ArgumentException("This page exceeds the 16-million-pixel analysis limit.");
            var rectangle = new System.Drawing.Rectangle(0, 0, original.Width, original.Height);
            var format = System.Drawing.Imaging.PixelFormat.Format32bppArgb;
            System.Drawing.Imaging.BitmapData a = null, b = null, h = null;
            try {
                result.Heatmap = new System.Drawing.Bitmap(original.Width, original.Height, format);
                a = original.LockBits(rectangle, System.Drawing.Imaging.ImageLockMode.ReadOnly, format);
                b = converted.LockBits(rectangle, System.Drawing.Imaging.ImageLockMode.ReadOnly, format);
                h = result.Heatmap.LockBits(rectangle, System.Drawing.Imaging.ImageLockMode.WriteOnly, format);
                byte[] rowA = new byte[original.Width * 4], rowB = new byte[rowA.Length], rowH = new byte[rowA.Length];
                double absolute = 0, squared = 0, brightness = 0; long changed = 0;
                for (int y = 0; y < original.Height; y++) {
                    Marshal.Copy(IntPtr.Add(a.Scan0, y * a.Stride), rowA, 0, rowA.Length);
                    Marshal.Copy(IntPtr.Add(b.Scan0, y * b.Stride), rowB, 0, rowB.Length);
                    for (int x = 0; x < rowA.Length; x += 4) {
                        int maximum = 0;
                        for (int c = 0; c < 3; c++) {
                            int delta = rowB[x+c] - rowA[x+c], magnitude = Math.Abs(delta);
                            absolute += magnitude; squared += delta * delta;
                            maximum = Math.Max(maximum, magnitude);
                            // Encoded sRGB brightness proxy, not linear luminance or Delta E.
                            brightness += delta * (c == 0 ? .0722 : c == 1 ? .7152 : .2126);
                        }
                        if (maximum != 0) changed++;
                        result.MaximumChannelDifference = Math.Max(result.MaximumChannelDifference, maximum);
                        int amplified = Math.Min(255, maximum * 8);
                        rowH[x] = 0; rowH[x+1] = (byte)(amplified / 2); rowH[x+2] = (byte)amplified; rowH[x+3] = 255;
                    }
                    Marshal.Copy(rowH, 0, IntPtr.Add(h.Scan0, y * h.Stride), rowH.Length);
                }
                result.MeanAbsolute = absolute / (result.Pixels * 3.0);
                result.RootMeanSquare = Math.Sqrt(squared / (result.Pixels * 3.0));
                result.BrightnessShift = brightness / result.Pixels;
                result.ChangedPercent = changed * 100.0 / result.Pixels;
            } catch {
                if (h != null) { result.Heatmap.UnlockBits(h); h = null; }
                result.Dispose(); throw;
            } finally {
                if (a != null) original.UnlockBits(a);
                if (b != null) converted.UnlockBits(b);
                if (h != null && result.Heatmap != null) result.Heatmap.UnlockBits(h);
            }
            return result;
        }
    }
}

namespace WebPOptimizerRuntime {
    // No Python delegates run on worker threads. UI polls completion via Timer.
    public sealed class PreviewDifferenceJob : IDisposable {
        private readonly object gate = new object();
        private bool done, abandoned;
        public PreviewDifference Result;
        public string Error;
        public bool Done { get { lock (gate) { return done; } } }
        public void Start(System.Drawing.Bitmap a, System.Drawing.Bitmap b) {
            var first = new System.Drawing.Bitmap(a);
            System.Drawing.Bitmap second;
            try { second = new System.Drawing.Bitmap(b); } catch { first.Dispose(); throw; }
            try {
                System.Threading.ThreadPool.QueueUserWorkItem(delegate {
                    PreviewDifference value = null; string error = null;
                    try { value = PreviewDifference.Analyze(first, second); }
                    catch (Exception ex) { error = ex.Message; }
                    finally { first.Dispose(); second.Dispose(); }
                    lock (gate) {
                        if (abandoned) { if (value != null) value.Dispose(); }
                        else { Result = value; Error = error; }
                        done = true;
                    }
                });
            } catch { first.Dispose(); second.Dispose(); throw; }
        }
        public PreviewDifference TakeResult() { lock (gate) { var value = Result; Result = null; return value; } }
        public void Dispose() { lock (gate) { abandoned = true; if (Result != null) { Result.Dispose(); Result = null; } } }
    }
}
