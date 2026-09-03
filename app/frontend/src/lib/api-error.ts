/** Read FastAPI `{ error: { message } }` from an Axios-style failure. */

const NETWORK_CODES = new Set([
  "ERR_NETWORK",
  "ENOTFOUND",
  "ECONNREFUSED",
  "ERR_NAME_NOT_RESOLVED",
]);

export function networkFailureMessage(err: unknown): string | null {
  if (err instanceof DOMException && err.name === "AbortError") {
    return "ยกเลิกการสตรีมแล้ว";
  }
  if (!err || typeof err !== "object") {
    return null;
  }
  const record = err as { code?: string; message?: string; name?: string };
  if (record.name === "AbortError") {
    return "ยกเลิกการสตรีมแล้ว";
  }
  const blob = `${record.code || ""} ${record.message || ""}`;
  if (
    NETWORK_CODES.has(record.code || "") ||
    /failed to fetch|networkerror|err_name_not_resolved|enotfound|econnrefused/i.test(
      blob
    )
  ) {
    return "เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ — ตรวจ Docker และเครือข่ายเครื่อง";
  }
  return null;
}

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
  const network = networkFailureMessage(err);
  if (network) {
    return network;
  }
  const message = record.response?.data?.error?.message;
  return typeof message === "string" && message.trim() ? message : fallback;
}
