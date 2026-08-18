/**
 * Configuration for the 8-step TOR Drafting Wizard.
 * Defines step labels, descriptions, and validation requirements.
 */

export interface WizardStepConfig {
  step: number;
  label: string;
  description: string;
  requiredFields: string[];
}

export const WIZARD_STEPS: WizardStepConfig[] = [
  {
    step: 1,
    label: "ข้อมูลโครงการ",
    description: "ชื่อโครงการ กระทรวง งบประมาณ ประเภท และแม่แบบ",
    requiredFields: ["projectName", "ministry", "budget", "projectType"],
  },
  {
    step: 2,
    label: "หลักการและเหตุผล",
    description: "คำอธิบายปัญหาและบริบทความเป็นมา",
    requiredFields: ["problemDescription"],
  },
  {
    step: 3,
    label: "วัตถุประสงค์",
    description: "วัตถุประสงค์ของโครงการ (SMART format)",
    requiredFields: ["objectives"],
  },
  {
    step: 4,
    label: "ขอบเขตงาน",
    description: "ขอบเขตของงานและรายการส่งมอบ",
    requiredFields: ["scope"],
  },
  {
    step: 5,
    label: "คุณสมบัติผู้เสนอราคา",
    description: "คุณสมบัติและทุนจดทะเบียนของผู้เสนอราคา",
    requiredFields: ["qualifications"],
  },
  {
    step: 6,
    label: "งบประมาณและการจ่ายเงิน",
    description: "รายละเอียดงบประมาณ งวดงาน และอัตราค่าปรับ",
    requiredFields: ["budgetBreakdown", "paymentSchedule"],
  },
  {
    step: 7,
    label: "ตรวจสอบและข้อเสนอแนะ",
    description: "ตรวจสอบ TOR ฉบับรวมและข้อเสนอแนะจาก AI",
    requiredFields: [],
  },
  {
    step: 8,
    label: "ส่งออก",
    description: "ส่งออกเอกสาร TOR เป็น Word หรือ PDF",
    requiredFields: [],
  },
];

export const TOTAL_STEPS = WIZARD_STEPS.length;

/**
 * Calculate completion percentage based on completed steps.
 */
export function calculateCompletionPercentage(
  formData: Record<number, unknown>,
  validationErrors: Record<number, string[]>
): number {
  let completedSteps = 0;

  for (const stepConfig of WIZARD_STEPS) {
    const stepData = formData[stepConfig.step];
    const errors = validationErrors[stepConfig.step];
    const hasData = stepData !== undefined && stepData !== null;
    const hasNoErrors = !errors || errors.length === 0;

    if (hasData && hasNoErrors) {
      completedSteps++;
    }
  }

  return Math.round((completedSteps / TOTAL_STEPS) * 100);
}

/**
 * Determine if a step is valid to proceed forward.
 * Steps 7 and 8 (Review, Export) have no required fields so are always passable.
 */
export function isStepValid(
  step: number,
  formData: Record<number, unknown>,
  validationErrors: Record<number, string[]>
): boolean {
  const stepConfig = WIZARD_STEPS.find((s) => s.step === step);
  if (!stepConfig) return false;

  // Steps with no required fields are always valid for navigation
  if (stepConfig.requiredFields.length === 0) return true;

  // Check that data exists for this step
  const stepData = formData[step];
  if (!stepData) return false;

  // Check no validation errors exist
  const errors = validationErrors[step];
  if (errors && errors.length > 0) return false;

  return true;
}

/**
 * Determine the status of each step for the indicator.
 */
export type StepStatus = "completed" | "current" | "upcoming" | "error";

export function getStepStatus(
  stepNumber: number,
  currentStep: number,
  formData: Record<number, unknown>,
  validationErrors: Record<number, string[]>
): StepStatus {
  if (stepNumber === currentStep) return "current";

  const errors = validationErrors[stepNumber];
  if (errors && errors.length > 0) return "error";

  const hasData = formData[stepNumber] !== undefined && formData[stepNumber] !== null;
  if (hasData && (!errors || errors.length === 0) && stepNumber < currentStep) {
    return "completed";
  }

  return "upcoming";
}
