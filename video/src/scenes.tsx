import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Rain} from './Rain';
import {Line, Term} from './Term';
import {C, MONO} from './theme';

// The film is laid out in a fixed 1920x1080 box. Other compositions (portrait, square) scale that
// box and add their own bands around it, so no scene has to reflow.
export const FILM_W = 1920;
export const FILM_H = 1080;

const fadeIn = (frame: number, at: number, len = 12) =>
  interpolate(frame, [at, at + len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

const rise = (frame: number, at: number, len = 14, px = 22) =>
  interpolate(frame, [at, at + len], [px, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

// ─────────────────────────────────────────────────────────────── 1. cold open
export const ColdOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const rainFade = interpolate(frame, [0, 8, 40, 62], [0, 1, 1, 0.16], {extrapolateRight: 'clamp'});
  const s = spring({frame: frame - 24, fps, config: {damping: 200}});

  return (
    <AbsoluteFill style={{background: C.bg}}>
      <Rain width={FILM_W} height={FILM_H} opacity={rainFade} speed={1.4} />
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily: MONO,
          opacity: fadeIn(frame, 22, 10),
          transform: `scale(${interpolate(s, [0, 1], [0.9, 1])})`,
        }}
      >
        <div style={{color: C.green, fontSize: 92, fontWeight: 700, letterSpacing: 14}}>
          ⌐■-■ A N D E R S O N
        </div>
        <div style={{color: C.greenDim, fontSize: 30, marginTop: 28, opacity: fadeIn(frame, 42)}}>
          the agents review the agents
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 2. premise
const PREMISE: Line[] = [
  {text: '$ /anderson:start ar-2270 "sku images lightbox"', at: 4, color: C.white, cps: 2.6},
  {text: '', at: 34, cps: 0},
  {text: '  four agents.', at: 40, color: C.green, cps: 0},
  {text: '  two human gates.', at: 54, color: C.green, cps: 0},
  {text: '  one pull request.', at: 68, color: C.amber, cps: 0},
];

export const Premise: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.bg}}>
      <Rain width={FILM_W} height={FILM_H} opacity={0.1} speed={0.7} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center'}}>
        <div style={{width: 1300, transform: `translateY(${rise(frame, 0, 16, 30)}px)`, opacity: fadeIn(frame, 0)}}>
          <Term lines={PREMISE} title="claude code · anderson" fontSize={38} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 3. the pipeline
type Stage = {glyph: string; persona: string; stage: string; spec: string; gate?: boolean; say: string};

// Personas, models and effort come from bin/banner.sh. One line each: the film is not the docs.
export const STAGES: Stage[] = [
  {glyph: '▲', persona: 'THE ARCHITECT', stage: 'plan', spec: 'opus · high', say: 'plans it. no code yet.'},
  {glyph: '◇', persona: 'THE INTERROGATOR', stage: 'grill', spec: 'you', gate: true, say: 'grills you on the plan.'},
  {glyph: '◎', persona: 'THE ORACLE', stage: 'plan_review', spec: 'fable · xhigh', say: 'tears the plan apart.'},
  {glyph: '■', persona: 'GATE 1', stage: 'you', spec: 'halts', gate: true, say: 'you approve, or nothing moves.'},
  {glyph: '●', persona: 'NEO', stage: 'implement', spec: 'sonnet · medium', say: 'writes the code.'},
  {glyph: '▣', persona: 'AGENT SMITH', stage: 'diff_review', spec: 'fable · high', say: 'reviews the diff. read-only.'},
  {glyph: '■', persona: 'GATE 2', stage: 'you', spec: 'halts', gate: true, say: 'you read it. you say ship.'},
  {glyph: '★', persona: 'THE ONE', stage: 'ship', spec: 'PR', say: 'branch, commit, pull request.'},
];

const PER_STAGE = 40;

const Pill: React.FC<{s: Stage; state: 'past' | 'now' | 'next'}> = ({s, state}) => {
  const active = state === 'now';
  const col = s.gate ? C.amber : C.green;
  return (
    <div
      style={{
        flex: '1 1 0',
        border: `1px solid ${active ? col : C.greenFaint}`,
        background: active ? 'rgba(62,240,122,0.08)' : 'transparent',
        borderRadius: 8,
        padding: '16px 10px',
        textAlign: 'center',
        opacity: state === 'next' ? 0.3 : 1,
        transform: `translateY(${active ? -6 : 0}px)`,
        boxShadow: active ? '0 0 40px rgba(62,240,122,0.18)' : 'none',
      }}
    >
      <div style={{color: active ? col : C.greenDim, fontSize: 28}}>{s.glyph}</div>
      <div style={{color: active ? C.white : C.grey, fontSize: 18, fontWeight: 700, marginTop: 8}}>
        {s.persona}
      </div>
      <div style={{color: active ? col : C.greenFaint, fontSize: 15, marginTop: 4}}>{s.spec}</div>
    </div>
  );
};

export const Pipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const idx = Math.min(STAGES.length - 1, Math.floor(frame / PER_STAGE));
  const local = frame - idx * PER_STAGE;
  const cur = STAGES[idx];
  const col = cur.gate ? C.amber : C.green;

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO, padding: '0 80px', justifyContent: 'center'}}>
      <div style={{color: C.white, fontSize: 46, fontWeight: 700, marginBottom: 44, opacity: fadeIn(frame, 0)}}>
        one task, four agents, nobody grades their own homework
      </div>

      <div style={{display: 'flex', gap: 10, alignItems: 'stretch'}}>
        {STAGES.map((s, i) => (
          <Pill key={s.persona} s={s} state={i < idx ? 'past' : i === idx ? 'now' : 'next'} />
        ))}
      </div>

      <div
        style={{
          marginTop: 64,
          minHeight: 120,
          opacity: interpolate(local, [0, 7], [0, 1], {extrapolateRight: 'clamp'}),
          transform: `translateY(${rise(local, 0, 8, 14)}px)`,
        }}
      >
        <div style={{color: col, fontSize: 30, letterSpacing: 4}}>{cur.stage.toUpperCase()}</div>
        <div style={{color: C.white, fontSize: 52, fontWeight: 700, marginTop: 12}}>{cur.say}</div>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 4. the gates
