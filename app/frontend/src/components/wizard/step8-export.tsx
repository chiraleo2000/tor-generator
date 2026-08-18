"use client";

import * as React from "react";
import { Download, FileText, Loader2, CheckCircle2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWizardStore } from "@/stores/wizard-store";
import { apiClient } from "@/lib/api-client";

type ExportStatus = "idle" | "pending" | "generating" | "completed" | "failed";

interface ExportState {
  status: ExportStatus;
  exportId: string | null;
  errorMessage: string | null;
}

const POLL_INTERVAL_MS = 2000;

/**
 * Step 8: Export — Final wizard step.
 * Triggers DOCX + PDF export generation, polls for completion,
 * and provides download buttons once ready.
 *
 * Validates: Requirements 8.1, 8.2
 */
export function Step8Export() {
  const { projectId, setFormData } = useWizardStore();

  const [exportState, setExportState] = React.useState<ExportState>({
    status: "idle",
    exportId: null,
    errorMessage: null,
  });

  const pollTimerRef = React.useRef<ReturnType<typeof setInterval> | null>(null);

  // Cleanup polling on unmount
  React.useEffect(() => {
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    };
  }, []);

  const stopPolling = () => {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  };

  const pollExportStatus = React.useCallback(() => {
    if (!projectId) return;

    pollTimerRef.current = setInterval(async () => {
      try {
        const response = await apiClient.get(
          `/projects/${projectId}/export/status`
        );
        const data = response.data?.data || response.data;
        const status = data?.status as ExportStatus;

        if (status === "completed") {
          stopPolling();
          setExportState((prev) => ({ ...prev, status: "completed" }));
          setFormData(8, { exported: true });
        } else if (status === "failed") {
          stopPolling();
          setExportState({
            status: "failed",
            exportId: data?.export_id || null,
            errorMessage: data?.error_message || "เกิดข้อผิดพลาดในการสร้างเอกสาร",
          });
        } else {
          // Still pending or generating
          setExportState((prev) => ({
            ...prev,
            status: status || prev.status,
          }));
        }
      } catch {
        stopPolling();
        setExportState((prev) => ({
          ...prev,
          status: "failed",
          errorMessage: "ไม่สามารถตรวจสอบสถานะการส่งออกได้",
        }));
      }
    }, POLL_INTERVAL_MS);
  }, [projectId, setFormData]);

  const handleTriggerExport = async () => {
    if (!projectId) {
      setExportState({
        status: "failed",
        exportId: null,
        errorMessage: "ไม่พบรหัสโครงการ กรุณาบันทึกโครงการก่อนส่งออก",
      });
      return;
    }

    setExportState({ status: "pending", exportId: null, errorMessage: null });

    try {
      const response = await apiClient.post(`/projects/${projectId}/export`);
      const data = response.data?.data || response.data;
      const exportId = data?.export_id || null;
      const status = (data?.status as ExportStatus) || "pending";

      setExportState({ status, exportId, errorMessage: null });

      // Start polling for status updates
      if (status !== "completed") {
        pollExportStatus();
      } else {
        setFormData(8, { exported: true });
      }
    } catch (error: unknown) {
      const axiosError = error as { response?: { data?: { error?: { message?: string } } } };
      const message =
        axiosError?.response?.data?.error?.message ||
        "เกิดข้อผิดพลาดในการเริ่มสร้างเอกสาร กรุณาลองใหม่อีกครั้ง";
      setExportState({
        status: "failed",
        exportId: null,
        errorMessage: message,
      });
    }
  };

  const handleRetry = () => {
    stopPolling();
    handleTriggerExport();
  };

  const handleDownload = async (format: "docx" | "pdf") => {
    if (!projectId) return;
    try {
      const response = await apiClient.get(
        `/projects/${projectId}/export/download/${format}`,
        { responseType: "blob" }
      );
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `TOR.${format}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      setExportState((prev) => ({
        ...prev,
        status: "failed",
        errorMessage: "ดาวน์โหลดไม่สำเร็จ กรุณาลองใหม่",
      }));
    }
  };

  const isProcessing =
    exportState.status === "pending" || exportState.status === "generating";

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 8: ส่งออกเอกสาร
        </h2>
        <p className="text-sm text-muted-foreground">
          สร้างเอกสาร TOR ฉบับสมบูรณ์ในรูปแบบ Word (.docx) และ PDF
          พร้อมรูปแบบเอกสารราชการไทย
        </p>
      </div>

      {/* Export trigger section */}
      <div className="border rounded-lg p-6 space-y-4">
        {/* Idle state — show trigger button */}
        {exportState.status === "idle" && (
          <div className="text-center space-y-4">
            <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <FileText className="h-8 w-8 text-primary" aria-hidden="true" />
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-4">
                เมื่อพร้อมแล้ว กดปุ่มด้านล่างเพื่อสร้างเอกสาร TOR
                ในรูปแบบ Word และ PDF
              </p>
              <Button
                onClick={handleTriggerExport}
                size="lg"
                aria-label="สร้างเอกสาร TOR"
                data-testid="export-generate"
              >
                <FileText className="h-4 w-4 mr-2" aria-hidden="true" />
                สร้างเอกสาร
              </Button>
            </div>
          </div>
        )}

        {/* Processing state — show progress */}
        {isProcessing && (
          <div className="text-center space-y-4" aria-live="polite">
            <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center">
              <Loader2
                className="h-8 w-8 text-primary animate-spin"
                aria-hidden="true"
              />
            </div>
            <div>
              <p className="font-medium">
                {exportState.status === "pending"
                  ? "กำลังเตรียมสร้างเอกสาร..."
                  : "กำลังสร้างเอกสาร..."}
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                กรุณารอสักครู่ ระบบกำลังจัดรูปแบบเอกสาร TOR
              </p>
            </div>
            {/* Progress steps */}
            <div className="flex justify-center gap-4 text-xs text-muted-foreground">
              <span
                className={
                  exportState.status === "pending"
                    ? "text-primary font-medium"
                    : "text-primary"
                }
              >
                ● เตรียมข้อมูล
              </span>
              <span
                className={
                  exportState.status === "generating"
                    ? "text-primary font-medium"
                    : ""
                }
              >
                ● สร้างเอกสาร
              </span>
              <span>● เสร็จสิ้น</span>
            </div>
          </div>
        )}

        {/* Completed state — show download buttons */}
        {exportState.status === "completed" && (
          <div className="text-center space-y-4" aria-live="polite">
            <div className="mx-auto w-16 h-16 rounded-full bg-green-100 flex items-center justify-center">
              <CheckCircle2
                className="h-8 w-8 text-green-600"
                aria-hidden="true"
              />
            </div>
            <div>
              <p className="font-medium text-green-700" data-testid="export-success">
                สร้างเอกสารเสร็จสมบูรณ์
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                ดาวน์โหลดเอกสาร TOR ได้จากปุ่มด้านล่าง
              </p>
            </div>
            <div className="flex justify-center gap-3">
              <Button
                onClick={() => handleDownload("docx")}
                variant="outline"
                aria-label="ดาวน์โหลดไฟล์ Word (.docx)"
                data-testid="export-download-docx"
              >
                <Download className="h-4 w-4 mr-2" aria-hidden="true" />
                ดาวน์โหลด Word (.docx)
              </Button>
              <Button
                onClick={() => handleDownload("pdf")}
                variant="outline"
                aria-label="ดาวน์โหลดไฟล์ PDF"
                data-testid="export-download-pdf"
              >
                <Download className="h-4 w-4 mr-2" aria-hidden="true" />
                ดาวน์โหลด PDF
              </Button>
            </div>
            {/* Regenerate option */}
            <div className="pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRetry}
                aria-label="สร้างเอกสารใหม่อีกครั้ง"
              >
                <RefreshCw className="h-3 w-3 mr-1" aria-hidden="true" />
                สร้างเอกสารใหม่
              </Button>
            </div>
          </div>
        )}

        {/* Failed state — show error + retry */}
        {exportState.status === "failed" && (
          <div className="text-center space-y-4" role="alert">
            <div className="mx-auto w-16 h-16 rounded-full bg-destructive/10 flex items-center justify-center">
              <AlertCircle
                className="h-8 w-8 text-destructive"
                aria-hidden="true"
              />
            </div>
            <div>
              <p className="font-medium text-destructive">
                ไม่สามารถสร้างเอกสารได้
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                {exportState.errorMessage}
              </p>
            </div>
            <Button
              onClick={handleRetry}
              aria-label="ลองสร้างเอกสารอีกครั้ง"
            >
              <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
              ลองใหม่อีกครั้ง
            </Button>
          </div>
        )}
      </div>

      {/* Info note about export format */}
      <div className="rounded-md border bg-muted/50 p-4">
        <p className="text-sm text-muted-foreground">
          <strong>หมายเหตุ:</strong> เอกสารที่ส่งออกจะใช้รูปแบบเอกสารราชการ —
          ฟอนต์ TH Sarabun New ขนาด 14pt, หัวข้อ 16pt, ขอบกระดาษ 2.5 ซม.
          วันที่ในรูปแบบ พ.ศ. สามารถส่งออกซ้ำได้หากมีการแก้ไขเนื้อหา TOR
        </p>
      </div>
    </div>
  );
}
