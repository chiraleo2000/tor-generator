import { ProjectType } from "./index";

/** Step 1: Project Information */
export interface Step1Data {
  project_name: string;
  ministry: string;
  budget: number | null;
  project_type: ProjectType;
  template_id: string | null;
  location: string;
  duration_days: number | null;
}

/** Step 2: Problem Description */
export interface Step2Data {
  description: string;
}

/** Step 3: Objectives */
export interface Step3Data {
  objectives: string[];
}

/** Step 4: Scope of Work */
export interface Step4Data {
  scope_items: { title: string; details: string }[];
  deliverables: string[];
}

/** Step 5: Vendor Qualifications */
export interface Step5Data {
  qualifications: string[];
  paid_up_capital: number | null;
}

/** Step 6: Budget & Payment */
export interface Step6Data {
  budget_breakdown: { item: string; amount: number }[];
  payment_schedule: { percentage: number; deliverable: string }[];
  penalty_rate: number | null;
  warranty: string;
  duration_days: number | null;
}

/** Step 7: Review (no user input, AI suggestions) */
export interface Step7Data {
  reviewed: boolean;
}

/** Step 8: Export */
export interface Step8Data {
  exported: boolean;
}

/** Union type of all step data */
export type StepData =
  | Step1Data
  | Step2Data
  | Step3Data
  | Step4Data
  | Step5Data
  | Step6Data
  | Step7Data
  | Step8Data;

/** Template option for selection in Step 1 */
export interface TemplateOption {
  id: string;
  name: string;
  industry: string;
  description?: string;
}

/** Validation result for a field */
export interface FieldValidation {
  field: string;
  message: string;
}
