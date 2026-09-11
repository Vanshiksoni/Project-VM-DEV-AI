import { useState } from "react";
import "./App.css";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

function App() {
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!question.trim() || loading) return;

    const userQuestion = question.trim();

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userQuestion,
      },
    ]);

    setQuestion("");
    setLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: userQuestion }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.answer,
          sources: data.sources || [],
        },
      ]);
    } catch (error) {
      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, could not connect to the DevAssist AI backend server.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectExample = (text) => {
    setQuestion(text);
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>DevAssist AI</h1>
          <p>Technical Documentation Assistant</p>
        </div>

        <div className="status">
          <span className="status-dot"></span>
          System Ready
        </div>
      </header>

      <main className="main">
        <section className="chat-section">
          {messages.length === 0 ? (
            <div className="welcome">
              <div className="logo">DA</div>

              <h2>Welcome to DevAssist AI</h2>

              <p>
                Ask technical documentation questions. Grounded answers are generated using index-backed RAG and local Code Llama inference.
              </p>

              <div className="examples">
                <button onClick={() => handleSelectExample("What is Docker?")}>
                  What is Docker?
                </button>

                <button
                  onClick={() =>
                    handleSelectExample("What is Docker Compose?")
                  }
                >
                  What is Docker Compose?
                </button>

                <button
                  onClick={() => handleSelectExample("What is a Docker image?")}
                >
                  What is a Docker image?
                </button>

                <button
                  onClick={() => handleSelectExample("What is quantum computing?")}
                >
                  What is quantum computing? (Out-of-domain test)
                </button>
              </div>
            </div>

          ) : (
            <div className="messages">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`message ${message.role}`}
                >
                  <div className="message-label">
                    {message.role === "user"
                      ? "You"
                      : "DevAssist AI"}
                  </div>

                  <div className="message-content">
                    {message.content}
                  </div>

                  {message.role === "assistant" &&
                    message.sources?.length > 0 && (
                      <div className="sources">
                        <div className="sources-title">
                          Retrieved Documentation Sources
                        </div>

                        {message.sources.map((source, sourceIndex) => (
                          <div
                            className="source"
                            key={sourceIndex}
                          >
                            <strong>{source.filename}</strong>
                            <span>Section: <em>{source.section || "General"}</em></span>
                            <span>Chunk ID: #{source.chunk_id}</span>
                            <span>Similarity: {source.similarity}</span>
                          </div>
                        ))}
                      </div>
                    )}
                </div>
              ))}

              {loading && (
                <div className="message assistant">
                  <div className="message-label">
                    DevAssist AI
                  </div>

                  <div className="message-content">
                    Retrieving context & generating grounded answer...
                  </div>
                </div>
              )}
            </div>
          )}

          <form className="input-area" onSubmit={handleSubmit}>
            <input
              type="text"
              placeholder="Ask a technical question..."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={loading}
            />

            <button type="submit" disabled={loading}>
              {loading ? "..." : "Send"}
            </button>
          </form>
        </section>

        <aside className="sidebar">
          <h3>Assistant</h3>

          <button className="sidebar-item active" onClick={handleClearChat}>
            <span>💬</span>
            New Chat
          </button>

          <h3 className="section-title">Features</h3>

          <div className="feature">
            <span>📚</span>
            <div>
              <strong>Documentation</strong>
              <p>Indexed Markdown docs</p>
            </div>
          </div>

          <div className="feature">
            <span>🎯</span>
            <div>
              <strong>Grounding</strong>
              <p>Zero-hallucination thresholding</p>
            </div>
          </div>

          <div className="feature">
            <span>🧠</span>
            <div>
              <strong>RAG Architecture</strong>
              <p>Nomic Embed + Code Llama</p>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;

