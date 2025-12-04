import { useState, useRef, useEffect } from 'react'
import { useGoogleLogin } from '@react-oauth/google'
import { Send, Bot, User, Loader2, Code, X, ExternalLink, ChevronDown, ChevronUp, Info } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement } from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
);
import './App.css'

const API_BASE_URL = 'http://127.0.0.1:8080';

import { TEST_QUESTIONS } from './test_questions';


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
      backgroundColor: s.fill || `hsla(${i * 60}, 70%, 50%, 0.5)`,
      borderColor: s.fill || `hsla(${i * 60}, 70%, 50%, 1)`,
      borderWidth: 1,
      yAxisID: s.yAxisID === 'right' ? 'y1' : 'y',
    })),
  };

  const renderChart = () => {
    switch (config.type) {
      case 'bar':
        return <Bar options={options} data={chartData} />;
      case 'line':
        return <Line options={options} data={chartData} />;
      case 'pie':
        // Pie charts need slightly different data structure for background colors
        const pieData = {
          ...chartData,
          datasets: chartData.datasets.map(ds => ({
            ...ds,
            backgroundColor: config.data.map((_, i) => `hsla(${i * 45}, 70%, 50%, 0.5)`),
            borderColor: config.data.map((_, i) => `hsla(${i * 45}, 70%, 50%, 1)`),
          }))
        };
        return <Pie options={options} data={pieData} />;
      default:
        return null;
    }
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

          {metadata.filters && Object.keys(metadata.filters).length > 0 && (
            <div className="metadata-section">
              <h4>Filters</h4>
              <ul>
                {Object.entries(metadata.filters).map(([key, value]) => (
                  <li key={key}>
                    <span className="metadata-key">{key}:</span> {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                  </li>
                ))}
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
                <span className="timing-duration">{step.duration ? step.duration.toFixed(1) + 's' : (elapsed - (step.startTime - timings.startTime) / 1000).toFixed(1) + 's'}</span>
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

function App() {
  const [messages, setMessages] = useState([
    { role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }
  ])
  const [accessToken, setAccessToken] = useState(localStorage.getItem('looker_access_token'))
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showPayload, setShowPayload] = useState(false)
  const [lastRequest, setLastRequest] = useState(null)
  const [lastResponse, setLastResponse] = useState(null)
  const messagesEndRef = useRef(null)
  // Generate a unique session ID when the component mounts
  const [sessionId] = useState(() => 'session_' + Math.random().toString(36).substr(2, 9))
  const [isAutoTesting, setIsAutoTesting] = useState(false)
  const autoTestIntervalRef = useRef(null)

  // State for Deep Test Suite
  const [isTestModalOpen, setIsTestModalOpen] = useState(false);
  const [testLogs, setTestLogs] = useState([]);
  const [isRunningTests, setIsRunningTests] = useState(false);

  const STARTER_QUESTIONS = [
    "Analyze the revenue trend for the last 6 months vs user acquisition.",
    "Show me total revenue by week broken down by platform.",
  ];
  const DEEP_TEST_QUESTIONS = [
    { label: "UA Performance", question: "Analyze the ROAS (Return on Ad Spend) by Campaign for the last 30 days. Which campaigns are performing best and should be scaled?" },
    { label: "Player Behavior", question: "Compare the average session length and retention rates (D1, D7) of paying users vs non-paying users for the game 'Looker Battle Royale' over the last 3 months." },
    { label: "Market Trends", question: "What are the top 3 countries by revenue for the last quarter? For these countries, how does the ARPU compare?" },
    { label: "Whale Demographics", question: "Identify the top 10% of users by total revenue. What is the breakdown of these users by Country and Platform? This helps us target high-value segments." },
    { label: "Campaign Efficiency", question: "Compare the ROAS and D7 Retention Rate for the top 5 campaigns by spend. Which campaign offers the best balance of short-term return and long-term engagement?" },
    { label: "Progression Impact", question: "Compare the Average Revenue Per User (ARPU) for users who have triggered the 'level_up' event at least 5 times vs those who haven't. Does deep progression correlate with higher spend?" },
    { label: "Geo Opportunities", question: "List the top 5 countries by number of users. For these countries, calculate the Conversion Rate (Paying Users / Total Users). Which country has high volume but low monetization?" },
    { label: "Platform Deep Dive", question: "Compare the Average Session Length and Total Revenue for 'iOS' vs 'Android' users. If one platform underperforms, break it down by Country to see if it's a regional issue." }
  ];

  const [isTestMenuOpen, setIsTestMenuOpen] = useState(false);

  const runScenario = async (question) => {
    setIsTestMenuOpen(false);
    setInput(question);
    // Wait a bit to show the question
    await new Promise(r => setTimeout(r, 500));
    // Submit
    await handleSubmit(null, question);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])



  const login = useGoogleLogin({
    onSuccess: tokenResponse => {
      console.log(tokenResponse);
      setAccessToken(tokenResponse.access_token);
      localStorage.setItem('looker_access_token', tokenResponse.access_token);
    },
    onError: error => console.log('Login Failed:', error),
    scope: 'https://www.googleapis.com/auth/cloud-platform'
  });

  // Refactored handleSubmit to accept an optional message argument and return a promise
  const handleSubmit = async (e, manualMessage = null) => {
    if (e) e.preventDefault()
    const userMessage = manualMessage || input
    if (!userMessage.trim()) return false

    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setInput('')
    setIsLoading(true)

    const requestPayload = {
      message: userMessage,
      session_id: sessionId
    }
    console.log('Sending request:', requestPayload)
    setLastRequest(requestPayload)
    setLastResponse(null)

    try {
      console.log(`Fetching from ${API_BASE_URL}/chat...`)
      const response = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(accessToken ? { 'Authorization': `Bearer ${accessToken}` } : {})
        },
        body: JSON.stringify(requestPayload),
      })

      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          logout();
          throw new Error('Session expired. Please log in again.');
        }
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch')
      }
      // Initialize empty agent message
      // Initialize empty agent message
      // Initialize empty agent message
      const startTime = Date.now();
      setMessages(prev => [...prev, { role: 'agent', content: '', thoughts: [], timings: { startTime, steps: [] } }])
      // setIsLoading(false) // Moved to end of stream

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
              thought.startsWith('Debug')) {
              continue;
            }

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
            const link = line.substring(6)
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
      setLastResponse({
        fullRawResponse: parsedChunks.join('\n'),
        parsedContent: fullResponse,
        parsedChunks: parsedChunks
      })
      setIsLoading(false)
      return true; // Signal completion

    } catch (error) {
      console.error('Error:', error)
      setMessages(prev => [...prev, { role: 'agent', content: 'Sorry, I encountered an error processing your request.' }])
      setLastResponse({ error: error.message })
      setIsLoading(false)
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

      // Handle Chart
      const isChart = !inline && match && (match[1] === 'json-chart' || (match[1] === 'json' && String(children).includes('"type":')));
      if (isChart) {
        try {
          const config = JSON.parse(String(children).replace(/\n$/, ''))
          if (config.type && config.data && config.series) {
            return <ChartRenderer config={config} />
          }
        } catch (e) {
          return <code className={className} {...props}>{children}</code>
        }
      }

      // Handle Metadata
      const isMetadata = !inline && match && (match[1] === 'json-metadata' || (match[1] === 'json' && String(children).includes('"fields":')));
      if (isMetadata) {
        try {
          const metadata = JSON.parse(String(children).replace(/\n$/, ''))
          return <MetadataAccordion metadata={metadata} />
        } catch (e) {
          return <code className={className} {...props}>{children}</code>
        }
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
        <h1>Gaming Analytics Agent</h1>
        <button onClick={() => login()} className="login-btn">
          Log-in to Looker
        </button>
      </div>
    )
  }

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-content">
          <Bot className="bot-icon" />
          <h1>Gaming Analytics Agent</h1>
          <div className="header-actions">
            <button
              className={`reauth-btn ${isAutoTesting ? 'active' : ''}`}
              onClick={() => setIsAutoTesting(!isAutoTesting)}
              title="Start/Stop Auto Test"
            >
              {isAutoTesting ? 'Stop Test' : 'Auto Test'}
            </button>
            <div className="test-menu-container">
              <button
                className={`reauth-btn ${isTestMenuOpen ? 'active' : ''}`}
                onClick={() => setIsTestMenuOpen(!isTestMenuOpen)}
                title="Select Deep Analysis Scenario"
                style={{ background: '#10b981', borderColor: 'transparent' }}
              >
                Test Scenarios
                {isTestMenuOpen ? <ChevronUp size={14} style={{ marginLeft: 4 }} /> : <ChevronDown size={14} style={{ marginLeft: 4 }} />}
              </button>
              {isTestMenuOpen && (
                <div className="test-menu-dropdown">
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
            <button
              className="reauth-btn"
              onClick={logout}
              title="Logout"
            >
              Logout
            </button>
            <button
              className={`payload - toggle ${showPayload ? 'active' : ''} `}
              onClick={() => setShowPayload(!showPayload)}
              title="Toggle Payload View"
            >
              <Code size={20} />
            </button>
          </div>
        </div>
      </header>

      <div className="main-content">
        <main className="chat-container">
          <div className="messages-list">
            {messages.map((msg, index) => (
              <div key={index} className={`message ${msg.role} `}>
                <div className="message-content">
                  <div className="message-header">
                    <div className="message-role">
                      {msg.role === 'agent' ? <Bot size={16} /> : <User size={16} />}
                      <span>{msg.role === 'agent' ? 'Analyst' : 'You'}</span>
                    </div>
                    {msg.role === 'agent' && msg.timings && <TimingPopup timings={msg.timings} />}
                  </div>

                  {/* Render Thoughts */}
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

                  {/* Render Explore Link */}
                  {msg.link && (
                    <div className="message-actions">
                      <a
                        href={msg.link}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="action-link"
                      >
                        <ExternalLink size={14} />
                        Open in Looker
                      </a>
                    </div>
                  )}

                  {/* Render Suggestions */}
                  {msg.suggestions && msg.suggestions.length > 0 && (
                    <div className="suggestions-container">
                      <div className="suggestions-label">Related Questions:</div>
                      <div className="suggestions-list">
                        {msg.suggestions.map((suggestion, i) => (
                          <button
                            key={i}
                            className="suggestion-chip"
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
              <div className="starter-questions-container">
                <div className="starter-header">
                  <h3>Try asking...</h3>
                </div>
                <div className="starter-grid">
                  {STARTER_QUESTIONS.map((q, i) => (
                    <button
                      key={i}
                      onClick={() => handleSubmit(null, q)}
                      className="starter-card"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {isLoading && (
              <div className="message agent">
                <div className="message-content">
                  <div className="message-header">
                    <Bot size={16} />
                    <span>Analyst</span>
                  </div>
                  <div className="message-text loading">
                    <Loader2 className="animate-spin" size={20} />
                    <span>Analyzing data...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        </main>

        {showPayload && (
          <aside className="payload-panel">
            <div className="payload-header">
              <h2>Debug Payloads</h2>
              <button onClick={() => setShowPayload(false)} className="close-btn">
                <X size={18} />
              </button>
            </div>
            <div className="payload-content">
              <div className="payload-section">
                <h3>Last Request</h3>
                <pre>{lastRequest ? JSON.stringify(lastRequest, null, 2) : 'No request yet'}</pre>
              </div>
              <div className="payload-section">
                <h3>Last Response</h3>
                <pre>{lastResponse ? JSON.stringify(lastResponse, null, 2) : 'No response yet'}</pre>
              </div>
            </div>
          </aside>
        )}
      </div>

      <footer className="input-area">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your gaming data..."
            disabled={isLoading}
          />
          <button type="submit" disabled={isLoading || !input.trim()}>
            <Send size={20} />
          </button>
        </form>
      </footer>

    </div>
  )
}

export default App
