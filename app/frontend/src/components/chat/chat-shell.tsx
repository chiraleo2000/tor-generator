"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bot,
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
import {
  ChatAnswerBody,
  ChatCitationBar,
  looksLikeNoRetrieve,
} from "@/components/chat/chat-answer";
import { MiniRoomList } from "@/components/chat/mini-room-list";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import {
  formatChatTimestamp,
  attachIngestFeedback,
  streamSsePost,
  adoptServerChatMessages,
  type ChatCitation,
  type ChatKind,
  type ChatMessageItem,
  type ChatPrompt,
  type ChatRoomCard,
  type SearchScope,
} from "@/lib/chat-sse";
import { uniqueById } from "@/lib/kb-categories";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
const TITLE_KB = "ถาม-ตอบคลังความรู้";
const TITLE_DRAFT = "แชทร่าง TOR";
const TITLE_NEW = "ห้องใหม่";

function isPlaceholderRoom(room: ChatRoomCard): boolean {
  const title = (room.title || "").trim();
  return (
    !(room.last_message || "").trim() &&
    (title === TITLE_NEW || title === TITLE_KB || title === TITLE_DRAFT)
  );
}

interface PrivateKbFile {
  id: string;
  name: string;
  chunk_count?: number;
}

function sseFieldText(value: unknown, fallback = ""): string {
  if (typeof value === "string") {
    return value;
  }
  if (typeof value === "number") {
    return String(value);
  }
  return fallback;
}

type ChatStreamActions = {
  setQueueStatus: (value: string | null) => void;
  setMessages: (
    value: ChatMessageItem[] | ((prev: ChatMessageItem[]) => ChatMessageItem[])
  ) => void;
  setBusy: (value: boolean) => void;
  setError: (value: string | null) => void;
  onReady?: () => void;
};

function appendStreamToken(prev: ChatMessageItem[], piece: string): ChatMessageItem[] {
  const last = prev.at(-1);
  if (last?.role !== "assistant") return prev;
  return withPatchedLastAssistant(prev, { content: last.content + piece });
}

function finishStreamMessage(
  prev: ChatMessageItem[],
  data: Record<string, unknown>
): ChatMessageItem[] {
  const citations = (data.citations as ChatCitation[]) || [];
  return withPatchedLastAssistant(prev, {
    content: sseFieldText(data.content) || prev.at(-1)?.content || "",
    citations,
    mcp_degraded: Boolean(data.mcp_degraded),
  });
}

function applyChatStreamEvent(
  event: string,
  data: Record<string, unknown>,
  actions: ChatStreamActions
) {
  if (event === "queued") {
    const position = Number(data.position || 0);
    actions.setQueueStatus(position > 0 ? `รอคิว (#${position})...` : "รอคิว AI...");
    return;
  }
  if (event === "started" || event === "token" || event === "done" || event === "error") {
    actions.setQueueStatus(null);
  }
  if (event === "token") {
    actions.setMessages((prev) => appendStreamToken(prev, sseFieldText(data.text)));
    return;
  }
  if (event === "done") {
    actions.setMessages((prev) => finishStreamMessage(prev, data));
    actions.setBusy(false);
    actions.onReady?.();
    return;
  }
  if (event === "error") {
    actions.setBusy(false);
    actions.setError(sseFieldText(data.message) || "แชทล้มเหลว");
  }
}

function readStoredRoomId(kind: ChatKind, projectId?: string): string | null {
  try {
    return sessionStorage.getItem(`chat-active:${kind}:${projectId || ""}`);
  } catch {
    return null;
  }
}

function pickExistingRoom(
  list: ChatRoomCard[],
  stored: string | null,
  projectId?: string
): ChatRoomCard | undefined {
  if (stored) {
    const storedRoom = list.find((room) => room.id === stored);
    if (storedRoom) return storedRoom;
  }
  if (projectId) {
    const projectRoom = list.find((room) => room.project_id === projectId);
    if (projectRoom) return projectRoom;
  }
  return list[0];
}