export const GateBeat: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame, fps, config: {damping: 200}});
  return (
    <AbsoluteFill
      style={{
        background: C.bg,
        fontFamily: MONO,
        justifyContent: 'center',
        alignItems: 'center',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          color: C.white,
          fontSize: 70,
          fontWeight: 700,
          opacity: fadeIn(frame, 0),
          transform: `scale(${interpolate(s, [0, 1], [0.92, 1])})`,
        }}
      >
        Both gates halt.
      </div>
      <div style={{color: C.amber, fontSize: 44, marginTop: 34, opacity: fadeIn(frame, 20)}}>
        green ≠ understood
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 5. the fleet
type Callout = {at: number; x: number; y: number; w: number; text: string};

// Frame-space coordinates. The board sits at left 80 / top 244 at its native 1760 x 640, so labels
// live in the margins and never cover a cell. Three of them, short: the board says the rest.
const CALLOUTS: Callout[] = [
  {at: 24, x: 80, y: 916, w: 520, text: 'one row per session, any repo'},
  {at: 60, x: 700, y: 916, w: 460, text: '☎ = waiting on you'},
  {at: 96, x: 1260, y: 916, w: 580, text: 'context, red past 80%'},
];

export const Fleet: React.FC = () => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 240], [1, 1.03]);

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO}}>
      <div style={{position: 'absolute', top: 80, left: 80, opacity: fadeIn(frame, 0)}}>
        <div style={{color: C.white, fontSize: 46, fontWeight: 700}}>
          every session on one screen
        </div>
      </div>

      <Img
        src={staticFile('fleet-operator.png')}
        style={{
          position: 'absolute',
          left: 80,
          top: 244,
          width: 1760,
          height: 640,
          borderRadius: 10,
          border: `1px solid ${C.greenFaint}`,
          boxShadow: '0 40px 120px rgba(0,0,0,0.7)',
          opacity: fadeIn(frame, 4, 16),
          transform: `scale(${zoom})`,
        }}
      />

      {CALLOUTS.map((c) => (
        <div
          key={c.text}
          style={{
            position: 'absolute',
            left: c.x,
            top: c.y,
            width: c.w,
            opacity: fadeIn(frame, c.at, 10),
            transform: `translateY(${rise(frame, c.at, 10, 12)}px)`,
            color: C.amber,
            fontSize: 28,
            borderLeft: `3px solid ${C.amber}`,
            paddingLeft: 14,
          }}
        >
          {c.text}
        </div>
      ))}
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 6. it rings
const ROW = '☎  fashion-webapp-2   ar-2270-sku-images-lightbox   ▣ AGENT SMITH   diff_review 1/2';

