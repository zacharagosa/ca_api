import { useState, useRef, useEffect } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { Send, Bot, User, Loader2, Code, X, ExternalLink, ChevronDown, ChevronUp, Info, AlertTriangle, LayoutDashboard, MessageSquare, Menu, ChevronRight, Maximize2, Minimize2, LogOut, Zap, Brain, RefreshCw, Square, Sparkles, Trash2 } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import JSON5 from 'json5'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement, Filler } from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';
import { LookerEmbedSDK } from '@looker/embed-sdk';

// UI Components
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

// Custom Components
import DataTableRenderer from './DataTableRenderer';
import { LookerLink } from '@/components/LookerLink';

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

const ChartRenderer = ({ config }) => {
  // Comprehensive validation - return null for any invalid config
  if (!config || !config.data) return null;

  // Detect Chart.js format (from frontend heuristic) vs ChartRenderer format (from backend)
  // Chart.js format has config.data.labels and config.data.datasets
  // ChartRenderer format has config.data as array and config.series
  const isChartJsFormat = config.data && Array.isArray(config.data.labels) && Array.isArray(config.data.datasets);

  if (isChartJsFormat) {
    // Additional validation for Chart.js format
    if (!config.data.labels || !config.data.datasets || config.data.datasets.length === 0) {
      return null;
    }

    // Render directly using Chart.js format with light theme
    const chartType = config.type || 'bar';
    const lightThemeOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: { color: '#374151', font: { size: 12 } }
        },
        title: config.options?.plugins?.title ? {
          ...config.options.plugins.title,
          color: '#111827',
          font: { size: 14, weight: 'bold' }
        } : undefined
      },
      scales: {
        x: { ticks: { color: '#6B7280' }, grid: { color: '#E5E7EB' } },
        y: { ticks: { color: '#6B7280' }, grid: { color: '#E5E7EB' } }
      }
    };
    // Merge user options with light theme defaults
    const options = { ...lightThemeOptions, ...(config.options || {}) };

    if (chartType === 'bar') return <Bar options={options} data={config.data} />;
    if (chartType === 'line' || chartType === 'area') return <Line options={options} data={config.data} />;
    if (chartType === 'pie') return <Pie options={options} data={config.data} />;
    return <Bar options={options} data={config.data} />;
  }

  // Original ChartRenderer format handling
  if (!Array.isArray(config.data) || !Array.isArray(config.series) || config.series.length === 0) return null;

  const hasRightAxis = config.series.some(s => s.yAxisID === 'right');

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#374151', // gray-700 for light theme
          font: { size: 12 }
        }
      },
      title: {
        display: !!config.title,
        text: config.title,
        color: '#111827', // gray-900 for light theme
        font: { size: 14, weight: 'bold' }
      },
    },
    scales: {
      x: {
        stacked: config.stacked,
        ticks: { color: '#6B7280' }, // gray-500
        grid: { color: '#E5E7EB' }, // gray-200
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        stacked: config.stacked,
        ticks: { color: '#6B7280' }, // gray-500
        grid: { color: '#E5E7EB' }, // gray-200
      },
      ...(hasRightAxis && {
        y1: {
          type: 'linear',
          display: true,
          position: 'right',
          grid: {
            drawOnChartArea: false,
          },
          stacked: config.stacked,
          ticks: { color: '#6B7280' },
        }
      }),
    },
  };

  const chartData = {
    labels: config.data.map(item => item[config.xAxisKey]),
    datasets: config.series.map((s, i) => ({
      label: s.name,
      data: config.data.map(item => item[s.dataKey]),
      backgroundColor: s.fillColor || `hsla(${i * 60}, 70%, 50%, 0.5)`,
      borderColor: s.strokeColor || `hsla(${i * 60}, 70%, 50%, 1)`,
      borderWidth: 1,
      yAxisID: s.yAxisID === 'right' ? 'y1' : 'y',
      fill: config.type === 'area' || s.type === 'area',
    })),
  };

  const renderChart = () => {
    // Basic types
    if (config.type === 'bar') return <Bar options={options} data={chartData} />;
    if (config.type === 'line' || config.type === 'area') return <Line options={options} data={chartData} />;

    if (config.type === 'pie') {
      const pieData = {
        ...chartData,
        datasets: chartData.datasets.map(ds => ({
          ...ds,
          backgroundColor: config.data.map((_, i) => `hsla(${i * 45}, 70%, 50%, 0.5)`),
          borderColor: config.data.map((_, i) => `hsla(${i * 45}, 70%, 50%, 1)`),
        }))
      };
      return <Pie options={options} data={pieData} />;
    }

    if (config.type === 'scatter') {
      const scatterData = {
        datasets: config.series.map((s, i) => ({
          label: s.name,
          data: config.data.map(item => ({
            x: item[config.xAxisKey], // Ensure X is numeric for scatter
            y: item[s.dataKey]
          })),
          backgroundColor: s.fillColor || `hsla(${i * 60}, 70%, 50%, 0.5)`,
        }))
      }
      return <Scatter options={options} data={scatterData} />;
    }

    if (config.type === 'combo') {
      // Combo chart usually uses 'Bar' component with mixed types in datasets
      const comboData = {
        labels: config.data.map(item => item[config.xAxisKey]),
        datasets: config.series.map((s, i) => ({
          type: s.type || 'bar', // 'line' or 'bar'
          label: s.name,
          data: config.data.map(item => item[s.dataKey]),
          backgroundColor: s.fillColor || `hsla(${i * 60}, 70%, 50%, 0.5)`,
          borderColor: s.strokeColor || `hsla(${i * 60}, 70%, 50%, 1)`,
          borderWidth: 1,
          yAxisID: s.yAxisID === 'right' ? 'y1' : 'y',
        }))
      };
      return <Bar options={options} data={comboData} />;
    }

    return null;
  };

  return (
    <div className="chart-container-wrapper">
      {renderChart()}
    </div>
  );
};

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
    <div className="metadata-accordion">
      <button
        type="button"
        className="metadata-header"
        onClick={() => setIsOpen(!isOpen)}
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px', background: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '8px', cursor: 'pointer', color: 'var(--text-primary)' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Code size={16} className="text-blue-400" />
          <span style={{ fontWeight: 500 }}>Query Details</span>
        </div>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isOpen && (
        <div className="metadata-content" style={{ marginTop: '8px', padding: '12px', background: 'rgba(0, 0, 0, 0.2)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          {details.question && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Question</div>
              <div style={{ fontSize: '0.9rem' }}>{details.question}</div>
            </div>
          )}

          {details.filters && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Filters</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {details.string_filters && details.string_filters.map((f, i) => (
                  <span key={i} style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                    {f.field_name}: {f.field_value}
                  </span>
                ))}
                {/* Handle other filter formats if present */}
                {!details.string_filters && details.filters && Array.isArray(details.filters) && details.filters.map((f, i) => (
                  <span key={i} style={{ background: 'rgba(59, 130, 246, 0.2)', color: '#93c5fd', padding: '4px 8px', borderRadius: '4px', fontSize: '0.8rem', fontFamily: 'monospace' }}>
                    {typeof f === 'string' ? f : JSON.stringify(f)}
                  </span>
                ))}
              </div>
            </div>
          )}

          {details.fields && (
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)', marginBottom: '4px' }}>Fields</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
                {details.fields.map((field, i) => (
                  <span key={i} style={{ background: 'rgba(255, 255, 255, 0.1)', padding: '2px 6px', borderRadius: '4px', fontSize: '0.8rem', fontFamily: 'monospace', color: 'var(--text-secondary)' }}>
                    {field}
                  </span>
                ))}
              </div>
            </div>
          )}

          {details.sql && (
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)', marginBottom: '4px' }}>SQL</div>
              <pre style={{ background: '#1e1e1e', padding: '8px', borderRadius: '4px', overflowX: 'auto', fontSize: '0.75rem', color: '#d4d4d4', margin: 0 }}>
                {details.sql}
              </pre>
            </div>
          )}

          {/* Fallback for sql on top level if strictly following the user json blob structure where sql is outside query_details but maybe passed in prop combined */}
          {!details.sql && details._sql_fallback && (
            <div>
              <div style={{ fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.5px', color: 'var(--text-secondary)', marginBottom: '4px' }}>SQL</div>
              <pre style={{ background: '#1e1e1e', padding: '8px', borderRadius: '4px', overflowX: 'auto', fontSize: '0.75rem', color: '#d4d4d4', margin: 0 }}>
                {details._sql_fallback}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

function App() {
  const [messages, setMessages] = useState([
    { role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }
  ])
  const [accessToken, setAccessToken] = useState(localStorage.getItem('looker_access_token'))
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [agentType, setAgentType] = useState('fast') // 'fast', 'deep', or 'mcp'
  const [isLongQuery, setIsLongQuery] = useState(false);
  const messagesEndRef = useRef(null)
  // Generate a unique session ID when the component mounts
  const [sessionId, setSessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9))
  const [isAutoTesting, setIsAutoTesting] = useState(false)
  const autoTestIntervalRef = useRef(null)

  // State for Deep Test Suite
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testLogs, setTestLogs] = useState([]);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [currentThought, setCurrentThought] = useState(null); // Track live status

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
          // Set initial dashboard if available
          if (config.dashboards && config.dashboards.length > 0) {
            setActiveDashboard(config.dashboards[0].id);
          }
        }
      } catch (e) {
        console.warn('Failed to load dataset config:', e);
      }
    };
    fetchDatasetConfig();
  }, []);

  const [isTestMenuOpen, setIsTestMenuOpen] = useState(false);
  const [isHistoryMenuOpen, setIsHistoryMenuOpen] = useState(false);
  const [history, setHistory] = useState([]);

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

  const [activeDashboard, setActiveDashboard] = useState('overview');
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [sidebarWidth, setSidebarWidth] = useState(600);
  const [isResizing, setIsResizing] = useState(false);

  // LOOKER EMBED STATE
  const [signedUrl, setSignedUrl] = useState(null);
  const [embedSession, setEmbedSession] = useState(null);
  const [embedError, setEmbedError] = useState(null);
  const embedContainerRef = useRef(null);
  const sidebarRef = useRef(null);

  // Ref to track resize state in event listeners without dependency issues
  const isResizingRef = useRef(false);

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
      if (!activeDashboard || !accessToken) return;

      const dashboard = datasetConfig.dashboards.find(d => d.id === activeDashboard);
      if (!dashboard) return;

      try {
        setEmbedError(null);
        setSignedUrl(null);
        setEmbedSession(null);

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

        const requestPayload = {
          target_url: dashboard.url,
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

        if (data.type === 'cookieless' && data.authentication_token) {
          console.log('Received cookieless embed session');

          // Initialize the Looker Embed SDK with cookieless auth
          const lookerHost = data.looker_host.replace(/^https?:\/\//, '');

          LookerEmbedSDK.initCookieless(
            lookerHost,
            // acquireSession callback - called when SDK needs a new session
            async () => {
              console.log('SDK requesting new session');
              const resp = await fetch(`${API_BASE_URL}/api/embed`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(requestPayload)
              });
              const newSession = await resp.json();
              return {
                authentication_token: newSession.authentication_token,
                authentication_token_ttl: newSession.authentication_token_ttl,
                navigation_token: newSession.navigation_token,
                navigation_token_ttl: newSession.navigation_token_ttl,
                session_reference_token_ttl: newSession.session_reference_token_ttl,
                api_token: newSession.api_token,
                api_token_ttl: newSession.api_token_ttl,
              };
            },
            // generateTokens callback - called when SDK needs to refresh tokens
            async (tokens) => {
              console.log('SDK requesting token refresh');
              const resp = await fetch(`${API_BASE_URL}/api/generate-embed-tokens`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  session_reference_token: tokens.session_reference_token,
                  api_token: tokens.api_token,
                  navigation_token: tokens.navigation_token,
                })
              });
              return await resp.json();
            }
          );

          // Store the session data - dashboard creation happens in separate useEffect
          setEmbedSession(data);
        } else if (data.url) {
          // Fallback to signed URL
          setSignedUrl(data.url);
          console.log('Using signed SSO embed URL');
        } else {
          throw new Error('No embed session or URL returned');
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
  useEffect(() => {
    // If we have a session but no container yet, we simply return and wait for the
    // component to re-render with the container div (which is conditioned on embedSession)
    if (!embedSession || !embedContainerRef.current) {
      return;
    }

    // Use a small timeout to ensure the DOM is fully updated and ref is stable
    const timer = setTimeout(() => {
      // Clear any existing content
      if (embedContainerRef.current) {
        embedContainerRef.current.innerHTML = '';

        // Extract the dashboard path from the target URL
        try {
          const targetUrl = new URL(embedSession.target_url);
          const dashboardPath = targetUrl.pathname;

          // Parse query params to pass to SDK
          // The SDK requires params to be passed via .withParams()
          const searchParams = new URLSearchParams(targetUrl.search);
          const params = {};
          for (const [key, value] of searchParams) {
            params[key] = value;
          }

          // Check if it's a dashboard ID or slug
          // Matches /embed/dashboards/123 or /dashboards/123
          const dashboardMatch = dashboardPath.match(/\/(?:embed\/)?dashboards\/([^/]+)/);

          if (dashboardMatch) {
            const dashboardId = dashboardMatch[1];
            console.log('Creating embed for dashboard:', dashboardId, 'with params:', params);

            LookerEmbedSDK.createDashboardWithId(dashboardId)
              .appendTo(embedContainerRef.current)
              .withClassName('looker-embed-dashboard')
              .withParams(params)
              .build()
              .connect()
              .then((dashboard) => {
                console.log('Dashboard embed connected successfully');
              })
              .catch((error) => {
                console.error('Dashboard embed error:', error);
                setEmbedError('Failed to load dashboard: ' + error.message);
              });
          } else {
            console.error('Could not extract dashboard ID from path:', dashboardPath);
          }
        } catch (e) {
          console.error('Error creating dashboard embed:', e);
          setEmbedError('Failed to create dashboard embed');
        }
      }
    }, 100);

    return () => clearTimeout(timer);
  }, [embedSession, activeDashboard]); // Re-run when session or dashboard changes


  const login = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      console.log(tokenResponse);
      setAccessToken(tokenResponse.access_token);
      localStorage.setItem('looker_access_token', tokenResponse.access_token);

      // Auto-provision user in Looker using cookieless embed
      // This creates an embed user without requiring an internal Looker license
      try {
        // Get user info from Google
        const userInfoResponse = await fetch('https://www.googleapis.com/oauth2/v3/userinfo', {
          headers: { Authorization: `Bearer ${tokenResponse.access_token}` }
        });

        if (userInfoResponse.ok) {
          const userInfo = await userInfoResponse.json();
          const userEmail = userInfo.email;

          if (userEmail) {
            console.log('Provisioning Looker embed user:', userEmail);

            // Provision user via cookieless embed API
            const provisionResponse = await fetch(
              `${API_BASE_URL}/api/looker-provision?user_id=${encodeURIComponent(userEmail)}`
            );

            if (provisionResponse.ok) {
              const result = await provisionResponse.json();
              if (result.provisioned) {
                console.log('Looker embed user provisioned successfully');
                // Store embed session tokens for later use
                localStorage.setItem('looker_embed_session', JSON.stringify({
                  user_id: userEmail,
                  session_reference_token: result.session_reference_token,
                  authentication_token: result.authentication_token,
                  navigation_token: result.navigation_token
                }));
              }
            } else {
              console.warn('Looker provisioning response not ok:', provisionResponse.status);
            }
          }
        }
      } catch (e) {
        // Don't fail login if Looker provisioning fails
        console.warn('Looker provisioning failed (non-blocking):', e);
      }
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
    // Optimistically set signedUrl to trigger iframe reload or just use the url if signing isn't needed/fails
    setEmbedError(null);
    setSignedUrl(null); // Force reload

    // We can assume the iframe will handle it, but since we are replacing the dashboard,
    // let's try to sign it first to be safe, similar to how fetchSignedUrl works.
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
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch')
      }

      const startTime = Date.now();
      setMessages(prev => [...prev, { role: 'agent', content: '', thoughts: [], timings: { startTime, steps: [] } }])

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let fullResponse = ''
      let buffer = ''
      let showChartRequested = false // Track explicit chart requests

      // Debug: Track parsed chunks
      const parsedChunks = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process buffer line by line
        const lines = buffer.split('\n')
        // Keep the last partial line in the buffer
        buffer = lines.pop() || ''

        for (const line of lines) {
          // Don't skip empty lines as they might be important for markdown formatting (e.g. paragraph breaks)
          // if (!line.trim()) continue 

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
                // Update timings
                if (lastMsg.timings) {
                  const steps = lastMsg.timings.steps;
                  // Check for duplicate (same label as last step)
                  const isDuplicate = steps.length > 0 && steps[steps.length - 1].label === thought;

                  if (!isDuplicate) {
                    if (steps.length > 0) {
                      steps[steps.length - 1].duration = (now - steps[steps.length - 1].startTime) / 1000;
                    }
                    steps.push({ label: thought, startTime: now });
                  }
                }

                const currentThoughts = lastMsg.thoughts || []
                if (!currentThoughts.includes(thought)) {
                  const updatedThoughts = [...currentThoughts, thought]
                  lastMsg.thoughts = updatedThoughts
                }
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
                lastMsg.content = fullResponse
              }
              return newMessages
            })
          } else if (line.startsWith('LINK: ')) {
            let link = line.substring(6).trim()
            // Check if link is in markdown format [url](url) or [text](url)
            const markdownMatch = link.match(/\[.*?\]\((.*?)\)/);
            if (markdownMatch) {
              link = markdownMatch[1];
            }
            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                lastMsg.link = link
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
                  lastMsg.suggestions = [...currentSuggestions, suggestion]
                }
              }
              return newMessages
            })
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
                      lastMsg.tableData = jsonContent.data

                      // Auto-generate chart if applicable AND requested
                      if (!lastMsg.chartConfig && jsonContent.data.rows.length > 1 && showChartRequested) {
                        const fields = jsonContent.data.fields || []
                        const rows = jsonContent.data.rows || []

                        // Heuristic: 1 date/cat + 1 metric
                        const dimension = fields.find(f => f.name.includes('date') || f.name.includes('month') || f.name.includes('name'))
                        const metric = fields.find(f => !f.name.includes('date') && !f.name.includes('month') && !f.name.includes('name'))

                        if (dimension && metric) {
                          lastMsg.chartConfig = {
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
                    }
                    return newMessages
                  })
                  continue
                } else if (jsonContent.type === 'json_link') {
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]
                    if (lastMsg.role === 'agent') {
                      lastMsg.link = jsonContent.url
                    }
                    return newMessages
                  })
                  continue
                } else if (jsonContent.type === 'json_chart') {
                  // Treat specific chart event as a signal to show chart
                  showChartRequested = true;

                  // Trigger chart generation logic - search for tableData in recent messages
                  setMessages(prev => {
                    const newMessages = [...prev]
                    const lastMsg = newMessages[newMessages.length - 1]

                    // Find the most recent tableData from any agent message
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
                          lastMsg.chartConfig = {
                            type: 'bar', // Default to bar for follow-up chart requests
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
                    }
                    return newMessages
                  })
                  continue
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

              // If we received the signal BUT we already processed the table data (race condition),
              // we need to trigger the chart generation now.
              setMessages(prev => {
                const newMessages = [...prev]
                const lastMsg = newMessages[newMessages.length - 1]
                if (lastMsg.role === 'agent' && lastMsg.tableData && !lastMsg.chartConfig) {
                  // We have data but no chart, and we just got the signal. Generate it!
                  const fields = lastMsg.tableData.fields || []
                  const rows = lastMsg.tableData.rows || []

                  if (rows.length > 1) {
                    const dimension = fields.find(f => f.name.includes('date') || f.name.includes('month') || f.name.includes('name'))
                    const metric = fields.find(f => !f.name.includes('date') && !f.name.includes('month') && !f.name.includes('name'))

                    if (dimension && metric) {
                      lastMsg.chartConfig = {
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
                }
                return newMessages
              })
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

  // Effect to manage auto-test loop
  useEffect(() => {
    if (!isAutoTesting) return;

    let currentIndex = 0;

    const runNext = async () => {
      // Use test_scenarios instead of starter_questions
      const scenarios = datasetConfig.test_scenarios || [];

      if (currentIndex >= scenarios.length || !isAutoTesting) {
        setIsAutoTesting(false);
        return;
      }

      // test_scenarios items are objects { label, question }, starter_questions are strings
      const item = scenarios[currentIndex];
      const question = typeof item === 'string' ? item : item.question;

      setInput(question);

      // Wait a bit to show the question in the input
      await new Promise(r => setTimeout(r, 1000));

      // Submit
      await handleSubmit(null, question);

      // Wait a bit before next question
      await new Promise(r => setTimeout(r, 2000));

      currentIndex++;
      if (isAutoTesting) runNext();
    };

    runNext();

    return () => {
      // Cleanup if component unmounts or auto-test stops
      setIsAutoTesting(false);
    };
  }, [isAutoTesting]); // Dependency on isAutoTesting state

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

  if (!accessToken) {
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
    <div className="flex h-screen w-full overflow-hidden bg-background">
      {/* Navigation Rail */}


      {/* Main Workspace */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center justify-between border-b bg-background px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-primary/10 p-2">
              <Bot className="text-primary h-6 w-6" />
            </div>
            <span className="text-lg font-semibold text-foreground whitespace-nowrap">Gaming Analytics</span>

            {/* Dashboard Selection Dropdown */}
            <div className="relative ml-4">
              <select
                value={activeDashboard}
                onChange={(e) => setActiveDashboard(e.target.value)}
                className="h-10 min-w-[200px] cursor-pointer rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
              >
                {datasetConfig.dashboards.map((dash) => (
                  <option key={dash.id} value={dash.id}>
                    {dash.title}
                  </option>
                ))}
              </select>
              <div style={{ position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none', color: 'var(--text-secondary)' }}>
                <ChevronDown size={14} />
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={logout}
              title="Logout"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                background: 'transparent',
                border: '1px solid var(--border-color)',
                padding: '8px 16px',
                borderRadius: '8px',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--bg-tertiary)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
            >
              <LogOut size={16} />
              <span>Log Out</span>
            </button>
          </div>
        </header>

        <section className="workspace-content" style={{ position: 'relative', flex: 1, display: 'flex', flexDirection: 'column' }}>
          {/* Overlay to catch mouse events during resize */}
          {isResizing && <div className="resize-overlay" style={{
            position: 'absolute', inset: 0, zIndex: 9999, background: 'transparent'
          }} />}
          <div style={{ flex: 1, position: 'relative' }}>
            {activeDashboard === 'chat' ? (
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
                ) : embedSession ? (
                  <div
                    ref={embedContainerRef}
                    style={{ width: '100%', height: '100%', position: 'relative' }}
                    className="looker-embed-container"
                  >
                    {/* Loading indicator shown initially, SDK will replace content */}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: '#666', position: 'absolute', inset: 0 }}>
                      <Loader2 className="spin" size={32} />
                      <span style={{ marginLeft: 10 }}>Loading Dashboard...</span>
                    </div>
                  </div>
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
      </div>

      {/* Resizer Handle */}
      {isSidebarOpen && (
        <div
          className={`sidebar-resizer ${isResizing ? 'resizing' : ''}`}
          onMouseDown={startResizing}
        />
      )}

      {/* Assistant Sidebar */}
      <aside
        ref={sidebarRef}
        className={`flex flex-col border-l bg-background transition-all duration-300 ${isSidebarOpen ? '' : 'w-0 opacity-0 overflow-hidden'}`}
        style={{ width: isSidebarOpen ? sidebarWidth : 0 }}
      >
        <header className="flex items-center justify-between border-b px-4 py-3">
          <div className="flex items-center gap-2">
            <h3 className="flex items-center gap-2 text-sm font-semibold">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2A10 10 0 0 0 2 12" stroke="#EA4335" strokeWidth="4" />
                <path d="M12 2A10 10 0 0 1 22 12" stroke="#4285F4" strokeWidth="4" />
                <path d="M22 12A10 10 0 0 1 12 22" stroke="#34A853" strokeWidth="4" />
                <path d="M12 22A10 10 0 0 1 2 12" stroke="#FBBC04" strokeWidth="4" />
              </svg>
              <span>Agent</span>
            </h3>
          </div>
          <div className="flex items-center gap-2">
            {/* New Chat Button */}
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground hover:text-foreground"
              onClick={startNewChat}
              title="New Chat"
            >
              <MessageSquare className="h-4 w-4" />
              <span className="sr-only">New Chat</span>
            </Button>

            {/* History Dropdown */}
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                className={`h-8 w-8 text-muted-foreground hover:text-foreground ${isHistoryMenuOpen ? 'bg-muted' : ''}`}
                onClick={() => setIsHistoryMenuOpen(!isHistoryMenuOpen)}
                title="History"
              >
                <div style={{ transform: 'rotate(0deg)' }}>
                  {/* Clock Icon can be imported or SVG */}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" /></svg>
                </div>
              </Button>

              {isHistoryMenuOpen && (
                <div className="absolute left-0 top-full z-50 mt-1 w-64 rounded-md border bg-popover shadow-md animate-in fade-in zoom-in-95 max-h-[400px] overflow-y-auto">
                  <div className="px-3 py-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider border-b sticky top-0 bg-popover">
                    Recent Conversations
                  </div>
                  {history.length === 0 ? (
                    <div className="p-4 text-center text-xs text-muted-foreground">No history found</div>
                  ) : (
                    history.map((item) => (
                      <div
                        key={item.id}
                        className={`group flex items-center w-full hover:bg-muted transition-colors border-b border-muted/20 ${sessionId === item.id ? 'bg-muted/50' : ''}`}
                      >
                        <button
                          className="flex-1 px-3 py-2 text-left text-xs"
                          onClick={() => loadSession(item.id)}
                        >
                          <div className={`line-clamp-1 ${sessionId === item.id ? 'font-medium' : ''}`}>{item.title || "Untitled Conversation"}</div>
                          <div className="text-[10px] text-muted-foreground mt-0.5">
                            {new Date(item.updated_at).toLocaleDateString()} {new Date(item.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </div>
                        </button>
                        <button
                          className="p-2 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => deleteSession(e, item.id)}
                          title="Delete Conversation"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="h-4 w-px bg-border mx-1" />
            {/* Test Controls - Scenarios Dropdown */}
            <div className="relative">
              <div className="relative">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsTestMenuOpen(!isTestMenuOpen)}
                  className="h-8 gap-1 text-xs"
                >
                  Scenarios <ChevronDown className="h-3 w-3 opacity-50" />
                </Button>
                {isTestMenuOpen && (
                  <div className="absolute right-0 top-full z-50 mt-1 w-48 rounded-md border bg-popover shadow-md animate-in fade-in zoom-in-95">
                    <div className="px-3 py-2 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider border-b">
                      TEST SCENARIOS
                    </div>
                    {datasetConfig.test_scenarios.map((item, i) => (
                      <button
                        key={i}
                        className="w-full px-3 py-2 text-left text-xs hover:bg-muted focus:bg-muted transition-colors"
                        onClick={() => runScenario(item.question)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <Button
              variant={isAutoTesting ? "secondary" : "ghost"}
              size="sm"
              onClick={() => setIsAutoTesting(!isAutoTesting)}
              className="h-8 gap-1 text-xs"
              title={isAutoTesting ? "Stop Auto Test" : "Start Auto Test"}
            >
              <LayoutDashboard size={14} />
              <span>{isAutoTesting ? "Stop" : "Auto Test"}</span>
            </Button>

            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => setIsSidebarOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
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

                {/* Auto-Generated Chart */}
                {msg.chartConfig && (
                  <div className="mt-4 p-4 bg-background rounded-lg border h-[300px]">
                    <ChartRenderer config={msg.chartConfig} />
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
              <div className="bg-muted text-foreground relative max-w-[85%] rounded-lg p-3 text-sm shadow-sm flex items-center gap-3">
                <Loader2 className="animate-spin text-primary" size={16} />
                <span className="animate-pulse">{currentThought || (isLongQuery ? "Thinking..." : "Processing...")}</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <footer className="border-t bg-background p-4 flex flex-col gap-2">
          {/* Agent Mode Toggle */}
          <div className="flex justify-center gap-1 mb-2">
            <Button
              variant={agentType === 'fast' ? "default" : "secondary"}
              size="sm"
              onClick={() => setAgentType('fast')}
              className="h-7 text-xs px-3"
              title="Fast Mode - Quick answers"
            >
              <Zap size={12} className="mr-1.5" /> Fast
            </Button>
            <Button
              variant={agentType === 'deep' ? "default" : "secondary"}
              size="sm"
              onClick={() => setAgentType('deep')}
              className="h-7 text-xs px-3"
              title="Deep Analysis Mode"
            >
              <Brain size={12} className="mr-1.5" /> Deep
            </Button>
            <Button
              variant={agentType === 'mcp' ? "default" : "secondary"}
              size="sm"
              onClick={() => setAgentType('mcp')}
              className="h-7 text-xs px-3"
              title="MCP Mode"
            >
              <Code size={12} className="mr-1.5" /> MCP
            </Button>
          </div>
          <div className="flex w-full items-center space-x-2">
            <Input
              type="text"
              placeholder="Query gaming data..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isLoading}
              className="flex-1"
            />
            <Button
              type={isLoading ? "button" : "submit"}
              onClick={isLoading ? handleStop : handleSubmit}
              disabled={!input.trim() && !isLoading}
              size="icon"
              variant={isLoading ? "destructive" : "default"}
            >
              {isLoading ? <Square className="h-4 w-4" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
        </footer>

      </aside>
    </div>
  )
}

export default App
