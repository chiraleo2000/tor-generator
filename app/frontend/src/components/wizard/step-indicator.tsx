"use client";

import * as React from "react";
import { Check, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";

export interface StepInfo {
  number: number;
  title: string;
}

export const WIZARD_STEPS: StepInfo[] = [
  { number: 1, title: "ข้อมูล" },
  { number: 2, title: "ความเป็นมา" },
  { number: 3, title: "วัตถุประสงค์" },
  { number: 4, title: "ขอบเขต" },
  { number: 5, title: "คุณสมบัติ" },
  { number: 6, title: "งบ/งวด" },
  { number: 7, title: "ตรวจสอบ" },
  { number: 8, title: "ส่งออก" },
];

interface StepIndicatorProps {
  currentStep: number;
  validationErrors: Record<number, string[]>;
  completedSteps: Set<number>;
  onStepClick: (step: number) => void;
}

/**
 * Step progress indicator component showing:
 * - Current step highlighted
 * - Completed steps with checkmark
 * - Completion percentage
 * - Validation status per step (error icon if has errors)
 */
export function StepIndicator({
  currentStep,
  validationErrors,
  completedSteps,
  onStepClick,
}: Readonly<StepIndicatorProps>) {
  const completionPercentage = Math.round(
    (completedSteps.size / WIZARD_STEPS.length) * 100
  );

  return (
    <div className="mb-8">
      {/* Header with title and completion percentage */}
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-lg font-semibold">จัดทำร่าง TOR</h1>
        <span className="text-sm text-muted-foreground">
          ความคืบหน้า: {completionPercentage}%
        </span>
      </div>

      {/* Progress bar */}
      <progress
        className="mb-4 h-2 w-full appearance-none overflow-hidden rounded-full bg-muted [&::-webkit-progress-bar]:rounded-full [&::-webkit-progress-bar]:bg-muted [&::-webkit-progress-value]:rounded-full [&::-webkit-progress-value]:bg-primary [&::-moz-progress-bar]:bg-primary"
        value={completionPercentage}
        max={100}
        aria-label={`ความคืบหน้า ${completionPercentage} เปอร์เซ็นต์`}
      />

      {/* Step indicators */}
      <nav aria-label="ขั้นตอนการจัดทำ TOR">
        <ol className="flex gap-1 overflow-x-auto pb-1">
          {WIZARD_STEPS.map((s) => {
            const isActive = s.number === currentStep;
            const isCompleted = completedSteps.has(s.number);
            const hasErrors =
              validationErrors[s.number] &&
              validationErrors[s.number].length > 0;
            const isNavigable = s.number <= currentStep || isCompleted;

            return (
              <li key={s.number} className="flex-1 min-w-0">
                <button
                  type="button"
                  onClick={() => {
                    if (isNavigable) {
                      onStepClick(s.number);
                    }
                  }}
                  disabled={!isNavigable}
                  className={cn(
                    "w-full text-center py-2 px-1 rounded text-xs transition-colors relative",
                    isActive &&
                      "bg-primary text-primary-foreground font-medium",
                    isActive && hasErrors && "ring-2 ring-destructive",
                    !isActive &&
                      isCompleted &&
                      "bg-primary/20 text-primary hover:bg-primary/30 cursor-pointer",
                    !isActive &&
                      !isCompleted &&
                      !isNavigable &&
                      "bg-muted text-muted-foreground cursor-not-allowed",
                    !isActive &&
                      !isCompleted &&
                      isNavigable &&
                      "bg-muted text-muted-foreground hover:bg-muted/80 cursor-pointer"
                  )}
                  aria-current={isActive ? "step" : undefined}
                  aria-label={`ขั้นตอนที่ ${s.number}: ${s.title}${
                    isCompleted ? " (เสร็จสิ้น)" : ""
                  }${hasErrors ? " (มีข้อผิดพลาด)" : ""}`}
                >
                  {/* Step number with checkmark/error icons */}
                  <span className="flex items-center justify-center gap-0.5">
                    {isCompleted && !isActive ? (
                      <Check
                        className="h-3 w-3 inline-block"
                        aria-hidden="true"
                      />
                    ) : (
                      <span className="font-medium">{s.number}</span>
                    )}
                    {hasErrors && (
                      <AlertCircle
                        className={cn(
                          "h-3 w-3 inline-block",
                          isActive
                            ? "text-primary-foreground"
                            : "text-destructive"
                        )}
                        aria-hidden="true"
                      />
                    )}
                  </span>
                  <span className="block truncate mt-0.5">{s.title}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </nav>
    </div>
  );
}
