"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Pencil, RotateCcw, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { streamSsePost } from "@/lib/chat-sse";
import { useAuthStore } from "@/stores/auth-store";
import { TOR_SECTION_LABELS, formatScopeSubHeading, formatTorSectionHeading, sectionIndexPad } from "@/lib/tor-sections";
import { cn } from "@/lib/utils";

interface SectionStatus {
  section_key: string;
  title: string;
  has_content: boolean;
  ai_drafted?: boolean;
  content_preview: string;
  human_confirmed: boolean;
}

interface SearchHit {
  title: string;
  url: string;
  snippet: string;
}

interface DraftMessage {
  id: string;
  role: "user" | "bot" | "system";
  content: string;
  sectionKey?: string;
  sectionTitle?: string;
  isDraft?: boolean;
  status?: "drafting" | "done" | "error" | "accepted" | "editing";
  searchHits?: SearchHit[];
  searchDisclaimer?: string;
  awaitingConfirm?: boolean;
}

function sectionTitle(key: string): string {
  return TOR_SECTION_LABELS[key as keyof typeof TOR_SECTION_LABELS] || key;
}

function applyReplyStreamEvent(
  event: string,
  data: Record<string, unknown>,
  responseMsgId: string,
  tokens: string,
  sectionKey: string,
  actions: {
    setMessages: MessageSetter;
    onSectionDone?: (key?: string, content?: string) => void;
    setBusy: (value: boolean) => void;
  }
): string {
  if (event === "section_start") {
    const key = data.section_key as string;
    const title = data.title as string;
    actions.setMessages((prev) =>
      prev.map((message) =>
        message.id === responseMsgId
          ? { ...message, sectionKey: key, sectionTitle: title, isDraft: true }
          : message
      )
    );
    return tokens;
  }
  if (event === "token") {
    const piece = typeof data.text === "string" ? data.text : "";
    const captured = tokens + piece;
    actions.setMessages((prev) =>
      prev.map((message) =>
        message.id === responseMsgId ? { ...message, content: captured } : message
      )
    );
    return captured;
  }
  const content = data.content as string;
  actions.setMessages((prev) =>
    prev.map((message) =>
      message.id === responseMsgId
        ? { ...message, content, status: "done", isDraft: true }
        : message
    )
  );
  actions.onSectionDone?.(
    typeof data.section_key === "string" ? data.section_key : sectionKey || undefined,
    content
  );
  actions.setBusy(false);
  return tokens;
}

function productSearchMessage(
  message: DraftMessage,
  responseMsgId: string,
  hits: SearchHit[],
  disclaimer: string | undefined
): DraftMessage {
  if (message.id !== responseMsgId) return message;
  return {
    ...message,
    content: hits.length
      ? "พบแหล่งอ้างอิงผลิตภัณฑ์/ผู้ขาย — ยืนยันก่อนแทรกลง TOR"
      : "ค้นแล้วไม่พบแหล่งอ้างอิง",
    status: "done",
    searchHits: hits,
    searchDisclaimer: disclaimer,
    awaitingConfirm: hits.length > 0,
  };
}

function insertedSearchMessage(
  message: DraftMessage,
  responseMsgId: string,
  content: string,
  sectionKey: string | undefined
): DraftMessage {
  if (message.id !== responseMsgId) return message;
  return {
    ...message,
    content: content || "แทรกแหล่งอ้างอิงแล้ว — ไม่ใช่สเปกที่ผูกยี่ห้อ",
    status: "done",
    awaitingConfirm: false,
    sectionKey: sectionKey || message.sectionKey,
  };
}

function patchDraftMessage(
  messages: DraftMessage[],
  messageId: string,
  patch: Partial<DraftMessage>
): DraftMessage[] {
  return messages.map((msg) => (msg.id === messageId ? { ...msg, ...patch } : msg));
}

function eventSectionKey(data: Record<string, unknown>): string {
  return typeof data.section_key === "string" ? data.section_key : "";
}

function progressTotal(data: Record<string, unknown>, fallback: number): number {
  const eventTotal = Number(data.total);
  return Number.isFinite(eventTotal) && eventTotal > 0 ? eventTotal : fallback;
}

type MessageSetter = (update: (prev: DraftMessage[]) => DraftMessage[]) => void;

