import React from 'react';
import {random, useCurrentFrame} from 'remotion';
import {C, MONO} from './theme';

// Digital rain, the same "01·" seed alphabet fleet's boot screen uses. Deterministic: every
// column's speed and offset come from remotion's seeded random, so a re-render is identical.
const CHARS = '01·10 1 0';

export const Rain: React.FC<{
  width: number;
  height: number;
  opacity?: number;
  cell?: number;
  speed?: number;
}> = ({width, height, opacity = 1, cell = 22, speed = 1}) => {
  const frame = useCurrentFrame();
  const cols = Math.ceil(width / cell);
  const rows = Math.ceil(height / (cell * 1.15));
  const tail = 14;

  const spans: React.ReactNode[] = [];
  for (let x = 0; x < cols; x++) {
    const v = (0.25 + random(`v${x}`) * 0.9) * speed;
    const off = random(`o${x}`) * rows * 2;
    const head = (frame * v + off) % (rows + tail * 2);
    for (let t = 0; t < tail; t++) {
      const y = Math.floor(head - t);
      if (y < 0 || y > rows) continue;
      // The character changes as the drop falls, but only every 4th frame: a stable flicker.
      const ch = CHARS[Math.floor(random(`c${x}-${y}-${Math.floor(frame / 4)}`) * CHARS.length)];
      if (ch === ' ') continue;
      spans.push(
        <span
          key={`${x}-${t}`}
          style={{
            position: 'absolute',
            left: x * cell,
            top: y * cell * 1.15,
            color: t === 0 ? C.white : C.green,
            opacity: (t === 0 ? 1 : 1 - t / tail) * 0.75,
          }}
        >
          {ch}
        </span>,
      );
    }
  }

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        fontFamily: MONO,
        fontSize: cell,
        lineHeight: 1,
        opacity,
        overflow: 'hidden',
      }}
    >
      {spans}
    </div>
  );
};
