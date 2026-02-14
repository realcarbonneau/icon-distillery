#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Icon Grid Browser — Standalone dev tool for browsing icon themes
in the Icon Distillery repository.

Usage:
    python scripts/icon_grid_browser.py

Requires: wxPython, cairosvg (for SVG rendering)
"""

import sys
import os
import io
from pathlib import Path
from dataclasses import dataclass, field

# Add scripts dir to path for icon_theme_processor import
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# --- Dependency check ---
try:
    import cairosvg
except ImportError:
    print("ERROR: cairosvg is required for SVG icon rendering.")
    print("  Install: pip install cairosvg  or  sudo apt install python3-cairosvg")
    sys.exit(1)

from icon_theme_processor import ThemeCatalog, ICON_EXTENSIONS

import wx


# ============================================================================
# Data Layer
# ============================================================================

def _theme_label(theme):
    """Get display label for a theme from its catalog config."""
    if "variants" in theme.config:
        for v in theme.config["variants"]:
            if v["id"] == theme.theme_id:
                return v.get("label", theme.theme_id.title())
    return theme.config.get("label", theme.theme_id.title())


@dataclass
class IconEntry:
    id: str
    name: str = ""
    hints: list = field(default_factory=list)
    source: str = ""               # theme_id
    category: str = ""             # context (actions, places, etc.)
    status: str = "external"       # hinted, duplicate, external
    paths: dict = field(default_factory=dict)   # size -> path_str
    duplicates: list = field(default_factory=list)
    duplicate_of: str = ""
    file: str = ""                 # bare filename from icons.json


class IconDataModel:
    """Loads and indexes icon data from ThemeCatalog themes."""

    def __init__(self):
        self._catalog = ThemeCatalog()
        self._entries = {}          # (theme_id, icon_id) -> IconEntry
        self._bitmap_cache = {}     # (entry_id, size) -> wx.Bitmap
        self._discovered_sizes = set()
        self._loaded_themes = set()
        self._themes = {}           # theme_id -> Theme (cached)

        # Pre-cache Theme objects for directory checks (prints theme headers)
        for tid in self._catalog.theme_ids():
            try:
                self._themes[tid] = self._catalog.get_theme(tid)
            except SystemExit:
                pass

    @property
    def catalog(self):
        return self._catalog

    @property
    def discovered_sizes(self):
        """All icon sizes discovered across loaded themes, sorted."""
        return sorted(self._discovered_sizes)

    def theme_ids(self):
        """Return all non-skipped theme IDs."""
        return self._catalog.theme_ids()

    def theme_available(self, theme_id):
        """Check if theme directory and icons.json exist on disk."""
        theme = self._themes.get(theme_id)
        if not theme:
            return False
        return os.path.isdir(theme.dir) and os.path.isfile(theme.icons_path)

    def theme_display_label(self, theme_id):
        """Get display label for a theme."""
        theme = self._themes.get(theme_id)
        if not theme:
            return theme_id.title()
        return _theme_label(theme)

    def theme_dir(self, theme_id):
        """Get theme directory path string."""
        theme = self._themes.get(theme_id)
        return theme.dir if theme else ""

    def load_theme(self, theme_id):
        """Load all icons from a theme's icons.json and disk scan."""
        if theme_id in self._loaded_themes:
            return
        self._loaded_themes.add(theme_id)

        theme = self._themes.get(theme_id)
        if not theme or not os.path.isdir(theme.dir):
            return
        if not os.path.isfile(theme.icons_path):
            print(f"Warning: icons.json not found for {theme_id}, skipping")
            return

        # Load icons.json metadata
        try:
            icons_data = theme.icons_data
        except SystemExit:
            return
        icons = icons_data.get("icons", {})

        # Scan disk for actual file paths
        try:
            discovered = theme.scan_directory()
        except SystemExit:
            discovered = {}

        # Build IconEntry objects from icons.json, paths from disk scan
        for icon_id, info in icons.items():
            context = info.get("context", "")
            filename = info.get("file", "")
            stem = Path(filename).stem

            # Status from icons.json fields
            if info.get("duplicate_of"):
                status = "duplicate"
            elif info.get("hints"):
                status = "hinted"
            else:
                status = "external"

            # Paths from disk scan (take first path per size)
            paths = {}
            if icon_id in discovered:
                for size, path_list in discovered[icon_id].get("paths", {}).items():
                    paths[size] = path_list[0]
                    self._discovered_sizes.add(size)

            key = (theme_id, icon_id)
            self._entries[key] = IconEntry(
                id=icon_id,
                name=info.get("label", stem.replace("-", " ").replace("_", " ").title()),
                hints=info.get("hints", []),
                source=theme_id,
                category=context,
                status=status,
                paths=paths,
                duplicates=info.get("duplicates", []),
                duplicate_of=info.get("duplicate_of", ""),
                file=filename,
            )

    def get_filtered(self, query="", themes=None, show_hinted=True,
                     show_duplicates=True, show_unhinted=True,
                     min_size=None, sort_key=None):
        """Return filtered list of IconEntry."""
        if themes is None:
            themes = set()

        results = []
        query_terms = query.lower().split() if query else []

        for key, entry in self._entries.items():
            theme_id = key[0]

            if theme_id not in themes:
                continue

            # Size filter
            if min_size and entry.paths:
                if max(entry.paths.keys()) < min_size:
                    continue

            # Status filter
            if entry.status == "hinted" and not show_hinted:
                continue
            if entry.status == "duplicate" and not show_duplicates:
                continue
            if entry.status == "external" and not show_unhinted:
                continue

            # Search filter
            if query_terms:
                search_text = (
                    f"{entry.name} {entry.id} {' '.join(entry.hints)} "
                    f"{entry.source} {entry.category}"
                ).lower()
                if not all(t in search_text for t in query_terms):
                    continue

            results.append(entry)

        if sort_key:
            results.sort(key=sort_key)
        else:
            results.sort(key=lambda e: (e.source, e.name.lower()))
        return results

    def get_bitmap(self, entry, size):
        """Get a wx.Bitmap for the given entry at the given size."""
        cache_key = (id(entry), size)
        if cache_key in self._bitmap_cache:
            return self._bitmap_cache[cache_key]

        # Find best available size
        path_str = entry.paths.get(size)
        if not path_str:
            available = sorted(entry.paths.keys())
            if not available:
                return wx.NullBitmap
            nearest = min(available, key=lambda s: abs(s - size))
            path_str = entry.paths[nearest]

        bitmap = self._load_bitmap(path_str, size)
        self._bitmap_cache[cache_key] = bitmap
        return bitmap

    def _load_bitmap(self, path_str, target_size):
        """Load a bitmap from a file path (PNG or SVG)."""
        try:
            if path_str.endswith((".svg", ".svgz")):
                png_data = cairosvg.svg2png(
                    url=str(path_str),
                    output_width=target_size,
                    output_height=target_size,
                )
                stream = io.BytesIO(png_data)
                image = wx.Image(stream)
            else:
                image = wx.Image(path_str)

            if not image.IsOk():
                return wx.NullBitmap

            if image.GetWidth() != target_size or image.GetHeight() != target_size:
                image.Rescale(target_size, target_size, wx.IMAGE_QUALITY_HIGH)

            return image.ConvertToBitmap()
        except Exception:
            return wx.NullBitmap

    def clear_cache(self):
        """Clear the bitmap cache (e.g., on size change)."""
        self._bitmap_cache.clear()


