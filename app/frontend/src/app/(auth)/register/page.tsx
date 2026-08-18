"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import axios from "axios";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isPasswordValid, validatePassword } from "@/lib/password-rules";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:4000/api/v1";

export default function RegisterPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [organization, setOrganization] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPasswordRules, setShowPasswordRules] = useState(false);

  const passwordValidation = validatePassword(password);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    // Validate required fields
    if (!name.trim()) {
      setError("กรุณากรอกชื่อ-นามสกุล");
      return;
    }
    if (!email.trim()) {
      setError("กรุณากรอกอีเมล");
      return;
    }
    if (!password) {
      setError("กรุณากรอกรหัสผ่าน");
      return;
    }
    if (!isPasswordValid(passwordValidation)) {
      setError("รหัสผ่านไม่ตรงตามเงื่อนไขที่กำหนด");
      return;
    }
    if (password !== confirmPassword) {
      setError("รหัสผ่านยืนยันไม่ตรงกัน");
      return;
    }
    if (!organization.trim()) {
      setError("กรุณากรอกหน่วยงาน");
      return;
    }

    setIsLoading(true);
    try {
      await axios.post(`${API_URL}/auth/register`, {
        name: name.trim(),
        email: email.trim(),
        password,
        organization: organization.trim(),
      });
      router.push("/login?registered=true");
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { error?: { message?: string } } } };
        const message = axiosErr.response?.data?.error?.message;
        setError(message || "ไม่สามารถสมัครสมาชิกได้ กรุณาลองใหม่อีกครั้ง");
      } else {
        setError("เกิดข้อผิดพลาดในการเชื่อมต่อ กรุณาลองใหม่อีกครั้ง");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div>
      <h1 className="mb-1.5 text-center text-2xl font-extrabold text-navy">สมัครสมาชิก</h1>
      <p className="mb-6 text-center text-[13px] text-muted-foreground">
        TOR Generator — ระบบร่างและตรวจสอบ TOR ภาครัฐ
      </p>

      <form onSubmit={handleSubmit} className="space-y-4" data-testid="register-form">
        {error && (
          <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="name">ชื่อ-นามสกุล</Label>
          <Input
            id="name"
            type="text"
            placeholder="นายสมชาย ใจดี"
            value={name}
            onChange={(e) => setName(e.target.value)}
            autoComplete="name"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="reg-email">อีเมล</Label>
          <Input
            id="reg-email"
            type="email"
            placeholder="example@agency.go.th"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
            disabled={isLoading}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="reg-password">รหัสผ่าน</Label>
          <Input
            id="reg-password"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              setShowPasswordRules(true);
            }}
            onFocus={() => setShowPasswordRules(true)}
            autoComplete="new-password"
            disabled={isLoading}
          />
          {showPasswordRules && (
            <ul className="mt-2 space-y-1 text-xs">
              <li className={passwordValidation.minLength ? "text-green-600" : "text-muted-foreground"}>
                {passwordValidation.minLength ? "✓" : "○"} อย่างน้อย 8 ตัวอักษร
              </li>
              <li className={passwordValidation.hasUppercase ? "text-green-600" : "text-muted-foreground"}>
                {passwordValidation.hasUppercase ? "✓" : "○"} มีตัวพิมพ์ใหญ่อย่างน้อย 1 ตัว (A-Z)
              </li>
              <li className={passwordValidation.hasLowercase ? "text-green-600" : "text-muted-foreground"}>
                {passwordValidation.hasLowercase ? "✓" : "○"} มีตัวพิมพ์เล็กอย่างน้อย 1 ตัว (a-z)
              </li>
              <li className={passwordValidation.hasDigit ? "text-green-600" : "text-muted-foreground"}>
                {passwordValidation.hasDigit ? "✓" : "○"} มีตัวเลขอย่างน้อย 1 ตัว (0-9)
              </li>
              <li className={passwordValidation.hasSpecial ? "text-green-600" : "text-muted-foreground"}>
                {passwordValidation.hasSpecial ? "✓" : "○"} มีอักขระพิเศษอย่างน้อย 1 ตัว (!@#$%...)
              </li>
            </ul>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="confirm-password">ยืนยันรหัสผ่าน</Label>
          <Input
            id="confirm-password"
            type="password"
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            disabled={isLoading}
          />
          {confirmPassword && password !== confirmPassword && (
            <p className="text-xs text-destructive">รหัสผ่านยืนยันไม่ตรงกัน</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="organization">หน่วยงาน</Label>
          <Input
            id="organization"
            type="text"
            placeholder="กรมบัญชีกลาง"
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
            disabled={isLoading}
          />
        </div>

        <Button type="submit" className="w-full" disabled={isLoading}>
          {isLoading ? "กำลังสมัครสมาชิก..." : "สมัครสมาชิก"}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted-foreground">
        มีบัญชีอยู่แล้ว?{" "}
        <Link
          href="/login"
          className="font-medium text-primary hover:underline"
        >
          เข้าสู่ระบบ
        </Link>
      </p>
    </div>
  );
}
