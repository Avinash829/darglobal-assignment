/**
 * Saves conversations in the browser's localStorage.
 *
 * Conversation: { id, title, messages, updatedAt }
 *
 * localStorage can be unavailable (private mode, blocked storage), so every
 * read and write is wrapped in try/catch and the app still works without it.
 */
const STORAGE_KEY = "property-assistant:conversations";
const MAX_SAVED_CONVERSATIONS = 30;

export function loadConversations() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return Array.isArray(saved) ? saved : [];
  } catch {
    return [];
  }
}

export function saveConversations(conversations) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, MAX_SAVED_CONVERSATIONS)));
  } catch {
    /* storage full or blocked: chats still work, they just are not saved */
  }
}

export function createConversationId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}
