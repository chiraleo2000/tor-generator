import * as React from "react";
import {
  Shield,
  Lightbulb,
  CheckCircle2,
  Link2,
  Check,
  X,
  Loader2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import type { Suggestion, SuggestionCategory } from "@/types/suggestions";

/** Category display configuration with Thai labels */
const CATEGORY_CONFIG: Record<
  SuggestionCategory,
  {
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
    Icon: React.ElementType;
  }
> = {
  compliance: {
    label: "ความถูกต้องตามกฎหมาย",
    color: "text-red-700",
    bgColor: "bg-red-50",
    borderColor: "border-red-200",
    Icon: Shield,
  },
  clarity: {
    label: "ความชัดเจน",
    color: "text-blue-700",
    bgColor: "bg-blue-50",
    borderColor: "border-blue-200",
    Icon: Lightbulb,
  },
  completeness: {
    label: "ความครบถ้วน",
    color: "text-amber-700",
    bgColor: "bg-amber-50",
    borderColor: "border-amber-200",
    Icon: CheckCircle2,
  },
  consistency: {
    label: "ความสอดคล้อง",
    color: "text-purple-700",
    bgColor: "bg-purple-50",
    borderColor: "border-purple-200",
    Icon: Link2,
  },
};

interface SuggestionItemProps {
  suggestion: Suggestion;
  onAccept: (id: string) => void;
  onDismiss: (id: string) => void;
  isProcessing: boolean;
}

/**
 * Individual suggestion card showing:
 * - Category badge with icon
 * - Affected section
 * - Current text vs suggested text
 * - Predicted score improvement
 * - Accept/Dismiss buttons
 */
export function SuggestionItem({
  suggestion,
  onAccept,
  onDismiss,
  isProcessing,
}: Readonly<SuggestionItemProps>) {
  const config = CATEGORY_CONFIG[suggestion.category];
  const { Icon } = config;

  return (
    <article
      className={cn(
        "rounded-lg border p-4 transition-colors",
        config.borderColor,
        config.bgColor
      )}
      aria-label={`ข้อเสนอแนะ: ${config.label} - ${suggestion.section_key}`}
    >
      {/* Header: category badge + score improvement */}
      <div className="flex items-center justify-between mb-3">
        <div className={cn("flex items-center gap-1.5 text-sm font-medium", config.color)}>
          <Icon className="h-4 w-4" aria-hidden="true" />
          <span>{config.label}</span>
        </div>
        <span className="text-xs font-medium text-green-700 bg-green-100 rounded-full px-2 py-0.5">
          +{suggestion.predicted_score_improvement.toFixed(1)} คะแนน
        </span>
      </div>

      {/* Affected section */}
      <p className="text-xs text-muted-foreground mb-2">
        ส่วน: <span className="font-medium">{suggestion.section_key}</span>
      </p>

      {/* Current text */}
      <div className="mb-2">
        <p className="text-xs font-medium text-muted-foreground mb-1">
          ข้อความปัจจุบัน:
        </p>
        <p className="text-sm bg-white/70 rounded px-2 py-1.5 border border-dashed border-gray-300 line-clamp-3">
          {suggestion.current_text}
        </p>
      </div>

      {/* Suggested text */}
      <div className="mb-3">
        <p className="text-xs font-medium text-muted-foreground mb-1">
          ข้อความที่แนะนำ:
        </p>
        <p className="text-sm bg-white rounded px-2 py-1.5 border border-green-200 line-clamp-3">
          {suggestion.suggested_text}
        </p>
      </div>

      {/* Action buttons */}
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="default"
          className="flex-1"
          onClick={() => onAccept(suggestion.id)}
          disabled={isProcessing}
          aria-label={`ยอมรับข้อเสนอแนะสำหรับส่วน ${suggestion.section_key}`}
        >
          {isProcessing ? (
            <Loader2 className="h-3 w-3 mr-1 animate-spin" aria-hidden="true" />
          ) : (
            <Check className="h-3 w-3 mr-1" aria-hidden="true" />
          )}
          ยอมรับ
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          onClick={() => onDismiss(suggestion.id)}
          disabled={isProcessing}
          aria-label={`ปิดข้อเสนอแนะสำหรับส่วน ${suggestion.section_key}`}
        >
          <X className="h-3 w-3 mr-1" aria-hidden="true" />
          ปิด
        </Button>
      </div>
    </article>
  );
}

export { CATEGORY_CONFIG };
