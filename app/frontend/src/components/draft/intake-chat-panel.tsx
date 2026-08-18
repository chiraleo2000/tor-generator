"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ChatShell } from "@/components/chat/chat-shell";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";

interface CoverageRow {
  key: string;
  label: string;
  status: string;
  filled: boolean;
  fact_required: boolean;
}

export function IntakeChatPanel({
  projectId,
  phase,
  onAnalyzed,
  onReady,
}: Readonly<{
  projectId: string;
  phase: number;
  onAnalyzed: () => void;
  onReady: () => void;
}>) {
  const [coverage, setCoverage] = useState<CoverageRow[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);
  const [ready, setReady] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

  const refreshCoverage = useCallback(async () => {
    const response = await apiClient.get(`/projects/${projectId}/intake/coverage`);
    const payload = unwrapData<{
      coverage?: CoverageRow[];
      gap_questions?: string[];
      ready_to_compose?: boolean;
    }>(response);
    setCoverage(payload.coverage || []);
    setGaps(payload.gap_questions || []);
    setReady(Boolean(payload.ready_to_compose));
  }, [projectId]);

  useEffect(() => {
    refreshCoverage().catch(() => undefined);
  }, [refreshCoverage]);

  async function uploadFiles(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    setMessage(null);
    try {
      const body = new FormData();
      for (const file of Array.from(files)) {
        body.append("files", file);
      }
      await apiClient.post(`/projects/${projectId}/intake/upload`, body);
      await apiClient.post(`/projects/${projectId}/intake/analyze`);
      await refreshCoverage();
      onAnalyzed();
      setMessage("แกะเอกสารแล้ว — บอทจะถามส่วนที่ยังขาด");
    } catch {
      setMessage("อัปโหลดหรือวิเคราะห์ไม่สำเร็จ");
    } finally {
      setBusy(false);
    }
  }

  async function fillReference(slotKey: string) {
    setBusy(true);
    try {
      await apiClient.post(`/projects/${projectId}/intake/fill-reference`, {
        slot_key: slotKey,
      });
      await refreshCoverage();
    } finally {
      setBusy(false);
    }
  }

  async function confirmReady() {
    setBusy(true);
    try {
      await apiClient.post(`/projects/${projectId}/intake/confirm-ready`, {
        confirm: true,
      });
      onReady();
    } catch {
      setMessage("ยังไม่ครบช่องข้อเท็จจริงที่บังคับ หรือยังไม่ได้ยืนยัน");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4" data-testid="intake-chat-panel">
      <div className="gov-card">
        <h3 className="text-navy">
          {phase === 0 ? "Phase 0: อัปโหลดชุดเอกสาร" : "Phase 1: ถามส่วนขาดและยืนยันพร้อมร่าง"}
        </h3>
        <p className="mt-1 text-sm text-muted-foreground">
          ลากวางหลายไฟล์ได้ ไม่ต้องเลือกประเภทก่อน ต้นฉบับเก็บใน Mongo แล้วจัดเข้า s1–s13 / s4.1–s4.14
        </p>
        <label className="mt-3 flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed p-6 text-sm">
          <span>{busy ? "กำลังประมวลผล..." : "คลิกหรือวางไฟล์ PDF / Word / สแกน"}</span>
          <input
            type="file"
            multiple
            className="sr-only"
            data-testid="intake-upload"
            onChange={(event) => uploadFiles(event.target.files)}
          />
        </label>
        {message ? <p className="mt-2 text-sm">{message}</p> : null}
      </div>

      {coverage.length ? (
        <div className="gov-card overflow-x-auto">
          <h4 className="mb-2 font-bold text-navy">ตารางความครบถ้วน</h4>
          <table className="w-full text-left text-sm">
            <thead>
              <tr>
                <th>ช่อง</th>
                <th>สถานะ</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {coverage.map((row) => (
                <tr key={row.key} className="border-t">
                  <td className="py-1">
                    {row.key} {row.label}
                    {row.fact_required ? " *" : ""}
                  </td>
                  <td>{row.status}</td>
                  <td>
                    {row.status === "gap" ? (
                      <Button
                        type="button"
                        variant="outline"
                        className="h-7 text-xs"
                        onClick={() => fillReference(row.key)}
                      >
                        ดึงอ้างอิงกฎหมาย
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {gaps.length ? (
            <ul className="mt-2 list-disc pl-5 text-sm">
              {gaps.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          ) : null}
          <Button
            type="button"
            className="mt-3"
            data-testid="intake-confirm-ready"
            disabled={busy}
            onClick={confirmReady}
          >
            พร้อมร่าง TOR แล้ว
          </Button>
          {ready ? <p className="mt-2 text-sm text-green-800">ยืนยันพร้อมร่างแล้ว</p> : null}
        </div>
      ) : null}

      <ChatShell
        kind="draft_intake"
        projectId={projectId}
        streamPath={() => `${apiBase}/projects/${projectId}/intake/chat`}
        onReady={() => {
          refreshCoverage().catch(() => undefined);
        }}
      />
    </div>
  );
}
