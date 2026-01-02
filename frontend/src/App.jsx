import { useState, useRef, useEffect } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { Send, Bot, User, Loader2, Code, X, ExternalLink, ChevronDown, ChevronUp, Info, AlertTriangle, LayoutDashboard, MessageSquare, Menu, ChevronRight, Maximize2, Minimize2, LogOut, Zap, Brain, RefreshCw, Square } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import JSON5 from 'json5'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement, Filler } from 'chart.js';
import { Bar, Line, Pie, Scatter } from 'react-chartjs-2';

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
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

import { TEST_QUESTIONS } from './test_questions';
import { DASHBOARDS } from './config/dashboards';
import { STARTER_QUESTIONS, DEEP_TEST_QUESTIONS } from './config/questions';


const ChartRenderer = ({ config }) => {
  if (!config || !config.data) return null;

  const hasRightAxis = config.series.some(s => s.yAxisID === 'right');

  const options = {
    responsive: true,
    interaction: {
      mode: 'index',
      intersect: false,
    },
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: config.title,
      },
    },
    scales: {
      x: {
        stacked: config.stacked
      },
      y: {
        type: 'linear',
        display: true,
        position: 'left',
        stacked: config.stacked,
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
    <div className="thoughts-accordion">
      <button
        className="thoughts-header-btn"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="thoughts-summary">
          <span>Thinking Process ({thoughts.length} steps)</span>
        </div>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isOpen && (
        <div className="thoughts-list">
          {thoughts.map((thought, i) => (
            <div key={i} className="thought-item">
              <span className="thought-dot"></span>
              {thought}
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
    <div className="timing-wrapper">
      <button className="timing-btn" onClick={() => setIsOpen(!isOpen)} title="Show Execution Timings">
        <Info size={14} />
        <span className="timing-badge">{Math.round(elapsed)}s</span>
      </button>
      {isOpen && (
        <div className="timing-popup">
          <div className="timing-header">
            <h4>Execution Breakdown</h4>
            <button onClick={() => setIsOpen(false)}><X size={14} /></button>
          </div>
          <div className="timing-list">
            {timings.steps.map((step, i) => (
              <div key={i} className="timing-item">
                <span className="timing-label" title={step.label}>{step.label}</span>
                <span className="timing-duration">{step.duration ? step.duration.toFixed(1) + 's' : ''}</span>
              </div>
            ))}
            <div className="timing-total">
              <span>Total Time</span>
              <span>{elapsed.toFixed(1)}s</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Helper component for signed Looker links
const LookerLink = ({ url }) => {
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/embed`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target_url: url })
      });

      if (!response.ok) throw new Error('Signing failed');

      const data = await response.json();
      window.open(data.url, '_blank');
    } catch (err) {
      console.error("Failed to open Looker link:", err);
      // Fallback to trying to open original if signing fails (though likely won't work for embed users)
      window.open(url, '_blank');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <a href={url} onClick={handleClick} className="action-link" style={{ cursor: 'pointer', opacity: isLoading ? 0.7 : 1 }}>
      {isLoading ? <Loader2 size={14} className="animate-spin" /> : <ExternalLink size={14} />}
      {isLoading ? ' Opening...' : ' View Source Query'}
    </a>
  );
};

function App() {
  const [messages, setMessages] = useState([
    { role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }
  ])
  const [accessToken, setAccessToken] = useState(localStorage.getItem('looker_access_token'))
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isDeepMode, setIsDeepMode] = useState(false) // Toggle state
  const [isLongQuery, setIsLongQuery] = useState(false);
  const messagesEndRef = useRef(null)
  // Generate a unique session ID when the component mounts
  const [sessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9))
  const [isAutoTesting, setIsAutoTesting] = useState(false)
  const autoTestIntervalRef = useRef(null)

  // State for Deep Test Suite
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testLogs, setTestLogs] = useState([]);
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [currentThought, setCurrentThought] = useState(null); // Track live status

  // Questions moved to config/questions.js

  const [isTestMenuOpen, setIsTestMenuOpen] = useState(false);

  const runScenario = async (question) => {
    setIsTestMenuOpen(false);
    setInput(question);
    // Wait a bit to show the question
    await new Promise(r => setTimeout(r, 500));
    // Submit
    await handleSubmit(null, question);
  };

  const [activeDashboard, setActiveDashboard] = useState(DASHBOARDS[0]?.id || 'overview'); // Changed to use ID
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [sidebarWidth, setSidebarWidth] = useState(600);
  const [isResizing, setIsResizing] = useState(false);

  // LOOKER SIGNED URL STATE
  const [signedUrl, setSignedUrl] = useState(null);
  const [embedError, setEmbedError] = useState(null);
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

  // Fetch Signed URL when dashboard or token changes
  useEffect(() => {
    const fetchSignedUrl = async () => {
      if (!activeDashboard || !accessToken) return;

      const dashboard = DASHBOARDS.find(d => d.id === activeDashboard);
      if (!dashboard) return;

      try {
        setEmbedError(null);
        // Don't clear URL immediately to avoid flash if possible, but for security/logic:
        setSignedUrl(null);

        const requestPayload = { target_url: dashboard.url };
        console.log('Fetching signed embed URL for:', dashboard.url);

        const response = await fetch(`${API_BASE_URL}/api/embed`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            // We don't necessarily strictly need auth for this particular demo endpoint, 
            // but good practice to pass if we had middleware.
            // For now server.py assumes it's open or internal. 
          },
          body: JSON.stringify(requestPayload)
        });

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.error || 'Failed to sign embed URL');
        }

        const data = await response.json();
        setSignedUrl(data.url);

      } catch (e) {
        console.error("Embed Error:", e);
        setEmbedError(e.message);
      }
    };

    fetchSignedUrl();
  }, [activeDashboard, accessToken]); // Dependency on activeDashboard and login state


  const login = useGoogleLogin({
    onSuccess: tokenResponse => {
      console.log(tokenResponse);
      setAccessToken(tokenResponse.access_token);
      localStorage.setItem('looker_access_token', tokenResponse.access_token);
    },
    onError: error => console.log('Login Failed:', error),
    scope: 'https://www.googleapis.com/auth/cloud-platform'
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
      deep_analysis: isDeepMode,
      force_refresh: options.forceRefresh || false
    }
    console.log('Sending request:', requestPayload)

    try {
      console.log(`Fetching from ${API_BASE_URL}/chat...`)
      const response = await fetch(`${API_BASE_URL}/chat`, {
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
            // Assume it's data content
            let contentLine = line;
            if (line.startsWith('DATA: ')) {
              contentLine = line.substring(6);
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
      if (currentIndex >= TEST_QUESTIONS.length || !isAutoTesting) {
        setIsAutoTesting(false);
        return;
      }

      const question = TEST_QUESTIONS[currentIndex];
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
          // Fallthrough to render as code if parsing fails
        }
      }

      // Handle Metadata - REMOVED per user request
      /*
      const isMetadata = !inline && (
        lang === 'json-metadata' ||
        (lang === 'json' && (
          String(children).includes('"fields":') ||
          String(children).includes('"filters":') ||
          String(children).includes('"sql":') ||
          String(children).includes('"metric":') ||
          String(children).includes('"query_details":')
        ))
      );
      if (isMetadata) {
         return null; // Don't render anything
      }
      */

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
      <div className="login-container">
        <div className="login-card glass">
          <h1>Gaming Analytics</h1>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '2rem' }}>Sign in to access your organization dashboard</p>
          <button onClick={() => login()} className="login-btn">
            Connect to Looker
          </button>
        </div>
      </div>
    )
  }

  const currentDashboard = DASHBOARDS.find(d => d.id === activeDashboard);

  return (
    <div className="app-container">
      {/* Navigation Rail */}


      {/* Main Workspace */}
      <div className="main-workspace">
        <header className="workspace-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ padding: 8, background: 'rgba(37, 99, 235, 0.1)', borderRadius: 8 }}>
              <Bot className="bot-icon" style={{ color: 'var(--primary-color)' }} size={24} />
            </div>
            <span style={{ fontWeight: 600, fontSize: '1.2rem', color: 'var(--text-primary)', whiteSpace: 'nowrap' }}>Gaming Analytics</span>

            {/* Dashboard Selection Dropdown */}
            <div style={{ position: 'relative', marginLeft: '1rem' }}>
              <select
                value={activeDashboard}
                onChange={(e) => setActiveDashboard(e.target.value)}
                style={{
                  appearance: 'none',
                  padding: '8px 32px 8px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--border-color)',
                  background: 'var(--bg-primary)',
                  color: 'var(--text-primary)',
                  fontSize: '0.9rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  outline: 'none',
                  minWidth: '200px'
                }}
              >
                {DASHBOARDS.map((dash) => (
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
        className={`assistant-sidebar ${isSidebarOpen ? '' : 'collapsed'}`}
        style={{ width: isSidebarOpen ? sidebarWidth : 0 }}
      >
        <header className="sidebar-header">
          <div className="sidebar-title">
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, textTransform: 'none' }}>
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2A10 10 0 0 0 2 12" stroke="#EA4335" strokeWidth="4" />
                <path d="M12 2A10 10 0 0 1 22 12" stroke="#4285F4" strokeWidth="4" />
                <path d="M22 12A10 10 0 0 1 12 22" stroke="#34A853" strokeWidth="4" />
                <path d="M12 22A10 10 0 0 1 2 12" stroke="#FBBC04" strokeWidth="4" />
              </svg>
              <span>Agent</span>
            </h3>
          </div>
          <div className="sidebar-actions" style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            {/* Mode Toggle */}
            <div className="mode-toggle-container">
              <button
                className={`mode-toggle-btn ${!isDeepMode ? 'active' : ''}`}
                onClick={() => setIsDeepMode(false)}
                title="Fast Mode"
              >
                <Zap size={14} />
                <span>Fast</span>
              </button>
              <button
                className={`mode-toggle-btn ${isDeepMode ? 'active' : ''}`}
                onClick={() => setIsDeepMode(true)}
                title="Deep Analysis Mode"
              >
                <Brain size={14} />
                <span>Deep</span>
              </button>
            </div>
            {/* Test Controls - Scenarios Dropdown */}
            <div style={{ marginRight: 'auto', display: 'flex', gap: '0.5rem', position: 'relative' }}>
              <div style={{ position: 'relative' }}>
                <button
                  className="test-menu-trigger"
                  onClick={() => setIsTestMenuOpen(!isTestMenuOpen)}
                  title="Scenarios"
                  style={{ width: 'auto', padding: '0 12px', fontSize: '0.8rem', height: 32 }}
                >
                  Scenarios <ChevronDown size={14} style={{ marginLeft: 4, opacity: 0.7 }} />
                </button>
                {isTestMenuOpen && (
                  <div className="test-menu-dropdown glass" style={{ right: 0, width: 200, top: '100%' }}>
                    <div style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      TEST SCENARIOS
                    </div>
                    {DEEP_TEST_QUESTIONS.map((item, i) => (
                      <button
                        key={i}
                        className="test-menu-item"
                        onClick={() => runScenario(item.question)}
                      >
                        {item.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            <button
              className={`nav-item ${isAutoTesting ? 'active' : ''}`}
              onClick={() => setIsAutoTesting(!isAutoTesting)}
              title={isAutoTesting ? "Stop Auto Test" : "Start Auto Test"}
              style={{ width: 'auto', padding: '0 12px', height: 32 }}
            >
              <LayoutDashboard size={16} /> {/* Placeholder icon for test */}
              <span style={{ fontSize: '0.8rem' }}>{isAutoTesting ? "Stop" : "Auto Test"}</span>
            </button>

            <button className="nav-item" onClick={() => setIsSidebarOpen(false)} style={{ width: 32, height: 32 }}>
              <X size={16} />
            </button>
          </div>
        </header>

        <div className="chat-messages">
          {messages.map((msg, index) => (
            <div key={index} className={`message ${msg.role}`}>
              <div className="message-header" style={{ justifyContent: msg.role === 'agent' ? 'flex-start' : 'flex-end' }}>
                {msg.role === 'agent' && (
                  <span className="message-role" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <Bot size={14} /> Analyst
                  </span>
                )}
                {/* User label hidden for cleaner look */}

                {msg.role === 'agent' && msg.timings && <TimingPopup timings={msg.timings} />}
              </div>

              <div className="message-bubble">
                {msg.thoughts && msg.thoughts.length > 0 && (
                  <ThinkingProcessAccordion
                    thoughts={msg.thoughts}
                    isComplete={index !== messages.length - 1 || !isLoading}
                  />
                )}
                <div className="message-text">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={markdownComponents}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>

                {msg.link && (
                  <div className="message-actions">
                    <LookerLink url={msg.link} />
                  </div>
                )}

                {msg.role === 'agent' && !msg.isStreaming && msg.thoughts && msg.thoughts.some(t => t.includes("Found similar question in cache")) && (
                  <div className="message-actions" style={{ marginTop: '8px' }}>
                    <button
                      className="action-link"
                      onClick={() => {
                        // Find the user prompt for this message. It's normally the one right before.
                        // We are mapping 'messages', so we have 'i'.
                        const prompt = messages[i - 1]?.content;
                        if (prompt) {
                          handleSubmit(null, prompt, { forceRefresh: true });
                        }
                      }}
                      disabled={isLoading}
                      style={{ cursor: isLoading ? 'not-allowed' : 'pointer', background: 'none', border: 'none', display: 'flex', alignItems: 'center', gap: '4px', color: '#64748b', fontSize: '0.8rem', padding: 0 }}
                    >
                      <RefreshCw size={14} className={isLoading ? "animate-spin" : ""} />
                      Refresh Data (Bypass Cache)
                    </button>
                  </div>
                )}

                {msg.suggestions && msg.suggestions.length > 0 && (
                  <div className="suggestions-container">
                    <div className="suggestions-list">
                      {msg.suggestions.map((suggestion, i) => (
                        <button key={i} className="suggestion-chip" onClick={() => handleSubmit(null, suggestion)}>
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
            <div className="starter-questions-container">
              <div className="starter-header">
                <span className="sparkle-icon">✨</span>
                <span className="starter-label">Suggested Queries</span>
              </div>
              <div className="starter-list">
                {STARTER_QUESTIONS.map((q, i) => (
                  <button key={i} onClick={() => handleSubmit(null, q)} className="starter-chip">
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {isLoading && (
            <div className="message agent">
              <div className="message-bubble">
                <div className="message-text loading" style={{ color: 'var(--primary-color)' }}>
                  <Loader2 className="animate-spin" size={16} />
                  <span>{currentThought || (isLongQuery ? "Thinking..." : "Processing...")}</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <footer className="assistant-input-area">
          <form onSubmit={handleSubmit} className="input-wrapper">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Query gaming data..."
              disabled={isLoading}
            />
            <button
              type={isLoading ? "button" : "submit"}
              className={`send-btn ${isLoading ? 'stop-btn' : ''}`}
              disabled={!input.trim() && !isLoading}
              onClick={isLoading ? handleStop : undefined}
            >
              {isLoading ? <Square size={20} fill="currentColor" /> : <Send size={20} />}
            </button>
          </form>
        </footer>

      </aside>
    </div>
  )
}

export default App
