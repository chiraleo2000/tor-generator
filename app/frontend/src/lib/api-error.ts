/** Read FastAPI `{ error: { message } }` from an Axios-style failure. */
export function apiErrorMessage(err: unknown, fallback: string): string {
  if (!err || typeof err !== "object") {
    return fallback;
  }
  const response = (err as { response?: { data?: { error?: { message?: unknown } } } })
    .response;
  const message = response?.data?.error?.message;
  return typeof message === "string" && message.trim() ? message : fallback;
}
