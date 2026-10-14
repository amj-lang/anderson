import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Pipe, Seat } from '../../types/band'
import { act, agentFile, band, C, costLine, effortOf, parseState, persona, verdict } from './band'
import { frame, portraitFor, SIZE } from './portraits'

const seatsA = atom({ plugin: 'anderson', key: 'seats' } as const, {})
const pipeA = atom({ plugin: 'anderson', key: 'pipe' } as const, null)
const taskA = atom({ plugin: 'anderson', key: 'task' } as const, null)
const tickA = atom({ plugin: 'anderson', key: 'tick' } as const, 0)
const tokA = atom({ plugin: 'anderson', key: 'tokens' } as const, { i: 0, o: 0 })

// Appends to cost.jsonl chain here so parallel seats never lose a line.
let ledger = Promise.resolve()

// state.md is written by tools (sed, Edit) that raise no event, so the band re-reads it on the clock.
const POLL_TICKS = 8 // x 250 ms = 2 s

/** Task slugs a prompt names: `/anderson:<cmd> <slug>` first, then every `feature-research/<task>/` path. */
export function tasksOf(text: string): string[] {
  const out: string[] = []
  const cmd = /\/anderson:(?:start|approve-plan|approve-diff|rework|status|auto)\s+(\S+)/.exec(text)
  if (cmd?.[1]) out.push(cmd[1])
  for (const m of text.matchAll(/feature-research\/([A-Za-z0-9._-]+)\//g)) if (m[1]) out.push(m[1])
  return out.map(t => t.split('/').pop() ?? '').filter(t => t && t !== '.' && t !== '..')
}

/** Pin this session to the first task the text names whose scratch dir exists (doc examples name none). */
async function pin($: EngineInterface, text: string) {
  const root = await $.session.root()
  for (const t of tasksOf(text)) {
    if (await $.fs.exists(`${root}/feature-research/${t}/state.md`)) { await update($, taskA, () => t); return }
  }
}

/** The state.md of this session's own task, or null: another session's task is never shown. */
async function loadPipe($: EngineInterface): Promise<Pipe | null> {
  const mine = await read($, taskA)
  if (!mine) return null
  const path = `${await $.session.root()}/feature-research/${mine}/state.md`
  if (!(await $.fs.exists(path))) return null // shipped: approve-diff removed the scratch
  const now = await $.clock.now()
  const s = parseState(await $.fs.read(path))
  const prev = await read($, pipeA)
  return {
    task: s.task ?? '?',
    stage: s.stage ?? '?',
    diffVerdict: s.diff_verdict ?? '',
    seenAt: prev && prev.task === s.task ? prev.seenAt : now,
  }
}

async function refresh($: EngineInterface) {
  const pipe = await loadPipe($).catch(() => null)
  await update($, pipeA, () => pipe)
}

export const register: Register = on => {
  let timer: { cancel(): void } | undefined
  on('session.start', async ($, e, next) => {
    const r = await next(e)
    await refresh($)
    // Animate spinners, stall timers and the portrait while the band shows anything; poll state.md.
    timer?.cancel()
    timer = $.clock.every(250, async () => {
      const seats = Object.values(await read($, seatsA))
      const tick = await read($, tickA)
      if (tick % POLL_TICKS === 0) await refresh($)
      if (seats.length || (await read($, pipeA))) await update($, tickA, n => n + 1)
    })
    return r
  })

  on('agent.spawn', async ($, e, next) => {
    const r = await next(e)
    if (r.deny || !r.agentId) return r
    const id = r.agentId
    try {
      await pin($, e.prompt)
      await refresh($)
      const now = await $.clock.now()
      const file = agentFile(e.subagentType)
      const md = file ? await $.fs.read(`${$.plugin.root}/agents/${file}.md`).catch(() => '') : ''
      const p = persona(e.subagentType, e.prompt, r.model, effortOf(md))
      const seat: Seat = { id, ...p, startedAt: now, lastAt: now, stage: (await read($, pipeA))?.stage }
      await update($, seatsA, s => ({ ...s, [id]: seat }))
    } catch {}
    return r
  })

  on('tool.call', async ($, e, next) => {
    const id = e.agentId
    if (id) {
      try {
        const seats = await read($, seatsA)
        if (seats[id]) {
          const now = await $.clock.now()
          const a = act(String(e.tool), e, await $.session.cwd())
          await update($, seatsA, s => (s[id] ? { ...s, [id]: { ...s[id], act: a, lastAt: now } } : s))
        }
      } catch {}
    }
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const r = await next(e)
    try {
      // Session tokens: every turn, main loop and subagents alike.
      const u = e.usage
      if (u) await update($, tokA, t => ({ i: t.i + u.input_tokens + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0), o: t.o + u.output_tokens }))
      const id = e.agentId
      if (id) {
        const seats = await read($, seatsA)
        if (seats[id]) {
          const now = await $.clock.now()
          const u = e.usage
          const tokens = u ? u.input_tokens + u.output_tokens + (u.cache_read_input_tokens ?? 0) + (u.cache_creation_input_tokens ?? 0) : undefined
          const v = verdict(e.answer, e.reason === 'answer')
          await update($, seatsA, s => (s[id] ? { ...s, [id]: { ...s[id], doneAt: now, tokens, ...v } } : s))
          // Ledger: only while the task's scratch dir lives (approve-diff removes it; a write would recreate it).
          const task = await read($, taskA)
          const dir = task && `${await $.session.root()}/feature-research/${task}`
          if (dir && (await $.fs.exists(`${dir}/state.md`))) {
            const line = costLine({ ...seats[id], tokens }, now)
            ledger = ledger.then(async () => {
              const old = await $.fs.read(`${dir}/cost.jsonl`).catch(() => '')
              await $.fs.write(`${dir}/cost.jsonl`, old + line)
            }).catch(() => {})
            await ledger
          }
        }
      }
      await refresh($)
    } catch {}
    return r
  })

  // A new prompt from the person: finished seats have been read, clear them.
  on('prompt.submit', async ($, e, next) => {
    try {
      await pin($, e.text)
      await update($, seatsA, s => Object.fromEntries(Object.entries(s).filter(([, x]) => x.doneAt === undefined)))
      await refresh($)
    } catch {}
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    if (e.props.hasSurvey) return next(e)
    const seats = Object.values(await read($, seatsA)).sort((a, b) => a.startedAt - b.startedAt)
    const pipe = await read($, pipeA)
    const tick = await read($, tickA)
    const tok = await read($, tokA)
    // The persona's portrait sits at the right edge, 8 cols x 4 rows; dropped on narrow terminals.
    const cols = e.props.bodyColumns
    const face = cols >= 80 ? portraitFor(seats, pipe) : undefined
    const lines = band({ seats, pipe, now: await $.clock.now(), cols: face ? cols - 9 : cols, tick, tok, working: e.props.isWorking })
    if (!lines.length) return next(e)
    const ui = $.ui.resolve(e)
    const { Box, Text } = ui
    const text = (
      <Box flexDirection="column" flexGrow={1}>
        {lines.map(l => (
          <Text wrap="truncate">
            {l.map(([t, c]) =>
              c === C.dim ? <Text dimColor>{t}</Text> : c === C.bold ? <Text bold>{t}</Text> : c ? <Text color={c}>{t}</Text> : t,
            )}
          </Text>
        ))}
      </Box>
    )
    // Pixels only where the surface draws an Image (terminal); elsewhere the band alone.
    if (!face || !('Image' in ui)) return text
    const { Image } = ui
    const rgba = (frame(face, tick) as Uint8Array & { toBase64(): string }).toBase64()
    return (
      <Box flexDirection="row">
        {text}
        <Box marginLeft={1}>
          <Image source={{ rgba, width: SIZE, height: SIZE }} columns={8} rows={4} alt={face.replace(/^(THE|AGENT) /, '')} />
        </Box>
      </Box>
    )
  })
}
