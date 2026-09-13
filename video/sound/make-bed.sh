#!/usr/bin/env bash
# make-bed.sh — the film's background bed, from the two tracks in sound/src/:
#   penny-candy.mp3   the music, looped and pushed well down
#   computer-loop.mp3 a machine-room texture under it (the raw file is ~-54 dB, so it needs +26 dB
#                     before it is audible at all)
# Both loop past the film's length and are trimmed to it, with a fade in and a long fade out, and
# the mix is loudness-matched low enough that the wow hits and the ring still cut through.
#
#   bash video/sound/make-bed.sh          # -> video/public/bed.wav   (48 kHz stereo, 40 s)
#   BED_SECONDS=60 bash video/sound/make-bed.sh
#
# Run from the repo root. Licences and attribution: video/sound/NOTICE.md.
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
src="$root/video/sound/src"
out="$root/video/public/bed.wav"
secs="${BED_SECONDS:-40}"

ffmpeg -y -v error \
  -stream_loop -1 -t "$secs" -i "$src/penny-candy.mp3" \
  -stream_loop -1 -t "$secs" -i "$src/computer-loop.mp3" \
  -filter_complex "\
    [0:a]aresample=48000,volume=-13dB[music];\
    [1:a]aresample=48000,volume=26dB,highpass=f=180,volume=-8dB[texture];\
    [music][texture]amix=inputs=2:duration=shortest:normalize=0,\
    loudnorm=I=-22:TP=-4:LRA=9,\
    afade=t=in:st=0:d=1.2,afade=t=out:st=$((secs - 3)):d=3[bed]" \
  -map "[bed]" -ar 48000 -ac 2 -c:a pcm_s16le "$out"

ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$out" \
  | xargs printf 'wrote %s (%.2fs)\n' "$out"
