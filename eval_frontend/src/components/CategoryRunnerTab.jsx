import React, { useState } from 'react'
import {
  Zap, Share2, LayoutDashboard, Brain, Play, CheckCircle2,
  XCircle, Clock, AlertCircle, ChevronDown, ChevronUp, Tag,
  Search, Filter, RefreshCw, Sparkles, MessageSquareQuote, CheckSquare, Square
} from 'lucide-react'
import VisualArtifactViewer from './VisualArtifactViewer'
import { getCategoryBadgeColor, getCategoryName } from '../lib/utils'

export default function CategoryRunnerTab({
  testSuites,
  activeCategoryFilter,
  setActiveCategoryFilter,
  onRunSingleTest,
  onRunCategorySuite,
  runningTestIds,
  testResultsMap,
  liveStreamingData
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('ALL') // 'ALL', 'PASSED', 'FAILED', 'RUNNING'
  const [expandedTestIds, setExpandedTestIds] = useState({})
  const [selectedTestIds, setSelectedTestIds] = useState({})

  // Category Tab configurations
  const categoryTabs = [
    { id: 'ALL', name: 'All Test Cases', icon: Sparkles, count: testSuites?.all_tests?.length || 0 },
    { id: 'metrics_fast', name: 'Looker Metrics', icon: Zap, count: testSuites?.metrics_tests?.length || 0 },
    { id: 'social_graph', name: 'Spanner Social Graph', icon: Share2, count: testSuites?.social_tests?.length || 0 },
    { id: 'dashboard_builder', name: 'Dashboard Architect', icon: LayoutDashboard, count: testSuites?.dashboard_tests?.length || 0 },
    { id: 'deep_research', name: 'Deep Research', icon: Brain, count: testSuites?.deep_research_tests?.length || 0 },
    { id: 'custom', name: 'Custom & AI Generated', icon: Sparkles, count: testSuites?.custom_tests?.length || 0 }
  ]

  // Filter test cases
  let displayedTests = testSuites?.all_tests || []
  if (activeCategoryFilter !== 'ALL') {
    if (activeCategoryFilter === 'custom') {
      displayedTests = testSuites?.custom_tests || []
    } else {
      displayedTests = displayedTests.filter(t => t.category === activeCategoryFilter)
    }
  }

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase()
    displayedTests = displayedTests.filter(t =>
      t.title?.toLowerCase().includes(q) ||
      t.prompt?.toLowerCase().includes(q) ||
      t.tags?.some(tag => tag.toLowerCase().includes(q))
    )
  }

  if (statusFilter !== 'ALL') {
    displayedTests = displayedTests.filter(t => {
      const res = testResultsMap[t.id]
      const isRunning = runningTestIds[t.id]
      if (statusFilter === 'RUNNING') return isRunning
      if (statusFilter === 'PASSED') return res?.rubric?.is_passed
      if (statusFilter === 'FAILED') return res && !res.rubric?.is_passed
      return true
    })
  }

  const toggleExpand = (id) => {
    setExpandedTestIds(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const toggleSelect = (id) => {
    setSelectedTestIds(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const handleSelectAll = () => {
    const next = {}
    displayedTests.forEach(t => { next[t.id] = true })
    setSelectedTestIds(next)
  }

  const handleClearSelection = () => {
    setSelectedTestIds({})
  }

  const selectedCount = Object.values(selectedTestIds).filter(Boolean).length

  return (
    <div className="space-y-5">
      
      {/* Category Navigation Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {categoryTabs.map(tab => {
          const Icon = tab.icon
          const isActive = activeCategoryFilter === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => setActiveCategoryFilter(tab.id)}
              className={`px-3.5 py-2 rounded-xl text-xs font-semibold flex items-center gap-2 transition-all whitespace-nowrap border ${
                isActive
                  ? 'bg-slate-800 text-cyan-400 border-slate-700 shadow-md ring-1 ring-cyan-500/20'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800/80 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.name}</span>
              <span className={`px-1.5 py-0.2 rounded-full text-[10px] font-mono ${
                isActive ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-500'
              }`}>
                {tab.count}
              </span>
            </button>
          )
        })}
      </div>

      {/* Action Controls & Filter Toolbar */}
      <div className="p-3.5 rounded-xl bg-slate-900/90 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-3 shadow-sm">
        
        {/* Left: Search & Status Filter */}
        <div className="flex items-center gap-2.5 flex-1">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search test prompt, title, tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-8 pr-3 py-1.5 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 transition-colors"
            />
          </div>

          <div className="flex items-center gap-1 text-xs">
            <Filter className="w-3.5 h-3.5 text-slate-500 ml-1" />
            {['ALL', 'PASSED', 'FAILED', 'RUNNING'].map(st => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
                  statusFilter === st
                    ? 'bg-slate-800 text-slate-200 border border-slate-700'
                    : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {st}
              </button>
            ))}
          </div>
        </div>

        {/* Right: Suite Execution Buttons */}
        <div className="flex items-center gap-2">
          {selectedCount > 0 && (
            <button
              onClick={() => onRunCategorySuite(Object.keys(selectedTestIds).filter(id => selectedTestIds[id]))}
              className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
            >
              <Play className="w-3 h-3 fill-current" />
              Run {selectedCount} Selected
            </button>
          )}

          <button
            onClick={() => onRunCategorySuite(activeCategoryFilter)}
            className="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-all"
          >
            <Play className="w-3 h-3 fill-current text-cyan-400" />
            Run {activeCategoryFilter === 'ALL' ? 'All 15 Tests' : `${getCategoryName(activeCategoryFilter)} Suite`}
          </button>
        </div>
      </div>

      {/* Test Cases List */}
      <div className="space-y-3">
        {displayedTests.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-900/60 border border-slate-800 text-slate-400 text-xs">
            No test cases found matching the criteria.
          </div>
        ) : (
          displayedTests.map(tc => {
            const isRunning = runningTestIds[tc.id]
            const result = testResultsMap[tc.id]
            const liveData = liveStreamingData[tc.id]
            const isExpanded = expandedTestIds[tc.id] || isRunning
            const isSelected = selectedTestIds[tc.id]

            return (
              <TestCard
                key={tc.id}
                testCase={tc}
                result={result}
                liveData={liveData}
                isRunning={isRunning}
                isExpanded={isExpanded}
                isSelected={isSelected}
                onToggleExpand={() => toggleExpand(tc.id)}
                onToggleSelect={() => toggleSelect(tc.id)}
                onRunTest={() => onRunSingleTest(tc)}
              />
            )
          })
        )}
      </div>

    </div>
  )
}

function TestCard({
  testCase,
  result,
  liveData,
  isRunning,
  isExpanded,
  isSelected,
  onToggleExpand,
  onToggleSelect,
  onRunTest
}) {
  const badgeColor = getCategoryBadgeColor(testCase.category)
  const isPassed = result?.rubric?.is_passed
  const hasExecuted = Boolean(result)

  return (
    <div className={`rounded-xl border transition-all overflow-hidden ${
      isRunning
        ? 'bg-slate-900/95 border-cyan-500/60 ring-1 ring-cyan-500/30 shadow-lg'
        : hasExecuted
          ? isPassed
            ? 'bg-slate-900/80 border-slate-800/90 hover:border-slate-700'
            : 'bg-slate-900/90 border-rose-900/40 hover:border-rose-700/50'
          : 'bg-slate-900/60 border-slate-800/70 hover:border-slate-700'
    }`}>
      
      {/* Test Card Header Row */}
      <div className="p-3.5 flex items-center justify-between gap-3">
        
        {/* Checkbox & Title */}
        <div className="flex items-center gap-3 min-w-0 flex-1">
          <button
            onClick={onToggleSelect}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            {isSelected ? (
              <CheckSquare className="w-4 h-4 text-cyan-400" />
            ) : (
              <Square className="w-4 h-4" />
            )}
          </button>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <span className={`px-2 py-0.5 rounded-md text-[10px] font-medium border ${badgeColor}`}>
                {getCategoryName(testCase.category)}
              </span>

              <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px] uppercase font-mono">
                {testCase.difficulty}
              </span>

              <h4 className="text-xs font-bold text-white truncate">
                {testCase.title}
              </h4>
            </div>

            <div className="text-[11px] text-slate-400 font-mono truncate">
              "{testCase.prompt}"
            </div>
          </div>
        </div>

        {/* Status, Latency & Actions */}
        <div className="flex items-center gap-3 shrink-0">
          
          {/* Status Badge */}
          {isRunning ? (
            <div className="px-2.5 py-1 rounded-md bg-cyan-950/60 border border-cyan-800/60 text-cyan-300 text-xs font-medium flex items-center gap-1.5 animate-pulse">
              <RefreshCw className="w-3 h-3 animate-spin" />
              Evaluating...
            </div>
          ) : hasExecuted ? (
            <div className={`px-2.5 py-1 rounded-md text-xs font-semibold flex items-center gap-1.5 border ${
              isPassed
                ? 'bg-emerald-950/40 border-emerald-800/50 text-emerald-300'
                : 'bg-rose-950/40 border-rose-800/50 text-rose-300'
            }`}>
              {isPassed ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> : <XCircle className="w-3.5 h-3.5 text-rose-400" />}
              <span>{isPassed ? 'PASSED' : 'FAILED'}</span>
              <span className="text-[10px] font-mono opacity-80">({result.rubric.overall_score})</span>
            </div>
          ) : (
            <span className="text-[11px] text-slate-500 font-mono">IDLE</span>
          )}

          {/* Latency */}
          {result?.duration_seconds > 0 && (
            <span className="text-[11px] font-mono text-slate-400 flex items-center gap-1">
              <Clock className="w-3 h-3 text-slate-500" />
              {result.duration_seconds}s
            </span>
          )}

          {/* Run Single Button */}
          <button
            onClick={onRunTest}
            disabled={isRunning}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-cyan-300 transition-colors border border-slate-700"
            title="Execute this test"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
          </button>

          {/* Expand Accordion Button */}
          <button
            onClick={onToggleExpand}
            className="p-1.5 rounded-lg bg-slate-800/50 hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>

      </div>

      {/* Expanded Details Pane */}
      {isExpanded && (
        <div className="px-4 pb-4 pt-2 border-t border-slate-800/80 bg-slate-950/60 space-y-4">
          
          {/* Subagent Routing Banner */}
          <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Expected Subagent:</span>
              <span className="font-mono text-cyan-300">{testCase.expected_subagent}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-slate-400">Routed Subagent:</span>
              <span className={`font-mono font-semibold ${
                (result?.routed_subagent || liveData?.routed_subagent) === testCase.expected_subagent
                  ? 'text-emerald-400'
                  : 'text-amber-400'
              }`}>
                {result?.routed_subagent || liveData?.routed_subagent || 'Routing pending...'}
              </span>
            </div>
          </div>

          {/* Live Streaming Thoughts Timeline */}
          {((liveData?.thoughts && liveData.thoughts.length > 0) || (result?.thoughts && result.thoughts.length > 0)) && (
            <div className="p-3 rounded-lg bg-slate-900/70 border border-slate-800 space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <Brain className="w-3.5 h-3.5 text-purple-400" />
                Live Agent Reasoning Thoughts ({((result?.thoughts || liveData?.thoughts) || []).length} steps)
              </div>
              <div className="space-y-1 max-h-36 overflow-y-auto font-mono text-[11px] text-slate-300 pr-1">
                {(result?.thoughts || liveData?.thoughts || []).map((t, idx) => (
                  <div key={idx} className="flex items-start gap-2 text-slate-300">
                    <span className="text-slate-500 shrink-0">[{idx + 1}]</span>
                    <span className="text-slate-300">{t}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Agent Response Text */}
          {(result?.response_text || liveData?.text) && (
            <div className="p-3.5 rounded-lg bg-slate-900/80 border border-slate-800 space-y-1.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquareQuote className="w-3.5 h-3.5 text-cyan-400" />
                Agent Output Text
              </div>
              <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                {result?.response_text || liveData?.text}
              </div>
            </div>
          )}

          {/* Rendered Visual Artifacts */}
          <VisualArtifactViewer
            visualArtifacts={result?.visual_artifacts || liveData?.visual_artifacts}
            responseText={result?.response_text || liveData?.text}
          />

          {/* Rubric Evaluation Scorecard & LLM Judge Feedback */}
          {result?.rubric && (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold text-slate-200 flex items-center gap-2">
                  <CheckCircle2 className="w-4 h-4 text-cyan-400" />
                  Argus QA Rubric & LLM-as-Judge Evaluation Report
                </div>
                <div className="flex items-center gap-2 font-mono text-xs">
                  <span>Score:</span>
                  <strong className={`text-sm ${isPassed ? 'text-emerald-400' : 'text-rose-400'}`}>
                    {result.rubric.overall_score} / 100
                  </strong>
                </div>
              </div>

              {/* 5-Score Radar Bars */}
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 pt-1 text-[11px]">
                <ScorePill label="Routing (30%)" score={result.rubric.routing_score} />
                <ScorePill label="Schema (25%)" score={result.rubric.schema_score} />
                <ScorePill label="Accuracy (25%)" score={result.rubric.accuracy_score} />
                <ScorePill label="Visuals (15%)" score={result.rubric.visual_score} />
                <ScorePill label="Latency (5%)" score={result.rubric.latency_score} />
              </div>

              {/* Judge Rationale & Issues */}
              {result.rubric.judge_rationale && (
                <div className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-1">
                  <span className="font-semibold text-slate-400 text-[10px] uppercase">Judge Rationale:</span>
                  <p className="text-slate-300 leading-relaxed">{result.rubric.judge_rationale}</p>
                </div>
              )}

              {result.rubric.issues_detected?.length > 0 && (
                <div className="p-2.5 rounded-lg bg-rose-950/30 border border-rose-900/40 text-xs space-y-1">
                  <span className="font-semibold text-rose-400 text-[10px] uppercase flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" /> Issues Detected:
                  </span>
                  <ul className="list-disc list-inside text-rose-200 space-y-0.5 text-[11px]">
                    {result.rubric.issues_detected.map((iss, i) => (
                      <li key={i}>{iss}</li>
                    ))}
                  </ul>
                </div>
              )}

              {result.rubric.suggestions?.length > 0 && (
                <div className="p-2.5 rounded-lg bg-cyan-950/30 border border-cyan-900/40 text-xs space-y-1">
                  <span className="font-semibold text-cyan-400 text-[10px] uppercase flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Actionable Recommendations:
                  </span>
                  <ul className="list-disc list-inside text-cyan-200 space-y-0.5 text-[11px]">
                    {result.rubric.suggestions.map((sug, i) => (
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
}

function ScorePill({ label, score }) {
  const isHigh = score >= 80
  return (
    <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 flex flex-col justify-between">
      <span className="text-slate-400 text-[10px] truncate">{label}</span>
      <span className={`font-bold font-mono text-xs mt-1 ${isHigh ? 'text-emerald-400' : 'text-amber-400'}`}>
        {score}
      </span>
    </div>
  )
}
