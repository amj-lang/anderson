# anderson promo video (Remotion)

A ~44 s film of the anderson loop and the fleet terminal. Built with [Remotion](https://www.remotion.dev):
React components rendered frame by frame, so every number, banner and key legend on screen is text
in source, not a hand-drawn mock.

```
cd video
npm install
npm run studio      # live editor at localhost:3000, scrub and edit
npm run render      # -> out/anderson.mp4           1920x1080, the film
npm run portrait    # -> out/anderson-portrait.mp4  1080x1350, feed cut
npm run square      # -> out/anderson-square.mp4    1080x1080, feed cut
npm run still       # -> out/frame.png              one frame, for a thumbnail
```

`npx remotion still Anderson out/f320.png --frame=320` renders any single frame, which is the cheap
way to check a scene without waiting for a full render.

`public/` holds copies of the stills and sounds, because Remotion only serves files from there.

The repo README's two explainer stills come from this film, so the copy can never drift from it:

```
npx remotion still Anderson ../assets/premise.png   --frame=180   # scene 2, Premise
npx remotion still Anderson ../assets/philosophy.png --frame=1155  # scene 8, Philosophy
cd ../assets && sips -c 560 1920 premise.png --out premise.png    # trim the dead space (frames move when `S` changes)
                sips -c 560 1920 philosophy.png --out philosophy.png
```

## The cut list

Scene lengths live in one object at the top of `src/Anderson.tsx` (`S`), and the composition's
duration is derived from it, so a scene cannot silently run past the end of the film.

| # | scene | what it says |
|---|-------|--------------|
| 1 | `ColdOpen` | digital rain resolving into the sigil, over the one big hit |
| 2 | `Premise` | four agents. two human gates. one pull request. |
| 3 | `Pipeline` | all eight stages, lighting up one at a time, one line each |
| 4 | `GateBeat` | both gates halt — green ≠ understood |
| 5 | `Fleet` | the real `fleet` board, with three short callouts |
| 6 | `Ring` | a ringing row plus the desktop banner, over the actual ring sound |
| 7 | `JackIn` | ⏎ and you are in that session, which is parked at GATE 2 |
| 8 | `Philosophy` | read less code, judge more intent: the job that is left, and where it happens |
| 9 | `Close` | repo, licence |

One idea per scene, on purpose: the readme is where the detail lives, and a feed video that has to be
paused to be read does not get watched.

## The three compositions

`Anderson` is the film, laid out in a fixed 1920x1080 box (`FILM_W` / `FILM_H` in `src/scenes.tsx`).
`AndersonFeed` scales that same box to the composition width and puts a title band above and a
caption band below it, which is what `AndersonPortrait` (4:5) and `AndersonSquare` (1:1) render.
Feed shapes get more autoplay height in a LinkedIn feed than a 16:9 strip, and the bands use that
height instead of letterboxing it. Because the film is a fixed box, no scene has to reflow.

## Sound

`sound/make-wow.sh` builds `public/wow.wav`: `jump.wav` pitched down for weight as the swell, then
`rift.wav` landing on top of it as the impact, with a short echo tail, loudness-matched and limited.
Both sources are the plugin's own bundled cuts, so the licences in
`plugins/anderson/assets/NOTICE.md` still cover the result.

```
bash video/sound/make-wow.sh     # from the repo root, after changing either source cut
```

It lands twice: on the cold open and on the closing card. The ring beat uses `phone.wav` (the actual
default ring), and `blip.wav` marks the two cuts in between.

## Sources of truth

Nothing in the film is invented copy:

- Stage personas, models and effort come from `plugins/anderson/bin/banner.sh`.
- The gate wording comes from `plugins/anderson/bin/demo.sh` (`/anderson:demo`).
- `public/fleet-operator.png` and `public/fleet-loading.png` are copies of the repo's own stills,
  recorded from the running program by `assets/*.tape` (VHS). After re-recording a still, refresh
  the copy from the repo root:
  `cp assets/fleet-operator.png assets/fleet-loading.png video/public/`
- `public/*.wav` are copies of the plugin's bundled ring sounds — licences and attribution in
  `plugins/anderson/assets/NOTICE.md`.

When the plugin's wording changes, update `STAGES` in `src/scenes.tsx` and re-render; a stale film is
worse than no film.