# ============================================================================
# UI Layer
# ============================================================================

# Border colors by status
COLOR_HINTED = wx.Colour(76, 175, 80)       # green — has hints
COLOR_DUPLICATE = wx.Colour(158, 158, 158)   # grey
COLOR_EXTERNAL = wx.Colour(220, 220, 220)    # light grey — no hints yet
COLOR_HOVER = wx.Colour(33, 150, 243)        # blue highlight

CELL_PADDING = 8
TEXT_HEIGHT = 30  # space for 2 lines of text below icon


def _status_border_color(entry):
    """Return the border color for an icon's status."""
    if entry.status == "hinted":
        return COLOR_HINTED
    elif entry.status == "duplicate":
        return COLOR_DUPLICATE
    else:
        return COLOR_EXTERNAL


class IconGridPanel(wx.ScrolledWindow):
    """Scrollable grid of icon cells with custom painting."""

    # Pre-created drawing resources (class-level, initialized once after wx.App)
    _BUFFER_MAX_HEIGHT = 30000
    _draw_resources = None

    @classmethod
    def _init_draw_resources(cls):
        """Create shared drawing resources (fonts, pens, brushes, colours)."""
        if cls._draw_resources is not None:
            return
        cls._draw_resources = {
            "font_name": wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                 wx.FONTWEIGHT_NORMAL),
            "font_src": wx.Font(7, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                wx.FONTWEIGHT_NORMAL),
            "bg_light": wx.Colour(245, 245, 245),
            "bg_dark": wx.Colour(40, 40, 40),
            "cell_bg_light": wx.Colour(255, 255, 255),
            "cell_bg_dark": wx.Colour(50, 50, 50),
            "text_light": wx.Colour(60, 60, 60),
            "text_dark": wx.Colour(220, 220, 220),
            "sub_light": wx.Colour(120, 120, 120),
            "sub_dark": wx.Colour(160, 160, 160),
            "ext_border_colour": wx.Colour(200, 200, 200),
            "pen_hover": wx.Pen(COLOR_HOVER, 3),
            "pen_hinted": wx.Pen(COLOR_HINTED, 2),
            "pen_dup": wx.Pen(COLOR_DUPLICATE, 2),
            "pen_ext": wx.Pen(COLOR_EXTERNAL, 2),
            "pen_ext_dim": wx.Pen(wx.Colour(200, 200, 200), 1),
        }

    def __init__(self, parent, model):
        super().__init__(parent, style=wx.VSCROLL | wx.WANTS_CHARS)
        self._init_draw_resources()
        self._model = model
        self._entries = []
        self._display_size = 32
        self._dark_bg = False
        self._hover_enabled = True
        self._hover_index = -1
        self._pinned = False
        self._pinned_index = -1
        self._popup = None
        self._text_cache = {}  # (entry_id, max_tw) -> (truncated_name, tw, th)
        self._buffer = None    # off-screen bitmap for smooth scrolling

        self.SetScrollRate(0, 20)
        self.SetBackgroundStyle(wx.BG_STYLE_PAINT)

        self.Bind(wx.EVT_PAINT, self._on_paint)
        self.Bind(wx.EVT_SIZE, self._on_size)
        self.Bind(wx.EVT_MOTION, self._on_motion)
        self.Bind(wx.EVT_LEAVE_WINDOW, self._on_leave)
        self.Bind(wx.EVT_LEFT_DOWN, self._on_click)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key_down)

    @property
    def cell_width(self):
        return self._display_size + CELL_PADDING * 2 + 40

    @property
    def cell_height(self):
        return self._display_size + CELL_PADDING * 2 + TEXT_HEIGHT

    @property
    def cols(self):
        w = self.GetClientSize().width
        return max(1, w // self.cell_width)

    def set_entries(self, entries):
        self._entries = entries
        self._hover_index = -1
        self._pinned = False
        self._pinned_index = -1
        self._text_cache.clear()
        self._destroy_popup()
        self._update_virtual_size()
        self._rebuild_buffer()
        self.Scroll(0, 0)
        self.Refresh()

    def set_display_size(self, size):
        if size != self._display_size:
            self._display_size = size
            self._model.clear_cache()
            self._text_cache.clear()
            self._update_virtual_size()
            self._rebuild_buffer()
            self.Refresh()

    def set_dark_bg(self, dark):
        self._dark_bg = dark
        self._rebuild_buffer()
        self.Refresh()

    def set_hover_enabled(self, enabled):
        self._hover_enabled = enabled
        if not enabled and not self._pinned:
            self._hover_index = -1
            self._destroy_popup()
            self.Refresh()

    def _update_virtual_size(self):
        cols = self.cols
        rows = (len(self._entries) + cols - 1) // cols if cols > 0 else 0
        self.SetVirtualSize(self.GetClientSize().width, rows * self.cell_height + 20)

    def _index_at(self, x, y):
        """Get entry index at pixel position (in virtual coords)."""
        vx, vy = self.CalcUnscrolledPosition(x, y)
        cols = self.cols
        col = vx // self.cell_width
        row = vy // self.cell_height
        if col >= cols:
            return -1
        idx = row * cols + col
        if idx >= len(self._entries):
            return -1
        return idx

    def _cell_rect(self, index):
        """Get the rect for a cell in virtual coordinates."""
        cols = self.cols
        row = index // cols
        col = index % cols
        x = col * self.cell_width
        y = row * self.cell_height
        return wx.Rect(x, y, self.cell_width, self.cell_height)

    def _get_truncated_text(self, dc, entry_id, name, max_tw):
        """Get truncated name and extents, cached per entry+width."""
        cache_key = (entry_id, max_tw)
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]
        tw, th = dc.GetTextExtent(name)
        if tw > max_tw:
            while tw > max_tw and len(name) > 1:
                name = name[:-1]
                tw, th = dc.GetTextExtent(name)
        self._text_cache[cache_key] = (name, tw, th)
        return name, tw, th

    def _rebuild_buffer(self):
        """Pre-render all cells to an off-screen bitmap for smooth scrolling."""
        entries = self._entries
        client_w = self.GetClientSize().width
        if not entries or client_w < 1:
            self._buffer = None
            return

        cols = self.cols
        cw = self.cell_width
        ch = self.cell_height
        ds = self._display_size
        rows = (len(entries) + cols - 1) // cols
        buf_w = max(client_w, cols * cw)
        buf_h = rows * ch + 20

        if buf_h > self._BUFFER_MAX_HEIGHT:
            self._buffer = None
            return

        bmp = wx.Bitmap(buf_w, buf_h)
        mdc = wx.MemoryDC(bmp)
        res = self._draw_resources
        dark = self._dark_bg

        mdc.SetBackground(wx.Brush(res["bg_dark"] if dark else res["bg_light"]))
        mdc.Clear()

        text_color = res["text_dark"] if dark else res["text_light"]
        sub_color = res["sub_dark"] if dark else res["sub_light"]
        cell_bg = res["cell_bg_dark"] if dark else res["cell_bg_light"]
        cell_brush = wx.Brush(cell_bg)
        pen_ext_dim = res["pen_ext_dim"]
        status_pens = {
            "hinted": res["pen_hinted"],
            "duplicate": res["pen_dup"],
            "external": res["pen_ext"],
        }

        mdc.SetFont(res["font_name"])
        max_tw = cw - 12

        for i, entry in enumerate(entries):
            row = i // cols
            col = i % cols
            rx = col * cw
            ry = row * ch

            status = entry.status
            if status == "external":
                mdc.SetPen(pen_ext_dim)
            else:
                mdc.SetPen(status_pens.get(status, res["pen_ext"]))
            mdc.SetBrush(cell_brush)
            mdc.DrawRoundedRectangle(rx + 5, ry + 5, cw - 10, ch - 10, 3)

            bitmap = self._model.get_bitmap(entry, ds)
            if bitmap.IsOk():
                mdc.DrawBitmap(bitmap, rx + (cw - ds) // 2, ry + CELL_PADDING, True)

            mdc.SetFont(res["font_name"])
            mdc.SetTextForeground(text_color)
            name, tw, th = self._get_truncated_text(
                mdc, id(entry), entry.name, max_tw)
            ty = ry + CELL_PADDING + ds + 2
            mdc.DrawText(name, rx + (cw - tw) // 2, ty)

            mdc.SetFont(res["font_src"])
            mdc.SetTextForeground(sub_color)
            src = entry.source
            tw2, _ = mdc.GetTextExtent(src)
            mdc.DrawText(src, rx + (cw - tw2) // 2, ty + th + 1)

        mdc.SelectObject(wx.NullBitmap)
        self._buffer = bmp

    def _on_paint(self, event):
        dc = wx.AutoBufferedPaintDC(self)
        self.DoPrepareDC(dc)

        if self._buffer is not None:
            res = self._draw_resources
            dark = self._dark_bg
            dc.SetBackground(wx.Brush(res["bg_dark"] if dark else res["bg_light"]))
            dc.Clear()
            dc.DrawBitmap(self._buffer, 0, 0)

            # Draw hover/pin highlight overlays
            cols = self.cols
            cw = self.cell_width
            ch = self.cell_height
            pen_hover = res["pen_hover"]
            for idx in (self._hover_index,
                        self._pinned_index if self._pinned else -1):
                if 0 <= idx < len(self._entries):
                    rx = (idx % cols) * cw
                    ry = (idx // cols) * ch
                    dc.SetPen(pen_hover)
                    dc.SetBrush(wx.TRANSPARENT_BRUSH)
                    dc.DrawRoundedRectangle(rx + 1, ry + 1, cw - 2, ch - 2, 5)
        else:
            self._paint_direct(dc)

    def _paint_direct(self, dc):
        """Fallback direct paint when buffer is too large or unavailable."""
        res = self._draw_resources

        dark = self._dark_bg
        dc.SetBackground(wx.Brush(res["bg_dark"] if dark else res["bg_light"]))
        dc.Clear()

        # Calculate visible range
        view_start = self.GetViewStart()
        client_h = self.GetClientSize().height
        scroll_y = view_start[1] * 20
        cols = self.cols
        cw = self.cell_width
        ch = self.cell_height
        ds = self._display_size

        first_row = max(0, scroll_y // ch)
        last_row = (scroll_y + client_h) // ch + 1
        first_idx = first_row * cols
        last_idx = min(len(self._entries), (last_row + 1) * cols)

        text_color = res["text_dark"] if dark else res["text_light"]
        sub_color = res["sub_dark"] if dark else res["sub_light"]
        cell_bg = res["cell_bg_dark"] if dark else res["cell_bg_light"]
        cell_brush = wx.Brush(cell_bg)
        pen_hover = res["pen_hover"]
        pen_ext_dim = res["pen_ext_dim"]

        # Status -> pen lookup
        status_pens = {
            "hinted": res["pen_hinted"],
            "duplicate": res["pen_dup"],
            "external": res["pen_ext"],
        }

        # Set name font once, get max_tw
        dc.SetFont(res["font_name"])
        max_tw = cw - 12

        hover_idx = self._hover_index
        pinned = self._pinned
        pinned_idx = self._pinned_index

        for i in range(first_idx, last_idx):
            entry = self._entries[i]
            row = i // cols
            col = i % cols
            rx = col * cw
            ry = row * ch
            is_highlighted = (i == hover_idx or (pinned and i == pinned_idx))

            dc.SetBrush(cell_brush)

            if is_highlighted:
                dc.SetPen(pen_hover)
                dc.DrawRoundedRectangle(rx + 1, ry + 1, cw - 2, ch - 2, 5)

            status = entry.status
            if status == "external" and not is_highlighted:
                dc.SetPen(pen_ext_dim)
            else:
                dc.SetPen(status_pens.get(status, res["pen_ext"]))
            dc.SetBrush(cell_brush)
            dc.DrawRoundedRectangle(rx + 5, ry + 5, cw - 10, ch - 10, 3)

            bitmap = self._model.get_bitmap(entry, ds)
            if bitmap.IsOk():
                dc.DrawBitmap(bitmap, rx + (cw - ds) // 2, ry + CELL_PADDING, True)

            # Name text (cached truncation)
            dc.SetFont(res["font_name"])
            dc.SetTextForeground(text_color)
            name, tw, th = self._get_truncated_text(
                dc, id(entry), entry.name, max_tw)
            ty = ry + CELL_PADDING + ds + 2
            dc.DrawText(name, rx + (cw - tw) // 2, ty)

            # Source text
            dc.SetFont(res["font_src"])
            dc.SetTextForeground(sub_color)
            src = entry.source
            tw2, _ = dc.GetTextExtent(src)
            dc.DrawText(src, rx + (cw - tw2) // 2, ty + th + 1)

    def _on_size(self, event):
        self._update_virtual_size()
        self._rebuild_buffer()
        self.Refresh()
        event.Skip()

    def _refresh_cell(self, index):
        """Refresh only a single cell's region."""
        if index < 0 or index >= len(self._entries):
            return
        rect = self._cell_rect(index)
        # Convert virtual coords to client coords for RefreshRect
        cx, cy = self.CalcScrolledPosition(rect.x, rect.y)
        self.RefreshRect(wx.Rect(cx, cy, rect.width, rect.height))

    def _on_motion(self, event):
        if self._pinned:
            event.Skip()
            return
        if not self._hover_enabled:
            event.Skip()
            return
        idx = self._index_at(event.GetX(), event.GetY())
        if idx != self._hover_index:
            old_idx = self._hover_index
            self._hover_index = idx
            # Only repaint the two affected cells
            self._refresh_cell(old_idx)
            self._refresh_cell(idx)
            if idx >= 0:
                self._show_hover_popup(idx)
            else:
                self._destroy_popup()
        event.Skip()

    def _on_leave(self, event):
        if self._pinned:
            self._hover_index = -1
            self.Refresh()
            event.Skip()
            return
        if not self._hover_enabled:
            event.Skip()
            return
        if self._popup and self._popup.IsShown():
            pos = wx.GetMousePosition()
            popup_rect = self._popup.GetScreenRect()
            if popup_rect.Contains(pos):
                event.Skip()
                return
        self._hover_index = -1
        self._destroy_popup()
        self.Refresh()
        event.Skip()

    def _on_click(self, event):
        idx = self._index_at(event.GetX(), event.GetY())
        if idx >= 0:
            self._pinned = True
            self._pinned_index = idx
            self._show_click_popup(idx, event.GetPosition())
        else:
            self._pinned = False
            self._pinned_index = -1
            self._destroy_popup()
        self.SetFocus()
        event.Skip()

    def _on_key_down(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.unpin()
        else:
            event.Skip()

    def unpin(self):
        """Dismiss pinned popup and clear all highlights."""
        self._pinned = False
        self._pinned_index = -1
        self._hover_index = -1
        self._destroy_popup()
        self.Refresh()

    def _show_hover_popup(self, index):
        """Show popup offset 2 cells from the hovered icon to allow scrolling."""
        self._destroy_popup()
        if index < 0 or index >= len(self._entries):
            return
        entry = self._entries[index]

        # Position 2 cells to the right of the hovered cell
        cell_rect = self._cell_rect(index)
        # Convert cell's right edge to client coords, then screen
        cell_right_x, cell_top_y = self.CalcScrolledPosition(cell_rect.x, cell_rect.y)
        screen_pos = self.ClientToScreen(wx.Point(cell_right_x, cell_top_y))
        offset_x = self.cell_width * 2

        self._popup = IconDetailPopup(self, self._model, entry)
        popup_size = self._popup.GetSize()
        display_idx = wx.Display.GetFromPoint(screen_pos)
        if display_idx == wx.NOT_FOUND:
            display_idx = 0
        display_rect = wx.Display(display_idx).GetClientArea()

        x = screen_pos.x + offset_x
        y = screen_pos.y

        # If it goes off the right edge, place 2 cells to the left instead
        if x + popup_size.width > display_rect.GetRight():
            x = screen_pos.x - popup_size.width - self.cell_width
        if y + popup_size.height > display_rect.GetBottom():
            y = display_rect.GetBottom() - popup_size.height

        self._popup.SetPosition(wx.Point(x, y))
        self._popup.Show()

    def _show_click_popup(self, index, pos):
        """Show popup at the click cursor position."""
        self._destroy_popup()
        if index < 0 or index >= len(self._entries):
            return
        entry = self._entries[index]
        screen_pos = self.ClientToScreen(pos)

        self._popup = IconDetailPopup(self, self._model, entry)
        popup_size = self._popup.GetSize()
        display_idx = wx.Display.GetFromPoint(screen_pos)
        if display_idx == wx.NOT_FOUND:
            display_idx = 0
        display_rect = wx.Display(display_idx).GetClientArea()

        x = screen_pos.x + 20
        y = screen_pos.y + 20

        if x + popup_size.width > display_rect.GetRight():
            x = screen_pos.x - popup_size.width - 10
        if y + popup_size.height > display_rect.GetBottom():
            y = display_rect.GetBottom() - popup_size.height

        self._popup.SetPosition(wx.Point(x, y))
        self._popup.Show()

    def _destroy_popup(self):
        if self._popup:
            self._popup.Destroy()
            self._popup = None


class IconDetailPopup(wx.Frame):
    """Hover/pinned popup showing icon details and metadata."""

    BORDER_WIDTH = 3

    def __init__(self, parent, model, entry):
        super().__init__(parent.GetTopLevelParent(), title="",
                         style=wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT
                         | wx.FRAME_NO_TASKBAR | wx.BORDER_NONE)
        self._grid_panel = parent
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

        border = wx.Panel(self)
        border.SetBackgroundColour(_status_border_color(entry))

        panel = wx.Panel(border)
        panel.SetBackgroundColour(wx.Colour(255, 255, 245))
        sizer = wx.BoxSizer(wx.VERTICAL)

        # --- Header ---
        header_font = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                              wx.FONTWEIGHT_BOLD)
        name_label = wx.TextCtrl(panel, value=f'"{entry.name}" ({entry.id})',
                                  style=wx.TE_READONLY | wx.BORDER_NONE)
        name_label.SetBackgroundColour(panel.GetBackgroundColour())
        name_label.SetFont(header_font)
        sizer.Add(name_label, 0, wx.EXPAND | wx.ALL, 5)

        # --- Info line ---
        info_parts = [f"Theme: {entry.source}", f"Status: {entry.status}"]
        if entry.category:
            info_parts.append(f"Context: {entry.category}")
        info_label = wx.TextCtrl(panel, value="  |  ".join(info_parts),
                                  style=wx.TE_READONLY | wx.BORDER_NONE)
        info_label.SetBackgroundColour(panel.GetBackgroundColour())
        info_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                   wx.FONTWEIGHT_NORMAL))
        sizer.Add(info_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # --- File / sizes ---
        sizes_str = ", ".join(str(s) for s in sorted(entry.paths.keys()))
        file_info = f"File: {entry.file}"
        if sizes_str:
            file_info += f"  |  Sizes: {sizes_str}"
        file_label = wx.TextCtrl(panel, value=file_info,
                                  style=wx.TE_READONLY | wx.BORDER_NONE)
        file_label.SetBackgroundColour(panel.GetBackgroundColour())
        file_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                   wx.FONTWEIGHT_NORMAL))
        sizer.Add(file_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # --- Duplicate info ---
        if entry.duplicate_of:
            dup_label = wx.TextCtrl(panel, value=f"Duplicate of: {entry.duplicate_of}",
                                    style=wx.TE_READONLY | wx.BORDER_NONE)
            dup_label.SetBackgroundColour(panel.GetBackgroundColour())
            dup_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                      wx.FONTWEIGHT_NORMAL))
            dup_label.SetForegroundColour(wx.Colour(150, 80, 80))
            sizer.Add(dup_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        if entry.duplicates:
            dups_str = ", ".join(str(d) for d in entry.duplicates)
            dups_label = wx.TextCtrl(panel, value=f"Duplicates: {dups_str}",
                                     style=wx.TE_READONLY | wx.BORDER_NONE)
            dups_label.SetBackgroundColour(panel.GetBackgroundColour())
            dups_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                       wx.FONTWEIGHT_NORMAL))
            sizer.Add(dups_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

        # --- Hints ---
        if entry.hints:
            hints_label = wx.TextCtrl(panel,
                                      value=f"Hints: {', '.join(entry.hints)}",
                                      style=wx.TE_READONLY | wx.BORDER_NONE)
            hints_label.SetBackgroundColour(panel.GetBackgroundColour())
            hints_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                        wx.FONTWEIGHT_NORMAL))
            hints_label.SetForegroundColour(wx.Colour(40, 120, 40))
            sizer.Add(hints_label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 5)

        # --- Size previews ---
        if entry.paths:
            size_sizer = wx.BoxSizer(wx.HORIZONTAL)
            for size in sorted(entry.paths.keys()):
                bmp = model.get_bitmap(entry, size)
                if bmp.IsOk():
                    vbox = wx.BoxSizer(wx.VERTICAL)
                    sb = wx.StaticBitmap(panel, bitmap=bmp)
                    vbox.Add(sb, 0, wx.ALIGN_CENTER | wx.ALL, 2)
                    lbl = wx.StaticText(panel, label=str(size))
                    lbl.SetFont(wx.Font(7, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                        wx.FONTWEIGHT_NORMAL))
                    vbox.Add(lbl, 0, wx.ALIGN_CENTER)
                    size_sizer.Add(vbox, 0, wx.RIGHT, 6)
            sizer.Add(size_sizer, 0, wx.ALL, 5)

        # --- File paths ---
        if entry.paths:
            sizer.Add(wx.StaticLine(panel), 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 5)

            paths_hdr = wx.BoxSizer(wx.HORIZONTAL)
            paths_label = wx.StaticText(panel, label="File paths:")
            paths_label.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                        wx.FONTWEIGHT_BOLD))
            paths_hdr.Add(paths_label, 1, wx.ALIGN_CENTER_VERTICAL)

            paths_lines = []
            for size in sorted(entry.paths.keys()):
                paths_lines.append(f"{size}: {entry.paths[size]}")
            paths_text = "\n".join(paths_lines)

            copy_btn = wx.Button(panel, label="Copy", size=(50, 22))
            copy_btn.Bind(wx.EVT_BUTTON,
                          lambda e: self._copy_to_clipboard(paths_text))
            paths_hdr.Add(copy_btn, 0, wx.LEFT, 5)
            sizer.Add(paths_hdr, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)

            n_lines = len(paths_lines)
            paths_ctrl = wx.TextCtrl(
                panel, value=paths_text,
                style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP,
                size=(500, min(20 + n_lines * 16, 120)),
            )
            paths_ctrl.SetFont(wx.Font(8, wx.FONTFAMILY_TELETYPE, wx.FONTSTYLE_NORMAL,
                                       wx.FONTWEIGHT_NORMAL))
            sizer.Add(paths_ctrl, 0, wx.ALL | wx.EXPAND, 5)

        panel.SetSizer(sizer)

        bw = self.BORDER_WIDTH
        border_sizer = wx.BoxSizer(wx.VERTICAL)
        border_sizer.Add(panel, 1, wx.ALL | wx.EXPAND, bw)
        border.SetSizer(border_sizer)

        sizer.Fit(panel)
        border_sizer.Fit(border)

        outer_sizer = wx.BoxSizer(wx.VERTICAL)
        outer_sizer.Add(border, 1, wx.EXPAND)
        self.SetSizerAndFit(outer_sizer)

    def _copy_to_clipboard(self, text):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(text))
            wx.TheClipboard.Close()

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            if hasattr(self._grid_panel, 'unpin'):
                self._grid_panel.unpin()
        else:
            event.Skip()