function ensureBatchMessage(
  ids: Record<string, string>,
  key: string,
  title: string,
  messageId: string,
  content: string,
  setMessages: MessageSetter
) {
  setMessages((prev) => {
    const existing = prev.find((row) => row.sectionKey === key && row.status === "drafting");
    if (existing) {
      ids[key] = existing.id;
      return prev;
    }
    return [
      ...prev,
      {
        id: messageId,
        role: "bot" as const,
        content,
        sectionKey: key,
        sectionTitle: title,
        isDraft: true,
        status: "drafting" as const,
      },
    ];
  });
}

function appendBatchToken(
  ids: Record<string, string>,
  key: string,
  piece: string,
  setDraftingLabel: (value: string) => void,
  setMessages: MessageSetter
) {
  if (!piece) return;
  let messageId = ids[key];
  if (!messageId) {
    messageId = `draft-${key}-${Date.now()}`;
    ids[key] = messageId;
    const title = sectionTitle(key);
    setDraftingLabel(formatTorSectionHeading(key, title));
    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "bot",
        content: piece,
        sectionKey: key,
        sectionTitle: title,
        isDraft: true,
        status: "drafting",
      },
    ]);
    return;
  }
  setMessages((prev) => {
    const current = prev.find((row) => row.id === messageId);
    return patchDraftMessage(prev, messageId, {
      content: `${current?.content || ""}${piece}`,
    });
  });
}

function labelBatchSubheading(
  data: Record<string, unknown>,
  setDraftingLabel: (value: string) => void
) {
  const subKey = typeof data.sub_key === "string" ? data.sub_key : "";
  const title = typeof data.title === "string" ? data.title : subKey;
  if (subKey) setDraftingLabel(formatScopeSubHeading(subKey, title));
}

function finishBatchSubsection(
  data: Record<string, unknown>,
  onSectionDone: ((key: string, content: string) => void) | undefined,
  refreshStatus: () => void | Promise<unknown>
) {
  const subKey = typeof data.sub_key === "string" ? data.sub_key : "";
  const subContent = typeof data.content === "string" ? data.content : "";
  onSectionDone?.(subKey || "s4", subContent);
  void refreshStatus();
}

function finishBatchAll(
  data: Record<string, unknown>,
  fallbackTotal: number,
  actions: {
    applyProgress: (count: number, total: number) => void;
    setDraftingLabel: (value: string | null) => void;
    setPhase: (value: DraftPhase) => void;
    setBusy: (value: boolean) => void;
    onAllDrafted: () => void;
    refreshStatus: () => void | Promise<unknown>;
  }
) {
  rememberDraftProgress(data, fallbackTotal, actions.applyProgress);
  actions.setDraftingLabel(null);
  actions.setPhase("complete");
  actions.setBusy(false);
  actions.onAllDrafted();
  void actions.refreshStatus();
}

function handleBatchRowEvent(
  event: string,
  data: Record<string, unknown>,
  key: string,
  ids: Record<string, string>,
  actions: {
    setDraftingLabel: (value: string) => void;
    setMessages: MessageSetter;
    applyProgress: (count: number, total: number) => void;
    total: number;
    onSectionDone?: (key: string, content: string) => void;
    noteDrafted: (key: string) => void;
    refreshStatus: () => void | Promise<unknown>;
  }
): boolean {
  if (event === "section_start" && key) {
    const messageId = `draft-${key}-${Date.now()}`;
    ids[key] = messageId;
    const title = typeof data.title === "string" ? data.title : sectionTitle(key);
    actions.setDraftingLabel(formatTorSectionHeading(key, title));
    ensureBatchMessage(ids, key, title, messageId, "", actions.setMessages);
    return true;
  }
  if (event === "token" && key) {
    appendBatchToken(
      ids,
      key,
      typeof data.text === "string" ? data.text : "",
      actions.setDraftingLabel,
      actions.setMessages
    );
    return true;
  }
  if (event !== "section_done" || !key) return false;
  const content = typeof data.content === "string" ? data.content : "";
  rememberDraftProgress(data, actions.total, actions.applyProgress);
  finishBatchSection(ids, key, content, actions.setMessages);
  actions.onSectionDone?.(key, content);
  actions.noteDrafted(key);
  void actions.refreshStatus();
  return true;
}

