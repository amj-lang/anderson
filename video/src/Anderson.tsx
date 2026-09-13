import React from 'react';
import {AbsoluteFill, Audio, interpolate, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {Close, ColdOpen, FILM_H, FILM_W, Fleet, GateBeat, JackIn, Philosophy, Pipeline, Premise, Ring, STAGES} from './scenes';
import {C, MONO} from './theme';

// One place for the cut list, so the composition length and the scenes cannot drift apart.
const S = {
  coldOpen: 90,
  premise: 105,
  pipeline: STAGES.length * 40,
  gates: 90,
  fleet: 240,
  ring: 120,
  jackIn: 90,
  philosophy: 135,
  close: 135,
};

const CUTS = (() => {
  let at = 0;
  const out: {name: keyof typeof S; from: number; dur: number}[] = [];
  for (const name of Object.keys(S) as (keyof typeof S)[]) {
    out.push({name, from: at, dur: S[name]});
    at += S[name];
  }
  return out;
})();

export const TOTAL = CUTS[CUTS.length - 1].from + CUTS[CUTS.length - 1].dur;

/** Where the closing card starts: the feed bands step aside for it, so the sigil is not doubled. */
export const CLOSE_FROM = CUTS[CUTS.length - 1].from;

const at = (name: keyof typeof S) => CUTS.find((c) => c.name === name)!;

/** The film itself, laid out in a fixed FILM_W x FILM_H box. */
export const Anderson: React.FC = () => {
  const scene = (name: keyof typeof S, el: React.ReactNode) => {
    const c = at(name);
    return (
      <Sequence key={name} from={c.from} durationInFrames={c.dur}>
        {el}
      </Sequence>
    );
  };

  return (
    <AbsoluteFill style={{background: C.bg}}>
      {scene('coldOpen', <ColdOpen />)}
      {scene('premise', <Premise />)}
      {scene('pipeline', <Pipeline />)}
      {scene('gates', <GateBeat />)}
      {scene('fleet', <Fleet />)}
      {scene('ring', <Ring />)}
      {scene('jackIn', <JackIn />)}
      {scene('philosophy', <Philosophy />)}
      {scene('close', <Close />)}

      {/* Sound: the plugin's own bundled cuts. wow.wav is jump + rift layered by
          sound/make-wow.sh; licences in plugins/anderson/assets/NOTICE.md. */}
      <Sequence from={0} durationInFrames={90}>
        <Audio src={staticFile('wow.wav')} volume={0.85} />
      </Sequence>
      <Sequence from={at('gates').from - 6} durationInFrames={40}>
        <Audio src={staticFile('blip.wav')} volume={0.5} />
      </Sequence>
      <Sequence from={at('ring').from + 6} durationInFrames={90}>
        <Audio src={staticFile('phone.wav')} volume={0.55} />
      </Sequence>
      <Sequence from={at('jackIn').from + 12} durationInFrames={30}>
        <Audio src={staticFile('blip.wav')} volume={0.45} />
      </Sequence>
      <Sequence from={at('close').from - 10} durationInFrames={90}>
        <Audio src={staticFile('wow.wav')} volume={0.5} />
      </Sequence>
    </AbsoluteFill>
  );
};

/**
 * Feed cut: the same film, scaled to the composition width and centred, with a title band above
 * and a caption band below. Portrait and square posts autoplay bigger in a LinkedIn feed than a
 * 16:9 strip does, and the bands use the height instead of letterboxing it.
 */
export const AndersonFeed: React.FC<{width: number; height: number}> = ({width, height}) => {
  const frame = useCurrentFrame();
  const scale = width / FILM_W;
  const filmH = FILM_H * scale;
  // The closing card carries the sigil and the link itself, so the bands fade out under it.
  const bands = interpolate(frame, [CLOSE_FROM - 12, CLOSE_FROM + 6], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO}}>
      <div
        style={{
          position: 'absolute',
          top: (height - filmH) / 2 - 96,
          width,
          textAlign: 'center',
          color: C.green,
          fontSize: 46,
          fontWeight: 700,
          letterSpacing: 8,
          opacity: bands,
        }}
      >
        ⌐■-■ anderson
      </div>

      <div
        style={{
          position: 'absolute',
          top: (height - filmH) / 2,
          left: 0,
          width: FILM_W,
          height: FILM_H,
          transform: `scale(${scale})`,
          transformOrigin: 'top left',
        }}
      >
        <Anderson />
      </div>

      <div
        style={{
          position: 'absolute',
          top: (height - filmH) / 2 + filmH + 56,
          width,
          textAlign: 'center',
          color: C.grey,
          fontSize: 32,
          lineHeight: 1.5,
          opacity: bands,
        }}
      >
        four agents · two human gates
        <div style={{color: C.amber, marginTop: 12}}>github.com/amj-lang/anderson</div>
      </div>
    </AbsoluteFill>
  );
};
