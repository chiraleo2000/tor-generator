"use client";

import { Download } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { UploadArea } from "@/components/brand/upload-area";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import {
  KB_BAR_CATEGORIES,
  kbCategoryLabel,
  kbProcessingBadgeClass,
  kbProcessingLabel,
  uniqueById,
} from "@/lib/kb-categories";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/utils";

interface CatalogFile {
  id: string;
  name: string;
  chunk_count: number;
  mandatory?: boolean;
  corpus_group?: string;
  category?: string;
  processing_status?: string;
  error_message?: string | null;
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

const CORPUS_GROUPS = [
  { key: "mandatory_handbook", label: "คู่มือแนวปฏิบัติ (บังคับ)" },
  { key: "mandatory_raw", label: "ข้อมูลดิบกฎหมาย/ระเบียบ (บังคับ)" },
] as const;

const KB_FILTERS = [{ id: "all", label: "ทั้งหมด" }, ...KB_BAR_CATEGORIES];

function inCategory(doc: CatalogFile, category: string): boolean {
  if (category === "all") return true;
  return (doc.category || "other") === category;
}

function corpusSource(
  metaKey: string,
  fromGroup: CatalogFile[],
  groups: CatalogGroup[],
  raw: Record<string, CatalogFile[]>
): CatalogFile[] {
  if (fromGroup.length > 0 || groups.length > 0) return fromGroup;
  if (metaKey !== "mandatory_raw") return [];
  return Object.entries(raw).flatMap(([category, items]) =>
    items.map((item) => ({ ...item, category: item.category || category }))
  );
}

async function downloadPrivateFile(documentId: string, fileName: string) {
  const response = await apiClient.get(`/knowledge-base/mine/${documentId}/file`, {
    responseType: "blob",
  });
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export default function KnowledgeBasePage() {
  const user = useAuthStore((s) => s.user);
  const isAdmin = user?.role === "admin";
  const [catalog, setCatalog] = useState<CatalogPayload>({});
  const [type, setType] = useState("all");
  const [openGroup, setOpenGroup] = useState<string>("");
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

  useEffect(() => {
    function refresh() {
      if (document.visibilityState !== "visible") return;
      load().catch(() => {
        /* remount/focus refresh is best-effort */
      });
    }
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => {
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", refresh);
    };
  }, [load]);

  async function upload(files: FileList) {
    setError(null);
    setMessage(null);
    try {
      await Array.from(files).reduce(async (previous, file) => {
        await previous;
        const body = new FormData();
        body.append("file", file);
        body.append("category", type === "all" ? "other" : type);
        body.append("name", file.name);
        const path = isAdmin ? "/knowledge-base/upload" : "/knowledge-base/mine";
        await apiClient.post(path, body);
      }, Promise.resolve());
      setMessage(
        isAdmin
          ? "อัปโหลดเข้าคลังส่วนกลางแล้ว — กำลังประมวลผล"
          : "อัปโหลดเฉพาะบัญชีของคุณแล้ว — กำลังประมวลผลเข้าคลัง"
      );
      await load();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "อัปโหลดไม่สำเร็จ"));
    }
  }

  async function removeMine(documentId: string, fileName: string) {
    if (!window.confirm(`ลบเอกสาร «${fileName}» ออกจากคลังของฉัน?`)) return;
    setError(null);
    setMessage(null);
    try {
      await apiClient.delete(`/knowledge-base/mine/${documentId}`);
      setMessage(`ลบ «${fileName}» แล้ว`);
      await load();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ลบเอกสารไม่สำเร็จ"));
    }
  }

  async function downloadMine(documentId: string, fileName: string) {
    setError(null);
    try {
      await downloadPrivateFile(documentId, fileName);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ดาวน์โหลดไม่สำเร็จ"));
    }
  }

  const raw = catalog.raw || {};
  const groups = catalog.groups || [];
  const allMine = uniqueById([
    ...groups.flatMap((group) => (group.mandatory ? [] : group.items)),
    ...(catalog.userFiles || []),
  ]);
  const mineDocs = allMine.filter((doc) => inCategory(doc, type));
  const corpusGroups = CORPUS_GROUPS.map((meta) => {
    const fromGroup = groups.find((group) => group.key === meta.key)?.items || [];
    const source = corpusSource(meta.key, fromGroup, groups, raw);
    return { ...meta, items: source.filter((doc) => inCategory(doc, type)) };
  });
  const centralCount = corpusGroups.reduce((sum, group) => sum + group.items.length, 0);

