import React, { useState } from 'react'
import {
  Sparkles, Play, Plus, RefreshCw, CheckCircle2,
  AlertCircle, Tag, Brain, Zap, Share2, LayoutDashboard
} from 'lucide-react'
import { getCategoryName, getCategoryBadgeColor } from '../lib/utils'

export default function AiGeneratorTab({
  onGenerateTests,
  isGenerating,
  generatedTests,
  onRunGeneratedTest,
  onSaveToSuite
}) {
  const [category, setCategory] = useState('metrics_fast')
  const [difficulty, setDifficulty] = useState('intermediate')
  const [intent, setIntent] = useState('Test boundary cases comparing Lookerwood Farm and Lookup Battle Royale with unexpected timeframe filters and platform breakdowns.')
  const [count, setCount] = useState(3)
  const [savedSuccess, setSavedSuccess] = useState(false)

  const handleGenerate = () => {
    if (!intent.trim()) return
    onGenerateTests({
      category,
      difficulty,
      intent,
      count
    })
  }

  const handleSaveAll = () => {
    if (onSaveToSuite && generatedTests.length > 0) {
      onSaveToSuite(generatedTests)
      setSavedSuccess(true)
      setTimeout(() => setSavedSuccess(false), 2500)
    }
  }

  return (
    <div className="space-y-6">
      
      {/* Generator Prompt Box */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400">
              <Sparkles className="w-4 h-4" />
            </span>
            <h2 className="text-sm font-bold text-white">Autonomous AI Test Case Synthesizer</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Generate new structured test cases dynamically using Gemini 3.5. Specify custom testing goals, adversarial edge cases, or specific schema requirements.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Target Conversation Type:
            </label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="metrics_fast">Quantitative Metrics (Looker)</option>
              <option value="social_graph">Social Graph & Clans (Spanner)</option>
              <option value="dashboard_builder">Dashboard Architect (MCP)</option>
              <option value="deep_research">Deep Research (Cross-Domain)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Difficulty Tier:
            </label>
            <select
              value={difficulty}
              onChange={(e) => setDifficulty(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="basic">Basic / Standard</option>
              <option value="intermediate">Intermediate (Multi-dimension / Filters)</option>
              <option value="advanced">Advanced (Multi-metric / Layouts / Whales)</option>
              <option value="adversarial">Adversarial (Edge cases / Ambiguity / Typos)</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              Number of Test Cases:
            </label>
            <select
              value={count}
              onChange={(e) => setCount(parseInt(e.target.value))}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="1">1 Test Case</option>
              <option value="3">3 Test Cases</option>
              <option value="5">5 Test Cases</option>
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-1.5">
            Testing Goal & Prompt Requirements:
          </label>
          <textarea
            rows={3}
            value={intent}
            onChange={(e) => setIntent(e.target.value)}
            placeholder="Describe what capabilities, schema fields, or edge cases you want to stress test..."
            className="w-full p-3 bg-slate-950 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500 font-mono leading-relaxed"
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <span>Presets:</span>
            <button
              onClick={() => setIntent("Test country breakdown with DE and JP filters and verify Looker explore link formatting.")}
              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]"
            >
              Country Filters
            </button>
            <button
              onClick={() => setIntent("Stress test clan friendship network retrieval with non-existent clan name to check graceful handling.")}
              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]"
            >
              Missing Clan Fallback
            </button>
            <button
              onClick={() => setIntent("Test creating a 4-tile LiveOps dashboard with DAU bar chart and IAP revenue single value KPI.")}
              className="px-2 py-0.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px]"
            >
              Dashboard 4-Tile
            </button>
          </div>

          <button
            onClick={handleGenerate}
            disabled={isGenerating || !intent.trim()}
            className={`px-5 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg transition-all ${
              isGenerating || !intent.trim()
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/25 active:scale-95'
            }`}
          >
            {isGenerating ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Synthesizing Tests with Gemini...
              </>
            ) : (
              <>
                <Sparkles className="w-3.5 h-3.5" />
                Generate {count} Tests
              </>
            )}
          </button>
        </div>
      </div>

      {/* Generated Tests Output Cards */}
      {generatedTests && generatedTests.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Generated Test Suite ({generatedTests.length} cases)
            </h3>

            <div className="flex items-center gap-2">
              {savedSuccess && (
                <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" /> Saved to Suite!
                </span>
              )}
              <button
                onClick={handleSaveAll}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-medium flex items-center gap-1.5"
              >
                <Plus className="w-3.5 h-3.5 text-cyan-400" />
                Save All to Suite
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {generatedTests.map((tc, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-900/90 border border-slate-800 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${getCategoryBadgeColor(tc.category)}`}>
                      {getCategoryName(tc.category)}
                    </span>
                    <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-400 text-[10px] uppercase font-mono">
                      {tc.difficulty}
                    </span>
                    <h4 className="text-xs font-bold text-white">{tc.title}</h4>
                  </div>

                  <button
                    onClick={() => onRunGeneratedTest(tc)}
                    className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-sm"
                  >
                    <Play className="w-3 h-3 fill-current" />
                    Run Now
                  </button>
                </div>

                <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 font-mono text-xs text-slate-200">
                  "{tc.prompt}"
                </div>

                <p className="text-[11px] text-slate-400">
                  {tc.description}
                </p>

                <div className="flex flex-wrap items-center gap-2 pt-1 text-[11px] text-slate-400">
                  <span>Expected Subagent: <strong className="text-cyan-300 font-mono">{tc.expected_subagent}</strong></span>
                  {tc.expected_artifacts?.table_required && <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">📊 Table</span>}
                  {tc.expected_artifacts?.chart_required && <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">📈 Chart</span>}
                  {tc.expected_artifacts?.graph_required && <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">🕸️ Force Graph</span>}
                  {tc.expected_artifacts?.link_required && <span className="px-1.5 py-0.2 rounded bg-slate-800 text-slate-300">🔗 Link</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
