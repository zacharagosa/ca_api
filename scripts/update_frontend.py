import re

with open('frontend/src/App.jsx', 'r') as f:
    text = f.read()

# 1. Update lucide-react imports to include Cpu, Check
old_imports = "import { Send, Bot, User, Loader2, Code, X, ExternalLink, ChevronDown, ChevronUp, Info, AlertTriangle, LayoutDashboard, MessageSquare, Menu, ChevronRight, Maximize2, Minimize2, LogOut, Zap, Brain, RefreshCw, Square, Sparkles, Trash2, ShieldCheck, BarChart3, Clock, Share2 } from 'lucide-react'"
new_imports = "import { Send, Bot, User, Loader2, Code, X, ExternalLink, ChevronDown, ChevronUp, Info, AlertTriangle, LayoutDashboard, MessageSquare, Menu, ChevronRight, Maximize2, Minimize2, LogOut, Zap, Brain, RefreshCw, Square, Sparkles, Trash2, ShieldCheck, BarChart3, Clock, Share2, Cpu, Check } from 'lucide-react'"

assert old_imports in text, 'old_imports not found'
text = text.replace(old_imports, new_imports, 1)

# 2. Add state variables for model swapping in App component
old_state = "  const [isTestModalOpen, setIsTestModalOpen] = useState(false);\n  const [testLogs, setTestLogs] = useState([]);"
new_state = """  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testLogs, setTestLogs] = useState([]);

  // Model Swapping State
  const [selectedModel, setSelectedModel] = useState(() => {
    return localStorage.getItem('looker_agent_model') || 'gemini-3.6-flash';
  });
  const [availableModels, setAvailableModels] = useState([
    {
      id: "gemini-3.6-flash",
      name: "Gemini 3.6 Flash",
      provider: "Google DeepMind",
      badge: "Default",
      description: "Ultra-fast multimodal reasoning with high-precision tool calling."
    },
    {
      id: "qwen3.8-27b",
      name: "Qwen 3.8 27B",
      provider: "Alibaba Cloud / Open Weights",
      badge: "Specialist",
      description: "Specialized open-weights model optimized for coding, Spanner GQL, and data analytics."
    },
    {
      id: "gemini-3.5-flash",
      name: "Gemini 3.5 Flash",
      provider: "Google DeepMind",
      badge: "Fast",
      description: "Standard low-latency model for high-throughput queries."
    },
    {
      id: "gemini-1.5-pro",
      name: "Gemini 1.5 Pro",
      provider: "Google DeepMind",
      badge: "Reasoning",
      description: "Deep multi-hop reasoning and long-context synthesis."
    },
    {
      id: "qwen2.5-72b",
      name: "Qwen 2.5 72B",
      provider: "Alibaba Cloud / Open Weights",
      badge: "High Capacity",
      description: "High-capacity open model for complex multi-domain intelligence."
    }
  ]);
  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);

  // Fetch available models from backend
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/models`)
      .then(res => res.json())
      .then(data => {
        if (data && data.models && data.models.length > 0) {
          setAvailableModels(data.models);
        }
      })
      .catch(err => console.log('Could not fetch models:', err));
  }, []);

  const handleModelChange = (modelId) => {
    setSelectedModel(modelId);
    localStorage.setItem('looker_agent_model', modelId);
    setIsModelMenuOpen(false);
  };"""

assert old_state in text, 'old_state not found'
text = text.replace(old_state, new_state, 1)

# 3. Add model_name to requestPayload in handleSubmit
old_payload = """    const requestPayload = {
      message: userMessage,
      session_id: sessionId,
      agent_type: agentType,
      force_refresh: options.forceRefresh || false
    }"""

new_payload = """    const requestPayload = {
      message: userMessage,
      session_id: sessionId,
      agent_type: agentType,
      model_name: selectedModel,
      force_refresh: options.forceRefresh || false
    }"""

assert old_payload in text, 'old_payload not found'
text = text.replace(old_payload, new_payload, 1)

# 4. Add Model Selector UI in Assistant Sidebar Header
old_header_buttons = """          <div className="flex items-center gap-1.5">
            {/* New Chat Button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-slate-500 hover:text-slate-900"
              onClick={startNewChat}
              title="New Chat"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span className="sr-only">New Chat</span>
            </Button>"""

