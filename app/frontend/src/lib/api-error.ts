/** Read FastAPI `{ error: { message } }` from an Axios-style failure. */
export function apiErrorMessage(err: unknown, fallback: string): string {
  if (!err || typeof err !== "object") {
    return fallback;
  }
  const record = err as {
    code?: string;
    message?: string;
    response?: { data?: { error?: { message?: unknown } } };
  };
  if (record.code === "ECONNABORTED" || /timeout/i.test(record.message ?? "")) {
    return "หมดเวลารอโมเดล — วางข้อความที่มีรหัสช่อง เช่น (s1): แล้วกดวิเคราะห์อีกครั้ง";
  }
  const message = record.response?.data?.error?.message;
  return typeof message === "string" && message.trim() ? message : fallback;
}
