"use client";

import { useCallback, useEffect, useState } from "react";
import { UploadArea } from "@/components/brand/upload-area";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

interface CatalogFile {
  id: string;
  name: string;
  chunk_count: number;
  mandatory?: boolean;
  corpus_group?: string;
}

interface CatalogGroup {
  key: string;
  label: string;
  mandatory: boolean;
  files: number;
  chunks: number;
  items: CatalogFile[];
}

interface CatalogPayload {
  raw?: Record<string, CatalogFile[]>;
  chunked?: { key: string; name: string; files: number; chunks: number }[];
  groups?: CatalogGroup[];
  userFiles?: CatalogFile[];
  totals?: { files: number; chunks: number };
}

const TYPES = [
  { id: "law", label: "กฎหมาย/ระเบียบกลาง" },
  { id: "guideline", label: "ประกาศราคากลาง / ระเบียบ" },
  { id: "example_tor", label: "ร่างเอกสารประกวดราคา" },
  { id: "manual", label: "ความต้องการ/คู่มือ" },
  { id: "regulation", label: "กฎกระทรวง" },
];

export default function KnowledgeBasePage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";
  const [catalog, setCatalog] = useState<CatalogPayload>({});
  const [type, setType] = useState("law");
  const [openGroup, setOpenGroup] = useState<string>("");
  const [openCat, setOpenCat] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const response = await apiClient.get("/knowledge-base/catalog");
    setCatalog(unwrapData<CatalogPayload>(response));
  }, []);

  useEffect(() => {
    load().catch((err: unknown) =>
      setError(apiErrorMessage(err, "โหลดคลังความรู้ไม่สำเร็จ"))
    );
  }, [load]);

  async function upload(files: FileList) {
    setError(null);
    setMessage(null);
    try {
      for (const file of Array.from(files)) {
        const body = new FormData();
        body.append("file", file);
        body.append("category", type);
        body.append("name", file.name);
        if (isAdmin) {
          await apiClient.post("/knowledge-base/upload", body);
        } else {
          await apiClient.post("/knowledge-base/mine", body);
        }
      }
      setMessage(
        isAdmin
          ? "อัปโหลดเข้าคลังส่วนกลางแล้ว — กำลังประมวลผล"
          : "อัปโหลดเฉพาะบัญชีของคุณแล้ว — กำลังแบ่ง chunk และฝังเข้า RAG"
      );
      await load();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "อัปโหลดไม่สำเร็จ"));
    }
  }

  const raw = catalog.raw || {};
  const chunked = catalog.chunked || [];
  const groups = catalog.groups || [];

  return (
    <div data-testid="knowledge-base-page">
      <div className="gov-card mb-5">
        <h2 className="mb-3 text-[16.5px] font-bold text-navy">
          {isAdmin ? "อัปโหลดเอกสารเข้าคลังความรู้ส่วนกลาง" : "อัปโหลดเอกสารของฉัน"}
        </h2>
        <p className="mb-3 text-[12.5px] text-muted-foreground">
          {isAdmin
            ? "ไฟล์ที่อัปโหลดที่นี่เป็นคลังบังคับ/ส่วนกลาง เห็นได้ทุกบัญชี"
            : "ไฟล์ของคุณถูก chunk และฝังเข้า RAG เฉพาะบัญชีนี้ ไม่เผยแพร่ให้เจ้าหน้าที่อื่น"}
        </p>
        <div className="mb-3.5 flex flex-wrap gap-2">
          {TYPES.map((item) => (
            <button
              key={item.id}
              type="button"
              className={cn(
                "rounded-full border px-3.5 py-2 text-[12.5px] font-bold",
                type === item.id
                  ? "border-navy bg-navy text-white"
                  : "border-gray-300 bg-white text-gray-700"
              )}
              onClick={() => setType(item.id)}
            >
              {item.label}
            </button>
          ))}
        </div>
        <UploadArea
          label="ลากไฟล์วาง หรือคลิกเพื่อเลือกไฟล์"
          hint="รองรับ PDF, Word — ระบบแบ่ง chunk และฝังเข้า Vector Store"
          onFiles={upload}
        />
        {error ? (
          <p className="mt-2 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        {message ? <p className="mt-2 text-sm text-navy">{message}</p> : null}
      </div>

      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">คลังกฎหมาย/ระเบียบตามกลุ่ม</h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11.5px] font-bold">
          {catalog.totals?.files || 0} ไฟล์
        </span>
      </div>
      {groups.length > 0
        ? groups.map((group) => (
            <div key={group.key} className="mb-2.5 overflow-hidden rounded-[10px] bg-white shadow-sm">
              <button
                type="button"
                className="flex w-full items-center justify-between px-4 py-3"
                onClick={() => setOpenGroup(openGroup === group.key ? "" : group.key)}
              >
                <span className="font-semibold text-navy">{group.label}</span>
                {group.mandatory ? (
                  <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-700">
                    บังคับ
                  </span>
                ) : (
                  <span className="rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-800">
                    ของฉัน
                  </span>
                )}
              </button>
              {openGroup === group.key
                ? group.items.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex justify-between border-t px-4 py-2 text-[12.5px]"
                    >
                      <span>{doc.name}</span>
                      <span className="text-muted-foreground">{doc.chunk_count} chunks</span>
                    </div>
                  ))
                : null}
            </div>
          ))
        : Object.entries(raw).map(([category, items]) => (
            <div key={category} className="mb-2.5 overflow-hidden rounded-[10px] bg-white shadow-sm">
              <button
                type="button"
                className="flex w-full items-center justify-between px-4 py-3"
                onClick={() => setOpenCat(openCat === category ? "" : category)}
              >
                <span className="font-semibold text-navy">{category}</span>
              </button>
              {openCat === category
                ? items.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex justify-between border-t px-4 py-2 text-[12.5px]"
                    >
                      <span>{doc.name}</span>
                      <span className="text-muted-foreground">{doc.chunk_count} chunks</span>
                    </div>
                  ))
                : null}
            </div>
          ))}

      <div className="mb-3 mt-6 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">คลังความรู้ที่ผ่านการ Chunk เข้า RAG</h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11.5px] font-bold">
          {catalog.totals?.chunks || 0} chunks
        </span>
      </div>
      {chunked.map((row) => (
        <div key={row.key} className="mb-2 flex justify-between rounded-[10px] bg-white px-4 py-3 shadow-sm">
          <span className="font-medium text-navy">{row.name}</span>
          <span className="text-[12px] text-muted-foreground">
            {row.files} ไฟล์ · {row.chunks} chunks
          </span>
        </div>
      ))}

      <div className="mb-3 mt-6 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">เอกสารที่ผู้ใช้อัปโหลด (เฉพาะบัญชีนี้)</h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11.5px] font-bold">
          {(catalog.userFiles || []).length} ไฟล์
        </span>
      </div>
      {(catalog.userFiles || []).map((doc) => (
        <div key={doc.id} className="mb-2 flex justify-between rounded-[10px] bg-white px-4 py-3 shadow-sm">
          <span className="font-medium text-navy">{doc.name}</span>
          <span className="text-[12px] text-muted-foreground">{doc.chunk_count} chunks</span>
        </div>
      ))}
    </div>
  );
}
