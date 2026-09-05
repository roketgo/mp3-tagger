#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MP3 tag editor for Nemo and Nautilus."""
import os, sys, re, shutil, tempfile, gettext, traceback, subprocess, mimetypes
from pathlib import Path

LOCALDIR = "/usr/share/mp3-tagger/locale"
if not os.path.isdir(LOCALDIR):
    LOCALDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locale")
try:
    _ = gettext.translation("mp3-tagger", localedir=LOCALDIR, fallback=True).gettext
except Exception:
    _ = gettext.gettext

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, GdkPixbuf
from mutagen.id3 import ID3, ID3NoHeaderError, TIT2, TPE1, TALB, TPE2, TCON, TDRC, TRCK, TPOS, TCOM, TEXT, TPE4, COMM, USLT, APIC

VERSION = "1.0.2"
PREVIEW = 120
AUDIO_EXTS = {".mp3"}

TAG_FIELDS = [
    ("title", _("タイトル"), TIT2),
    ("artist", _("アーティスト"), TPE1),
    ("album", _("アルバム"), TALB),
    ("albumartist", _("アルバムアーティスト"), TPE2),
    ("genre", _("ジャンル"), TCON),
    ("date", _("年 / 日付"), TDRC),
    ("track", _("トラック番号"), TRCK),
    ("disc", _("ディスク番号"), TPOS),
    ("composer", _("作曲者"), TCOM),
    ("lyricist", _("作詞家"), TEXT),
    ("arranger", _("編曲"), TPE4),
]

def msg(parent, kind, text, detail=None):
    d = Gtk.MessageDialog(transient_for=parent, flags=0, message_type=kind, buttons=Gtk.ButtonsType.OK, text=text)
    if detail: d.format_secondary_text(str(detail)[-2500:])
    d.run(); d.destroy()

def error(parent, text, detail=None): msg(parent, Gtk.MessageType.ERROR, text, detail)

def confirm(parent, text):
    d = Gtk.MessageDialog(transient_for=parent, flags=0, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO, text=text)
    r = d.run(); d.destroy(); return r == Gtk.ResponseType.YES

def tag_text(frame):
    if frame is None: return ""
    try: return str(frame.text[0]) if frame.text else ""
    except Exception: return ""

def get_lyrics(tags):
    frames = tags.getall("USLT")
    if not frames: return ""
    # Prefer an existing Japanese/English/default lyrics frame, otherwise first.
    for f in frames:
        if getattr(f, "lang", "") in ("jpn", "eng", "und"):
            return f.text or ""
    return frames[0].text or ""

def get_comment(tags):
    frames = tags.getall("COMM")
    if not frames: return ""
    for f in frames:
        if getattr(f, "lang", "") == "eng" or getattr(f, "desc", "") == "":
            return f.text[0] if f.text else ""
    return frames[0].text[0] if frames[0].text else ""

def natural_key(name):
    return [int(x) if x.isdigit() else x.casefold() for x in re.split(r'(\d+)', name)]

def sibling_mp3s(path):
    folder = os.path.dirname(os.path.abspath(path)) or "."
    try:
        entries = [e.path for e in os.scandir(folder) if e.is_file() and os.path.splitext(e.name)[1].lower() in AUDIO_EXTS]
        entries.sort(key=lambda p: natural_key(os.path.basename(p)))
        return entries or [os.path.abspath(path)]
    except Exception:
        return [os.path.abspath(path)]

def image_pixbuf(path, size=PREVIEW):
    return GdkPixbuf.Pixbuf.new_from_file_at_scale(path, size, size, True)

