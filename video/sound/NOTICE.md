# Video sound sources (`video/sound/src/`, `video/public/`)

The film's sound is built from two kinds of source: the plugin's own bundled ring cuts (licences in
[`plugins/anderson/assets/NOTICE.md`](../../plugins/anderson/assets/NOTICE.md)) and the two music
tracks archived here.

## Built here

| file | built by | from |
|---|---|---|
| `public/wow.wav` | `sound/make-wow.sh` | `jump.wav` + `rift.wav` (the plugin's bundled cuts) |
| `public/bed.wav` | `sound/make-bed.sh` | `src/penny-candy.mp3` + `src/computer-loop.mp3` |

Both scripts are re-runnable from the repo root and overwrite their output, so the film's sound can
be rebuilt from source at any time.

## Archived sources

| file | source |
|---|---|
| `src/penny-candy.mp3` | "Penny Candy" by **fuzzydrawing**, Pixabay #427332 |
| `src/computer-loop.mp3` | "Programming a computer loop" by **kuzu420**, Pixabay #323395 |

Both downloaded from [Pixabay](https://pixabay.com) on 2026-09-09 under the
[Pixabay Content License](https://pixabay.com/service/license-summary/): free to use and modify,
including inside a distributed product, no attribution required (given anyway). Not for resale as
standalone stock files.
