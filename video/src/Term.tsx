import React from 'react';
import {useCurrentFrame} from 'remotion';
import {C, MONO} from './theme';

export type Line = {
  text: string;
  color?: string;
  bold?: boolean;
  dim?: boolean;
  /** frame (relative to the sequence) this line starts printing */
  at: number;
  /** characters per frame; 0 = appear whole */
  cps?: number;
};

/** A terminal window: title bar, then lines that print themselves. */
export const Term: React.FC<{
  lines: Line[];
  title?: string;
  width?: number | string;
  fontSize?: number;
  padding?: number;
  cursor?: boolean;
}> = ({lines, title = 'anderson', width = '100%', fontSize = 26, padding = 34, cursor = true}) => {
  const frame = useCurrentFrame();
  const visible = lines.filter((l) => frame >= l.at);
  const last = visible[visible.length - 1];

  return (
    <div
      style={{
        width,
        background: C.panel,
        border: `1px solid ${C.greenFaint}`,
        borderRadius: 10,
        boxShadow: '0 30px 90px rgba(0,0,0,0.6)',
        overflow: 'hidden',
        fontFamily: MONO,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '12px 18px',
          borderBottom: `1px solid ${C.greenFaint}`,
          color: C.greenDim,
          fontSize: fontSize * 0.62,
          letterSpacing: 1,
        }}
      >
        <span style={{color: C.green}}>⌐■-■</span>
        <span>{title}</span>
      </div>
      <div style={{padding, fontSize, lineHeight: 1.5, whiteSpace: 'pre'}}>
        {visible.map((l, i) => {
          const cps = l.cps ?? 3;
          const shown = cps === 0 ? l.text : l.text.slice(0, Math.ceil((frame - l.at) * cps));
          const isLast = l === last;
          return (
            <div
              key={i}
              style={{
                color: l.color ?? C.white,
                fontWeight: l.bold ? 700 : 400,
                opacity: l.dim ? 0.55 : 1,
                minHeight: fontSize * 1.5,
              }}
            >
              {shown}
              {cursor && isLast && shown.length < l.text.length ? (
                <span style={{background: C.green, color: C.panel}}>_</span>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
};
