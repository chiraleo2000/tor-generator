"use client";

import * as React from "react";
import { useParams, useRouter } from "next/navigation";
import { ChevronLeft, ChevronRight, Sparkles, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWizardStore } from "@/stores/wizard-store";
import { useProjectStore } from "@/stores/project-store";
import { StepIndicator } from "@/components/wizard/step-indicator";
import { Step1ProjectInfo } from "@/components/wizard/step1-project-info";
import { Step2ProblemDescription } from "@/components/wizard/step2-problem-description";
import { Step3Objectives } from "@/components/wizard/step3-objectives";
import { Step4ScopeOfWork } from "@/components/wizard/step4-scope-of-work";
import { Step5Qualifications } from "@/components/wizard/step5-qualifications";
import { Step6BudgetPayment } from "@/components/wizard/step6-budget-payment";
import { Step7Review } from "@/components/wizard/step7-review";
import { Step8Export } from "@/components/wizard/step8-export";
import { SuggestionsPanel } from "@/components/wizard/suggestions-panel";
import { AutoSaveIndicator } from "@/components/wizard/auto-save-indicator";
import { useAutoSave } from "@/lib/use-auto-save";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { ORPHAN_SECTIONS, STEP_SECTION_MAP } from "@/lib/tor-sections";
import { toWizardApiPayload } from "@/lib/wizard-api";
import { isMeaningfulStepData } from "@/lib/wizard-hydrate";

