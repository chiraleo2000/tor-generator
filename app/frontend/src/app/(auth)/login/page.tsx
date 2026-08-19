"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ClipboardList } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function LoginPage() {
  const router = useRouter();
  const login = useAuthStore((s) => s.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!email.trim()) {
      setError("กรุณากรอกอีเมล");
      return;
    }
    if (!password) {
      setError("กรุณากรอกรหัสผ่าน");
      return;
    }
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/projects");
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as {
          response?: { data?: { error?: { message?: string } } };
        };
        setError(axiosErr.response?.data?.error?.message || "อีเมลหรือรหัสผ่านไม่ถูกต้อง");
      } else {
        setError("เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-gradient-to-br from-navy to-crimson">
        <ClipboardList className="h-7 w-7 text-white" />
      </div>
      <h1 className="mb-1.5 text-center text-2xl font-extrabold text-navy">เข้าสู่ระบบ</h1>
      <p className="mb-6 text-center text-[13px] text-muted-foreground">
        TOR Generator — ระบบร่างและตรวจสอบ TOR ภาครัฐ
      </p>
      <form onSubmit={handleSubmit} className="space-y-4" data-testid="login-form">
        {error ? (
          <div
            className="rounded-lg bg-red-50 p-3 text-[12.5px] text-red-700"
            data-testid="login-error"
            role="alert"
          >
            {error}
          </div>
        ) : null}
        <div className="space-y-2">
          <Label htmlFor="email" className="font-bold text-navy">
            อีเมล
          </Label>
          <Input
            id="email"
            type="email"
            placeholder="you@ministry.go.th"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            disabled={submitting}
            data-testid="login-email"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password" className="font-bold text-navy">
            รหัสผ่าน
          </Label>
          <Input
            id="password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            disabled={submitting}
            data-testid="login-password"
          />
        </div>
        <Button type="submit" className="w-full font-bold" disabled={submitting} data-testid="login-submit">
          {submitting ? "กำลังเข้าสู่ระบบ..." : "เข้าสู่ระบบ"}
        </Button>
      </form>
      <div className="mt-4 rounded-lg border border-dashed bg-gray-50 p-2.5 text-center text-[11.5px] text-muted-foreground">
        บัญชีทดลอง: officer@example.go.th / Passw0rd!
      </div>
      <p className="mt-4 text-center text-[13px] text-muted-foreground">
        ยังไม่มีบัญชี?{" "}
        <Link href="/register" className="font-bold text-navy">
          สมัครสมาชิก
        </Link>
      </p>
    </div>
  );
}