class CheckListComboPopup(wx.ComboPopup):
    """Popup with a CheckListBox for multi-select dropdown."""

    def __init__(self, labels, theme_ids, available):
        super().__init__()
        self._labels = labels
        self._theme_ids = theme_ids
        self._available = available
        self._checklist = None

    def Create(self, parent):
        self._checklist = wx.CheckListBox(parent, choices=self._labels)
        self._checklist.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT,
                                         wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        for i, pid in enumerate(self._theme_ids):
            if not self._available.get(pid):
                self._checklist.SetItemForegroundColour(i, wx.Colour(180, 120, 120))
        self._checklist.Bind(wx.EVT_CHECKLISTBOX, self._on_check)
        return True

    def GetControl(self):
        return self._checklist

    def GetAdjustedSize(self, minWidth, prefHeight, maxHeight):
        count = self._checklist.GetCount()
        h = min(count * 24 + 6, maxHeight)
        return wx.Size(max(minWidth, 300), h)

    def _on_check(self, event):
        idx = event.GetInt()
        pid = self._theme_ids[idx]
        if not self._available.get(pid):
            self._checklist.Check(idx, False)
            return
        combo = self.GetComboCtrl()
        combo.update_text()
        evt = wx.CommandEvent(wx.wxEVT_TEXT, combo.GetId())
        evt.SetEventObject(combo)
        combo.GetEventHandler().ProcessEvent(evt)

    def is_checked(self, idx):
        return self._checklist.IsChecked(idx)

    def check(self, idx, state):
        self._checklist.Check(idx, state)


