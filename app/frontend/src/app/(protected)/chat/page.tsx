"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div data-testid="chat-page">
      <p className="mb-3 text-sm text-muted-foreground">
        ถาม-ตอบจากคลังกลาง (ข้อมูลดิบที่ฝังด้วย EmbeddingGemma) และเอกสารที่คุณอัปโหลดเอง
        คำตอบอ้างไฟล์ต้นฉบับและมาตราในกราฟกฎหมาย
      </p>
      <ChatShell kind="kb" />
    </div>
  );
}
