"use client";

import { Button } from "@/components/ui/button";

export function Phase4Export({
  exporting,
  error,
  info,
  onExport,
}: Readonly<{
  exporting: boolean;
  error: string | null;
  info: string | null;
  onExport: (format: "docx" | "pdf") => Promise<void>;
}>) {
  return (
    <div className="gov-card mt-4 space-y-3" data-testid="phase4-export">
      <h3 className="text-navy">เผยแพร่เอกสาร</h3>
      <p className="text-sm text-muted-foreground">
        ส่งออก Word หรือ PDF ตามมาตรฐานราชการ (TH Sarabun, พ.ศ.) การอัปโหลดเข้าระบบ e-Bidding
        เป็นขั้นตอนของเจ้าหน้าที่นอกแอปนี้
      </p>
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
        <Button disabled={exporting} data-testid="export-docx" onClick={() => onExport("docx")}>
          ส่งออก Word
        </Button>
        <Button disabled={exporting} data-testid="export-pdf" onClick={() => onExport("pdf")}>
          ส่งออก PDF
        </Button>
      </div>
    </div>
  );
}
