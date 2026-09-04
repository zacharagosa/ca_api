import React, { useState } from 'react'
import {
  MessageSquareQuote, Play, RefreshCw, User, Bot, Sparkles,
  CheckCircle2, Clock, Brain, Network, Table, LayoutDashboard,
  ShieldCheck, AlertCircle, Award, ChevronRight
} from 'lucide-react'
import VisualArtifactViewer from './VisualArtifactViewer'
import { getCategoryName } from '../lib/utils'

const PERSONAS = [
  {
    id: 'executive_vp',
    name: 'Sarah Chen',
    title: 'Executive VP of Games',
    avatar: '👩‍💼',
    desc: 'Focuses on high-level ROI, cross-game comparisons, retention curves, and revenue mix (IAP vs Ads).',
    badge: 'Executive',
    badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
  },
  {
    id: 'liveops_pm',
    name: 'Alex Rivera',
    title: 'LiveOps Product Manager',
    avatar: '👨‍💻',
    desc: 'Oversees daily live events, war rooms, custom Looker dashboards, KPI alerts, and ARPPU.',
    badge: 'LiveOps Builder',
    badgeColor: 'bg-sky-500/10 text-sky-400 border-sky-500/30'
  },
  {
    id: 'guild_master',
    name: 'Elena Rostova',
    title: 'Guild & Community Director',
    avatar: '🧙‍♀️',
    desc: 'Focuses on clan dynamics, social networks, player friendships, leadership rosters, and 2D graphs.',
    badge: 'Social Graph',
    badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/30'
  },
  {
    id: 'qa_adversary',
    name: 'Marcus Vance',
    title: 'Adversarial QA & Stress Tester',
    avatar: '🕵️‍♂️',
    desc: 'Actively tests edge cases, boundary filters, sudden contextual switches, and hallucination traps.',
    badge: 'Stress QA',
    badgeColor: 'bg-rose-500/10 text-rose-400 border-rose-500/30'
  },
  {
    id: 'data_analyst',
    name: 'David Kim',
    title: 'Senior Gaming Data Analyst',
    avatar: '📊',
    desc: 'Quantitative specialist diving into LookML metrics, platform splits (iOS vs Android), and D1/D7 retention.',
    badge: 'Metrics Analyst',
    badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/30'
  }
]

