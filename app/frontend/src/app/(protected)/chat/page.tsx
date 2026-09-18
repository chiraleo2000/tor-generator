"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div className="min-w-0" data-testid="chat-page">
      <ChatShell kind="kb" />
    </div>
  );
}
