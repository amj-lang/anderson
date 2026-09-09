import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile} from 'remotion';
import {Close, ColdOpen, Fleet, GateBeat, JackIn, Pipeline, Premise, Ring, STAGES} from './scenes';
import {C} from './theme';

// One place for the cut list, so the composition length and the scenes cannot drift apart.
const S = {
  coldOpen: 120,
  premise: 150,
  pipeline: STAGES.length * 54,
  gates: 120,
  fleet: 330,
  ring: 150,
  jackIn: 105,
  close: 165,
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

const at = (name: keyof typeof S) => CUTS.find((c) => c.name === name)!;

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
      {scene('close', <Close />)}

      {/* Sound: the plugin's own bundled cuts (see plugins/anderson/assets/NOTICE.md). */}
      <Sequence from={2} durationInFrames={60}>
        <Audio src={staticFile('hitech.wav')} volume={0.35} />
      </Sequence>
      <Sequence from={at('gates').from} durationInFrames={30}>
        <Audio src={staticFile('blip.wav')} volume={0.5} />
      </Sequence>
      <Sequence from={at('ring').from + 8} durationInFrames={90}>
        <Audio src={staticFile('phone.wav')} volume={0.55} />
      </Sequence>
      <Sequence from={at('jackIn').from + 14} durationInFrames={30}>
        <Audio src={staticFile('blip.wav')} volume={0.45} />
      </Sequence>
    </AbsoluteFill>
  );
};