async function startChatSession(input: {
  cancelled: () => boolean;
  compact: boolean;
  kind: ChatKind;
  projectId?: string;
  alreadyPicked: () => boolean;
  loadRooms: () => Promise<ChatRoomCard[]>;
  loadMine: () => Promise<void>;
  selectRoom: (id: string, fromUser?: boolean) => Promise<void>;
}): Promise<void> {
  const list = await input.loadRooms();
  if (input.cancelled()) return;
  try {
    if (!input.compact) await input.loadMine();
  } catch {
    /* private catalog is optional in chat */
  }
  if (input.cancelled() || input.alreadyPicked()) return;
  const existing = pickExistingRoom(
    list,
    readStoredRoomId(input.kind, input.projectId),
    input.projectId
  );
  if (existing) {
    await input.selectRoom(existing.id, false);
    return;
  }
  if (input.kind !== "draft_intake" || !input.projectId) return;
  const created = await apiClient.post("/chat/rooms", {
    kind: input.kind,
    project_id: input.projectId,
    title: TITLE_DRAFT,
  });
  const room = unwrapData<ChatRoomCard>(created);
  if (input.cancelled() || input.alreadyPicked()) return;
  await input.loadRooms();
  await input.selectRoom(room.id, false);
}

async function uploadRoomAttachments(roomId: string, files: File[]): Promise<string[]> {
  const notes: string[] = [];
  await files.reduce(async (previous, file) => {
    await previous;
    const body = new FormData();
    body.append("file", file);
    const response = await apiClient.post(`/chat/rooms/${roomId}/attachments`, body);
    const payload = unwrapData<{
      document_id?: string;
      name?: string;
      status?: string;
      processing_status?: string;
      chunk_count?: number;
    }>(response);
    notes.push(attachIngestFeedback(payload, file.name));
  }, Promise.resolve());
  return notes;
}

