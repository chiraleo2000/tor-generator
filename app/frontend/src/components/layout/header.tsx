"use client";

import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { useUIStore } from "@/stores/ui-store";
import { pageMeta } from "@/lib/page-meta";

export function Header() {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const meta = pageMeta(pathname);
  const initial = (user?.name || user?.email || "?").slice(0, 1).toUpperCase();

  return (
    <header className="flex shrink-0 items-center justify-between gap-3 border-b bg-white px-3 py-3 shadow-[0_2px_4px_rgba(0,0,0,0.04)] sm:px-5 lg:px-[26px] lg:py-3.5">
      <div className="flex min-w-0 items-center gap-2">
        <button
          type="button"
          data-testid="nav-toggle"
          aria-label="เปิดเมนู"
          aria-expanded={sidebarOpen}
          className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border text-navy lg:hidden"
          onClick={toggleSidebar}
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-lg font-extrabold text-navy sm:text-[21px]">{meta.title}</h1>
          <p className="mt-0.5 hidden text-[12.5px] text-muted-foreground sm:block">{meta.sub}</p>
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-3 text-[13px]">
        <span className="hidden max-w-[12rem] truncate sm:inline">{user?.email}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-navy font-bold text-white">
          {initial}
        </div>
      </div>
    </header>
  );
}
