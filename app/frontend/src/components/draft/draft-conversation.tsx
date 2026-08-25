"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { streamSsePost, type ChatMessageItem } from "@/lib/chat-sse";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";
import type { CoverageRow } from "@/components/draft/phase1-coverage";

function briefAsMessage(brief: string): ChatMessageItem {
  return {
    id: "phase2-brief",
    role: "assistant",
    content: brief,
    citations: [],
  };
}

export function DraftConversation({
  projectId,
  mode,
  apiBase,
  placeholder,
  onCoverage,
  onSectionRevised,
}: Readonly<{
  projectId: string;
  mode: "intake" | "compose";
  apiBase: string;
  placeholder?: string;
  coverage?: CoverageRow[];
  onCoverage?: (rows: CoverageRow[]) => void;
  onSectionRevised?: () => void;
}>) {
  const token = useAuthStore((state) => state.token);
  const [roomId, setRoomId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [attachLegal, setAttachLegal] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const onCoverageRef = useRef(onCoverage);
  onCoverageRef.current = onCoverage;
  const onSectionRevisedRef = useRef(onSectionRevised);
  onSectionRevisedRef.current = onSectionRevised;

  const loadMessages = useCallback(async (id: string) => {
    const response = await apiClient.get(`/chat/rooms/${id}/messages`);
    const payload = unwrapData<{ messages?: ChatMessageItem[] }>(response);
    return payload.messages || [];
  }, []);

  useEffect(() => {
    let live = true;
    const path = mode === "compose" ? "open-draft" : "open-qa";
    apiClient
      .post(`/projects/${projectId}/intake/${path}`)
      .then(async (response) => {
        const payload = unwrapData<{
          room_id?: string;
          coverage?: CoverageRow[];
          brief?: string;
        }>(response);
        if (!live) return;
        const id = payload.room_id || "";
        setRoomId(id);
        if (payload.coverage?.length) {
          onCoverageRef.current?.(payload.coverage);
        }
        let loaded: ChatMessageItem[] = [];
        if (id) {
          loaded = await loadMessages(id);
        }
        if (!live) return;
        if (loaded.length) {
          setMessages(loaded);
          return;
        }
        if (payload.brief) {
          setMessages([briefAsMessage(payload.brief)]);
        }
      })
      .catch(() => {
        if (live) setError("โหลดบทสนทนาร่างไม่สำเร็จ");
      });
    return () => {
      live = false;
    };
  }, [projectId, mode, loadMessages]);

  useEffect(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === "function") {
      node.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  async function sendIntake(content: string, withLegal: boolean) {
    const controller = new AbortController();
    abortRef.current = controller;
    await streamSsePost(
      `${apiBase}/projects/${projectId}/intake/chat`,
      { content, search_scope: "both", attach_legal_reference: withLegal },
      token,
      (event, data) => {
        if (event === "token") {
          const piece = typeof data.text === "string" ? data.text : "";
          setMessages((prev) => {
            const last = prev.at(-1);
            if (last?.role !== "assistant") return prev;
            return [...prev.slice(0, -1), { ...last, content: last.content + piece }];
          });
        }
        if (event === "done") {
          const text = typeof data.content === "string" ? data.content : "";
          setMessages((prev) => {
            const last = prev.at(-1);
            if (last?.role !== "assistant") return prev;
            return [...prev.slice(0, -1), { ...last, content: text || last.content }];
          });
          if (Array.isArray(data.coverage)) {
            onCoverageRef.current?.(data.coverage as CoverageRow[]);
          }
        }
        if (event === "error") {
          setError(typeof data.message === "string" ? data.message : "แชทล้มเหลว");
        }
      },
      controller.signal
    );
  }

  async function sendCompose(content: string) {
    const response = await apiClient.post(`/projects/${projectId}/draft-chat`, { content });
    const payload = unwrapData<{ reply?: string }>(response);
    setMessages((prev) => [
      ...prev.slice(0, -1),
      {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: payload.reply || "ปรับร่างแล้วครับ",
        citations: [],
      },
    ]);
    onSectionRevisedRef.current?.();
  }

  async function send() {
    const content = draft.trim();
    if (!content || busy) return;
    const withLegal = mode === "intake" && attachLegal;
    setDraft("");
    setAttachLegal(false);
    setBusy(true);
    setError(null);
    const sentAt = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", content, citations: [], created_at: sentAt },
      { id: `a-${Date.now()}`, role: "assistant", content: "", citations: [], created_at: sentAt },
    ]);
    try {
      if (mode === "compose") {
        await sendCompose(content);
      } else {
        await sendIntake(content, withLegal);
      }
      if (roomId) {
        const loaded = await loadMessages(roomId);
        if (loaded.length) setMessages(loaded);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "ส่งข้อความไม่สำเร็จ");
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  return (
    <div className="flex min-h-[48vh] flex-col overflow-hidden rounded-xl border bg-white" data-testid="draft-conversation">
      {error ? (
        <p className="px-4 py-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <div className="flex-1 space-y-3 overflow-y-auto p-4" data-testid="chat-messages">
        {messages.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            กำลังเปิดบทจากผลวิเคราะห์...
          </p>
        ) : null}
        {messages.map((item) => (
          <article
            key={item.id}
            data-testid={item.role === "assistant" ? "chat-msg-assistant" : "chat-msg-user"}
            className={cn(
              "max-w-[85%] rounded-xl px-3 py-2 text-sm whitespace-pre-wrap",
              item.role === "user" ? "ml-auto bg-navy text-white" : "bg-muted text-foreground"
            )}
          >
            {item.content || (busy && item.role === "assistant" ? "กำลังพิมพ์..." : "")}
          </article>
        ))}
        <div ref={endRef} />
      </div>
      <div className="border-t p-3">
        <div className="flex items-end gap-2">
          <textarea
            data-testid="chat-input"
            className="min-h-[48px] flex-1 rounded-md border p-2 text-sm"
            value={draft}
            placeholder={placeholder || "ตอบเป็นภาษาพูดได้เลย"}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                send().catch(() => undefined);
              }
            }}
          />
          <Button
            type="button"
            data-testid="chat-send"
            disabled={busy || !draft.trim()}
            onClick={() => {
              send().catch(() => undefined);
            }}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        {mode === "intake" ? (
          <label className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              data-testid="intake-attach-legal"
              checked={attachLegal}
              disabled={busy}
              onChange={(event) => setAttachLegal(event.target.checked)}
            />
            {" "}
            <span>แนบอ้างอิงกฎหมายประกอบคำตอบนี้</span>
          </label>
        ) : null}
      </div>
    </div>
  );
}
