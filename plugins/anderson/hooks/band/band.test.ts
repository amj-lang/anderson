import { expect, test } from 'claude-code/testing'

import { act, agentFile, band, effortOf, nextStep, parseState, persona, verdict } from './band'

const text = (ls: [string, string][][]) => ls.map(l => l.map(s => s[0]).join('').trimEnd())

test('persona: anderson agents, crew seats, effort twins, others', () => {
  expect(persona('anderson:implementer', 'go', 'claude-sonnet-5-5', 'medium')).toEqual({ name: 'NEO', model: 'sonnet/medium', why: undefined })
  expect(persona('anderson:reviewer-xhigh', 'review', 'claude-opus-5-5', 'xhigh')).toEqual({ name: 'AGENT SMITH', model: 'opus/xhigh', why: undefined })
  expect(persona('anderson:reviewer-medium', 'You are NIOBE, the performance lens seat on the diff review', 'claude-opus-5-5', 'medium'))
    .toEqual({ name: 'NIOBE', model: 'opus/medium', why: 'performance' })
  expect(persona('Explore', 'find x', 'claude-haiku-5-5', '')).toEqual({ name: 'Explore', model: 'haiku', why: undefined })
  expect(agentFile('anderson:reviewer-xhigh')).toBe('reviewer-xhigh')
  expect(effortOf('---\nname: reviewer\nmodel: opus\neffort: high\n---')).toBe('high')
})

test('verdict: blocking, nits, plain done, aborted', () => {
  expect(verdict('Found 1 blocking issue and 2 nits.', true)).toEqual({ verdict: '✗ 1 blocking · 2 nits', bad: true })
  expect(verdict('0 blocking, 1 nit', true)).toEqual({ verdict: '✓ 0 blocking · 1 nit', bad: false })
  expect(verdict('All good.', true)).toEqual({ verdict: '✓ done', bad: false })
  expect(verdict('', false).bad).toBe(true)
})

test('act: tool + short arg, cwd stripped', () => {
  expect(act('Read', { file_path: '/repo/api/limiter.py' }, '/repo')).toBe('Read api/limiter.py')
  expect(act('Bash', { command: 'pytest  -k\nexport' }, '/repo')).toBe('Bash pytest -k export')
})

test('state.md parse and gate step', () => {
  const s = parseState('<!-- STATE:START -->\ntask:            ar-1-x\nstage:           diff_review\ndiff_verdict:    blocking\n')
  expect(s.stage).toBe('diff_review')
  expect(nextStep({ task: 'ar-1-x', stage: s.stage ?? '', diffVerdict: s.diff_verdict ?? '', seenAt: 0 })).toBe('/anderson:rework')
})

test('band: crew grid, stall, verdict, and shrink when crowded', () => {
  const seat = (name: string, extra = {}) => ({ id: name, name, model: 'opus/high', startedAt: 0, lastAt: 0, act: 'Read a.py', ...extra })
  const seats = [
    seat('AGENT SMITH', { doneAt: 1000, verdict: '✗ 1 blocking', bad: true }),
    seat('SERAPH', { doneAt: 1000, verdict: '✓ 0 blocking' }),
    seat('NIOBE', { lastAt: 0 }),
    seat('MEROVINGIAN', { lastAt: 200_000 }),
  ]
  const pipe = { task: 'ar-412-rate-limit', stage: 'diff_review', diffVerdict: 'pending', seenAt: 0 }
  const wide = text(band({ seats, pipe, now: 230_000, cols: 144, tick: 1, usd: 1.19, working: true }))
  expect(wide[0]).toContain('●●●●●◐○ diff_review 6/7')
  expect(wide.join('\n')).toContain('✗ 1 blocking')
  expect(wide.join('\n')).toContain('⚠ stalled 3:50')
  expect(wide.join('\n')).toContain('▸ Read a.py')
  const narrow = text(band({ seats, pipe, now: 230_000, cols: 80, tick: 1, usd: 1.19, working: true }))
  expect(narrow.join('\n')).toContain('[ SMITH ✗ 1 blocking ]')
  for (const l of narrow) expect([...l].length <= 81).toBe(true)
  // Idle at the gate: header names the next command.
  const gate = text(band({ seats: [], pipe, now: 1000, cols: 144, tick: 1, usd: 1, working: false }))
  expect(gate[0]).toContain('your turn ▸ /anderson:approve-diff')
  expect(band({ seats: [], pipe: null, now: 0, cols: 144, tick: 0, working: false })).toEqual([])
})
