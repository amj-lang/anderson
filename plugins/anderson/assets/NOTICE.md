# Bundled sounds (`assets/sounds/`)

All cuts: mono 22.05 kHz 16-bit, ≤2.5 s, peak-normalized, 10 ms fade-in, short fade-out. Pick one with `s`
in fleet or `--ring NAME`; drop your own `.wav` in `~/.claude/fleet/sounds/` to add to the list.

## phone.wav (default)

The phone: exactly one ring. 2.43 s cut (0.97 s → 3.40 s, boundaries found by energy scan, 10 ms
fade-in, 100 ms fade-out, peak-normalized, mono 22.05 kHz) from **"Full Matrix.wav"** by **skycarl**,
Freesound sound #210499
(https://freesound.org/people/skycarl/sounds/210499/), published 2013-12-12 under
**Creative Commons 0** (public domain dedication, https://creativecommons.org/publicdomain/zero/1.0/).
Also mirrored on Pixabay as "Full Matrix" (technology-full-matrix-75029).

skycarl describes it as a compilation of: JM_FX_Matrix Sound 02 (Julien Matthey), scroll_matrix.wav
(Melissapons), Telephone ring (xyzr_kx). The cut used here is the telephone ring section.

## The others (Pixabay, downloaded 2026-09-09)

| file | source | license | cut |
|---|---|---|---|
| `snare.wav` | "The Matrix Snare" by mrstokes302, Pixabay #531245 | Pixabay Content License | 0.72–2.00 s (the hit) |
| `hitech.wav` | "SFX Hi-Tech User Interface Sound Effects" by fronbondi_skegs, Pixabay #335625 | Pixabay Content License | 0.70–2.33 s (the three blips) |
| `freeze.wav` | "Freeze 4 Audio 9" (freesound_community mirror), Pixabay #103366 | CC0 | 2.55–3.70 s (the impact) |
| `blip.wav` | "Blip8bit 02" by alex_jauk, Pixabay #293062 | Pixabay Content License | whole (0.16 s) |
| `rift.wav` | "Reality Distortion Rift 8bit" by alex_jauk, Pixabay #293073 | Pixabay Content License | 0–1.25 s |
| `jump.wav` | "Matrix jump sound fx slower" (freesound_community mirror), Pixabay #77329 | CC0 | 0–2.40 s, faded |

Pixabay Content License (https://pixabay.com/service/license-summary/): free to use and modify,
including inside a distributed product, no attribution required (given anyway). Not for resale as
standalone stock files.

Played by `bin/fleet.py` when a session starts waiting on you (`m` toggles, `s` cycles). Your own
`~/.claude/fleet/ring.wav` overrides whatever is picked.
