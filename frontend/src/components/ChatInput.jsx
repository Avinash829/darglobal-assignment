import { useEffect, useRef, useState } from "react";
import { SendIcon, StopIcon } from "./Icons";

const MAX_QUESTION_LENGTH = 1000;
const MAX_INPUT_HEIGHT_PX = 160;

export default function ChatInput({ onSend, onStop, isLoading }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);
  const canSend = text.trim().length > 0 && !isLoading;

  // Grow the text box with its content, up to a maximum height.
  useEffect(() => {
    const textarea = textareaRef.current;
    textarea.style.height = "auto";
    textarea.style.height = `${Math.min(textarea.scrollHeight, MAX_INPUT_HEIGHT_PX)}px`;
  }, [text]);

  const send = () => {
    if (!canSend) return;
    onSend(text);
    setText("");
  };

  // Enter sends, Shift+Enter adds a new line.
  const handleKeyDown = (event) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      send();
    }
  };

  return (
    <form className="chat-input" onSubmit={(event) => { event.preventDefault(); send(); }}>
      <textarea
        ref={textareaRef}
        rows={1}
        value={text}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about projects, locations, listings..."
        maxLength={MAX_QUESTION_LENGTH}
        aria-label="Your question"
        autoFocus
      />
      {isLoading ? (
        <button type="button" onClick={onStop} aria-label="Stop generating" title="Stop">
          <StopIcon size={16} />
        </button>
      ) : (
        <button type="submit" disabled={!canSend} aria-label="Send question" title="Send">
          <SendIcon size={18} />
        </button>
      )}
    </form>
  );
}
