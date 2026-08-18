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
    throw new Error("สตรีมแชทไม่สำเร็จ");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const block of parts) {
      let dataLine = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) {
          eventName = line.slice(6).trim();
        } else if (line.startsWith("data:")) {
          dataLine += line.slice(5).trim();
        }
      }
      if (!dataLine) continue;
      try {
        onEvent(eventName, JSON.parse(dataLine) as Record<string, unknown>);
      } catch {
        onEvent(eventName, { text: dataLine });
      }
      eventName = "message";
    }
  }
}
