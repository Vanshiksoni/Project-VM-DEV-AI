import { useState } from "react";
import "./App.css";

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
      const response = await fetch(
        `http://127.0.0.1:8000/ask?question=${encodeURIComponent(
          userQuestion
        )}`
      );

      if (!response.ok) {
        throw new Error("Backend request failed");
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
          content:
            "Sorry, I could not connect to the DevAssist AI backend.",
          sources: [],
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const useExample = (text) => {
    setQuestion(text);
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
                Ask technical questions and get assistance from your
                documentation-powered AI assistant.
              </p>

              <div className="examples">
                <button onClick={() => useExample("What is Docker?")}>
                  What is Docker?
                </button>

                <button
                  onClick={() =>
                    useExample("What is Docker Compose?")
                  }
                >
                  What is Docker Compose?
                </button>

                <button
                  onClick={() => useExample("What is a Docker image?")}
                >
                  What is a Docker image?
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
                          Sources
                        </div>

                        {message.sources.map((source, sourceIndex) => (
                          <div
                            className="source"
                            key={sourceIndex}
                          >
                            <strong>{source.filename}</strong>

                            <span>
                              Chunk {source.chunk_id}
                            </span>

                            <span>
                              Similarity: {source.similarity}
                            </span>
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
                    Thinking...
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

          <div className="sidebar-item active">
            <span>💬</span>
            New Chat
          </div>

          <h3 className="section-title">Features</h3>

          <div className="feature">
            <span>📚</span>
            <div>
              <strong>Documentation</strong>
              <p>Search indexed documentation</p>
            </div>
          </div>

          <div className="feature">
            <span>🔎</span>
            <div>
              <strong>Sources</strong>
              <p>See where answers come from</p>
            </div>
          </div>

          <div className="feature">
            <span>🧠</span>
            <div>
              <strong>RAG</strong>
              <p>Context-aware responses</p>
            </div>
          </div>
        </aside>
      </main>
    </div>
  );
}

export default App;
