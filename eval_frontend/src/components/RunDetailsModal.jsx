import React, { useState, useEffect } from 'react'
import {
  X, CheckCircle2, XCircle, AlertCircle, Clock, ShieldCheck,
  Zap, Share2, LayoutDashboard, Brain, BarChart3, Search,
  Filter, Bookmark, ChevronDown, ChevronUp, Sparkles, MessageSquareQuote,
  ExternalLink, Table, Network, Copy, Check
} from 'lucide-react'
import VisualArtifactViewer from './VisualArtifactViewer'
import { getCategoryName, getCategoryBadgeColor, formatNumber } from '../lib/utils'

export default function RunDetailsModal({
  runDetails,
  isOpen,
  onClose,
  onSetBaseline
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL') // 'ALL', 'PASSED', 'FAILED'
  const [categoryFilter, setCategoryFilter] = useState('ALL')
  const [expandedTestIds, setExpandedTestIds] = useState({})

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
    }
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'hidden'
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [isOpen, onClose])

  if (!isOpen || !runDetails) return null

  const toggleExpand = (id) => {
    setExpandedTestIds(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const expandAll = () => {
    const next = {}
    ;(runDetails.results || []).forEach(r => { next[r.test_id] = true })
    setExpandedTestIds(next)
  }

  const collapseAll = () => {
    setExpandedTestIds({})
  }

  // Filter test results
  let filteredResults = runDetails.results || []

  if (categoryFilter !== 'ALL') {
    filteredResults = filteredResults.filter(r => r.category === categoryFilter)
  }

  if (statusFilter === 'PASSED') {
    filteredResults = filteredResults.filter(r => r.rubric?.is_passed)
  } else if (statusFilter === 'FAILED') {
    filteredResults = filteredResults.filter(r => !r.rubric?.is_passed)
  }

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase()
    filteredResults = filteredResults.filter(r =>
      r.test_title?.toLowerCase().includes(q) ||
      r.prompt?.toLowerCase().includes(q) ||
      r.routed_subagent?.toLowerCase().includes(q) ||
      r.response_text?.toLowerCase().includes(q)
    )
  }

  const startedTimeStr = runDetails.started_at
    ? new Date(runDetails.started_at * 1000).toLocaleString()
    : 'Recent Run'

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      
      {/* Modal Container */}
      <div className="relative w-full max-w-6xl max-h-[92vh] flex flex-col bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        
        {/* Modal Header */}
        <div className="p-5 border-b border-slate-800 bg-slate-900/95 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 to-blue-600 flex items-center justify-center text-white shadow-md shadow-cyan-500/20 shrink-0">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-base font-bold text-white truncate">
                  {runDetails.title || `Test Run Details (${runDetails.run_id})`}
                </h2>
                {runDetails.is_baseline && (
                  <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/40 text-[10px] font-bold uppercase tracking-wider">
                    Official Baseline
                  </span>
                )}
                <span className="text-[11px] font-mono text-slate-400">
                  ID: <span className="text-cyan-300">{runDetails.run_id}</span>
                </span>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-0.5">
                <span>Executed: <strong className="text-slate-300 font-normal">{startedTimeStr}</strong></span>
                <span>•</span>
                <span>Duration: <strong className="text-slate-300 font-mono font-normal">{runDetails.duration_seconds}s</strong></span>
                <span>•</span>
                <span>Model: <strong className="text-slate-300 font-mono font-normal">{runDetails.model_name || 'gemini-3.5-flash'}</strong></span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {!runDetails.is_baseline && onSetBaseline && (
              <button
                onClick={() => onSetBaseline(runDetails.run_id)}
                className="px-3 py-1.5 rounded-lg bg-amber-950/60 hover:bg-amber-900/80 text-amber-300 border border-amber-800/60 text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
              >
                <Bookmark className="w-3.5 h-3.5" />
                Set as Baseline
              </button>
            )}

            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-colors"
              title="Close modal (Esc)"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Content */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          
          {/* Top Scorecard Summary Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
              <span className="text-slate-400 text-[11px]">Pass Rate</span>
              <div className="flex items-baseline gap-1.5 mt-1">
                <span className={`text-xl font-bold font-mono ${
                  runDetails.pass_rate >= 90 ? 'text-emerald-400' : 'text-amber-400'
                }`}>
                  {runDetails.pass_rate}%
                </span>
                <span className="text-[10px] text-slate-500 font-mono">
                  ({runDetails.passed_tests}/{runDetails.total_tests})
                </span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
              <span className="text-slate-400 text-[11px]">Reliability Score</span>
              <div className="flex items-baseline gap-1 mt-1">
                <span className="text-xl font-bold text-white font-mono">
                  {runDetails.overall_reliability_score}
                </span>
                <span className="text-xs text-slate-500">/ 100</span>
              </div>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
              <span className="text-slate-400 text-[11px]">Routing Accuracy</span>
              <span className="text-xl font-bold text-purple-400 font-mono mt-1">
                {runDetails.routing_accuracy_pct}%
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
              <span className="text-slate-400 text-[11px]">Visual Payload Rate</span>
              <span className="text-xl font-bold text-amber-400 font-mono mt-1">
                {runDetails.visual_payload_rate_pct}%
              </span>
            </div>

            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col justify-between">
              <span className="text-slate-400 text-[11px]">Avg Stream Latency</span>
              <span className="text-xl font-bold text-sky-400 font-mono mt-1">
                {runDetails.avg_latency_seconds}s
              </span>
            </div>
          </div>

          {/* Category Breakdown Badges */}
          {runDetails.category_breakdown && (
            <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                Category Breakdown Performance
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                {Object.entries(runDetails.category_breakdown).map(([catKey, catData]) => (
                  <div key={catKey} className="p-3 rounded-lg bg-slate-900 border border-slate-800/80 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-slate-200">{getCategoryName(catKey)}</div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">
                        Avg Latency: {catData.avg_latency}s
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs font-bold text-emerald-400 font-mono">{catData.pass_rate}% Pass</div>
                      <div className="text-[10px] text-slate-400 font-mono">Score: {catData.avg_score}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Test Case Filtering & Search Toolbar */}
          <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-2 flex-1">
              <div className="relative flex-1 max-w-xs">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Search test prompt, title, routing..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-8 pr-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Status Filter */}
              <div className="flex items-center gap-1 text-xs">
                {['ALL', 'PASSED', 'FAILED'].map(st => (
                  <button
                    key={st}
                    onClick={() => setStatusFilter(st)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
                      statusFilter === st
                        ? 'bg-slate-800 text-cyan-300 border border-slate-700'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              {/* Category Filter */}
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="px-2.5 py-1 bg-slate-900 border border-slate-800 rounded-md text-xs text-slate-300 focus:outline-none focus:border-cyan-500"
              >
                <option value="ALL">All Categories</option>
                <option value="metrics_fast">Metrics Analyst</option>
                <option value="social_graph">Social Graph</option>
                <option value="dashboard_builder">Dashboard Architect</option>
                <option value="deep_research">Deep Research</option>
              </select>
            </div>

            <div className="flex items-center gap-2 text-xs">
              <span className="text-slate-400 text-[11px]">
                Showing <strong>{filteredResults.length}</strong> of {(runDetails.results || []).length} tests
              </span>
              <button
                onClick={expandAll}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px]"
              >
                Expand All
              </button>
              <button
                onClick={collapseAll}
                className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px]"
              >
                Collapse All
              </button>
            </div>
          </div>

          {/* Individual Test Results List */}
          <div className="space-y-3">
            {filteredResults.length === 0 ? (
              <div className="p-8 text-center rounded-xl bg-slate-950 border border-slate-800 text-slate-400 text-xs">
                No test results match the selected filter.
              </div>
            ) : (
              filteredResults.map(testRes => {
                const isExpanded = expandedTestIds[testRes.test_id]
                const isPassed = testRes.rubric?.is_passed
                const badgeColor = getCategoryBadgeColor(testRes.category)

                return (
                  <div
                    key={testRes.test_id}
                    className={`rounded-xl border transition-all overflow-hidden ${
                      isPassed
                        ? 'bg-slate-950/80 border-slate-800/90 hover:border-slate-700'
                        : 'bg-slate-950/90 border-rose-900/50 hover:border-rose-700/60'
                    }`}
                  >
                    {/* Test Card Header */}
                    <div
                      onClick={() => toggleExpand(testRes.test_id)}
                      className="p-3.5 flex items-center justify-between gap-3 cursor-pointer select-none"
                    >
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border shrink-0 ${badgeColor}`}>
                          {getCategoryName(testRes.category)}
                        </span>
                        <div className="min-w-0 flex-1">
                          <h4 className="text-xs font-bold text-white truncate">
                            {testRes.test_title}
                          </h4>
                          <div className="text-[11px] text-slate-400 font-mono truncate">
                            "{testRes.prompt}"
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-3 shrink-0">
                        <div className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 border ${
                          isPassed
                            ? 'bg-emerald-950/40 border-emerald-800/50 text-emerald-300'
                            : 'bg-rose-950/40 border-rose-800/50 text-rose-300'
                        }`}>
                          {isPassed ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-rose-400" />}
                          <span>{isPassed ? 'PASSED' : 'FAILED'}</span>
                          <span className="text-[10px] font-mono opacity-80">({testRes.rubric?.overall_score ?? 0})</span>
                        </div>

                        <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {testRes.duration_seconds}s
                        </span>

                        <span className="text-slate-400">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </span>
                      </div>
                    </div>

                    {/* Test Card Expanded Drawer */}
                    {isExpanded && (
                      <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/95 space-y-4">
                        
                        {/* Subagent Routing Info */}
                        <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900 border border-slate-800 text-xs">
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400">Expected Subagent:</span>
                            <span className="font-mono text-cyan-300">{testRes.expected_subagent}</span>
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-slate-400">Routed Subagent:</span>
                            <span className={`font-mono font-semibold ${
                              testRes.routed_subagent === testRes.expected_subagent
                                ? 'text-emerald-400'
                                : 'text-amber-400'
                            }`}>
                              {testRes.routed_subagent}
                            </span>
                          </div>
                        </div>

                        {/* Step-by-Step Reasoning Thoughts */}
                        {testRes.thoughts && testRes.thoughts.length > 0 && (
                          <div className="p-3 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5">
                            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                              <Brain className="w-3.5 h-3.5 text-purple-400" />
                              Agent Reasoning Steps ({testRes.thoughts.length} thoughts)
                            </div>
                            <div className="space-y-1 max-h-36 overflow-y-auto font-mono text-[11px] text-slate-300 pr-1">
                              {testRes.thoughts.map((th, idx) => (
                                <div key={idx} className="flex items-start gap-2 text-slate-300">
                                  <span className="text-slate-500 shrink-0">[{idx + 1}]</span>
                                  <span>{th}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Agent Output Text */}
                        {testRes.response_text && (
                          <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-1.5">
                            <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                              <MessageSquareQuote className="w-3.5 h-3.5 text-cyan-400" />
                              Agent Output Text
                            </div>
                            <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                              {testRes.response_text}
                            </div>
                          </div>
                        )}

                        {/* Visual Artifacts */}
                        <VisualArtifactViewer
                          visualArtifacts={testRes.visual_artifacts}
                          responseText={testRes.response_text}
                        />

                        {/* Rubric Evaluation Report */}
                        {testRes.rubric && (
                          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
                            <div className="flex items-center justify-between">
                              <div className="text-xs font-bold text-slate-200 flex items-center gap-2">
                                <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                                Argus 5-Point Evaluation Rubric Breakdown
                              </div>
                              <div className="flex items-center gap-2 font-mono text-xs">
                                <span>Composite Score:</span>
                                <strong className={`text-sm ${isPassed ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  {testRes.rubric.overall_score} / 100
                                </strong>
                              </div>
                            </div>

                            {/* 5 Dimensions Grid */}
                            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1 text-[11px]">
                              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                                <span className="text-slate-400 text-[10px]">Routing (30%)</span>
                                <span className={`font-bold font-mono text-xs mt-1 ${testRes.rubric.routing_score >= 80 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                  {testRes.rubric.routing_score}
                                </span>
                              </div>
                              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                                <span className="text-slate-400 text-[10px]">Schema (25%)</span>
                                <span className={`font-bold font-mono text-xs mt-1 ${testRes.rubric.schema_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                  {testRes.rubric.schema_score}
                                </span>
                              </div>
                              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                                <span className="text-slate-400 text-[10px]">Accuracy (25%)</span>
                                <span className={`font-bold font-mono text-xs mt-1 ${testRes.rubric.accuracy_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                  {testRes.rubric.accuracy_score}
                                </span>
                              </div>
                              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                                <span className="text-slate-400 text-[10px]">Visuals (15%)</span>
                                <span className={`font-bold font-mono text-xs mt-1 ${testRes.rubric.visual_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                  {testRes.rubric.visual_score}
                                </span>
                              </div>
                              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
                                <span className="text-slate-400 text-[10px]">Latency (5%)</span>
                                <span className={`font-bold font-mono text-xs mt-1 ${testRes.rubric.latency_score >= 80 ? 'text-emerald-400' : 'text-amber-400'}`}>
                                  {testRes.rubric.latency_score}
                                </span>
                              </div>
                            </div>

                            {/* Rationale */}
                            {testRes.rubric.judge_rationale && (
                              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-1">
                                <span className="font-semibold text-slate-400 text-[10px] uppercase">Judge Rationale:</span>
                                <p className="text-slate-300 leading-relaxed">{testRes.rubric.judge_rationale}</p>
                              </div>
                            )}

                            {/* Issues */}
                            {testRes.rubric.issues_detected?.length > 0 && (
                              <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-900/40 text-xs space-y-1">
                                <span className="font-semibold text-rose-400 text-[10px] uppercase flex items-center gap-1">
                                  <AlertCircle className="w-3 h-3" /> Issues Detected:
                                </span>
                                <ul className="list-disc list-inside text-rose-200 space-y-0.5 text-[11px]">
                                  {testRes.rubric.issues_detected.map((iss, i) => (
                                    <li key={i}>{iss}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {/* Suggestions */}
                            {testRes.rubric.suggestions?.length > 0 && (
                              <div className="p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-900/40 text-xs space-y-1">
                                <span className="font-semibold text-cyan-400 text-[10px] uppercase flex items-center gap-1">
                                  <Sparkles className="w-3 h-3" /> Recommendations:
                                </span>
                                <ul className="list-disc list-inside text-cyan-200 space-y-0.5 text-[11px]">
                                  {testRes.rubric.suggestions.map((sug, i) => (
                                    <li key={i}>{sug}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}

                      </div>
                    )}
                  </div>
                )
              })
            )}
          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/95 flex items-center justify-between text-xs text-slate-400">
          <div>
            Run ID: <span className="font-mono text-slate-200">{runDetails.run_id}</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold transition-colors"
          >
            Close Details
          </button>
        </div>

      </div>
    </div>
  )
}