function withPatchedLastAssistant(
  prev: ChatMessageItem[],
  patch: Partial<Pick<ChatMessageItem, "content" | "citations" | "mcp_degraded">>
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
  compact = false,
}: Readonly<{
  kind: ChatKind;
  projectId?: string;
  streamPath?: (roomId: string) => string;
  extraToolbar?: React.ReactNode;
  onReady?: () => void;
  compact?: boolean;
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
  const [mineFiles, setMineFiles] = useState<PrivateKbFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [queueStatus, setQueueStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attachNote, setAttachNote] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const loadGen = useRef(0);
  const pickedId = useRef<string | null>(null);
  const userPicked = useRef(false);

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

  const loadMessages = useCallback(async (roomId: string, mode: "replace" | "adopt" = "replace") => {
    const gen = ++loadGen.current;
    const response = await apiClient.get(`/chat/rooms/${roomId}/messages`);
    if (gen !== loadGen.current || pickedId.current !== roomId) {
      return false;
    }
    const payload = unwrapData<{ messages?: ChatMessageItem[] }>(response);
    const rows = Array.isArray(payload.messages) ? payload.messages : [];
    if (mode === "adopt") {
      let adopted = false;
      setMessages((prev) => {
        const result = adoptServerChatMessages(prev, rows);
        adopted = result.adopted;
        return result.next;
      });
      return adopted;
    }
    setMessages(rows);
    return rows.some((item) => item.role === "assistant" && String(item.content || "").trim());
  }, []);

  const loadMine = useCallback(async () => {
    const response = await apiClient.get("/knowledge-base/catalog");
    const payload = unwrapData<{ userFiles?: PrivateKbFile[] }>(response);
    setMineFiles(uniqueById(payload.userFiles || []));
  }, []);

  const rememberRoom = useCallback(
    (id: string | null) => {
      pickedId.current = id;
      try {
        const key = `chat-active:${kind}:${projectId || ""}`;
        if (id) sessionStorage.setItem(key, id);
        else sessionStorage.removeItem(key);
      } catch {
        /* ignore private-mode storage */
      }
    },
    [kind, projectId]
  );

  const selectRoom = useCallback(
    async (id: string, fromUser = true) => {
      if (fromUser) {
        userPicked.current = true;
      } else if (userPicked.current) {
        return;
      }
      rememberRoom(id);
      setActiveId(id);
      setError(null);
      setMessages([]);
      try {
        await loadMessages(id);
      } catch (err: unknown) {
        if (pickedId.current === id) {
          setError(apiErrorMessage(err, "โหลดข้อความไม่สำเร็จ"));
        }
      }
    },
    [loadMessages, rememberRoom]
  );

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
      await startChatSession({
        cancelled: () => cancelled,
        compact,
        kind,
        projectId,
        alreadyPicked: () => Boolean(userPicked.current || pickedId.current),
        loadRooms,
        loadMine,
        selectRoom,
      });
    }

    bootstrap().catch(() => {
      if (!cancelled) setError("โหลดห้องแชทไม่สำเร็จ");
    });
    return () => {
      cancelled = true;
    };
  }, [kind, projectId, compact, loadRooms, loadMessages, loadMine, selectRoom]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const mq = window.matchMedia("(max-width: 767px)");
    const apply = () => setCollapsed(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  useEffect(() => {
    if (!busy || !activeId) return undefined;
    const roomId = activeId;
    const timer = window.setInterval(() => {
      void loadMessages(roomId, "adopt").then((adopted) => {
        if (adopted) {
          setBusy(false);
          setQueueStatus(null);
        }
      });
    }, 2000);
    return () => window.clearInterval(timer);
  }, [busy, activeId, loadMessages]);

  async function handleNew(loadHistory = false) {
    const blank = rooms.find((room) => isPlaceholderRoom(room));
    if (blank) {
      if (loadHistory) {
        await selectRoom(blank.id);
        return blank.id;
      }
      userPicked.current = true;
      rememberRoom(blank.id);
      setActiveId(blank.id);
      setMessages([]);
      setError(null);
      return blank.id;
    }
    const response = await apiClient.post("/chat/rooms", {
      kind,
      project_id: projectId,
      title: kind === "kb" ? TITLE_NEW : TITLE_DRAFT,
    });
    const room = unwrapData<ChatRoomCard>(response);
    await loadRooms();
    userPicked.current = true;
    rememberRoom(room.id);
    setActiveId(room.id);
    setMessages([]);
    setError(null);
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
      if (next[0]) {
        await selectRoom(next[0].id);
        return;
      }
      rememberRoom(null);
      setActiveId(null);
      setMessages([]);
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
    loadGen.current += 1;
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
          applyChatStreamEvent(event, data, {
            setQueueStatus,
            setMessages,
            setBusy,
            setError,
            onReady,
          });
        },
        controller.signal,
        { "X-AI-Request-Id": requestId }
      );
      await loadRooms();
      await loadMessages(roomId, "adopt").catch(() => false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "ส่งข้อความไม่สำเร็จ");
    } finally {
      setBusy(false);
      setQueueStatus(null);
      abortRef.current = null;
    }
  }

  async function attach(files: FileList | null) {
    if (!files?.length) {
      return;
    }
    setBusy(true);
    setError(null);
    setAttachNote("กำลังอัปโหลดเข้าคลังของฉัน...");
    try {
      let roomId = activeId;
      if (!roomId) {
        roomId = await handleNew();
      }
      if (!roomId) {
        setAttachNote(null);
        setError("ยังไม่มีห้องแชทสำหรับแนบไฟล์");
        return;
      }
      const notes = await uploadRoomAttachments(roomId, Array.from(files));
      try {
        await loadMine();
      } catch {
        /* catalog refresh is best-effort after attach */
      }
      const summary = notes.join("\n");
      setAttachNote(summary);
      setMessages((prev) => [
        ...prev,
        {
          id: `sys-${Date.now()}`,
          role: "assistant",
          content: summary,
          citations: [],
        },
      ]);
    } catch (err: unknown) {
      setAttachNote(null);
      setError(apiErrorMessage(err, "อัปโหลดไฟล์ไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function removeMineFile(documentId: string, fileName: string) {
    if (!window.confirm(`ลบ «${fileName}» ออกจากคลังของฉัน?`)) return;
    try {
      await apiClient.delete(`/knowledge-base/mine/${documentId}`);
      await loadMine();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ลบเอกสารไม่สำเร็จ"));
    }
  }

  const lastAssistant = messages.findLast((item) => item.role === "assistant");
  const briefing = kind === "kb" && !compact;

  return (
    <div
      className={cn(
        "flex overflow-hidden rounded-xl border bg-white",
        compact ? "min-h-[52vh]" : "relative min-h-[70vh]",
        briefing && "bg-slate-50"
      )}
      data-testid="chat-shell"
    >
      {compact || collapsed ? null : (
        <button
          type="button"
          aria-label="ปิดรายการห้อง"
          className="absolute inset-0 z-10 bg-navy/25 md:hidden"
          onClick={() => setCollapsed(true)}
        />
      )}
      {compact ? null : (
      <MiniRoomList
        rooms={rooms}
        activeId={activeId}
        search={search}
        collapsed={collapsed}
        onSearch={setSearch}
        onSelect={(id) => {
          void selectRoom(id);
          if (
            typeof window !== "undefined" &&
            typeof window.matchMedia === "function" &&
            window.matchMedia("(max-width: 767px)").matches
          ) {
            setCollapsed(true);
          }
        }}
        onNew={() => {
          void handleNew(true);
        }}
        onRename={handleRename}
        onDelete={handleDelete}
        onToggleCollapse={() => setCollapsed((value) => !value)}
      />
      )}
      <section className="flex min-w-0 flex-1 flex-col bg-[hsl(150,20%,97%)]">
        {briefing ? (
          <div className="border-b bg-white px-5 py-4">
            <div className="flex items-start gap-3">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500 text-white">
                <Bot className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-lg font-extrabold text-navy">
                    AI ผู้ช่วยถาม-ตอบคลังความรู้
                  </h2>
                  <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />{" "}
                    ออนไลน์
                  </span>
                </div>
                <p className="mt-0.5 text-[12.5px] text-muted-foreground">
                  ถามได้ด้วยภาษาธรรมชาติ โดยทุกคำตอบอ้างอิงแหล่งข้อมูลจากคลังกฎหมาย
                  ซึ่งสามารถตรวจสอบย้อนกลับได้
                </p>
              </div>
            </div>
          </div>
        ) : null}
        {compact ? null : (
        <div className="flex flex-wrap items-center gap-1 border-b bg-white px-3 py-2">
          <p className="mr-auto truncate text-sm font-semibold text-navy" data-testid="chat-active-title">
            {rooms.find((room) => room.id === activeId)?.title || "แชทใหม่"}
          </p>
          <label className="cursor-pointer rounded-md p-1.5 hover:bg-muted" title="แนบไฟล์">
            <Paperclip className="h-4 w-4" />
            <input
              type="file"
              className="sr-only"
              multiple
              data-testid="chat-attach"
              onChange={(event) => {
                const input = event.currentTarget;
                attach(input.files)
                  .catch(() => undefined)
                  .finally(() => {
                    input.value = "";
                  });
              }}
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
              if (lastAssistant) void navigator.clipboard.writeText(lastAssistant.content);
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
              if (lastUser) void send(lastUser.content);
            }}
          >
            <RotateCcw className="h-4 w-4" />
          </button>
          {extraToolbar}
        </div>
        )}
        {!compact && mineFiles.length ? (
          <div className="flex flex-wrap items-center gap-2 border-b px-3 py-2 text-xs" data-testid="chat-mine-files">
            <Link href="/knowledge-base" className="font-bold text-navy underline">
              คลังของฉัน
            </Link>
            {mineFiles.slice(0, 8).map((file) => (
              <span
                key={file.id}
                className="inline-flex max-w-[14rem] items-center gap-1 truncate rounded-full bg-blue-50 px-2 py-0.5 text-blue-900"
                data-testid={`chat-mine-${file.id}`}
                title={file.name}
              >
                {file.name}
                <button
                  type="button"
                  className="font-bold"
                  data-testid={`chat-delete-mine-${file.id}`}
                  onClick={() => {
                    removeMineFile(file.id, file.name).catch(() => {
                      /* removeMineFile sets error */
                    });
                  }}
                >
                  ×
                </button>
              </span>
            ))}
            {mineFiles.length > 8 ? (
              <span className="text-muted-foreground">+{mineFiles.length - 8} ไฟล์</span>
            ) : null}
          </div>
        ) : null}
        {error ? (
          <p className="px-4 py-2 text-sm text-destructive" role="alert" data-testid="chat-error">
            {error}
          </p>
        ) : null}
        {attachNote ? (
          <output
            className="block px-4 py-2 text-sm text-navy"
            data-testid="chat-attach-feedback"
          >
            {attachNote}
          </output>
        ) : null}
        <ChatTranscript
          kind={kind}
          briefing={briefing}
          prompts={prompts}
          messages={messages}
          busy={busy}
          queueStatus={queueStatus}
          endRef={endRef}
          onPrompt={(body) => {
            void send(body);
          }}
        />
        <ChatComposer
          kind={kind}
          compact={compact}
          briefing={briefing}
          prompts={prompts}
          draft={draft}
          busy={busy}
          onDraft={setDraft}
          onSend={() => {
            void send(draft);
          }}
        />
      </section>
    </div>
  );
}

