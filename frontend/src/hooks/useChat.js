import { useEffect, useRef, useState } from "react";
import { streamChat } from "../api/chatApi";
import { createConversationId, loadConversations, saveConversations } from "../utils/chatStorage";

const TITLE_MAX_LENGTH = 60;

/**
 * Holds the current conversation, the saved history, and talks to the backend.
 * Each message: { role: "user" | "assistant", content, sources?, isError?, question? }
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeConversationId, setActiveConversationId] = useState(null);
  const [conversations, setConversations] = useState(loadConversations);
  const abortControllerRef = useRef(null);

  // Save the current conversation into the history once an answer has finished.
  useEffect(() => {
    if (isLoading || !activeConversationId || messages.length === 0) return;

    setConversations((saved) => {
      const existing = saved.find((conversation) => conversation.id === activeConversationId);
      if (existing?.messages === messages) return saved; // just opened, nothing changed

      const updatedConversation = {
        id: activeConversationId,
        title: messages[0].content.slice(0, TITLE_MAX_LENGTH),
        messages,
        updatedAt: Date.now(),
      };
      const others = saved.filter((conversation) => conversation.id !== activeConversationId);
      return [updatedConversation, ...others]; // newest first
    });
  }, [messages, isLoading, activeConversationId]);

  useEffect(() => saveConversations(conversations), [conversations]);

  // Update the last message (the assistant reply being streamed).
  const updateLastMessage = (changes) =>
    setMessages((current) => {
      const lastMessage = current[current.length - 1];
      const updated = typeof changes === "function" ? changes(lastMessage) : changes;
      return [...current.slice(0, -1), { ...lastMessage, ...updated }];
    });

  const sendQuestion = async (question, previousMessages = messages) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || isLoading) return;

    if (!activeConversationId) setActiveConversationId(createConversationId());

    // History sent to the backend: only successful, finished messages.
    const history = previousMessages
      .filter((message) => !message.isError && message.content)
      .map(({ role, content }) => ({ role, content }));

    setMessages([
      ...previousMessages,
      { role: "user", content: trimmedQuestion },
      { role: "assistant", content: "", sources: [], question: trimmedQuestion },
    ]);
    setIsLoading(true);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await streamChat(trimmedQuestion, history, {
        onSources: (sources) => updateLastMessage({ sources }),
        onToken: (text) => updateLastMessage((last) => ({ content: last.content + text })),
        onError: (errorText) => updateLastMessage({ content: errorText, isError: true }),
      }, controller.signal);
    } catch (error) {
      if (error.name === "AbortError") {
        updateLastMessage((last) => ({ content: last.content || "Stopped.", isStopped: true }));
      } else {
        updateLastMessage({ content: "Could not reach the server. Check your connection and try again.", isError: true });
      }
    } finally {
      setIsLoading(false);
      abortControllerRef.current = null;
    }
  };

  const stopGenerating = () => abortControllerRef.current?.abort();

  // Remove the failed question/answer pair and ask the same question again.
  const retryLastQuestion = () => {
    const lastAnswer = messages[messages.length - 1];
    if (!lastAnswer?.question) return;
    sendQuestion(lastAnswer.question, messages.slice(0, -2));
  };

  // The current chat is already saved in the history; just start an empty one.
  const startNewChat = () => {
    stopGenerating();
    setActiveConversationId(null);
    setMessages([]);
  };

  const openConversation = (conversationId) => {
    const conversation = conversations.find((item) => item.id === conversationId);
    if (!conversation) return;
    stopGenerating();
    setActiveConversationId(conversation.id);
    setMessages(conversation.messages);
  };

  const deleteConversation = (conversationId) => {
    setConversations((saved) => saved.filter((conversation) => conversation.id !== conversationId));
    if (conversationId === activeConversationId) startNewChat();
  };

  return {
    messages, isLoading, conversations, activeConversationId,
    sendQuestion, stopGenerating, retryLastQuestion,
    startNewChat, openConversation, deleteConversation,
  };
}
