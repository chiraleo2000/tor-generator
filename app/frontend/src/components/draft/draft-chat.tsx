"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Pencil, RotateCcw, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { streamSsePost } from "@/lib/chat-sse";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

interface SectionStatus {
  section_key: string;
  title: string;
  has_content: boolean;
  content_preview: string;
  human_confirmed: boolean;
}

interface DraftMessage {
  id: string;
  role: "user" | "bot" | "system";
  content: string;
  sectionKey?: string;
  sectionTitle?: string;
  isDraft?: boolean;
  status?: "drafting" | "done" | "error" | "accepted" | "editing";
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

type DraftPhase = "idle" | "drafting" | "reviewing" | "complete";

function phaseStatusCopy(phase: DraftPhase): { text: string; className: string } | null {
  if (phase === "drafting") {
    return { text: "กำลังร่าง... กรุณารอ", className: "mt-1.5 text-xs text-amber-700" };
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
    return "bg-green-100 text-green-800";
  }
  if (status === "error") {
    return "bg-red-100 text-red-800";
  }
  if (status === "accepted") {
    return "bg-brand-green text-white";
  }
  return "bg-amber-100 text-amber-800";
}

function DraftChatMessage({
  msg,
  busy,
  onAccept,
  onEdit,
  onRedraft,
}: Readonly<{
  msg: DraftMessage;
  busy: boolean;
  onAccept: (key: string) => void;
  onEdit: (key: string) => void;
  onRedraft: (key: string) => void;
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
                "rounded-full px-2.5 py-0.5 text-[11px] font-bold",
                sectionBadgeClass(msg.status)
              )}
            >
              {msg.sectionKey}
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
}: Readonly<{
  projectId: string;
  onAllDrafted: () => void;
  onSectionDone?: () => void;
}>) {
  const token = useAuthStore((state) => state.token);
  const [messages, setMessages] = useState<DraftMessage[]>([]);
  const [sections, setSections] = useState<SectionStatus[]>([]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [draftedCount, setDraftedCount] = useState(0);
  const [totalSections] = useState(13);
  const [phase, setPhase] = useState<"idle" | "drafting" | "reviewing" | "complete">("idle");
  const [currentEditSection, setCurrentEditSection] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);
  const started = useRef(false);

  const scrollToEnd = useCallback(() => {
    const node = endRef.current;
    if (node && typeof node.scrollIntoView === "function") {
      node.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  useEffect(scrollToEnd, [messages, scrollToEnd]);

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
      }>(response);
      setSections(data.sections);
      setDraftedCount(data.drafted_count);
      if (data.all_drafted) {
        setPhase("complete");
        onAllDrafted();
      }
    } catch {
      // non-critical — status display only
    }
  }, [projectId, onAllDrafted]);

  // Auto-start drafting on mount
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    startDrafting();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function startDrafting() {
    setBusy(true);
    setPhase("drafting");
    setError(null);
    setMessages([
      {
        id: "sys-start",
        role: "system",
        content: "กำลังเริ่มร่าง TOR ทั้ง 13 หมวดอัตโนมัติ — กรุณารอสักครู่...",
      },
    ]);

    const controller = new AbortController();
    let currentSectionId = "";
    let currentTokens = "";

    try {
      await streamSsePost(
        `${API_BASE}/projects/${projectId}/draft-chat/start`,
        {},
        token,
        (event: string, data: Record<string, unknown>) => {
          if (event === "section_start") {
            const key = data.section_key as string;
            const title = data.title as string;
            currentSectionId = `draft-${key}-${Date.now()}`;
            currentTokens = "";
            setMessages((prev) => [
              ...prev,
              {
                id: currentSectionId,
                role: "bot",
                content: "",
                sectionKey: key,
                sectionTitle: title,
                isDraft: true,
                status: "drafting",
              },
            ]);
          }
          if (event === "token") {
            const t = typeof data.text === "string" ? data.text : "";
            currentTokens += t;
            const captured = currentTokens;
            const capturedId = currentSectionId;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === capturedId ? { ...m, content: captured } : m
              )
            );
          }
          if (event === "section_done") {
            const content = data.content as string;
            const count = data.drafted_count as number;
            setDraftedCount(count);
            const capturedId = currentSectionId;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === capturedId
                  ? { ...m, content, status: "done" }
                  : m
              )
            );
            onSectionDone?.();
          }
          if (event === "section_error") {
            const capturedId = currentSectionId;
            const msg = data.message as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === capturedId
                  ? { ...m, content: `ร่างไม่สำเร็จ: ${msg}`, status: "error" }
                  : m
              )
            );
          }
          if (event === "all_done") {
            const count = data.drafted_count as number;
            setDraftedCount(count);
            setPhase("reviewing");
            setMessages((prev) => [
              ...prev,
              {
                id: `sys-done-${Date.now()}`,
                role: "system",
                content: `ร่างครบ ${count}/13 หมวดแล้ว — ตรวจแต่ละหมวดแล้วกด ยอมรับ หรือ ขอแก้ไข`,
              },
            ]);
          }
        },
        controller.signal
      );
      await refreshStatus();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "เริ่มร่างไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function sendMessage(text?: string) {
    const content = (text || draft).trim();
    if (!content || busy) return;
    if (!text) setDraft("");
    setBusy(true);
    setError(null);

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
        { content, section_key: currentEditSection },
        token,
        (event: string, data: Record<string, unknown>) => {
          if (event === "section_start") {
            const key = data.section_key as string;
            const title = data.title as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId
                  ? { ...m, sectionKey: key, sectionTitle: title, isDraft: true }
                  : m
              )
            );
          }
          if (event === "token") {
            const t = typeof data.text === "string" ? data.text : "";
            responseTokens += t;
            const captured = responseTokens;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId ? { ...m, content: captured } : m
              )
            );
          }
          if (event === "section_done") {
            const content2 = data.content as string;
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId
                  ? { ...m, content: content2, status: "done", isDraft: true }
                  : m
              )
            );
            onSectionDone?.();
          }
          if (event === "accepted") {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId
                  ? { ...m, content: "ยอมรับแล้ว ✓", status: "accepted" }
                  : m
              )
            );
          }
          if (event === "error") {
            const msg = data.message as string;
            setError(msg);
            setMessages((prev) =>
              prev.map((m) =>
                m.id === responseMsgId
                  ? { ...m, content: msg || "เกิดข้อผิดพลาด", status: "error" }
                  : m
              )
            );
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
    sendMessage("ยอมรับ");
  }

  function handleRedraft(sectionKey: string) {
    setCurrentEditSection(sectionKey);
    sendMessage(`ร่างใหม่ ${sectionKey}`);
  }

  function handleEdit(sectionKey: string) {
    setCurrentEditSection(sectionKey);
    setDraft(`แก้ไข หมวด ${sectionKey.replace("s", "")}: `);
  }

  const hint = phaseStatusCopy(phase);

  return (
    <div className="flex flex-col rounded-xl border bg-white" data-testid="draft-chat">
      {/* Progress header */}
      <div className="border-b px-4 py-3">
        <div className="flex items-center justify-between text-sm">
          <span className="font-bold text-navy">ร่าง TOR อัตโนมัติ</span>
          <span className="text-muted-foreground">
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
                : "พิมพ์ข้อเสนอแนะ เช่น 'แก้ไข หมวด 1: เพิ่มรายละเอียด...'"
            }
            value={draft}
            disabled={busy || phase === "drafting"}
            data-testid="draft-chat-input"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
          />
          <Button
            size="sm"
            disabled={busy || !draft.trim() || phase === "drafting"}
            data-testid="draft-chat-send"
            onClick={() => sendMessage()}
          >
            <Send className="h-4 w-4" />
          </Button>
        </div>
        {currentEditSection ? (
          <p className="mt-1 text-xs text-muted-foreground">
            กำลังแก้ไข: หมวด {currentEditSection}
          </p>
        ) : null}
      </div>

      {/* Section sidebar (mini) */}
      {sections.length > 0 ? (
        <div className="border-t px-4 py-2">
          <div className="flex flex-wrap gap-1.5">
            {sections.map((s) => (
              <span
                key={s.section_key}
                className={cn(
                  "rounded-full px-2 py-0.5 text-[10px] font-bold",
                  s.has_content
                    ? "bg-green-100 text-green-800"
                    : "bg-gray-100 text-gray-500"
                )}
                data-testid={`draft-section-badge-${s.section_key}`}
                title={s.title}
              >
                {s.has_content ? "✓" : "○"} {s.section_key.replace("s", "")}
              </span>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
