"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";

interface AdminUser {
  id: string;
  name: string;
  email: string;
  organization: string;
  role: string;
  disabled: boolean;
}

export default function AdminUsersPage() {
  const [items, setItems] = useState<AdminUser[]>([]);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("Passw0rd!");
  const [organization, setOrganization] = useState("");
  const [role, setRole] = useState("officer");

  async function load() {
    const response = await apiClient.get("/admin/users");
    const payload = unwrapData<{ items?: AdminUser[] }>(response);
    setItems(payload.items || []);
  }

  useEffect(() => {
    load().catch(() => setItems([]));
  }, []);

  return (
    <div className="max-w-5xl mx-auto space-y-6" data-testid="admin-users-page">
      <h1 className="text-2xl font-extrabold text-navy">ผู้ใช้ระบบ</h1>
      <div className="gov-card grid sm:grid-cols-2 gap-3">
        <div>
          <Label>ชื่อ</Label>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <div>
          <Label>อีเมล</Label>
          <Input value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <Label>รหัสผ่าน</Label>
          <Input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>
        <div>
          <Label>หน่วยงาน</Label>
          <Input
            value={organization}
            onChange={(e) => setOrganization(e.target.value)}
          />
        </div>
        <div>
          <Label>บทบาท</Label>
          <Select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            options={[
              { value: "officer", label: "เจ้าหน้าที่" },
              { value: "reviewer", label: "ผู้ตรวจสอบ" },
              { value: "admin", label: "ผู้ดูแลระบบ" },
            ]}
          />
        </div>
        <div className="flex items-end">
          <Button
            onClick={async () => {
              await apiClient.post("/admin/users", {
                name,
                email,
                password,
                organization,
                role,
              });
              setName("");
              setEmail("");
              await load();
            }}
          >
            สร้างผู้ใช้
          </Button>
        </div>
      </div>
      <div className="space-y-2">
        {items.map((user) => (
          <div
            key={user.id}
            className="gov-card flex items-center justify-between"
          >
            <div>
              <p className="font-medium">
                {user.name} {user.disabled ? "(ปิดใช้งาน)" : ""}
              </p>
              <p className="text-xs text-muted-foreground">
                {user.email} · {user.role} · {user.organization}
              </p>
            </div>
            <div className="flex gap-2">
              <Select
                value={user.role}
                onChange={async (e) => {
                  await apiClient.put(`/admin/users/${user.id}`, {
                    role: e.target.value,
                  });
                  await load();
                }}
                options={[
                  { value: "officer", label: "เจ้าหน้าที่" },
                  { value: "reviewer", label: "ผู้ตรวจสอบ" },
                  { value: "admin", label: "ผู้ดูแลระบบ" },
                ]}
              />
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  await apiClient.put(`/admin/users/${user.id}`, {
                    disabled: !user.disabled,
                  });
                  await load();
                }}
              >
                {user.disabled ? "เปิดใช้" : "ปิดใช้"}
              </Button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
