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
  const [evalStatus, setEvalStatus] = useState("idle");
  const [safetyPassed, setSafetyPassed] = useState(null);
  const [criticScore, setCriticScore] = useState(null);
  const [audioFallback, setAudioFallback] = useState(false);

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
    setSafetyPassed(null);
    setCriticScore(null);
    setAudioFallback(false);
    
    // Stop any currently playing browser TTS before starting fresh
    if (window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }

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
      setSafetyPassed(data.safety_passed);
      setCriticScore(data.critic_score);
      
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
      <div className="diagnostic-card fade-in">
        <h4 className="diag-title">Pipeline Latency {result && <span className="metrics-total">({totalSec}s)</span>}</h4>
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
                  {idx === activeNodeIndex && <span className="node-status">Processing</span>}
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
                  <span className="node-time">
                     {(timeMs / 1000).toFixed(2)}s
                  </span>
                </div>
              </div>
            ))}
            <div className="node-item complete sync-node">
              <div className="node-icon">⚡</div>
              <div className="node-details">
                <span className="node-label">
                  [finalizing_audio] <br/><small className="non-graph-text">(Not part of LangGraph)</small>
                </span>
                <span className="node-time">
                   Async
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  };

  const handleAudioError = () => {
    console.warn("ElevenLabs audio stream failed. Quota Exceeded. Falling back to native browser TTS.");
    setAudioFallback(true);
    if ('speechSynthesis' in window && result) {
      // Strip markdown asterisks and hash symbols so they aren't spoken out loud
      const plainText = result.replace(/[#*`_\[\]]/g, '');
      const utterance = new SpeechSynthesisUtterance(plainText);
      window.speechSynthesis.speak(utterance);
    }
  };

  const EvalDiagnosticsPanel = () => {
    if (!cacheId) return null;

    if (evalStatus === "pending" || evalStatus === "running") {
      return (
        <div className="diagnostic-card fade-in">
          <div className="eval-header">
            <h4 className="diag-title">DeepEval Metrics</h4>
            <div className="eval-spinner-container">
              <span className="eval-spinner"></span>
              <span className="eval-status-text">Evaluating...</span>
            </div>
          </div>
        </div>
      );
    }

    if (evalStatus === "failed" || !evalMetrics) {
      return (
        <div className="diagnostic-card fade-in">
          <h4 className="diag-title">DeepEval Metrics</h4>
          <p className="eval-error-text">Evaluation failed or timed out.</p>
        </div>
      );
    }

    const { faithfulness, answer_relevance, hallucination } = evalMetrics;
    
    const MetricCard = ({ title, metric }) => {
      const isErrorMetric = title === "Hallucination";
      const scoreNum = (metric && metric.score !== undefined) ? metric.score : 0;
      const isGood = isErrorMetric ? scoreNum <= 0.3 : scoreNum >= 0.7;

      return (
        <div className="metric-card">
          <div className="metric-title">{title}</div>
          <div className={`metric-score ${isGood ? 'good' : 'bad'}`}>
            {(scoreNum * 100).toFixed(0)}%
          </div>
          {(metric && metric.reasoning) && (
            <div className="metric-reasoning">
              {metric.reasoning}
            </div>
          )}
        </div>
      );
    };

    return (
      <div className="diagnostic-card fade-in">
        <div className="eval-header">
          <h4 className="diag-title">DeepEval Metrics</h4>
          <span className="eval-badge">Quant Unit Tests</span>
        </div>
        <p className="eval-desc">
          Matched against Context Cache <code>{cacheId}</code>
        </p>
        <div className="eval-metrics-grid">
           <MetricCard title="Faithfulness" metric={faithfulness} />
           <MetricCard title="Relevance" metric={answer_relevance} />
           <MetricCard title="Hallucination" metric={hallucination} />
        </div>
      </div>
    );
  };

  return (
    <div className="app-container">
      <div className="background-effect"></div>
      <header className="navbar">
        <h1 className="brand">Project Auricle</h1>
        <p className="brand-subtitle">Contextual Briefing Agent</p>
      </header>

      <div className="layout-wrapper">
        <main className="main-content">
          <div className="control-panel glass-panel">
            <h2>Generate Daily Briefing</h2>
            <p className="panel-desc">This will orchestrate the LangGraph supervisor to fetch recent context and generate a safe, auditory brief.</p>
            
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

          {result && (
            <div className="result-panel glass-panel fade-in">
              <div className="result-header">
                <h3>Briefing Results</h3>
                <div className={`safety-badge ${safetyPassed === false ? 'failed' : ''}`}>
                  {safetyPassed === false ? `⚠ Safety Blocked (${criticScore !== null ? criticScore : 0}%)` : `🛡️ Safety Validated (${criticScore !== null ? criticScore : 100}%)`}
                </div>
              </div>
              
              {audioUrl && !audioFallback && (
                <div className="audio-player">
                  <h4>Audio Synthesis</h4>
                  <audio controls src={audioUrl} onError={handleAudioError} autoPlay />
                </div>
              )}

              {audioFallback && (
                <div className="audio-player fallback">
                  <h4>Audio Synthesis <span className="warning-pill" style={{backgroundColor: '#ff9800', padding: '2px 8px', borderRadius: '12px', fontSize: '12px', marginLeft: '10px', color: '#fff'}}>Native TTS Fallback</span></h4>
                  <p style={{fontSize: '13px', color: '#666'}}>ElevenLabs API Quota Exceeded. Streaming via your browser's native accessibility speaker.</p>
                </div>
              )}
              
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

        <aside className="right-sidebar">
          <div className="diagnostics-panel">
            <div className="diagnostics-header">
              <h3>System Diagnostics</h3>
            </div>
            
            {PipelineProgress()}

            {error && (
              <div className="error-panel diagnostic-card fade-in">
                <h4>Diagnostic Error</h4>
                <p>{error}</p>
              </div>
            )}
          </div>

          {cacheId && (
            <div className="eval-sidebar-panel fade-in">
              {EvalDiagnosticsPanel()}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
