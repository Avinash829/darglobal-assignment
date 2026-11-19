import { useEffect } from "react";
import { ChatIcon, CloseIcon, PlusIcon, TrashIcon } from "./Icons";

// "Today, 14:05" / "Yesterday" / "12 Nov"
function formatTime(timestamp) {
  const date = new Date(timestamp);
  const today = new Date();
  const yesterday = new Date();
  yesterday.setDate(today.getDate() - 1);

  if (date.toDateString() === today.toDateString()) {
    return `Today, ${date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
  }
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday";
  return date.toLocaleDateString([], { day: "numeric", month: "short" });
}

export default function HistoryPanel({
  isOpen, onClose, conversations, activeConversationId, onOpen, onDelete, onNewChat,
}) {
  // Close with the Escape key.
  useEffect(() => {
    if (!isOpen) return;
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [isOpen, onClose]);

  return (
    <>
      <div className={`overlay ${isOpen ? "overlay--visible" : ""}`} onClick={onClose} aria-hidden="true" />

      <aside className={`history ${isOpen ? "history--open" : ""}`} aria-label="Chat history"
             aria-hidden={!isOpen} inert={!isOpen ? "" : undefined}>
        <div className="history__header">
          <h2>Chat history</h2>
          <button className="icon-button icon-button--square" onClick={onClose} aria-label="Close history">
            <CloseIcon size={18} />
          </button>
        </div>

        <button className="history__new" onClick={() => { onNewChat(); onClose(); }}>
          <PlusIcon size={16} /> New chat
        </button>

        {conversations.length === 0 ? (
          <p className="history__empty">Your conversations will appear here. They are saved only in this browser.</p>
        ) : (
          <ul className="history__list">
            {conversations.map((conversation) => (
              <li key={conversation.id}
                  className={`history-item ${conversation.id === activeConversationId ? "history-item--active" : ""}`}>
                <button className="history-item__open" onClick={() => { onOpen(conversation.id); onClose(); }}>
                  <ChatIcon size={16} />
                  <span className="history-item__text">
                    <span className="history-item__title">{conversation.title}</span>
                    <span className="history-item__time">{formatTime(conversation.updatedAt)}</span>
                  </span>
                </button>
                <button className="icon-button icon-button--square history-item__delete"
                        onClick={() => onDelete(conversation.id)} aria-label={`Delete "${conversation.title}"`}
                        title="Delete">
                  <TrashIcon size={15} />
                </button>
              </li>
            ))}
          </ul>
        )}

        <p className="history__note">Saved in this browser only.</p>
      </aside>
    </>
  );
}
