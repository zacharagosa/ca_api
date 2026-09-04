import React from 'react'
import {
  ShieldCheck, Activity, Play, MessageSquareQuote, Sparkles,
  History, Server, Zap, RefreshCw, Cpu
} from 'lucide-react'

export default function Header({
  activeTab,
  setActiveTab,
  systemStatus,
  onRunAllSuites,
  isRunningAll,
  onRefreshStatus
}) {
  const isBackendOnline = systemStatus?.gaming_backend?.status === 'online'
  const isEvalOnline = systemStatus?.status === 'healthy'

  return (
    <header className="sticky top-0 z-50 bg-slate-900/90 backdrop-blur-md border-b border-slate-800/80 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Logo & System Badges */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-sky-500 to-indigo-500 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-white/20">
            <ShieldCheck className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-base font-bold text-white tracking-tight flex items-center gap-1.5">
                Argus QA <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">Evaluation Agent</span>
              </h1>
              <span className="text-[11px] font-mono text-slate-400">v1.2</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-0.5">
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${isBackendOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
                <span>Agent (8080): <strong className={isBackendOnline ? 'text-emerald-400 font-normal' : 'text-rose-400'}>{isBackendOnline ? 'Online' : 'Offline'}</strong></span>
              </div>
              <span>•</span>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${isEvalOnline ? 'bg-cyan-400' : 'bg-rose-500'}`} />
                <span>Eval Engine (8085): <strong className="text-cyan-400 font-normal">{isEvalOnline ? 'Active' : 'Error'}</strong></span>
              </div>
              <span>•</span>
              <span className="font-mono text-slate-400">Dataset: <span className="text-sky-300">{systemStatus?.dataset || 'events'}</span></span>
            </div>
          </div>
        </div>

        {/* Global Quick Action Buttons */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={onRefreshStatus}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors border border-slate-700 text-xs flex items-center gap-1.5"
            title="Refresh System Status"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={() => setActiveTab('simulation')}
            className="px-3 py-2 rounded-lg bg-purple-950/60 hover:bg-purple-900/80 text-purple-200 border border-purple-800/60 text-xs font-medium flex items-center gap-1.5 transition-all shadow-sm"
          >
            <MessageSquareQuote className="w-3.5 h-3.5 text-purple-400" />
            Dynamic Simulation
          </button>

          <button
            onClick={onRunAllSuites}
            disabled={isRunningAll}
            className={`px-4 py-2 rounded-lg text-xs font-semibold flex items-center gap-2 transition-all shadow-lg ${
              isRunningAll
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                : 'bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-cyan-500/25 active:scale-95'
            }`}
          >
            {isRunningAll ? (
              <>
                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                Running All Suites...
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                Run Full Evaluation (4 Categories)
              </>
            )}
          </button>
        </div>
      </div>

      {/* Main Tabs Navigation */}
      <div className="max-w-7xl mx-auto flex items-center gap-1.5 mt-3 pt-2.5 border-t border-slate-800/60 overflow-x-auto text-xs">
        <NavTab
          id="overview"
          label="Overview & Regression Delta"
          icon={Activity}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
        <NavTab
          id="category_runner"
          label="Category Test Suites (4 Types)"
          icon={Zap}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          badge="15 Tests"
        />
        <NavTab
          id="simulation"
          label="Dynamic Persona Dialogue"
          icon={MessageSquareQuote}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          badge="Synthetic Agent"
        />
        <NavTab
          id="generator"
          label="AI Test Case Generator"
          icon={Sparkles}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
        <NavTab
          id="history"
          label="Historical Benchmark Diffs"
          icon={History}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
        />
      </div>
    </header>
  )
}

function NavTab({ id, label, icon: Icon, activeTab, setActiveTab, badge }) {
  const isActive = activeTab === id
  return (
    <button
      onClick={() => setActiveTab(id)}
      className={`px-3.5 py-1.5 rounded-lg flex items-center gap-2 font-medium transition-all whitespace-nowrap ${
        isActive
          ? 'bg-slate-800 text-cyan-400 border border-slate-700 shadow-sm'
          : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
      }`}
    >
      <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
      <span>{label}</span>
      {badge && (
        <span className={`text-[10px] px-1.5 py-0.2 rounded-full font-mono ${
          isActive ? 'bg-cyan-500/20 text-cyan-300' : 'bg-slate-800 text-slate-500'
        }`}>
          {badge}
        </span>
      )}
    </button>
  )
}
