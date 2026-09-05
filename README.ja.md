# MP3 tag editor for Nemo and Nautilus

NemoとNautilusから直接起動できる、シンプルでコンパクトなMP3タグエディタです。

特に、**MP3ファイルへ歌詞を手動で追加・編集すること**を主な目的としています。

## 主な機能

- Nemo対応
- Nautilus対応
- 歌詞の手動入力・編集（ID3 USLT）
- MP3/ID3の基本タグ編集
- トラック番号 / 総トラック数
- ディスク番号 / 総ディスク数
- 作曲者
- 作詞家
- 編曲
- ジャンル：手動入力または選択
- アルバムアート表示
- 任意の画像ファイルからアルバムアートを設定
- アルバムアート削除
- MP3ファイル名変更
- 前のMP3 / 次のMP3への移動
- gettextによる日本語・英語対応

## インストール

GitHub Releasesから `.deb` パッケージをダウンロードして、次のコマンドでインストールしてください。

```bash
sudo apt install ./mp3-tagger_1.0.2-3_all.deb
```

インストール後、必要に応じてNemo/Nautilusを再起動してください。

## 必要環境

- Linux
- Python 3
- GTK 3
- PyGObject
- Mutagen
- Nemo または Nautilus

## ライセンス

MIT License

---

🖖 長寿と繁栄を。
