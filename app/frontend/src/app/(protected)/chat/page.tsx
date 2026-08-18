"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div data-testid="chat-page">
      <p className="mb-3 text-sm text-muted-foreground">
        ถาม-ตอบจากคลังกลางด้วยโมเดลในเครื่อง (Gemma) — คำตอบอ้างไฟล์ต้นฉบับและมาตรา ไม่ใช่หน้าจำลอง
      </p>
      <ChatShell kind="kb" />
    </div>
  );
}