class CheckListComboCtrl(wx.ComboCtrl):
    """Dropdown combo that shows a CheckListBox popup for multi-select."""

    def __init__(self, parent, labels, theme_ids, available,
                 theme_labels, **kwargs):
        super().__init__(parent, style=wx.CB_READONLY, **kwargs)
        self._theme_ids = theme_ids
        self._labels = labels
        self._available = available
        self._theme_labels = theme_labels  # {theme_id: display_label}
        self._popup = CheckListComboPopup(labels, theme_ids, available)
        self.SetPopupControl(self._popup)
        self.update_text()

    def check(self, idx, state):
        self._popup.check(idx, state)

    def update_text(self):
        selected = []
        for i, pid in enumerate(self._theme_ids):
            if self._popup.is_checked(i):
                selected.append(self._theme_labels.get(pid, pid.title()))
        self.SetText(", ".join(selected) if selected else "(none)")

    def get_checked_ids(self):
        return {self._theme_ids[i]
                for i in range(len(self._theme_ids))
                if self._popup.is_checked(i)}


class ControlsPanel(wx.Panel):
    """Top control bar with filters."""

    SORT_CHOICES = ["Icon Name", "Status", "Theme Pack"]
    SORT_KEYS = {
        "Theme Pack": lambda e: (e.source, e.name.lower()),
        "Icon Name": lambda e: e.name.lower(),
        "Status": lambda e: (e.status, e.source, e.name.lower()),
    }

    def __init__(self, parent, model, on_filter_changed):
        super().__init__(parent)
        self._model = model
        self._on_filter_changed = on_filter_changed

        def make_col(label_text, ctrl, min_width=0):
            col = wx.BoxSizer(wx.VERTICAL)
            lbl = wx.StaticText(self, label=label_text)
            lbl.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL,
                                wx.FONTWEIGHT_BOLD))
            col.Add(lbl, 0, wx.BOTTOM, 3)
            if min_width:
                ctrl.SetMinSize((min_width, -1))
            col.Add(ctrl, 0, wx.EXPAND)
            return col

        row_sizer = wx.BoxSizer(wx.HORIZONTAL)

        # 1. Search
        self._search = wx.SearchCtrl(self, size=(200, -1))
        self._search.SetDescriptiveText("Search icons...")
        self._search.ShowCancelButton(True)
        row_sizer.Add(make_col("Search", self._search), 0, wx.RIGHT, 12)

        # 2. Display size
        initial_sizes = model.discovered_sizes or [16, 32]
        self._size_values = list(initial_sizes)
        self._size_choice = wx.Choice(self, choices=[str(s) for s in self._size_values])
        self._size_choice.SetSelection(0)
        row_sizer.Add(make_col("Size", self._size_choice), 0, wx.RIGHT, 12)

        # 3. Theme picker (multi-select dropdown)
        project_dir = SCRIPT_DIR.parent
        self._theme_ids = []
        self._theme_available = {}
        self._theme_labels = {}
        popup_labels = []

        for theme_id in model.theme_ids():
            exists = model.theme_available(theme_id)
            self._theme_ids.append(theme_id)
            self._theme_available[theme_id] = exists

            label = model.theme_display_label(theme_id)
            self._theme_labels[theme_id] = label

            theme_dir = model.theme_dir(theme_id)
            try:
                rel_dir = os.path.relpath(theme_dir, str(project_dir))
            except ValueError:
                rel_dir = theme_dir

            if exists:
                popup_labels.append(f"{label}  ({rel_dir})")
            else:
                popup_labels.append(f"{label}  ({rel_dir}) \u2014 not found")

        self._theme_combo = CheckListComboCtrl(
            self, popup_labels, self._theme_ids,
            self._theme_available, self._theme_labels,
            size=(220, -1))
        # Select oxygen and papirus by default
        default_themes = {"nuvola", "oxygen", "papirus"}
        for i, theme_id in enumerate(self._theme_ids):
            if theme_id in default_themes and self._theme_available.get(theme_id):
                self._theme_combo.check(i, True)
        self._theme_combo.update_text()
        row_sizer.Add(make_col("Theme Packs", self._theme_combo), 0, wx.RIGHT, 12)

        # 4. Sort
        self._sort_choice = wx.Choice(self, choices=self.SORT_CHOICES)
        self._sort_choice.SetSelection(0)
        row_sizer.Add(make_col("Sort By", self._sort_choice), 0, wx.RIGHT, 12)

        # 5. Limit
        self._limit_values = [100, 500, 1000, 5000, 10000, 50000, 0]
        self._limit_labels = [str(v) if v else "All" for v in self._limit_values]
        self._limit_choice = wx.Choice(self, choices=self._limit_labels)
        self._limit_choice.SetSelection(self._limit_values.index(1000))
        row_sizer.Add(make_col("Limit", self._limit_choice), 0, wx.RIGHT, 12)

        # 6. Show hinted
        self._cb_hinted = wx.CheckBox(self, label="Hinted")
        self._cb_hinted.SetValue(True)
        row_sizer.Add(make_col("Show", self._cb_hinted), 0, wx.RIGHT, 12)

        # 6. Show unhinted
        self._cb_unhinted = wx.CheckBox(self, label="Unhinted")
        self._cb_unhinted.SetValue(True)
        row_sizer.Add(make_col("", self._cb_unhinted), 0, wx.RIGHT, 12)

        # 7. Show duplicates
        self._cb_duplicates = wx.CheckBox(self, label="Duplicates")
        self._cb_duplicates.SetValue(True)
        row_sizer.Add(make_col("", self._cb_duplicates), 0, wx.RIGHT, 12)

        # 8. Dark background
        self._cb_dark = wx.CheckBox(self, label="Dark BG")
        row_sizer.Add(make_col("", self._cb_dark), 0, wx.RIGHT, 12)

        # 9. Hover popup toggle
        self._cb_hover = wx.CheckBox(self, label="Hover")
        self._cb_hover.SetValue(True)
        row_sizer.Add(make_col("", self._cb_hover), 0, wx.RIGHT, 12)

        # 10. Count
        self._count_label = wx.StaticText(self, label="0 / 0")
        row_sizer.Add(make_col("Showing", self._count_label), 0)

        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(row_sizer, 0, wx.ALL, 8)
        self.SetSizer(outer)

        # Bind events
        self._search_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_search_timer, self._search_timer)
        self._search.Bind(wx.EVT_TEXT, self._on_search_text)
        self._search.Bind(wx.EVT_SEARCHCTRL_CANCEL_BTN, self._on_search_cancel)
        self._size_choice.Bind(wx.EVT_CHOICE, self._on_change)
        self._sort_choice.Bind(wx.EVT_CHOICE, self._on_change)
        self._limit_choice.Bind(wx.EVT_CHOICE, self._on_change)
        self._cb_hinted.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_unhinted.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_duplicates.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_dark.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._cb_hover.Bind(wx.EVT_CHECKBOX, self._on_change)
        self._theme_combo.Bind(wx.EVT_TEXT, self._on_theme_change)

    def _on_search_text(self, event):
        self._search_timer.StartOnce(300)

    def _on_search_cancel(self, event):
        self._search.SetValue("")
        self._on_filter_changed()

    def _on_search_timer(self, event):
        self._on_filter_changed()

    def _on_change(self, event):
        self._on_filter_changed()

    def _on_theme_change(self, event):
        for theme_id in self._theme_combo.get_checked_ids():
            self._model.load_theme(theme_id)
        self.update_size_choices()
        self._on_filter_changed()

    @property
    def search_query(self):
        return self._search.GetValue()

    def update_size_choices(self):
        """Refresh the size dropdown from model's discovered sizes."""
        new_sizes = self._model.discovered_sizes or [16, 32]
        if new_sizes != self._size_values:
            prev = self.display_size
            self._size_values = list(new_sizes)
            self._size_choice.Set([str(s) for s in self._size_values])
            if prev in self._size_values:
                self._size_choice.SetSelection(self._size_values.index(prev))
            else:
                closest = min(self._size_values, key=lambda s: abs(s - prev))
                self._size_choice.SetSelection(self._size_values.index(closest))

    @property
    def display_size(self):
        idx = self._size_choice.GetSelection()
        if idx < 0 or idx >= len(self._size_values):
            return self._size_values[0] if self._size_values else 16
        return self._size_values[idx]

    @property
    def selected_themes(self):
        return self._theme_combo.get_checked_ids()

    @property
    def sort_key(self):
        name = self.SORT_CHOICES[self._sort_choice.GetSelection()]
        return self.SORT_KEYS[name]

    @property
    def display_limit(self):
        """Return selected limit (0 means no limit)."""
        idx = self._limit_choice.GetSelection()
        if idx < 0 or idx >= len(self._limit_values):
            return 1000
        return self._limit_values[idx]

    @property
    def show_hinted(self):
        return self._cb_hinted.IsChecked()

    @property
    def show_unhinted(self):
        return self._cb_unhinted.IsChecked()

    @property
    def show_duplicates(self):
        return self._cb_duplicates.IsChecked()

    @property
    def dark_bg(self):
        return self._cb_dark.IsChecked()

    @property
    def hover_enabled(self):
        return self._cb_hover.IsChecked()

    def set_count(self, visible, filtered, total):
        if visible < filtered:
            self._count_label.SetLabel(f"{visible} / {filtered} / {total}")
        else:
            self._count_label.SetLabel(f"{visible} / {total}")


