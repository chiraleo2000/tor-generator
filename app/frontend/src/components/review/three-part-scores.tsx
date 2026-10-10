"use client";

import { CheckItem } from "@/components/brand/check-item";
import type { BidderRiskView } from "@/components/review/bidder-risk-panel";

export type AnalyzerFindingView = {
  source_quote?: string;
  reason?: string;
  suggested_text?: string;
  section_key?: string;
  legal_basis?: string;
};

export type PartScoreView = {
  key: string;
  label: string;
  score: number;
  explanation: string;
  findings?: AnalyzerFindingView[];
};

export type TorPartScoresView = {
  legal: PartScoreView;
  lock_in: PartScoreView;
  project: PartScoreView;
  total: number;
  summary: string;
  missing_sections?: Record<string, string>;
  halted?: boolean;
  bidder_risk?: BidderRiskView | null;
};

const PART_ORDER: Array<keyof Pick<TorPartScoresView, "legal" | "lock_in" | "project">> = [
  "legal",
  "lock_in",
  "project",
];

const PART_TEST_ID: Record<string, string> = {
  legal: "review-part-legal",
  lock_in: "review-part-lock-in",
  project: "review-part-project",
};

export function isTorPartScores(value: unknown): value is TorPartScoresView {
  if (!value || typeof value !== "object") return false;
  const raw = value as Record<string, unknown>;
  return (
    typeof raw.total === "number" &&
    Boolean(raw.legal) &&
    Boolean(raw.lock_in) &&
    Boolean(raw.project)
  );
}

export function ThreePartScores({
  analysis,
}: Readonly<{ analysis: TorPartScoresView }>) {
  return (
    <div className="my-3 space-y-3" data-testid="review-part-scores">
      <CheckItem
        tone={analysis.total >= 70 ? "pass" : "warn"}
        title={`คะแนนรวมสามด้าน ${analysis.total}/100`}
        detail={analysis.summary}
      />
      {analysis.halted && analysis.missing_sections ? (
        <p className="text-xs text-muted-foreground" data-testid="review-part-missing">
          ยังขาดหมวด {Object.keys(analysis.missing_sections).join(", ")} แต่ยังให้คะแนนจากข้อความที่มี
        </p>
      ) : null}
      {PART_ORDER.map((key) => {
        const part = analysis[key];
        return (
          <section
            key={key}
            className="rounded-lg border border-navy/15 bg-slate-50 p-3"
            data-testid={PART_TEST_ID[key]}
          >
            <h4 className="text-sm font-bold text-navy">
              {part.label} — {part.score}/100
            </h4>
            <p className="mt-1 text-xs text-navy">{part.explanation}</p>
            {(part.findings || []).map((item, index) => (
              <CheckItem
                key={`${part.key}-${index}`}
                tone="warn"
                title={item.reason || "ประเด็นที่ตรวจพบ"}
                detail={[item.source_quote, item.suggested_text, item.legal_basis]
                  .filter(Boolean)
                  .join(" — ")}
              />
            ))}
          </section>
        );
      })}
    </div>
  );
}