new_header_buttons = """          <div className="flex items-center gap-1.5">
            {/* Model Selector Dropdown */}
            <div className="relative">
              <button
                type="button"
                onClick={() => {
                  setIsModelMenuOpen(!isModelMenuOpen);
                  setIsHistoryMenuOpen(false);
                  setIsTestMenuOpen(false);
                }}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-[11px] font-semibold text-slate-700 dark:text-slate-200 transition-colors border border-slate-200/80 dark:border-slate-700"
                title="Swap Underlying AI Model"
              >
                <Cpu size={12} className={selectedModel.startsWith('qwen') ? 'text-amber-500' : 'text-blue-500'} />
                <span className="max-w-[95px] truncate">
                  {availableModels.find(m => m.id === selectedModel)?.name || selectedModel}
                </span>
                <ChevronDown size={11} className="text-slate-400" />
              </button>

              {isModelMenuOpen && (
                <div className="absolute right-0 top-full z-50 mt-1.5 w-72 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xl p-2 animate-in fade-in zoom-in-95">
                  <div className="px-2.5 py-1.5 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                    <span>Active AI Model</span>
                    <span className="text-[9px] text-blue-600 dark:text-blue-400 font-mono">Hot-Swap</span>
                  </div>
                  <div className="py-1 space-y-1">
                    {availableModels.map((m) => {
                      const isSelected = m.id === selectedModel;
                      const isQwen = m.id.startsWith('qwen');
                      return (
                        <button
                          key={m.id}
                          type="button"
                          onClick={() => handleModelChange(m.id)}
                          className={`w-full px-2.5 py-2 text-left rounded-xl transition-all flex flex-col gap-0.5 ${
                            isSelected
                              ? 'bg-blue-50 dark:bg-blue-950/60 border border-blue-200 dark:border-blue-800'
                              : 'hover:bg-slate-100 dark:hover:bg-slate-800/80 border border-transparent'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1.5 font-bold text-xs text-slate-800 dark:text-slate-100">
                              <Cpu size={13} className={isQwen ? 'text-amber-500' : 'text-blue-500'} />
                              <span>{m.name}</span>
                              {isSelected && <Check size={12} className="text-blue-600 dark:text-blue-400 ml-1" />}
                            </div>
                            {m.badge && (
                              <span className={`text-[9px] font-extrabold px-1.5 py-0.5 rounded-md ${
                                m.badge === 'Specialist'
                                  ? 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                                  : m.badge === 'Default'
                                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300'
                                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'
                              }`}>
                                {m.badge}
                              </span>
                            )}
                          </div>
                          <p className="text-[10px] text-slate-500 dark:text-slate-400 line-clamp-2 mt-0.5 leading-snug">
                            {m.description}
                          </p>
                          <div className="text-[9px] text-slate-400 font-mono mt-0.5">
                            Provider: {m.provider}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* New Chat Button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-slate-500 hover:text-slate-900"
              onClick={startNewChat}
              title="New Chat"
            >
              <MessageSquare className="h-3.5 w-3.5" />
              <span className="sr-only">New Chat</span>
            </Button>"""

assert old_header_buttons in text, 'old_header_buttons not found'
text = text.replace(old_header_buttons, new_header_buttons, 1)

# 5. Update footer pill with active model indicator
old_footer_pill = """              <span className="text-[10px] text-slate-400 font-normal hidden sm:inline">
                • {activeSubagent.description}
              </span>"""

new_footer_pill = """              <span className="text-[10px] text-slate-400 font-normal hidden sm:inline">
                • {activeSubagent.description} • <span className="font-semibold text-blue-600 dark:text-blue-400">{availableModels.find(m => m.id === selectedModel)?.name || selectedModel}</span>
              </span>"""

assert old_footer_pill in text, 'old_footer_pill not found'
text = text.replace(old_footer_pill, new_footer_pill, 1)

with open('frontend/src/App.jsx', 'w') as f:
    f.write(text)

print('frontend/src/App.jsx successfully updated!')
