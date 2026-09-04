import { useState, useRef, useEffect } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { Send, Bot, User, Loader2, Code, X, ExternalLink, ChevronDown, ChevronUp, Info, AlertTriangle, LayoutDashboard, MessageSquare, Menu, ChevronRight, Maximize2, Minimize2, LogOut, Zap, Brain, RefreshCw, Square, Sparkles, Trash2, ShieldCheck, BarChart3, Clock, Share2, Cpu, Check } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import JSON5 from 'json5'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement, Filler } from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';


// UI Components
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

// Custom Components
import DataTableRenderer from './DataTableRenderer';
import { LookerLink } from '@/components/LookerLink';
import VegaChartRenderer from '@/components/VegaChartRenderer';
import GraphRenderer from '@/components/GraphRenderer';
import ChartRenderer from '@/components/ChartRenderer';
import AiSummaryDashboard from '@/components/AiSummaryDashboard';
import PlayerSafetyDashboard from '@/components/PlayerSafetyDashboard';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
  Filler
);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

// Default fallback values
const DEFAULT_DASHBOARDS = [];
const DEFAULT_STARTER_QUESTIONS = [];
const DEFAULT_TEST_SCENARIOS = [];

const ContentAccordion = ({ children, title }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="chart-accordion">
      <button
        className="chart-header"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <span>{title || "Data Table"}</span>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {isOpen && <div className="chart-content">{children}</div>}
    </div>
  )
}

