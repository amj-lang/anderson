import React from 'react';
import {AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {Rain} from './Rain';
import {Line, Term} from './Term';
import {C, MONO} from './theme';

const fadeIn = (frame: number, at: number, len = 12) =>
  interpolate(frame, [at, at + len], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

const rise = (frame: number, at: number, len = 14, px = 22) =>
  interpolate(frame, [at, at + len], [px, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

// ─────────────────────────────────────────────────────────────── 1. cold open
export const ColdOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height, fps} = useVideoConfig();
  const rainFade = interpolate(frame, [0, 8, 55, 80], [0, 1, 1, 0.16], {extrapolateRight: 'clamp'});
  const s = spring({frame: frame - 18, fps, config: {damping: 200}});

  return (
    <AbsoluteFill style={{background: C.bg}}>
      <Rain width={width} height={height} opacity={rainFade} speed={1.4} />
      <AbsoluteFill
        style={{
          justifyContent: 'center',
          alignItems: 'center',
          fontFamily: MONO,
          opacity: fadeIn(frame, 14, 16),
          transform: `scale(${interpolate(s, [0, 1], [0.94, 1])})`,
        }}
      >
        <div style={{color: C.green, fontSize: 86, fontWeight: 700, letterSpacing: 14}}>
          ⌐■-■ A N D E R S O N
        </div>
        <div style={{color: C.green, fontSize: 30, marginTop: 30, opacity: fadeIn(frame, 40)}}>
          Loading anderson…
        </div>
        <div style={{color: C.greenDim, fontSize: 26, marginTop: 14, opacity: fadeIn(frame, 52)}}>
          "the agents review the agents"
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 2. premise
const PREMISE: Line[] = [
  {text: '$ /anderson:start ar-2270 "sku images lightbox"', at: 6, color: C.white, cps: 2.2},
  {text: '', at: 40, cps: 0},
  {text: '  one task', at: 46, color: C.green, cps: 0},
  {text: '  four subagents that never grade their own homework', at: 62, color: C.green, cps: 0},
  {text: '  two human gates that halt no matter what', at: 78, color: C.green, cps: 0},
  {text: '', at: 92, cps: 0},
  {text: '  → a reviewed pull request', at: 98, color: C.amber, cps: 0},
];

export const Premise: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: C.bg}}>
      <Rain width={width} height={height} opacity={0.1} speed={0.7} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', padding: 140}}>
        <div style={{width: 1360, transform: `translateY(${rise(frame, 0, 16, 30)}px)`, opacity: fadeIn(frame, 0)}}>
          <Term lines={PREMISE} title="claude code · anderson" fontSize={34} />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 3. the pipeline
type Stage = {
  glyph: string;
  persona: string;
  stage: string;
  spec: string;
  gate?: boolean;
  say: string[];
};

// Personas, models and banner wording lifted from bin/banner.sh and bin/demo.sh.
export const STAGES: Stage[] = [
  {
    glyph: '▲',
    persona: 'THE ARCHITECT',
    stage: 'plan',
    spec: 'opus · high',
    say: [
      '⌐■-■  A N D E R S O N  ·  1/4 · PLAN',
      '      THE ARCHITECT · planner · opus · high',
      '      blast radius, failure paths, a risk scorecard. no code yet.',
    ],
  },
  {
    glyph: '◇',
    persona: 'THE INTERROGATOR',
    stage: 'grill',
    spec: 'you',
    gate: true,
    say: [
      '⌐■-■  A N D E R S O N  ·  GRILL · that one is you',
      '      🔴 architecture · 🟡 behavior · 🟢 preference',
      '      "should the lightbox preload the next image, or fetch on open?"',
    ],
  },
  {
    glyph: '◎',
    persona: 'THE ORACLE',
    stage: 'plan_review',
    spec: 'fable · xhigh',
    say: [
      '⌐■-■  A N D E R S O N  ·  2/4 · PLAN_REVIEW',
      '      THE ORACLE · plan-reviewer · fable · xhigh',
      '      edits plan.md in place. verdict: ship / fix_first / regrill',
    ],
  },
  {
    glyph: '■',
    persona: 'GATE 1',
    stage: 'you',
    spec: 'halts',
    gate: true,
    say: [
      '  ■ GATE 1 · your turn. Read plan.md (## 🔭 Review, verdict=ship).',
      '    Approve: /anderson:approve-plan   (or just say "approved, go")',
      '',
    ],
  },
  {
    glyph: '●',
    persona: 'NEO',
    stage: 'implement',
    spec: 'sonnet · medium',
    say: [
      '⌐■-■  A N D E R S O N  ·  3/4 · IMPLEMENT',
      '      NEO · implementer · sonnet · medium',
      '      touch only what the plan told you to touch.',
    ],
  },
  {
    glyph: '▣',
    persona: 'AGENT SMITH',
    stage: 'diff_review',
    spec: 'fable · high',
    say: [
      '⌐■-■  A N D E R S O N  ·  4/4 · DIFF_REVIEW',
      '      AGENT SMITH · reviewer · fable · high · read-only',
      '      blocks on any unproven acceptance criterion.',
    ],
  },
  {
    glyph: '■',
    persona: 'GATE 2',
    stage: 'you',
    spec: 'halts',
    gate: true,
    say: [
      '  ■ GATE 2 · awaiting you. Read the diff AND the review.',
      '    Ship: /anderson:approve-diff    Rework: /anderson:rework',
      '',
    ],
  },
  {
    glyph: '★',
    persona: 'THE ONE',
    stage: 'ship',
    spec: 'branch · commit · PR',
    say: [
      '⌐■-■  A N D E R S O N  ·  ✓ · SHIP',
      '      THE ONE · welcome to the real world',
      '      branch anderson/ar-2270 · commit · push · pull request',
    ],
  },
];

const PER_STAGE = 54; // frames each stage holds

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
        padding: '14px 10px',
        textAlign: 'center',
        opacity: state === 'next' ? 0.34 : 1,
        transform: `translateY(${active ? -6 : 0}px)`,
        boxShadow: active ? `0 0 40px rgba(62,240,122,0.18)` : 'none',
      }}
    >
      <div style={{color: active ? col : C.greenDim, fontSize: 26}}>{s.glyph}</div>
      <div style={{color: active ? C.white : C.grey, fontSize: 17, fontWeight: 700, marginTop: 6}}>
        {s.persona}
      </div>
      <div style={{color: active ? col : C.greenFaint, fontSize: 15, marginTop: 4}}>{s.stage}</div>
      <div style={{color: C.grey, fontSize: 13, marginTop: 2}}>{s.spec}</div>
    </div>
  );
};

