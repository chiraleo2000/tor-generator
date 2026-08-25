import { Loader2, Check, AlertCircle, Edit3 } from "lucide-react";
import { useWizardStore } from "@/stores/wizard-store";
import { Button } from "@/components/ui/button";

interface AutoSaveIndicatorProps {
  /** Callback to retry saving */
  onRetry?: () => void;
}

/**
 * Displays the current auto-save status:
 * - isDirty: "มีการแก้ไข" (has unsaved changes)
 * - isAutoSaving: "กำลังบันทึก..." (saving in progress)
 * - autoSaveError: "บันทึกไม่สำเร็จ กรุณาลองใหม่" (save failed, retry)
 * - default (saved): "บันทึกแล้ว" (saved)
 *
 * Requirements: 4.2, 4.8
 */
export function AutoSaveIndicator({
  onRetry,
}: Readonly<AutoSaveIndicatorProps>) {
  const isDirty = useWizardStore((s) => s.isDirty);
  const isAutoSaving = useWizardStore((s) => s.isAutoSaving);
  const autoSaveError = useWizardStore((s) => s.autoSaveError);

  if (isAutoSaving) {
    return (
      <div
        className="flex items-center gap-1.5 text-sm text-muted-foreground"
        role="status"
        aria-live="polite"
        aria-label="กำลังบันทึกข้อมูล"
      >
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
        <span>กำลังบันทึก...</span>
      </div>
    );
  }

  if (autoSaveError) {
    return (
      <div
        className="flex items-center gap-1.5 text-sm text-destructive"
        role="alert"
        aria-live="assertive"
      >
        <AlertCircle className="h-3.5 w-3.5" aria-hidden="true" />
        <span>บันทึกไม่สำเร็จ</span>
        {onRetry && (
          <Button
            variant="ghost"
            size="sm"
            className="h-6 px-2 text-xs text-destructive hover:text-destructive"
            onClick={onRetry}
            aria-label="ลองบันทึกอีกครั้ง"
          >
            ลองใหม่
          </Button>
        )}
      </div>
    );
  }

  if (isDirty) {
    return (
      <div
        className="flex items-center gap-1.5 text-sm text-amber-600"
        role="status"
        aria-live="polite"
        aria-label="มีการแก้ไขที่ยังไม่บันทึก"
      >
        <Edit3 className="h-3.5 w-3.5" aria-hidden="true" />
        <span>มีการแก้ไข</span>
      </div>
    );
  }

  // All saved
  return (
    <div
      className="flex items-center gap-1.5 text-sm text-green-600"
      role="status"
      aria-live="polite"
      aria-label="ข้อมูลถูกบันทึกแล้ว"
    >
      <Check className="h-3.5 w-3.5" aria-hidden="true" />
      <span>บันทึกแล้ว</span>
    </div>
  );
}
