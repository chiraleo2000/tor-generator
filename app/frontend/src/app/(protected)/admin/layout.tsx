"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/stores/auth-store";

export default function AdminLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (user && user.role !== "admin") {
      router.replace("/projects");
    }
  }, [user, router]);

  if (user && user.role !== "admin") {
    return <p className="text-sm text-muted-foreground">เฉพาะผู้ดูแลระบบ</p>;
  }
  return <>{children}</>;
}
