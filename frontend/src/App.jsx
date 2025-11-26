import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2, Code, X } from 'lucide-react'
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

const ChartRenderer = ({ config }) => {
  if (!config || !config.data) return null;

  const options = {
    responsive: true,
    plugins: {
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: config.title,
      },
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

function App() {
  const [messages, setMessages] = useState([
    { role: 'agent', content: 'Hello! I am your mobile gaming data analyst. How can I help you today?' }
  ])
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

  const TEST_QUESTIONS = [
    "What is the total revenue for the last 30 days?",
    "Show me a trend of daily active users for the last week.",
    "What are the top 3 games by revenue?",
    "Break down the number of sessions by device platform.",
    "How many new users did we acquire yesterday?",
    "Show me the revenue by country as a pie chart."
  ];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
      console.log('Fetching from http://127.0.0.1:5000/chat...')
      const response = await fetch('http://127.0.0.1:5000/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestPayload),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.error || 'Failed to fetch')
      }
      // Initialize empty agent message
      setMessages(prev => [...prev, { role: 'agent', content: '', thoughts: [] }])
      setIsLoading(false)

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
            setMessages(prev => {
              const newMessages = [...prev]
              const lastMsg = newMessages[newMessages.length - 1]
              if (lastMsg.role === 'agent') {
                const currentThoughts = lastMsg.thoughts || []
                if (!currentThoughts.includes(thought)) {
                  const updatedThoughts = [...currentThoughts, thought].slice(-2)
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

      // Update debug panel with detailed parsing info
      setLastResponse({
        fullRawResponse: parsedChunks.join('\n'),
        parsedContent: fullResponse,
        parsedChunks: parsedChunks
      })
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
      const response = await fetch('http://127.0.0.1:5000/reauth', { method: 'POST' })
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
      // Check for 'json-chart' specifically, or if the language is 'json' and it looks like a chart config
      const isChart = !inline && match && (match[1] === 'json-chart' || (match[1] === 'json' && String(children).includes('"type":')));

      if (isChart) {
        try {
          const config = JSON.parse(String(children).replace(/\n$/, ''))
          // Only render if it has the expected chart structure
          if (config.type && config.data && config.series) {
            return <ChartRenderer config={config} />
          }
        } catch (e) {
          // If parsing fails, fall back to code block
          return <code className={className} {...props}>{children}</code>
        }
      }
      return <code className={className} {...props}>{children}</code>
    }
  }).current

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
            <button
              className="reauth-btn"
              onClick={handleReauth}
              title="Re-authenticate with Google Cloud"
            >
              Re-auth
            </button>
            <button
              className={`payload-toggle ${showPayload ? 'active' : ''}`}
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
              <div key={index} className={`message ${msg.role}`}>
                <div className="message-content">
                  <div className="message-header">
                    {msg.role === 'agent' ? <Bot size={16} /> : <User size={16} />}
                    <span>{msg.role === 'agent' ? 'Analyst' : 'You'}</span>
                  </div>

                  {/* Render Thoughts */}
                  {msg.thoughts && msg.thoughts.length > 0 && (
                    <div className="thoughts-container">
                      <div className="thoughts-header">Thinking Process:</div>
                      {msg.thoughts.map((thought, i) => (
                        <div key={i} className="thought-item">
                          <span className="thought-dot"></span>
                          {thought}
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="message-text">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={markdownComponents}
                    >
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))}
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