export const Pipeline: React.FC = () => {
  const frame = useCurrentFrame();
  const idx = Math.min(STAGES.length - 1, Math.floor(frame / PER_STAGE));
  const local = frame - idx * PER_STAGE;
  const cur = STAGES[idx];

  const lines: Line[] = cur.say.map((text, i) => ({
    text,
    at: i * 6,
    color: i === 0 ? (cur.gate ? C.amber : C.green) : C.white,
    bold: i === 0,
    dim: i > 1,
    cps: i === 0 ? 0 : 2.6,
  }));

  return (
    <AbsoluteFill
      style={{background: C.bg, fontFamily: MONO, padding: '0 80px', justifyContent: 'center'}}
    >
      <div style={{color: C.greenDim, fontSize: 22, letterSpacing: 6, marginBottom: 8}}>
        THE PIPELINE
      </div>
      <div style={{color: C.white, fontSize: 40, fontWeight: 700, marginBottom: 34}}>
        every stage its own agent, its own model, its own effort
      </div>

      <div style={{display: 'flex', gap: 10, alignItems: 'stretch'}}>
        {STAGES.map((s, i) => (
          <Pill key={s.persona} s={s} state={i < idx ? 'past' : i === idx ? 'now' : 'next'} />
        ))}
      </div>

      <div
        style={{
          marginTop: 46,
          minHeight: 250,
          opacity: interpolate(local, [0, 8], [0, 1], {extrapolateRight: 'clamp'}),
        }}
      >
        <Term
          key={idx}
          lines={lines}
          title={`feature-research/ar-2270/state.md · stage: ${cur.stage}`}
          fontSize={27}
          padding={30}
        />
      </div>

      <div style={{color: C.grey, fontSize: 22, marginTop: 26}}>
        state lives on disk · walk away and resume · the maker never grades its own homework
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
          color: C.amber,
          fontSize: 34,
          letterSpacing: 8,
          opacity: fadeIn(frame, 0),
          transform: `scale(${interpolate(s, [0, 1], [0.9, 1])})`,
        }}
      >
        ■ ■   T W O   G A T E S
      </div>
      <div style={{color: C.white, fontSize: 64, fontWeight: 700, marginTop: 26, opacity: fadeIn(frame, 8)}}>
        Both halt. Even on a ship verdict.
      </div>
      <div style={{color: C.green, fontSize: 38, marginTop: 30, opacity: fadeIn(frame, 30)}}>
        green ≠ understood
      </div>
      <div style={{color: C.grey, fontSize: 26, marginTop: 44, opacity: fadeIn(frame, 46)}}>
        you read the plan · you read the diff · you say ship
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 5. the fleet
type Callout = {at: number; x: number; y: number; w: number; text: string};

