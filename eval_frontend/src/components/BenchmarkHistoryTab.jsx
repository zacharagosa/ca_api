import React, { useState } from 'react'
import {
  History, Bookmark, ArrowUpRight, ArrowDownRight, CheckCircle2,
  XCircle, AlertTriangle, Sparkles, Clock, Eye, RefreshCw
} from 'lucide-react'
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend
} from 'recharts'
import { getCategoryName, getCategoryBadgeColor } from '../lib/utils'

export default function BenchmarkHistoryTab({
  recentRuns,
  baselineComparison,
  onSetBaseline,
  onSelectRun
}) {
  const [selectedRunId, setSelectedRunId] = useState(recentRuns?.[0]?.run_id || '')

  const currentRun = recentRuns?.find(r => r.run_id === selectedRunId) || recentRuns?.[0]
  const baselineRun = recentRuns?.find(r => r.is_baseline) || recentRuns?.[recentRuns.length - 1]

  // Trend data over runs
  const trendData = (recentRuns || []).slice().reverse().map(r => ({
    name: r.run_id.slice(0, 8),
    PassRate: r.pass_rate,
    Score: r.overall_reliability_score,
    Latency: r.avg_latency_seconds
  }))

  const regressions = baselineComparison?.regressions || []
  const improvements = baselineComparison?.improvements || []

  return (
    <div className="space-y-6">
      
      {/* Header & Run Selector */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
              <History className="w-4 h-4" />
            </span>
            <h2 className="text-sm font-bold text-white">Historical Benchmark Diffs & Regression Audit</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Compare benchmark scores across recent codebase updates to detect quality regressions, schema errors, and latency shifts.
          </p>
        </div>

        {recentRuns?.length > 0 && (
          <div className="flex items-center gap-2">
            <label className="text-xs text-slate-400">Select Run:</label>
            <select
              value={selectedRunId}
              onChange={(e) => setSelectedRunId(e.target.value)}
              className="px-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs font-mono text-slate-200 focus:outline-none focus:border-indigo-500"
            >
              {recentRuns.map(r => (
                <option key={r.run_id} value={r.run_id}>
                  {r.title || r.run_id} ({r.pass_rate}% Pass - {new Date((r.started_at || 0) * 1000).toLocaleTimeString()})
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Regression & Improvement Delta Cards */}
      {baselineComparison && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Pass Rate Delta</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-2">
              <span>{baselineComparison.pass_rate_delta > 0 ? `+${baselineComparison.pass_rate_delta}%` : `${baselineComparison.pass_rate_delta}%`}</span>
              <span className={`text-xs font-semibold ${baselineComparison.pass_rate_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                {baselineComparison.pass_rate_delta >= 0 ? 'Improved' : 'Regressed'}
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Reliability Score Delta</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-2">
              <span>{baselineComparison.reliability_delta > 0 ? `+${baselineComparison.reliability_delta}` : `${baselineComparison.reliability_delta}`}</span>
              <span className={`text-xs font-semibold ${baselineComparison.reliability_delta >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                pts
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Latency Delta</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-2">
              <span>{baselineComparison.latency_delta_seconds > 0 ? `+${baselineComparison.latency_delta_seconds}s` : `${baselineComparison.latency_delta_seconds}s`}</span>
              <span className={`text-xs font-semibold ${baselineComparison.latency_delta_seconds <= 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
                {baselineComparison.latency_delta_seconds <= 0 ? 'Faster' : 'Slower'}
              </span>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800">
            <div className="text-xs font-medium text-slate-400">Routing Accuracy Delta</div>
            <div className="text-xl font-bold text-white mt-1 flex items-baseline gap-2">
              <span>{baselineComparison.routing_accuracy_delta > 0 ? `+${baselineComparison.routing_accuracy_delta}%` : `${baselineComparison.routing_accuracy_delta}%`}</span>
              <span className="text-xs text-cyan-400 font-semibold">Router</span>
            </div>
          </div>
        </div>
      )}

      {/* Regressions Alert Box */}
      {regressions.length > 0 ? (
        <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-800/50 space-y-3">
          <div className="flex items-center gap-2 text-xs font-bold text-rose-300">
            <AlertTriangle className="w-4 h-4 text-rose-400" />
            ⚠️ {regressions.length} Regression(s) Detected Compared to Baseline
          </div>
          <div className="space-y-2">
            {regressions.map((reg, idx) => (
              <div key={idx} className="p-3 rounded-lg bg-slate-950 border border-rose-900/50 flex items-center justify-between text-xs">
                <div>
                  <div className="font-bold text-white flex items-center gap-2">
                    <span>{reg.title}</span>
                    <span className="text-[10px] font-mono text-slate-400">({reg.test_id})</span>
                  </div>
                  <div className="text-[11px] text-rose-300 mt-1">
                    Previous Score: <strong>{reg.previous_score}</strong> → Current Score: <strong>{reg.current_score}</strong>
                  </div>
                  {reg.issues?.length > 0 && (
                    <div className="text-[10px] text-slate-400 mt-0.5">{reg.issues.join(' | ')}</div>
                  )}
                </div>
                <span className="px-2 py-1 rounded bg-rose-900/60 text-rose-200 text-[10px] font-bold">
                  REGRESSION
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-800/40 text-emerald-300 text-xs flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          <span>Zero quality regressions detected! All previous benchmark test invariants maintained.</span>
        </div>
      )}

      {/* Historical Trend Charts */}
      {trendData.length > 1 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
            <div className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-cyan-400" />
              Pass Rate & Reliability Score Trend
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Line type="monotone" dataKey="PassRate" stroke="#34d399" strokeWidth={2} name="Pass Rate (%)" />
                  <Line type="monotone" dataKey="Score" stroke="#38bdf8" strokeWidth={2} name="Reliability Score" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
            <div className="text-xs font-semibold text-slate-200 mb-3 flex items-center gap-2">
              <Clock className="w-4 h-4 text-sky-400" />
              Average Latency Trend (Seconds)
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={trendData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                  <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                  <Bar dataKey="Latency" fill="#60a5fa" radius={[4, 4, 0, 0]} name="Avg Latency (s)" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}
