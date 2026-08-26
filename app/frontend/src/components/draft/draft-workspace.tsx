"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { StatusPill } from "@/components/brand/status-pill";
import { PhaseFlow } from "@/components/brand/phase-flow";
import { IntakeChatPanel } from "@/components/draft/intake-chat-panel";
import { Phase3Draft } from "@/components/draft/phase3-draft";
import { Phase4Review } from "@/components/draft/phase4-review";
import { Phase4Export } from "@/components/draft/phase4-export";
import type { ReviewSuggestion, SectionPayload } from "@/components/draft/draft-types";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { useProjectStore } from "@/stores/project-store";
import { TOR_SECTION_ORDER, isSectionFilled } from "@/lib/tor-sections";
import { toReviewFinding, type ReviewFinding } from "@/lib/review-findings";
import {
  markProjectReviewFinished,
  markProjectReviewStarted,
  shouldSkipProjectReview,
} from "@/lib/review-run-guard";
import { canSelectPhase, displayPhase, intakeUnlockedPhase } from "@/lib/phase-gate";
import { phaseLabelTh } from "@/lib/phase-handoff";
import { clearDraftingProject, markDraftingProject } from "@/lib/drafting-guard";
import {
  PHASE_FORWARD_CONFIRM,
  useConfirmPhase,
} from "@/components/draft/confirm-phase-dialog";

const EXPORT_WAIT_MESSAGE: Record<"failed" | "timeout", string> = {
  failed: "สร้างเอกสารไม่สำเร็จ",
  timeout: "สร้างเอกสารใช้เวลานานเกินไป กรุณาลองใหม่",
};