// Frame-space coordinates (1920 x 1080). The board sits at left 80 / top 244 at its native
// 1760 x 640, so labels live in the margins above and below it and never cover a cell.
const CALLOUTS: Callout[] = [
  {at: 12, x: 1090, y: 158, w: 750, text: 'your /usage windows: session and week, with bars and time left'},
  {at: 40, x: 80, y: 916, w: 500, text: 'one row per Claude Code session, whatever repo it lives in'},
  {at: 68, x: 640, y: 916, w: 520, text: 'the persona on the job, its stage, and what it is doing this second'},
  {at: 96, x: 1240, y: 916, w: 600, text: 'context per session, red past 80% · ☎︎ ring = it is waiting on you'},
];

export const Fleet: React.FC = () => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 330], [1, 1.03]);

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO}}>
      <div style={{position: 'absolute', top: 56, left: 80, opacity: fadeIn(frame, 0)}}>
        <div style={{color: C.greenDim, fontSize: 22, letterSpacing: 6}}>THE OPERATOR</div>
        <div style={{color: C.white, fontSize: 40, fontWeight: 700, marginTop: 6}}>
          every session on one screen. zero tokens.
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
          opacity: fadeIn(frame, 4, 18),
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
            fontSize: 22,
            lineHeight: 1.35,
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
const ROW = '☎︎  fashion-webapp-2   ar-2270-sku-images-lightbox   ▣ AGENT SMITH   diff_review 1/2';

