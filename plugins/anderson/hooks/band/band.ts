// Pure logic for the anderson crew band: no `$`, so the test can drive it directly.
import type { Pipe, Seat } from '../../types/band'

export type Seg = [text: string, color: string]
export type Line = Seg[]

export const STAGES = ['plan', 'grill', 'plan_review', 'implement', 'repair', 'diff_review', 'ship']
export const STALL_MS = 120_000
const SPIN = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

// Colors: hex or theme keys; 'dim' and 'bold' are handled by the renderer.
export const C = { green: '#3cff7a', cyan: '#5fe3ff', yellow: 'warning', red: 'error', blue: '#8fb7ff', grey: '#9aa59f', dim: 'dim', bold: 'bold' }

// Persona per agent; model/effort come from agents/<name>.md frontmatter, not from here.
// Same names as bin/fleet.py PERSONA and bin/crew.py PERSONA (test/test_band_personas.py keeps them in step).
export const PERSONA: Record<string, string> = {
  planner: 'THE ARCHITECT',
  'plan-reviewer': 'THE ORACLE',
  implementer: 'NEO',
  'test-fixer': 'TRINITY',
  reviewer: 'AGENT SMITH',
  prototyper: 'THE CONSTRUCT',
}

/** The agent file a subagent type runs from (`anderson:reviewer-xhigh` → `reviewer-xhigh`), or undefined for other plugins. */
export const agentFile = (subagentType: string) => (subagentType.startsWith('anderson:') ? subagentType.slice(9) : undefined)

/** Frontmatter `effort:` of an agent .md, or ''. */
export const effortOf = (md: string) => /^effort:\s*(\S+)/m.exec(md)?.[1] ?? ''

