export type ChatKind = "kb" | "draft_intake";
export type SearchScope = "global" | "mine" | "both";

export interface ChatRoomCard {
  id: string;
  kind: ChatKind;
  project_id: string | null;
  title: string;
  updated_at: string | null;
  last_message: string;
  last_role: string | null;
}

export interface ChatCitation {
  type: string;
  label: string;
}

export interface ChatMessageItem {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations: ChatCitation[];
  created_at?: string | null;
}

export interface ChatPrompt {
  id: string;
  title: string;
  body: string;
}

export function formatChatTimestamp(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("th-TH", { dateStyle: "short", timeStyle: "short" });
}

function dispatchSseBlock(
  block: string,
  eventName: string,
  onEvent: (event: string, data: Record<string, unknown>) => void
): string {
  let dataLine = "";
  let nextEvent = eventName;
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      nextEvent = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      dataLine += line.slice(5).trim();
    }
  }
  if (!dataLine) {
    return nextEvent;
  }
  try {
    onEvent(nextEvent, JSON.parse(dataLine) as Record<string, unknown>);
  } catch {
    onEvent(nextEvent, { text: dataLine });
  }
  return "message";
}

export async function streamSsePost(
  url: string,
  body: unknown,
  token: string | null,
  onEvent: (event: string, data: Record<string, unknown>) => void,
  signal?: AbortSignal
): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(url, {
    method: "POST",
    credentials: "include",
    headers,
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok || !response.body) {
    let detail = "สตรีมแชทไม่สำเร็จ";
    try {
      const payload = (await response.json()) as { error?: { message?: string } };
      const message = payload?.error?.message;
      if (typeof message === "string" && message.trim()) {
        detail = message;
      }
    } catch {
      // keep the default Thai error when the body is not JSON
    }
    throw new Error(detail);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";
  let more = true;
  while (more) {
    const { done, value } = await reader.read();
    more = !done;
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      eventName = dispatchSseBlock(block, eventName, onEvent);
    }
  }
}
