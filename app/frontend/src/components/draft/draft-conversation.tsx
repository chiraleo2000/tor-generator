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
  onCoverage?: (rows: CoverageRow[]) => void;
  onSectionRevised?: () => void;
}>) {
  const token = useAuthStore((state) => state.token);
  const [roomId, setRoomId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const onCoverageRef = useRef(onCoverage);
  onCoverageRef.current = onCoverage;
  const onSectionRevisedRef = useRef(onSectionRevised);
  onSectionRevisedRef.current = onSectionRevised;

  const loadMessages = useCallback(async (id: string) => {
    const response = await apiClient.get(`/chat/rooms/${id}/messages`);
    const payload = unwrapData<{ messages?: ChatMessageItem[] }>(response);
    setMessages(payload.messages || []);
  }, []);

  useEffect(() => {
    let live = true;
    const path = mode === "compose" ? "open-draft" : "open-qa";
    apiClient
      .post(`/projects/${projectId}/intake/${path}`)
      .then(async (response) => {
        const payload = unwrapData<{ room_id?: string; coverage?: CoverageRow[] }>(response);
        if (!live) return;
        const id = payload.room_id || "";
        setRoomId(id);
        if (payload.coverage) onCoverageRef.current?.(payload.coverage);
        if (id) await loadMessages(id);
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

  async function sendIntake(content: string) {
    const controller = new AbortController();
    abortRef.current = controller;
    await streamSsePost(
      `${apiBase}/projects/${projectId}/intake/chat`,
      { content, search_scope: "both" },
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
    setDraft("");
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
        await sendIntake(content);
      }
      if (roomId) await loadMessages(roomId);
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
      <div className="flex items-end gap-2 border-t p-3">
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
    </div>
  );
}