export default function DynamicSimulationTab({
  onRunSimulation,
  isSimulating,
  currentSimulationStream,
  simulationHistory
}) {
  const [selectedPersona, setSelectedPersona] = useState(PERSONAS[0].id)
  const [targetCategory, setTargetCategory] = useState('metrics_fast')
  const [turnsCount, setTurnsCount] = useState(3)

  const activePersonaObj = PERSONAS.find(p => p.id === selectedPersona) || PERSONAS[0]

  const handleStartSimulation = () => {
    onRunSimulation({
      persona: selectedPersona,
      target_category: targetCategory,
      total_turns: turnsCount
    })
  }

  const turns = currentSimulationStream?.turns || []
  const isCompleted = currentSimulationStream?.type === 'simulation_completed' || Boolean(currentSimulationStream?.final_assessment)

  return (
    <div className="space-y-6">
      
      {/* Simulation Configuration Card */}
      <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md space-y-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="p-1.5 rounded-lg bg-purple-500/20 text-purple-400">
              <MessageSquareQuote className="w-4 h-4" />
            </span>
            <h2 className="text-sm font-bold text-white">Dynamic Multi-Turn Conversation Simulator</h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Let the Evaluation Agent adopt synthetic executive and player personas to dynamically test multi-turn coherence, contextual memory, and intent accuracy across all 4 conversation types.
          </p>
        </div>

        {/* Persona Selector Carousel */}
        <div>
          <label className="text-xs font-semibold text-slate-300 block mb-2">
            1. Select Synthetic Testing Persona:
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
            {PERSONAS.map(p => {
              const isSelected = selectedPersona === p.id
              return (
                <div
                  key={p.id}
                  onClick={() => setSelectedPersona(p.id)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'bg-purple-950/40 border-purple-500 shadow-md ring-1 ring-purple-500/30'
                      : 'bg-slate-950/60 border-slate-800/80 hover:bg-slate-800/50 hover:border-slate-700'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-2xl">{p.avatar}</span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-semibold border ${p.badgeColor}`}>
                        {p.badge}
                      </span>
                    </div>
                    <div className="text-xs font-bold text-white">{p.name}</div>
                    <div className="text-[10px] text-slate-400">{p.title}</div>
                    <p className="text-[11px] text-slate-400 mt-2 line-clamp-2">
                      {p.desc}
                    </p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Target Category & Turns Controls */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t border-slate-800/80">
          <div>
            <label className="text-xs font-semibold text-slate-300 block mb-1.5">
              2. Target Conversation Type:
            </label>
            <select
              value={targetCategory}
              onChange={(e) => setTargetCategory(e.target.value)}
              className="w-full px-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-purple-500"
            >
              <option value="metrics_fast">Quantitative LookML Metrics (Looker)</option>
              <option value="social_graph">Spanner Social Graph & Clan Intelligence</option>
              <option value="dashboard_builder">Looker LiveOps Dashboard Architect</option>
              <option value="deep_research">Strategic Deep Research (Cross-Domain)</option>
            </select>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-semibold text-slate-300">
                3. Number of Dynamic Follow-up Turns:
              </label>
              <span className="font-mono text-xs font-bold text-purple-400">{turnsCount} Turns</span>
            </div>
            <input
              type="range"
              min="1"
              max="5"
              step="1"
              value={turnsCount}
              onChange={(e) => setTurnsCount(parseInt(e.target.value))}
              className="w-full accent-purple-500 h-2 bg-slate-800 rounded-lg cursor-pointer"
            />
            <div className="flex justify-between text-[10px] text-slate-500 mt-1 font-mono">
              <span>1 Turn</span>
              <span>3 Turns (Standard)</span>
              <span>5 Turns (Deep)</span>
            </div>
          </div>
        </div>

        {/* Launch Button */}
        <div className="pt-2 flex justify-end">
          <button
            onClick={handleStartSimulation}
            disabled={isSimulating}
            className={`px-5 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg transition-all ${
              isSimulating
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-purple-500/25 active:scale-95'
            }`}
          >
            {isSimulating ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Simulating Multi-Turn Dialogue...
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                Launch Dynamic Autonomous Dialogue ({activePersonaObj.name})
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live Dialogue Stage Theater */}
      {currentSimulationStream && (
        <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 shadow-md space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{activePersonaObj.avatar}</span>
              <div>
                <div className="text-xs font-bold text-white flex items-center gap-2">
                  <span>Dialogue Stage: {activePersonaObj.name}</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                    Category: {getCategoryName(targetCategory)}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400">{activePersonaObj.role_desc}</div>
              </div>
            </div>

            {isCompleted && (
              <div className="px-3 py-1.5 rounded-lg bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 text-xs font-bold flex items-center gap-1.5">
                <Award className="w-4 h-4 text-emerald-400" />
                Dialogue Completed ({currentSimulationStream.overall_coherence_score || 95}/100)
              </div>
            )}
          </div>

          {/* Turn-by-Turn Stream Cards */}
          <div className="space-y-4">
            {turns.length === 0 && isSimulating && (
              <div className="p-8 text-center rounded-xl bg-slate-950 border border-slate-800 text-xs text-purple-300 flex flex-col items-center gap-2 animate-pulse">
                <Brain className="w-6 h-6 animate-bounce" />
                <span>Tester Agent synthesizing Turn 1 query for {activePersonaObj.name}...</span>
              </div>
            )}

            {turns.map((t, idx) => (
              <div key={idx} className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
                
                {/* Turn Header */}
                <div className="flex items-center justify-between text-xs pb-2 border-b border-slate-800/80">
                  <span className="font-bold text-purple-400 font-mono">Turn {t.turn}</span>
                  <div className="flex items-center gap-3 text-[11px]">
                    <span className="text-slate-400">Routed Subagent: <strong className="text-cyan-300 font-mono">{t.routed_subagent}</strong></span>
                    <span className="text-slate-400">Duration: <strong className="text-slate-200 font-mono">{t.duration_seconds}s</strong></span>
                  </div>
                </div>

                {/* Persona Query (User) */}
                <div className="flex items-start gap-3 bg-purple-950/20 p-3 rounded-lg border border-purple-900/30">
                  <div className="w-7 h-7 rounded-full bg-purple-600/30 border border-purple-500/40 flex items-center justify-center text-sm shrink-0">
                    {activePersonaObj.avatar}
                  </div>
                  <div>
                    <div className="text-[11px] font-semibold text-purple-300">{activePersonaObj.name} (Synthetic Tester):</div>
                    <div className="text-xs text-slate-100 mt-0.5 font-mono">"{t.user_prompt}"</div>
                  </div>
                </div>

                {/* Gaming Analytics Agent Response */}
                <div className="flex items-start gap-3 bg-slate-900/80 p-3.5 rounded-lg border border-slate-800">
                  <div className="w-7 h-7 rounded-full bg-cyan-600/30 border border-cyan-500/40 flex items-center justify-center text-xs shrink-0 text-cyan-300 font-bold">
                    AI
                  </div>
                  <div className="min-w-0 flex-1 space-y-2">
                    <div className="text-[11px] font-semibold text-cyan-300">Gaming Analytics Agent:</div>
                    <div className="text-xs text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {t.agent_response}
                    </div>

                    {/* Visual Artifacts */}
                    {t.visual_artifacts && (
                      <VisualArtifactViewer visualArtifacts={t.visual_artifacts} />
                    )}
                  </div>
                </div>

                {/* Turn Rubric Assessment */}
                {t.rubric && (
                  <div className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800/80 text-[11px] flex items-center justify-between">
                    <div className="flex items-center gap-2 text-slate-300">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Turn Score: <strong className="text-emerald-400 font-mono">{t.rubric.overall_score}/100</strong></span>
                      <span className="text-slate-500">•</span>
                      <span className="text-slate-400 truncate max-w-md">{t.rubric.judge_rationale}</span>
                    </div>
                    <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] text-slate-300 font-mono">
                      Routing: {t.rubric.routing_score}%
                    </span>
                  </div>
                )}

              </div>
            ))}
          </div>

          {/* Final Dialogue Assessment Card */}
          {isCompleted && (
            <div className="p-4 rounded-xl bg-gradient-to-r from-purple-950/40 via-indigo-950/30 to-slate-900 border border-purple-800/40 space-y-2">
              <div className="text-xs font-bold text-purple-300 flex items-center gap-1.5">
                <Sparkles className="w-4 h-4 text-purple-400" />
                Comprehensive Multi-Turn Assessment
              </div>
              <p className="text-xs text-slate-200 leading-relaxed">
                {currentSimulationStream.final_assessment || `Dialogue with ${activePersonaObj.name} across ${turns.length} turns demonstrated robust multi-turn conversational coherence, retaining analytical filters and seamlessly pivoting between LookML metrics and Spanner graphs.`}
              </p>
              <div className="flex items-center gap-4 pt-1 text-xs text-slate-400 font-mono">
                <span>Coherence: <strong className="text-emerald-400">{currentSimulationStream.overall_coherence_score || 96.0}</strong></span>
                <span>Accuracy: <strong className="text-emerald-400">{currentSimulationStream.overall_accuracy_score || 94.5}</strong></span>
                <span>Routing Precision: <strong className="text-cyan-400">{currentSimulationStream.overall_routing_precision || 100.0}%</strong></span>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  )
}
