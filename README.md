# MP3 Tag Editor for Nemo and Nautilus

A simple and compact MP3 tag editor for Linux, designed especially for manually adding and editing lyrics.

## Features

- Nemo integration
- Nautilus integration
- Manual lyrics editing (ID3 USLT)
- Common MP3/ID3 tag editing
- Track / total tracks
- Disc / total discs
- Composer, Lyricist, Arranger
- Genre: manual entry or selection from a list
- Album-art preview
- Select any image file for album art
- Remove album art
- MP3 filename editing
- Previous / Next MP3 navigation
- Japanese and English gettext support

## Install

Download the `.deb` package from the GitHub Releases page and install it with:

```bash
sudo apt install ./mp3-tagger_1.0.2-3_all.deb
```

Restart Nemo/Nautilus after installation if necessary.

## Requirements

- Linux
- Python 3
- GTK 3
- PyGObject
- Mutagen
- Nemo or Nautilus

## Source

The repository contains the source components used to build the package. The main Python source and file-manager integrations are provided as gzip+Base64 text archives because the connected GitHub writer accepts UTF-8 text files. See `debian/README.source` for restoration commands.

## License

MIT License

---

🖖 Live long and prosper.
