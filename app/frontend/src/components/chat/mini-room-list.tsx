"use client";

import { Folder, MessageSquare, MoreHorizontal, Plus, Search, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatRoomCard } from "@/lib/chat-sse";

function isToday(iso: string | null): boolean {
  if (!iso) return false;
  const date = new Date(iso);
  const now = new Date();
  return date.toDateString() === now.toDateString();
}

function timeLabel(iso: string | null): string {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit" });
}

export function MiniRoomList({
  rooms,
  activeId,
  search,
  collapsed,
  onSearch,
  onSelect,
  onNew,
  onRename,
  onDelete,
  onToggleCollapse,
}: Readonly<{
  rooms: ChatRoomCard[];
  activeId: string | null;
  search: string;
  collapsed: boolean;
  onSearch: (value: string) => void;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string) => void;
  onDelete: (id: string) => void;
  onToggleCollapse: () => void;
}>) {
  const filtered = rooms.filter((room) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;
    return (
      room.title.toLowerCase().includes(q) ||
      (room.last_message || "").toLowerCase().includes(q)
    );
  });
  const today = filtered.filter((room) => isToday(room.updated_at));
  const earlier = filtered.filter((room) => !isToday(room.updated_at));

  return (
    <aside
      data-testid="chat-room-list"
      className={cn(
        "flex shrink-0 flex-col border-r bg-white",
        collapsed ? "w-14" : "w-[260px]"
      )}
    >
      <div className="flex items-center gap-1 border-b p-2">
        <button
          type="button"
          title="ห้องใหม่"
          data-testid="chat-new-room"
          className="rounded-md p-1.5 hover:bg-muted"
          onClick={onNew}
        >
          <Plus className="h-4 w-4" />
        </button>
        {collapsed ? null : (
          <div className="relative min-w-0 flex-1">
            <Search className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              data-testid="chat-room-search"
              className="w-full rounded-md border py-1 pl-7 pr-2 text-xs"
              placeholder="ค้นหาห้อง"
              value={search}
              onChange={(event) => onSearch(event.target.value)}
            />
          </div>
        )}
        <button
          type="button"
          title="ปักหมุด (เร็ว ๆ นี้)"
          className="rounded-md p-1.5 text-muted-foreground"
          disabled
        >
          <Folder className="h-4 w-4" />
        </button>
        <button
          type="button"
          title="ยุบแถบ"
          className="rounded-md p-1.5 hover:bg-muted"
          onClick={onToggleCollapse}
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>
      {collapsed ? null : (
        <div className="flex-1 overflow-y-auto p-2">
          <RoomGroup title="วันนี้" rooms={today} activeId={activeId} onSelect={onSelect} onRename={onRename} onDelete={onDelete} />
          <RoomGroup title="ก่อนหน้า" rooms={earlier} activeId={activeId} onSelect={onSelect} onRename={onRename} onDelete={onDelete} />
        </div>
      )}
    </aside>
  );
}

function RoomGroup({
  title,
  rooms,
  activeId,
  onSelect,
  onRename,
  onDelete,
}: Readonly<{
  title: string;
  rooms: ChatRoomCard[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onRename: (id: string) => void;
  onDelete: (id: string) => void;
}>) {
  if (!rooms.length) return null;
  return (
    <div className="mb-3">
      <p className="mb-1 px-1 text-[11px] font-bold uppercase tracking-wide text-muted-foreground">
        {title}
      </p>
      {rooms.map((room) => (
        <div
          key={room.id}
          className={cn(
            "group mb-1 flex items-start gap-2 rounded-lg px-2 py-1.5",
            activeId === room.id ? "bg-brand-orange/40" : "hover:bg-muted"
          )}
        >
          <button
            type="button"
            className="flex min-w-0 flex-1 items-start gap-2 text-left"
            data-testid="chat-room-item"
            onClick={() => onSelect(room.id)}
          >
            <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy text-[11px] font-bold text-white">
              <MessageSquare className="h-3.5 w-3.5" />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] font-semibold text-navy">
                {room.title}
              </span>
              <span className="block truncate text-[11px] text-muted-foreground">
                {room.last_message || "ยังไม่มีข้อความ"}
              </span>
            </span>
            <span className="shrink-0 text-[10px] text-muted-foreground">
              {timeLabel(room.updated_at)}
            </span>
          </button>
          <div className="hidden shrink-0 group-hover:flex">
            <button
              type="button"
              title="เปลี่ยนชื่อ"
              className="rounded p-1 hover:bg-white"
              onClick={() => onRename(room.id)}
            >
              <MoreHorizontal className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              title="ลบ"
              className="rounded p-1 hover:bg-white"
              onClick={() => onDelete(room.id)}
            >
              <Trash2 className="h-3.5 w-3.5 text-red-600" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
