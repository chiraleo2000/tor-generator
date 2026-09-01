"use client";

import * as React from "react";
import {
  Loader2,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  Edit3,
  Save,
  X,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useWizardStore } from "@/stores/wizard-store";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { splitReviewFindings, toReviewFinding, type ReviewFinding } from "@/lib/review-findings";
import { useRealtimeValidation } from "@/lib/use-realtime-validation";
import { InlineValidationFeedback } from "@/components/wizard/inline-validation-feedback";
import { TOR_SECTION_LABELS, TOR_SECTION_ORDER, SCOPE_SUBSECTIONS } from "@/lib/tor-sections";
import { cn } from "@/lib/utils";

// --- Types ---

interface CategoryScore {
  category: string;
  label: string;
  score: number;
  weight: number;
}

interface ReviewResult {
  quality_score: number;
  categories: CategoryScore[];
  findings: ReviewFinding[];
}

interface TORSection {
  key: string;
  title: string;
  content: string;
}

type ReviewStatus = "idle" | "loading" | "success" | "error";

// --- Constants ---

/** Default category labels (Thai) with weights from the Rule Engine */
const DEFAULT_CATEGORIES: CategoryScore[] = [
  { category: "legal", label: "ความถูกต้องตามกฎหมาย", score: 0, weight: 40 },
  { category: "completeness", label: "ความครบถ้วน", score: 0, weight: 30 },
  { category: "consistency", label: "ความสอดคล้อง", score: 0, weight: 20 },
  { category: "format", label: "รูปแบบเอกสาร", score: 0, weight: 10 },
];

/** Maps wizard form data onto canonical s1–s13 */
function assembleSections(
  formData: Record<number, unknown>
): TORSection[] {
  const step1 = formData[1] as
    | {
        project_name?: string;
        ministry?: string;
        budget?: number;
        location?: string;
        duration_days?: number | null;
      }
    | undefined;
  const step2 = formData[2] as { description?: string } | undefined;
  const step3 = formData[3] as { objectives?: string[] } | undefined;
  const step4 = formData[4] as
    | { scope_items?: { title: string; details: string }[]; deliverables?: string[] }
    | undefined;
  const step5 = formData[5] as
    | { qualifications?: string[]; paid_up_capital?: number }
    | undefined;
  const step6 = formData[6] as
    | {
        budget_breakdown?: { item: string; amount: number }[];
        payment_schedule?: { percentage: number; deliverable: string }[];
        penalty_rate?: number | null;
        warranty?: string;
        duration_days?: number | null;
        s5?: string;
        s6?: string;
        s8?: string;
        s9?: string;
        s10?: string;
      }
    | undefined;
  const step7 = formData[7] as Record<string, string> | undefined;

  const contents: Record<string, string> = {};
  contents.s1 = step2?.description || step7?.s1 || "";
  contents.s2 = step3?.objectives?.filter(Boolean).map((o, i) => `${i + 1}. ${o}`).join("\n") || step7?.s2 || "";
  contents.s3 = [
    ...(step5?.qualifications || []),
    step5?.paid_up_capital
      ? `ทุนจดทะเบียนขั้นต่ำ ${step5.paid_up_capital.toLocaleString("th-TH")} บาท`
      : "",
  ]
    .filter(Boolean)
    .join("\n");
  if (step4) {
    const lines: string[] = [];
    step4.scope_items?.forEach((item, i) => {
      if (item.title || item.details) {
        lines.push(`${i + 1}. ${item.title}`);
        if (item.details) lines.push(`   ${item.details}`);
      }
    });
    if (step4.deliverables?.some(Boolean)) {
      lines.push("ผลงานส่งมอบ:");
      step4.deliverables.forEach((d, i) => d && lines.push(`  ${i + 1}. ${d}`));
    }
    contents.s4 = lines.join("\n");
  }
  contents.s5 =
    step6?.s5 ||
    (step1?.duration_days
      ? `ระยะเวลาดำเนินการ ${step1.duration_days} วัน นับจากวันลงนามในสัญญา`
      : "") ||
    (step6?.duration_days
      ? `ระยะเวลาดำเนินการ ${step6.duration_days} วัน นับจากวันลงนามในสัญญา`
      : "");
  if (step6?.budget_breakdown?.some((b) => b.item)) {
    contents.s6 = step6.budget_breakdown
      .filter((b) => b.item)
      .map((b) => `- ${b.item}: ${b.amount.toLocaleString("th-TH")} บาท`)
      .join("\n");
  } else {
    contents.s6 = step6?.s6 || (step1?.budget ? `งบประมาณ ${step1.budget.toLocaleString("th-TH")} บาท` : "");
  }
  contents.s7 = step1?.location || step7?.s7 || "";
  if (step6?.payment_schedule?.some((p) => p.deliverable || p.percentage)) {
    contents.s8 = step6.payment_schedule
      .map((p, i) => `งวดที่ ${i + 1}: ${p.percentage}% — ${p.deliverable}`)
      .join("\n");
  } else {
    contents.s8 = step6?.s8 || "";
  }
  contents.s9 = step6?.warranty || step6?.s9 || step7?.s9 || "";
  contents.s10 =
    step6?.penalty_rate != null
      ? `อัตราค่าปรับร้อยละ ${step6.penalty_rate} ต่อวัน แต่ไม่ต่ำกว่า 100 บาทต่อวัน`
      : step6?.s10 || "";
  contents.s11 = step7?.s11 || "";
  contents.s12 = step7?.s12 || "";
  contents.s13 = step7?.s13 || "";

  return TOR_SECTION_ORDER.map((key, index) => ({
    key,
    title: `${index + 1}. ${TOR_SECTION_LABELS[key]}`,
    content: contents[key] || "",
  }));
}

