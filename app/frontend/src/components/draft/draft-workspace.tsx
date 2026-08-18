"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { StatusPill } from "@/components/brand/status-pill";
import { PhaseFlow } from "@/components/brand/phase-flow";
import { MappingBox } from "@/components/brand/mapping-box";
import { CheckItem } from "@/components/brand/check-item";
import { IntakeChatPanel } from "@/components/draft/intake-chat-panel";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { useProjectStore } from "@/stores/project-store";
import {
  HITL_SECTIONS,
  SCOPE_SUBSECTIONS,
  SECTION_FIELDS,
  TOR_SECTION_ORDER,
  serializeSectionDraft,
  type SectionField,
} from "@/lib/tor-sections";
import { toReviewFinding, findingCheckTone, type ReviewFinding } from "@/lib/review-findings";
import { canSelectPhase, displayPhase, intakeUnlockedPhase } from "@/lib/phase-gate";
import { cn } from "@/lib/utils";

interface SectionPayload {
  key: string;
  title: string;
  filled: boolean;
  content: string;
  human_confirmed: boolean;
  hitl: boolean;
  matchStatus: string;
  big?: boolean;
  subs?: { key: string; title: string; content: string; filled: boolean }[];
}

function parseFields(content: string): Record<string, string> {
  if (!content) return {};
  try {
    const parsed = JSON.parse(content) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, string>;
    }
  } catch {
    return { body: content };
  }
  return { body: content };
}

function displayExtracted(value: unknown): string {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return "";
}

function sectionCircleClass(filled: boolean, expanded: boolean): string {
  if (filled) return "border-[#0f5c22] bg-brand-green text-white";
  if (expanded) return "border-crimson bg-brand-orange text-navy";
  return "border-gray-300 bg-gray-200 text-gray-700";
}