export function WizardPageContent() {
  const params = useParams();
  const router = useRouter();
  const projectIdParam = (params.id as string) || "";
  const stepParam = Number.parseInt(params.step as string, 10);
  const step = Number.isNaN(stepParam) ? 1 : Math.max(1, Math.min(8, stepParam));

  const {
    currentStep,
    formData,
    setStep,
    setFormData,
    setProjectId,
    projectId,
    validationErrors,
  } = useWizardStore();
  const { fetchProject } = useProjectStore();
  const { retrySave } = useAutoSave();
  const [hydrating, setHydrating] = React.useState(() => {
    const existing = useWizardStore.getState();
    return !(
      existing.projectId === projectIdParam &&
      isMeaningfulStepData(1, existing.formData[1])
    );
  });
  const [drafting, setDrafting] = React.useState(false);

  React.useEffect(() => {
    if (projectIdParam) {
      setProjectId(projectIdParam);
    }
  }, [projectIdParam, setProjectId]);

  React.useEffect(() => {
    if (step !== currentStep) {
      setStep(step);
    }
  }, [step, currentStep, setStep]);

  React.useEffect(() => {
    let cancelled = false;
    async function hydrate() {
      if (!projectIdParam) {
        setHydrating(false);
        return;
      }
      const existing = useWizardStore.getState();
      if (
        existing.projectId === projectIdParam &&
        isMeaningfulStepData(1, existing.formData[1])
      ) {
        setHydrating(false);
        return;
      }
      setHydrating(true);
      try {
        await fetchProject(projectIdParam);
        for (let n = 1; n <= 8; n += 1) {
          try {
            const response = await apiClient.get(
              `/projects/${projectIdParam}/steps/${n}`
            );
            const payload = unwrapData<{ form_data?: unknown }>(response);
            const formData = payload.form_data;
            if (isMeaningfulStepData(n, formData) && !cancelled) {
              setFormData(n, formData, { skipAutoSave: true });
            }
          } catch {
            // empty step is fine
          }
        }
        if (!cancelled) {
          const project = useProjectStore.getState().activeProject;
          const step1 = useWizardStore.getState().formData[1] as
            | { project_name?: string }
            | undefined;
          if (project && !step1?.project_name?.trim()) {
            setFormData(
              1,
              {
                project_name: project.name,
                ministry: project.ministry,
                budget: project.budget,
                project_type: project.projectType,
                template_id: project.templateId,
                location: "",
                duration_days: null,
              },
              { skipAutoSave: true }
            );
          }
        }
      } finally {
        if (!cancelled) setHydrating(false);
      }
    }
    hydrate();
    return () => {
      cancelled = true;
    };
  }, [projectIdParam, fetchProject, setFormData]);

  const orphansDrafted = React.useRef(false);

  React.useEffect(() => {
    if (step !== 7 || !projectIdParam || hydrating) return;
    if (orphansDrafted.current) return;
    orphansDrafted.current = true;
    let cancelled = false;
    async function draftOrphans() {
      setDrafting(true);
      try {
        const snapshot = useWizardStore.getState().formData;
        const step1 = snapshot[1] as { location?: string } | undefined;
        const step7 = (snapshot[7] as Record<string, string>) || {};
        for (const section of ORPHAN_SECTIONS) {
          const existing =
            section === "s7"
              ? step1?.location || step7.s7
              : step7[section];
          if (existing && String(existing).trim()) continue;
          const mappedStep = Object.entries(STEP_SECTION_MAP).find(([, keys]) =>
            keys.includes(section)
          )?.[0];
          if (!mappedStep) continue;
          try {
            await apiClient.post(
              `/projects/${projectIdParam}/steps/${mappedStep}/draft`,
              { target_section: section }
            );
          } catch {
            // continue remaining sections
          }
          if (cancelled) return;
        }
        await apiClient.post(`/projects/${projectIdParam}/review`);
      } finally {
        if (!cancelled) setDrafting(false);
      }
    }
    draftOrphans();
    return () => {
      cancelled = true;
    };
  }, [step, projectIdParam, hydrating]);

  const completedSteps = React.useMemo(() => {
    const completed = new Set<number>();
    for (let i = 1; i < step; i++) {
      const hasData = formData[i] !== undefined && formData[i] !== null;
      const hasNoErrors =
        !validationErrors[i] || validationErrors[i].length === 0;
      if (hasData && hasNoErrors) {
        completed.add(i);
      }
    }
    return completed;
  }, [formData, validationErrors, step]);

  const canGoForward =
    !validationErrors[step] || validationErrors[step].length === 0;

  const basePath = projectIdParam
    ? `/projects/${projectIdParam}/wizard/`
    : "/wizard/";

  const goToStep = (targetStep: number) => {
    if (targetStep >= 1 && targetStep <= 8) {
      router.push(basePath + targetStep);
    }
  };

  const handleDraftCurrent = async () => {
    if (!projectId) return;
    setDrafting(true);
    try {
      const keys = STEP_SECTION_MAP[step] || [];
      for (const target of keys) {
        await apiClient.post(`/projects/${projectId}/steps/${step}/draft`, {
          target_section: target,
          additional_context: toWizardApiPayload(step, formData[step]),
        });
      }
    } finally {
      setDrafting(false);
    }
  };

  const renderStepContent = () => {
    switch (step) {
      case 1:
        return <Step1ProjectInfo />;
      case 2:
        return <Step2ProblemDescription />;
      case 3:
        return <Step3Objectives />;
      case 4:
        return <Step4ScopeOfWork />;
      case 5:
        return <Step5Qualifications />;
      case 6:
        return <Step6BudgetPayment />;
      case 7:
        return <Step7Review />;
      case 8:
        return <Step8Export />;
      default:
        return null;
    }
  };

  const isStep7 = step === 7;

  if (!projectIdParam) {
    return (
      <div className="max-w-xl mx-auto text-center py-16 space-y-4">
        <p>กรุณาสร้างหรือเลือกโครงการจากแดชบอร์ดก่อนเริ่มวิซาร์ด</p>
        <Button onClick={() => router.push("/projects")}>ไปที่แดชบอร์ด</Button>
      </div>
    );
  }

  if (hydrating) {
    return (
      <div
        className="flex justify-center py-20 text-muted-foreground gap-2"
        data-testid="wizard-loading"
      >
        <Loader2 className="h-5 w-5 animate-spin" />
        กำลังโหลดข้อมูลโครงการ...
      </div>
    );
  }

  return (
    <div
      className={isStep7 ? "max-w-7xl mx-auto" : "max-w-4xl mx-auto"}
      data-testid="wizard-page"
    >
      <StepIndicator
        currentStep={step}
        validationErrors={validationErrors}
        completedSteps={completedSteps}
        onStepClick={goToStep}
      />

      <div className="flex justify-end mb-2 gap-2">
        {step >= 2 && step <= 7 && (
          <Button
            variant="outline"
            size="sm"
            onClick={handleDraftCurrent}
            disabled={drafting}
          >
            {drafting ? (
              <Loader2 className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4 mr-1" />
            )}
            ร่างด้วย AI
          </Button>
        )}
        <AutoSaveIndicator onRetry={retrySave} />
      </div>

      {isStep7 ? (
        <div className="mb-6 flex flex-col gap-4 lg:flex-row">
          <div className="min-w-0 flex-1 rounded-lg border bg-card p-4 sm:p-6">
            {drafting && (
              <p className="text-sm text-muted-foreground mb-3">
                กำลังร่างหัวข้อที่ยังว่าง และตรวจสอบความสอดคล้อง...
              </p>
            )}
            {renderStepContent()}
          </div>
          <div className="w-full shrink-0 overflow-hidden rounded-lg border bg-card lg:w-[320px] lg:max-h-[calc(100vh-180px)] lg:sticky lg:top-20">
            <SuggestionsPanel />
          </div>
        </div>
      ) : (
        <div className="mb-6 rounded-lg border bg-card p-4 sm:p-6">{renderStepContent()}</div>
      )}

      {validationErrors[step] && validationErrors[step].length > 0 && (
        <div
          className="mb-4 rounded-md border border-destructive/50 bg-destructive/10 p-3"
          role="alert"
        >
          <p className="text-sm font-medium text-destructive mb-1">
            กรุณาแก้ไขข้อมูลดังต่อไปนี้:
          </p>
          <ul className="text-sm text-destructive list-disc list-inside">
            {validationErrors[step].map((err: string) => (
              <li key={err}>{err}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex justify-between">
        <Button
          type="button"
          variant="outline"
          onClick={() => goToStep(step - 1)}
          disabled={step === 1}
          data-testid="wizard-back"
        >
          <ChevronLeft className="h-4 w-4 mr-1" />
          ย้อนกลับ
        </Button>
        <Button
          type="button"
          onClick={() => goToStep(step + 1)}
          disabled={!canGoForward || step === 8}
          data-testid="wizard-next"
        >
          ถัดไป
          <ChevronRight className="h-4 w-4 ml-1" />
        </Button>
      </div>
    </div>
  );
}
