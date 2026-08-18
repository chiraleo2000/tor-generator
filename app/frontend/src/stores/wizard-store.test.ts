import { beforeEach, describe, expect, it, vi } from "vitest";
import { useWizardStore } from "./wizard-store";

describe("wizard-store", () => {
  beforeEach(() => {
    useWizardStore.getState().reset();
  });

  it("ignores steps outside 1-8 and stores form data", () => {
    useWizardStore.getState().setStep(0);
    expect(useWizardStore.getState().currentStep).toBe(1);
    useWizardStore.getState().setStep(4);
    expect(useWizardStore.getState().currentStep).toBe(4);

    const listener = vi.fn();
    useWizardStore.getState().setAutoSaveListener(listener);
    useWizardStore.getState().setFormData(4, { scope: "งาน" });
    expect(useWizardStore.getState().formData[4]).toEqual({ scope: "งาน" });
    expect(useWizardStore.getState().isDirty).toBe(true);
    expect(listener).toHaveBeenCalledWith(4, { scope: "งาน" });

    listener.mockClear();
    useWizardStore.getState().setFormData(4, { scope: "กู้คืน" }, { skipAutoSave: true });
    expect(listener).not.toHaveBeenCalled();
  });

  it("tracks validation errors and save flags", () => {
    useWizardStore.getState().setValidationErrors(1, ["ต้องระบุชื่อ"]);
    useWizardStore.getState().setValidationErrors(1, ["ต้องระบุชื่อ"]);
    expect(useWizardStore.getState().validationErrors[1]).toEqual(["ต้องระบุชื่อ"]);
    useWizardStore.getState().clearValidationErrors(1);
    expect(useWizardStore.getState().validationErrors[1]).toBeUndefined();

    useWizardStore.getState().markDirty();
    useWizardStore.getState().setAutoSaving(true);
    useWizardStore.getState().setAutoSaveError("ล้มเหลว");
    useWizardStore.getState().markSaved();
    expect(useWizardStore.getState().isDirty).toBe(false);
    expect(useWizardStore.getState().autoSaveError).toBeNull();
  });

  it("resets form data when the project id changes", () => {
    useWizardStore.getState().setFormData(1, { project_name: "เก่า" }, { skipAutoSave: true });
    useWizardStore.getState().setProjectId("p1");
    expect(useWizardStore.getState().projectId).toBe("p1");
    useWizardStore.getState().setProjectId("p1");
    useWizardStore.getState().setFormData(1, { project_name: "ใหม่" }, { skipAutoSave: true });
    useWizardStore.getState().setProjectId("p2");
    expect(useWizardStore.getState().formData).toEqual({});
  });
});