class IconGridBrowserFrame(wx.Frame):
    """Main window for the Icon Distillery grid browser."""

    def __init__(self):
        super().__init__(None, title="Icon Distillery Browser", size=(1100, 750))

        self._model = IconDataModel()

        # Build UI
        main_sizer = wx.BoxSizer(wx.VERTICAL)

        self._controls = ControlsPanel(self, self._model, self._on_filter_changed)
        main_sizer.Add(self._controls, 0, wx.EXPAND)

        main_sizer.Add(wx.StaticLine(self), 0, wx.EXPAND)

        self._grid = IconGridPanel(self, self._model)
        main_sizer.Add(self._grid, 1, wx.EXPAND)

        self.SetSizer(main_sizer)

        # Frame-level Escape key binding
        escape_id = wx.NewIdRef()
        self.Bind(wx.EVT_MENU, self._on_escape, id=escape_id)
        accel = wx.AcceleratorTable([
            wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, escape_id),
        ])
        self.SetAcceleratorTable(accel)

        # Load themes that are checked by default
        for theme_id in self._controls.selected_themes:
            self._model.load_theme(theme_id)

        # Initial filter
        self._on_filter_changed()

    def _on_escape(self, event):
        self._grid.unpin()

    def _on_filter_changed(self):
        display_size = self._controls.display_size
        sort_key = self._controls.sort_key
        limit = self._controls.display_limit
        entries = self._model.get_filtered(
            query=self._controls.search_query,
            themes=self._controls.selected_themes,
            show_hinted=self._controls.show_hinted,
            show_duplicates=self._controls.show_duplicates,
            show_unhinted=self._controls.show_unhinted,
            min_size=display_size,
            sort_key=sort_key,
        )

        total_filtered = len(entries)
        if limit:
            entries = entries[:limit]

        self._grid.set_display_size(display_size)
        self._grid.set_dark_bg(self._controls.dark_bg)
        self._grid.set_hover_enabled(self._controls.hover_enabled)
        self._grid.set_entries(entries)

        # Count total (all statuses visible)
        all_entries = self._model.get_filtered(
            themes=self._controls.selected_themes,
            show_hinted=True,
            show_duplicates=True,
            show_unhinted=True,
            min_size=display_size,
        )
        self._controls.set_count(len(entries), total_filtered, len(all_entries))


# ============================================================================
# Entry point
# ============================================================================

def main():
    app = wx.App()
    frame = IconGridBrowserFrame()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()
