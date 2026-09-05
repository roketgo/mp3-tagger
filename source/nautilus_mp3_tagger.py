#!/usr/bin/env python3
import os, gettext, subprocess, gi
gi.require_version("Nautilus", "4.0")
from gi.repository import GObject, Nautilus
LOCALDIR="/usr/share/mp3-tagger/locale"
try: _=gettext.translation("mp3-tagger", localedir=LOCALDIR, fallback=True).gettext
except Exception: _=gettext.gettext
SCRIPT="/usr/share/mp3-tagger/mp3_tagger.py"
class MP3TaggerExtension(GObject.GObject, Nautilus.MenuProvider):
    def _is_mp3(self,f):
        try: return (f.get_mime_type() or "").lower() == "audio/mpeg" or f.get_uri().lower().endswith(".mp3")
        except Exception: return False
    def get_file_items(self,*args):
        files=args[-1] if args else []
        if not files or len(files)!=1 or not self._is_mp3(files[0]): return []
        item=Nautilus.MenuItem(name="MP3TaggerExtension::edit", label=_("🎵 MP3タグを編集…"), tip=_("MP3のタグ、歌詞、アルバムアートを編集します"))
        path=files[0].get_location().get_path(); item.connect("activate",self._activate,path); return [item]
    def _activate(self,_item,path):
        env=os.environ.copy(); env["MP3_TAGGER_FILE_MANAGER"]="nautilus"
        subprocess.Popen(["/usr/bin/python3",SCRIPT,path],env=env,start_new_session=True)
    def get_background_items(self,*args): return []
