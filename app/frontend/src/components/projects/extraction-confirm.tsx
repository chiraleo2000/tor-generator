"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { useWizardStore } from "@/stores/wizard-store";

interface ExtractionResult {
  proposed: Record<string, string>;
  fields: { location?: string; duration_days?: number };
  preview: { key: string; title: string; content: string }[];
  filename?: string;
}

export function ExtractionConfirm({
  projectId,
}: Readonly<{ projectId: string }>) {
  const setFormData = useWizardStore((s) => s.setFormData);
  const formData = useWizardStore((s) => s.formData);
  const [file, setFile] = useState<File | null>(null);
  const [proposed, setProposed] = useState<ExtractionResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function analyze() {
    if (!file) return;
    setBusy(true);
    setMessage(null);
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await apiClient.post(`/projects/${projectId}/extraction`, body);
      setProposed(unwrapData<ExtractionResult>(response));
    } catch {
      setMessage("อ่านไฟล์ไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function confirmApply() {
    if (!proposed) return;
    setBusy(true);
    try {
      await apiClient.post(`/projects/${projectId}/extraction/apply`, {
        sections: proposed.proposed,
        fields: proposed.fields,
        confirm: true,
      });
      const step1 = (formData[1] as Record<string, unknown>) || {};
      setFormData(1, {
        ...step1,
        location: proposed.fields.location || step1.location,
        duration_days: proposed.fields.duration_days || step1.duration_days,
      });
      if (proposed.proposed.s1) {
        setFormData(2, { description: proposed.proposed.s1 });
      }
      if (proposed.proposed.s2) {
        setFormData(3, {
          objectives: proposed.proposed.s2.split("\n").filter(Boolean),
        });
      }
      setFormData(7, { ...(formData[7] as object), ...proposed.proposed });
      setMessage("นำเข้าข้อมูลแล้ว — ตรวจสอบในวิซาร์ดก่อนส่งออก");
      setProposed(null);
    } catch {
      setMessage("ยืนยันไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-lg border p-4 space-y-3">
      <h3 className="font-medium">นำเข้า TOR อ้างอิง (Phase 0)</h3>
      <p className="text-sm text-muted-foreground">
        อัปโหลดไฟล์ DOCX/PDF แล้วระบบจะเสนอการจับคู่ไปยัง s1–s4 / สถานที่ /
        ระยะเวลา — ต้องยืนยันก่อนเขียนทับ
      </p>
      <input
        type="file"
        accept=".pdf,.docx,.txt"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <div className="flex gap-2">
        <Button type="button" variant="outline" onClick={analyze} disabled={!file || busy}>
          วิเคราะห์ไฟล์
        </Button>
        {proposed && (
          <Button type="button" onClick={confirmApply} disabled={busy}>
            ยืนยันนำเข้า
          </Button>
        )}
      </div>
      {message && <p className="text-sm">{message}</p>}
      {proposed && (
        <div className="max-h-64 overflow-y-auto space-y-2 text-sm">
          {proposed.preview.map((item) => (
            <div key={item.key} className="border rounded p-2">
              <p className="font-medium">
                {item.key} {item.title}
              </p>
              <pre className="whitespace-pre-wrap text-muted-foreground font-sans">
                {item.content.slice(0, 400)}
              </pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