function failBatchSection(
  ids: Record<string, string>,
  key: string,
  data: Record<string, unknown>,
  setError: (value: string) => void,
  setMessages: MessageSetter
) {
  const msg = typeof data.message === "string" ? data.message : "ร่างไม่สำเร็จ";
  setError(msg);
  if (!key || !ids[key]) return;
  setMessages((prev) =>
    patchDraftMessage(prev, ids[key], {
      content: `ร่างไม่สำเร็จ: ${msg}`,
      status: "error",
    })
  );
}

function finishBatchSection(
  ids: Record<string, string>,
  key: string,
  content: string,
  setMessages: MessageSetter
) {
  const existingId = ids[key];
  if (!existingId) {
    const messageId = `draft-${key}-done`;
    ids[key] = messageId;
    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "bot",
        content,
        sectionKey: key,
        sectionTitle: sectionTitle(key),
        isDraft: true,
        status: "done",
      },
    ]);
    return;
  }
  setMessages((prev) => patchDraftMessage(prev, existingId, { content, status: "done" }));
}

function rememberDraftProgress(
  data: Record<string, unknown>,
  fallbackTotal: number,
  applyProgress: (count: number, total: number) => void
) {
  const count = Number(data.drafted_count);
  if (!Number.isFinite(count) || count <= 0) return;
  applyProgress(count, progressTotal(data, fallbackTotal));
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

type DraftPhase = "idle" | "drafting" | "reviewing" | "complete";

export function resetDraftChatStartsForTests(): void {
  // Draft start state lives on the component instance. Tests call this between cases.
}

function phaseStatusCopy(
  phase: DraftPhase,
  draftingLabel?: string | null
): { text: string; className: string } | null {
  if (phase === "drafting") {
    return {
      text: draftingLabel
        ? `กำลังร่าง ${draftingLabel}...`
        : "กำลังร่าง... กรุณารอ",
      className: "mt-1.5 text-xs text-amber-700",
    };
  }
  if (phase === "reviewing") {
    return {
      text: "ตรวจร่างแต่ละหมวด แล้วยอมรับหรือแก้ไข",
      className: "mt-1.5 text-xs text-navy",
    };
  }
  if (phase === "complete") {
    return {
      text: "ร่างครบทุกหมวดแล้ว — พร้อมไปทบทวน",
      className: "mt-1.5 text-xs font-bold text-green-700",
    };
  }
  return null;
}

function sectionBadgeClass(status?: DraftMessage["status"]): string {
  if (status === "done") {
    return "text-green-800";
  }
  if (status === "error") {
    return "text-red-800";
  }
  if (status === "accepted") {
    return "text-brand-green";
  }
  return "text-amber-800";
}

function asSearchHits(value: unknown): SearchHit[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => {
      if (!item || typeof item !== "object") return null;
      const row = item as Record<string, unknown>;
      return {
        title: typeof row.title === "string" ? row.title : "",
        url: typeof row.url === "string" ? row.url : "",
        snippet: typeof row.snippet === "string" ? row.snippet : "",
      };
    })
    .filter((item): item is SearchHit => Boolean(item && (item.title || item.url || item.snippet)));
}

