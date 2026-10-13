export type Seat = {
  id: string
  name: string
  model: string
  why?: string
  startedAt: number
  lastAt: number
  act?: string
  doneAt?: number
  verdict?: string
  bad?: boolean
  tokens?: number
}

export type Pipe = {
  task: string
  stage: string
  diffVerdict: string
  seenAt: number
}

declare module 'claude-code' {
  interface PluginState {
    'anderson': { seats: Record<string, Seat>; pipe: Pipe | null; tick: number; tokens: { i: number; o: number } }
  }
}
