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
import { analysisMappingReady } from "@/lib/intake-complete";

function isIntakeErrorMessage(text: string): boolean {
  return /ไม่สำเร็จ|ยังไม่ครบ|อย่างน้อย|ต้อง/.test(text);
}

type CoveragePayload = {
  coverage?: CoverageRow[];
  gap_questions?: string[];
  ready_to_compose?: boolean;
  has_material?: boolean;
  analyzed?: boolean;
};

const ANALYZE_HTTP_TIMEOUT_MS = 360_000;
const ANALYZE_POLL_MS = 2_500;
const ANALYZE_RECOVERY_MS = 180_000;


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
  const [uploadStatus, setUploadStatus] = useState<"idle" | "uploading" | "analyzing" | "done">(
    "idle"
  );
  const advancedRef = useRef(false);
  const { ask, dialog } = useConfirmPhase();
  const apiBase = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

  const refreshCoverage = useCallback(async () => {
    const response = await apiClient.get(`/projects/${projectId}/intake/coverage`);
    const payload = unwrapData<CoveragePayload>(response);
    setCoverage(payload.coverage || []);
    setGaps(payload.gap_questions || []);
    setReady(Boolean(payload.ready_to_compose));
    if (payload.has_material) setHasPack(true);
    return payload;
  }, [projectId]);

  const advanceAfterAnalyze = useCallback(async () => {
    if (advancedRef.current) return;
    advancedRef.current = true;
    setUploadStatus("done");
    await Promise.resolve(onAnalyzed());
  }, [onAnalyzed]);

  const pollUntilMapped = useCallback(
    async (maxMs: number) => {
      const deadline = Date.now() + maxMs;
      while (Date.now() < deadline) {
        if (advancedRef.current) return true;
        try {
          const payload = await refreshCoverage();
          const readyMapped = analysisMappingReady(payload);
          if (readyMapped) {
            await advanceAfterAnalyze();
            return true;
          }
        } catch {
          /* keep polling while backend may still be writing */
        }
        await new Promise((resolve) => window.setTimeout(resolve, ANALYZE_POLL_MS));
      }
      return false;
    },
    [advanceAfterAnalyze, refreshCoverage]
  );

  useEffect(() => {
    let live = true;
    refreshCoverage()
      .then(() => {
        if (!live) return;
        // Do NOT auto persistPhase(1) on mount — that raced and downgraded Phase 2→1.
        // Fresh analyze / pollUntilMapped call advanceAfterAnalyze explicitly.
      })
      .catch(() => {
        /* coverage loads after upload/paste */
      });
    return () => {
      live = false;
    };
  }, [refreshCoverage, phase, uploadStatus]);

  async function uploadFiles(files: FileList | null) {
    if (!files?.length) return;
    const names = Array.from(files).map((file) => file.name);
    setBusy(true);
    setUploadStatus("uploading");
    setMessage(null);
    setUploadedNames((prev) => [...prev, ...names]);
    try {
      const body = new FormData();
      for (const file of Array.from(files)) {
        body.append("files", file);
      }
      await apiClient.post(`/projects/${projectId}/intake/upload`, body);
      setHasPack(true);
      setMessage("อัปโหลดแล้ว — กดเริ่มวิเคราะห์เมื่อครบชุดเอกสาร");
    } catch (err: unknown) {
      setUploadedNames((prev) => prev.filter((name) => !names.includes(name)));
      setMessage(apiErrorMessage(err, "อัปโหลดไม่สำเร็จ"));
    } finally {
      setBusy(false);
      setUploadStatus("idle");
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
    advancedRef.current = false;
    setBusy(true);
    setUploadStatus("analyzing");
    setMessage(null);

    // Parallel poll: if HTTP dies but backend finishes, still leave Phase 0.
    const pollPromise = pollUntilMapped(ANALYZE_HTTP_TIMEOUT_MS + ANALYZE_RECOVERY_MS);

    try {
      if (draftText.trim().length >= 20) {
        await saveText();
      }
      await apiClient.post(
        `/projects/${projectId}/intake/analyze`,
        {},
        { timeout: ANALYZE_HTTP_TIMEOUT_MS }
      );
      const payload = await refreshCoverage();
      if (analysisMappingReady(payload)) {
        await advanceAfterAnalyze();
        return;
      }
      // Backend said OK but coverage not visible yet — brief poll then fail clearly.
      const recovered = await pollUntilMapped(30_000);
      if (recovered) return;
      setUploadStatus("idle");
      setMessage(
        "วิเคราะห์ยังไม่ครบ — ยังไม่มีตารางช่องจากเอกสาร กรุณาลองอีกครั้งหรือเพิ่มข้อความโครงการ"
      );
    } catch (err: unknown) {
      const recovered = await pollUntilMapped(ANALYZE_RECOVERY_MS);
      if (recovered) return;
      setUploadStatus("idle");
      setMessage(apiErrorMessage(err, "วิเคราะห์ไม่สำเร็จ — อัปโหลดหรือวางข้อความก่อน"));
    } finally {
      await pollPromise.catch(() => undefined);
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
          status={uploadStatus}
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
          ready={ready}
          busy={busy}
          message={message}
          isError={isError}
          onEnterQa={onEnterQa}
        />
      ) : null}
      {phase === 2 ? (
        <Phase2Qa
          projectId={projectId}
          coverage={coverage}
          ready={ready}
          busy={busy}
          message={message}
          isError={isError}
          apiBase={apiBase}
          onConfirmReady={() => {
            confirmReady().catch(() => undefined);
          }}
          onCoverage={(rows) => {
            setCoverage(rows);
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