  return (
    <div data-testid="knowledge-base-page">
      <div className="gov-card mb-5">
        <h2 className="mb-3 text-[16.5px] font-bold text-navy">
          {isAdmin ? "อัปโหลดเอกสารเข้าคลังความรู้ส่วนกลาง" : "อัปโหลดเอกสารของฉัน"}
        </h2>
        <p className="mb-3 text-[12.5px] text-muted-foreground">
          {isAdmin
            ? "ไฟล์ที่อัปโหลดที่นี่เป็นคลังบังคับ/ส่วนกลาง เห็นได้ทุกบัญชี — เลือกประเภทจากแถบด้านบนก่อนอัปโหลด"
            : "ไฟล์ของคุณเข้าคลังเฉพาะบัญชีนี้ ไม่เผยแพร่ให้เจ้าหน้าที่อื่น — เลือกประเภทจากแถบด้านบนก่อนอัปโหลด"}
        </p>
        <div className="mb-3.5 flex flex-wrap gap-2" data-testid="kb-category-bar">
          {KB_FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              data-testid={`kb-category-${item.id}`}
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
          hint={
            type === "all"
              ? "รองรับ PDF, Word และรูปภาพ — เลือกทั้งหมดจะจัดเป็นข้อมูลอื่น ๆ"
              : "รองรับ PDF, Word และรูปภาพ — จัดเข้าประเภทที่เลือกบนแถบ"
          }
          onFiles={(files) => {
            void upload(files);
          }}
        />
        {error ? (
          <p className="mt-2 text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
        {message ? <p className="mt-2 text-sm text-navy">{message}</p> : null}
      </div>

      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">เอกสารที่ผู้ใช้อัปโหลด (เฉพาะบัญชีนี้)</h2>
        <span
          className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11.5px] font-bold text-blue-800"
          data-testid="kb-mine-count"
        >
          {mineDocs.length} ไฟล์
        </span>
      </div>
      {mineDocs.length === 0 ? (
        <p className="mb-6 text-sm text-muted-foreground">
          {allMine.length === 0
            ? "ยังไม่มีเอกสารของฉัน — อัปโหลดด้านบนหรือแนบจากถาม-ตอบ"
            : "ไม่มีเอกสารของฉันในประเภทนี้"}
        </p>
      ) : null}
      {mineDocs.map((doc) => (
        <div
          key={doc.id}
          className="mb-2 flex items-center justify-between gap-3 rounded-[10px] bg-white px-4 py-3 shadow-sm"
          data-testid={`kb-mine-row-${doc.id}`}
        >
          <span className="font-medium text-navy">
            {doc.name}
            <span className="ml-2 rounded-full bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-800">
              ส่วนตัว
            </span>
            {doc.category ? (
              <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-bold text-gray-700">
                {kbCategoryLabel(doc.category)}
              </span>
            ) : null}
            {doc.processing_status ? (
              <span
                className={cn(
                  "ml-2 rounded-full px-2 py-0.5 text-[11px]",
                  kbProcessingBadgeClass(doc.processing_status)
                )}
                title={
                  doc.processing_status === "failed"
                    ? doc.error_message || kbProcessingLabel(doc.processing_status)
                    : undefined
                }
                data-testid={`kb-mine-status-${doc.id}`}
              >
                {kbProcessingLabel(doc.processing_status)}
              </span>
            ) : null}
          </span>
          <span className="flex items-center gap-2 text-[12px] text-muted-foreground">
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid={`download-mine-${doc.id}`}
              onClick={() => {
                downloadMine(doc.id, doc.name).catch(() => {
                  /* downloadMine sets error */
                });
              }}
            >
              <Download className="mr-1 h-3.5 w-3.5" />
              ดาวน์โหลด
            </Button>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              data-testid={`delete-user-file-${doc.id}`}
              onClick={() => {
                void removeMine(doc.id, doc.name);
              }}
            >
              ลบ
            </Button>
          </span>
        </div>
      ))}

      <div className="mb-3 mt-6 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">คลังกฎหมาย/ระเบียบตามกลุ่ม</h2>
        <span
          className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11.5px] font-bold"
          data-testid="kb-central-count"
        >
          {centralCount} ไฟล์
        </span>
      </div>
      {corpusGroups.map((group) => (
        <div key={group.key} className="mb-2.5 overflow-hidden rounded-[10px] bg-white shadow-sm">
          <button
            type="button"
            className="flex w-full items-center justify-between px-4 py-3"
            data-testid={`kb-group-${group.key}`}
            onClick={() => setOpenGroup(openGroup === group.key ? "" : group.key)}
          >
            <span className="font-semibold text-navy">{group.label}</span>
            <span className="rounded-full bg-red-50 px-2 py-0.5 text-[11px] font-bold text-red-700">
              คลังกลาง · บังคับ
            </span>
          </button>
          {openGroup === group.key
            ? group.items.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between gap-3 border-t px-4 py-2 text-[12.5px]"
                >
                  <span>
                    {doc.name}
                    {doc.category ? (
                      <span className="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-[11px] font-bold text-gray-700">
                        {kbCategoryLabel(doc.category)}
                      </span>
                    ) : null}
                  </span>
                  <span className="text-muted-foreground">ลบไม่ได้</span>
                </div>
              ))
            : null}
          {openGroup === group.key && group.items.length === 0 ? (
            <p className="border-t px-4 py-2 text-[12.5px] text-muted-foreground">
              ไม่มีไฟล์ในประเภทนี้
            </p>
          ) : null}
        </div>
      ))}
    </div>
  );
}
