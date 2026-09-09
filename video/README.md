# anderson promo video (Remotion)

A ~52 s film of the anderson loop and the fleet terminal. Built with [Remotion](https://www.remotion.dev):
React components rendered frame by frame, so every number, banner and key legend on screen is text
in source, not a hand-drawn mock.

```
cd video
npm install
npm run studio     # live editor at localhost:3000, scrub and edit
npm run render     # -> out/anderson.mp4  (1920x1080, 30fps, with sound)
npm run still      # -> out/frame.png     (one frame, for a thumbnail)
```

`npx remotion still Anderson out/f320.png --frame=320` renders any single frame, which is the cheap
way to check a scene without waiting for a full render.

## The cut list

Scene lengths live in one object at the top of `src/Anderson.tsx` (`S`), and the composition's
duration is derived from it, so a scene cannot silently run past the end of the film.

| # | scene | what it says |
|---|-------|--------------|
| 1 | `ColdOpen` | digital rain resolving into the sigil, the same boot screen `fleet` prints |
| 2 | `Premise` | one task, four subagents, two human gates |
| 3 | `Pipeline` | all eight stages, lighting up one at a time, with the real banner text |
| 4 | `GateBeat` | both gates halt, even on a ship verdict — green ≠ understood |
| 5 | `Fleet` | the real `fleet` screenshot with callouts on usage, persona, context, ring |
| 6 | `Ring` | a ringing row plus the desktop banner, over the actual ring sound |
| 7 | `JackIn` | ⏎ moves you into that session, which lands at GATE 2 |
| 8 | `Close` | repo, licence, install line |

## Sources of truth

Nothing in the film is invented copy:

- Stage personas, models and effort come from `plugins/anderson/bin/banner.sh`.
- The banner and gate wording comes from `plugins/anderson/bin/demo.sh` (`/anderson:demo`).
- `public/fleet-operator.png` and `public/fleet-loading.png` are copies of the repo's own stills,
  recorded from the running program by `assets/*.tape` (VHS). Remotion only serves files under
  `public/`, so after re-recording a still, refresh the copy from the repo root:
  `cp assets/fleet-operator.png assets/fleet-loading.png video/public/`
- `public/*.wav` are copies of the plugin's bundled ring sounds — licences and attribution in
  `plugins/anderson/assets/NOTICE.md`.

When the plugin's wording changes, update `STAGES` in `src/scenes.tsx` and re-render; a stale film is
worse than no film.

## Other aspect ratios

The composition is 1920x1080. For a square or vertical cut, add another `<Composition>` in
`src/Root.tsx` with the same `component` and different `width`/`height` — the scenes are laid out with
flex and absolute frame-space coordinates, so the Fleet scene's callouts are the one place that needs
its numbers revisited.
