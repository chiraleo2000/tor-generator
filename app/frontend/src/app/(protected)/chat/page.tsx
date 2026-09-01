"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div data-testid="chat-page">
      <p className="mb-3 text-sm text-muted-foreground">
        ถาม-ตอบจากคลังกฎหมาย (pgvector / RAG) — ดึงหลายชิ้นจากคลังแล้วตอบเป็นย่อหน้าเนื้อหา อ้างมาตราและไฟล์ต้นฉบับในเนื้อหาเมื่อมีในบริบท
      </p>
      <ChatShell kind="kb" />
    </div>
  );
}
