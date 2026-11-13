#!/usr/bin/env python3
"""Majora's Mask 3D Heart Piece Tracker — GTK4 / libadwaita front end."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mm3d_save as mm  # noqa: E402

APP_ID = "io.github.mm3d_heart_tracker"
STATE_FILE = Path(GLib.get_user_config_dir()) / "mm3d-heart-tracker" / "state.json"

CSS = """
.hero-count { font-size: 42px; font-weight: 800; font-feature-settings: "tnum"; }
.hero-total { font-size: 20px; font-weight: 600; opacity: .55; }
.piece-icon { border-radius: 999px; min-width: 30px; min-height: 30px; }
.piece-icon.got { background: alpha(@success_color, .18); color: @success_color; }
.piece-icon.maybe { background: alpha(@warning_color, .18); color: @warning_color; }
.piece-icon.missing { background: alpha(@window_fg_color, .07); color: alpha(@window_fg_color, .35); }
row.got-row .title { opacity: .6; }
.region-chip { border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600;
               background: alpha(@window_fg_color, .07); }
.region-chip.done { background: alpha(@success_color, .18); color: @success_color; }
progressbar.hearts trough, progressbar.hearts progress { min-height: 10px; border-radius: 99px; }
progressbar.hearts progress { background: #e5484d; }
"""


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state))
    except OSError:
        pass


class HeartMeter(Gtk.DrawingArea):
    """In-game style heart row: full hearts plus a quarter-filled one in progress."""

    SIZE = 22
    GAP = 4
    PER_ROW = 10

    def __init__(self):
        super().__init__()
        self.full = 0
        self.quarters = 0
        self.set_draw_func(self._draw)

    def set_hearts(self, full: int, quarters: int):
        self.full, self.quarters = full, quarters
        n = full + (1 if quarters else 0)
        rows = max(1, math.ceil(n / self.PER_ROW))
        cols = min(max(n, 1), self.PER_ROW)
        self.set_content_width(cols * (self.SIZE + self.GAP))
        self.set_content_height(rows * (self.SIZE + self.GAP))
        self.queue_draw()

    @staticmethod
    def _heart_path(cr, x, y, s):
        cr.move_to(x + s / 2, y + s * 0.92)
        cr.curve_to(x - s * 0.05, y + s * 0.5, x + s * 0.02, y + s * 0.02, x + s * 0.27, y + s * 0.06)
        cr.curve_to(x + s * 0.4, y + s * 0.08, x + s * 0.48, y + s * 0.18, x + s / 2, y + s * 0.26)
        cr.curve_to(x + s * 0.52, y + s * 0.18, x + s * 0.6, y + s * 0.08, x + s * 0.73, y + s * 0.06)
        cr.curve_to(x + s * 0.98, y + s * 0.02, x + s * 1.05, y + s * 0.5, x + s / 2, y + s * 0.92)
        cr.close_path()

    def _draw(self, _area, cr, _w, _h):
        s, g = self.SIZE, self.GAP
        items = [1.0] * self.full + ([self.quarters / 4] if self.quarters else [])
        for i, fill in enumerate(items):
            x = (i % self.PER_ROW) * (s + g) + 1
            y = (i // self.PER_ROW) * (s + g) + 1
            # empty background
            self._heart_path(cr, x, y, s - 2)
            cr.set_source_rgba(0.9, 0.28, 0.3, 0.18)
            cr.fill()
            if fill:
                cr.save()
                self._heart_path(cr, x, y, s - 2)
                cr.clip()
                # quarter pieces fill as pie slices like the game
                cr.move_to(x + s / 2, y + s / 2)
                cr.arc(x + s / 2 - 1, y + s / 2, s, -math.pi / 2, -math.pi / 2 + 2 * math.pi * fill)
                cr.close_path()
                cr.set_source_rgb(0.9, 0.28, 0.3)
                cr.fill()
                cr.restore()
            self._heart_path(cr, x, y, s - 2)
            cr.set_source_rgba(0.55, 0.1, 0.12, 0.9)
            cr.set_line_width(1.2)
            cr.stroke()


class TrackerWindow(Adw.ApplicationWindow):
    def __init__(self, app, initial: Path | None):
        super().__init__(application=app, title="Heart Piece Tracker")
        self.set_default_size(560, 860)
        self.state = load_state()
        self.slots: list[Path] = []
        self.current: Path | None = None
        self.monitor: Gio.FileMonitor | None = None
        self._reload_id = 0
        self.filter_mode = self.state.get("filter", "all")

        self.toasts = Adw.ToastOverlay()
        view = Adw.ToolbarView()
        self.toasts.set_child(view)
        self.set_content(self.toasts)

        header = Adw.HeaderBar()
        open_btn = Gtk.Button(icon_name="document-open-symbolic", tooltip_text="Open save file (Ctrl+O)")
        open_btn.connect("clicked", lambda *_: self.choose_file())
        header.pack_start(open_btn)
        self.reload_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Reload (Ctrl+R)")
        self.reload_btn.connect("clicked", lambda *_: self.reload())
        self.reload_btn.set_sensitive(False)
        header.pack_start(self.reload_btn)

        self.title = Adw.WindowTitle(title="Heart Piece Tracker", subtitle="Majora's Mask 3D")
        header.set_title_widget(self.title)
        view.add_top_bar(header)

        # slot + filter bar
        bar = Gtk.Box(spacing=8, margin_start=12, margin_end=12, margin_top=6, margin_bottom=6)
        self.slot_group = Adw.ToggleGroup(hexpand=True)
        self.slot_group.add_css_class("round")
        self.slot_group.connect("notify::active-name", self._on_slot_toggled)
        bar.append(self.slot_group)
        self.filter_group = Adw.ToggleGroup()
        for name, label, icon in (("all", "All", None), ("missing", "Missing", None)):
            self.filter_group.add(Adw.Toggle(name=name, label=label))
        self.filter_group.set_active_name(self.filter_mode)
        self.filter_group.connect("notify::active-name", self._on_filter_toggled)
        bar.append(self.filter_group)
        self.topbar = bar
        bar.set_visible(False)
        view.add_top_bar(bar)

        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        view.set_content(self.stack)

        empty = Adw.StatusPage(
            icon_name="document-open-symbolic",
            title="Open your save",
            description="Pick a Majora's Mask 3D slot file (save0.bin, save1.bin or save2.bin)\n"
                        "from Checkpoint/JKSM or a 3DS emulator, or drop it on this window.",
        )
        btn = Gtk.Button(label="Open Save File…", halign=Gtk.Align.CENTER)
        btn.add_css_class("pill")
        btn.add_css_class("suggested-action")
        btn.connect("clicked", lambda *_: self.choose_file())
        empty.set_child(btn)
        self.stack.add_named(empty, "empty")

        self.scroller = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.stack.add_named(self.scroller, "tracker")

        drop = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop.connect("drop", self._on_drop)
        self.add_controller(drop)

        for accel, cb in (("<Control>o", self.choose_file), ("<Control>r", self.reload)):
            sc = Gtk.Shortcut(trigger=Gtk.ShortcutTrigger.parse_string(accel),
                              action=Gtk.CallbackAction.new(lambda *_a, f=cb: (f(), True)[1]))
            ctl = Gtk.ShortcutController()
            ctl.add_shortcut(sc)
            self.add_controller(ctl)

        start = initial
        if start is None and self.state.get("last") and Path(self.state["last"]).is_file():
            start = Path(self.state["last"])
        if start is None:
            found = mm.discover_saves()
            start = found[0] if found else None
        if start:
            self.open_path(start)

    # ---- file handling ------------------------------------------------------
    def choose_file(self):
        dlg = Gtk.FileDialog(title="Open Majora's Mask 3D save")
        f = Gtk.FileFilter(name="MM3D save slots")
        f.add_pattern("*.bin")
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(f)
        dlg.set_filters(filters)
        if self.current:
            dlg.set_initial_folder(Gio.File.new_for_path(str(self.current.parent)))
        dlg.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, dlg, res):
        try:
            gfile = dlg.open_finish(res)
        except GLib.Error:
            return
        if gfile and gfile.get_path():
            self.open_path(Path(gfile.get_path()))

    def _on_drop(self, _target, value, _x, _y):
        files = value.get_files()
        if files and files[0].get_path():
            self.open_path(Path(files[0].get_path()))
            return True
        return False

    def open_path(self, path: Path):
        try:
            mm.read_slot(path)
        except (OSError, mm.SaveError) as e:
            self.toasts.add_toast(Adw.Toast(title=str(e), timeout=6))
            return
        self.slots = mm.find_slot_siblings(path)
        if path not in self.slots:
            self.slots = [path]
        self._rebuild_slot_toggles()
        self.current = path  # so the toggle handler below doesn't load it a second time
        self.slot_group.set_active_name(str(path))
        self.show_slot(path)

    def _rebuild_slot_toggles(self):
        self.slot_group.remove_all()
        for p in self.slots:
            try:
                r = mm.read_slot(p)
                label = f"{r.player_name}"
            except (OSError, mm.SaveError):
                label = p.stem
            idx = p.stem[-1] if p.stem[-1].isdigit() else "?"
            num = int(idx) + 1 if idx.isdigit() else idx
            t = Adw.Toggle(name=str(p), label=f"{num} · {label}", tooltip=str(p))
            self.slot_group.add(t)
        self.slot_group.set_visible(len(self.slots) > 1)

    def _on_slot_toggled(self, group, _pspec):
        name = group.get_active_name()
        if name and (self.current is None or name != str(self.current)):
            self.show_slot(Path(name))

    def _on_filter_toggled(self, group, _pspec):
        self.filter_mode = group.get_active_name() or "all"
        self.state["filter"] = self.filter_mode
        save_state(self.state)
        self.reload(quiet=True)

    def show_slot(self, path: Path):
        self.current = path
        self.state["last"] = str(path)
        save_state(self.state)
        self._watch(path)
        self.reload(quiet=True)

    def _watch(self, path: Path):
        if self.monitor:
            self.monitor.cancel()
        self.monitor = Gio.File.new_for_path(str(path)).monitor_file(Gio.FileMonitorFlags.NONE, None)
        self.monitor.connect("changed", self._on_file_changed)

    def _on_file_changed(self, *_):
        if self._reload_id:
            GLib.source_remove(self._reload_id)
        self._reload_id = GLib.timeout_add(400, self._delayed_reload)

    def _delayed_reload(self):
        self._reload_id = 0
        self.reload(quiet=False, auto=True)
        return GLib.SOURCE_REMOVE

    def reload(self, quiet: bool = False, auto: bool = False):
        if not self.current:
            return
        scroll = self.scroller.get_vadjustment().get_value() if auto else 0.0
        try:
            result = mm.read_slot(self.current)
        except (OSError, mm.SaveError) as e:
            self.toasts.add_toast(Adw.Toast(title=f"Couldn't read save: {e}", timeout=6))
            return
        viewport = Gtk.Viewport(scroll_to_focus=False, child=self._build_tracker(result))
        self.scroller.set_child(viewport)

        def restore():
            self.scroller.get_vadjustment().set_value(scroll)
            return GLib.SOURCE_REMOVE
        GLib.idle_add(restore)
        self.stack.set_visible_child_name("tracker")
        self.topbar.set_visible(True)
        self.reload_btn.set_sensitive(True)
        self.title.set_subtitle(f"{result.player_name} — {self.current.name}")
        if not quiet:
            self.toasts.add_toast(Adw.Toast(title="Save changed — updated" if auto else "Reloaded", timeout=2))

    # ---- UI -------------------------------------------------------------------
    def _build_tracker(self, r: mm.SlotResult) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                       margin_top=18, margin_bottom=30, margin_start=12, margin_end=12)
        clamp = Adw.Clamp(maximum_size=640, child=page)

        page.append(self._build_summary(r))

        if not r.crc_ok:
            page.append(self._banner("dialog-warning-symbolic",
                                     "This save's checksum doesn't match. It may be damaged or edited, "
                                     "so the results could be wrong."))
        if r.unexplained > 0:
            page.append(self._banner("dialog-question-symbolic",
                                     f"Your hearts show {r.unexplained} more piece(s) than the save's flags "
                                     "account for. One of the pieces marked missing may already be yours."))

        any_rows = False
        for region in mm.REGIONS:
            pieces = [p for p in mm.PIECES if p.region == region]
            got = sum(1 for p in pieces if p.id in r.collected)
            shown = [p for p in pieces if self.filter_mode == "all" or p.id not in r.collected]
            if not shown:
                continue
            any_rows = True
            group = Adw.PreferencesGroup(title=GLib.markup_escape_text(region))
            chip = Gtk.Label(label=f"{got} / {len(pieces)}", valign=Gtk.Align.CENTER)
            chip.add_css_class("region-chip")
            if got == len(pieces):
                chip.add_css_class("done")
            group.set_header_suffix(chip)
            for p in shown:
                group.add(self._piece_row(p, r.collected.get(p.id)))
            page.append(group)

        if not any_rows:
            done = Adw.StatusPage(icon_name="starred-symbolic", title="All 52 collected!",
                                  description="Every Piece of Heart in Termina is yours.")
            page.append(done)
        return clamp

    def _build_summary(self, r: mm.SlotResult) -> Gtk.Widget:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        card.add_css_class("card")
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                        margin_top=16, margin_bottom=16, margin_start=18, margin_end=18)
        card.append(inner)

        top = Gtk.Box(spacing=12)
        nums = Gtk.Box(spacing=4, valign=Gtk.Align.END)
        count = Gtk.Label(label=str(r.collected_count))
        count.add_css_class("hero-count")
        total = Gtk.Label(label=f"/ {mm.TOTAL_PIECES}", valign=Gtk.Align.BASELINE)
        total.add_css_class("hero-total")
        nums.append(count)
        nums.append(total)
        top.append(nums)
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, valign=Gtk.Align.CENTER, hexpand=True)
        t = Gtk.Label(label="Pieces of Heart", xalign=0)
        t.add_css_class("heading")
        missing = mm.TOTAL_PIECES - r.collected_count
        sub = Gtk.Label(label=f"{missing} still to find" if missing else "Complete!", xalign=0)
        sub.add_css_class("dim-label")
        side.append(t)
        side.append(sub)
        top.append(side)
        inner.append(top)

        bar = Gtk.ProgressBar(fraction=r.collected_count / mm.TOTAL_PIECES)
        bar.add_css_class("hearts")
        inner.append(bar)

        hearts = HeartMeter()
        hearts.set_hearts(r.heart_containers, r.pieces_in_progress)
        inner.append(hearts)

        boss = ", ".join(r.boss_containers) if r.boss_containers else "none yet"
        info = Gtk.Label(
            label=f"{r.heart_containers} hearts · {r.pieces_in_progress}/4 toward the next · "
                  f"boss containers: {boss}",
            xalign=0, wrap=True)
        info.add_css_class("caption")
        info.add_css_class("dim-label")
        inner.append(info)
        return card

    @staticmethod
    def _banner(icon: str, text: str) -> Gtk.Widget:
        box = Gtk.Box(spacing=10)
        box.add_css_class("card")
        img = Gtk.Image(icon_name=icon, margin_start=14, valign=Gtk.Align.CENTER)
        lbl = Gtk.Label(label=text, wrap=True, xalign=0, hexpand=True,
                        margin_top=10, margin_bottom=10, margin_end=14)
        box.append(img)
        box.append(lbl)
        return box

    @staticmethod
    def _piece_row(p: mm.Piece, status: str | None) -> Gtk.Widget:
        row = Adw.ActionRow(title=GLib.markup_escape_text(p.name),
                            subtitle=GLib.markup_escape_text(p.hint))
        row.set_subtitle_lines(2)
        icon_name, cls, tip = {
            "yes": ("object-select-symbolic", "got", "Collected"),
            "inferred": ("dialog-question-symbolic", "maybe",
                         "Probably collected. MM3D clears this flag on each new cycle, so it's "
                         "worked out from your heart total."),
            None: ("radio-symbolic", "missing", "Not collected yet"),
        }[status]
        img = Gtk.Image(icon_name=icon_name, valign=Gtk.Align.CENTER, tooltip_text=tip)
        img.add_css_class("piece-icon")
        img.add_css_class(cls)
        row.add_prefix(img)
        if status == "yes":
            row.add_css_class("got-row")
        if status == "inferred":
            tag = Gtk.Label(label="Inferred", valign=Gtk.Align.CENTER, tooltip_text=tip)
            tag.add_css_class("caption")
            tag.add_css_class("warning")
            row.add_suffix(tag)
        return row


class TrackerApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN | Gio.ApplicationFlags.NON_UNIQUE)

    def do_startup(self):
        Adw.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_string(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), provider,
                                                  Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def do_activate(self):
        TrackerWindow(self, None).present()

    def do_open(self, files, _n, _hint):
        path = Path(files[0].get_path()) if files and files[0].get_path() else None
        TrackerWindow(self, path).present()


def main():
    return TrackerApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
