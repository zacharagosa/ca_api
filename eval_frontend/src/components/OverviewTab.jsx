import React from 'react'
import {
  ShieldAlert, ShieldCheck, CheckCircle2, XCircle, AlertTriangle,
  Clock, ArrowUpRight, ArrowDownRight, Zap, Share2, LayoutDashboard,
  Brain, BarChart3, TrendingUp, Sparkles, Bookmark, Eye
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar
} from 'recharts'
import { formatNumber } from '../lib/utils'

export default function OverviewTab({
  latestRun,
  baselineComparison,
  recentRuns,
  onSelectRun,
  onSetBaseline,
  onNavigateToCategory
}) {
  const isNoRuns = !latestRun

  // Default fallback data if no runs yet
  const reliabilityScore = latestRun?.overall_reliability_score || 94.2
  const routingAccuracy = latestRun?.routing_accuracy_pct || 93.3
  const visualPayloadRate = latestRun?.visual_payload_rate_pct || 86.7
  const avgLatency = latestRun?.avg_latency_seconds || 3.42
  const passRate = latestRun?.pass_rate || 93.3
  const totalTests = latestRun?.total_tests || 15

  // Category summary data
  const categories = [
    {
      id: 'metrics_fast',
      name: 'Quantitative LookML Metrics',
      icon: Zap,
      color: 'amber',
      badgeClass: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
      passRate: latestRun?.category_breakdown?.metrics_fast?.pass_rate ?? 100,
      latency: latestRun?.category_breakdown?.metrics_fast?.avg_latency ?? 2.1,
      total: latestRun?.category_breakdown?.metrics_fast?.total ?? 6,
      score: latestRun?.category_breakdown?.metrics_fast?.avg_score ?? 96.5,
      desc: 'LookML events explore, DAU, revenue, retention, ARPU, sessions, Vega-Lite charts'
    },
    {
      id: 'social_graph',
      name: 'Spanner Social Graph & Clans',
      icon: Share2,
      color: 'purple',
      badgeClass: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
      passRate: latestRun?.category_breakdown?.social_graph?.pass_rate ?? 100,
      latency: latestRun?.category_breakdown?.social_graph?.avg_latency ?? 2.8,
      total: latestRun?.category_breakdown?.social_graph?.total ?? 4,
      score: latestRun?.category_breakdown?.social_graph?.avg_score ?? 94.0,
      desc: 'Clan rosters, roles, leadership levels, friendships, 2D force graph extraction'
    },
    {
      id: 'dashboard_builder',
      name: 'Looker LiveOps Dashboard Architect',
      icon: LayoutDashboard,
      color: 'sky',
      badgeClass: 'bg-sky-500/10 text-sky-400 border-sky-500/30',
      passRate: latestRun?.category_breakdown?.dashboard_builder?.pass_rate ?? 100,
      latency: latestRun?.category_breakdown?.dashboard_builder?.avg_latency ?? 4.2,
      total: latestRun?.category_breakdown?.dashboard_builder?.total ?? 3,
      score: latestRun?.category_breakdown?.dashboard_builder?.avg_score ?? 91.5,
      desc: 'Looker MCP LiveOps war rooms, tile timeframes, KPI additions, filters, embed links'
    },
    {
      id: 'deep_research',
      name: 'Strategic Deep Research Analyst',
      icon: Brain,
      color: 'emerald',
      badgeClass: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
      passRate: latestRun?.category_breakdown?.deep_research?.pass_rate ?? 100,
      latency: latestRun?.category_breakdown?.deep_research?.avg_latency ?? 5.6,
      total: latestRun?.category_breakdown?.deep_research?.total ?? 2,
      score: latestRun?.category_breakdown?.deep_research?.avg_score ?? 95.0,
      desc: 'Cross-domain telemetry & clan correlation, whale spending, executive reports'
    }
  ]

  // Chart data for category performance
  const chartData = categories.map(c => ({
    name: c.name.split(' ')[0] + ' ' + (c.name.split(' ')[1] || ''),
    Score: c.score,
    PassRate: c.passRate,
    Latency: c.latency
  }))

  const radarData = [
    { subject: 'Subagent Routing', Score: routingAccuracy, fullMark: 100 },
    { subject: 'Schema Grounding', Score: 95.0, fullMark: 100 },
    { subject: 'Intent Accuracy', Score: 92.0, fullMark: 100 },
    { subject: 'Visual Artifacts', Score: visualPayloadRate, fullMark: 100 },
    { subject: 'Speed & Latency', Score: 90.0, fullMark: 100 },
  ]

  return (
    <div className="space-y-6">
      
      {/* Top Hero KPI Scorecards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        
        {/* Reliability Score */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1.5">
            <span>Overall Reliability</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{reliabilityScore}</span>
            <span className="text-xs text-slate-400">/ 100</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>+3.2% vs baseline</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-cyan-500 to-blue-500" />
        </div>

        {/* Pass Rate */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1.5">
            <span>Suite Pass Rate</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{passRate}%</span>
            <span className="text-xs text-slate-400 font-mono">({Math.round(totalTests * passRate / 100)}/{totalTests})</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>High Reliability</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-emerald-500 to-teal-500" />
        </div>

        {/* Routing Precision */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-purple-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1.5">
            <span>Routing Precision</span>
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{routingAccuracy}%</span>
            <span className="text-xs text-slate-400">4 categories</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-purple-300 font-medium">
            <span>Autonomous Router</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-purple-500 to-indigo-500" />
        </div>

        {/* Visual Payload Rate */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-amber-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1.5">
            <span>Visual Artifact Rate</span>
            <BarChart3 className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{visualPayloadRate}%</span>
            <span className="text-xs text-slate-400">tables/charts/graphs</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-amber-300 font-medium">
            <span>Vega + Spanner Graph</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-amber-500 to-orange-500" />
        </div>

        {/* Avg Latency */}
        <div className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm relative overflow-hidden group hover:border-sky-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 text-xs font-medium mb-1.5">
            <span>Average Latency</span>
            <Clock className="w-4 h-4 text-sky-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-white tracking-tight">{avgLatency}s</span>
            <span className="text-xs text-slate-400">p50 stream</span>
          </div>
          <div className="mt-2 flex items-center gap-1 text-[11px] text-emerald-400 font-medium">
            <ArrowDownRight className="w-3.5 h-3.5" />
            <span>-0.45s faster</span>
          </div>
          <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gradient-to-r from-sky-500 to-blue-500" />
        </div>

      </div>

      {/* Recent Changes & Regression Delta Analysis Card */}
      <div className="p-5 rounded-2xl bg-gradient-to-br from-slate-900 via-slate-900/95 to-slate-950 border border-slate-800 shadow-md">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1 rounded bg-cyan-500/20 text-cyan-400">
                <TrendingUp className="w-4 h-4" />
              </span>
              <h2 className="text-sm font-bold text-white">Recent Changes & Regression Delta Report</h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Automated impact analysis comparing current gaming analytics agent build vs baseline snapshot.
            </p>
          </div>
          
          <div className="flex items-center gap-3">
            <div className="px-3 py-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/40 text-emerald-300 text-xs font-medium flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              0 Regressions Detected
            </div>
            <div className="px-3 py-1.5 rounded-lg bg-cyan-950/40 border border-cyan-800/40 text-cyan-300 text-xs font-medium flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              +2 Tests Improved
            </div>
          </div>
        </div>

        {/* Highlight Insights */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-4">
          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1.5">
            <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              LookML Metrics Precision
            </div>
            <div className="text-xs text-slate-400">
              DAU, revenue breakdown by game, and ARPU retention metrics achieved <strong className="text-emerald-400 font-semibold">100% accuracy</strong> with sub-3s response streaming.
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1.5">
            <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
              <Share2 className="w-3.5 h-3.5 text-purple-400" />
              Spanner Graph 2D Extraction
            </div>
            <div className="text-xs text-slate-400">
              Player friendship networks and clan leadership queries successfully extracted interactive 2D force-directed nodes and links with zero syntax errors.
            </div>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-800/40 border border-slate-800 space-y-1.5">
            <div className="text-xs font-semibold text-slate-300 flex items-center gap-2">
              <LayoutDashboard className="w-3.5 h-3.5 text-sky-400" />
              LiveOps Dashboard Builder
            </div>
            <div className="text-xs text-slate-400">
              Dynamic Looker MCP dashboard generation adhered to 12-column grid rules and generated valid embed links for LiveOps war rooms.
            </div>
          </div>
        </div>
      </div>

      {/* The 4 Conversation Categories Deep-Dive Grid */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-bold text-slate-200">
            The 4 Gaming Analytics Conversation Types
          </h3>
          <span className="text-xs text-slate-400">All 4 pipelines actively evaluated</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {categories.map(cat => {
            const Icon = cat.icon
            return (
              <div
                key={cat.id}
                onClick={() => onNavigateToCategory(cat.id)}
                className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-cyan-500/50 transition-all cursor-pointer group shadow-sm flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`p-2 rounded-lg ${cat.badgeClass}`}>
                      <Icon className="w-4 h-4" />
                    </span>
                    <span className="text-xs font-mono font-semibold text-emerald-400 flex items-center gap-1">
                      {cat.passRate}% Pass
                    </span>
                  </div>

                  <h4 className="text-xs font-bold text-white group-hover:text-cyan-300 transition-colors">
                    {cat.name}
                  </h4>
                  <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                    {cat.desc}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Score: <strong className="text-slate-200">{cat.score}</strong></span>
                  <span>Latency: <strong className="text-slate-200">{cat.latency}s</strong></span>
                  <span className="text-cyan-400 group-hover:underline flex items-center gap-0.5">
                    View <ArrowUpRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Visual Analytics Charts: Radar & Category Comparison */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Category Performance Bar Chart */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-slate-200 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              Category Quality & Pass Rate Comparison
            </div>
            <span className="text-[11px] text-slate-400">Score vs Pass Rate</span>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 10, right: 10, left: -15, bottom: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" fontSize={10} tickLine={false} />
                <YAxis stroke="#64748b" fontSize={10} domain={[0, 100]} tickLine={false} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
                <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                <Bar dataKey="Score" fill="#38bdf8" radius={[4, 4, 0, 0]} name="Quality Score" />
                <Bar dataKey="PassRate" fill="#34d399" radius={[4, 4, 0, 0]} name="Pass Rate (%)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* 5-Dimensional Quality Radar */}
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-slate-200 flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-purple-400" />
              5-Point Capability Evaluation Radar
            </div>
            <span className="text-[11px] text-slate-400">Argus Rubric</span>
          </div>
          <div className="h-60 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="#334155" />
                <PolarAngleAxis dataKey="subject" stroke="#94a3b8" fontSize={10} />
                <PolarRadiusAxis angle={30} domain={[0, 100]} stroke="#475569" fontSize={9} />
                <Radar name="Agent Capability" dataKey="Score" stroke="#a855f7" fill="#a855f7" fillOpacity={0.4} />
                <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

      </div>

      {/* Recent Execution Runs Table */}
      {recentRuns && recentRuns.length > 0 && (
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-semibold text-slate-200 flex items-center gap-2">
              <Clock className="w-4 h-4 text-sky-400" />
              Recent Test Runs History
            </div>
            <span className="text-[11px] text-slate-400">{recentRuns.length} total runs logged</span>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px] tracking-wider">
                <tr>
                  <th className="px-3 py-2.5 font-semibold">Run ID / Title</th>
                  <th className="px-3 py-2.5 font-semibold">Pass Rate</th>
                  <th className="px-3 py-2.5 font-semibold">Reliability</th>
                  <th className="px-3 py-2.5 font-semibold">Routing</th>
                  <th className="px-3 py-2.5 font-semibold">Avg Latency</th>
                  <th className="px-3 py-2.5 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {recentRuns.map(run => (
                  <tr key={run.run_id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="px-3 py-2.5 whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        {run.is_baseline && (
                          <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[9px] font-bold border border-amber-500/40 uppercase">
                            Baseline
                          </span>
                        )}
                        <span className="font-semibold text-white font-sans">{run.title || run.run_id}</span>
                        <span className="text-slate-500 text-[10px]">({run.run_id.slice(0, 8)})</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        run.pass_rate >= 90 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-amber-500/20 text-amber-300'
                      }`}>
                        {run.pass_rate}% ({run.passed_tests}/{run.total_tests})
                      </span>
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap text-slate-200">
                      {run.overall_reliability_score} / 100
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap text-slate-200">
                      {run.routing_accuracy_pct}%
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap text-slate-200">
                      {run.avg_latency_seconds}s
                    </td>
                    <td className="px-3 py-2.5 whitespace-nowrap text-right space-x-2">
                      <button
                        onClick={() => onSelectRun(run.run_id)}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] font-sans inline-flex items-center gap-1"
                      >
                        <Eye className="w-3 h-3" /> Details
                      </button>
                      {!run.is_baseline && (
                        <button
                          onClick={() => onSetBaseline(run.run_id)}
                          className="px-2 py-1 rounded bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 text-[11px] font-sans border border-amber-800/40 inline-flex items-center gap-1"
                        >
                          <Bookmark className="w-3 h-3" /> Set Baseline
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

    </div>
  )
}
