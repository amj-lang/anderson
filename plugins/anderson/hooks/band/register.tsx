import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register } from 'claude-code'

import type { Pipe, Seat } from '../../types/band'
import { act, agentFile, band, C, effortOf, parseState, persona, verdict } from './band'
import { frame, portraitFor, SIZE } from './portraits'

const seatsA = atom({ plugin: 'anderson', key: 'seats' } as const, {})
const pipeA = atom({ plugin: 'anderson', key: 'pipe' } as const, null)
const tickA = atom({ plugin: 'anderson', key: 'tick' } as const, 0)
const tokA = atom({ plugin: 'anderson', key: 'tokens' } as const, { i: 0, o: 0 })

// ponytail: tasks untouched for 6h are stale and hidden; make it an option if someone parks a task longer.
const STALE_MS = 6 * 3600_000

/** Newest feature-research/<task>/state.md under the project root, or null. */
async function loadPipe($: EngineInterface): Promise<Pipe | null> {
  const root = await $.session.root()
  const dir = `${root}/feature-research`
  if (!(await $.fs.exists(dir))) return null
  let best: { path: string; mtime: number } | null = null
  for (const ent of await $.fs.list(dir)) {
    if (ent.kind !== 'dir') continue
    const path = `${dir}/${ent.name}/state.md`
    if (!(await $.fs.exists(path))) continue
    const { mtimeMs } = await $.fs.stat(path)
    if (!best || mtimeMs > best.mtime) best = { path, mtime: mtimeMs }
  }
  const now = await $.clock.now()
  if (!best || now - best.mtime > STALE_MS) return null
  const s = parseState(await $.fs.read(best.path))
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
  on('session.start', async ($, e, next) => {
    const r = await next(e)
    await refresh($)
    // Animate spinners, stall timers and the portrait while the band shows anything.
    $.clock.every(250, async () => {
      const seats = Object.values(await read($, seatsA))
      if (seats.length || (await read($, pipeA))) await update($, tickA, n => n + 1)
    })
    return r
  })

  on('agent.spawn', async ($, e, next) => {
    const r = await next(e)
    if (r.deny || !r.agentId) return r
    const id = r.agentId
    try {
      const now = await $.clock.now()
      const file = agentFile(e.subagentType)
      const md = file ? await $.fs.read(`${$.plugin.root}/agents/${file}.md`).catch(() => '') : ''
      const p = persona(e.subagentType, e.prompt, r.model, effortOf(md))
      const seat: Seat = { id, ...p, startedAt: now, lastAt: now }
      await update($, seatsA, s => ({ ...s, [id]: seat }))
      await refresh($)
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
        }
      }
      await refresh($)
    } catch {}
    return r
  })

  // A new prompt from the person: finished seats have been read, clear them.
  on('prompt.submit', async ($, e, next) => {
    try {
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