function getScoreBadgeColor(score: number): string {
  if (score >= 70) return "bg-green-100 text-green-800 border-green-300";
  if (score >= 50) return "bg-amber-100 text-amber-800 border-amber-300";
  return "bg-red-100 text-red-800 border-red-300";
}

function getScoreBarColor(score: number): string {
  if (score >= 70) return "bg-green-500";
  if (score >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function getSeverityStyle(severity: string): string {
  switch (severity) {
    case "error":
      return "border-red-300 bg-red-50 text-red-800";
    case "warning":
      return "border-amber-300 bg-amber-50 text-amber-800";
    default:
      return "border-blue-300 bg-blue-50 text-blue-800";
  }
}

function getSeverityLabel(severity: string): string {
  switch (severity) {
    case "error":
      return "ข้อผิดพลาด";
    case "warning":
      return "คำเตือน";
    default:
      return "ข้อเสนอแนะ";
  }
}

function WizardFindingGroup({
  title,
  items,
}: Readonly<{ title: string; items: ReviewFinding[] }>) {
  return (
    <div>
      <h4 className="mb-2 text-xs font-semibold text-navy">{title}</h4>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">ไม่พบรายการในกลุ่มนี้</p>
      ) : (
        <div className="max-h-60 space-y-2 overflow-y-auto">
          {items.map((finding) => (
            <div
              key={`${finding.rule}-${finding.section}-${finding.message}`}
              className={cn(
                "rounded-md border p-3 text-sm",
                getSeverityStyle(finding.severity)
              )}
            >
              <div className="mb-1 flex items-center gap-2">
                <span className="rounded-full bg-white/50 px-2 py-0.5 text-xs font-medium">
                  {getSeverityLabel(finding.severity)}
                </span>
                <span className="text-xs opacity-75">ส่วน: {finding.section}</span>
              </div>
              <p>{finding.message}</p>
              {finding.legalBasis ? (
                <p className="mt-1 text-xs opacity-75">อ้างอิง: {finding.legalBasis}</p>
              ) : null}
              {finding.recommendation ? (
                <p className="mt-1 text-xs opacity-75">แนะนำ: {finding.recommendation}</p>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Component ---

/**
 * Step 7: Review — Displays full assembled TOR document, quality score badge,
 * category breakdown bars, findings, and inline section editing.
 *
 * Validates: Requirements 4.4, 10.4
 */
export function Step7Review() {
  const { projectId, formData, setFormData } = useWizardStore();

  const [reviewStatus, setReviewStatus] = React.useState<ReviewStatus>("idle");
  const [reviewResult, setReviewResult] = React.useState<ReviewResult | null>(null);
  const [errorMessage, setErrorMessage] = React.useState<string | null>(null);

  // Assembled TOR sections (editable)
  const [sections, setSections] = React.useState<TORSection[]>([]);
  // Track which section is being inline-edited
  const [editingSection, setEditingSection] = React.useState<string | null>(null);
  const [editContent, setEditContent] = React.useState<string>("");

  // Real-time validation for inline editing (3s debounce)
  const {
    findings: validationFindings,
    isValidating,
    qualityScore: validationScore,
    isValid: validationIsValid,
    error: validationError,
    validate: triggerValidation,
    clearValidation,
  } = useRealtimeValidation(projectId);

  // Initialize sections from wizard form data
  React.useEffect(() => {
    const assembled = assembleSections(formData);
    setSections(assembled);
  }, [formData]);

  // Call POST /review on mount to get fresh score
  const runReview = React.useCallback(async () => {
    if (!projectId) {
      setReviewStatus("error");
      setErrorMessage("ไม่พบรหัสโครงการ กรุณาบันทึกโครงการก่อนตรวจสอบ");
      return;
    }

    setReviewStatus("loading");
    setErrorMessage(null);

    try {
      const response = await apiClient.post(`/projects/${projectId}/review`);
      const data = unwrapData<{
        quality_score?: number;
        categories?: CategoryScore[];
        findings?: Record<string, unknown>[];
      }>(response);
      const categories = (data.categories || DEFAULT_CATEGORIES).map(
        (cat: CategoryScore) => ({
          ...cat,
          label:
            cat.label ||
            DEFAULT_CATEGORIES.find((d) => d.category === cat.category)?.label ||
            cat.category,
          weight: cat.weight <= 1 ? Math.round(cat.weight * 100) : cat.weight,
        })
      );
      const findings = (data.findings || []).map(toReviewFinding);

      const result: ReviewResult = {
        quality_score: data.quality_score ?? 0,
        categories,
        findings,
      };

      setReviewResult(result);
      setReviewStatus("success");
      setFormData(7, { reviewed: true });
    } catch (error: unknown) {
      const axiosError = error as {
        response?: { data?: { error?: { message?: string } } };
      };
      const message =
        axiosError?.response?.data?.error?.message ||
        "เกิดข้อผิดพลาดในการตรวจสอบเอกสาร กรุณาลองใหม่อีกครั้ง";
      setReviewStatus("error");
      setErrorMessage(message);
    }
  }, [projectId, setFormData]);

  // --- Inline Editing ---
  const handleStartEdit = (sectionKey: string, content: string) => {
    setEditingSection(sectionKey);
    setEditContent(content);
    clearValidation();
  };

  const handleSaveEdit = (sectionKey: string) => {
    setSections((prev) =>
      prev.map((s) => (s.key === sectionKey ? { ...s, content: editContent } : s))
    );
    const existing = (formData[7] as Record<string, string>) || {};
    setFormData(7, { ...existing, [sectionKey]: editContent });
    if (projectId) {
      apiClient
        .put(`/projects/${projectId}/steps/7`, {
          data: { [sectionKey]: editContent },
        })
        .catch(() => undefined);
    }
    setEditingSection(null);
    setEditContent("");
    clearValidation();
  };

  const handleCancelEdit = () => {
    setEditingSection(null);
    setEditContent("");
    clearValidation();
  };

  /** Handle content change while editing — triggers debounced validation */
  const handleEditContentChange = (sectionKey: string, newContent: string) => {
    setEditContent(newContent);
    // Trigger real-time validation with 3s debounce
    if (newContent.trim().length > 0) {
      triggerValidation(sectionKey, newContent);
    }
  };

  // --- Render helpers ---

  const qualityScore = reviewResult?.quality_score ?? 0;
  const categories = reviewResult?.categories || DEFAULT_CATEGORIES;
  const findings = reviewResult?.findings || [];
  const findingGroups = splitReviewFindings(findings);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold mb-2">
          ขั้นตอนที่ 7: ตรวจสอบและข้อเสนอแนะ
        </h2>
        <p className="text-sm text-muted-foreground">
          นำเข้าเนื้อหาจากขั้นตอนก่อนหน้าแล้วกดเริ่มตรวจสอบ — ระบบจะไม่รันจนกว่าคุณยืนยัน
        </p>
      </div>

      {/* Loading state */}
      {reviewStatus === "loading" && (
        <div
          className="flex flex-col items-center justify-center py-12"
          aria-live="polite"
        >
          <Loader2 className="h-8 w-8 text-primary animate-spin mb-3" aria-hidden="true" />
          <p className="text-sm text-muted-foreground">
            กำลังตรวจสอบเอกสาร TOR...
          </p>
        </div>
      )}

      {/* Error state */}
      {reviewStatus === "error" && (
        <div className="border border-destructive/50 rounded-lg p-6 text-center" role="alert">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" aria-hidden="true" />
          <p className="font-medium text-destructive mb-2">
            ไม่สามารถตรวจสอบเอกสารได้
          </p>
          <p className="text-sm text-muted-foreground mb-4">{errorMessage}</p>
          <Button onClick={runReview} variant="outline" aria-label="ลองตรวจสอบอีกครั้ง">
            <RefreshCw className="h-4 w-4 mr-2" aria-hidden="true" />
            ลองใหม่อีกครั้ง
          </Button>
        </div>
      )}

      {/* Success state: Score + Document Preview */}
      {reviewStatus === "success" && (
        <>
          {/* Quality Score Badge */}
          <div className="flex items-center gap-4 p-4 border rounded-lg">
            <div
              className={cn(
                "flex items-center justify-center w-20 h-20 rounded-full border-2 text-2xl font-bold",
                getScoreBadgeColor(qualityScore)
              )}
              aria-label={`คะแนนคุณภาพ ${qualityScore} จาก 100`}
            >
              {qualityScore}
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-lg">คะแนนคุณภาพ TOR</h3>
              <p className="text-sm text-muted-foreground">
                {qualityScore >= 70 && "คุณภาพดี — พร้อมส่งออก"}
                {qualityScore >= 50 && qualityScore < 70 && "คุณภาพปานกลาง — ควรปรับปรุงก่อนส่งออก"}
                {qualityScore < 50 && "คุณภาพต่ำ — จำเป็นต้องแก้ไข"}
              </p>
              {qualityScore >= 70 && (
                <CheckCircle2 className="h-4 w-4 text-green-600 inline-block mt-1" aria-hidden="true" />
              )}
            </div>
            <Button onClick={runReview} variant="ghost" size="sm" aria-label="ตรวจสอบอีกครั้ง">
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>

          {/* Category Breakdown */}
          <div className="border rounded-lg p-4 space-y-3">
            <h3 className="font-medium text-sm">คะแนนแยกตามหมวดหมู่</h3>
            {categories.map((cat) => (
              <div key={cat.category} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span>
                    {cat.label} ({cat.weight}%)
                  </span>
                  <span className="font-medium">{cat.score}/100</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2">
                  <progress
                    className="sr-only"
                    value={cat.score}
                    max={100}
                    aria-label={`${cat.label}: ${cat.score} คะแนน`}
                  />
                  <div
                    className={cn("h-2 rounded-full transition-all duration-300", getScoreBarColor(cat.score))}
                    style={{ width: `${cat.score}%` }}
                    aria-hidden="true"
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Findings */}
          {findings.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-medium text-sm">
                ผลการตรวจสอบ ({findings.length} รายการ)
              </h3>
              <WizardFindingGroup
                title="กลุ่ม ก — ผิดกฎหมาย / ระเบียบ"
                items={findingGroups.legal}
              />
              <WizardFindingGroup
                title="กลุ่ม ข — ความเสี่ยงจากความผิดปกติ"
                items={findingGroups.risk}
              />
            </div>
          )}

          {/* Full TOR Document Preview with inline editing */}
          <div className="border rounded-lg">
            <div className="border-b px-4 py-3 bg-muted/30">
              <h3 className="font-medium">ตัวอย่างเอกสาร TOR ฉบับสมบูรณ์</h3>
              <p className="text-xs text-muted-foreground">
                คลิกปุ่มแก้ไขเพื่อปรับเนื้อหาแต่ละส่วนได้โดยตรง
              </p>
            </div>

            <div className="divide-y">
              {sections.length === 0 && (
                <div className="p-6 text-center text-muted-foreground text-sm">
                  ยังไม่มีข้อมูลจากขั้นตอนก่อนหน้า
                  กรุณากลับไปกรอกข้อมูลในขั้นตอนที่ 1-6
                </div>
              )}

              {sections.map((section) => (
                <div key={section.key} className="p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-sm">{section.title}</h4>
                    {editingSection !== section.key ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleStartEdit(section.key, section.content)}
                        aria-label={`แก้ไข${section.title}`}
                      >
                        <Edit3 className="h-3 w-3 mr-1" aria-hidden="true" />
                        แก้ไข
                      </Button>
                    ) : (
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleSaveEdit(section.key)}
                          aria-label={`บันทึกการแก้ไข${section.title}`}
                        >
                          <Save className="h-3 w-3 mr-1" aria-hidden="true" />
                          บันทึก
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={handleCancelEdit}
                          aria-label="ยกเลิกการแก้ไข"
                        >
                          <X className="h-3 w-3 mr-1" aria-hidden="true" />
                          ยกเลิก
                        </Button>
                      </div>
                    )}
                  </div>

                  {editingSection === section.key ? (
                    <div>
                      <Textarea
                        value={editContent}
                        onChange={(e) => handleEditContentChange(section.key, e.target.value)}
                        className="min-h-[120px] font-mono text-sm"
                        lang="th"
                        aria-label={`แก้ไขเนื้อหา${section.title}`}
                      />
                      {/* Real-time validation feedback inline with the section being edited */}
                      <InlineValidationFeedback
                        findings={validationFindings}
                        isValidating={isValidating}
                        qualityScore={validationScore}
                        isValid={validationIsValid}
                        error={validationError}
                      />
                    </div>
                  ) : (
                    <>
                    <pre className="whitespace-pre-wrap text-sm text-muted-foreground font-sans leading-relaxed">
                      {section.content || "(ไม่มีข้อมูล)"}
                    </pre>
                    {section.key === "s4" && (
                      <div className="flex flex-wrap gap-1 mt-3">
                        {SCOPE_SUBSECTIONS.map((sub) => (
                          <span
                            key={sub.key}
                            className="text-[11px] px-2 py-0.5 rounded-full border bg-muted"
                          >
                            {sub.key.replace("s", "")} {sub.title}
                          </span>
                        ))}
                      </div>
                    )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Idle state — prompt to run review */}
      {reviewStatus === "idle" && (
        <div className="text-center py-8">
          <p className="text-sm text-muted-foreground mb-4">
            กดยืนยันเพื่อเริ่มตรวจสอบคุณภาพเอกสาร TOR
          </p>
          <Button
            onClick={runReview}
            aria-label="เริ่มตรวจสอบ"
            data-testid="wizard-start-review"
          >
            เริ่มตรวจสอบ TOR
          </Button>
        </div>
      )}
    </div>
  );
}