export function DraftWorkspace() {
  const params = useParams();
  const router = useRouter();
  const projectId = (params.id as string) || "";
  const { activeProject, fetchProject } = useProjectStore();
  const [phase, setPhase] = useState(0);
  const [unlocked, setUnlocked] = useState(0);
  const [sections, setSections] = useState<SectionPayload[]>([]);
  const [expanded, setExpanded] = useState<string>("s1");
  const [openSub, setOpenSub] = useState<string>("");
  const [extracted, setExtracted] = useState<Record<string, unknown>>({});
  const [busy, setBusy] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [reviewScore, setReviewScore] = useState<number | null>(null);
  const [reviewFindings, setReviewFindings] = useState<ReviewFinding[]>([]);
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInfo, setActionInfo] = useState<string | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);

  const loadSections = useCallback(async () => {
    const response = await apiClient.get(`/projects/${projectId}/sections`);
    const payload = unwrapData<{ sections?: SectionPayload[] }>(response);
    setSections(payload.sections || []);
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    fetchProject(projectId)
      .then((project) => {
        const nextUnlocked = intakeUnlockedPhase(project);
        setUnlocked(nextUnlocked);
        setPhase(displayPhase(project.currentPhase ?? 0, nextUnlocked));
        if (project.extractedFields) {
          setExtracted(project.extractedFields);
        }
      })
      .catch(() => undefined);
    loadSections().catch(() => undefined);
  }, [projectId, fetchProject, loadSections]);

  async function persistPhase(next: number, nextUnlocked = unlocked) {
    if (!canSelectPhase(phase, nextUnlocked, next)) {
      return;
    }
    try {
      await apiClient.patch(`/projects/${projectId}/phase`, { phase: next });
      setUnlocked(nextUnlocked);
      setPhase(next);
    } catch {
      // stay on the current phase when the server rejects a skip
    }
  }

  async function saveSection(
    key: string,
    content: string,
    humanConfirmed = false
  ) {
    await apiClient.put(`/projects/${projectId}/sections/${key}`, {
      content,
      filled: Boolean(content.trim()),
      human_confirmed: humanConfirmed,
    });
    await loadSections();
  }

  async function draftSection(key: string) {
    setBusy(true);
    setActionError(null);
    setActionInfo(null);
    try {
      await apiClient.post(`/projects/${projectId}/draft-section`, {
        section_key: key,
      });
      await loadSections();
      setActionInfo("ร่างด้วย AI สำเร็จ — ตรวจข้อความแล้วบันทึก");
    } catch (err: unknown) {
      setActionError(apiErrorMessage(err, "ร่างด้วย AI ไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  const filledCount = sections.filter((s) => s.filled).length;
  const hitlReady = HITL_SECTIONS.every((key) =>
    sections.find((s) => s.key === key && s.human_confirmed)
  );

  if (!projectId) {
    return (
      <div className="py-16 text-center">
        <p>กรุณาเลือกโครงการจากแดชบอร์ด</p>
        <Button className="mt-3" onClick={() => router.push("/projects")}>
          ไปที่แดชบอร์ด
        </Button>
      </div>
    );
  }

  return (
    <div data-testid="draft-page">
      <div className="gov-card mb-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-[15px] font-bold text-navy">
              {activeProject?.name || "โครงการใหม่"}
            </p>
            <p className="text-xs text-muted-foreground">
              เริ่มที่ Phase 0 — วางข้อความหรืออัปโหลดเอกสารก่อน จึงจะไปร่าง TOR ได้
            </p>
          </div>
          <StatusPill status={activeProject?.status || "draft"} />
        </div>
        <PhaseFlow
          current={phase}
          unlocked={unlocked}
          onSelect={(next) => persistPhase(next)}
        />
      </div>

      {phase === 0 || phase === 1 ? (
        <IntakeChatPanel
          projectId={projectId}
          phase={phase}
          onAnalyzed={() => persistPhase(1, Math.max(unlocked, 1))}
          onReady={() => {
            persistPhase(2, 2)
              .then(() => loadSections())
              .catch(() => undefined);
          }}
        />
      ) : null}

      {phase === 2 ? (
        <Phase2
          sections={sections}
          expanded={expanded}
          openSub={openSub}
          extracted={extracted}
          busy={busy}
          actionError={actionError}
          actionInfo={actionInfo}
          onExpand={setExpanded}
          onOpenSub={setOpenSub}
          onSave={saveSection}
          onDraft={draftSection}
          onBack={() => persistPhase(1)}
          onNext={() => persistPhase(3)}
        />
      ) : null}

      {phase === 3 ? (
        <Phase3
          filledCount={filledCount}
          total={TOR_SECTION_ORDER.length}
          hitlReady={hitlReady}
          score={reviewScore}
          findings={reviewFindings}
          busy={reviewBusy}
          error={actionError}
          onBack={() => persistPhase(2)}
          onReview={async () => {
            setReviewBusy(true);
            setActionError(null);
            try {
              const response = await apiClient.post(`/projects/${projectId}/review`);
              const payload = unwrapData<{
                quality_score?: number;
                findings?: Record<string, unknown>[];
              }>(response);
              setReviewScore(payload.quality_score ?? null);
              setReviewFindings(
                (payload.findings || []).map((item) => toReviewFinding(item))
              );
            } catch (err: unknown) {
              setActionError(apiErrorMessage(err, "ตรวจสอบไม่สำเร็จ"));
            } finally {
              setReviewBusy(false);
            }
          }}
          onSubmit={async () => {
            try {
              await apiClient.post(`/projects/${projectId}/submit`);
              await persistPhase(4);
              router.push("/projects");
            } catch (err: unknown) {
              setActionError(apiErrorMessage(err, "ส่งขออนุมัติไม่สำเร็จ"));
            }
          }}
        />
      ) : null}

      {phase === 4 ? (
        <Phase4
          exporting={exporting}
          onBack={() => persistPhase(3)}
          onExport={async (format: "docx" | "pdf") => {
            setExporting(true);
            try {
              await apiClient.post(`/projects/${projectId}/export`);
              for (let attempt = 0; attempt < 30; attempt += 1) {
                const statusRes = await apiClient.get(
                  `/projects/${projectId}/export/status`
                );
                const status = unwrapData<{ status?: string }>(statusRes).status;
                if (status === "completed") break;
                if (status === "failed") {
                  return;
                }
                await new Promise((resolve) => setTimeout(resolve, 2000));
              }
              const download = await apiClient.get(
                `/projects/${projectId}/export/download/${format}`,
                { responseType: "blob" }
              );
              const url = URL.createObjectURL(download.data as Blob);
              const link = document.createElement("a");
              link.href = url;
              link.download = `TOR.${format}`;
              link.click();
              URL.revokeObjectURL(url);
            } finally {
              setExporting(false);
            }
          }}
        />
      ) : null}
    </div>
  );
}


function Phase2({
  sections,
  expanded,
  openSub,
  extracted,
  busy,
  actionError,
  actionInfo,
  onExpand,
  onOpenSub,
  onSave,
  onDraft,
  onBack,
  onNext,
}: Readonly<{
  sections: SectionPayload[];
  expanded: string;
  openSub: string;
  extracted: Record<string, unknown>;
  busy: boolean;
  actionError: string | null;
  actionInfo: string | null;
  onExpand: (key: string) => void;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
  onDraft: (key: string) => void;
  onBack: () => void;
  onNext: () => void;
}>) {
  return (
    <div className="gov-card">
      <h3 className="mb-1 text-navy">Phase 2: ร่างเนื้อหา TOR — 13 หมวดหลัก</h3>
      <p className="mb-4 text-xs text-muted-foreground">
        ข้อความจาก Phase 0 ถูกจัดเข้าหมวดแล้ว กดร่างด้วย AI (LM Studio) เพื่อขยายเป็นภาษาราชการ — หมวดกฎหมายต้องยืนยันโดยเจ้าหน้าที่
      </p>
      {busy ? <p className="mb-3 text-sm text-navy">กำลังร่างด้วย AI จากโมเดลในเครื่อง...</p> : null}
      {actionError ? (
        <p className="mb-3 text-sm text-destructive" role="alert">
          {actionError}
        </p>
      ) : null}
      {actionInfo ? <p className="mb-3 text-sm text-brand-green">{actionInfo}</p> : null}
      <div className="flex flex-col">
        {sections.map((section, index) => (
          <SectionCard
            key={section.key}
            section={section}
            index={index}
            last={index === sections.length - 1}
            expanded={expanded === section.key}
            openSub={openSub}
            extracted={extracted}
            busy={busy}
            onToggle={() => onExpand(expanded === section.key ? "" : section.key)}
            onOpenSub={onOpenSub}
            onSave={onSave}
            onDraft={onDraft}
          />
        ))}
      </div>
      <div className="mt-4 flex justify-between">
        <Button variant="secondary" onClick={onBack} data-testid="phase2-back">
          ย้อนกลับ
        </Button>
        <Button onClick={onNext} data-testid="phase2-next">
          ถัดไป: ทบทวน/อนุมัติ
        </Button>
      </div>
    </div>
  );
}

function SectionCard({
  section,
  index,
  last,
  expanded,
  openSub,
  extracted,
  busy,
  onToggle,
  onOpenSub,
  onSave,
  onDraft,
}: Readonly<{
  section: SectionPayload;
  index: number;
  last: boolean;
  expanded: boolean;
  openSub: string;
  extracted: Record<string, unknown>;
  busy: boolean;
  onToggle: () => void;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
  onDraft: (key: string) => void;
}>) {
  const baseFields = SECTION_FIELDS[section.key] || [
    { key: "body", label: section.title, type: "textarea" as const },
  ];
  const values = parseFields(section.content);
  const fields =
    values.body && !baseFields.some((item) => item.key === "body")
      ? [
          {
            key: "body",
            label: "เนื้อหาร่าง (จากเอกสาร/AI)",
            type: "textarea" as const,
          },
          ...baseFields,
        ]
      : baseFields;
  const [draft, setDraft] = useState(values);
  useEffect(() => {
    setDraft(parseFields(section.content));
  }, [section.content]);

  function suggested(mapField?: string) {
    if (!mapField) return "";
    return displayExtracted(extracted[mapField]);
  }

  return (
    <div className="flex gap-3.5">
      <div className="flex w-9 shrink-0 flex-col items-center">
        <div
          className={cn(
            "z-[1] flex h-[34px] w-[34px] items-center justify-center rounded-full border-2 text-[13px] font-extrabold",
            sectionCircleClass(section.filled, expanded)
          )}
        >
          {section.filled ? "✓" : index + 1}
        </div>
        {!last ? (
          <div className={cn("w-0.5 flex-1", section.filled ? "bg-brand-green" : "bg-gray-300")} />
        ) : null}
      </div>
      <div
        className={cn(
          "mb-3.5 flex-1 overflow-hidden rounded-[10px] border",
          expanded ? "border-crimson shadow-[0_4px_14px_rgba(196,30,58,0.12)]" : "border-gray-200"
        )}
      >
        <button
          type="button"
          className="flex w-full items-center justify-between bg-gray-50 px-4 py-3 text-left"
          onClick={onToggle}
        >
          <div>
            <h3 className="text-[14.5px] text-navy">
              หมวด {section.key.replace("s", "")}: {section.title}
            </h3>
            <p className="text-[11.5px] text-muted-foreground">
              {section.filled ? "กรอกแล้ว" : "ยังไม่กรอก"}
              {section.hitl ? " · ต้องให้เจ้าหน้าที่ยืนยัน" : ""}
            </p>
          </div>
          <span className="text-xs text-muted-foreground">{expanded ? "▴ ย่อ" : "▾ ขยาย"}</span>
        </button>
        {expanded ? (
          <div className="space-y-3 border-t p-4">
            {section.big ? (
              <ScopeSubsectionEditor
                subs={section.subs}
                openSub={openSub}
                onOpenSub={onOpenSub}
                onSave={onSave}
              />
            ) : (
              <StandardSectionFields
                fields={fields}
                draft={draft}
                extracted={extracted}
                suggested={suggested}
                onChange={(key, next) =>
                  setDraft((prev) => ({ ...prev, [key]: next }))
                }
              />
            )}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={busy}
                data-testid={`draft-ai-${section.key}`}
                onClick={() => onDraft(section.key)}
              >
                ร่างด้วย AI
              </Button>
                <Button
                  size="sm"
                  variant="outline"
                  data-testid={`save-section-${section.key}`}
                  onClick={() => onSave(section.key, serializeSectionDraft(draft), false)}
                >
                  บันทึกหมวดนี้
                </Button>
              {HITL_SECTIONS.includes(section.key) ? (
                <Button
                  size="sm"
                  data-testid={`hitl-confirm-${section.key}`}
                  onClick={() => onSave(section.key, serializeSectionDraft(draft), true)}
                >
                  เจ้าหน้าที่ยืนยันแล้ว
                </Button>
              ) : null}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function Phase3({
  filledCount,
  total,
  hitlReady,
  score,
  findings,
  busy,
  error,
  onBack,
  onReview,
  onSubmit,
}: Readonly<{
  filledCount: number;
  total: number;
  hitlReady: boolean;
  score: number | null;
  findings: ReviewFinding[];
  busy: boolean;
  error: string | null;
  onBack: () => void;
  onReview: () => Promise<void>;
  onSubmit: () => Promise<void>;
}>) {
  const pct = Math.round((filledCount / total) * 100);
  return (
    <div className="gov-card">
      <h3 className="mb-2 text-navy">Phase 3: ทบทวนและอนุมัติ</h3>
      <p className="text-sm">ความครบถ้วน: {filledCount}/{total} หมวด</p>
      <div className="my-2 h-2 overflow-hidden rounded bg-gray-200">
        <div
          className="h-full bg-gradient-to-r from-navy to-brand-orange-dark"
          style={{ width: `${pct}%` }}
        />
      </div>
      {pct < 100 ? (
        <CheckItem tone="warn" title="ยังกรอกไม่ครบทุกหมวด" detail="กลับไป Phase 2 เพื่อกรอกให้ครบ" />
      ) : (
        <CheckItem tone="pass" title="ข้อมูลครบถ้วนทุกหมวด พร้อมส่งทบทวน" />
      )}
      {hitlReady ? (
        <CheckItem tone="pass" title="หมวดกฎหมาย งบ งวดจ่าย ค่าปรับ เงื่อนไขอื่น ได้รับการยืนยัน" />
      ) : (
        <CheckItem tone="warn" title="ยังไม่ได้ยืนยันหมวด HITL" />
      )}
      {score != null ? (
        <CheckItem
          tone={score >= 70 ? "pass" : "warn"}
          title={`คะแนนคุณภาพจาก Rule Engine ${score}/100`}
        />
      ) : (
        <CheckItem tone="warn" title="ยังไม่ได้รันตรวจสอบ" detail="กดรัน Rule Engine เพื่อตรวจกฎหมาย ความครบถ้วน และความสอดคล้อง" />
      )}
      {findings.map((finding, index) => (
        <CheckItem
          key={`${finding.rule}-${index}`}
          tone={findingCheckTone(finding.severity)}
          title={finding.message}
          detail={[finding.section, finding.recommendation].filter(Boolean).join(" — ")}
        />
      ))}
      {error ? (
        <p className="mt-2 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <div className="mt-4 flex justify-between">
        <Button variant="secondary" onClick={onBack} data-testid="phase3-back">
          ย้อนกลับไปแก้ไข
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onReview} disabled={busy} data-testid="run-review">
            {busy ? "กำลังตรวจสอบ..." : "รัน Rule Engine"}
          </Button>
          <Button onClick={onSubmit} disabled={pct < 100 || !hitlReady || busy}>
            ส่งขออนุมัติ / สร้าง TOR
          </Button>
        </div>
      </div>
    </div>
  );
}

function Phase4({
  exporting,
  onBack,
  onExport,
}: Readonly<{
  exporting: boolean;
  onBack: () => void;
  onExport: (format: "docx" | "pdf") => Promise<void>;
}>) {
  return (
    <div className="gov-card space-y-3">
      <h3 className="text-navy">Phase 4: เผยแพร่</h3>
      <p className="text-sm text-muted-foreground">
        ส่งออก Word หรือ PDF ตามมาตรฐานราชการ (TH Sarabun, พ.ศ.) การอัปโหลดเข้าระบบ e-Bidding
        เป็นขั้นตอนของเจ้าหน้าที่นอกแอปนี้
      </p>
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onBack} data-testid="phase4-back">
          ย้อนกลับ
        </Button>
        <Button disabled={exporting} data-testid="export-docx" onClick={() => onExport("docx")}>
          ส่งออก Word
        </Button>
        <Button disabled={exporting} data-testid="export-pdf" onClick={() => onExport("pdf")}>
          ส่งออก PDF
        </Button>
      </div>
    </div>
  );
}

function ScopeSubsectionEditor({
  subs,
  openSub,
  onOpenSub,
  onSave,
}: Readonly<{
  subs: SectionPayload["subs"];
  openSub: string;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
}>) {
  const chips = subs || SCOPE_SUBSECTIONS.map((item) => ({
    ...item,
    content: "",
    filled: false,
  }));
  const openItem = (subs || []).find((sub) => sub.key === openSub);
  return (
    <>
      <p className="text-xs text-muted-foreground">
        หมวด 4 แบ่งเป็น {SCOPE_SUBSECTIONS.length} หัวข้อย่อย
      </p>
      <div className="flex flex-wrap gap-1.5">
        {chips.map((sub) => (
          <button
            key={sub.key}
            type="button"
            className={cn(
              "rounded-md border px-2.5 py-1 text-[11.5px] font-semibold",
              sub.filled
                ? "border-green-300 bg-green-50 text-green-800"
                : "border-gray-200 bg-gray-100"
            )}
            onClick={() => onOpenSub(openSub === sub.key ? "" : sub.key)}
          >
            {sub.key.replace("s4.", "4.")} {sub.title}
          </button>
        ))}
      </div>
      {openItem ? (
        <div className="rounded-lg border-l-[3px] border-navy bg-gray-50 p-3">
          <Label>{openItem.title}</Label>
          <Textarea
            className="mt-1"
            defaultValue={openItem.content}
            onBlur={(event) => onSave(openItem.key, event.target.value)}
          />
        </div>
      ) : null}
    </>
  );
}

function StandardSectionFields({
  fields,
  draft,
  extracted,
  suggested,
  onChange,
}: Readonly<{
  fields: SectionField[];
  draft: Record<string, string>;
  extracted: Record<string, unknown>;
  suggested: (mapField?: string) => string;
  onChange: (key: string, next: string) => void;
}>) {
  return (
    <>
      {fields.map((field) => {
        const value = draft[field.key] || suggested(field.mapField);
        const tag = field.mapField && extracted[field.mapField] ? "matched" : "partial";
        return (
          <div key={field.key}>
            <Label>{field.label}</Label>
            <SectionFieldControl
              field={field}
              value={value}
              onChange={(next) => onChange(field.key, next)}
            />
            {field.mapField ? (
              <MappingBox
                rows={[
                  {
                    field: field.mapField,
                    label: field.label,
                    value: suggested(field.mapField),
                    tag,
                  },
                ]}
              />
            ) : null}
          </div>
        );
      })}
    </>
  );
}

function SectionFieldControl({
  field,
  value,
  onChange,
}: Readonly<{
  field: SectionField;
  value: string;
  onChange: (next: string) => void;
}>) {
  if (field.type === "textarea") {
    return (
      <Textarea
        className="mt-1"
        value={value}
        maxLength={50000}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }
  if (field.type === "select") {
    return (
      <select
        className="mt-1 h-10 w-full rounded-md border px-3 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">เลือก</option>
        {(field.options || []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  return (
    <Input
      className="mt-1"
      type={field.type === "number" ? "text" : field.type}
      value={value}
      maxLength={2000}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}


