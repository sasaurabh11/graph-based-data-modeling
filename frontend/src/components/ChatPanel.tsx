import { useEffect, useRef, useState } from "react";
import type { ChatPayload } from "../types";

type ChatMessage =
  | { kind: "user"; text: string }
  | { kind: "assistant"; payload: ChatPayload }
  | { kind: "error"; text: string };

type ChatPanelProps = {
  examples: string[];
  onAsk: (question: string) => Promise<ChatPayload>;
};

function normalize(value: string): string[] {
  return value
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

function filterExamples(examples: string[], query: string): string[] {
  const tokens = normalize(query);
  if (tokens.length === 0) return [];
  return examples.filter((example) => {
    const haystack = example.toLowerCase();
    return tokens.every((token) => haystack.includes(token));
  }).slice(0, 5);
}

export function ChatPanel({ examples, onAsk }: ChatPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [inputFocused, setInputFocused] = useState(false);
  const logRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!logRef.current) return;
    logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, loading]);

  async function submit(nextQuestion: string) {
    const trimmed = nextQuestion.trim();
    if (!trimmed || loading) return;

    setMessages((prev) => [...prev, { kind: "user", text: trimmed }]);
    setQuestion("");
    setLoading(true);
    try {
      const payload = await onAsk(trimmed);
      setMessages((prev) => [...prev, { kind: "assistant", payload }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          kind: "error",
          text: error instanceof Error ? error.message : "Request failed",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  const trimmed = question.trim();
  const matchingExamples = trimmed.length === 0
    ? examples.slice(0, 6)
    : filterExamples(examples, question);

  const showSuggestions = matchingExamples.length > 0 && (
    trimmed.length === 0 ? messages.length === 0 : inputFocused
  );

  return (
    <section className="panel chat-panel">
      <div className="panel-heading">
        <h2>Chat</h2>
        <p>Ask dataset questions in plain English. The answer stays grounded in the loaded records.</p>
      </div>

      <div className="chat-log" ref={logRef}>
        {messages.map((message, index) => {
          if (message.kind === "user") {
            return (
              <article key={index} className="message user">
                <span className="message-role">You</span>
                {message.text}
              </article>
            );
          }
          if (message.kind === "error") {
            return (
              <article key={index} className="message error">
                {message.text}
              </article>
            );
          }
          return (
            <article key={index} className="message assistant">
              <span className="message-role">Answer</span>
              <strong>{message.payload.answer}</strong>
              {message.payload.rationale ? <p className="message-rationale">{message.payload.rationale}</p> : null}
              <details className="message-details">
                <summary>SQL &amp; evidence</summary>
                <pre className="message-code">{message.payload.sql}</pre>
                {message.payload.evidence.length > 0 ? (
                  <pre className="message-evidence">{JSON.stringify(message.payload.evidence.slice(0, 5), null, 2)}</pre>
                ) : null}
              </details>
            </article>
          );
        })}
        {loading && (
          <article className="message assistant loading-message">
            <span className="message-role">Answer</span>
            <span className="thinking-dots"><span>.</span><span>.</span><span>.</span></span>
          </article>
        )}
      </div>

      <form
        className="chat-form"
        onSubmit={(event) => {
          event.preventDefault();
          void submit(question);
        }}
      >
        {showSuggestions ? (
          <div className="chat-suggestions">
            <span className="suggestions-label">{trimmed.length === 0 ? "Try asking:" : "Suggestions:"}</span>
            <div className="suggestions-chips">
              {matchingExamples.map((example) => (
                <button
                  key={example}
                  type="button"
                  className="sample-chip"
                  onMouseDown={(event) => {
                    event.preventDefault();
                    void submit(example);
                  }}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        ) : null}
        <div className="chat-input-row">
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            onFocus={() => setInputFocused(true)}
            onBlur={() => {
              window.setTimeout(() => setInputFocused(false), 120);
            }}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                void submit(question);
              }
            }}
            rows={2}
            placeholder="Ask about orders, deliveries, billing, payments… (Enter to send)"
          />
          <button type="submit" disabled={loading} className="send-button">
            {loading ? "…" : "Send"}
          </button>
        </div>
      </form>
    </section>
  );
}
