import { networkFailureMessage } from "@/lib/api-error";

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
  mcp_degraded?: boolean;
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
    return `เอกสาร «${name}» ถูกเพิ่มเข้าคลังของฉันแล้ว — ใช้ค้นหาได้ทันที (${chunks} ส่วนข้อความ)`;
  }
  if (payload.document_id) {
    return `เอกสาร «${name}» ถูกเพิ่มเข้าคลังของฉันแล้ว — กำลังจัดทำดัชนีค้นหา`;
  }
  return `กำลังประมวลผล «${name}» เข้าคลัง...`;
}

export function adoptServerChatMessages(
  prev: ChatMessageItem[],
  rows: ChatMessageItem[]
): { next: ChatMessageItem[]; adopted: boolean } {
  if (rows.length < prev.length) {
    return { next: prev, adopted: false };
  }
  const serverLast = rows.at(-1);
  const serverText = String(serverLast?.content || "").trim();
  if (serverLast?.role !== "assistant" || !serverText) {
    return { next: prev, adopted: false };
  }
  const localLast = prev.at(-1);
  if (localLast?.role === "assistant") {
    if (serverText.length < String(localLast.content || "").trim().length) {
      return { next: prev, adopted: false };
    }
    return {
      next: [...prev.slice(0, -1), { ...localLast, ...serverLast }],
      adopted: true,
    };
  }
  return { next: rows, adopted: true };
}

export function formatChatTimestamp(iso?: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("th-TH", { dateStyle: "short", timeStyle: "short" });
}

const PAINT_SSE_EVENTS = new Set([
  "token",
  "section_done",
  "subsection_done",
  "all_done",
  "done",
  "error",
]);

export const TERMINAL_SSE_EVENTS = new Set(["done", "all_done", "error"]);

function yieldForPaint(): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, 0);
  });
}

function dispatchSseBlock(
  block: string,
  eventName: string,
  onEvent: (event: string, data: Record<string, unknown>) => void
): { nextEvent: string; dispatched: string | null } {
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
    return { nextEvent, dispatched: null };
  }
  try {
    onEvent(nextEvent, JSON.parse(dataLine) as Record<string, unknown>);
  } catch {
    onEvent(nextEvent, { text: dataLine });
  }
  return { nextEvent: "message", dispatched: nextEvent };
}

async function dispatchSseBlockAndPaint(
  block: string,
  eventName: string,
  onEvent: (event: string, data: Record<string, unknown>) => void
): Promise<{ nextEvent: string; terminal: boolean }> {
  const result = dispatchSseBlock(block, eventName, onEvent);
  if (result.dispatched && PAINT_SSE_EVENTS.has(result.dispatched)) {
    await yieldForPaint();
  }
  return {
    nextEvent: result.nextEvent,
    terminal: Boolean(result.dispatched && TERMINAL_SSE_EVENTS.has(result.dispatched)),
  };
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
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      credentials: "include",
      headers,
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    throw new Error(networkFailureMessage(err) || "สตรีมแชทไม่สำเร็จ");
  }
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
  try {
    while (more) {
      const { done, value } = await reader.read();
      more = !done;
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split(/\r?\n\r?\n/);
      buffer = parts.pop() || "";
      for (const block of parts) {
        const dispatched = await dispatchSseBlockAndPaint(block, eventName, onEvent);
        eventName = dispatched.nextEvent;
        if (dispatched.terminal) {
          return;
        }
      }
    }
    if (buffer.trim()) {
      await dispatchSseBlockAndPaint(buffer, eventName, onEvent);
    }
  } finally {
    try {
      await reader.cancel();
    } catch {
      /* already closed */
    }
  }
}
