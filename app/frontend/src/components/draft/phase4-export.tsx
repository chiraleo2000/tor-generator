"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export type ExportNumberingScheme = "none" | "numbered_consecutive";

export function Phase4Export({
  exporting,
  error,
  info,
  onExport,
}: Readonly<{
  exporting: boolean;
  error: string | null;
  info: string | null;
  onExport: (format: "docx" | "pdf", numberingScheme: ExportNumberingScheme) => Promise<void>;
}>) {
  const [numberedHeadings, setNumberedHeadings] = useState(false);
  const numberingScheme: ExportNumberingScheme = numberedHeadings
    ? "numbered_consecutive"
    : "none";
  return (
    <div className="gov-card mt-4 space-y-3" data-testid="phase4-export">
      <h3 className="text-navy">เผยแพร่เอกสาร</h3>
      <p className="text-sm text-muted-foreground">
        ส่งออก Word หรือ PDF ตามมาตรฐานราชการ (TH Sarabun New 16pt ระยะบรรทัด 1.0
        หัวข้อ 18pt ขอบบน/ล่าง 2.54 ซม. ซ้าย/ขวา 1.91 ซม. หัวข้อเป็นชื่อหมวดโดยไม่มีเลขนำหน้า
        วันที่ พ.ศ.) การอัปโหลดเข้าระบบ e-Bidding เป็นขั้นตอนของเจ้าหน้าที่นอกแอปนี้
      </p>
      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          data-testid="export-numbered-headings"
          checked={numberedHeadings}
          disabled={exporting}
          onChange={(event) => setNumberedHeadings(event.target.checked)}
        />
        <span>ใส่เลขหมวดต่อเนื่อง (๑. ๒. ๓. …)</span>
      </label>
      {exporting ? (
        <output className="flex items-center gap-2 rounded-md bg-blue-50 p-3 text-sm text-blue-800">
          <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-blue-600 border-t-transparent" />
          {info || "กำลังสร้างเอกสาร... กรุณารอสักครู่"}
        </output>
      ) : null}
      {error ? (
        <p className="text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      {!exporting && info ? <p className="text-sm text-brand-green">{info}</p> : null}
      <div className="flex gap-2">
        <Button
          disabled={exporting}
          data-testid="export-docx"
          onClick={() => onExport("docx", numberingScheme)}
        >
          ส่งออก Word
        </Button>
        <Button
          disabled={exporting}
          data-testid="export-pdf"
          onClick={() => onExport("pdf", numberingScheme)}
        >
          ส่งออก PDF
        </Button>
      </div>
    </div>
  );
}
