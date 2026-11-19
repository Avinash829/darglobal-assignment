import { useCallback, useEffect, useRef, useState } from "react";
import ChatInput from "./components/ChatInput";
import HistoryPanel from "./components/HistoryPanel";
import MessageBubble from "./components/MessageBubble";
import WelcomeMessage from "./components/WelcomeMessage";
import { BuildingIcon, HistoryIcon, PlusIcon } from "./components/Icons";
import { useChat } from "./hooks/useChat";
import "./App.css";

export default function App() {
  const {
    messages, isLoading, conversations, activeConversationId,
    sendQuestion, stopGenerating, retryLastQuestion,
    startNewChat, openConversation, deleteConversation,
  } = useChat();
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const closeHistory = useCallback(() => setIsHistoryOpen(false), []);
  const bottomRef = useRef(null);
  const hasMessages = messages.length > 0;

  // Keep the newest message in view while the answer streams in.
  useEffect(() => {
    if (hasMessages) bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, hasMessages]);

  return (
    <div className="app">
      <header className="app__header">
        <div className="container header__inner">
          <div className="brand">
            <button className="header-button header-button--icon" onClick={() => setIsHistoryOpen(true)}
                    aria-label="Open chat history" title="Chat history">
              <HistoryIcon size={18} />
            </button>
            <span className="brand__mark" aria-hidden="true"><BuildingIcon size={18} /></span>
            <div>
              <h1>Property Assistant</h1>
              <p>DarGlobal developments · Wasalt listings</p>
            </div>
          </div>

          {hasMessages ? (
            <button className="header-button" onClick={startNewChat}>
              <PlusIcon size={16} /> <span>New chat</span>
            </button>
          ) : (
            <span className="status"><span className="status__dot" /> Online</span>
          )}
        </div>
      </header>

      <HistoryPanel
        isOpen={isHistoryOpen}
        onClose={closeHistory}
        conversations={conversations}
        activeConversationId={activeConversationId}
        onOpen={openConversation}
        onDelete={deleteConversation}
        onNewChat={startNewChat}
      />

      <main className="app__messages">
        <div className="container messages__inner" aria-live="polite">
          {!hasMessages && <WelcomeMessage onSelect={sendQuestion} isDisabled={isLoading} />}
          {messages.map((message, index) => (
            <MessageBubble
              key={index}
              message={message}
              isLast={index === messages.length - 1}
              isStreaming={isLoading && index === messages.length - 1}
              onRetry={retryLastQuestion}
            />
          ))}
          <div ref={bottomRef} />
        </div>
      </main>

      <footer className="app__footer">
        <div className="container">
          <ChatInput onSend={sendQuestion} onStop={stopGenerating} isLoading={isLoading} />
          <small>
            Answers are generated from public data and may be incomplete. Please verify on the official websites.
          </small>
        </div>
      </footer>
    </div>
  );
}
