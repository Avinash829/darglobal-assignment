/**
 * Sends a question to the backend and reads the streamed answer.
 *
 * The backend sends Server-Sent Events, one JSON object per event:
 *   { type: "sources", data: [...] }   links used for the answer
 *   { type: "token",   data: "text" }  the next piece of the answer
 *   { type: "error",   data: "msg" }
 *   { type: "done" }
 *
 * Pass an AbortSignal to stop the stream (the "Stop" button).
 */
export async function streamChat(question, history, { onSources, onToken, onError }, signal) {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, history }),
    signal,
  });

  if (!response.ok) {
    onError("Something went wrong on our side. Please try again.");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop(); // keep any half-received event for the next read

    for (const rawEvent of events) {
      if (!rawEvent.startsWith("data: ")) continue;
      const event = JSON.parse(rawEvent.slice("data: ".length));

      if (event.type === "sources") onSources(event.data);
      if (event.type === "token") onToken(event.data);
      if (event.type === "error") onError(event.data);
    }
  }
}
