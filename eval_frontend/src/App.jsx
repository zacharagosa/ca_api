import React, { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import OverviewTab from './components/OverviewTab'
import CategoryRunnerTab from './components/CategoryRunnerTab'
import DynamicSimulationTab from './components/DynamicSimulationTab'
import AiGeneratorTab from './components/AiGeneratorTab'
import BenchmarkHistoryTab from './components/BenchmarkHistoryTab'
import RunDetailsModal from './components/RunDetailsModal'

export default function App() {
  const [activeTab, setActiveTab] = useState('overview')
  const [activeCategoryFilter, setActiveCategoryFilter] = useState('ALL')
  
  // State
  const [systemStatus, setSystemStatus] = useState(null)
  const [testSuites, setTestSuites] = useState({ all_tests: [] })
  const [recentRuns, setRecentRuns] = useState([])
  const [baselineComparison, setBaselineComparison] = useState(null)
  const [simulationHistory, setSimulationHistory] = useState([])
  
  // Run Details Modal State
  const [selectedRunDetails, setSelectedRunDetails] = useState(null)
  const [isRunDetailsModalOpen, setIsRunDetailsModalOpen] = useState(false)
  
  // Execution State
  const [isRunningAll, setIsRunningAll] = useState(false)
  const [runningTestIds, setRunningTestIds] = useState({})
  const [testResultsMap, setTestResultsMap] = useState({})
  const [liveStreamingData, setLiveStreamingData] = useState({})
  
  // Simulation State
  const [isSimulating, setIsSimulating] = useState(false)
  const [currentSimulationStream, setCurrentSimulationStream] = useState(null)
  
  // AI Generator State
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedTests, setGeneratedTests] = useState([])

  // Fetch initial data
  const fetchHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health')
      if (res.ok) {
        const data = await res.json()
        setSystemStatus(data)
      }
    } catch (e) {
      console.warn("Could not fetch /api/health:", e)
    }
  }, [])

  const fetchSuites = useCallback(async () => {
    try {
      const res = await fetch('/api/test-suites')
      if (res.ok) {
        const data = await res.json()
        setTestSuites(data)
      }
    } catch (e) {
      console.warn("Could not fetch /api/test-suites:", e)
    }
  }, [])

  const fetchRuns = useCallback(async () => {
    try {
      const res = await fetch('/api/runs')
      if (res.ok) {
        const data = await res.json()
        setRecentRuns(data)
        if (data.length > 0) {
          fetchComparison(data[0].run_id)
        }
      }
    } catch (e) {
      console.warn("Could not fetch /api/runs:", e)
    }
  }, [])

  const fetchComparison = async (runId) => {
    try {
      const url = runId ? `/api/benchmarks/comparison?run_id=${runId}` : '/api/benchmarks/comparison'
      const res = await fetch(url)
      if (res.ok) {
        const data = await res.json()
        setBaselineComparison(data)
      }
    } catch (e) {
      console.warn("Could not fetch benchmark comparison:", e)
    }
  }

  const fetchSimulations = useCallback(async () => {
    try {
      const res = await fetch('/api/simulations')
      if (res.ok) {
        const data = await res.json()
        setSimulationHistory(data)
      }
    } catch (e) {
      console.warn("Could not fetch simulations:", e)
    }
  }, [])

  useEffect(() => {
    fetchHealth()
    fetchSuites()
    fetchRuns()
    fetchSimulations()
    const interval = setInterval(fetchHealth, 10000)
    return () => clearInterval(interval)
  }, [fetchHealth, fetchSuites, fetchRuns, fetchSimulations])

  // Open Run Details Modal & fetch full data
  const handleOpenRunDetails = async (runId) => {
    try {
      // 1. Try local recentRuns first
      const localRun = recentRuns.find(r => r.run_id === runId)
      if (localRun && localRun.results && localRun.results.length > 0) {
        setSelectedRunDetails(localRun)
        setIsRunDetailsModalOpen(true)
      }

      // 2. Fetch full fresh run details from API
      const res = await fetch(`/api/runs/${runId}`)
      if (res.ok) {
        const data = await res.json()
        setSelectedRunDetails(data)
        setIsRunDetailsModalOpen(true)
      } else if (localRun) {
        setSelectedRunDetails(localRun)
        setIsRunDetailsModalOpen(true)
      }
    } catch (e) {
      console.error("Error opening run details:", e)
      const localRun = recentRuns.find(r => r.run_id === runId)
      if (localRun) {
        setSelectedRunDetails(localRun)
        setIsRunDetailsModalOpen(true)
      }
    }
  }

  // 1. Run Single Test Case (SSE Stream)
  const handleRunSingleTest = async (testCase) => {
    const testId = testCase.id
    setRunningTestIds(prev => ({ ...prev, [testId]: true }))
    setLiveStreamingData(prev => ({
      ...prev,
      [testId]: { thoughts: [], text: '', routed_subagent: 'Routing...', visual_artifacts: {} }
    }))

    try {
      const response = await fetch('/api/test-case/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ custom_test: testCase })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              handleStreamEvent(event, testId)
            } catch (err) {
              console.error("Error parsing SSE event:", err)
            }
          }
        }
      }
    } catch (e) {
      console.error("Error running test:", e)
    } finally {
      setRunningTestIds(prev => ({ ...prev, [testId]: false }))
    }
  }

  const handleStreamEvent = (event, fallbackTestId) => {
    const tid = event.test_id || fallbackTestId

    if (event.type === 'thought') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: { ...current, thoughts: [...current.thoughts, event.content] }
        }
      })
    } else if (event.type === 'subagent_routed') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: { ...current, routed_subagent: event.subagent }
        }
      })
    } else if (event.type === 'chunk') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: { ...current, text: current.text + event.text }
        }
      })
    } else if (event.type === 'artifact_table') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: {
            ...current,
            visual_artifacts: { ...current.visual_artifacts, table_data: event.data }
          }
        }
      })
    } else if (event.type === 'artifact_chart') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: {
            ...current,
            visual_artifacts: { ...current.visual_artifacts, chart_config: event.config }
          }
        }
      })
    } else if (event.type === 'artifact_graph') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: {
            ...current,
            visual_artifacts: { ...current.visual_artifacts, graph_data: event.graphData }
          }
        }
      })
    } else if (event.type === 'artifact_link') {
      setLiveStreamingData(prev => {
        const current = prev[tid] || { thoughts: [], text: '', visual_artifacts: {} }
        return {
          ...prev,
          [tid]: {
            ...current,
            visual_artifacts: { ...current.visual_artifacts, explore_url: event.url }
          }
        }
      })
    } else if (event.type === 'test_completed') {
      setTestResultsMap(prev => ({
        ...prev,
        [tid]: event.result
      }))
    }
  }

  // 2. Run Category Suite or Selected
  const handleRunCategorySuite = async (categoryOrTestIds) => {
    let payload = {}
    if (Array.isArray(categoryOrTestIds)) {
      payload = { test_ids: categoryOrTestIds, title: `Custom Selection (${categoryOrTestIds.length} Tests)` }
    } else if (categoryOrTestIds === 'ALL') {
      payload = { category: 'ALL', title: 'Full 4-Category Suite Run' }
    } else {
      payload = { category: categoryOrTestIds, title: `${categoryOrTestIds} Suite Run` }
    }

    setIsRunningAll(true)
    try {
      const response = await fetch('/api/suite/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'suite_progress') {
                setRunningTestIds(prev => ({ ...prev, [event.current_test_id]: true }))
              } else if (event.type === 'test_completed') {
                setRunningTestIds(prev => ({ ...prev, [event.test_id]: false }))
                setTestResultsMap(prev => ({ ...prev, [event.test_id]: event.result }))
              } else if (event.type === 'suite_completed') {
                fetchRuns()
              } else {
                handleStreamEvent(event, event.test_id)
              }
            } catch (err) {
              console.error("Error parsing suite SSE:", err)
            }
          }
        }
      }
    } catch (e) {
      console.error("Suite run error:", e)
    } finally {
      setIsRunningAll(false)
      fetchRuns()
    }
  }

  // 3. Dynamic Dialogue Simulation
  const handleRunSimulation = async ({ persona, target_category, total_turns }) => {
    setIsSimulating(true)
    setCurrentSimulationStream({
      persona,
      target_category,
      total_turns,
      turns: []
    })

    try {
      const response = await fetch('/api/simulate-dialogue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ persona, target_category, total_turns })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const event = JSON.parse(line.slice(6))
              if (event.type === 'simulation_turn_completed') {
                setCurrentSimulationStream(prev => ({
                  ...prev,
                  turns: [...(prev?.turns || []), event.turn_result]
                }))
              } else if (event.type === 'simulation_completed') {
                setCurrentSimulationStream(event.simulation)
                fetchSimulations()
              }
            } catch (err) {
              console.error("Simulation SSE parse error:", err)
            }
          }
        }
      }
    } catch (e) {
      console.error("Simulation error:", e)
    } finally {
      setIsSimulating(false)
    }
  }

  // 4. Generate AI Test Cases
  const handleGenerateTests = async ({ category, difficulty, intent, count }) => {
    setIsGenerating(true)
    try {
      const res = await fetch('/api/generate-test-cases', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, difficulty, intent, count })
      })
      if (res.ok) {
        const data = await res.json()
        setGeneratedTests(data.test_cases || [])
        fetchSuites()
      }
    } catch (e) {
      console.error("Error generating tests:", e)
    } finally {
      setIsGenerating(false)
    }
  }

  // 5. Baseline Setting
  const handleSetBaseline = async (runId) => {
    try {
      const res = await fetch(`/api/runs/${runId}/set-baseline`, { method: 'POST' })
      if (res.ok) {
        fetchRuns()
      }
    } catch (e) {
      console.error("Error setting baseline:", e)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
        onRunAllSuites={() => handleRunCategorySuite('ALL')}
        isRunningAll={isRunningAll}
        onRefreshStatus={fetchHealth}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-6">
        {activeTab === 'overview' && (
          <OverviewTab
            latestRun={recentRuns[0]}
            baselineComparison={baselineComparison}
            recentRuns={recentRuns}
            onSelectRun={handleOpenRunDetails}
            onSetBaseline={handleSetBaseline}
            onNavigateToCategory={(catId) => {
              setActiveCategoryFilter(catId)
              setActiveTab('category_runner')
            }}
          />
        )}

        {activeTab === 'category_runner' && (
          <CategoryRunnerTab
            testSuites={testSuites}
            activeCategoryFilter={activeCategoryFilter}
            setActiveCategoryFilter={setActiveCategoryFilter}
            onRunSingleTest={handleRunSingleTest}
            onRunCategorySuite={handleRunCategorySuite}
            runningTestIds={runningTestIds}
            testResultsMap={testResultsMap}
            liveStreamingData={liveStreamingData}
          />
        )}

        {activeTab === 'simulation' && (
          <DynamicSimulationTab
            onRunSimulation={handleRunSimulation}
            isSimulating={isSimulating}
            currentSimulationStream={currentSimulationStream}
            simulationHistory={simulationHistory}
          />
        )}

        {activeTab === 'generator' && (
          <AiGeneratorTab
            onGenerateTests={handleGenerateTests}
            isGenerating={isGenerating}
            generatedTests={generatedTests}
            onRunGeneratedTest={(tc) => {
              handleRunSingleTest(tc)
              setActiveTab('category_runner')
            }}
            onSaveToSuite={() => fetchSuites()}
          />
        )}

        {activeTab === 'history' && (
          <BenchmarkHistoryTab
            recentRuns={recentRuns}
            baselineComparison={baselineComparison}
            onSetBaseline={handleSetBaseline}
            onSelectRun={handleOpenRunDetails}
          />
        )}
      </main>

      {/* Full Trial Run Details Modal */}
      <RunDetailsModal
        runDetails={selectedRunDetails}
        isOpen={isRunDetailsModalOpen}
        onClose={() => setIsRunDetailsModalOpen(false)}
        onSetBaseline={handleSetBaseline}
      />
    </div>
  )
}
