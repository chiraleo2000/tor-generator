/** Decide whether persisted wizard step JSON should replace local defaults. */
export function isMeaningfulStepData(step: number, data: unknown): boolean {
  if (!data || typeof data !== "object") return false;
  const obj = data as Record<string, unknown>;
  if (Object.keys(obj).length === 0) return false;
  if (step === 2) {
    return typeof obj.description === "string" && Boolean(obj.description.trim());
  }
  if (step === 3) {
    return (
      Array.isArray(obj.objectives) &&
      obj.objectives.some((item) => String(item).trim())
    );
  }
  if (step === 4) {
    const items = obj.scope_items as { title?: string }[] | undefined;
    const deliverables = obj.deliverables as string[] | undefined;
    return Boolean(
      items?.some((item) => item.title?.trim()) ||
        deliverables?.some((item) => item.trim())
    );
  }
  if (step === 5) {
    return (
      Array.isArray(obj.qualifications) &&
      obj.qualifications.some((item) => String(item).trim())
    );
  }
  if (step === 6) {
    const breakdown = obj.budget_breakdown as
      | { item?: string; amount?: number }[]
      | undefined;
    return Boolean(
      breakdown?.some((item) => item.item?.trim() && (item.amount || 0) > 0)
    );
  }
  if (step === 7) {
    return Object.values(obj).some(
      (value) => typeof value === "string" && value.trim()
    );
  }
  if (step === 8) return obj.exported === true;
  return true;
}
