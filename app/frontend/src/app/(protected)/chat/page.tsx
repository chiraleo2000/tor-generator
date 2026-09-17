"use client";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return (
    <div data-testid="chat-page">
      <ChatShell kind="kb" />
    </div>
  );
}
