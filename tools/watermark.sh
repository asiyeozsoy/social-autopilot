#!/usr/bin/env bash
# Kullanım: watermark.sh <factyeap|tinynotes> <logo_klasoru> <video_klasoru> <cikis_klasoru>
set -euo pipefail
BRAND=$1; WM=$2; IN=$3; OUT=$4; mkdir -p "$OUT"
case $BRAND in
  factyeap)  LOGO="$WM/factyeap_wm_white.png";   WF=0.30; OP=0.65 ;;
  tinynotes) LOGO="$WM/tinynotes_wm_maroon.png"; WF=0.20; OP=0.75 ;;
  *) echo "marka: factyeap veya tinynotes"; exit 1 ;;
esac
shopt -s nullglob nocaseglob
for v in "$IN"/*.{mp4,mov,webm}; do
  name=$(basename "${v%.*}")
  ffmpeg -nostdin -loglevel error -y -i "$v" -i "$LOGO" -filter_complex \
   "[1:v][0:v]scale2ref=w=iw*${WF}:h=ow/mdar[lg][base];[lg]format=rgba,colorchannelmixer=aa=${OP}[lg2];[base][lg2]overlay=x=(W-w)/2:y=H*0.80-h/2" \
   -c:v libx264 -preset veryfast -crf 18 -pix_fmt yuv420p -c:a copy -movflags +faststart "$OUT/${name}_logo.mp4"
  echo "✓ $name"
done
