"use client";

import { AuthGuard } from "@/components/auth/auth-guard";
import { SidebarNav } from "@/components/layout/sidebar-nav";
import { Header } from "@/components/layout/header";

export default function ProtectedLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background">
        <SidebarNav />
        <div className="ml-[255px] flex min-h-screen min-w-0 flex-1 flex-col">
          <Header />
          <main className="flex-1 overflow-x-hidden p-[26px]">{children}</main>
        </div>
      </div>
    </AuthGuard>
  );
}