const MetadataAccordion = ({ metadata }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!metadata) return null;

  return (
    <div className="metadata-accordion">
      <button
        type="button"
        className="metadata-header"
        onClick={(e) => {
          e.preventDefault();
          setIsOpen(!isOpen);
        }}
      >
        <span>Query Details</span>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isOpen && (
        <div className="metadata-content">
          {metadata.sql && (
            <div className="metadata-section">
              <h4>Generated SQL</h4>
              <pre className="sql-code">{metadata.sql}</pre>
            </div>
          )}

          {metadata.filters && (
            <div className="metadata-section">
              <h4>Filters</h4>
              <ul>
                {Array.isArray(metadata.filters) ? (
                  metadata.filters.map((f, i) => (
                    <li key={i}>
                      <span className="metadata-key">{f.field || f.name}:</span> {String(f.value || f.expression)}
                    </li>
                  ))
                ) : (
                  Object.entries(metadata.filters).map(([key, value]) => (
                    <li key={key}>
                      <span className="metadata-key">{key}:</span> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </li>
                  ))
                )}
              </ul>
            </div>
          )}

          {metadata.sorts && metadata.sorts.length > 0 && (
            <div className="metadata-section">
              <h4>Sorts</h4>
              <ul>
                {metadata.sorts.map((sort, i) => (
                  <li key={i}>{typeof sort === 'object' ? JSON.stringify(sort) : String(sort)}</li>
                ))}
              </ul>
            </div>
          )}

          {metadata.fields && metadata.fields.length > 0 && (
            <div className="metadata-section">
              <h4>Fields</h4>
              <div className="fields-list">
                {metadata.fields.map((field, i) => {
                  const fieldName = typeof field === 'object' ? (field.name || JSON.stringify(field)) : String(field);
                  return <span key={i} className="field-chip">{fieldName}</span>
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ThinkingProcessAccordion = ({ thoughts, isComplete }) => {
  const [isOpen, setIsOpen] = useState(!isComplete);

  useEffect(() => {
    if (isComplete) {
      setIsOpen(false);
    } else {
      setIsOpen(true);
    }
  }, [isComplete]);

  if (!thoughts || thoughts.length === 0) return null;

  return (
    <div className="border rounded-md bg-muted/30 my-2">
      <button
        className="flex items-center justify-between w-full px-3 py-2 text-xs font-medium text-muted-foreground hover:bg-muted/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <span>Thinking Process ({thoughts.length} steps)</span>
        </div>
        {isOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>

      {isOpen && (
        <div className="p-3 border-t space-y-1.5">
          {thoughts.map((thought, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-muted-foreground">
              <span className="mt-1.5 w-1 h-1 rounded-full bg-primary/50 shrink-0"></span>
              <span className="leading-relaxed">{thought}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// Enhanced Live Thinking Panel for better loading visibility
const LiveThinkingPanel = ({ thoughts, currentThought, elapsedTime }) => {
  const scrollRef = useRef(null);

  useEffect(() => {
    // Auto-scroll to latest thought
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [thoughts, currentThought]);

  return (
    <div className="bg-muted text-foreground rounded-lg p-4 shadow-sm max-w-[85%] space-y-3">
      {/* Header with animated indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="relative flex items-center justify-center w-5 h-5">
            <span className="absolute w-3 h-3 bg-primary rounded-full animate-ping opacity-75"></span>
            <span className="relative w-2 h-2 bg-primary rounded-full"></span>
          </div>
          <span className="font-medium text-sm text-foreground">Analyzing your question...</span>
        </div>
        {elapsedTime !== undefined && (
          <span className="text-[10px] font-mono text-muted-foreground bg-muted-foreground/10 px-2 py-0.5 rounded">
            {Math.round(elapsedTime)}s
          </span>
        )}
      </div>

      {/* Thinking steps */}
      {thoughts && thoughts.length > 0 && (
        <div
          ref={scrollRef}
          className="border-l-2 border-primary/30 pl-3 space-y-2 max-h-[180px] overflow-y-auto"
        >
          {thoughts.map((thought, i) => {
            // Parse thought into title and rest if it has the "Title: Description" format
            const colonIndex = thought.indexOf(':');
            const hasTitle = colonIndex > 0 && colonIndex < 40;
            const title = hasTitle ? thought.substring(0, colonIndex).trim() : null;
            const description = hasTitle ? thought.substring(colonIndex + 1).trim() : thought;

            return (
              <div
                key={i}
                className={`text-xs ${i === thoughts.length - 1 ? 'text-foreground' : 'text-muted-foreground'} animate-in slide-in-from-left-2 duration-300`}
              >
                <div className="flex items-start gap-2">
                  <span className={`mt-1 w-1.5 h-1.5 rounded-full shrink-0 ${i === thoughts.length - 1 ? 'bg-primary' : 'bg-muted-foreground/50'}`}></span>
                  <div>
                    {title && (
                      <span className="font-semibold text-primary">{title}: </span>
                    )}
                    <span className="leading-relaxed">{description.substring(0, 120)}{description.length > 120 ? '...' : ''}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Current action with shimmer effect */}
      {currentThought && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground pt-2 border-t border-muted-foreground/10">
          <Loader2 className="animate-spin text-primary" size={12} />
          <span className="animate-pulse truncate">{currentThought}</span>
        </div>
      )}

      {/* Progress bar skeleton */}
      <div className="h-1 bg-muted-foreground/10 rounded-full overflow-hidden">
        <div className="h-full bg-gradient-to-r from-primary/50 via-primary to-primary/50 animate-pulse rounded-full w-full"></div>
      </div>
    </div>
  );
};

const TimingPopup = ({ timings }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const updateTimer = () => {
      const end = timings.endTime || Date.now();
      setElapsed((end - timings.startTime) / 1000);
    };

    updateTimer(); // Initial update

    if (!timings.endTime) {
      const interval = setInterval(updateTimer, 100);
      return () => clearInterval(interval);
    }
  }, [timings.startTime, timings.endTime]);

  if (!timings) return null;

  return (
    <div className="relative">
      <button
        className="flex items-center gap-1.5 px-2 py-1 rounded bg-muted/50 hover:bg-muted transition-colors text-[10px] text-muted-foreground"
        onClick={() => setIsOpen(!isOpen)}
        title="Show Execution Timings"
      >
        <Info size={10} />
        <span className="font-mono">{Math.round(elapsed)}s</span>
      </button>
      {isOpen && (
        <div className="absolute right-0 top-full mt-2 z-50 w-64 rounded-md border bg-popover p-3 shadow-md text-popover-foreground animate-in fade-in zoom-in-95">
          <div className="flex items-center justify-between border-b pb-2 mb-2">
            <h4 className="text-xs font-semibold">Execution Breakdown</h4>
            <button onClick={() => setIsOpen(false)} className="text-muted-foreground hover:text-foreground">
              <X size={12} />
            </button>
          </div>
          <div className="space-y-1">
            {timings.steps.map((step, i) => (
              <div key={i} className="flex justify-between text-[10px]">
                <span className="truncate max-w-[140px]" title={step.label}>{step.label}</span>
                <span className="font-mono text-muted-foreground">{step.duration ? step.duration.toFixed(1) + 's' : ''}</span>
              </div>
            ))}
            <div className="flex justify-between border-t pt-2 mt-2 font-medium text-xs">
              <span>Total Time</span>
              <span>{elapsed.toFixed(1)}s</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const MetricCard = ({ data }) => {
  // Support both single object or array of objects
  const metrics = Array.isArray(data) ? data : [data];

  return (
    <div className="flex flex-wrap gap-4 my-4">
      {metrics.map((metric, i) => (
        <Card key={i} className="min-w-[140px] flex-1 bg-card/50 border-muted">
          <CardContent className="p-4 pt-4">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider">{metric.label}</div>
            <div className="text-2xl font-bold mt-1 text-foreground">{metric.value}</div>
            {metric.trend && (
              <div className={`text-xs mt-1 font-medium ${metric.trend.includes('+') ? 'text-green-500' : metric.trend.includes('-') ? 'text-red-500' : 'text-muted-foreground'}`}>
                {metric.trend}
              </div>
            )}
            {metric.description && (
              <div className="text-xs text-muted-foreground mt-2 border-t pt-2 mt-2 border-border/50">
                {metric.description}
              </div>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

const QueryDetails = ({ details }) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!details) return null;

  return (
    <div className="border rounded-md bg-muted/30 my-2 query-details-wrapper">
      <button
        type="button"
        className="flex items-center justify-between w-full px-3 py-2 text-sm font-medium hover:bg-muted/50 transition-colors rounded-t-md text-foreground"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <Code size={16} className="text-primary" />
          <span>Query Details</span>
        </div>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isOpen && (
        <div className="p-3 border-t bg-card rounded-b-md space-y-3">
          {details.question && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Question</div>
              <div className="text-sm text-foreground">{details.question}</div>
            </div>
          )}

          {details.filters && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Filters</div>
              <div className="flex flex-wrap gap-2">
                {details.string_filters && details.string_filters.map((f, i) => (
                  <span key={i} className="px-2 py-0.5 rounded text-xs font-mono bg-primary/10 text-primary border border-primary/20">
                    {f.field_name}: {f.field_value}
                  </span>
                ))}
                {/* Handle other filter formats if present */}
                {!details.string_filters && details.filters && Array.isArray(details.filters) && details.filters.map((f, i) => (
                  <span key={i} className="px-2 py-0.5 rounded text-xs font-mono bg-primary/10 text-primary border border-primary/20">
                    {typeof f === 'string' ? f : JSON.stringify(f)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {details.fields && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">Fields</div>
              <div className="flex flex-wrap gap-1">
                {details.fields.map((field, i) => (
                  <span key={i} className="px-1.5 py-0.5 rounded text-xs font-mono bg-muted text-muted-foreground">
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}

          {details.sql && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">SQL</div>
              <pre className="p-2 rounded bg-muted font-mono text-xs overflow-x-auto text-foreground whitespace-pre-wrap break-all">
                {details.sql}
              </pre>
            </div>
          )}

          {/* Fallback for sql on top level if strictly following the user json blob structure where sql is outside query_details but maybe passed in prop combined */}
          {!details.sql && details._sql_fallback && (
            <div>
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1">SQL</div>
              <pre className="p-2 rounded bg-muted font-mono text-xs overflow-x-auto text-foreground whitespace-pre-wrap break-all">
                {details._sql_fallback}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const AgentInfoModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm animate-in fade-in-0">
      <div className="relative w-full max-w-lg rounded-lg border bg-card p-6 shadow-lg animate-in fade-in-0 zoom-in-95">
        <div className="flex flex-col space-y-1.5 text-center sm:text-left mb-4">
          <h2 className="text-lg font-semibold leading-none tracking-tight">Agent Capabilities</h2>
          <p className="text-sm text-muted-foreground">
            Choose the right agent for your analysis needs.
          </p>
        </div>

        <div className="grid gap-4 py-4">
          <div className="flex items-start gap-4 rounded-md border p-4 bg-muted/50">
            <Zap className="mt-1 h-5 w-5 text-amber-500 shrink-0" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">Fast Agent</p>
              <p className="text-sm text-muted-foreground">
                Best for real-time simple queries, checking specific metrics, or pulling raw data tables.
                <br />
                <span className="text-xs italic">Example: "What is the DAU for last week?"</span>
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 rounded-md border p-4 bg-muted/50">
            <Brain className="mt-1 h-5 w-5 text-purple-500 shrink-0" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">Deep Agent</p>
              <p className="text-sm text-muted-foreground">
                Performs complex multi-step reasoning, root cause analysis, and cross-comparisons.
                <br />
                <span className="text-xs italic">Example: "Why did retention drop on iOS yesterday?"</span>
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4 rounded-md border p-4 bg-muted/50">
            <Code className="mt-1 h-5 w-5 text-blue-500 shrink-0" />
            <div className="space-y-1">
              <p className="text-sm font-medium leading-none">MCP Agent</p>
              <p className="text-sm text-muted-foreground">
                Access advanced tools for dashboard management, LookML analysis, and system health checks.
                <br />
                <span className="text-xs italic">Example: "Create a new dashboard for user acquisition."</span>
              </p>
            </div>
          </div>
        </div>

        <div className="flex justify-end mt-4">
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState([
    { role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }
  ]);
  const isProduction = !window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1') && !window.location.hostname.includes('.googlers.com');
  const [accessToken, setAccessToken] = useState(
    isProduction ? 'iap_authenticated' : (localStorage.getItem('looker_access_token') || 'local_authenticated')
  );
  const [activeDashboard, setActiveDashboard] = useState('ai_summary');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [sidebarWidth, setSidebarWidth] = useState(600);
  const [isResizing, setIsResizing] = useState(false);
  const [signedUrl, setSignedUrl] = useState(null);
  const [embedError, setEmbedError] = useState(null);
  const [expandedGraph, setExpandedGraph] = useState(null);
  const sidebarRef = useRef(null);
  const isResizingRef = useRef(false);

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [agentType, setAgentType] = useState('auto'); // 'auto', 'fast', 'deep', or 'mcp'
  const [activeSubagent, setActiveSubagent] = useState({
    key: 'auto',
    name: 'Auto-Routing Engine',
    icon: 'Sparkles',
    description: 'Intelligent Intent Dispatcher'
  });
  const [isInfoModalOpen, setIsInfoModalOpen] = useState(false);
  const [isLongQuery, setIsLongQuery] = useState(false);
  const messagesEndRef = useRef(null);
  // Generate a unique session ID when the component mounts
  const [sessionId, setSessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9));

  // State for Deep Test Suite
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testLogs, setTestLogs] = useState([]);

  // Model Swapping State
  const [selectedModel, setSelectedModel] = useState(() => {
    const saved = localStorage.getItem('looker_agent_model');
    if (!saved || saved === 'gemini-3.6-flash') {
      return 'gemini-3.8-flash';
    }
    return saved;
  });
  const [availableModels, setAvailableModels] = useState([
    {
      id: "gemini-3.8-flash",
      name: "Gemini 3.8 Flash",
      provider: "Google DeepMind",
      badge: "Default",
      description: "Next-gen ultra-fast multimodal reasoning with high-precision tool calling."
    },
    {
      id: "gemini-3.6-flash",
      name: "Gemini 3.6 Flash",
      provider: "Google DeepMind",
      badge: "Fast",
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
          const saved = localStorage.getItem('looker_agent_model');
          if (!saved || saved === 'gemini-3.6-flash') {
            const def = data.default_model || 'gemini-3.8-flash';
            setSelectedModel(def);
            localStorage.setItem('looker_agent_model', def);
          }
        }
      })
      .catch(err => console.log('Could not fetch models:', err));
  }, []);

  const handleModelChange = (modelId) => {
    setSelectedModel(modelId);
    localStorage.setItem('looker_agent_model', modelId);
    setIsModelMenuOpen(false);
  };
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [currentThought, setCurrentThought] = useState(null); // Track live status

  const [isTestMenuOpen, setIsTestMenuOpen] = useState(false);
  const [isHistoryMenuOpen, setIsHistoryMenuOpen] = useState(false);
  const [history, setHistory] = useState([]);

  // Dataset config loaded from API
  const [datasetConfig, setDatasetConfig] = useState({
    name: '',
    display_name: 'Gaming Analytics',
    starter_questions: DEFAULT_STARTER_QUESTIONS,
    test_scenarios: DEFAULT_TEST_SCENARIOS,
    dashboards: DEFAULT_DASHBOARDS
  });

  // Load dataset config from API on mount
  useEffect(() => {
    const fetchDatasetConfig = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/dataset-config`);
        if (response.ok) {
          const config = await response.json();
          setDatasetConfig(config);
          // Set initial dashboard to AI Daily Insights if available, or fallback to first
          if (config.dashboards && config.dashboards.length > 0) {
            const hasAiSummary = config.dashboards.some(d => d.id === 'ai_summary');
            setActiveDashboard(hasAiSummary ? 'ai_summary' : config.dashboards[0].id);
          }
        }
      } catch (e) {
        console.warn('Failed to load dataset config:', e);
      }
    };
    fetchDatasetConfig();
  }, []);

  // Fetch history
  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/history`);
      if (res.ok) {
        setHistory(await res.json());
      }
    } catch (e) {
      console.error("Failed to load history", e);
    }
  };

  useEffect(() => {
    if (isHistoryMenuOpen) {
      fetchHistory();
    }
  }, [isHistoryMenuOpen]);

  const loadSession = async (id) => {
    setIsLoading(true);
    setIsHistoryMenuOpen(false);
    try {
      const res = await fetch(`${API_BASE_URL}/api/history/${id}`);
      if (res.ok) {
        const msgs = await res.json();
        // Ensure msgs has at least one item or default
        if (msgs.length === 0) {
          setMessages([{ role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }]);
        } else {
          // Normalize loaded messages: 'model' -> 'agent', and preserve rich data
          const normalizedMsgs = msgs.map(msg => ({
            ...msg,
            role: msg.role === 'model' ? 'agent' : msg.role,
            // Preserve rich data fields if they exist
            tableData: msg.tableData || null,
            chartConfig: msg.chartConfig || null,
            link: msg.link || null,
            thoughts: msg.thoughts || [],
            timings: msg.timings || null
          }));
          setMessages(normalizedMsgs);
        }
        // Force set session ID (this might need state update logic if sessionId is const/state)
        // Since sessionId is state, we need to add setSessionId to the hook above first.
        setSessionId(id);
      }
    } catch (e) {
      console.error("Failed to load session", e);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteSession = async (e, id) => {
    e.stopPropagation(); // Prevent loading the session
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;

    try {
      const res = await fetch(`${API_BASE_URL}/api/history/${id}`, { method: 'DELETE' });
      if (res.ok) {
        setHistory(prev => prev.filter(item => item.id !== id));
        // If we deleted the current session, start a new one
        if (id === sessionId) {
          startNewChat();
        }
      }
    } catch (e) {
      console.error("Failed to delete session", e);
    }
  };

  const startNewChat = () => {
    const newId = 'session_' + Math.random().toString(36).substr(2, 9);
    setSessionId(newId);
    setMessages([{ role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }]);
    setIsHistoryMenuOpen(false);
  };

  const runScenario = async (question) => {
    setIsTestMenuOpen(false);
    setInput(question);
    // Wait a bit to show the question
    await new Promise(r => setTimeout(r, 500));
    // Submit
    await handleSubmit(null, question);
  };

  const startResizing = (e) => {
    e.preventDefault();
    setIsResizing(true);
    isResizingRef.current = true;
    // Add overlay to body to prevent iframe capturing events
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  };

  useEffect(() => {
    const resize = (e) => {
      if (isResizingRef.current) {
        const newWidth = window.innerWidth - e.clientX;
        if (newWidth > 350 && newWidth < 1200) {
          setSidebarWidth(newWidth);
        }
      }
    };

    const stopResizing = () => {
      if (isResizingRef.current) {
        setIsResizing(false);
        isResizingRef.current = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      }
    };

    window.addEventListener('mousemove', resize);
    window.addEventListener('mouseup', stopResizing);
    window.addEventListener('mouseleave', stopResizing); // Stop if mouse leaves window

    return () => {
      window.removeEventListener('mousemove', resize);
      window.removeEventListener('mouseup', stopResizing);
      window.removeEventListener('mouseleave', stopResizing);
    };
  }, []);



  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, isLongQuery])

  useEffect(() => {
    let timer;
    if (isLoading) {
      setIsLongQuery(false);
      timer = setTimeout(() => {
        setIsLongQuery(true);
      }, 15000); // 15 seconds threshold
    } else {
      setIsLongQuery(false);
    }
    return () => clearTimeout(timer);
  }, [isLoading]);

  // Fetch Embed Session when dashboard or token changes
  useEffect(() => {
    const fetchEmbedSession = async () => {
      if (!activeDashboard || !accessToken || activeDashboard === 'ai_summary' || activeDashboard === 'toxicity_safety') return;

      let dashboard = datasetConfig?.dashboards?.find(d => d.id === activeDashboard);
      let targetUrl = dashboard?.url;
      if (!targetUrl) {
        if (activeDashboard.startsWith('custom_') || activeDashboard.startsWith('dashboard_') || /^\d+$/.test(activeDashboard)) {
          const rawId = activeDashboard.replace('custom_', '').replace('dashboard_', '');
          targetUrl = `/embed/dashboards/${rawId}`;
        } else if (activeDashboard === 'embedded_explore') {
          targetUrl = '/embed/explore/gaming/events';
        } else {
          return;
        }
      }

      try {
        setEmbedError(null);
        setSignedUrl(null);

        // Get user email from stored session or fetch from Google
        let userEmail = null;
        const storedSession = localStorage.getItem('looker_embed_session');
        if (storedSession) {
          try {
            const session = JSON.parse(storedSession);
            userEmail = session.user_id;
          } catch (e) { }
        }

        // If no stored email, try to get from Google
        if (!userEmail && accessToken) {
          try {
            const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
              headers: { Authorization: `Bearer ${accessToken}` }
            });
            if (userInfoResponse.ok) {
              const userInfo = await userInfoResponse.json();
              userEmail = userInfo.email;
            }
          } catch (e) { }
        }

        const normalizedTargetUrl = targetUrl === 'embedded_explore' ? '/embed/explore/gaming/events' : targetUrl;

        const requestPayload = {
          target_url: normalizedTargetUrl,
          // Use 'embed_' prefix to ensure we create a distinct embed user
          // and avoid conflicts if the email matches an existing native Looker user.
          user_id: userEmail ? `embed_${userEmail}` : 'embed_guest_user',
          first_name: userEmail ? userEmail.split('@')[0] : 'Guest',
          last_name: 'User'
        };
        console.log('Fetching cookieless embed session for:', dashboard.url, 'user:', requestPayload.user_id);

        const response = await fetch(`${API_BASE_URL}/api/embed`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestPayload)
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.error || 'Failed to get embed session');
        }

        const data = await response.json();

        if (data.url) {
          // Fallback to signed URL
          setSignedUrl(data.url);
          console.log('Using signed SSO embed URL');
        } else {
          throw new Error('No embed valid URL returned');
        }

      } catch (e) {
        console.error("Embed Error:", e);
        setEmbedError(e.message);
      }
    };

    fetchEmbedSession();
  }, [activeDashboard, accessToken, datasetConfig.dashboards]);

  // Create the dashboard embed AFTER the container is rendered
  // Create the dashboard embed AFTER the container is rendered



  const login = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      console.log(tokenResponse);
      setAccessToken(tokenResponse.access_token);
      localStorage.setItem('looker_access_token', tokenResponse.access_token);

      // Note: We no longer manually provision the embed user here.
      // The embed session is acquired on-demand in the dashboard component
      // using the 'embed_' prefixed user identity.
    },
    onError: error => console.log('Login Failed:', error),
    scope: 'https://www.googleapis.com/auth/cloud-platform https://www.googleapis.com/auth/userinfo.email'
  });

  // Ref for AbortController
  const abortControllerRef = useRef(null);

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsLoading(false);
  };

  const handleLookerLinkClick = async (url) => {
    setEmbedError(null);
    setSignedUrl(null); // Force reload

    // Route dashboard URLs to dashboard view and explore URLs to embedded_explore
    if (url.includes('/dashboards/')) {
      const match = url.match(/\/dashboards\/([0-9a-zA-Z_]+)/);
      if (match) {
        const dashId = match[1];
        const customId = `custom_${dashId}`;
        const existing = datasetConfig?.dashboards?.find(d => d.id === customId || d.id === dashId || d.url?.includes(dashId));
        if (existing) {
          setActiveDashboard(existing.id);
        } else {
          setDatasetConfig(prev => ({
            ...prev,
            dashboards: [
              {
                id: customId,
                title: `Custom Dashboard #${dashId}`,
                url: `/embed/dashboards/${dashId}`,
                icon: 'LayoutDashboard'
              },
              ...(prev?.dashboards || [])
            ]
          }));
          setActiveDashboard(customId);
        }
      }
    } else {
      setActiveDashboard('embedded_explore');
    }

    console.log('Handling Looker Link Click:', url);

    try {
      const response = await fetch(`${API_BASE_URL}/api/embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_url: url })
      });

      if (!response.ok) throw new Error('Signing failed');

      const data = await response.json();
      setSignedUrl(data.url);
    } catch (e) {
      console.error("Link Signing Error:", e);
      // Fallback to raw URL if signing fails
      setSignedUrl(url);
    }
  };

  // Refactored handleSubmit to accept an optional message argument and return a promise
  const handleSubmit = async (e, manualMessage = null, options = {}) => {
    if (e && e.preventDefault) e.preventDefault() // Check if e.preventDefault exists

    // If loading, this button acts as Stop (handled in the render, but just in case)
    if (isLoading) {
      handleStop();
      return;
    }

    const userMessage = manualMessage || input
    if (!userMessage.trim()) return false

    setMessages(prev => [...prev, { role: 'user', content: userMessage, timestamp: new Date() }])
    if (!manualMessage) setInput('')
    setIsLoading(true)

    // Create new AbortController
    abortControllerRef.current = new AbortController();

    const requestPayload = {
      message: userMessage,
      session_id: sessionId,
      agent_type: agentType,
      model_name: selectedModel,
      force_refresh: options.forceRefresh || false
    }
    console.log('Sending request:', requestPayload)

    try {
      // Use fast-query endpoint for fast mode, regular /chat for others
      const endpoint = agentType === 'fast' ? '/fast-query' : '/chat';
      console.log(`Fetching from ${API_BASE_URL}${endpoint}...`)
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
        },
        body: JSON.stringify(requestPayload),
        signal: abortControllerRef.current.signal // Attach signal
      })

      // If aborted, fetch throws AbortError
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          logout();
          throw new Error('Session expired. Please log in again.');
        }
        // Try to read the response body - might be JSON or plain text
        let errorMessage = 'Failed to fetch';
        try {
          const responseText = await response.text();
          try {
            const data = JSON.parse(responseText);
            errorMessage = data.error || errorMessage;
          } catch {
            // Response is not JSON, use text directly
            errorMessage = responseText || `Server error: ${response.status}`;
          }
        } catch {
          errorMessage = `Server error: ${response.status}`;
        }
        throw new Error(errorMessage);
      }

      const startTime = Date.now();
      setMessages(prev => [...prev, { role: 'agent', content: '', thoughts: [], timings: { startTime, steps: [] } }])

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''
      let buffer = ''
      let showChartRequested = false // Track explicit chart requests

      // Detect chart request from user message (frontend-side detection for reliability)
      const userMsgLower = userMessage.toLowerCase();
      const chartKeywords = ['chart', 'graph', 'plot', 'visualize', 'visualization', 'bar chart', 'pie chart', 'line chart', 'scatter', 'area chart'];
      if (chartKeywords.some(k => userMsgLower.includes(k))) {
        showChartRequested = true;
        console.log('Chart request detected from user message');
      }

      // Determine requested chart type from user message
      let requestedChartType = 'bar'; // default
      if (userMsgLower.includes('pie')) requestedChartType = 'pie';
      else if (userMsgLower.includes('line')) requestedChartType = 'line';
      else if (userMsgLower.includes('scatter')) requestedChartType = 'scatter';
      else if (userMsgLower.includes('area')) requestedChartType = 'area';

      // Debug: Track parsed chunks
      const parsedChunks = []

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const lines = buffer.split('\n');
        // Keep the last segment in the buffer as it might be incomplete
        buffer = lines.pop();

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i].trim();
          if (!line) continue;

          parsedChunks.push(line) // Log raw line

          if (line.startsWith('THOUGHT: ')) {
            const thought = line.substring(9)

            // Filter debug logs
            if (thought.startsWith('Data Rows Count') ||
              thought.startsWith('Stream processing complete') ||
              thought.startsWith('Stream Chunk') ||
              thought.startsWith('Chunk') ||
              thought.startsWith('Debug') ||
              thought.startsWith('Time to') ||
              thought.startsWith('Local Post-Processing')) {
              continue;
            }

            setCurrentThought(thought); // Update status indicator

            const now = Date.now();
            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                const updatedMsg = { ...lastMsg };

                if (updatedMsg.timings) {
                  const steps = [...(updatedMsg.timings.steps || [])];
                  const isDuplicate = steps.length > 0 && steps[steps.length - 1].label === thought;

                  if (!isDuplicate) {
                    if (steps.length > 0) {
                      steps[steps.length - 1] = {
                        ...steps[steps.length - 1],
                        duration: (now - steps[steps.length - 1].startTime) / 1000
                      };
                    }
                    steps.push({ label: thought, startTime: now });
                    updatedMsg.timings = { ...updatedMsg.timings, steps };
                  }
                }

                const currentThoughts = updatedMsg.thoughts || []
                if (!currentThoughts.includes(thought)) {
                  updatedMsg.thoughts = [...currentThoughts, thought];
                }

                newMessages[newMessages.length - 1] = updatedMsg;
              }
              return newMessages
            })
          } else if (line.startsWith('ERROR: ')) {
            const errorMsg = line.substring(7)
            fullResponse += `\n\n*Error: ${errorMsg}*`
            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                newMessages[newMessages.length - 1] = {
                  ...lastMsg,
                  content: fullResponse
                };
              }
              return newMessages
            })
          } else if (line.startsWith('LINK: ')) {
            let link = line.substring(6).trim()
            const markdownMatch = link.match(/\[.*?\]\((.*?)\)/);
            if (markdownMatch) {
              link = markdownMatch[1];
            }
            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                newMessages[newMessages.length - 1] = {
                  ...lastMsg,
                  link: link
                };
              }
              return newMessages
            })
          } else if (line.startsWith('SUGGESTION: ')) {
            const suggestion = line.substring(12)
            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                const currentSuggestions = lastMsg.suggestions || []
                if (!currentSuggestions.includes(suggestion)) {
                  newMessages[newMessages.length - 1] = {
                    ...lastMsg,
                    suggestions: [...currentSuggestions, suggestion]
                  };
                }
              }
              return newMessages
            })
          } else if (line.includes('<tool_code>') || line.includes('</tool_code>')) {
            // Filter out internal tool execution tags
            continue;
          } else {
            // Check for JSON DATA lines
            if (line.startsWith('DATA: {')) {
              try {
                const jsonContent = JSON.parse(line.substring(6))
                if (jsonContent.type === 'json_table') {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'agent') {
                      const updatedMsg = { ...lastMsg, tableData: jsonContent.data };

                      // Auto-generate chart if applicable AND requested
                      if (!updatedMsg.chartConfig && jsonContent.data.rows.length > 1 && showChartRequested) {
                        const fields = jsonContent.data.fields || []
                        const rows = jsonContent.data.rows || []

                        const dimension = fields.find(f => f.name.includes('date') || f.name.includes('month') || f.name.includes('name'))
                        const metric = fields.find(f => !f.name.includes('date') && !f.name.includes('month') && !f.name.includes('name'))

                        if (dimension && metric) {
                          updatedMsg.chartConfig = {
                            type: fields.length > 2 ? 'bar' : 'line',
                            data: {
                              labels: rows.map(r => r[dimension.name]),
                              datasets: [{
                                label: metric.label,
                                data: rows.map(r => r[metric.name]),
                                backgroundColor: 'rgba(53, 162, 235, 0.5)',
                                borderColor: 'rgb(53, 162, 235)',
                                borderWidth: 1
                              }]
                            },
                            options: {
                              responsive: true,
                              plugins: {
                                legend: { position: 'top' },
                                title: { display: true, text: metric.label }
                              }
                            }
                          }
                        }
                      }
                      newMessages[newMessages.length - 1] = updatedMsg;
                    }
                    return newMessages
                  })
                  continue
                } else if (jsonContent.type === 'json_link') {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'agent') {
                      newMessages[newMessages.length - 1] = { ...lastMsg, link: jsonContent.url };
                    }
                    return newMessages
                  })
                  continue
                } else if (jsonContent.type === 'json_chart') {
                  const config = jsonContent.config;

                  if (config && config.vega_config) {
                    setMessages(prev => {
                      const newMessages = [...prev]
                      const lastMsg = newMessages[newMessages.length - 1]
                      if (lastMsg.role === 'agent') {
                        newMessages[newMessages.length - 1] = { ...lastMsg, vegaConfig: config.vega_config };
                      }
                      return newMessages
                    })
                    continue;
                  }

                  showChartRequested = true;

                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]

                    let tableData = null;
                    for (let i = newMessages.length - 1; i >= 0; i--) {
                      if (newMessages[i].role === 'agent' && newMessages[i].tableData) {
                        tableData = newMessages[i].tableData;
                        break;
                      }
                    }

                    if (lastMsg.role === 'agent' && tableData && !lastMsg.chartConfig) {
                      const fields = tableData.fields || []
                      const rows = tableData.rows || []

                      if (rows.length >= 1) {
                        const dimension = fields.find(f => f.name.includes('date') || f.name.includes('month') || f.name.includes('name'))
                        const metric = fields.find(f => !f.name.includes('date') && !f.name.includes('month') && !f.name.includes('name'))

                        if (dimension && metric) {
                          const chartConfig = {
                            type: 'bar',
                            data: {
                              labels: rows.map(r => r[dimension.name]),
                              datasets: [{
                                label: metric.label,
                                data: rows.map(r => r[metric.name]),
                                backgroundColor: 'rgba(53, 162, 235, 0.5)',
                                borderColor: 'rgb(53, 162, 235)',
                                borderWidth: 1
                              }]
                            },
                            options: {
                              responsive: true,
                              plugins: {
                                legend: { position: 'top' },
                                title: { display: true, text: metric.label }
                              }
                            }
                          };
                          newMessages[newMessages.length - 1] = { ...lastMsg, chartConfig };
                        }
                      }
                    }
                    return newMessages
                  })
                  continue
                } else if (jsonContent.type === 'json_graph') {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'agent') {
                      newMessages[newMessages.length - 1] = { ...lastMsg, graphData: jsonContent.graphData };
                    }
                    return newMessages
                  })
                  continue
                } else if (jsonContent.type === 'json_dashboard_created') {
                  const newDash = jsonContent.dashboard;
                  if (newDash) {
                    setDatasetConfig(prev => {
                      const exists = prev.dashboards.some(d => d.id === newDash.id || d.url === newDash.url);
                      if (exists) {
                        return {
                          ...prev,
                          dashboards: prev.dashboards.map(d => (d.id === newDash.id || d.url === newDash.url) ? { ...d, ...newDash } : d)
                        };
                      }
                      return {
                        ...prev,
                        dashboards: [newDash, ...prev.dashboards]
                      };
                    });
                    setActiveDashboard(newDash.id);
                    if (newDash.signed_url) {
                      setSignedUrl(newDash.signed_url);
                    }
                  }
                  continue
                } else if (jsonContent.type === 'subagent_routed') {
                  setActiveSubagent({
                    key: jsonContent.subagent || 'auto',
                    name: jsonContent.name || 'Auto-Routing Engine',
                    icon: jsonContent.icon || 'Sparkles',
                    description: jsonContent.description || 'Intelligent Intent Dispatcher'
                  });
                  continue;
                } else if (jsonContent.type === 'query_details') {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'agent') {
                      const sqlQueries = lastMsg.sqlQueries ? [...lastMsg.sqlQueries] : [];
                      sqlQueries.push(jsonContent);
                      newMessages[newMessages.length - 1] = { ...lastMsg, sqlQueries };
                    }
                    return newMessages
                  })
                  continue;
                }
              } catch (e) {
                // Not JSON, treat as text
              }
            }

            // Assume it's data content
            let contentLine = line;
            if (line.startsWith('DATA: ')) {
              contentLine = line.substring(6);
            }

            // Check for explicit chart request signal
            if (contentLine.includes('SHOW_CHART')) {
              showChartRequested = true;
              contentLine = contentLine.replace('SHOW_CHART', '').trim();

              // Heuristic: Check user's last message for chart type preference
              // We access the message that *initiated* this request, which is usually the last one in 'messages' before we added the placeholder (or we can just check 'userMessage' variable if available, but it's passed as arg)
              // Actually, we can check 'messages' state indirectly via a check on the *last user message* in the state
              // But inside this loop 'prev' is the latest state.

              setMessages(prev => {
                const newMessages = [...prev]
                const lastMsg = newMessages[newMessages.length - 1]

                // Find last user message
                let userRequest = "";
                for (let i = newMessages.length - 1; i >= 0; i--) {
                  if (newMessages[i].role === 'user') {
                    userRequest = newMessages[i].content.toLowerCase();
                    break;
                  }
                }

                let requestedType = 'bar'; // default
                if (userRequest.includes('pie')) requestedType = 'pie';
                else if (userRequest.includes('line')) requestedType = 'line';
                else if (userRequest.includes('scatter')) requestedType = 'scatter';
                else if (userRequest.includes('area')) requestedType = 'area';

                // Find the most recent message with tableData
                let targetTableData = null;
                // Check current msg first (in case data came in same stream)
                if (lastMsg.role === 'agent' && lastMsg.tableData) {
                  targetTableData = lastMsg.tableData;
                } else {
                  // Search backwards
                  for (let i = newMessages.length - 1; i >= 0; i--) {
                    if (newMessages[i].role === 'agent' && newMessages[i].tableData) {
                      targetTableData = newMessages[i].tableData;
                      break;
                    }
                  }
                }

                if (lastMsg.role === 'agent' && targetTableData && !lastMsg.chartConfig) {
                  // We have data matching the request (either current or previous). Generate chart!
                  const fields = targetTableData.fields || []
                  const rows = targetTableData.rows || []

                  if (rows.length >= 1) {
                    const dimension = fields.find(f => f.name.includes('date') || f.name.includes('month') || f.name.includes('name'))
                    const metric = fields.find(f => !f.name.includes('date') && !f.name.includes('month') && !f.name.includes('name'))

                    if (dimension && metric) {
                      lastMsg.chartConfig = {
                        type: requestedType,
                        data: {
                          labels: rows.map(r => r[dimension.name]),
                          datasets: [{
                            label: metric.label,
                            data: rows.map(r => r[metric.name]),
                            backgroundColor: 'rgba(53, 162, 235, 0.5)',
                            borderColor: 'rgb(53, 162, 235)',
                            borderWidth: 1,
                            fill: requestedType === 'area'
                          }]
                        },
                        options: {
                          responsive: true,
                          plugins: {
                            legend: { position: 'top' },
                            title: { display: true, text: metric.label }
                          }
                        }
                      }
                    }
                  }
                }
                return newMessages
              })
            }

            // Skip raw query_details JSON that shouldn't be displayed to user
            // These should have been filtered server-side, but catch any that slipped through
            // Handle both single JSON and multiple concatenated JSON objects

            // Check if the entire line is just JSON blobs (no actual text content)
            const trimmedLine = contentLine.trim();
            if (trimmedLine.startsWith('{"type":') && trimmedLine.includes('"query_details"')) {
              // The entire line is JSON - skip it entirely
              continue;
            }

            // Check for multiple JSON objects or any {"type": ..., "sql": ..., "source": ...} patterns
            if (trimmedLine.includes('{"type":') && trimmedLine.includes('"source":') && trimmedLine.includes('"sql":')) {
              // Try to extract any non-JSON text by removing all JSON objects
              // Pattern matches: {"type": ... "source": "..."} 
              let cleaned = trimmedLine.replace(/\{"type":\s*"[^"]*"[^}]*"source":\s*"[^"]*"\s*\}/g, '');
              cleaned = cleaned.trim();

              if (!cleaned) {
                // Nothing left after removing JSON - skip
                continue;
              }

              // Use the cleaned version
              contentLine = cleaned;
            }

            // Append with newline to preserve formatting
            fullResponse += contentLine + '\n'

            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                lastMsg.content = fullResponse
              }
              return newMessages
            })
          }
        }
      }

      // After stream completes: If chart was requested but no chart generated, create one from recent data
      if (showChartRequested) {
        setMessages(prev => {
          const newMessages = [...prev];
          const lastMsg = newMessages[newMessages.length - 1];

          if (lastMsg.role === 'agent' && !lastMsg.chartConfig) {
            // Find most recent tableData from any message
            let tableData = null;
            for (let i = newMessages.length - 1; i >= 0; i--) {
              if (newMessages[i].tableData) {
                tableData = newMessages[i].tableData;
                break;
              }
            }

            if (tableData) {
              console.log('Generating chart from previous tableData');
              const fields = tableData.fields || [];
              const rows = tableData.rows || [];

              if (rows.length >= 1 && fields.length >= 2) {
                // Find dimension (first field that looks like a category)
                const dimension = fields.find(f =>
                  f.name.includes('date') || f.name.includes('month') ||
                  f.name.includes('name') || f.name.includes('country') ||
                  f.name.includes('platform') || f.name.includes('category') ||
                  f.name.includes('type') || f.name.includes('region')
                ) || fields[0]; // fallback to first field

                // Find metric (first numeric-looking field that's not the dimension)
                const metric = fields.find(f =>
                  f !== dimension &&
                  (f.name.includes('count') || f.name.includes('sum') ||
                    f.name.includes('total') || f.name.includes('revenue') ||
                    f.name.includes('amount') || f.name.includes('avg') ||
                    !f.name.includes('date') && !f.name.includes('name'))
                ) || fields.find(f => f !== dimension); // fallback to second field

                if (dimension && metric) {
                  lastMsg.chartConfig = {
                    type: requestedChartType,
                    data: {
                      labels: rows.map(r => r[dimension.name]),
                      datasets: [{
                        label: metric.label || metric.name,
                        data: rows.map(r => r[metric.name]),
                        backgroundColor: requestedChartType === 'pie'
                          ? rows.map((_, i) => `hsla(${i * 45}, 70%, 50%, 0.7)`)
                          : 'rgba(53, 162, 235, 0.5)',
                        borderColor: requestedChartType === 'pie'
                          ? rows.map((_, i) => `hsla(${i * 45}, 70%, 50%, 1)`)
                          : 'rgb(53, 162, 235)',
                        borderWidth: 1,
                        fill: requestedChartType === 'area'
                      }]
                    },
                    options: {
                      responsive: true,
                      plugins: {
                        legend: { position: 'top' },
                        title: { display: true, text: metric.label || metric.name }
                      }
                    }
                  };
                  console.log('Chart config generated:', lastMsg.chartConfig.type);
                }
              }
            }
          }
          return newMessages;
        });
      }

      // Finalize timings
      const endTime = Date.now();
      setMessages(prev => {
        const newMessages = [...prev];
        const lastMsg = newMessages[newMessages.length - 1];
        if (lastMsg.role === 'agent' && lastMsg.timings) {
          lastMsg.timings.endTime = endTime;
          // Close last step
          const steps = lastMsg.timings.steps;
          if (steps.length > 0) {
            steps[steps.length - 1].duration = (endTime - steps[steps.length - 1].startTime) / 1000;
          }
        }
        return newMessages;
      });

      // Update debug panel with detailed parsing info
      // setLastResponse removed
      setIsLoading(false)
      return true; // Signal completion

    } catch (error) {
      if (error.name === 'AbortError') {
        console.log('Fetch aborted by user');
        setMessages(prev => [...prev, { role: 'agent', content: 'Analysis stopped by user.' }]);
      } else {
        console.error('Error:', error)
        setMessages(prev => [...prev, { role: 'agent', content: 'Sorry, I encountered an error processing your request.' }])
      }
      setIsLoading(false)
      abortControllerRef.current = null;
      return false;
    }
  }

  const handleReauth = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/reauth`, { method: 'POST' })
      const data = await response.json()
      alert(data.status || data.error)
    } catch (error) {
      alert('Failed to trigger authentication: ' + error.message)
    }
  }

  // Memoize the markdown components to prevent re-renders on every keystroke
  const markdownComponents = useRef({
    a({ node, href, children, ...props }) {
      // Intercept Looker links (or all links if we want everything embedded)
      // For now, let's assume if it starts with http/https it might be external, 
      // but if we want to force embed behavior for known Looker domains or all links:
      return (
        <a
          href={href}
          onClick={(e) => {
            e.preventDefault();
            handleLookerLinkClick(href);
          }}
          className="text-blue-500 hover:underline cursor-pointer"
          {...props}
        >
          {children}
        </a>
      );
    },
    code({ node, inline, className, children, ...props }) {
      const match = /language-(\w+)/.exec(className || '')
      const lang = match ? match[1] : '';

      // Handle Chart
      const isChart = !inline && (lang === 'json-chart' || (lang === 'json' && String(children).includes('"type":')));
      if (isChart) {
        try {
          const config = JSON5.parse(String(children));
          if (config.type && config.data && config.series) {
            return <ChartRenderer config={config} />
          }
        } catch (e) {
          console.error("Chart JSON Parse Error:", e);
        }
      }

      // Handle Query Details
      // We look for specific keys that indicate this is a query details blob
      const content = String(children);
      const isQueryDetails = !inline && (
        lang === 'json' && (
          content.includes('"query_details":') ||
          (content.includes('"sql":') && content.includes('"fields":'))
        )
      );

      if (isQueryDetails) {
        try {
          const parsed = JSON5.parse(content);
          // Support both direct object or wrapped in query_details
          let details = parsed.query_details || parsed;

          // If the SQL is at the top level but not inside query_details (as per user example), merge it
          if (parsed.sql && !details.sql) {
            details = { ...details, _sql_fallback: parsed.sql };
          }

          return <QueryDetails details={details} />;
        } catch (e) {
          console.error("Query Details Parse Error:", e);
        }
      }

      // Handle JSON Metrics
      // Check explicit tag OR heuristic check for metric structure
      const isMetric = !inline && (
        lang === 'json-metric' ||
        (lang === 'json' && String(children).includes('"label":') && String(children).includes('"value":'))
      );

      if (isMetric) {
        try {
          const content = String(children);
          const data = JSON5.parse(content);

          // Validate structure (Duck typing)
          const validItem = (item) => item && typeof item.label === 'string' && typeof item.value !== 'undefined';
          const isValid = Array.isArray(data) ? data.every(validItem) : validItem(data);

          if (isValid) {
            return <MetricCard data={data} />;
          }
        } catch (e) {
          // If parsing fails or validation fails, fall through to normal code block
          // console.error("Metric Parse Error", e);
        }
      }

      // Handle SQL
      if (!inline && lang === 'sql') {
        return (
          <ContentAccordion title="Generated SQL">
            <div className="sql-code">
              <code className={className} {...props}>{children}</code>
            </div>
          </ContentAccordion>
        )
      }

      return <code className={className} {...props}>{children}</code>
    },
    table({ children, ...props }) {
      return (
        <ContentAccordion title="Data Table">
          <table {...props}>{children}</table>
        </ContentAccordion>
      )
    }
  }).current


  const logout = () => {
    setAccessToken(null);
    localStorage.removeItem('looker_access_token');
  };

  // Login screen only shown in development mode when not authenticated
  // In production, IAP handles authentication before users reach this point
  if (!accessToken && !isProduction) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-bold text-primary">Gaming Analytics</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4">
            <p className="text-muted-foreground text-center">
              Sign in to access your organization dashboard
            </p>
            <Button onClick={() => login()} className="w-full" size="lg">
              Connect to Looker
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const currentDashboard = datasetConfig.dashboards.find(d => d.id === activeDashboard);

  return (
    <div className="flex flex-col h-screen w-full overflow-hidden bg-[#f4f6fb] dark:bg-slate-950 font-sans">
      <header className="w-full flex items-center justify-between border-b border-slate-200/80 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md px-6 py-3 shrink-0 shadow-sm z-10">
        <div className="flex items-center gap-3">
          <div className="p-1.5 rounded-xl bg-blue-600 text-white shadow-sm flex items-center justify-center">
            <Sparkles size={18} />
          </div>
          <span className="text-base font-extrabold text-slate-800 dark:text-white tracking-tight">Gaming Analytics</span>

          {/* Dashboard Selection Dropdown */}
          <div className="relative ml-4">
            <select
              value={activeDashboard}
              onChange={(e) => setActiveDashboard(e.target.value)}
              className="appearance-none h-9 min-w-[210px] cursor-pointer rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900 pl-3.5 pr-8 py-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 shadow-sm"
            >
              {datasetConfig.dashboards.map((dash) => (
                <option key={dash.id} value={dash.id}>
                  {dash.title}
                </option>
              ))}
            </select>
            <div style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: '#94a3b8' }}>
              <ChevronDown size={14} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant={isSidebarOpen ? "default" : "outline"}
            size="sm"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className={`flex items-center gap-2 text-xs font-semibold rounded-xl transition-all ${
              isSidebarOpen 
                ? "bg-blue-600 text-white shadow-sm" 
                : "border-slate-200 text-slate-700 hover:bg-slate-100"
            }`}
          >
            <Bot size={15} />
            <span>{isSidebarOpen ? "Close Agent" : "Agent Assistant"}</span>
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsInfoModalOpen(true)}
            className="rounded-xl border-slate-200 text-slate-700 hover:bg-slate-100 text-xs font-semibold flex items-center gap-1.5"
          >
            <Info size={14} />
            <span>Info</span>
          </Button>
          <button
            onClick={logout}
            title="Logout"
            className="p-1.5 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/40 transition-colors"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden relative">
        <section className="workspace-content my-3 ml-3 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-md flex-1 overflow-hidden relative flex flex-col">
          {/* Overlay to catch mouse events during resize */}
          {isResizing && <div className="resize-overlay" style={{
            position: 'absolute', inset: 0, zIndex: 9999, background: 'transparent'
          }} />}
          <div style={{ flex: 1, position: 'relative' }}>
            {/* Expanded Graph View - takes over main content area */}
            {expandedGraph ? (
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, background: 'var(--background)', padding: '1rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--foreground)' }}>
                    Social Graph Visualization
                    <span style={{ fontSize: '0.875rem', fontWeight: 400, marginLeft: '0.5rem', color: 'var(--muted-foreground)' }}>
                      ({expandedGraph.nodes?.length || 0} nodes, {expandedGraph.links?.length || 0} connections)
                    </span>
                  </h2>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setExpandedGraph(null)}
                    className="flex items-center gap-1"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="18" y1="6" x2="6" y2="18"></line>
                      <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                    Close
                  </Button>
                </div>
                <div style={{ height: 'calc(100% - 3rem)', borderRadius: '0.5rem', overflow: 'hidden', border: '1px solid var(--border)' }}>
                  <GraphRenderer
                    data={expandedGraph}
                    width={window.innerWidth - sidebarWidth - 100}
                    height={window.innerHeight - 200}
                  />
                </div>
              </div>
            ) : activeDashboard === 'ai_summary' ? (
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflowY: 'auto' }}>
                <AiSummaryDashboard />
              </div>
            ) : activeDashboard === 'toxicity_safety' ? (
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflowY: 'auto' }}>
                <PlayerSafetyDashboard />
              </div>
            ) : activeDashboard === 'chat' ? (
              /* Chat is now sidebar only, this view might be deprecated or used for full-screen chat. 
                 But based on layout, we are toggling DASHBOARDS here. */
              <div style={{ padding: '2rem', color: '#fff' }}>Select a dashboard from the left.</div>
            ) : (
              <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflow: 'hidden' }}>
                {embedError ? (
                  <div style={{
                    position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                    background: 'rgba(255,0,0,0.1)', padding: '20px', borderRadius: '8px', border: '1px solid #ff4444', color: '#ff4444'
                  }}>
                    <h3>Embedding Error</h3>
                    <p>{embedError}</p>
                    <p style={{ fontSize: '0.8em', opacity: 0.8 }}>Check backend logs for API connection details.</p>
                  </div>
                ) : signedUrl ? (
                  <iframe
                    src={signedUrl}
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Looker Dashboard"
                  />
                ) : (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666' }}>
                    <Loader2 className="spin" size={32} />
                    <span style={{ marginLeft: 10 }}>Loading Dashboard...</span>
                  </div>
                )}
              </div>
            )}
          </div>
          {!isSidebarOpen && (
            <button className="sidebar-toggle glass" onClick={() => setIsSidebarOpen(true)} title="Open Assistant">
              <MessageSquare size={20} />
            </button>
          )}
        </section>

      {/* Resizer Handle */}
      {
        isSidebarOpen && (
          <div
            className={`sidebar-resizer ${isResizing ? 'resizing' : ''}`}
            onMouseDown={startResizing}
          />
        )
      }

      {/* Assistant Sidebar */}
      <aside
        ref={sidebarRef}
        className={`my-3 mr-3 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 shadow-md flex flex-col transition-all duration-300 overflow-hidden shrink-0 ${isSidebarOpen ? '' : 'w-0 opacity-0 border-0 my-0 mr-0'}`}
        style={{ width: isSidebarOpen ? sidebarWidth : 0 }}
      >
        <header className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 px-4 py-3 bg-slate-50/70 dark:bg-slate-900/70 shrink-0">
          <div className="flex items-center gap-2">
            <div className="p-1 rounded-lg bg-blue-600 text-white shadow-sm">
              <Bot size={16} />
            </div>
            <h3 className="text-xs font-extrabold text-slate-800 dark:text-white tracking-tight">AI Analytics Assistant</h3>
          </div>
          <div className="flex items-center gap-1.5">
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
            </Button>

            {/* History Dropdown */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                className={`h-7 w-7 text-slate-500 hover:text-slate-900 ${isHistoryMenuOpen ? 'bg-slate-100' : ''}`}
                onClick={() => setIsHistoryMenuOpen(!isHistoryMenuOpen)}
                title="History"
              >
                <Clock className="h-3.5 w-3.5" />
              </Button>

              {isHistoryMenuOpen && (
                <div className="absolute right-0 top-full z-50 mt-1 w-64 rounded-xl border border-slate-200 bg-white dark:bg-slate-900 shadow-lg animate-in fade-in zoom-in-95 max-h-[400px] overflow-y-auto p-1">
                  <div className="px-3 py-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800">
                    Recent Conversations
                  </div>
                  {history.length === 0 ? (
                    <div className="p-4 text-center text-xs text-slate-400">No history found</div>
                  ) : (
                    history.map((item) => (
                      <div
                        key={item.id}
                        className={`group flex items-center w-full rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors ${sessionId === item.id ? 'bg-slate-100/70 font-semibold' : ''}`}
                      >
                        <button
                          className="flex-1 px-3 py-2 text-left text-xs"
                          onClick={() => {
                            loadSession(item.id);
                            setIsHistoryMenuOpen(false);
                          }}
                        >
                          <div className="line-clamp-1">{item.title || "Untitled Conversation"}</div>
                          <div className="text-[10px] text-slate-400 mt-0.5">
                            {new Date(item.updated_at).toLocaleDateString()}
                          </div>
                        </button>
                        <button
                          className="p-1.5 text-slate-400 hover:text-rose-600 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => deleteSession(e, item.id)}
                          title="Delete Conversation"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            {/* Test Controls - Scenarios Dropdown */}
            <div className="relative ml-1">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsTestMenuOpen(!isTestMenuOpen)}
                className="h-7 px-2.5 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 rounded-lg flex items-center gap-1 border border-slate-200/60 dark:border-slate-800"
              >
                <span>Scenarios</span>
                <ChevronDown className="h-3 w-3 opacity-50" />
              </Button>
              {isTestMenuOpen && (
                <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-xl border border-slate-200 bg-white dark:bg-slate-900 shadow-xl p-1 animate-in fade-in zoom-in-95 max-h-[350px] overflow-y-auto">
                  <div className="px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100 dark:border-slate-800">
                    PRE-BUILT ANALYTICAL SCENARIOS
                  </div>
                  {datasetConfig.test_scenarios.map((item, i) => (
                    <button
                      key={i}
                      className="w-full px-3 py-2 text-left text-xs rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors text-slate-700 dark:text-slate-200 font-medium"
                      onClick={() => {
                        runScenario(item.question);
                        setIsTestMenuOpen(false);
                      }}
                    >
                      {item.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

          </div>
        </header>

        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {messages.map((msg, index) => (
            <div key={index} className={`flex flex-col ${msg.role === 'agent' ? 'items-start' : 'items-end'}`}>
              <div className={`flex items-center gap-2 mb-1 ${msg.role === 'agent' ? '' : 'flex-row-reverse'}`}>
                {msg.role === 'agent' && (
                  <span className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
                    <Bot size={12} /> Analyst
                  </span>
                )}
                {/* User label hidden for cleaner look */}

                {msg.role === 'agent' && msg.timings && <TimingPopup timings={msg.timings} />}
              </div>

              <div className={`relative max-w-[85%] rounded-lg p-3 text-sm leading-relaxed shadow-sm ${msg.role === 'agent'
                ? 'bg-muted text-foreground'
                : 'bg-primary text-primary-foreground'
                }`}>
                {msg.thoughts && msg.thoughts.length > 0 && (
                  <ThinkingProcessAccordion
                    thoughts={msg.thoughts}
                    isComplete={index !== messages.length - 1 || !isLoading}
                  />
                )}
                <div className={`prose prose-sm dark:prose-invert max-w-none ${msg.role === 'user' ? 'text-primary-foreground' : ''}`}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {/* Structured Data Renderer (Table & Chart) */}
                {msg.tableData && (
                  <DataTableRenderer
                    data={msg.tableData}
                    link={msg.link}
                    onLinkClick={handleLookerLinkClick}
                  />
                )}

                {/* Vega Chart (from Fast Mode API v2) */}
                {msg.vegaConfig && (
                  <div className="mt-4 p-4 bg-background rounded-lg border">
                    <VegaChartRenderer vegaConfig={msg.vegaConfig} data={msg.tableData} />
                  </div>
                )}

                {/* Chart.js Chart (from Deep/MCP mode or fallback) */}
                {msg.chartConfig && !msg.vegaConfig && (
                  <div className="mt-4 p-4 bg-background rounded-lg border h-[300px]">
                    <ChartRenderer config={msg.chartConfig} />
                  </div>
                )}

                {/* Graph Analytics Renderer */}
                {msg.graphData && (
                  <div
                    className="mt-4 p-4 bg-background rounded-lg border h-[400px] relative cursor-pointer group hover:border-primary transition-colors"
                    onClick={() => setExpandedGraph(msg.graphData)}
                    title="Click to expand in main view"
                  >
                    <div className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="bg-primary text-primary-foreground px-2 py-1 rounded text-xs flex items-center gap-1">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="15 3 21 3 21 9"></polyline>
                          <polyline points="9 21 3 21 3 15"></polyline>
                          <line x1="21" y1="3" x2="14" y2="10"></line>
                          <line x1="3" y1="21" x2="10" y2="14"></line>
                        </svg>
                        Expand
                      </div>
                    </div>
                    <GraphRenderer data={msg.graphData} />
                  </div>
                )}

                {!msg.tableData && msg.link && (
                  <div className="mt-2 text-right">
                    <LookerLink url={msg.link} onLinkClick={handleLookerLinkClick} />
                  </div>
                )}


                {msg.role === 'agent' && !msg.isStreaming && msg.thoughts && msg.thoughts.some(t => t.includes("Found similar question in cache")) && (
                  <div className="mt-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        const prompt = messages[i - 1]?.content;
                        if (prompt) {
                          handleSubmit(null, prompt, { forceRefresh: true });
                        }
                      }}
                      disabled={isLoading}
                      className="h-auto p-0 text-xs text-muted-foreground hover:text-foreground gap-1"
                    >
                      <RefreshCw size={12} className={isLoading ? "animate-spin" : ""} />
                      Refresh Data (Bypass Cache)
                    </Button>
                  </div>
                )}

                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="mt-4">
                    <div className="flex flex-wrap gap-2">
                      {msg.suggestions.map((suggestion, i) => (
                        <button
                          key={i}
                          className="px-3 py-1.5 text-xs font-medium rounded-full bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                          onClick={() => handleSubmit(null, suggestion)}
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {messages.length === 1 && !isLoading && (
            <div className="mt-8 flex flex-col items-center gap-4">
              <div className="flex items-center gap-2 text-muted-foreground">
                <span className="text-lg">✨</span>
                <span className="font-medium">Suggested Queries</span>
              </div>
              <div className="flex flex-wrap justify-center gap-2 max-w-lg">
                {datasetConfig.starter_questions.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSubmit(null, q)}
                    className="px-4 py-2 text-sm rounded-full border bg-background hover:bg-muted transition-colors text-foreground shadow-sm"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {isLoading && (
            <div className="flex flex-col items-start">
              <LiveThinkingPanel
                thoughts={messages[messages.length - 1]?.thoughts || []}
                currentThought={currentThought}
                elapsedTime={messages[messages.length - 1]?.timings?.startTime
                  ? (Date.now() - messages[messages.length - 1].timings.startTime) / 1000
                  : undefined}
              />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <footer className="border-t border-slate-100 dark:border-slate-800 p-3.5 flex flex-col gap-2 bg-white dark:bg-slate-900 shrink-0">
          <div className="flex justify-center gap-1.5 mb-1 items-center">
            <Button
              variant="outline"
              size="icon"
              onClick={() => setIsInfoModalOpen(true)}
              className="h-7 w-7 mr-1 shrink-0 rounded-full border-slate-200"
              title="Agent Info"
            >
              <Info size={13} />
            </Button>
            <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 rounded-full text-xs font-medium text-slate-700 dark:text-slate-200 shadow-sm transition-all animate-fadeIn">
              {activeSubagent.key === 'social_graph' ? (
                <Share2 size={13} className="text-purple-500 shrink-0 animate-pulse" />
              ) : activeSubagent.key === 'dashboard_builder' ? (
                <LayoutDashboard size={13} className="text-amber-500 shrink-0 animate-pulse" />
              ) : activeSubagent.key === 'deep_research' ? (
                <Brain size={13} className="text-blue-600 shrink-0 animate-pulse" />
              ) : activeSubagent.key === 'metrics_fast' ? (
                <Zap size={13} className="text-emerald-500 shrink-0 animate-pulse" />
              ) : (
                <Sparkles size={13} className="text-indigo-500 shrink-0" />
              )}
              <span className="font-semibold text-slate-800 dark:text-slate-100">{activeSubagent.name}</span>
              <span className="text-[10px] text-slate-400 font-normal hidden sm:inline">
                • {activeSubagent.description} • <span className="font-semibold text-blue-600 dark:text-blue-400">{availableModels.find(m => m.id === selectedModel)?.name || selectedModel}</span>
              </span>
            </div>
          </div>
          <div className="flex w-full items-center space-x-2">
            <Input
              type="text"
              placeholder="Query gaming data..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSubmit(e)}
              disabled={isLoading}
              className="flex-1 rounded-full bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 px-4 text-xs h-9 focus-visible:ring-blue-500"
            />
            <Button
              type={isLoading ? "button" : "submit"}
              onClick={isLoading ? handleStop : handleSubmit}
              disabled={!input.trim() && !isLoading}
              size="icon"
              className="h-9 w-9 rounded-full bg-blue-600 hover:bg-blue-700 text-white shrink-0 shadow-sm"
              variant={isLoading ? "destructive" : "default"}
            >
              {isLoading ? <Square className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </footer>

      </aside>
      </div>
      <AgentInfoModal isOpen={isInfoModalOpen} onClose={() => setIsInfoModalOpen(false)} />
    </div>
  )
}

export default App
