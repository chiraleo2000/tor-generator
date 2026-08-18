"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

export default function HomePage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, restoreSession } = useAuthStore();

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  useEffect(() => {
    if (isLoading) return;
    router.replace(isAuthenticated ? "/projects" : "/login");
  }, [isAuthenticated, isLoading, router]);

  return (
    <main
      className="flex min-h-screen items-center justify-center bg-gradient-to-br from-navy to-navy-dark"
      data-testid="landing-page"
    >
      <p className="text-white">กำลังเปิดระบบ...</p>
      <a href="/login" className="sr-only" data-testid="landing-login">
        เข้าสู่ระบบ
      </a>
      <a href="/register" className="sr-only" data-testid="landing-register">
        สมัครสมาชิก
      </a>
    </main>
  );
}
