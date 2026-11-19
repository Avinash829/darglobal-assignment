import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm"; // tables, strikethrough, auto-links
import { CheckIcon, CopyIcon, LinkIcon, RetryIcon, SparkleIcon } from "./Icons";

// Links open in a new tab; tables get a scroll wrapper so they never break the layout.
const markdownComponents = {
  a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
  table: (props) => <div className="table-scroll"><table {...props} /></div>,
};

function CopyButton({ text }) {
  const [isCopied, setIsCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 1500);
    } catch {
      /* clipboard can be blocked by the browser; nothing to do */
    }
  };

  return (
    <button className="icon-button" onClick={copy} aria-label="Copy answer" title="Copy">
      {isCopied ? <CheckIcon size={14} /> : <CopyIcon size={14} />}
      <span>{isCopied ? "Copied" : "Copy"}</span>
    </button>
  );
}

export default function MessageBubble({ message, isStreaming, isLast, onRetry }) {
  const { role, content, sources = [], isError } = message;
  const isAssistant = role === "assistant";
  const isWaiting = isStreaming && content === "";
  const isFinished = isAssistant && !isStreaming && content;

  return (
    <article className={`message message--${role} ${isError ? "message--error" : ""}`}>
      {isAssistant && <span className="avatar" aria-hidden="true"><SparkleIcon size={16} /></span>}

      <div className="message__body">
        <div className="message__bubble">
          {isWaiting ? (
            <span className="typing-dots" role="status" aria-label="Assistant is thinking">
              <span /><span /><span />
            </span>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>{content}</ReactMarkdown>
          )}
        </div>

        {isAssistant && sources.length > 0 && !isWaiting && !isError && (
          <div className="message__sources" aria-label="Sources">
            {sources.map((source) => (
              <a key={source.url} href={source.url} target="_blank" rel="noreferrer"
                 className={`source-chip source-chip--${source.source.toLowerCase()}`}>
                <LinkIcon size={12} />
                <span className="source-chip__site">{source.source}</span>
                <span className="source-chip__title">{source.title}</span>
              </a>
            ))}
          </div>
        )}

        {isFinished && (
          <div className="message__actions">
            {isError && isLast ? (
              <button className="icon-button" onClick={onRetry}>
                <RetryIcon size={14} /> <span>Try again</span>
              </button>
            ) : (
              !isError && <CopyButton text={content} />
            )}
          </div>
        )}
      </div>
    </article>
  );
}