/** Who a subagent is: a crew lens seat from its prompt, an anderson persona, or its raw type. */
export function persona(subagentType: string, prompt: string, model: string, effort: string) {
  const fam = /opus|sonnet|haiku|fable/i.exec(model)?.[0].toLowerCase() ?? model
  const file = agentFile(subagentType)
  const kind = file?.replace(/-(xhigh|medium)$/, '')
  const who = kind ? (PERSONA[kind] ?? kind.toUpperCase()) : subagentType
  // Crew prompts open with "You are <PERSONA>, the <lens> lens seat ..." (commands/approve-plan.md).
  const crew = /You are ([A-Z][A-Z' ]+?), the ([a-z]+) lens seat/.exec(prompt)
  return { name: crew?.[1] ?? who, model: effort ? `${fam}/${effort}` : fam, why: crew?.[2] }
}

/** One-line verdict from a finished seat's answer. */
export function verdict(answer: string, ok: boolean): { verdict: string; bad: boolean } {
  if (!ok) return { verdict: '✗ aborted', bad: true }
  const b = /(\d+)\s+blocking/i.exec(answer)
  const n = /(\d+)\s+nits?\b/i.exec(answer)
  const nits = n ? ` · ${n[1]} nit${n[1] === '1' ? '' : 's'}` : ''
  if (!b) return { verdict: '✓ done' + nits, bad: false }
  const k = Number(b[1])
  return { verdict: `${k ? '✗' : '✓'} ${k} blocking${nits}`, bad: k > 0 }
}

/** "Read api/limiter.py" from a tool call. */
export function act(tool: string, input: unknown, cwd: string): string {
  const i = (input ?? {}) as Record<string, unknown>
  const arg = [i.file_path, i.pattern, i.command, i.path, i.url, i.query, i.description].find(v => typeof v === 'string') as string | undefined
  const short = (arg ?? '').replace(cwd + '/', '').replace(/\s+/g, ' ')
  return `${tool.replace(/^mcp__[^_]+__/, '')} ${short}`.trim().slice(0, 80)
}

/** The STATE block of feature-research/<task>/state.md. */
export function parseState(text: string): Record<string, string> {
  const out: Record<string, string> = {}
  for (const l of text.split('\n')) {
    const m = /^([a-z_]+):\s+(.*?)\s*$/.exec(l)
    if (m?.[1] && m[2] !== undefined) out[m[1]] = m[2]
  }
  return out
}

/** The command the human types next at a gate, or undefined while nothing waits on them. */
export function nextStep(p: Pipe): string | undefined {
  if (p.stage === 'grill') return 'answer the grill'
  if (p.stage === 'plan_review') return '/anderson:approve-plan'
  if (p.stage === 'diff_review') return /block|rework/i.test(p.diffVerdict) ? '/anderson:rework' : '/anderson:approve-diff'
  return undefined
}

const W = (s: string) => [...s].length
const len = (l: Line) => l.reduce((n, [t]) => n + W(t), 0)
const pad = (l: Line, w: number): Line => (len(l) < w ? [...l, [' '.repeat(w - len(l)), '']] : l)
const cut = (s: string, w: number) => (W(s) > w ? [...s].slice(0, w - 1).join('') + '…' : s)
const clock = (ms: number) => { const s = Math.max(0, Math.round(ms / 1000)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}` }
const tok = (n?: number) => (n ? `${Math.round(n / 1000)}k tok` : '')
export const money = (x?: number) => (x === undefined ? '' : `$${x.toFixed(2)}`)

export type View = { seats: Seat[]; pipe: Pipe | null; now: number; cols: number; tick: number; usd?: number; working: boolean }

function dots(p: Pipe): Line {
  const at = STAGES.indexOf(p.stage)
  return STAGES.map((_, j): Seg => (j < at || p.stage === 'done' ? ['●', C.green] : j === at ? ['◐', p.stage === 'repair' ? C.yellow : C.cyan] : ['○', C.dim]))
}

function header(v: View): Line {
  const live = v.seats.filter(s => !s.doneAt).length
  const sig: Seg = ['⌐■-■', v.tick % 8 === 0 ? C.cyan : C.green]
  const h: Line = [sig, [' ', '']]
  const p = v.pipe
  if (p) {
    h.push(...dots(p), [' ', ''])
    const ask = !v.working && live === 0 ? nextStep(p) : undefined
    if (p.stage === 'done') h.push(['shipped', C.green], [' · ', C.dim])
    else if (ask) h.push(['your turn ▸ ', C.yellow], [ask, C.bold], [' · ', C.dim])
    else h.push([p.stage, p.stage === 'repair' ? C.yellow : C.bold], [` ${STAGES.indexOf(p.stage) + 1}/${STAGES.length} · `, C.dim])
    h.push([`${clock(v.now - p.seenAt)} · `, C.dim])
  } else h.push(['crew · ', C.dim])
  h.push([money(v.usd), C.green])
  if (live) h.push([`  ${live} live`, C.dim])
  return h
}

function box(s: Seat, v: View): Line[] {
  const w = 34
  const done = s.doneAt !== undefined
  const stalled = !done && v.now - s.lastAt > STALL_MS
  const edge = stalled ? C.yellow : done && s.bad ? C.red : C.dim
  const glyph: Seg = done ? [s.bad ? '✗' : '✓', s.bad ? C.red : C.green] : stalled ? ['⚠', C.yellow] : [SPIN.charAt(v.tick % SPIN.length), C.cyan]
  const name = ' ' + cut(s.name, 18) + ' '
  const why = s.why ? ' ' + s.why + ' ' : ''
  const fill = Math.max(1, w - 2 - W(name) - 2 - W(why))
  const top: Line = [['┌', edge], [name, C.bold], glyph, [' ' + '─'.repeat(fill), edge], [why, C.dim], ['┐', edge]]
  const meta = ' ' + s.model.padEnd(13) + clock((s.doneAt ?? v.now) - s.startedAt).padStart(5) + '  ' + tok(s.tokens)
  let tail: string, tc: string
  if (done) { tail = ` ${s.verdict} `; tc = s.bad ? C.red : C.green }
  else if (stalled) { tail = ` ⚠ stalled ${clock(v.now - s.lastAt)} · ${s.act ?? ''} `; tc = C.yellow }
  else { tail = ` ▸ ${s.act ?? 'starting'} `; tc = C.grey }
  tail = cut(tail, w - 3)
  return [
    top,
    [['│', edge], [cut(meta, w - 2).padEnd(w - 2), C.blue], ['│', edge]],
    [['└', edge], [tail, tc], ['─'.repeat(Math.max(0, w - 2 - W(tail))), edge], ['┘', edge]],
  ]
}

function compact(s: Seat): Line {
  return [['[ ', C.dim], [s.name.replace(/^(THE|AGENT) /, '') + ' ', C.bold], [(s.verdict ?? '✓').split(' · ')[0] ?? '✓', s.bad ? C.red : C.green], [' ]', C.dim]]
}

/** Lay boxes left to right, wrapping when full; when crowded, finished seats shrink to one-line cells. */
function grid(v: View): Line[] {
  const full = v.seats.map(s => box(s, v))
  const total = full.reduce((n, b) => n + len(b[0] ?? []) + 1, 0)
  const shrink = total > v.cols && v.seats.some(s => s.doneAt) && v.seats.some(s => !s.doneAt)
  const items = shrink
    ? [...v.seats.filter(s => !s.doneAt).map(s => box(s, v)), v.seats.filter(s => s.doneAt).map(compact)]
    : full
  const rows: Line[][][] = []
  let cur: Line[][] = [], curW = 0
  for (const b of items) {
    const bw = Math.max(...b.map(len)) + 1
    if (curW + bw > v.cols && cur.length) { rows.push(cur); cur = []; curW = 0 }
    cur.push(b); curW += bw
  }
  if (cur.length) rows.push(cur)
  const out: Line[] = []
  for (const r of rows) {
    const h = Math.max(...r.map(b => b.length))
    for (let y = 0; y < h; y++) {
      const l: Line = []
      for (const b of r) l.push(...pad(b[y] ?? [], Math.max(...b.map(len))), [' ', ''])
      out.push(l)
    }
  }
  return out
}

/** The band: header, then the crew grid. Empty when there is nothing to show. */
export function band(v: View): Line[] {
  if (!v.pipe && !v.seats.length) return []
  return [header(v), ...(v.seats.length ? grid(v) : [])]
}
