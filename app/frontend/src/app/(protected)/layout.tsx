"use client";

import { useEffect } from "react";
import { AuthGuard } from "@/components/auth/auth-guard";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { Header } from "@/components/layout/header";
import { useUIStore } from "@/stores/ui-store";
import { cn } from "@/lib/utils";

export default function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const setSidebarOpen = useUIStore((state) => state.setSidebarOpen);
  const closeNav = () => setSidebarOpen(false);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return undefined;
    const mq = window.matchMedia("(min-width: 1024px)");
    const onChange = () => {
      if (!mq.matches) setSidebarOpen(false);
    };
    onChange();
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, [setSidebarOpen]);

  return (
    <AuthGuard>
      <div className="flex min-h-dvh min-w-0 bg-background">
        {sidebarOpen ? (
          <button
            type="button"
            aria-label="ปิดเมนู"
            data-testid="nav-overlay"
            className="fixed inset-0 z-40 bg-navy/40 lg:hidden"
            onClick={closeNav}
          />
        ) : null}
        <div
          className={cn(
            "fixed inset-y-0 left-0 z-50 transform transition-transform duration-200 ease-out",
            "lg:translate-x-0",
            sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          )}
        >
          <SidebarNav onNavigate={closeNav} />
        </div>
        <div className="flex min-h-dvh min-w-0 flex-1 flex-col lg:ml-[255px]">
          <Header />
          <main className="min-w-0 flex-1 overflow-x-hidden p-3 sm:p-5 lg:p-[26px]">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