async function waitForExportReady(
  projectId: string
): Promise<"completed" | "failed" | "timeout"> {
  for (let attempt = 0; attempt < 66; attempt += 1) {
    const statusRes = await apiClient.get(`/projects/${projectId}/export/status`);
    const status = unwrapData<{ status?: string }>(statusRes).status;
    if (status === "completed") return "completed";
    if (status === "failed") return "failed";
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  return "timeout";
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
  const [reviewSuggestions, setReviewSuggestions] = useState<ReviewSuggestion[]>(
    []
  );
  const [reviewAssessment, setReviewAssessment] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionInfo, setActionInfo] = useState<string | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const hydrateGen = useRef(0);
  const { ask, dialog } = useConfirmPhase();

  const loadSections = useCallback(async () => {
    const response = await apiClient.get(`/projects/${projectId}/sections`);
    const payload = unwrapData<{ sections?: SectionPayload[] }>(response);
    setSections(payload.sections || []);
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    markDraftingProject(projectId);
    return () => clearDraftingProject(projectId);
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    const gen = hydrateGen.current + 1;
    hydrateGen.current = gen;
    setHydrated(false);
    fetchProject(projectId)
      .then((project) => {
        if (hydrateGen.current !== gen) return;
        const nextUnlocked = intakeUnlockedPhase(project);
        setUnlocked(nextUnlocked);
        setPhase((prev) => Math.max(prev, displayPhase(project.currentPhase ?? 0, nextUnlocked)));
        if (project.extractedFields) {
          setExtracted(project.extractedFields);
        }
        if (project.qualityScore != null) {
          setReviewScore(project.qualityScore);
        }
        const persisted = project.analysisJson?.review_findings;
        if (Array.isArray(persisted)) {
          setReviewFindings(
            persisted
              .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === "object")
              .map((item) => toReviewFinding(item))
          );
        }
        const assessment = project.analysisJson?.review_assessment;
        if (typeof assessment === "string" && assessment.trim()) {
          setReviewAssessment(assessment);
        }
        setHydrated(true);
      })
      .catch((err: unknown) => {
        setActionError(apiErrorMessage(err, "โหลดโครงการไม่สำเร็จ"));
        setHydrated(true);
      });
    loadSections().catch((err: unknown) =>
      setActionError(apiErrorMessage(err, "โหลดหมวดเอกสารไม่สำเร็จ"))
    );
  }, [projectId, fetchProject, loadSections]);

  async function persistPhase(
    next: number,
    nextUnlocked = unlocked,
    options?: { allowDowngrade?: boolean }
  ) {
    const allowDowngrade = options?.allowDowngrade ?? false;
    // Allow advancing when caller passes a higher unlock (e.g. after analyze).
    const effectiveUnlocked = Math.max(unlocked, nextUnlocked);
    const allowed = canSelectPhase(phase, effectiveUnlocked, next);
    if (!allowed) {
      setActionError(`ยังไป${phaseLabelTh(next)}ไม่ได้ — ทำขั้นก่อนหน้าให้ครบก่อน`);
      return;
    }
    // Resume/analyze must never yank the server backward (Phase 2 → 1 race).
    if (!allowDowngrade && next < phase) {
      setUnlocked(effectiveUnlocked);
      return;
    }
    const previousPhase = phase;
    const previousUnlocked = unlocked;
    setUnlocked(effectiveUnlocked);
    setPhase(next);
    setActionError(null);
    try {
      await apiClient.patch(`/projects/${projectId}/phase`, { phase: next });
    } catch (err: unknown) {
      setPhase(previousPhase);
      setUnlocked(previousUnlocked);
      setActionError(apiErrorMessage(err, "เปลี่ยนขั้นตอนไม่สำเร็จ"));
    }
  }

  async function requestStepperPhase(next: number) {
    if (!canSelectPhase(phase, unlocked, next)) {
      return;
    }
    if (next > phase && next !== 2) {
      const prompt =
        PHASE_FORWARD_CONFIRM[next] || `ไป${phaseLabelTh(next)}?`;
      const ok = await ask(prompt);
      if (!ok) return;
    }
    await persistPhase(next, unlocked, { allowDowngrade: next < phase });
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
    setActionInfo("รอคิวระบบอัจฉริยะ...");
    const requestId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `req-${Date.now()}`;
    const poll = window.setInterval(() => {
      apiClient
        .get(`/ai/queue/${requestId}`)
        .then((response) => {
          const payload = unwrapData<{ status?: string; position?: number }>(response);
          if (payload.status === "waiting") {
            const position = Number(payload.position || 0);
            setActionInfo(
              position > 0 ? `รอคิวประมวลผล (ลำดับ ${position})...` : "รอคิวระบบอัจฉริยะ..."
            );
          } else if (payload.status === "running") {
            setActionInfo("กำลังร่างด้วยระบบอัจฉริยะ...");
          }
        })
        .catch(() => undefined);
    }, 500);
    try {
      await apiClient.post(
        `/projects/${projectId}/draft-section`,
        { section_key: key },
        { headers: { "X-AI-Request-Id": requestId } }
      );
      await loadSections();
      setActionInfo("ร่างด้วยระบบอัจฉริยะสำเร็จ — ตรวจข้อความแล้วบันทึก");
    } catch (err: unknown) {
      setActionError(apiErrorMessage(err, "ร่างด้วยระบบอัจฉริยะไม่สำเร็จ"));
      setActionInfo(null);
    } finally {
      window.clearInterval(poll);
      setBusy(false);
    }
  }

  const runProjectReview = useCallback(async (force = false) => {
    if (shouldSkipProjectReview(projectId, force) || !projectId) {
      return;
    }
    markProjectReviewStarted(projectId);
    setReviewBusy(true);
    setActionError(null);
    setActionInfo("รอคิวระบบอัจฉริยะ...");
    const requestId =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `req-${Date.now()}`;
    const poll = window.setInterval(() => {
      apiClient
        .get(`/ai/queue/${requestId}`)
        .then((response) => {
          const payload = unwrapData<{ status?: string; position?: number }>(response);
          if (payload.status === "waiting") {
            const position = Number(payload.position || 0);
            setActionInfo(
              position > 0 ? `รอคิว (ลำดับ ${position})...` : "รอคิวระบบอัจฉริยะ..."
            );
          } else if (payload.status === "running") {
            setActionInfo("กำลังตรวจสอบ...");
          }
        })
        .catch(() => undefined);
    }, 500);
    let succeeded = false;
    try {
      const response = await apiClient.post(
        `/projects/${projectId}/review`,
        {},
        { headers: { "X-AI-Request-Id": requestId } }
      );
      const payload = unwrapData<{
        quality_score?: number;
        findings?: Record<string, unknown>[];
        overall_assessment?: string;
      }>(response);
      setReviewScore(payload.quality_score ?? null);
      setReviewFindings(
        (payload.findings || []).map((item) => toReviewFinding(item))
      );
      if (payload.overall_assessment) {
        setReviewAssessment(payload.overall_assessment);
      }
      try {
        const sugRes = await apiClient.get(`/projects/${projectId}/suggestions`);
        const sugPayload = unwrapData<{ items?: ReviewSuggestion[] }>(sugRes);
        setReviewSuggestions(sugPayload.items || []);
      } catch {
        setReviewSuggestions([]);
      }
      setActionInfo(null);
      succeeded = true;
    } catch (err: unknown) {
      setActionError(apiErrorMessage(err, "ตรวจสอบไม่สำเร็จ"));
      setActionInfo(null);
    } finally {
      window.clearInterval(poll);
      markProjectReviewFinished(projectId, succeeded);
      setReviewBusy(false);
    }
  }, [projectId]);

  async function exportDocument(format: "docx" | "pdf") {
    setExporting(true);
    setActionError(null);
    setActionInfo("กำลังสร้างเอกสาร...");
    try {
      await apiClient.post(`/projects/${projectId}/export`);
      const wait = await waitForExportReady(projectId);
      if (wait !== "completed") {
        setActionInfo(null);
        setActionError(EXPORT_WAIT_MESSAGE[wait]);
        return;
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
      setActionInfo("ดาวน์โหลดเอกสารแล้ว");
    } catch (err: unknown) {
      setActionInfo(null);
      setActionError(apiErrorMessage(err, "ส่งออกไม่สำเร็จ"));
    } finally {
      setExporting(false);
    }
  }

  const filledCount = sections.filter((s) => isSectionFilled(s)).length;

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
      {dialog}
      <div className="gov-card mb-5">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <p className="text-[15px] font-bold text-navy">
              {activeProject?.name || "โครงการใหม่"}
            </p>
            <p className="text-xs text-muted-foreground">
              เริ่มที่ขั้นที่ ๐ — อัปโหลดแล้วกดวิเคราะห์ จากนั้นดูผลขั้นที่ ๑ แล้วคุยต่อขั้นที่ ๒
            </p>
          </div>
          <StatusPill status={activeProject?.status || "draft"} />
        </div>
        <PhaseFlow
          current={phase}
          unlocked={unlocked}
          onSelect={(next) => {
            requestStepperPhase(next).catch(() => undefined);
          }}
        />
      </div>
      {actionError && phase < 3 ? (
        <p className="mb-3 text-sm text-destructive" role="alert">
          {actionError}
        </p>
      ) : null}

      {!hydrated ? (
        <p className="text-sm text-muted-foreground">กำลังโหลดขั้นตอนโครงการ...</p>
      ) : null}

      {hydrated && (phase === 0 || phase === 1 || phase === 2) ? (
        <IntakeChatPanel
          projectId={projectId}
          phase={phase}
          onAnalyzed={() => persistPhase(1, Math.max(unlocked, 2))}
          onEnterQa={() => persistPhase(2, Math.max(unlocked, 2))}
          onReady={() => {
            persistPhase(3, 3)
              .then(() => loadSections())
              .catch((err: unknown) =>
                setActionError(apiErrorMessage(err, "ไปขั้นตอนร่างไม่สำเร็จ"))
              );
          }}
        />
      ) : null}

      {hydrated && phase === 3 ? (
        <Phase3Draft
          projectId={projectId}
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
          onRefresh={() => {
            loadSections().catch(() => undefined);
          }}
          onBack={() => persistPhase(2, unlocked, { allowDowngrade: true })}
          onConfirm={async () => {
            if (filledCount < 13) {
              setActionError("ร่างให้ครบ ๑๓ หมวดก่อนเข้าทบทวน");
              return;
            }
            const ok = await ask(PHASE_FORWARD_CONFIRM[4]);
            if (!ok) return;
            setBusy(true);
            setActionError(null);
            try {
              if (unlocked < 4) {
                await apiClient.post(`/projects/${projectId}/intake/confirm-phase4`, {
                  confirm: true,
                });
              }
              await persistPhase(4, 4);
            } catch (err: unknown) {
              setActionError(apiErrorMessage(err, "ไปทบทวนไม่สำเร็จ — ตรวจการยืนยันแล้วลองใหม่"));
            } finally {
              setBusy(false);
            }
          }}
        />
      ) : null}

      {hydrated && phase === 4 ? (
        <>
          <Phase4Review
            projectId={projectId}
            sections={sections}
            filledCount={filledCount}
            total={TOR_SECTION_ORDER.length}
            score={reviewScore}
            findings={reviewFindings}
            suggestions={reviewSuggestions}
            assessment={reviewAssessment}
            busy={reviewBusy}
            error={actionError}
            onBack={() => persistPhase(3, unlocked, { allowDowngrade: true })}
            onReview={runProjectReview}
            onAsk={async (question) => {
              const res = await apiClient.post(`/projects/${projectId}/review/comment`, {
                content: question,
              });
              return unwrapData<{ reply?: string }>(res).reply || "";
            }}
            onSubmit={async () => {
              try {
                await apiClient.post(`/projects/${projectId}/submit`);
                router.push("/projects");
              } catch (err: unknown) {
                setActionError(apiErrorMessage(err, "ส่งขออนุมัติไม่สำเร็จ"));
              }
            }}
          />
          <Phase4Export
            exporting={exporting}
            error={actionError}
            info={actionInfo}
            onExport={exportDocument}
          />
        </>
      ) : null}
    </div>
  );
}
