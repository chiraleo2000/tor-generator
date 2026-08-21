"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Phase0Upload } from "@/components/draft/phase0-upload";
import { Phase1Coverage, type CoverageRow } from "@/components/draft/phase1-coverage";
import { Phase2Qa } from "@/components/draft/phase2-qa";
import {
  PHASE_FORWARD_CONFIRM,
  useConfirmPhase,
} from "@/components/draft/confirm-phase-dialog";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";

function isIntakeErrorMessage(text: string): boolean {
  return /ไม่สำเร็จ|ยังไม่ครบ|อย่างน้อย|ต้อง/.test(text);
}

export function IntakeChatPanel({
  projectId,
  phase,
  onAnalyzed,
  onEnterQa,
  onReady,
}: Readonly<{
  projectId: string;
  phase: number;
  onAnalyzed: () => void;
  onEnterQa: () => void;
  onReady: () => void;
}>) {
  const [coverage, setCoverage] = useState<CoverageRow[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);
  const [ready, setReady] = useState(false);
  const [hasPack, setHasPack] = useState(false);
  const [draftText, setDraftText] = useState("");
  const [uploadedNames, setUploadedNames] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [fillingRefs, setFillingRefs] = useState(false);
  const filledRefsFor = useRef<string>("");
  const { ask, dialog } = useConfirmPhase();
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

  const refreshCoverage = useCallback(async () => {
    const response = await apiClient.get(`/projects/${projectId}/intake/coverage`);
    const payload = unwrapData<{
      coverage?: CoverageRow[];
      gap_questions?: string[];
      ready_to_compose?: boolean;
      has_material?: boolean;
      analyzed?: boolean;
    }>(response);
    setCoverage(payload.coverage || []);
    setGaps(payload.gap_questions || []);
    setReady(Boolean(payload.ready_to_compose));
    if (payload.has_material) setHasPack(true);
    return payload;
  }, [projectId]);

  useEffect(() => {
    refreshCoverage().catch(() => {
      /* coverage loads after upload/paste */
    });
  }, [refreshCoverage]);

  useEffect(() => {
    if (phase < 1) {
      filledRefsFor.current = "";
      return undefined;
    }
    if (filledRefsFor.current === projectId) return undefined;
    filledRefsFor.current = projectId;
    let cancelled = false;
    setFillingRefs(true);
    setMessage("กำลังดึงกฎระเบียบที่เกี่ยวข้อง...");
    apiClient
      .post(`/projects/${projectId}/intake/fill-references`)
      .then(() => {
        if (cancelled) return undefined;
        return refreshCoverage();
      })
      .then(() => {
        if (cancelled) return;
        setMessage("ดึงกฎระเบียบแล้ว — พร้อมไปขั้นถัดไปเมื่อข้อมูลข้อเท็จจริงครบ");
      })
      .catch(() => {
        if (!cancelled) setMessage(null);
      })
      .finally(() => {
        if (!cancelled) setFillingRefs(false);
      });
    return () => {
      cancelled = true;
    };
  }, [phase, projectId, refreshCoverage]);

  async function uploadFiles(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    setMessage(null);
    try {
      const body = new FormData();
      for (const file of Array.from(files)) {
        body.append("files", file);
      }
      await apiClient.post(`/projects/${projectId}/intake/upload`, body);
      setHasPack(true);
      setUploadedNames((prev) => [
        ...prev,
        ...Array.from(files).map((file) => file.name),
      ]);
      setMessage("อัปโหลดแล้ว — กดเริ่มวิเคราะห์เมื่อครบชุดเอกสาร (ยังไม่ประมวลผล)");
    } catch (err: unknown) {
      setMessage(apiErrorMessage(err, "อัปโหลดไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function saveText() {
    const content = draftText.trim();
    if (content.length < 20) {
      setMessage("วางข้อความร่างหรือรายละเอียดโครงการอย่างน้อย 20 ตัวอักษร");
      return false;
    }
    await apiClient.post(`/projects/${projectId}/intake/text`, { content });
    setHasPack(true);
    return true;
  }

  async function startAnalyze() {
    const confirmed = await ask(PHASE_FORWARD_CONFIRM[1]);
    if (!confirmed) return;
    setBusy(true);
    setMessage(null);
    try {
      if (draftText.trim().length >= 20) {
        await saveText();
      }
      await apiClient.post(`/projects/${projectId}/intake/analyze`);
      await refreshCoverage();
      onAnalyzed();
      setMessage("วิเคราะห์แล้ว — ดูผลใน Phase 1 แล้วไปสอบถามเพิ่มใน Phase 2");
    } catch (err: unknown) {
      setMessage(apiErrorMessage(err, "วิเคราะห์ไม่สำเร็จ — อัปโหลดหรือวางข้อความก่อน"));
    } finally {
      setBusy(false);
    }
  }

  async function confirmReady() {
    const confirmed = await ask(PHASE_FORWARD_CONFIRM[3]);
    if (!confirmed) return;
    setBusy(true);
    try {
      await apiClient.post(`/projects/${projectId}/intake/confirm-ready`, {
        confirm: true,
      });
      onReady();
    } catch (err: unknown) {
      setMessage(apiErrorMessage(err, "ยังไม่ครบช่องข้อเท็จจริงที่บังคับ หรือยังไม่ได้ยืนยัน"));
    } finally {
      setBusy(false);
    }
  }

  async function enterQa() {
    const confirmed = await ask(PHASE_FORWARD_CONFIRM[2]);
    if (!confirmed) return;
    onEnterQa();
  }

  const canStart = hasPack || draftText.trim().length >= 20;
  const isError = Boolean(message && isIntakeErrorMessage(message));

  return (
    <div className="space-y-4" data-testid="intake-chat-panel">
      {dialog}
      {phase === 0 ? (
        <Phase0Upload
          draftText={draftText}
          busy={busy}
          canStart={canStart}
          uploadedNames={uploadedNames}
          message={message}
          isError={isError}
          onDraftText={setDraftText}
          onBlurSave={() => {
            if (draftText.trim().length < 20) return;
            saveText().catch(() => {
              /* startAnalyze reports save failures */
            });
          }}
          onUpload={uploadFiles}
          onAnalyze={() => {
            startAnalyze().catch(() => {
              /* startAnalyze already sets message */
            });
          }}
        />
      ) : null}
      {phase === 1 ? (
        <Phase1Coverage
          coverage={coverage}
          gaps={gaps}
          fillingRefs={fillingRefs}
          ready={ready}
          busy={busy}
          message={message}
          isError={isError}
          onEnterQa={() => {
            enterQa().catch(() => undefined);
          }}
        />
      ) : null}
      {phase === 2 ? (
        <Phase2Qa
          projectId={projectId}
          coverage={coverage}
          ready={ready}
          busy={busy}
          fillingRefs={fillingRefs}
          message={message}
          isError={isError}
          apiBase={apiBase}
          onConfirmReady={() => {
            confirmReady().catch(() => undefined);
          }}
          onChatReady={() => {
            refreshCoverage().catch(() => {
              /* coverage refresh is best-effort after chat */
            });
          }}
        />
      ) : null}
    </div>
  );
}
