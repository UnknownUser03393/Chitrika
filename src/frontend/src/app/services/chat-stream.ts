/** SSE chat transport and protocol parser. */

import { API_BASE, apiFetch } from "./api-client";
import type { StreamErrorInfo } from "./api";

export function streamMessage(
  conversationId: string,
  content: string,
  onChunk: (text: string) => void,
  onMessageDone: (messageText: string, messageId: string) => void,
  onStreamEnd: () => void,
  onError: (error: StreamErrorInfo) => void,
  onUserMessageSaved?: (messageId: string) => void,
): AbortController {
  const controller = new AbortController();

  apiFetch(`${API_BASE}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        const detail =
          typeof body.detail === "string" ? body.detail : `HTTP ${response.status}`;
        onError({
          code: `http_${response.status}`,
          message: detail,
          details: detail,
        });
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError({
          code: "missing_stream",
          message: "The server did not provide a response stream.",
          details: "Response.body was empty.",
        });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";
      let currentMessageText = "";
      let currentMessageId = "";
      let receivedDone = false;

      const handleBlock = (block: string): boolean => {
        const dataLines = block
          .split(/\r?\n/)
          .filter((line) => line.startsWith("data:"))
          .map((line) => line.slice(5).trimStart());
        if (dataLines.length === 0) return true;

        let event: Record<string, unknown>;
        try {
          event = JSON.parse(dataLines.join("\n"));
        } catch (error) {
          throw new Error(
            `Malformed SSE JSON: ${
              error instanceof Error ? error.message : String(error)
            }`,
          );
        }

        switch (event.type) {
          case "start":
            currentMessageId = String(event.message_id || "");
            currentMessageText = "";
            if (event.user_message_id) {
              onUserMessageSaved?.(String(event.user_message_id));
            }
            break;
          case "content": {
            const chunk = String(event.content || "");
            currentMessageText += chunk;
            onChunk(chunk);
            break;
          }
          case "done":
            receivedDone = true;
            onMessageDone(
              currentMessageText,
              String(event.message_id || currentMessageId),
            );
            break;
          case "error":
            onError({
              code: String(event.code || "generation_error"),
              message: String(event.message || "The response failed."),
              details: String(
                event.details ||
                  event.message ||
                  "No technical details were provided.",
              ),
              message_id: event.message_id
                ? String(event.message_id)
                : currentMessageId || undefined,
            });
            return false;
        }
        return true;
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        let boundary = buffer.indexOf("\n\n");
        while (boundary >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          if (!handleBlock(block)) return;
          boundary = buffer.indexOf("\n\n");
        }
      }

      buffer += decoder.decode();
      if (buffer.trim() && !handleBlock(buffer)) return;
      if (!receivedDone) {
        onError({
          code: "stream_disconnected",
          message: "The stream disconnected while responding.",
          details: `The SSE connection reached EOF before a done event${
            currentMessageId ? ` (message ${currentMessageId})` : ""
          }.`,
          message_id: currentMessageId || undefined,
        });
        return;
      }
      onStreamEnd();
    })
    .catch((error) => {
      if (error instanceof DOMException && error.name === "AbortError") return;
      onError({
        code: "stream_parse_error",
        message: "The response stream could not be processed.",
        details: error instanceof Error ? error.message : String(error),
      });
    });

  return controller;
}
