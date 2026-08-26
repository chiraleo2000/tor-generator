import { Loader2, CheckCircle2, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type UploadStatus = "idle" | "uploading" | "analyzing" | "done";

type Phase0UploadProps = Readonly<{
  draftText: string;
  busy: boolean;
  canStart: boolean;
  uploadedNames: string[];
  message: string | null;
  isError: boolean;
  status: UploadStatus;
  onDraftText: (value: string) => void;
  onBlurSave: () => void;
  onUpload: (files: FileList | null) => void;
  onAnalyze: () => void;
}>;

function FileNameList({ names }: Readonly<{ names: string[] }>) {
  if (!names.length) return null;
  return (
    <ul className="mt-2 space-y-1 text-sm" data-testid="phase0-file-list">
      {names.map((name, index) => (
        <li key={`${name}-${index}`} className="font-medium text-navy">
          {name}
        </li>
      ))}
    </ul>
  );
}

function Phase0ProgressPanel({
  status,
  uploadedNames,
  hasPaste,
}: Readonly<{
  status: "analyzing" | "done";
  uploadedNames: string[];
  hasPaste: boolean;
}>) {
  if (status === "done") {
    return (
      <div className="gov-card" data-testid="phase0-upload">
        <div
          className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-4"
          data-testid="phase0-done"
        >
          <CheckCircle2 className="h-6 w-6 text-green-600" />
          <div>
            <p className="text-sm font-bold text-green-800">วิเคราะห์สำเร็จ</p>
            <p className="text-xs text-green-700">กำลังไปตารางความครบในขั้นที่ ๑...</p>
          </div>
        </div>
      </div>
    );
  }
  return (
    <div className="gov-card" data-testid="phase0-upload">
      <h3 className="text-navy">กำลังวิเคราะห์เอกสาร</h3>
      <div
        className="mt-4 flex items-start gap-3 rounded-lg border border-navy/20 bg-blue-50 p-4"
        data-testid="phase0-analyzing"
      >
        <Loader2 className="mt-0.5 h-6 w-6 shrink-0 animate-spin text-navy" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold text-navy">กำลังวิเคราะห์เอกสาร...</p>
          <p className="text-xs text-muted-foreground">อย่าปิดหน้านี้ จนกว่าจะเข้าขั้นที่ ๑</p>
          <progress className="mt-3 h-2 w-full" />
          <FileNameList names={uploadedNames} />
          {hasPaste ? (
            <p className="mt-2 text-xs text-navy">รวมข้อความที่วางไว้</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function Phase0Upload({
  draftText,
  busy,
  canStart,
  uploadedNames,
  message,
  isError,
  status,
  onDraftText,
  onBlurSave,
  onUpload,
  onAnalyze,
}: Phase0UploadProps) {
  if (status === "analyzing" || status === "done") {
    return (
      <Phase0ProgressPanel
        status={status}
        uploadedNames={uploadedNames}
        hasPaste={draftText.trim().length >= 20}
      />
    );
  }

  return (
    <div className="gov-card" data-testid="phase0-upload">
      <h3 className="text-navy">ขั้นที่ ๐: เตรียมข้อมูล — อัปโหลดหรือวางข้อความ</h3>
      <p className="mt-1 text-sm text-muted-foreground">
        อัปโหลดหรือวางข้อความได้หลายครั้ง แล้วกดเริ่มวิเคราะห์ — ระบบจัดเข้าช่องแล้วพาไปตารางความครบในขั้นที่ ๑
      </p>
      <textarea
        className="mt-3 min-h-[120px] w-full rounded-md border p-3 text-sm"
        data-testid="intake-paste"
        placeholder="วางข้อความร่าง TOR หรือรายละเอียดโครงการที่นี่"
        value={draftText}
        onChange={(event) => onDraftText(event.target.value)}
        onBlur={onBlurSave}
      />

      <label
        className={cn(
          "mt-3 flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed p-6 text-sm transition-colors",
          status === "uploading"
            ? "border-navy bg-blue-50"
            : "hover:border-navy hover:bg-gray-50"
        )}
      >
        {status === "uploading" ? (
          <div className="flex items-center gap-2 text-navy" data-testid="phase0-uploading">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span>กำลังอัปโหลด...</span>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Upload className="h-5 w-5" />
            <span>คลิกอัปโหลดไฟล์ PDF / Word / สแกน</span>
          </div>
        )}
        <input
          type="file"
          multiple
          className="sr-only"
          data-testid="intake-upload"
          disabled={busy}
          onChange={(event) => onUpload(event.target.files)}
        />
      </label>

      <FileNameList names={uploadedNames} />

      <Button
        type="button"
        className="mt-3"
        data-testid="intake-start-analyze"
        disabled={busy || !canStart}
        onClick={onAnalyze}
      >
        เริ่มวิเคราะห์และเข้าขั้นที่ ๑
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
