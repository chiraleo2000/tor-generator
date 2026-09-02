"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div data-testid="chat-page">
      <p className="mb-3 text-sm text-muted-foreground">
        ถาม-ตอบจากคลังกฎหมายด้วย PageIndex และ Claude Sonnet 4.6 พร้อมอ้างมาตราและไฟล์ต้นฉบับ
      </p>
      <ChatShell kind="kb" />
    </div>
  );
}