function DraftChatMessage({
  msg,
  busy,
  onAccept,
  onEdit,
  onRedraft,
  onConfirmSearch,
}: Readonly<{
  msg: DraftMessage;
  busy: boolean;
  onAccept: (key: string) => void;
  onEdit: (key: string) => void;
  onRedraft: (key: string) => void;
  onConfirmSearch?: (hits: SearchHit[]) => void;
}>) {
  if (msg.role === "system") {
    return (
      <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-2 text-sm text-blue-800">
        {msg.content}
      </div>
    );
  }
  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-xl bg-navy px-4 py-2.5 text-sm text-white">
          {msg.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex justify-start">
      <div className="max-w-[90%] rounded-xl border bg-gray-50 px-4 py-3 text-sm">
        {msg.sectionKey ? (
          <div className="mb-2 flex items-center gap-2">
            <span
              className={cn(
                "font-mono text-[11px] font-semibold tabular-nums tracking-wide",
                sectionBadgeClass(msg.status)
              )}
            >
              {sectionIndexPad(msg.sectionKey)}
            </span>
            <span className="text-xs font-medium text-navy">{msg.sectionTitle}</span>
            {msg.status === "drafting" ? (
              <span className="animate-pulse text-xs text-muted-foreground">กำลังร่าง...</span>
            ) : null}
          </div>
        ) : null}
        <div className="whitespace-pre-wrap text-gray-800">
          {msg.content || (
            <span className="animate-pulse text-muted-foreground">กำลังคิด...</span>
          )}
        </div>
        {msg.searchHits?.length ? (
          <div className="mt-3 space-y-2 border-t pt-2" data-testid="draft-search-results">
            <p className="text-xs text-amber-800" data-testid="draft-search-disclaimer">
              {msg.searchDisclaimer ||
                "แหล่งอ้างอิงเท่านั้น ไม่ใช่สเปกที่ผูกยี่ห้อ ต้องยืนยันก่อนแทรกลง TOR"}
            </p>
            <ul className="space-y-2">
              {msg.searchHits.map((hit) => (
                <li key={`${hit.url}-${hit.title}`} className="text-xs">
                  <p className="font-medium text-navy">{hit.title || hit.url}</p>
                  {hit.url ? (
                    <p className="break-all text-muted-foreground">{hit.url}</p>
                  ) : null}
                  {hit.snippet ? <p className="text-gray-700">{hit.snippet}</p> : null}
                </li>
              ))}
            </ul>
            {msg.awaitingConfirm && onConfirmSearch ? (
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                disabled={busy}
                data-testid="draft-search-confirm"
                onClick={() => onConfirmSearch(msg.searchHits || [])}
              >
                ยืนยันแทรกลง TOR
              </Button>
            ) : null}
          </div>
        ) : null}
        {msg.isDraft && msg.status === "done" && msg.sectionKey ? (
          <div className="mt-3 flex gap-2 border-t pt-2">
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={busy}
              data-testid={`draft-accept-${msg.sectionKey}`}
              onClick={() => onAccept(msg.sectionKey!)}
            >
              <Check className="mr-1 h-3 w-3" /> ยอมรับ
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={busy}
              data-testid={`draft-edit-${msg.sectionKey}`}
              onClick={() => onEdit(msg.sectionKey!)}
            >
              <Pencil className="mr-1 h-3 w-3" /> แก้ไข
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              disabled={busy}
              data-testid={`draft-redraft-${msg.sectionKey}`}
              onClick={() => onRedraft(msg.sectionKey!)}
            >
              <RotateCcw className="mr-1 h-3 w-3" /> ร่างใหม่
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export function DraftChat({
  projectId,
  onAllDrafted,
  onSectionDone,
  onDraftingChange,
}: Readonly<{
  projectId: string;
  onAllDrafted: () => void;
  onSectionDone?: (sectionKey?: string, content?: string) => void;
  onDraftingChange?: (busy: boolean) => void;
}>) {
  const token = useAuthStore((state) => state.token);
  const [messages, setMessages] = useState<DraftMessage[]>([]);
  const [sections, setSections] = useState<SectionStatus[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftedCount, setDraftedCount] = useState(0);
  const [totalSections, setTotalSections] = useState(13);
  const totalSectionsRef = useRef(13);
  const [phase, setPhase] = useState<"idle" | "drafting" | "reviewing" | "complete">("idle");
  const [currentEditSection, setCurrentEditSection] = useState<string | null>(null);
  const [draftingLabel, setDraftingLabel] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const started = useRef(false);
  const sectionsRef = useRef<SectionStatus[]>([]);
  const seenDraftedKeysRef = useRef<Set<string> | null>(null);
  const onSectionDoneRef = useRef(onSectionDone);
  onSectionDoneRef.current = onSectionDone;

  const scrollToEnd = useCallback(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === "function") {
      node.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  useEffect(scrollToEnd, [messages, scrollToEnd]);

  useEffect(() => {
    onDraftingChange?.(busy || phase === "drafting");
  }, [busy, phase, onDraftingChange]);

  const applyProgress = useCallback((drafted: number, total: number) => {
    const safeTotal = Math.max(1, total || totalSectionsRef.current || 13);
    totalSectionsRef.current = safeTotal;
    setTotalSections(safeTotal);
    setDraftedCount(Math.min(safeTotal, Math.max(0, drafted)));
  }, []);

  const notifyNewlyDrafted = useCallback((rows: SectionStatus[]) => {
    const ready = rows
      .filter((row) => row.ai_drafted || row.has_content)
      .map((row) => row.section_key);
    if (seenDraftedKeysRef.current === null) {
      seenDraftedKeysRef.current = new Set(ready);
      return;
    }
    for (const key of ready) {
      if (seenDraftedKeysRef.current.has(key)) continue;
      seenDraftedKeysRef.current.add(key);
      // No content payload — parent reloads full section text from API.
      onSectionDoneRef.current?.(key);
    }
  }, []);

  const refreshStatus = useCallback(async () => {
    try {
      const response = await apiClient.get(
        `/projects/${projectId}/draft-chat/status`
      );
      const data = unwrapData<{
        sections: SectionStatus[];
        drafted_count: number;
        total: number;
        all_drafted: boolean;
        job_status?: string;
      }>(response);
      const rows = Array.isArray(data.sections) ? data.sections : [];
      setSections(rows);
      sectionsRef.current = rows;
      notifyNewlyDrafted(rows);
      const total = Number(data.total) || rows.length || 13;
      applyProgress(Number(data.drafted_count) || 0, total);
      const running = data.job_status === "running" || data.job_status === "queued";
      if (running) {
        setPhase((prev) => (prev === "complete" ? prev : "drafting"));
      }
      if (data.all_drafted) {
        setPhase("complete");
        setDraftingLabel(null);
        onAllDrafted();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }, [projectId, onAllDrafted, applyProgress, notifyNewlyDrafted]);

  useEffect(() => {
    if (phase !== "drafting") return;
    const timer = window.setInterval(() => {
      void refreshStatus();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [phase, refreshStatus]);

  // Auto-start drafting on mount unless all 13 sections already exist
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    refreshStatus()
      .then((done) => {
        if (done) return;
        void startDrafting();
      })
      .catch(() => {
        void startDrafting();
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function streamOneSection(sectionKey: string): Promise<boolean> {
    const title = sectionTitle(sectionKey);
    const messageId = `draft-${sectionKey}-${Date.now()}`;
    let tokens = "";
    setMessages((prev) => [
      ...prev,
      {
        id: messageId,
        role: "bot",
        content: "",
        sectionKey,
        sectionTitle: title,
        isDraft: true,
        status: "drafting",
      },
    ]);
    try {
      let failed = false;
      await streamSsePost(
        `${API_BASE}/projects/${projectId}/draft-chat/message`,
        {
          content: `ร่างใหม่ ${formatTorSectionHeading(sectionKey)}`,
          section_key: sectionKey,
        },
        token,
        (event: string, data: Record<string, unknown>) => {
          if (event === "token") {
            const piece = typeof data.text === "string" ? data.text : "";
            tokens += piece;
            const captured = tokens;
            setMessages((prev) => patchDraftMessage(prev, messageId, { content: captured }));
            return;
          }
          if (event === "section_done") {
            const content = typeof data.content === "string" ? data.content : tokens;
            setMessages((prev) =>
              patchDraftMessage(prev, messageId, { content, status: "done" })
            );
            onSectionDone?.(sectionKey, content);
            seenDraftedKeysRef.current ??= new Set();
            seenDraftedKeysRef.current.add(sectionKey);
            void refreshStatus();
            return;
          }
          if (event === "error" || event === "section_error") {
            failed = true;
            const msg = typeof data.message === "string" ? data.message : "ร่างไม่สำเร็จ";
            setMessages((prev) =>
              patchDraftMessage(prev, messageId, {
                content: `ร่างไม่สำเร็จ: ${msg}`,
                status: "error",
              })
            );
          }
        }
      );
      return !failed && tokens.trim().length > 0;
    } catch (err: unknown) {
      setMessages((prev) =>
        prev.map((row) =>
          row.id === messageId
            ? {
                ...row,
                content: `ร่างไม่สำเร็จ: ${apiErrorMessage(err, "หมดเวลาหรือตัดการเชื่อมต่อ")}`,
                status: "error",
              }
            : row
        )
      );
      return false;
    }
  }

  async function streamBatchDraft(): Promise<boolean> {
    const ids: Record<string, string> = {};
    let failed = false;
    await streamSsePost(
      `${API_BASE}/projects/${projectId}/draft-chat/start`,
      {},
      token,
      (event: string, data: Record<string, unknown>) => {
        const key = eventSectionKey(data);
        if (
          handleBatchRowEvent(event, data, key, ids, {
            setDraftingLabel,
            setMessages,
            applyProgress,
            total: totalSectionsRef.current,
            onSectionDone,
            noteDrafted: (draftedKey) => {
              seenDraftedKeysRef.current ??= new Set();
              seenDraftedKeysRef.current.add(draftedKey);
            },
            refreshStatus,
          })
        ) {
          return;
        }
        if (event === "subsection_start") {
          labelBatchSubheading(data, setDraftingLabel);
          return;
        }
        if (event === "subsection_done") {
          finishBatchSubsection(data, onSectionDone, refreshStatus);
          return;
        }
        if (event === "progress") {
          const message = typeof data.message === "string" ? data.message : "";
          if (message) setDraftingLabel(message);
          return;
        }
        if (event === "all_done") {
          finishBatchAll(data, totalSectionsRef.current, {
            applyProgress,
            setDraftingLabel,
            setPhase,
            setBusy,
            onAllDrafted,
            refreshStatus,
          });
          return;
        }
        if (event === "section_error") {
          failed = true;
          failBatchSection(ids, key, data, setError, setMessages);
        }
      }
    );
    return !failed;
  }

  async function startDrafting() {
    setBusy(true);
    setPhase("drafting");
    setError(null);
    setMessages([
      {
        id: "sys-start",
        role: "system",
        content: "กำลังเริ่มร่างตามประเภทงานอัตโนมัติ — หมวดขอบเขตงานจะเติมลงหัวข้อย่อยโดยตรง",
      },
    ]);

    try {
      if (await refreshStatus()) {
        return;
      }
      let ok = false;
      try {
        ok = await streamBatchDraft();
      } catch {
        ok = false;
      }
      if (await refreshStatus()) {
        return;
      }
      if (!ok) {
        try {
          ok = await streamBatchDraft();
        } catch {
          ok = false;
        }
      }
      const done = await refreshStatus();
      if (!done) {
        setPhase((prev) => (prev === "complete" ? prev : "drafting"));
      }
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "เริ่มร่างไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(
    text?: string,
    sectionKeyOverride?: string,
    extras?: { confirmInsert?: boolean; searchHits?: SearchHit[] }
  ) {
    const content = (text || draft).trim();
    if (!content || busy) return;
    if (!text) setDraft("");
    setBusy(true);
    setError(null);
    const sectionKey = sectionKeyOverride || currentEditSection;

    // Add user message
    setMessages((prev) => [
      ...prev,
      { id: `user-${Date.now()}`, role: "user", content },
    ]);

    const controller = new AbortController();
    let responseMsgId = `bot-resp-${Date.now()}`;
    let responseTokens = "";

    setMessages((prev) => [
      ...prev,
      { id: responseMsgId, role: "bot", content: "", status: "drafting" },
    ]);

    try {
      await streamSsePost(
        `${API_BASE}/projects/${projectId}/draft-chat/message`,
        {
          content,
          section_key: sectionKey,
          confirm_insert: Boolean(extras?.confirmInsert),
          search_hits: extras?.searchHits,
        },
        token,
        (event: string, data: Record<string, unknown>) => {
          if (event === "section_start" || event === "token" || event === "section_done") {
            responseTokens = applyReplyStreamEvent(
              event,
              data,
              responseMsgId,
              responseTokens,
              sectionKey,
              { setMessages, onSectionDone, setBusy }
            );
            return;
          }
          if (event === "product_search") {
            const hits = asSearchHits(data.results);
            const disclaimer = typeof data.disclaimer === "string" ? data.disclaimer : undefined;
            setMessages((prev) => prev.map((m) => productSearchMessage(m, responseMsgId, hits, disclaimer)));
            setBusy(false);
          }
          if (event === "search_inserted") {
            const content2 = typeof data.content === "string" ? data.content : "";
            const insertedKey = typeof data.section_key === "string" ? data.section_key : undefined;
            setMessages((prev) => prev.map((m) => insertedSearchMessage(m, responseMsgId, content2, insertedKey)));
            onSectionDone?.(
              typeof data.section_key === "string" ? data.section_key : sectionKey || undefined,
              content2
            );
            setBusy(false);
          }
          if (event === "accepted") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId
                  ? { ...m, content: "ยอมรับแล้ว ✓", status: "accepted" }
                  : m
              )
            );
            onSectionDone?.();
            setBusy(false);
          }
          if (event === "done") {
            setBusy(false);
          }
          if (event === "error" || event === "section_error") {
            const msg = data.message as string;
            setError(msg);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId
                  ? { ...m, content: msg || "เกิดข้อผิดพลาด", status: "error" }
                  : m
              )
            );
            setBusy(false);
          }
        },
        controller.signal
      );
      setCurrentEditSection(null);
      await refreshStatus();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ส่งข้อความไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  function handleAccept(sectionKey: string) {
    setCurrentEditSection(sectionKey);
    void sendMessage("ยอมรับ", sectionKey);
  }

  function handleRedraft(sectionKey: string) {
    setCurrentEditSection(sectionKey);
    void sendMessage(`ร่างใหม่ ${sectionKey}`, sectionKey);
  }

  function handleEdit(sectionKey: string) {
    setCurrentEditSection(sectionKey);
    setDraft(`แก้ไข ${formatTorSectionHeading(sectionKey)}: `);
  }

  function handleConfirmSearch(hits: SearchHit[]) {
    void sendMessage("ยืนยันแทรกแหล่งค้นหา", currentEditSection || "s4", {
      confirmInsert: true,
      searchHits: hits,
    });
  }

  const hint = phaseStatusCopy(phase, draftingLabel);

  return (
    <div className="flex flex-col rounded-xl border bg-white" data-testid="draft-chat">
      {/* Progress header */}
      <div className="border-b px-4 py-3">
        <div className="flex items-center justify-between text-sm">
          <span className="font-bold text-navy">ร่าง TOR อัตโนมัติ</span>
          <span className="text-muted-foreground" data-testid="draft-chat-count">
            {draftedCount}/{totalSections} หมวด
          </span>
        </div>
        <div className="mt-2 h-2 rounded-full bg-gray-100">
          <div
            className="h-2 rounded-full bg-brand-green transition-all"
            style={{ width: `${(draftedCount / totalSections) * 100}%` }}
            data-testid="draft-progress-bar"
          />
        </div>
        {hint ? <p className={hint.className}>{hint.text}</p> : null}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-3" style={{ maxHeight: "60vh" }}>
        {messages.map((msg) => (
          <div key={msg.id} className="mb-4">
            <DraftChatMessage
              msg={msg}
              busy={busy}
              onAccept={handleAccept}
              onEdit={handleEdit}
              onRedraft={handleRedraft}
              onConfirmSearch={handleConfirmSearch}
            />
          </div>
        ))}
        <div ref={endRef} />
      </div>

      {/* Error */}
      {error ? (
        <p className="px-4 pb-2 text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}

      {/* Input */}
      <div className="border-t px-4 py-3">
        <div className="flex gap-2">
          <input
            type="text"
            className="flex-1 rounded-lg border px-3 py-2 text-sm focus:border-navy focus:outline-none"
            placeholder={
              phase === "drafting"
                ? "กำลังร่าง... รอสักครู่"
                : "พิมพ์ข้อเสนอแนะ เช่น 'แก้ไข 1. ความเป็นมา: เพิ่มรายละเอียด...'"
            }
            value={draft}
            disabled={busy || phase === "drafting"}
            data-testid="draft-chat-input"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void sendMessage();
              }
            }}
          />
          <Button
            size="sm"
            disabled={busy || !draft.trim() || phase === "drafting"}
            data-testid="draft-chat-send"
            onClick={() => {
              void sendMessage();
            }}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        {currentEditSection ? (
          <p className="mt-1 font-mono text-xs text-muted-foreground">
            กำลังแก้ไข · {formatTorSectionHeading(currentEditSection)}
          </p>
        ) : null}
      </div>

      {/* Section index strip */}
      {sections.length > 0 ? (
        <div className="border-t px-4 py-2">
          <div className="flex flex-wrap gap-1">
            {sections.map((s) => (
              <span
                key={s.section_key}
                className={cn(
                  "border px-1.5 py-0.5 font-mono text-[10px] tabular-nums tracking-wide",
                  s.has_content
                    ? "border-brand-green/30 bg-green-50 text-green-900"
                    : "border-gray-200 text-muted-foreground"
                )}
                data-testid={`draft-section-badge-${s.section_key}`}
                title={s.title}
              >
                {sectionIndexPad(s.section_key)}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
