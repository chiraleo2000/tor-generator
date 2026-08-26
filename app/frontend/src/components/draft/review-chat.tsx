"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ReviewFinding } from "@/lib/review-findings";

function reviewOpening(score: number | null, findings: ReviewFinding[]): string {
  if (score == null) {
    return "กำลังตรวจด้วยกฎระเบียบ พ.ร.บ. และเอกสารขั้นที่ ๐ ของโครงการนี้...";
  }
  const lines = [
    `ตรวจร่างแล้ว ได้คะแนนคุณภาพ ${score}/100`,
  ];
  if (findings.length) {
    lines.push("ประเด็นที่พบ:");
    findings.slice(0, 6).forEach((item) => {
      lines.push(`- ${item.message}`);
    });
  } else {
    lines.push("ไม่พบประเด็นสำคัญจากการตรวจกฎ");
  }
  lines.push("พิมพ์ได้เลย เช่น ตรวจอีกครั้ง หรือถามว่าร่างยังขาดอะไร");
  return lines.join("\n");
}

export function ReviewChat({
  score,
  findings,
  busy,
  onReview,
  onAsk,
}: Readonly<{
  score: number | null;
  findings: ReviewFinding[];
  busy: boolean;
  onReview: (force?: boolean) => Promise<void>;
  onAsk?: (question: string) => Promise<string>;
}>) {
  const [draft, setDraft] = useState("");
  const [messages, setMessages] = useState<string[]>(() => [reviewOpening(score, findings)]);
  const started = useRef(false);
  const findingsRef = useRef(findings);
  findingsRef.current = findings;
  const findingKey = findings.map((item) => item.message).join("\n");

  useEffect(() => {
    if (started.current) {
      return;
    }
    started.current = true;
    if (score != null) {
      return;
    }
    onReview().catch(() => undefined);
  }, [onReview, score]);

  useEffect(() => {
    if (score == null && !findingKey) {
      return;
    }
    setMessages((prev) => {
      const next = reviewOpening(score, findingsRef.current);
      if (prev.at(-1) === next) {
        return prev;
      }
      return [...prev, next];
    });
  }, [score, findingKey]);

  async function send() {
    const content = draft.trim();
    if (!content || busy) {
      return;
    }
    setDraft("");
    setMessages((prev) => [...prev, `คุณ: ${content}`]);
    if (content.includes("รันใหม่") || content.includes("ตรวจอีกครั้ง")) {
      setMessages((prev) => [...prev, "กำลังตรวจอีกครั้ง..."]);
      await onReview(true);
      return;
    }
    if (onAsk) {
      try {
        const reply = await onAsk(content);
        setMessages((prev) => [...prev, reply || "ยังให้ความเห็นไม่ได้ กรุณาลองใหม่"]);
      } catch {
        setMessages((prev) => [...prev, "ถามความเห็นไม่สำเร็จ กรุณาลองใหม่"]);
      }
      return;
    }
    setMessages((prev) => [...prev, "พิมพ์ ตรวจอีกครั้ง หรือถามความเห็นได้ครับ"]);
  }

  return (
    <div className="mt-4 rounded-xl border bg-white" data-testid="review-chat">
      <div className="max-h-64 space-y-2 overflow-y-auto p-3 text-sm" data-testid="review-chat-messages">
        {messages.map((item, index) => (
          <p key={`${index}-${item.slice(0, 24)}`} className="whitespace-pre-wrap">
            {item}
          </p>
        ))}
      </div>
      <div className="flex gap-2 border-t p-3">
        <input
          className="flex-1 rounded-md border px-3 py-2 text-sm"
          data-testid="review-chat-input"
          placeholder="ถามความเห็น หรือพิมพ์ ตรวจอีกครั้ง"
          value={draft}
          disabled={busy}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              send().catch(() => undefined);
            }
          }}
        />
        <Button
          size="sm"
          data-testid="review-chat-send"
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