function ChatTranscript({
  kind,
  briefing,
  prompts,
  messages,
  busy,
  queueStatus,
  endRef,
  onPrompt,
}: Readonly<{
  kind: ChatKind;
  briefing: boolean;
  prompts: ChatPrompt[];
  messages: ChatMessageItem[];
  busy: boolean;
  queueStatus: string | null;
  endRef: { current: HTMLDivElement | null };
  onPrompt: (body: string) => void;
}>) {
  return (
    <div className="min-w-0 flex-1 space-y-4 overflow-x-hidden overflow-y-auto p-5" data-testid="chat-messages">
      {messages.length === 0 ? (
        <div className="space-y-4 py-6" data-testid="chat-empty">
          <p className="text-center text-sm text-muted-foreground">
            {kind === "kb"
              ? "เลือกประวัติทางซ้าย หรือพิมพ์คำถามเพื่อเริ่มแชทใหม่ — ระบบดึงหลายชิ้นจากคลังแล้วตอบพร้อมอ้างอิง"
              : "บอทจะสรุปผลวิเคราะห์ขั้นที่ ๑ ให้ก่อน แล้วคุยถามส่วนที่ยังขาดเป็นภาษาพูด"}
          </p>
          {briefing && prompts.length ? (
            <div className="flex flex-col items-end gap-2">
              {prompts.map((prompt) => (
                <button
                  key={prompt.id}
                  type="button"
                  data-testid="chat-suggested-prompt"
                  className="max-w-[90%] rounded-2xl bg-emerald-500 px-4 py-2 text-left text-sm text-white shadow-sm hover:bg-emerald-600"
                  onClick={() => onPrompt(prompt.body)}
                >
                  {prompt.title}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      {messages.map((item) => (
        <ChatBubble key={item.id} item={item} briefing={briefing} busy={busy} queueStatus={queueStatus} />
      ))}
      <div ref={endRef} />
    </div>
  );
}

function ChatComposer({
  kind,
  compact,
  briefing,
  prompts,
  draft,
  busy,
  onDraft,
  onSend,
}: Readonly<{
  kind: ChatKind;
  compact: boolean;
  briefing: boolean;
  prompts: ChatPrompt[];
  draft: string;
  busy: boolean;
  onDraft: (value: string) => void;
  onSend: () => void;
}>) {
  return (
    <div className="border-t bg-white p-3">
      <div className="mb-2 flex flex-wrap gap-1">
        {compact
          ? null
          : prompts.map((prompt) => (
              <button
                key={prompt.id}
                type="button"
                data-testid="chat-prompt-chip"
                className="rounded-full border px-2 py-0.5 text-[11px] hover:bg-muted"
                onClick={() => onDraft(prompt.body)}
              >
                {prompt.title}
              </button>
            ))}
      </div>
      <div className="flex items-end gap-2">
        <textarea
          data-testid="chat-input"
          className={cn(
            "min-h-[48px] flex-1 border p-2 text-sm",
            briefing ? "rounded-2xl px-4 py-3 shadow-sm" : "rounded-md"
          )}
          value={draft}
          placeholder={
            kind === "kb"
              ? "พิมพ์คำถามเกี่ยวกับกฎหมาย ระเบียบ และแนวปฏิบัติจัดซื้อจัดจ้าง..."
              : "ตอบเป็นภาษาพูดได้ เช่น วงเงินสองล้านห้าแสนบาท จากงบดำเนินงาน"
          }
          onChange={(event) => onDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              onSend();
            }
          }}
        />
        <Button
          type="button"
          data-testid="chat-send"
          disabled={busy || !draft.trim()}
          className={briefing ? "h-11 w-11 rounded-full bg-emerald-500 hover:bg-emerald-600" : undefined}
          onClick={onSend}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function userBubbleClass(briefing: boolean): string {
  return cn(
    "ml-auto max-w-[85%] rounded-2xl px-4 py-2.5 text-sm text-white",
    briefing ? "bg-emerald-500" : "bg-navy"
  );
}

function assistantBubbleClass(briefing: boolean): string {
  if (briefing) {
    return "w-full min-w-0 max-w-none rounded-2xl bg-white px-6 py-5 text-sm shadow-[0_2px_12px_rgba(15,23,42,0.06)]";
  }
  return "max-w-[85%] rounded-xl bg-muted px-3 py-2 text-sm text-foreground";
}

function bubbleCitations(
  item: ChatMessageItem,
  briefing: boolean,
  isUser: boolean
) {
  if (briefing && !isUser) {
    return <ChatCitationBar citations={item.citations || []} />;
  }
  if (item.citations?.length) {
    return <ChatCitationBar citations={item.citations} />;
  }
  return null;
}

function ChatBubble({
  item,
  briefing,
  busy,
  queueStatus,
}: Readonly<{
  item: ChatMessageItem;
  briefing: boolean;
  busy: boolean;
  queueStatus: string | null;
}>) {
  const isUser = item.role === "user";
  const noRetrieve =
    !isUser && looksLikeNoRetrieve(item.content, item.citations);
  return (
    <article
      data-testid={isUser ? "chat-msg-user" : "chat-msg-assistant"}
      className={isUser ? userBubbleClass(briefing) : assistantBubbleClass(briefing)}
    >
      {isUser || !briefing ? (
        <p className="whitespace-pre-wrap">{item.content}</p>
      ) : (
        <ChatAnswerBody text={item.content} />
      )}
      {!item.content && !isUser && busy ? (
        <span className="inline-flex items-center gap-1 text-sm" aria-label="กำลังพิมพ์">
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
      {item.created_at && !briefing ? (
        <time className="mt-1 block text-[10px] opacity-70" dateTime={item.created_at}>
          {formatChatTimestamp(item.created_at)}
        </time>
      ) : null}
      {item.mcp_degraded ? (
        <p className="mt-2 text-[11px] opacity-80" data-testid="mcp-unavailable">
          แหล่ง MCP ไม่พร้อม — แสดงผลจากคลังในเครื่องและ Custom RAG
        </p>
      ) : null}
      {noRetrieve ? (
        <p
          className="mt-3 inline-flex rounded-full bg-amber-50 px-2 py-0.5 text-[11px] font-medium text-amber-800"
          data-testid="chat-no-retrieve"
        >
          ไม่ดึงคลัง
        </p>
      ) : null}
      {bubbleCitations(item, briefing, isUser)}
    </article>
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
