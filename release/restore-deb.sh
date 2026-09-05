#!/bin/bash
set -e
cd "$(dirname "$0")"
cat mp3-tagger_1.0.2-3_all.deb.part-*.b64 | base64 -d > mp3-tagger_1.0.2-3_all.deb
chmod 644 mp3-tagger_1.0.2-3_all.deb
echo "Created: $(pwd)/mp3-tagger_1.0.2-3_all.deb"
