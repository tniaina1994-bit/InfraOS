import React from 'react'

export function Card({ title, children, right }: { title?: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="card">
      {(title || right) && (
        <div className="flex items-center justify-between mb-3">
          {title && <h3 className="font-semibold">{title}</h3>}
          {right}
        </div>
      )}
      {children}
    </div>
  )
}

export function Stat({ label, value, tone }: { label: string; value: string; tone?: 'ok' | 'warn' | 'bad' }) {
  const color = tone === 'ok' ? 'text-green-400' : tone === 'warn' ? 'text-yellow-400' : tone === 'bad' ? 'text-red-400' : ''
  return (
    <div className="card">
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`text-2xl font-bold break-words ${color}`}>{value}</p>
    </div>
  )
}

export function Badge({ value, good, bad }: { value: string; good?: string[]; bad?: string[] }) {
  const v = String(value)
  const tone = good?.includes(v) ? 'bg-green-800' : bad?.includes(v) ? 'bg-red-800' : 'bg-slate-700'
  return <span className={`text-xs px-2 py-0.5 rounded ${tone}`}>{v}</span>
}

export function StatusDot({ active }: { active: boolean }) {
  return <span className={`inline-block w-2 h-2 rounded-full ${active ? 'bg-green-400' : 'bg-slate-500'}`} />
}

export function Table<T extends Record<string, any>>({ columns, rows, keyOf }: {
  columns: [string, (row: T) => React.ReactNode][]
  rows: T[]
  keyOf: (row: T, i: number) => string | number
}) {
  if (rows.length === 0) return <p className="text-sm text-slate-400">Aucune donnée</p>
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-400 border-b border-slate-800">
            {columns.map(([h]) => <th key={h} className="py-1 pr-3 font-medium">{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={keyOf(r, i)} className="border-b border-slate-800/50">
              {columns.map(([h, f]) => <td key={h} className="py-1.5 pr-3">{f(r)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 text-xs text-slate-400">
      {label}
      {children}
    </label>
  )
}

export const inputCls = 'px-2 py-1.5 rounded bg-slate-800 text-sm text-slate-100'

export function Msg({ text }: { text: string }) {
  if (!text) return null
  return <div className="card text-sm">{text}</div>
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-slate-400 py-4" role="status" aria-live="polite">
      <span className="inline-block w-4 h-4 rounded-full border-2 border-slate-600 border-t-blue-400 animate-spin" />
      {label || 'Chargement…'}
    </div>
  )
}

export function Skeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-2 py-1" aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className="h-4 rounded bg-slate-800 animate-pulse" style={{ width: `${95 - i * 12}%` }} />
      ))}
    </div>
  )
}

export function Empty({ text }: { text: string }) {
  return <p className="text-sm text-slate-400">{text}</p>
}