export const Ring: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const pulse = 0.55 + 0.45 * Math.sin((frame / 30) * Math.PI * 2);
  const notif = spring({frame: frame - 24, fps, config: {damping: 200}});

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{color: C.white, fontSize: 60, fontWeight: 700, opacity: fadeIn(frame, 0)}}>
        it rings when it needs you
      </div>

      <div
        style={{
          marginTop: 52,
          width: 1620,
          background: C.panel,
          border: `1px solid ${C.amber}`,
          borderRadius: 8,
          padding: '24px 28px',
          color: C.amber,
          fontSize: 25,
          whiteSpace: 'pre',
          opacity: fadeIn(frame, 8),
          boxShadow: `0 0 ${40 * pulse}px rgba(240,192,74,${0.35 * pulse})`,
        }}
      >
        {ROW}
        <span style={{color: C.grey}}>{'   ☎ ring 12m'}</span>
      </div>

      <div
        style={{
          marginTop: 46,
          display: 'flex',
          gap: 18,
          alignItems: 'center',
          background: '#1b1f1c',
          border: `1px solid ${C.greenFaint}`,
          borderRadius: 14,
          padding: '20px 26px',
          width: 780,
          transform: `translateX(${interpolate(notif, [0, 1], [420, 0])}px)`,
          opacity: notif,
        }}
      >
        <div style={{color: C.green, fontSize: 32}}>⌐■-■</div>
        <div>
          <div style={{color: C.white, fontSize: 24, fontWeight: 700}}>fleet · fashion-webapp-2</div>
          <div style={{color: C.grey, fontSize: 21, marginTop: 4}}>AGENT SMITH is waiting at GATE 2</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 7. jack in
export const JackIn: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const press = spring({frame: frame - 12, fps, config: {damping: 14, stiffness: 220}});

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{color: C.white, fontSize: 60, fontWeight: 700, opacity: fadeIn(frame, 0)}}>
        one key and you are there
      </div>

      <div
        style={{
          marginTop: 54,
          width: 170,
          height: 120,
          border: `2px solid ${C.green}`,
          borderRadius: 16,
          color: C.green,
          fontSize: 58,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          transform: `translateY(${interpolate(press, [0, 1], [0, 12])}px)`,
          background: press > 0.5 ? 'rgba(62,240,122,0.12)' : 'transparent',
        }}
      >
        ⏎
      </div>

      <div
        style={{
          marginTop: 54,
          width: 1320,
          opacity: fadeIn(frame, 34, 10),
          transform: `translateY(${rise(frame, 34, 12, 26)}px)`,
        }}
      >
        <Term
          lines={[
            {text: '  ■ GATE 2 · awaiting you. +212 −48 · verdict: ship', at: 38, color: C.amber, bold: true, cps: 0},
            {text: '    Ship: /anderson:approve-diff ar-2270', at: 50, color: C.green, cps: 2.6},
          ]}
          title="fashion-webapp-2 · claude code"
          fontSize={30}
        />
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 8. close
export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO}}>
      <Rain width={FILM_W} height={FILM_H} opacity={0.14} speed={0.9} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
        <div style={{color: C.green, fontSize: 80, fontWeight: 700, letterSpacing: 10, opacity: fadeIn(frame, 0)}}>
          ⌐■-■ anderson
        </div>
        <div style={{color: C.amber, fontSize: 34, marginTop: 40, opacity: fadeIn(frame, 16)}}>
          github.com/amj-lang/anderson
        </div>
        <div style={{color: C.grey, fontSize: 26, marginTop: 20, opacity: fadeIn(frame, 30)}}>
          a Claude Code plugin · MIT
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
