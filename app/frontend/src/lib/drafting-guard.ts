export const DRAFTING_PROJECT_KEY = "tor-drafting-project-id";

export type ArchiveDecision = "proceed" | "blocked" | "cancelled";

export function markDraftingProject(projectId: string): void {
  if (typeof sessionStorage === "undefined" || !projectId) return;
  sessionStorage.setItem(DRAFTING_PROJECT_KEY, projectId);
}

export function clearDraftingProject(projectId?: string): void {
  if (typeof sessionStorage === "undefined") return;
  if (projectId && sessionStorage.getItem(DRAFTING_PROJECT_KEY) !== projectId) {
    return;
  }
  sessionStorage.removeItem(DRAFTING_PROJECT_KEY);
}

export function isCurrentlyDrafting(projectId: string): boolean {
  if (typeof sessionStorage === "undefined") return false;
  return sessionStorage.getItem(DRAFTING_PROJECT_KEY) === projectId;
}

export function decideArchiveProject(
  projectId: string,
  projectName: string,
  confirmFn: (message: string) => boolean
): ArchiveDecision {
  if (isCurrentlyDrafting(projectId)) return "blocked";
  if (!confirmFn(`ลบโครงการ «${projectName}» ?`)) return "cancelled";
  return "proceed";
}
