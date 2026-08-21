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

export interface AttachIngestPayload {
  document_id?: string;
  name?: string;
  status?: string;
  processing_status?: string;
  chunk_count?: number;
}

export function attachIngestFeedback(
  payload: AttachIngestPayload,
  fallbackName: string
): string {
  const name = payload.name || fallbackName;
  const status = payload.status || payload.processing_status || "";
  const chunks = payload.chunk_count ?? 0;
  if (status === "failed") {
    return `ไม่สามารถประมวลผล «${name}» ได้`;
  }
  if (status === "completed" || chunks > 0) {
    return `เอกสาร «${name}» ถูกเพิ่มเข้าคลังของฉันแล้ว — ใช้ RAG ได้ทันที (${chunks} chunks)`;
  }
  return `กำลังประมวลผล «${name}» เข้าคลัง...`;
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
  signal?: AbortSignal,
  extraHeaders?: Record<string, string>
): Promise<void> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "text/event-stream",
  };
  if (extraHeaders) {
    Object.assign(headers, extraHeaders);
  }
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