class MP3TaggerWindow(Gtk.Window):
    def __init__(self, path, manager="nemo"):
        super().__init__(title=_("MP3タグエディタ {version}").format(version=VERSION))
        self.set_default_size(460, 620)
        self.set_border_width(8)
        self.set_resizable(True)
        self.path = os.path.abspath(path)
        self.manager = manager
        self.files = sibling_mp3s(self.path)
        self.index = self.files.index(self.path) if self.path in self.files else 0
        self.path = self.files[self.index]
        self.cover_data = None
        self.cover_mime = "image/jpeg"
        self.remove_cover = False
        self.busy = False
        self.tmp_files = []
        self.connect("destroy", self.on_destroy)
        self.build_ui()
        self.load_file()

    def build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5); self.add(root)
        self.file_label = Gtk.Label(xalign=0); root.pack_start(self.file_label, False, False, 0)
        name_box = Gtk.Box(spacing=5); root.pack_start(name_box, False, False, 0)
        name_box.pack_start(Gtk.Label(label=_("ファイル名:"), xalign=0), False, False, 0)
        self.name_entry = Gtk.Entry(hexpand=True); name_box.pack_start(self.name_entry, True, True, 0)

        grid = Gtk.Grid(column_spacing=6, row_spacing=3); root.pack_start(grid, False, False, 0)
        self.entries = {}
        self.track_num = Gtk.Entry(width_chars=5)
        self.track_total = Gtk.Entry(width_chars=5)
        self.disc_num = Gtk.Entry(width_chars=5)
        self.disc_total = Gtk.Entry(width_chars=5)
        genres = ["Blues", "Classical", "Country", "Electronic", "Folk", "Hip-Hop", "Jazz", "Pop", "R&B", "Reggae", "Rock", "Soundtrack", "Other"]
        self.genre_combo = Gtk.ComboBoxText.new_with_entry()
        for genre in genres:
            self.genre_combo.append_text(genre)
        row = 0
        for key, label, _cls in TAG_FIELDS:
            if key == "track":
                grid.attach(Gtk.Label(label=_("トラック"), xalign=0), 0, row, 1, 1)
                box = Gtk.Box(spacing=3)
                box.pack_start(self.track_num, False, False, 0)
                box.pack_start(Gtk.Label(label="/"), False, False, 0)
                box.pack_start(self.track_total, False, False, 0)
                box.pack_start(Gtk.Label(label=_("ディスク")), False, False, 6)
                box.pack_start(self.disc_num, False, False, 0)
                box.pack_start(Gtk.Label(label="/"), False, False, 0)
                box.pack_start(self.disc_total, False, False, 0)
                grid.attach(box, 1, row, 1, 1)
            elif key == "disc":
                continue
            elif key == "genre":
                self.entries[key] = self.genre_combo.get_child()
                grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1); grid.attach(self.genre_combo, 1, row, 1, 1)
            else:
                e = Gtk.Entry(hexpand=True); self.entries[key] = e
                grid.attach(Gtk.Label(label=label, xalign=0), 0, row, 1, 1); grid.attach(e, 1, row, 1, 1)
            row += 1
        # Comment is compact single-line field.
        self.comment_entry = Gtk.Entry(hexpand=True)
        grid.attach(Gtk.Label(label=_("コメント"), xalign=0), 0, row, 1, 1); grid.attach(self.comment_entry, 1, row, 1, 1)

        root.pack_start(Gtk.Separator(), False, False, 2)
        art_box = Gtk.Box(spacing=7); root.pack_start(art_box, False, False, 0)
        frame = Gtk.Frame(); self.cover_image = Gtk.Image(); self.cover_image.set_size_request(PREVIEW, PREVIEW); frame.add(self.cover_image); art_box.pack_start(frame, False, False, 0)
        art_controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3); art_box.pack_start(art_controls, True, True, 0)
        self.cover_btn = Gtk.Button(label=_("画像ファイルを選択…")); self.cover_btn.connect("clicked", self.choose_cover); art_controls.pack_start(self.cover_btn, False, False, 0)
        self.clear_cover_btn = Gtk.Button(label=_("アルバムアートを削除")); self.clear_cover_btn.connect("clicked", self.clear_cover); art_controls.pack_start(self.clear_cover_btn, False, False, 0)
        self.cover_status = Gtk.Label(xalign=0); self.cover_status.set_line_wrap(True); art_controls.pack_start(self.cover_status, False, False, 0)

        root.pack_start(Gtk.Label(label=_("歌詞"), xalign=0), False, False, 0)
        sw = Gtk.ScrolledWindow(); sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC); sw.set_min_content_height(105); root.pack_start(sw, True, True, 0)
        self.lyrics_view = Gtk.TextView(); self.lyrics_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); self.lyrics_view.set_left_margin(4); self.lyrics_view.set_right_margin(4); sw.add(self.lyrics_view)

        bottom = Gtk.Box(spacing=5); root.pack_start(bottom, False, False, 2)
        self.status = Gtk.Label(xalign=0); bottom.pack_start(self.status, True, True, 0)
        self.prev = Gtk.Button(label="◀"); self.prev.connect("clicked", lambda *_: self.navigate(-1)); bottom.pack_start(self.prev, False, False, 0)
        self.next = Gtk.Button(label="▶"); self.next.connect("clicked", lambda *_: self.navigate(1)); bottom.pack_start(self.next, False, False, 0)
        self.apply = Gtk.Button(label=_("適用")); self.apply.get_style_context().add_class("suggested-action"); self.apply.connect("clicked", self.apply_tags); bottom.pack_start(self.apply, False, False, 0)
        self.close_btn = Gtk.Button(label=_("終了")); self.close_btn.connect("clicked", lambda *_: self.close()); bottom.pack_start(self.close_btn, False, False, 0)
        self.show_all()

    def load_file(self):
        try:
            tags = ID3(self.path)
        except ID3NoHeaderError:
            tags = ID3()
        except Exception as e:
            error(self, _("MP3タグの読み込みに失敗しました。"), e); return
        self.tags = tags
        self.file_label.set_markup("<b>%s</b>" % GLib.markup_escape_text(os.path.basename(self.path)))
        self.name_entry.set_text(os.path.basename(self.path))
        mapping = {"title":"TIT2","artist":"TPE1","album":"TALB","albumartist":"TPE2","genre":"TCON","date":"TDRC","track":"TRCK","disc":"TPOS","composer":"TCOM","lyricist":"TEXT","arranger":"TPE4"}
        for key, _label, _cls in TAG_FIELDS:
            if key in ("track", "disc"):
                continue
            self.entries[key].set_text(tag_text(tags.get(mapping[key])))
        track = tag_text(tags.get("TRCK"))
        track_parts = track.split("/", 1)
        self.track_num.set_text(track_parts[0])
        self.track_total.set_text(track_parts[1] if len(track_parts) > 1 else "")
        disc = tag_text(tags.get("TPOS"))
        disc_parts = disc.split("/", 1)
        self.disc_num.set_text(disc_parts[0])
        self.disc_total.set_text(disc_parts[1] if len(disc_parts) > 1 else "")
        self.comment_entry.set_text(get_comment(tags))
        buf = self.lyrics_view.get_buffer(); buf.set_text(get_lyrics(tags))
        self.cover_data = None; self.remove_cover = False
        apics = tags.getall("APIC")
        if apics:
            apic = apics[0]; self.cover_data = bytes(apic.data); self.cover_mime = apic.mime or "image/jpeg"
            try:
                loader = GdkPixbuf.PixbufLoader(); loader.write(self.cover_data); loader.close(); self.cover_image.set_from_pixbuf(loader.get_pixbuf().scale_simple(PREVIEW, PREVIEW, GdkPixbuf.InterpType.BILINEAR)); self.cover_status.set_text(_("アルバムアートあり"))
            except Exception: self.cover_status.set_text(_("アルバムアートあり（プレビュー不可）"))
        else:
            self.cover_image.clear(); self.cover_status.set_text(_("アルバムアートなし"))
        self.prev.set_sensitive(self.index > 0); self.next.set_sensitive(self.index < len(self.files)-1)

    def choose_cover(self, _button):
        d = Gtk.FileChooserDialog(title=_("アルバムアート画像を選択"), parent=self, action=Gtk.FileChooserAction.OPEN, buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        f = Gtk.FileFilter(); f.set_name(_("画像ファイル")); f.add_pixbuf_formats(); d.add_filter(f)
        if d.run() == Gtk.ResponseType.ACCEPT:
            p = d.get_filename()
            try:
                pix = image_pixbuf(p); self.cover_image.set_from_pixbuf(pix); self.cover_data = Path(p).read_bytes(); self.cover_mime = mimetypes.guess_type(p)[0] or "image/jpeg"; self.remove_cover = False; self.cover_status.set_text(_("新しい画像を設定"))
            except Exception as e: error(self, _("画像を読み込めませんでした。"), e)
        d.destroy()

    def clear_cover(self, _button):
        if confirm(self, _("アルバムアートを削除しますか？")):
            self.cover_data = None; self.remove_cover = True; self.cover_image.clear(); self.cover_status.set_text(_("アルバムアートを削除します"))

    def navigate(self, delta):
        if self.busy: return
        ni = self.index + delta
        if 0 <= ni < len(self.files): self.index = ni; self.path = self.files[ni]; self.load_file()

    def apply_tags(self, _button):
        if self.busy: return
        newname = self.name_entry.get_text().strip(); oldname = os.path.basename(self.path)
        if not newname or newname in (".", "..") or "/" in newname or "\\" in newname:
            return error(self, _("ファイル名が正しくありません。"))
        if Path(newname).suffix.lower() != ".mp3" or Path(oldname).suffix.lower() != ".mp3":
            return error(self, _("MP3の拡張子は変更できません。"))
        newpath = os.path.join(os.path.dirname(self.path), newname)
        if os.path.abspath(newpath) != self.path and os.path.exists(newpath): return error(self, _("同じ名前のファイルが既に存在します。"))
        self.busy = True; self.apply.set_sensitive(False); self.status.set_text(_("保存しています…"))
        buf = self.lyrics_view.get_buffer(); lyrics = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        values = {k:e.get_text().strip() for k,e in self.entries.items()}
        track_num = self.track_num.get_text().strip(); track_total = self.track_total.get_text().strip()
        values["track"] = track_num + (("/" + track_total) if track_total else "")
        disc_num = self.disc_num.get_text().strip(); disc_total = self.disc_total.get_text().strip()
        values["disc"] = disc_num + (("/" + disc_total) if disc_total else "")
        comment = self.comment_entry.get_text().strip()
        try:
            orig_stat = os.stat(self.path)
            tags = ID3(self.path)
        except ID3NoHeaderError:
            orig_stat = os.stat(self.path)
            tags = ID3()
        mapping = {"title":"TIT2","artist":"TPE1","album":"TALB","albumartist":"TPE2","genre":"TCON","date":"TDRC","track":"TRCK","disc":"TPOS","composer":"TCOM","lyricist":"TEXT","arranger":"TPE4"}
        for key, frameid in mapping.items():
            tags.delall(frameid)
            if values[key]: tags.add(globals()[frameid](encoding=3, text=[values[key]]))
        tags.delall("COMM")
        if comment: tags.add(COMM(encoding=3, lang="eng", desc="", text=[comment]))
        tags.delall("USLT")
        if lyrics: tags.add(USLT(encoding=3, lang="eng", desc="", text=lyrics))
        tags.delall("APIC")
        if self.cover_data and not self.remove_cover:
            tags.add(APIC(encoding=3, mime=self.cover_mime, type=3, desc="", data=self.cover_data))
        try:
            tags.save(self.path, v2_version=3)
            orig_stat = os.stat(self.path)
            if os.path.abspath(newpath) != self.path:
                os.replace(self.path, newpath); self.path = newpath
                os.utime(self.path, (orig_stat.st_atime, orig_stat.st_mtime))
            else:
                os.utime(self.path, (orig_stat.st_atime, orig_stat.st_mtime))
            self.files = sibling_mp3s(self.path); self.index = self.files.index(self.path) if self.path in self.files else 0
            self.busy = False; self.apply.set_sensitive(True); self.status.set_text(_("適用完了")); self.load_file()
        except Exception as e:
            self.busy = False; self.apply.set_sensitive(True); self.status.set_text(""); error(self, _("保存に失敗しました。"), e)

    def on_destroy(self, *_):
        for p in self.tmp_files:
            try: os.remove(p)
            except Exception: pass
        Gtk.main_quit()

def main():
    paths = sys.argv[1:]
    if not paths:
        paths = [p for p in os.environ.get("NEMO_SCRIPT_SELECTED_FILE_PATHS", "").splitlines() if p]
    if not paths or os.path.splitext(paths[0])[1].lower() != ".mp3":
        error(None, _("MP3ファイルを指定してください。"), _("NemoまたはNautilusでMP3ファイルを右クリックして実行してください。")); return 1
    manager = os.environ.get("MP3_TAGGER_FILE_MANAGER", "nemo")
    win = MP3TaggerWindow(paths[0], manager); win.connect("delete-event", lambda *_: False); Gtk.main(); return 0

if __name__ == "__main__":
    try: sys.exit(main())
    except Exception: traceback.print_exc(); sys.exit(1)
