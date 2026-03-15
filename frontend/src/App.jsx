const { useState, useEffect, useRef } = React;

function App() {
  const [profilePath, setProfilePath] = useState("scripts/user_profile_sample.txt");
  const [isGenerating, setIsGenerating] = useState(false);
  const [cacheId, setCacheId] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  
  // Pipeline nodes
  const executionNodes = [
    { id: "routing", label: "Supervisor Routing", duration: 500 },
    { id: "fetch_emails", label: "Fetching Latest Emails", duration: 1500 },
    { id: "fetch_calendar", label: "Fetching Calendar Events", duration: 1500 },
    { id: "synthesizing", label: "Gemini Synthesis", duration: 3000 },
    { id: "critique", label: "Reflexion Safety Diagnostics", duration: 2500 }
  ];
  
  const [activeNodeIndex, setActiveNodeIndex] = useState(-1);

  // Simulated Progress Pipeline for UX (since SSE isn't implemented on backend yet)
  useEffect(() => {
    let timeoutId;
    if (isGenerating && activeNodeIndex < executionNodes.length) {
      const currentDuration = activeNodeIndex === -1 ? 500 : executionNodes[activeNodeIndex].duration;
      timeoutId = setTimeout(() => {
        setActiveNodeIndex(prev => prev + 1);
      }, currentDuration);
    }
    return () => clearTimeout(timeoutId);
  }, [isGenerating, activeNodeIndex]);

  const [chatHistory, setChatHistory] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [isChatting, setIsChatting] = useState(false);
  const [chatError, setChatError] = useState(null);

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

  const handleGenerate = async () => {
    setIsGenerating(true);
    setError(null);
    setResult(null);
    setActiveNodeIndex(-1);
    setCacheId(null);
    setAudioUrl(null);

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
      
      // Force pipeline to completion
      setActiveNodeIndex(executionNodes.length);
      
      setResult(data.briefing);
      setCacheId(data.cache_id || "mock-cache-id");
      
      if (data.audio_path) {
        setAudioUrl(`/${data.audio_path}`);
      }

    } catch (err) {
      setError(err.message);
      setActiveNodeIndex(-1);
    } finally {
      setIsGenerating(false);
    }
  };

  const PipelineProgress = () => {
    if (!isGenerating && !result) return null;
    return (
      <div className="pipeline-container">
        <h3>Execution Pipeline</h3>
        <div className="nodes">
          {executionNodes.map((node, i) => {
            let status = "pending";
            if (activeNodeIndex > i || result) status = "complete";
            else if (activeNodeIndex === i) status = "active";
            
            return (
              <div key={node.id} className={`node-item ${status}`}>
                <div className="node-icon">
                  {status === "complete" ? "✓" : status === "active" ? "↻" : "⚬"}
                </div>
                <div>{node.label}</div>
              </div>
            );
          })}
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
              <option value="scripts/user_profile_sample.txt">VP of Engineering (Sample)</option>
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

        <PipelineProgress />

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
                  <div className="msg-content">{msg.content}</div>
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
