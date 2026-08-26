"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div data-testid="chat-page">
      <p className="mb-3 text-sm text-muted-foreground">
        ถาม-ตอบจากคลังกฎหมาย (pgvector / RAG) ด้วย Gemma — ดึงหลายชิ้นจากคลังแล้วตอบแบบเจ้าหน้าที่พัสดุ อ้างมาตราและไฟล์ต้นฉบับ
      </p>
      <ChatShell kind="kb" />
    </div>
  );
}
