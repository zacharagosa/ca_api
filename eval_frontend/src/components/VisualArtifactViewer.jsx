import React, { useState, useEffect, useRef } from 'react'
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar,
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts'
import { Table, BarChart3, Network, ExternalLink, LayoutDashboard, Copy, Check } from 'lucide-react'
import { formatCurrency, formatNumber } from '../lib/utils'

export default function VisualArtifactViewer({ visualArtifacts, responseText }) {
  const [copied, setCopied] = useState(false)
  const fgRef = useRef(null)

  if (!visualArtifacts) return null

  const { table_data, chart_config, graph_data, explore_url, dashboard_info } = visualArtifacts

  const hasAnyArtifact = table_data || chart_config || graph_data || explore_url || dashboard_info

  if (!hasAnyArtifact) return null

  const handleCopyLink = (url) => {
    navigator.clipboard.writeText(url)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="mt-4 space-y-4 border-t border-slate-800/80 pt-4">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
        <BarChart3 className="w-3.5 h-3.5 text-cyan-400" />
        Rendered Visual Artifacts & Payloads
      </div>

      {/* 1. Explore / Embed Link */}
      {explore_url && (
        <div className="flex items-center justify-between p-3 rounded-lg bg-cyan-950/30 border border-cyan-800/40 text-cyan-200 text-xs">
          <div className="flex items-center gap-2 truncate">
            <ExternalLink className="w-4 h-4 text-cyan-400 shrink-0" />
            <span className="font-medium text-slate-300">Looker Explore Link:</span>
            <a
              href={explore_url}
              target="_blank"
              rel="noreferrer"
              className="truncate text-cyan-400 hover:underline hover:text-cyan-300 font-mono"
            >
              {explore_url}
            </a>
          </div>
          <button
            onClick={() => handleCopyLink(explore_url)}
            className="px-2 py-1 ml-2 rounded bg-cyan-900/60 hover:bg-cyan-800 text-cyan-300 flex items-center gap-1 shrink-0"
          >
            {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      )}

      {/* 2. Dashboard Created / Modified Info */}
      {dashboard_info && (
        <div className="p-3.5 rounded-lg bg-sky-950/30 border border-sky-800/40 text-sky-200 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 font-semibold text-sky-300">
              <LayoutDashboard className="w-4 h-4 text-sky-400" />
              Looker LiveOps Dashboard Created/Updated
            </div>
            <span className="px-2 py-0.5 rounded bg-sky-500/20 text-sky-300 text-[10px] font-mono">
              ID: {dashboard_info.id || 'live-dash'}
            </span>
          </div>
          <div className="text-slate-300">{dashboard_info.title || 'LiveOps War Room'}</div>
          {dashboard_info.tiles && (
            <div className="flex flex-wrap gap-1.5 pt-1">
              {dashboard_info.tiles.map((t, idx) => (
                <span key={idx} className="px-2 py-0.5 rounded bg-slate-800/80 text-slate-300 text-[11px] border border-slate-700">
                  🗂️ {typeof t === 'string' ? t : t.title || `Tile ${idx + 1}`}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 3. Recharts / Chart Config */}
      {chart_config && (
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-inner">
          <div className="flex items-center justify-between mb-3">
            <div className="text-xs font-medium text-slate-300 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan-400" />
              {chart_config.title || 'Dynamic Metric Visualization'}
            </div>
            <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              {chart_config.type || 'chart'}
            </span>
          </div>
          <div className="h-56 w-full">
            <RenderDynamicChart config={chart_config} />
          </div>
        </div>
      )}

      {/* 4. Spanner 2D Force-Directed Social Graph */}
      {graph_data && (
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-inner space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-xs font-medium text-purple-300 flex items-center gap-2">
              <Network className="w-4 h-4 text-purple-400" />
              Spanner Clan & Friendship Network Graph
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30">
              {(graph_data.nodes || []).length} nodes | {(graph_data.links || []).length} edges
            </span>
          </div>
          <div className="h-64 w-full bg-slate-950 rounded-lg overflow-hidden border border-slate-800 relative flex items-center justify-center">
            <NetworkGraphViewer graphData={graph_data} />
          </div>
        </div>
      )}

      {/* 5. Structured Data Table */}
      {table_data && (
        <div className="p-4 rounded-xl bg-slate-900/80 border border-slate-800 shadow-inner space-y-2">
          <div className="flex items-center justify-between mb-1">
            <div className="text-xs font-medium text-slate-300 flex items-center gap-2">
              <Table className="w-4 h-4 text-amber-400" />
              Structured LookML Data Table
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              {(table_data.rows || []).length} rows
            </span>
          </div>
          <div className="overflow-x-auto max-h-56 rounded-lg border border-slate-800">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-800/80 text-slate-400 uppercase text-[10px] tracking-wider sticky top-0">
                <tr>
                  {(table_data.fields || Object.keys(table_data.rows?.[0] || {})).map((f, i) => (
                    <th key={i} className="px-3 py-2 border-b border-slate-700 font-semibold truncate">
                      {typeof f === 'object' ? (f.label || f.name) : f}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {(table_data.rows || []).slice(0, 10).map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-800/40 transition-colors">
                    {Object.values(row).map((val, cIdx) => (
                      <td key={cIdx} className="px-3 py-1.5 whitespace-nowrap text-slate-200">
                        {typeof val === 'number'
                          ? (val > 1000 ? formatNumber(val) : val)
                          : String(val ?? '-')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {(table_data.rows || []).length > 10 && (
            <div className="text-[10px] text-slate-500 text-right pr-1">
              Showing top 10 of {(table_data.rows || []).length} rows
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RenderDynamicChart({ config }) {
  if (!config || !config.data || config.data.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-xs text-slate-500">
        No chart data points available
      </div>
    )
  }

  const data = config.data
  const xAxisKey = config.xAxisKey || 'date' || Object.keys(data[0])[0]
  const series = config.series || [{ name: 'Value', dataKey: Object.keys(data[0]).find(k => k !== xAxisKey) || 'value', strokeColor: '#38bdf8' }]

  if (config.type === 'bar') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey={xAxisKey} stroke="#64748b" fontSize={10} tickLine={false} />
          <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
          <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
          {series.map((s, idx) => (
            <Bar key={idx} dataKey={s.dataKey} name={s.name || s.dataKey} fill={s.fillColor || s.strokeColor || '#38bdf8'} radius={[4, 4, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    )
  }

  if (config.type === 'area') {
    return (
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
          <XAxis dataKey={xAxisKey} stroke="#64748b" fontSize={10} tickLine={false} />
          <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
          <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
          {series.map((s, idx) => (
            <Area
              key={idx}
              type="monotone"
              dataKey={s.dataKey}
              name={s.name || s.dataKey}
              stroke={s.strokeColor || '#38bdf8'}
              fill={s.fillColor || 'rgba(56, 189, 248, 0.2)'}
              stackId={config.stacked ? "1" : undefined}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    )
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
        <XAxis dataKey={xAxisKey} stroke="#64748b" fontSize={10} tickLine={false} />
        <YAxis stroke="#64748b" fontSize={10} tickLine={false} />
        <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }} />
        <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
        {series.map((s, idx) => (
          <Line
            key={idx}
            type="monotone"
            dataKey={s.dataKey}
            name={s.name || s.dataKey}
            stroke={s.strokeColor || '#38bdf8'}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}

function NetworkGraphViewer({ graphData }) {
  const [ForceGraph, setForceGraph] = useState(null)

  useEffect(() => {
    import('react-force-graph-2d').then(mod => {
      setForceGraph(() => mod.default || mod.ForceGraph2D)
    }).catch(err => {
      console.warn("ForceGraph2D load warning:", err)
    })
  }, [])

  if (!ForceGraph) {
    return (
      <div className="flex flex-col items-center justify-center p-4 text-center">
        <Network className="w-8 h-8 text-purple-400 mb-2 animate-pulse" />
        <div className="text-xs text-purple-300 font-medium">Clan & Friendship Network Active</div>
        <div className="text-[11px] text-slate-400 mt-1">
          {graphData.nodes?.length || 0} players & clans linked across {graphData.links?.length || 0} connections
        </div>
      </div>
    )
  }

  return (
    <ForceGraph
      graphData={graphData}
      width={600}
      height={250}
      nodeLabel="id"
      nodeColor={node => node.group === 'clan' ? '#a855f7' : '#38bdf8'}
      nodeRelSize={6}
      linkColor={() => '#475569'}
      linkWidth={1.5}
      backgroundColor="#020617"
    />
  )
}
