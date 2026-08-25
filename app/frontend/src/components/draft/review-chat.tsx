"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { HITL_SECTIONS, TOR_SECTION_LABELS, type TorSectionKey } from "@/lib/tor-sections";
import type { ReviewFinding } from "@/lib/review-findings";

function reviewOpening(score: number | null, findings: ReviewFinding[]): string {
  if (score == null) {
    return "กำลังรัน Rule Engine เพื่อทบทวนร่าง TOR...";
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
    lines.push("ไม่พบประเด็นสำคัญจาก Rule Engine");
  }
  lines.push(
    "พิมพ์ได้เลย เช่น ยืนยันหมวด 6, ยอมรับหมวดกฎหมาย, หรือ ตรวจอีกครั้ง"
  );
  return lines.join("\n");
}

function parseHitlKey(text: string): string | null {
  const raw = text.trim();
  if (raw.includes("รันใหม่") || raw.includes("ตรวจอีกครั้ง")) {
    return null;
  }
  if (!/ยอมรับ|ยืนยัน/.test(raw)) {
    return null;
  }
  for (let number = 13; number >= 1; number -= 1) {
    if (raw.includes(`หมวด ${number}`) || raw.includes(`s${number}`)) {
      return `s${number}`;
    }
  }
  for (const key of HITL_SECTIONS) {
    const label = TOR_SECTION_LABELS[key as TorSectionKey];
    if (label && raw.includes(label)) {
      return key;
    }
  }
  return null;
}

export function ReviewChat({
  score,
  findings,
  busy,
  onReview,
  onAcceptHitl,
}: Readonly<{
  score: number | null;
  findings: ReviewFinding[];
  busy: boolean;
  onReview: (force?: boolean) => Promise<void>;
  onAcceptHitl: (sectionKey: string) => Promise<void>;
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
    onReview().catch(() => undefined);
  }, [onReview]);

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
    const key = parseHitlKey(content);
    if (key) {
      await onAcceptHitl(key);
      const label = TOR_SECTION_LABELS[key as TorSectionKey] || key;
      setMessages((prev) => [...prev, `ยืนยันหมวด ${label} แล้วครับ`]);
      return;
    }
    setMessages((prev) => [
      ...prev,
      "พิมพ์ ยืนยันหมวด 6 หรือ ตรวจอีกครั้ง ได้ครับ",
    ]);
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
          placeholder="ยืนยันหมวด 6 หรือ ตรวจอีกครั้ง"
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
