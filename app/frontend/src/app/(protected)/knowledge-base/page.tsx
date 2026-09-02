"use client";

import Link from "next/link";
import {
  ChevronDown,
  Download,
  LoaderCircle,
  MessageSquare,
  RefreshCw,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { UploadArea } from "@/components/brand/upload-area";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import {
  KB_CATEGORIES,
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
  uploaded_at?: string;
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

async function downloadFile(path: string, fileName: string) {
  const response = await apiClient.get(path, {
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
  const [type, setType] = useState("law");
  const [openGroup, setOpenGroup] = useState<string>("");
  const [openCat, setOpenCat] = useState<string>("");
  const [openReadyCategory, setOpenReadyCategory] = useState<string>("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const load = useCallback(async () => {
    const response = await apiClient.get("/knowledge-base/catalog");
    setCatalog(unwrapData<CatalogPayload>(response));
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    load().catch((err: unknown) =>
      setError(apiErrorMessage(err, "โหลดคลังความรู้ไม่สำเร็จ"))
    );
  }, [load]);

  const groups = catalog.groups || [];
  const visibleDocs = uniqueById([
    ...groups.flatMap((group) => group.items),
    ...(catalog.userFiles || []),
  ]);
  const processingDocs = visibleDocs.filter((doc) =>
    ["pending", "processing"].includes(doc.processing_status || "")
  );

  useEffect(() => {
    if (processingDocs.length === 0) return;
    const timer = window.setInterval(() => {
      load().catch(() => {
        /* keep the last known status if a polling request fails */
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [load, processingDocs.length]);

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
          : "อัปโหลดเฉพาะบัญชีของคุณแล้ว — กำลังอ่านโครงสร้างเอกสาร"
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

  async function removeCentral(documentId: string, fileName: string) {
    if (
      !window.confirm(
        `ลบเอกสาร «${fileName}»? ระบบจะลบทั้งไฟล์ต้นฉบับและข้อมูล PageIndex และย้อนกลับไม่ได้`
      )
    ) {
      return;
    }
    setError(null);
    setMessage(null);
    try {
      await apiClient.delete(`/knowledge-base/${documentId}`);
      setMessage(`ลบ «${fileName}» ออกจากคลังส่วนกลางแล้ว`);
      await load();
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ลบเอกสารไม่สำเร็จ"));
    }
  }

  async function downloadMine(documentId: string, fileName: string) {
    setError(null);
    try {
      await downloadFile(`/knowledge-base/mine/${documentId}/file`, fileName);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ดาวน์โหลดไม่สำเร็จ"));
    }
  }

  async function downloadCentral(documentId: string, fileName: string) {
    setError(null);
    try {
      await downloadFile(`/knowledge-base/${documentId}/file`, fileName);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "ดาวน์โหลดไม่สำเร็จ"));
    }
  }

  const raw = catalog.raw || {};
  const centralGroups = groups.filter((group) => group.mandatory);
  const mineDocs = uniqueById([
    ...groups.flatMap((group) => (group.mandatory ? [] : group.items)),
    ...(catalog.userFiles || []),
  ]);
  const readyDocs = visibleDocs.filter(
    (doc) =>
      doc.processing_status === "completed" ||
      (!doc.processing_status && doc.chunk_count > 0)
  );
  const readyByCategory = new Map<string, CatalogFile[]>();
  for (const doc of readyDocs) {
    const category = doc.category || "other";
    const rows = readyByCategory.get(category) || [];
    rows.push(doc);
    readyByCategory.set(category, rows);
  }
  const readyCategoryOrder = [
    ...KB_CATEGORIES.map((item) => item.id).filter((id) => readyByCategory.has(id)),
    ...Array.from(readyByCategory.keys()).filter(
      (id) => !KB_CATEGORIES.some((item) => item.id === id)
    ),
  ];

  return (
    <div data-testid="knowledge-base-page">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-extrabold text-navy">ฐานความรู้</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            อัปโหลดเอกสาร รอดูสถานะ PageIndex แล้วนำเอกสารที่พร้อมไปถาม-ตอบหรือสร้าง TOR
          </p>
        </div>
        <Button asChild>
          <Link href="/chat" data-testid="kb-open-chat">
            <MessageSquare className="mr-2 h-4 w-4" />
            ถามเอกสารในคลัง
          </Link>
        </Button>
      </div>

      {processingDocs.length > 0 ? (
        <div
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-amber-50 px-4 py-3 text-amber-950"
          role="status"
          aria-live="polite"
          data-testid="kb-processing-summary"
        >
          <div className="flex items-start gap-2.5">
            <LoaderCircle className="mt-0.5 h-4 w-4 shrink-0 animate-spin motion-reduce:animate-none" />
            <div>
              <p className="text-sm font-bold">
                PageIndex กำลังประมวลผล {processingDocs.length} ไฟล์
              </p>
              <p className="mt-0.5 text-xs text-amber-900">
                ไฟล์หลายหน้าอาจใช้เวลาหลายนาที หน้านี้ตรวจสถานะใหม่อัตโนมัติทุก 5 วินาที
                {lastUpdated
                  ? ` · อัปเดตล่าสุด ${lastUpdated.toLocaleTimeString("th-TH")}`
                  : ""}
              </p>
            </div>
          </div>
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={refreshing}
            onClick={async () => {
              setRefreshing(true);
              try {
                await load();
              } finally {
                setRefreshing(false);
              }
            }}
          >
            <RefreshCw
              className={cn(
                "mr-1.5 h-3.5 w-3.5",
                refreshing && "animate-spin motion-reduce:animate-none"
              )}
            />
            ตรวจสถานะตอนนี้
          </Button>
        </div>
      ) : null}

      <div className="gov-card mb-5">
        <h2 className="mb-3 text-[16.5px] font-bold text-navy">
          {isAdmin ? "อัปโหลดเอกสารเข้าคลังความรู้ส่วนกลาง" : "อัปโหลดเอกสารของฉัน"}
        </h2>
        <p className="mb-3 text-[12.5px] text-muted-foreground">
          {isAdmin
            ? "ไฟล์ที่อัปโหลดที่นี่เป็นคลังบังคับ/ส่วนกลาง เห็นได้ทุกบัญชี — ไม่มีการแชร์เอกสารส่วนตัวข้ามผู้ใช้"
            : "ระบบอ่านสารบัญ หัวข้อ และเนื้อหาเพื่อค้นหาตามบริบท เฉพาะบัญชีของคุณเท่านั้น"}
        </p>
        <div className="mb-3.5 flex flex-wrap gap-2">
          {KB_CATEGORIES.map((item) => (
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
          accept=".pdf,.docx,.txt"
          label="ลากไฟล์วาง หรือคลิกเพื่อเลือกไฟล์"
          hint="รองรับ PDF, Word และ TXT — ระบบอ่านโครงสร้าง หัวข้อ และเนื้อหาของเอกสาร"
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
        <h2 className="text-[16.5px] text-navy">เอกสารที่ผู้ใช้อัปโหลด (เฉพาะบัญชีนี้)</h2>
        <span
          className="rounded-full bg-blue-50 px-2.5 py-0.5 text-[11.5px] font-bold text-blue-800"
          data-testid="kb-mine-count"
        >
          {mineDocs.length} ไฟล์
        </span>
      </div>
      {mineDocs.length === 0 ? (
        <p className="mb-6 text-sm text-muted-foreground">ยังไม่มีเอกสารของฉัน — อัปโหลดด้านบนหรือแนบจากถาม-ตอบ</p>
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
              onClick={() => removeMine(doc.id, doc.name)}
            >
              ลบ
            </Button>
          </span>
        </div>
      ))}

      <div className="mb-3 mt-6 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">คลังกฎหมาย/ระเบียบตามกลุ่ม</h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11.5px] font-bold">
          {catalog.totals?.files || 0} ไฟล์
        </span>
      </div>
      {centralGroups.length > 0
        ? centralGroups.map((group) => (
            <div key={group.key} className="mb-2.5 overflow-hidden rounded-[10px] bg-white shadow-sm">
              <button
                type="button"
                className="flex w-full items-center justify-between px-4 py-3"
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
                      className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-[12.5px]"
                      data-testid={`kb-central-row-${doc.id}`}
                    >
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-medium text-navy">{doc.name}</span>
                          {doc.processing_status ? (
                            <span
                              className={cn(
                                "rounded-full px-2 py-0.5 text-[11px]",
                                kbProcessingBadgeClass(doc.processing_status)
                              )}
                              title={doc.error_message || undefined}
                              data-testid={`kb-central-status-${doc.id}`}
                            >
                              {kbProcessingLabel(doc.processing_status)}
                            </span>
                          ) : null}
                        </div>
                        {doc.processing_status === "completed" && doc.chunk_count > 0 ? (
                          <p className="mt-1 text-xs text-muted-foreground">
                            PageIndex อ่านได้ {doc.chunk_count} หัวข้อ
                          </p>
                        ) : null}
                        {doc.error_message ? (
                          <p className="mt-1 text-xs text-destructive">{doc.error_message}</p>
                        ) : null}
                      </div>
                      {isAdmin ? (
                        <div className="flex items-center gap-2">
                          <Button
                            type="button"
                            size="sm"
                            variant="outline"
                            data-testid={`download-central-${doc.id}`}
                            onClick={() => {
                              downloadCentral(doc.id, doc.name).catch(() => undefined);
                            }}
                          >
                            <Download className="mr-1 h-3.5 w-3.5" />
                            ดาวน์โหลด
                          </Button>
                          <Button
                            type="button"
                            size="sm"
                            variant="destructive"
                            data-testid={`delete-central-${doc.id}`}
                            onClick={() => removeCentral(doc.id, doc.name)}
                          >
                            ลบ
                          </Button>
                        </div>
                      ) : (
                        <span className="text-xs text-muted-foreground">
                          เอกสารส่วนกลาง · จัดการโดยผู้ดูแลระบบ
                        </span>
                      )}
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
                <span className="font-semibold text-navy">{kbCategoryLabel(category)}</span>
              </button>
              {openCat === category
                ? items.map((doc) => (
                    <div
                      key={doc.id}
                      className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3 text-[12.5px]"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span>{doc.name}</span>
                        {doc.processing_status ? (
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-[11px]",
                              kbProcessingBadgeClass(doc.processing_status)
                            )}
                          >
                            {kbProcessingLabel(doc.processing_status)}
                          </span>
                        ) : null}
                      </div>
                      {isAdmin ? (
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          onClick={() => removeCentral(doc.id, doc.name)}
                        >
                          ลบ
                        </Button>
                      ) : null}
                    </div>
                  ))
                : null}
            </div>
          ))}

      <div className="mb-3 mt-6 flex items-center gap-2">
        <h2 className="text-[16.5px] text-navy">ฐานความรู้ที่พร้อมค้นหาด้วย PageIndex</h2>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-[11.5px] font-bold">
          {readyDocs.length} ไฟล์
        </span>
      </div>
      <p className="mb-3 text-sm text-muted-foreground">
        กดแต่ละหมวดเพื่อดูว่าเอกสารใดพร้อมนำไปถาม-ตอบและสร้าง TOR แล้ว
      </p>
      {readyCategoryOrder.length === 0 ? (
        <p className="rounded-lg bg-white px-4 py-3 text-sm text-muted-foreground shadow-sm">
          ยังไม่มีเอกสารที่ประมวลผลเสร็จ
        </p>
      ) : null}
      {readyCategoryOrder.map((category) => {
        const items = readyByCategory.get(category) || [];
        const expanded = openReadyCategory === category;
        const contentId = `kb-ready-content-${category}`;
        return (
          <div
            key={category}
            className="mb-2.5 overflow-hidden rounded-[10px] bg-white shadow-sm"
          >
            <button
              type="button"
              className="flex w-full items-center justify-between gap-4 px-4 py-3 text-left hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring"
              aria-expanded={expanded}
              aria-controls={contentId}
              data-testid={`kb-ready-toggle-${category}`}
              onClick={() => setOpenReadyCategory(expanded ? "" : category)}
            >
              <span>
                <span className="block font-semibold text-navy">
                  {kbCategoryLabel(category)}
                </span>
                <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                  {expanded ? "กดเพื่อซ่อนรายชื่อ" : "กดเพื่อดูรายชื่อเอกสาร"}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2 text-[12px] text-muted-foreground">
                {items.length} ไฟล์
                <ChevronDown
                  aria-hidden="true"
                  className={cn(
                    "h-4 w-4 transition-transform duration-200 motion-reduce:transition-none",
                    expanded && "rotate-180"
                  )}
                />
              </span>
            </button>
            {expanded ? (
              <div id={contentId} data-testid={`kb-ready-list-${category}`}>
                {items.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex flex-wrap items-center justify-between gap-3 border-t px-4 py-3"
                    data-testid={`kb-ready-document-${doc.id}`}
                  >
                    <div className="min-w-0 flex-1">
                      <p className="break-words text-sm font-medium text-navy">{doc.name}</p>
                      <p className="mt-1 text-xs text-muted-foreground">
                        {doc.mandatory ? "เอกสารส่วนกลาง" : "เอกสารของฉัน"}
                        {doc.chunk_count > 0
                          ? ` · PageIndex อ่านได้ ${doc.chunk_count} หัวข้อ`
                          : ""}
                      </p>
                    </div>
                    <span className="rounded-full bg-green-50 px-2.5 py-1 text-[11px] font-bold text-green-800">
                      พร้อมใช้งาน
                    </span>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
