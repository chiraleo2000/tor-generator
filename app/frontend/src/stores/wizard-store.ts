import { create } from 'zustand';

export interface SetFormDataOptions {
  /** If true, skip triggering auto-save (used when restoring from localStorage) */
  skipAutoSave?: boolean;
}

export interface WizardState {
  currentStep: number;
  formData: Record<number, unknown>;
  validationErrors: Record<number, string[]>;
  isDirty: boolean;
  isAutoSaving: boolean;
  autoSaveError: string | null;
  projectId: string | null;

  /** Auto-save change listener — set externally by useAutoSave hook */
  _autoSaveListener: ((step: number, data: unknown) => void) | null;

  setStep: (step: number) => void;
  setFormData: (step: number, data: unknown, options?: SetFormDataOptions) => void;
  setValidationErrors: (step: number, errors: string[]) => void;
  clearValidationErrors: (step: number) => void;
  markDirty: () => void;
  markSaved: () => void;
  setAutoSaving: (saving: boolean) => void;
  setAutoSaveError: (error: string | null) => void;
  setProjectId: (id: string) => void;
  setAutoSaveListener: (listener: ((step: number, data: unknown) => void) | null) => void;
  reset: () => void;
}

export const useWizardStore = create<WizardState>()((set, get) => ({
  currentStep: 1,
  formData: {},
  validationErrors: {},
  isDirty: false,
  isAutoSaving: false,
  autoSaveError: null,
  projectId: null,
  _autoSaveListener: null,

  setStep: (step: number) => {
    if (step >= 1 && step <= 8) {
      set({ currentStep: step });
    }
  },

  setFormData: (step: number, data: unknown, options?: SetFormDataOptions) => {
    set((state) => ({
      formData: { ...state.formData, [step]: data },
      isDirty: true,
    }));

    // Notify auto-save listener (unless explicitly skipped, e.g. during restore)
    if (!options?.skipAutoSave) {
      const listener = get()._autoSaveListener;
      if (listener) {
        listener(step, data);
      }
    }
  },

  setValidationErrors: (step: number, errors: string[]) => {
    const current = get().validationErrors[step];
    if (
      current?.length === errors.length &&
      current.every((item, index) => item === errors[index])
    ) {
      return;
    }
    set((state) => ({
      validationErrors: { ...state.validationErrors, [step]: errors },
    }));
  },

  clearValidationErrors: (step: number) => {
    set((state) => {
      const { [step]: _, ...rest } = state.validationErrors;
      return { validationErrors: rest };
    });
  },

  markDirty: () => {
    set({ isDirty: true });
  },

  markSaved: () => {
    set({ isDirty: false, isAutoSaving: false, autoSaveError: null });
  },

  setAutoSaving: (saving: boolean) => {
    set({ isAutoSaving: saving });
  },

  setAutoSaveError: (error: string | null) => {
    set({ autoSaveError: error });
  },

  setProjectId: (id: string) => {
    const prev = get().projectId;
    if (prev === id) return;
    set({
      projectId: id,
      formData: prev ? {} : get().formData,
      validationErrors: prev ? {} : get().validationErrors,
      isDirty: false,
      autoSaveError: null,
    });
  },

  setAutoSaveListener: (listener: ((step: number, data: unknown) => void) | null) => {
    if (get()._autoSaveListener === listener) return;
    set({ _autoSaveListener: listener });
  },

  reset: () => {
    set({
      currentStep: 1,
      formData: {},
      validationErrors: {},
      isDirty: false,
      isAutoSaving: false,
      autoSaveError: null,
      projectId: null,
      _autoSaveListener: null,
    });
  },
}));