export const Ring: React.FC = () => {
  const frame = useCurrentFrame();
  const pulse = 0.55 + 0.45 * Math.sin((frame / 30) * Math.PI * 2);
  const notif = spring({frame: frame - 26, fps: 30, config: {damping: 200}});

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{color: C.white, fontSize: 52, fontWeight: 700, opacity: fadeIn(frame, 0)}}>
        it tells you when it needs you
      </div>

      <div
        style={{
          marginTop: 46,
          width: 1620,
          background: C.panel,
          border: `1px solid ${C.amber}`,
          borderRadius: 8,
          padding: '22px 28px',
          color: C.amber,
          fontSize: 25,
          whiteSpace: 'pre',
          opacity: fadeIn(frame, 10),
          boxShadow: `0 0 ${40 * pulse}px rgba(240,192,74,${0.35 * pulse})`,
        }}
      >
        {ROW}
        <span style={{color: C.grey}}>{'   ☎︎ ring 12m'}</span>
      </div>

      <div
        style={{
          marginTop: 40,
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
          <div style={{color: C.grey, fontSize: 21, marginTop: 4}}>
            AGENT SMITH is waiting at GATE 2
          </div>
        </div>
      </div>

      <div style={{color: C.greenDim, fontSize: 24, marginTop: 40, opacity: fadeIn(frame, 60), textAlign: 'center'}}>
        the Matrix phone by default · seven bundled sounds · or drop your own .wav
        <div style={{marginTop: 10, opacity: fadeIn(frame, 78)}}>
          desktop banner too, skipped when that terminal is already in front of you
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 7. jack in
export const JackIn: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const press = spring({frame: frame - 14, fps, config: {damping: 14, stiffness: 220}});

  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO, justifyContent: 'center', alignItems: 'center'}}>
      <div style={{color: C.white, fontSize: 50, fontWeight: 700, opacity: fadeIn(frame, 0)}}>
        one key and you are in that session
      </div>

      <div
        style={{
          marginTop: 50,
          display: 'flex',
          alignItems: 'center',
          gap: 30,
        }}
      >
        <div
          style={{
            width: 150,
            height: 110,
            border: `2px solid ${C.green}`,
            borderRadius: 14,
            color: C.green,
            fontSize: 52,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transform: `translateY(${interpolate(press, [0, 1], [0, 12])}px)`,
            background: press > 0.5 ? 'rgba(62,240,122,0.12)' : 'transparent',
          }}
        >
          ⏎
        </div>
        <div style={{color: C.grey, fontSize: 26, maxWidth: 700, lineHeight: 1.4}}>
          switches the tmux pane, or focuses the iTerm2 / Terminal.app tab that owns it, or brings
          the IDE forward
        </div>
      </div>

      <div
        style={{
          marginTop: 44,
          width: 1420,
          opacity: fadeIn(frame, 40, 10),
          transform: `translateY(${rise(frame, 40, 12, 26)}px)`,
        }}
      >
        <Term
          lines={[
            {text: '  ■ GATE 2 · awaiting you. Read the diff AND the review.', at: 44, color: C.amber, bold: true, cps: 0},
            {text: '    47 passed, 0 failed · +212 −48 · verdict: ship', at: 54, color: C.white, cps: 0},
            {text: '    Ship: /anderson:approve-diff ar-2270', at: 64, color: C.green, cps: 2.4},
          ]}
          title="fashion-webapp-2 · claude code"
          fontSize={28}
        />
      </div>
    </AbsoluteFill>
  );
};

// ─────────────────────────────────────────────────────────────── 8. close
export const Close: React.FC = () => {
  const frame = useCurrentFrame();
  const {width, height} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: C.bg, fontFamily: MONO}}>
      <Rain width={width} height={height} opacity={0.14} speed={0.9} />
      <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', textAlign: 'center'}}>
        <div style={{color: C.green, fontSize: 74, fontWeight: 700, letterSpacing: 10, opacity: fadeIn(frame, 0)}}>
          ⌐■-■ anderson
        </div>
        <div style={{color: C.white, fontSize: 32, marginTop: 26, opacity: fadeIn(frame, 12)}}>
          a Claude Code plugin · four subagents · two human gates
        </div>
        <div style={{color: C.amber, fontSize: 30, marginTop: 40, opacity: fadeIn(frame, 26)}}>
          github.com/amj-lang/anderson
        </div>
        <div style={{color: C.grey, fontSize: 24, marginTop: 18, opacity: fadeIn(frame, 34)}}>
          MIT · /plugin marketplace add amj-lang/anderson
        </div>
        <div style={{color: C.greenDim, fontSize: 24, marginTop: 54, opacity: fadeIn(frame, 46)}}>
          "never send a human to do a machine's job"
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
