"use client";

import { usePathname } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";
import { pageMeta } from "@/lib/page-meta";

export function Header() {
  const pathname = usePathname();
  const user = useAuthStore((state) => state.user);
  const meta = pageMeta(pathname);
  const initial = (user?.name || user?.email || "?").slice(0, 1).toUpperCase();

  return (
    <header className="flex shrink-0 items-center justify-between border-b bg-white px-[26px] py-3.5 shadow-[0_2px_4px_rgba(0,0,0,0.04)]">
      <div>
        <h1 className="text-[21px] font-extrabold text-navy">{meta.title}</h1>
        <p className="mt-0.5 text-[12.5px] text-muted-foreground">{meta.sub}</p>
      </div>
      <div className="flex items-center gap-3 text-[13px]">
        <span className="hidden sm:inline">{user?.email}</span>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-navy font-bold text-white">
          {initial}
        </div>
      </div>
    </header>
  );
}
