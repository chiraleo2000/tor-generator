"use client";

import * as React from "react";
import { ValidationFinding, ValidationSeverity } from "@/types";

/**
 * Severity icon mapping:
 * - error = ❌
 * - warning = ⚠️
 * - suggestion = 💡
 */
const SEVERITY_ICONS: Record<ValidationSeverity, string> = {
  error: "❌",
  warning: "⚠️",
  suggestion: "💡",
};

const SEVERITY_LABELS: Record<ValidationSeverity, string> = {
  error: "ข้อผิดพลาด",
  warning: "คำเตือน",
  suggestion: "ข้อเสนอแนะ",
};

const SEVERITY_STYLES: Record<ValidationSeverity, string> = {
  error: "border-red-300 bg-red-50 text-red-800",
  warning: "border-amber-300 bg-amber-50 text-amber-800",
  suggestion: "border-blue-300 bg-blue-50 text-blue-800",
};

interface FindingItemProps {
  finding: ValidationFinding;
}

function FindingItem({ finding }: FindingItemProps) {
  const [showCorrection, setShowCorrection] = React.useState(false);

  return (
    <div
      className={`rounded-md border p-3 ${SEVERITY_STYLES[finding.severity]}`}
      role="alert"
      aria-label={`${SEVERITY_LABELS[finding.severity]}: ${finding.message}`}
    >
      <div className="flex items-start gap-2">
        <span className="text-base flex-shrink-0" aria-hidden="true">
          {SEVERITY_ICONS[finding.severity]}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium">{finding.message}</p>
          <p className="text-xs mt-1 opacity-75">
            กฎที่ละเมิด: {finding.rule_violated}
          </p>
          {finding.recommended_correction && (
            <div className="mt-2">
              <button
                type="button"
                className="text-xs underline cursor-pointer hover:opacity-80 focus:outline-none focus:ring-2 focus:ring-offset-1 focus:ring-current rounded"
                onClick={() => setShowCorrection(!showCorrection)}
                aria-expanded={showCorrection}
                aria-controls={`correction-${finding.rule_violated}`}
              >
                {showCorrection
                  ? "ซ่อนคำแนะนำการแก้ไข"
                  : "ดูคำแนะนำการแก้ไข"}
              </button>
              {showCorrection && (
                <p
                  id={`correction-${finding.rule_violated}`}
                  className="text-sm mt-1 p-2 rounded bg-white/50 border border-current/10"
                >
                  {finding.recommended_correction}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export interface InlineValidationFeedbackProps {
  /** Findings from real-time validation for the current section */
  findings: ValidationFinding[];
  /** Whether validation is currently running */
  isValidating: boolean;
  /** Quality score from validation (0-100) */
  qualityScore: number | null;
  /** Whether the content passed validation */
  isValid: boolean | null;
  /** Error message if the validation request failed */
  error: string | null;
}

/**
 * Displays real-time validation findings inline below/beside the section being edited.
 *
 * Features:
 * - Severity icons: error=❌, warning=⚠️, suggestion=💡
 * - Expandable recommended_correction text
 * - Loading state while validation is in progress
 * - Thai language messages
 *
 * Requirements: 10.6
 */
export function InlineValidationFeedback({
  findings,
  isValidating,
  qualityScore,
  isValid,
  error,
}: InlineValidationFeedbackProps) {
  // Nothing to show yet
  if (!isValidating && findings.length === 0 && isValid === null && !error) {
    return null;
  }

  return (
    <div
      className="mt-3 space-y-2"
      aria-live="polite"
      aria-atomic="false"
      role="region"
      aria-label="ผลการตรวจสอบแบบเรียลไทม์"
    >
      {/* Loading indicator */}
      {isValidating && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground animate-pulse">
          <svg
            className="h-4 w-4 animate-spin"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>กำลังตรวจสอบ...</span>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div
          className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* Quality score summary (shown when we have results) */}
      {!isValidating && qualityScore !== null && (
        <div className="flex items-center gap-3 text-sm">
          <span className="text-muted-foreground">คะแนนคุณภาพ:</span>
          <span
            className={`font-semibold ${
              qualityScore >= 70
                ? "text-green-600"
                : qualityScore >= 50
                  ? "text-amber-600"
                  : "text-red-600"
            }`}
          >
            {qualityScore}/100
          </span>
          {isValid !== null && (
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${
                isValid
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-700"
              }`}
            >
              {isValid ? "ผ่าน" : "ไม่ผ่าน"}
            </span>
          )}
        </div>
      )}

      {/* Findings list */}
      {!isValidating && findings.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">
            พบ {findings.length} รายการ
          </p>
          {findings.map((finding, index) => (
            <FindingItem key={`${finding.rule_violated}-${index}`} finding={finding} />
          ))}
        </div>
      )}

      {/* All clear state */}
      {!isValidating && isValid === true && findings.length === 0 && (
        <div className="flex items-center gap-2 text-sm text-green-600">
          <span aria-hidden="true">✅</span>
          <span>เนื้อหาผ่านการตรวจสอบทั้งหมด</span>
        </div>
      )}
    </div>
  );
}
