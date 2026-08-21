"use client";

import { Button } from "@/components/ui/button";

export function Phase0Upload({
  draftText,
  busy,
  canStart,
  uploadedNames,
  message,
  isError,
  onDraftText,
  onBlurSave,
  onUpload,
  onAnalyze,
}: Readonly<{
  draftText: string;
  busy: boolean;
  canStart: boolean;
  uploadedNames: string[];
  message: string | null;
  isError: boolean;
  onDraftText: (value: string) => void;
  onBlurSave: () => void;
  onUpload: (files: FileList | null) => void;
  onAnalyze: () => void;
}>) {
  return (
    <div className="gov-card" data-testid="phase0-upload">
      <h3 className="text-navy">Phase 0: เตรียมข้อมูล — อัปโหลดหรือวางข้อความ</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        อัปโหลดเอกสารหรือวางข้อความได้หลายครั้ง — กดเริ่มวิเคราะห์เมื่อพร้อม ระบบจะอ่านแล้วไปคุยต่อใน Phase 2
      </p>
      <textarea
        className="mt-3 min-h-[120px] w-full rounded-md border p-3 text-sm"
        data-testid="intake-paste"
        placeholder="วางข้อความร่าง TOR หรือรายละเอียดโครงการที่นี่"
        value={draftText}
        onChange={(event) => onDraftText(event.target.value)}
        onBlur={onBlurSave}
      />
      <label className="mt-3 flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed p-6 text-sm">
        <span>{busy ? "กำลังอัปโหลด..." : "คลิกอัปโหลดไฟล์ PDF / Word / สแกน"}</span>
        <input
          type="file"
          multiple
          className="sr-only"
          data-testid="intake-upload"
          onChange={(event) => onUpload(event.target.files)}
        />
      </label>
      {uploadedNames.length ? (
        <ul className="mt-2 list-disc pl-5 text-sm" data-testid="phase0-file-list">
          {uploadedNames.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      ) : null}
      <Button
        type="button"
        className="mt-3"
        data-testid="intake-start-analyze"
        disabled={busy || !canStart}
        onClick={onAnalyze}
      >
        เริ่มวิเคราะห์และเข้า Phase 1
      </Button>
      {message ? (
        <p
          className={`mt-2 text-sm ${isError ? "text-destructive" : "text-brand-green"}`}
          role={isError ? "alert" : undefined}
        >
          {message}
        </p>
      ) : null}
    </div>
  );
}
