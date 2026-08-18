"use client";

import * as React from "react";
import {
  Loader2,
  AlertTriangle,
  Sparkles,
  RefreshCw,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { useWizardStore } from "@/stores/wizard-store";
import { SuggestionItem, CATEGORY_CONFIG } from "@/components/wizard/suggestion-item";
import type {
  Suggestion,
  SuggestionCategory,
  SuggestionsResponse,
} from "@/types/suggestions";

type FilterCategory = SuggestionCategory | "all";

interface SuggestionsPanelProps {
  /** Override project ID (defaults to wizard store projectId) */
  projectId?: string;
}

/**
 * AI Suggestions Panel (Step 7 side panel)
 *
 * Displays 3–20 AI-identified improvements categorized by:
 * - compliance (ความถูกต้องตามกฎหมาย)
 * - clarity (ความชัดเจน)
 * - completeness (ความครบถ้วน)
 * - consistency (ความสอดคล้อง)
 *
 * Features:
 * - Category filter tabs
 * - Accept suggestion: applies change via PUT, then re-validates
 * - Dismiss suggestion: persists as dismissed, not re-shown unless content changes
 * - Quality score display with category breakdown
 *
 * Requirements: 10.1, 10.3, 10.4, 10.5, 10.7
 */
export function SuggestionsPanel({
  projectId: propProjectId,
}: Readonly<SuggestionsPanelProps>) {
  const storeProjectId = useWizardStore((s) => s.projectId);
  const projectId = propProjectId || storeProjectId;

  const [suggestions, setSuggestions] = React.useState<Suggestion[]>([]);
  const [qualityScore, setQualityScore] = React.useState<number>(0);
  const [isLoading, setIsLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [processingId, setProcessingId] = React.useState<string | null>(null);
  const [activeFilter, setActiveFilter] = React.useState<FilterCategory>("all");

  // Fetch suggestions from API
  const fetchSuggestions = React.useCallback(async () => {
    if (!projectId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<SuggestionsResponse>(
        `/projects/${projectId}/suggestions`
      );
      const payload = unwrapData<SuggestionsResponse>(response);
      const items = payload.items || [];
      setSuggestions(items.filter((s) => s.status === "pending"));
      setQualityScore(payload.quality_score ?? 0);
    } catch {
      setError("ไม่สามารถโหลดข้อเสนอแนะได้ กรุณาลองใหม่อีกครั้ง");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  // Load suggestions on mount
  React.useEffect(() => {
    fetchSuggestions();
  }, [fetchSuggestions]);

  // Accept a suggestion: apply change via PUT, then re-validate
  const setFormData = useWizardStore((s) => s.setFormData);
  const formData = useWizardStore((s) => s.formData);

  const handleAccept = React.useCallback(
    async (suggestionId: string) => {
      if (!projectId) return;

      setProcessingId(suggestionId);
      try {
        const suggestion = suggestions.find((s) => s.id === suggestionId);
        await apiClient.put(
          `/projects/${projectId}/suggestions/${suggestionId}`,
          { status: "accepted" }
        );

        if (suggestion?.suggested_text) {
          const existing = (formData[7] as Record<string, string>) || {};
          setFormData(7, {
            ...existing,
            [suggestion.section_key]: suggestion.suggested_text,
          });
          await apiClient.put(`/projects/${projectId}/steps/7`, {
            data: { [suggestion.section_key]: suggestion.suggested_text },
          });
        }

        await apiClient.post(`/projects/${projectId}/validate`);
        setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId));
        await fetchSuggestions();
      } catch {
        setError("ไม่สามารถยอมรับข้อเสนอแนะได้ กรุณาลองใหม่อีกครั้ง");
      } finally {
        setProcessingId(null);
      }
    },
    [projectId, fetchSuggestions, suggestions, formData, setFormData]
  );

  // Dismiss a suggestion: persist as dismissed
  const handleDismiss = React.useCallback(
    async (suggestionId: string) => {
      if (!projectId) return;

      setProcessingId(suggestionId);
      try {
        await apiClient.put(
          `/projects/${projectId}/suggestions/${suggestionId}`,
          { status: "dismissed" }
        );

        // Remove dismissed suggestion from the displayed list
        setSuggestions((prev) => prev.filter((s) => s.id !== suggestionId));
      } catch {
        setError("ไม่สามารถปิดข้อเสนอแนะได้ กรุณาลองใหม่อีกครั้ง");
      } finally {
        setProcessingId(null);
      }
    },
    [projectId]
  );

  // Filter suggestions by category
  const filteredSuggestions = React.useMemo(() => {
    if (activeFilter === "all") return suggestions;
    return suggestions.filter((s) => s.category === activeFilter);
  }, [suggestions, activeFilter]);

  // Count suggestions per category
  const categoryCounts = React.useMemo(() => {
    const counts: Record<SuggestionCategory, number> = {
      compliance: 0,
      clarity: 0,
      completeness: 0,
      consistency: 0,
    };
    suggestions.forEach((s) => {
      counts[s.category]++;
    });
    return counts;
  }, [suggestions]);

  // No project ID available
  if (!projectId) {
    return (
      <aside
        className="w-full h-full flex items-center justify-center p-4"
        aria-label="แผงข้อเสนอแนะ AI"
      >
        <p className="text-sm text-muted-foreground">
          ไม่พบโครงการ กรุณาเลือกโครงการก่อน
        </p>
      </aside>
    );
  }

  return (
    <aside
      className="flex h-full w-full min-h-0 flex-col bg-background"
      aria-label="แผงข้อเสนอแนะ AI"
    >
      {/* Panel Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" aria-hidden="true" />
            <h2 className="text-base font-semibold">ข้อเสนอแนะ AI</h2>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={fetchSuggestions}
            disabled={isLoading}
            aria-label="รีเฟรชข้อเสนอแนะ"
          >
            <RefreshCw
              className={cn("h-4 w-4", isLoading && "animate-spin")}
              aria-hidden="true"
            />
          </Button>
        </div>

        {/* Quality Score Badge */}
        <div className="flex items-center gap-2 mb-3">
          <span className="text-sm text-muted-foreground">คะแนนคุณภาพ:</span>
          <span
            className={cn(
              "text-lg font-bold px-2 py-0.5 rounded",
              qualityScore >= 70 && "text-green-700 bg-green-100",
              qualityScore >= 50 && qualityScore < 70 && "text-amber-700 bg-amber-100",
              qualityScore < 50 && "text-red-700 bg-red-100"
            )}
          >
            {qualityScore}/100
          </span>
        </div>

        {/* Category Filter Tabs */}
        <div className="flex flex-wrap gap-1">
          <button
            type="button"
            onClick={() => setActiveFilter("all")}
            className={cn(
              "text-xs px-2 py-1 rounded-full border transition-colors",
              activeFilter === "all"
                ? "bg-primary text-primary-foreground border-primary"
                : "bg-muted text-muted-foreground border-transparent hover:bg-muted/80"
            )}
            aria-pressed={activeFilter === "all"}
          >
            ทั้งหมด ({suggestions.length})
          </button>
          {(
            Object.keys(CATEGORY_CONFIG) as SuggestionCategory[]
          ).map((cat) => {
            const config = CATEGORY_CONFIG[cat];
            return (
              <button
                key={cat}
                type="button"
                onClick={() => setActiveFilter(cat)}
                className={cn(
                  "text-xs px-2 py-1 rounded-full border transition-colors",
                  activeFilter === cat
                    ? `${config.bgColor} ${config.color} ${config.borderColor}`
                    : "bg-muted text-muted-foreground border-transparent hover:bg-muted/80"
                )}
                aria-pressed={activeFilter === cat}
              >
                {config.label} ({categoryCounts[cat]})
              </button>
            );
          })}
        </div>
      </div>

      {/* Suggestions List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Loading state */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center py-8">
            <Loader2 className="h-8 w-8 animate-spin text-primary mb-2" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">กำลังโหลดข้อเสนอแนะ...</p>
          </div>
        )}

        {/* Error state */}
        {error && !isLoading && (
          <div
            className="flex items-start gap-2 p-3 rounded-md border border-destructive/50 bg-destructive/10"
            role="alert"
          >
            <AlertTriangle className="h-4 w-4 text-destructive mt-0.5" aria-hidden="true" />
            <div>
              <p className="text-sm text-destructive">{error}</p>
              <Button
                variant="ghost"
                size="sm"
                className="mt-1 text-xs"
                onClick={() => {
                  setError(null);
                  fetchSuggestions();
                }}
              >
                ลองใหม่
              </Button>
            </div>
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && filteredSuggestions.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Sparkles className="h-8 w-8 text-muted-foreground/50 mb-2" aria-hidden="true" />
            <p className="text-sm text-muted-foreground">
              {activeFilter === "all"
                ? "ไม่มีข้อเสนอแนะในขณะนี้"
                : "ไม่มีข้อเสนอแนะในหมวดนี้"}
            </p>
          </div>
        )}

        {/* Suggestion items */}
        {!isLoading &&
          !error &&
          filteredSuggestions.map((suggestion) => (
            <SuggestionItem
              key={suggestion.id}
              suggestion={suggestion}
              onAccept={handleAccept}
              onDismiss={handleDismiss}
              isProcessing={processingId === suggestion.id}
            />
          ))}
      </div>

      {/* Footer with suggestion count */}
      {!isLoading && suggestions.length > 0 && (
        <div className="p-3 border-t text-center">
          <p className="text-xs text-muted-foreground">
            แสดง {filteredSuggestions.length} จาก {suggestions.length} ข้อเสนอแนะ
          </p>
        </div>
      )}
    </aside>
  );
}
