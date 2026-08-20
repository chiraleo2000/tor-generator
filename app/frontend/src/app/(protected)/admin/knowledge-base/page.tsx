"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";

interface KBDoc {
  id: string;
  name: string;
  category: string;
  file_type: string;
  processing_status: string;
  chunk_count: number;
  error_message?: string | null;
  uploaded_at: string;
}

export default function AdminKnowledgeBasePage() {
  const [items, setItems] = useState<KBDoc[]>([]);
  const [category, setCategory] = useState("guideline");
  const [dragging, setDragging] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const response = await apiClient.get("/knowledge-base");
    const payload = unwrapData<{ items?: KBDoc[] }>(response);
    setItems(payload.items || []);
  }, []);

  useEffect(() => {
    load().catch((err: unknown) =>
      setError(apiErrorMessage(err, "โหลดฐานความรู้ไม่สำเร็จ"))
    );
  }, [load]);

  async function uploadFiles(files: FileList | File[]) {
    setMessage(null);
    for (const file of Array.from(files)) {
      const body = new FormData();
      body.append("file", file);
      body.append("category", category);
      body.append("name", file.name);
      await apiClient.post("/knowledge-base/upload", body);
    }
    setMessage("อัปโหลดแล้ว — กำลังประมวลผล");
    await load();
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6" data-testid="admin-kb-page">
      <h1 className="text-2xl font-extrabold text-navy">ฐานความรู้</h1>
      {error ? (
        <p className="text-sm rounded-md border border-destructive/50 text-destructive p-3" role="alert">
          {error}
        </p>
      ) : null}
      <div className="gov-card space-y-4">
        <div className="flex items-center gap-3">
        <Select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          options={[
            { value: "law", label: "กฎหมาย" },
            { value: "regulation", label: "กฎกระทรวง" },
            { value: "guideline", label: "ระเบียบ/หนังสือ" },
            { value: "manual", label: "คู่มือ" },
            { value: "example_tor", label: "ตัวอย่าง TOR" },
          ]}
        />
        <Button
          type="button"
          variant="outline"
          onClick={async () => {
            setError(null);
            try {
              await apiClient.post("/knowledge-base/batch-ingest");
              setMessage("เริ่มประมวลผลทั้งคลัง");
              await load();
            } catch (err: unknown) {
              setError(apiErrorMessage(err, "ประมวลผลคลังไม่สำเร็จ"));
            }
          }}
        >
          ประมวลผลใหม่ทั้งชุด
        </Button>
        </div>
      <label
        className={`block border-2 border-dashed rounded-lg p-10 text-center ${
          dragging ? "border-primary bg-primary/5" : ""
        }`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          if (e.dataTransfer.files.length) {
            uploadFiles(e.dataTransfer.files).catch((err: unknown) =>
              setError(apiErrorMessage(err, "อัปโหลดไม่สำเร็จ"))
            );
          }
        }}
      >
        <span className="block">ลากไฟล์ PDF / DOCX / TXT มาวางที่นี่ หรือคลิกเพื่อเลือก</span>
        <span className="sr-only">เลือกไฟล์</span>
        <input
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.docx,.txt"
          onChange={(e) => {
            if (e.target.files) {
              uploadFiles(e.target.files).catch((err: unknown) =>
                setError(apiErrorMessage(err, "อัปโหลดไม่สำเร็จ"))
              );
            }
          }}
        />
      </label>
      {message && <p className="text-sm">{message}</p>}
      </div>
      <div className="space-y-2">
        {items.map((doc) => (
          <div
            key={doc.id}
            className="gov-card flex items-center justify-between"
          >
            <div>
              <p className="font-medium">{doc.name}</p>
              <p className="text-xs text-muted-foreground">
                {doc.category} · {doc.file_type} · {doc.processing_status} ·{" "}
                {doc.chunk_count} chunks
              </p>
              {doc.error_message && (
                <p className="text-xs text-destructive">{doc.error_message}</p>
              )}
            </div>
            <Button
              size="sm"
              variant="destructive"
              onClick={async () => {
                if (!window.confirm("ลบเอกสารนี้?")) return;
                setError(null);
                try {
                  await apiClient.delete(`/knowledge-base/${doc.id}`);
                  await load();
                } catch (err: unknown) {
                  setError(apiErrorMessage(err, "ลบเอกสารไม่สำเร็จ"));
                }
              }}
            >
              ลบ
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
