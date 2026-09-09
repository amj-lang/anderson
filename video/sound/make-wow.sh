#!/usr/bin/env bash
# make-wow.sh — build the film's one big hit out of two of the plugin's own bundled cuts:
# jump.wav (the whoosh) pitched down for weight, then rift.wav landing on top of it as the impact,
# with a short echo tail. Nothing else is added, so the licences in
# plugins/anderson/assets/NOTICE.md still cover it.
#
#   bash video/sound/make-wow.sh        # -> video/public/wow.wav  (48 kHz stereo, ~3 s)
#
# Run from the repo root. Re-run after changing either source cut.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
src="$root/plugins/anderson/assets/sounds"
out="$root/video/public/wow.wav"

ffmpeg -y -v error \
  -i "$src/jump.wav" -i "$src/rift.wav" \
  -filter_complex "\
    [0:a]asetrate=18500,aresample=48000,aformat=channel_layouts=stereo,\
         afade=t=in:st=0:d=0.06,volume=1.15[swell];\
    [1:a]aresample=48000,aformat=channel_layouts=stereo,volume=1.5,\
         adelay=1000|1000,aecho=0.7:0.55:230|470:0.32|0.18[hit];\
    [swell][hit]amix=inputs=2:duration=longest:normalize=0,\
    loudnorm=I=-13:TP=-1.0:LRA=9,volume=3dB,alimiter=limit=0.95,\
    afade=t=out:st=2.75:d=0.45,atrim=0:3.2[mix]" \
  -map "[mix]" -ar 48000 -ac 2 -c:a pcm_s16le "$out"

ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$out" \
  | xargs printf 'wrote %s (%.2fs)\n' "$out"
