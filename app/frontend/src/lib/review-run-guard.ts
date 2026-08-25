/** Module-level lock so remounts do not start a second Rule Engine run. */

const inFlightIds = new Set<string>();
const doneIds = new Set<string>();

export function resetReviewRunGuard(): void {
  inFlightIds.clear();
  doneIds.clear();
}

export function shouldSkipProjectReview(projectId: string | null, force: boolean): boolean {
  if (!projectId) {
    return true;
  }
  if (force) {
    return false;
  }
  return inFlightIds.has(projectId) || doneIds.has(projectId);
}

export function markProjectReviewStarted(projectId: string): void {
  inFlightIds.add(projectId);
}

export function markProjectReviewFinished(projectId: string, succeeded: boolean): void {
  if (succeeded) {
    doneIds.add(projectId);
  }
  inFlightIds.delete(projectId);
}
