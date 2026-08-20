"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Copy,
  Globe,
  Library,
  Paperclip,
  RotateCcw,
  Send,
  Square,
  User,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { MiniRoomList } from "@/components/chat/mini-room-list";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import {
  formatChatTimestamp,
  streamSsePost,
  type ChatCitation,
  type ChatKind,
  type ChatMessageItem,
  type ChatPrompt,
  type ChatRoomCard,
  type SearchScope,
} from "@/lib/chat-sse";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const TITLE_KB = "ถาม-ตอบคลังความรู้";
const TITLE_DRAFT = "แชทร่าง TOR";

function sseFieldText(value: unknown, fallback = ""): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return fallback;
}

function withPatchedLastAssistant(
  prev: ChatMessageItem[],
  patch: Partial<Pick<ChatMessageItem, "content" | "citations">>
): ChatMessageItem[] {
  const last = prev.at(-1);
  if (last?.role !== "assistant") {
    return prev;
  }
  return [...prev.slice(0, -1), { ...last, ...patch }];
}

export function ChatShell({
  kind,
  projectId,
  streamPath,
  extraToolbar,
  onReady,
}: Readonly<{
  kind: ChatKind;
  projectId?: string;
  streamPath?: (roomId: string) => string;
  extraToolbar?: React.ReactNode;
  onReady?: () => void;
}>) {
  const token = useAuthStore((state) => state.token);
  const [rooms, setRooms] = useState<ChatRoomCard[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [prompts, setPrompts] = useState<ChatPrompt[]>([]);
  const [draft, setDraft] = useState("");
  const [search, setSearch] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [scope, setScope] = useState<SearchScope>("both");
  const [busy, setBusy] = useState(false);
  const [queueStatus, setQueueStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  const pathFor = useMemo(
    () =>
      streamPath ||
      ((roomId: string) => `${API_BASE}/chat/rooms/${roomId}/messages`),
    [streamPath]
  );

  const loadRooms = useCallback(async () => {
    const response = await apiClient.get("/chat/rooms", {
      params: { kind, ...(projectId ? { project_id: projectId } : {}) },
    });
    const payload = unwrapData<{ rooms?: ChatRoomCard[] }>(response);
    const next = payload.rooms || [];
    setRooms(next);
    return next;
  }, [kind, projectId]);

  const loadMessages = useCallback(async (roomId: string) => {
    const response = await apiClient.get(`/chat/rooms/${roomId}/messages`);
    const payload = unwrapData<{ messages?: ChatMessageItem[] }>(response);
    setMessages(payload.messages || []);
  }, []);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get("/chat/prompts", { params: { kind } })
      .then((response) => {
        if (cancelled) return;
        const payload = unwrapData<{ prompts?: ChatPrompt[] }>(response);
        setPrompts(payload.prompts || []);
      })
      .catch(() => {
        /* prompt chips are optional */
      });

    async function bootstrap() {
      const list = await loadRooms();
      if (cancelled) return;
      const existing =
        (projectId ? list.find((room) => room.project_id === projectId) : undefined) ||
        list[0];
      if (existing) {
        setActiveId(existing.id);
        await loadMessages(existing.id);
        return;
      }
      if (kind === "draft_intake" && projectId) {
        const created = await apiClient.post("/chat/rooms", {
          kind,
          project_id: projectId,
          title: TITLE_DRAFT,
        });
        const room = unwrapData<ChatRoomCard>(created);
        if (cancelled) return;
        await loadRooms();
        setActiveId(room.id);
        await loadMessages(room.id);
        return;
      }
      if (kind !== "kb") return;
      const created = await apiClient.post("/chat/rooms", {
        kind,
        title: TITLE_KB,
      });
      const room = unwrapData<ChatRoomCard>(created);
      if (cancelled) return;
      await loadRooms();
      setActiveId(room.id);
    }

    bootstrap().catch(() => {
      if (!cancelled) setError("โหลดห้องแชทไม่สำเร็จ");
    });
    return () => {
      cancelled = true;
    };
  }, [kind, projectId, loadRooms, loadMessages]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleNew() {
    const response = await apiClient.post("/chat/rooms", {
      kind,
      project_id: projectId,
      title: kind === "kb" ? TITLE_KB : TITLE_DRAFT,
    });
    const room = unwrapData<ChatRoomCard>(response);
    await loadRooms();
    setActiveId(room.id);
    setMessages([]);
    return room.id;
  }

  async function handleRename(id: string) {
    const title = window.prompt("ชื่อห้อง");
    if (!title) return;
    await apiClient.patch(`/chat/rooms/${id}`, { title });
    await loadRooms();
  }

  async function handleDelete(id: string) {
    await apiClient.delete(`/chat/rooms/${id}`);
    const next = await loadRooms();
    if (activeId === id) {
      setActiveId(next[0]?.id || null);
      setMessages([]);
      if (next[0]) await loadMessages(next[0].id);
    }
  }

  async function send(text: string) {
    const content = text.trim();
    if (!content || busy) return;
    let roomId = activeId;
    if (!roomId) {
      roomId = await handleNew();
    }
    if (!roomId) return;
    setDraft("");
    setBusy(true);
    setError(null);
    const sentAt = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      {
        id: `u-${Date.now()}`,
        role: "user",
        content,
        citations: [],
        created_at: sentAt,
      },
      {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: "",
        citations: [],
        created_at: sentAt,
      },
    ]);
    const controller = new AbortController();
    abortRef.current = controller;
    const requestId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `req-${Date.now()}`;
    setQueueStatus("รอคิว AI...");
    try {
      await streamSsePost(
        pathFor(roomId),
        { content, search_scope: scope },
        token,
        (event, data) => {
          if (event === "queued") {
            const position = Number(data.position || 0);
            setQueueStatus(
              position > 0 ? `รอคิว (#${position})...` : "รอคิว AI..."
            );
          }
          if (event === "started") {
            setQueueStatus(null);
          }
          if (event === "token") {
            setQueueStatus(null);
            const piece = sseFieldText(data.text);
            setMessages((prev) => {
              const last = prev.at(-1);
              if (last?.role !== "assistant") {
                return prev;
              }
              return withPatchedLastAssistant(prev, {
                content: last.content + piece,
              });
            });
          }
          if (event === "done") {
            setQueueStatus(null);
            const citations = (data.citations as ChatCitation[]) || [];
            setMessages((prev) =>
              withPatchedLastAssistant(prev, {
                content: sseFieldText(data.content) || prev.at(-1)?.content || "",
                citations,
              })
            );
            onReady?.();
          }
          if (event === "error") {
            setQueueStatus(null);
            setError(sseFieldText(data.message) || "แชทล้มเหลว");
          }
        },
        controller.signal,
        { "X-AI-Request-Id": requestId }
      );
      await loadRooms();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "ส่งข้อความไม่สำเร็จ");
    } finally {
      setBusy(false);
      setQueueStatus(null);
      abortRef.current = null;
    }
  }

  async function attach(files: FileList | null) {
    if (!files || !activeId) return;
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        const body = new FormData();
        body.append("file", file);
        await apiClient.post(`/chat/rooms/${activeId}/attachments`, body);
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "assistant",
          content: `แนบไฟล์แล้ว ${Array.from(files).map((item) => item.name).join(", ")}`,
          citations: [],
        },
      ]);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "อัปโหลดไฟล์ไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  const lastAssistant = messages.findLast((item) => item.role === "assistant");

  return (
    <div className="flex min-h-[70vh] overflow-hidden rounded-xl border bg-white" data-testid="chat-shell">
      <MiniRoomList
        rooms={rooms}
        activeId={activeId}
        search={search}
        collapsed={collapsed}
        onSearch={setSearch}
        onSelect={(id) => {
          setActiveId(id);
          loadMessages(id).catch((err: unknown) =>
            setError(apiErrorMessage(err, "โหลดข้อความไม่สำเร็จ"))
          );
        }}
        onNew={handleNew}
        onRename={handleRename}
        onDelete={handleDelete}
        onToggleCollapse={() => setCollapsed((value) => !value)}
      />
      <section className="flex min-w-0 flex-1 flex-col">
        <div className="flex flex-wrap items-center gap-1 border-b px-3 py-2">
          <label className="cursor-pointer rounded-md p-1.5 hover:bg-muted" title="แนบไฟล์">
            <Paperclip className="h-4 w-4" />
            <input
              type="file"
              className="sr-only"
              multiple
              data-testid="chat-attach"
              onChange={(event) => attach(event.target.files)}
            />
          </label>
          <ScopeButton current={scope} value="global" onClick={setScope} icon={Globe} label="คลังกลาง" />
          <ScopeButton current={scope} value="mine" onClick={setScope} icon={User} label="ของฉัน" />
          <ScopeButton current={scope} value="both" onClick={setScope} icon={Library} label="ทั้งคู่" />
          <button
            type="button"
            title="คัดลอก"
            className="rounded-md p-1.5 hover:bg-muted"
            onClick={() => {
              if (lastAssistant) navigator.clipboard.writeText(lastAssistant.content);
            }}
          >
            <Copy className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="หยุด"
            className="rounded-md p-1.5 hover:bg-muted"
            onClick={() => abortRef.current?.abort()}
          >
            <Square className="h-4 w-4" />
          </button>
          <button
            type="button"
            title="ส่งใหม่"
            className="rounded-md p-1.5 hover:bg-muted"
            onClick={() => {
              const lastUser = messages.findLast((item) => item.role === "user");
              if (lastUser) send(lastUser.content);
            }}
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          {extraToolbar}
        </div>
        {error ? (
          <p className="px-4 py-2 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex-1 space-y-3 overflow-y-auto p-4" data-testid="chat-messages">
          {messages.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              {kind === "kb"
                ? "พิมพ์คำถามจากคลังกฎหมาย หรือเลือกชิปพรอมต์ด้านล่าง — คำตอบมาจากโมเดลในเครื่องพร้อมอ้างอิง"
                : "วางข้อความหรืออัปโหลดเอกสารด้านบน แล้วถามบอทส่วนที่ยังขาด"}
            </p>
          ) : null}
          {messages.map((item) => (
            <article
              key={item.id}
              className={cn(
                "max-w-[85%] rounded-xl px-3 py-2 text-sm",
                item.role === "user"
                  ? "ml-auto bg-navy text-white"
                  : "bg-muted text-foreground"
              )}
            >
              <p className="whitespace-pre-wrap">{item.content}</p>
              {!item.content && item.role === "assistant" && busy ? (
                <span className="inline-flex gap-1 items-center text-sm" aria-label="กำลังพิมพ์">
                  {queueStatus ? (
                    <span>{queueStatus}</span>
                  ) : (
                    <>
                      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:0ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:150ms]" />
                      <span className="h-2 w-2 animate-bounce rounded-full bg-gray-400 [animation-delay:300ms]" />
                    </>
                  )}
                </span>
              ) : null}
              {item.created_at ? (
                <time
                  className="mt-1 block text-[10px] opacity-70"
                  dateTime={item.created_at}
                >
                  {formatChatTimestamp(item.created_at)}
                </time>
              ) : null}
              {item.citations?.length ? (
                <div className="mt-2 flex flex-wrap gap-1">
                  {item.citations.map((cite) => (
                    <span
                      key={`${cite.type}-${cite.label}`}
                      className="rounded-full bg-white/80 px-2 py-0.5 text-[11px] text-navy"
                    >
                      {cite.type}: {cite.label}
                    </span>
                  ))}
                </div>
              ) : null}
            </article>
          ))}
          <div ref={endRef} />
        </div>
        <div className="border-t p-3">
          <div className="mb-2 flex flex-wrap gap-1">
            {prompts.map((prompt) => (
              <button
                key={prompt.id}
                type="button"
                className="rounded-full border px-2 py-0.5 text-[11px] hover:bg-muted"
                onClick={() => setDraft(prompt.body)}
              >
                {prompt.title}
              </button>
            ))}
          </div>
          <div className="flex items-end gap-2">
            <textarea
              data-testid="chat-input"
              className="min-h-[48px] flex-1 rounded-md border p-2 text-sm"
              value={draft}
              placeholder={kind === "kb" ? "ถามจากคลังกฎหมาย เช่น งวดจ่ายต้องวางหลักประกันหรือไม่" : "ตอบบอท หรือบอกข้อเท็จจริงโครงการ"}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  send(draft);
                }
              }}
            />
            <Button
              type="button"
              data-testid="chat-send"
              disabled={busy || !draft.trim()}
              onClick={() => send(draft)}
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

function ScopeButton({
  current,
  value,
  onClick,
  icon: Icon,
  label,
}: Readonly<{
  current: SearchScope;
  value: SearchScope;
  onClick: (value: SearchScope) => void;
  icon: React.ElementType;
  label: string;
}>) {
  return (
    <button
      type="button"
      title={label}
      className={cn(
        "rounded-md p-1.5",
        current === value ? "bg-brand-orange text-navy" : "hover:bg-muted"
      )}
      data-testid={`chat-scope-${value}`}
      onClick={() => onClick(value)}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
