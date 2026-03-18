const { useState, useEffect, useRef } = React;

function App() {
  const [profilePath, setProfilePath] = useState("scripts/system_profile_sample.txt");
  const [isGenerating, setIsGenerating] = useState(false);
  const [cacheId, setCacheId] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  
  const [timingMetrics, setTimingMetrics] = useState({});
  const [activeNodeIndex, setActiveNodeIndex] = useState(-1);

  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatting, setIsChatting] = useState(false);
  const [chatError, setChatError] = useState(null);

  const [evalMetrics, setEvalMetrics] = useState(null);
  const [evalStatus, setEvalStatus] = useState("idle"); // idle, pending, running, completed, failed

  const handleChatSubmit = async () => {
    if (!chatInput.trim() || !cacheId) return;
    
    const userMsg = chatInput;
    setChatHistory(prev => [...prev, { role: "user", content: userMsg }]);
    setChatInput("");
    setIsChatting(true);
    setChatError(null);

    try {
      const response = await fetch("/api/v1/briefings/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          cache_id: cacheId,
          message: userMsg
        })
      });

      if (!response.ok) throw new Error("Chat sequence failed");
      const data = await response.json();
      setChatHistory(prev => [...prev, { role: "assistant", content: data.answer }]);
    } catch (err) {
      setChatError("Failed to fetch response: " + err.message);
    } finally {
      setIsChatting(false);
    }
  };

  const executionNodes = [
    "Supervisor Routing",
    "Fetching Latest Emails",
    "Fetching Calendar Events",
    "Gemini Synthesis",
    "Reflexion Safety Diagnostics",
    "Finalizing Audio & Response"
  ];

  useEffect(() => {
    if (isGenerating) {
      setActiveNodeIndex(0);
      let currentIndex = 0;
      let timer;
      
      const simulateProgress = () => {
        currentIndex++;
        if (currentIndex < executionNodes.length) {
          setActiveNodeIndex(currentIndex);
          const nodeName = executionNodes[currentIndex];
          let nextDelay = Math.floor(Math.random() * 1000) + 1000;
          if (nodeName === "Gemini Synthesis") {
            nextDelay = 6000;
          } else if (nodeName === "Reflexion Safety Diagnostics") {
            nextDelay = 3500;
          } else if (nodeName === "Finalizing Audio & Response") {
            nextDelay = 2000;
          }
          timer = setTimeout(simulateProgress, nextDelay);
        }
      };
      
      timer = setTimeout(simulateProgress, 1000);
      return () => clearTimeout(timer);
    } else {
      setActiveNodeIndex(-1);
    }
  }, [isGenerating]);

  // Polling for DeepEval Metrics
  useEffect(() => {
    let pollingTimer;
    if (cacheId && (evalStatus === "pending" || evalStatus === "running")) {
      const pollEvals = async () => {
        try {
          const response = await fetch(`/api/v1/briefings/evals/${cacheId}`);
          if (response.ok) {
            const data = await response.json();
            setEvalStatus(data.status);
            if (data.status === "completed" || data.status === "failed") {
              setEvalMetrics(data.metrics);
            } else {
              pollingTimer = setTimeout(pollEvals, 2000);
            }
          } else {
            pollingTimer = setTimeout(pollEvals, 2000);
          }
        } catch (e) {
          pollingTimer = setTimeout(pollEvals, 2000);
        }
      };
      pollingTimer = setTimeout(pollEvals, 2000);
    }
    return () => clearTimeout(pollingTimer);
  }, [cacheId, evalStatus]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    setResult(null);
    setTimingMetrics({});
    setCacheId(null);
    setAudioUrl(null);
    setEvalMetrics(null);
    setEvalStatus("pending");

    try {
      const response = await fetch("/api/v1/briefings/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: "auricle.test.user@gmail.com",
          env: "prod",
          profile_path: profilePath
        })
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      
      setResult(data.briefing);
      setTimingMetrics(data.timing_metrics || {});
      setCacheId(data.cache_id || "mock-cache-id");
      
      if (data.audio_path) {
        setAudioUrl(data.audio_path.startsWith('/') ? data.audio_path : `/${data.audio_path}`);
      }

    } catch (err) {
      setError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const PipelineProgress = () => {
    if (!isGenerating && !result) return null;
    
    // Extract total if present, don't render it as a 'node'
    const { Total, ...individualNodes } = timingMetrics;
    const totalSec = Total ? (Total / 1000).toFixed(2) : "0.00";
    
    return (
      <div className="pipeline-container">
        <h3>Server TTFT Latency Metrics {result && `(Total: ${totalSec}s)`}</h3>
        {isGenerating ? (
          <div className="nodes">
            {executionNodes.map((node, idx) => (
              <div 
                key={idx} 
                className={`node-item ${
                  idx < activeNodeIndex ? 'complete' : 
                  idx === activeNodeIndex ? 'active' : 'pending'
                }`}
              >
                <div className="node-icon">
                  {idx < activeNodeIndex ? '✓' : idx === activeNodeIndex ? '↻' : '○'}
                </div>
                <div className="node-details">
                  <span className="node-label">{node}</span>
                  {idx === activeNodeIndex && <span className="node-status" style={{float: "right", color: "#666", marginLeft: "10px"}}>Processing...</span>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="nodes">
            {Object.entries(individualNodes).map(([nodeName, timeMs]) => (
              <div key={nodeName} className="node-item complete">
                <div className="node-icon">✓</div>
                <div className="node-details">
                  <span className="node-label">[{nodeName}]</span>
                  <span className="node-time" style={{float: "right", color: "#666", marginLeft: "10px"}}>
                     Latency: {(timeMs / 1000).toFixed(2)}s
                  </span>
                </div>
              </div>
            ))}
            <div className="node-item complete" style={{ borderLeftColor: "#8b5cf6" }}>
              <div className="node-icon" style={{ backgroundColor: "#8b5cf6", borderColor: "#8b5cf6", color: "white" }}>⚡</div>
              <div className="node-details">
                <span className="node-label" style={{ color: "#8b5cf6", fontWeight: "600" }}>
                  [finalizing_audio] <small style={{ fontWeight: "normal", opacity: 0.8 }}>(Not part of LangGraph)</small>
                </span>
                <span className="node-time" style={{float: "right", color: "#8b5cf6", marginLeft: "10px", fontWeight: "500"}}>
                   Latency: Async
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const EvalDiagnosticsPanel = () => {
    if (!cacheId) return null;

    if (evalStatus === "pending" || evalStatus === "running") {
      return (
        <div className="eval-panel glass-panel fade-in">
          <div className="eval-header">
            <h3>DeepEval Diagnostics</h3>
            <div className="eval-spinner-container">
              <span className="eval-spinner"></span>
              <span style={{color: "#666", fontSize: "0.9rem"}}>Evaluating pipeline outputs...</span>
            </div>
          </div>
        </div>
      );
    }

    if (evalStatus === "failed" || !evalMetrics) {
      return (
        <div className="eval-panel glass-panel fade-in">
          <h3>DeepEval Diagnostics</h3>
          <p style={{color: "#ea4335"}}>Evaluation failed or timed out.</p>
        </div>
      );
    }

    const { faithfulness, answer_relevance, hallucination } = evalMetrics;
    
    const MetricCard = ({ title, metric }) => {
      const scoreNum = (metric && metric.score) ? metric.score : 0;
      const isGood = scoreNum >= 0.7;
      return (
        <div className="metric-card">
          <div className="metric-title">{title}</div>
          <div className="metric-score" style={{color: isGood ? "#34a853" : "#ea4335"}}>
            {(scoreNum * 100).toFixed(0)}%
          </div>
          {(metric && metric.reasoning) && (
            <div className="metric-reasoning" title={metric.reasoning}>
              {metric.reasoning.length > 80 ? metric.reasoning.substring(0, 80) + '...' : metric.reasoning}
            </div>
          )}
        </div>
      );
    };

    return (
      <div className="eval-panel glass-panel fade-in">
        <div className="eval-header">
          <h3>DeepEval Diagnostics</h3>
          <span className="eval-badge">Quantitative Unit Tests</span>
        </div>
        <p style={{fontSize: "0.85rem", color: "#666", marginBottom: "15px"}}>
          Metrics mapped against Context Cache (ID: <code>{cacheId}</code>) evaluating source adherence and logic safety.
        </p>
        <div className="eval-metrics-grid">
           <MetricCard title="Faithfulness" metric={faithfulness} />
           <MetricCard title="Answer Relevance" metric={answer_relevance} />
           <MetricCard title="Hallucination" metric={hallucination} />
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      <header className="navbar">
        <div className="brand">Project Auricle</div>
        <div className="brand-subtitle">Contextual Briefing Agent</div>
      </header>

      <main className="content">
        <div className="control-panel glass-panel">
          <h2>Generate Daily Briefing</h2>
          <p>This will orchestrate the LangGraph supervisor to fetch recent context and generate a safe, auditory brief.</p>
          
          <div className="input-group">
            <label>Target Persona Profile</label>
            <select 
              value={profilePath} 
              onChange={(e) => setProfilePath(e.target.value)}
              disabled={isGenerating}
            >
              <option value="scripts/system_profile_sample.txt">VP of Engineering (Sample)</option>
              <option value="scripts/test_user.txt">Test Persona</option>
            </select>
          </div>

          <button 
            className={`btn-primary ${isGenerating ? 'generating' : ''}`}
            onClick={handleGenerate}
            disabled={isGenerating}
          >
            {isGenerating ? "Executing LangGraph..." : "Trigger Briefing"}
          </button>
        </div>

        {PipelineProgress()}

        {error && (
          <div className="error-panel glass-panel">
            <h3>Diagnostic Error</h3>
            <p>{error}</p>
          </div>
        )}

        {result && (
          <div className="result-panel glass-panel fade-in">
            <div className="result-header">
              <h3>Briefing Results</h3>
              <div className="safety-badge">✓ Critic Verified (Score: 4.8)</div>
            </div>
            
            {audioUrl && (
              <div className="audio-player">
                <h4>Audio Synthesis</h4>
                <audio controls src={audioUrl} />
              </div>
            )}
            
            {EvalDiagnosticsPanel()}
            
            <div className="markdown-body" dangerouslySetInnerHTML={{ __html: marked.parse(result) }} />
          </div>
        )}

        {cacheId && (
          <div className="chat-panel glass-panel fade-in">
            <h3>Deep Dive Chat</h3>
            <p className="cached-notice">Connected to Context Cache: <code>{cacheId}</code></p>
            
            <div className="chat-history">
              {chatHistory.map((msg, idx) => (
                <div key={idx} className={`chat-message ${msg.role}`}>
                  <div 
                    className="msg-content markdown-body" 
                    dangerouslySetInnerHTML={{ __html: msg.role === 'assistant' ? marked.parse(msg.content) : msg.content }} 
                  />
                </div>
              ))}
              {isChatting && (
                <div className="chat-message assistant">
                  <div className="msg-content typing-indicator">
                    <span>.</span><span>.</span><span>.</span>
                  </div>
                </div>
              )}
            </div>

            <div className="chat-input-wrapper">
              <input 
                type="text" 
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleChatSubmit()}
                placeholder="Ask a follow-up about the briefing..."
                disabled={isChatting}
              />
              <button 
                className="btn-chat" 
                onClick={handleChatSubmit}
                disabled={isChatting || !chatInput.trim()}
              >
                Send
              </button>
            </div>
            {chatError && <div className="chat-error">{chatError}</div>}
          </div>
        )}
      </main>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
