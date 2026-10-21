"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";

interface Summary {
  requests: number;
  prompt_tokens: number;
  completion_tokens: number;
  cache_creation_input_tokens: number;
  cache_read_input_tokens: number;
  total_tokens: number;
  cost_usd: number;
  calls_per_hour: number;
  by_user: Array<{ key: string; requests: number; tokens: number; cost_usd: number }>;
  by_model: Array<{ key: string; requests: number; tokens: number; cost_usd: number }>;
}

interface Bucket {
  start: string;
  requests: number;
  tokens: number;
  cost_usd: number;
}

interface AlertItem {
  id: string;
  title: string;
  severity: string;
  rule_id: string;
  subject_key: string;
  open: boolean;
  detail: Record<string, unknown>;
}

interface Infra {
  status: string;
  services: Record<string, string>;
  rate_limit: { limit_per_minute: number; redis: string; active_keys: number; highest_count: number };
  admission: { waiting: number | null; wait_p95_ms: number | null; queues: Array<{ name: string; waiting: number }> };
}

interface RateRow {
  provider: string;
  model: string;
  input_per_million: number;
  output_per_million: number;
  cache_write_per_million: number;
  cache_read_per_million: number;
}

interface UsageEvent {
  id: string;
  provider: string;
  model: string;
  task: string;
  total_tokens: number;
  cost_usd: number;
  status: string;
}

const EMPTY_SUMMARY: Summary = {
  requests: 0,
  prompt_tokens: 0,
  completion_tokens: 0,
  cache_creation_input_tokens: 0,
  cache_read_input_tokens: 0,
  total_tokens: 0,
  cost_usd: 0,
  calls_per_hour: 0,
  by_user: [],
  by_model: [],
};

export default function AdminUsagePage() {
  const [hours, setHours] = useState(24);
  const [summary, setSummary] = useState<Summary>(EMPTY_SUMMARY);
  const [buckets, setBuckets] = useState<Bucket[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [openCount, setOpenCount] = useState(0);
  const [infra, setInfra] = useState<Infra | null>(null);
  const [rates, setRates] = useState<RateRow[]>([]);
  const [events, setEvents] = useState<UsageEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const load = useCallback(async (windowHours: number) => {
    const start = new Date(Date.now() - windowHours * 3600 * 1000).toISOString();
    const query = `start=${encodeURIComponent(start)}`;
    const grain = windowHours > 48 ? "day" : "hour";
    const [summaryRes, seriesRes, alertRes, infraRes, priceRes, eventRes] = await Promise.all([
      apiClient.get(`/admin/usage/summary?${query}`),
      apiClient.get(`/admin/usage/timeseries?${query}&grain=${grain}`),
      apiClient.get("/admin/usage/alerts"),
      apiClient.get("/admin/usage/infra"),
      apiClient.get("/admin/usage/pricing"),
      apiClient.get(`/admin/usage/events?${query}&limit=10`),
    ]);
    setSummary(unwrapData<Summary>(summaryRes));
    setBuckets(unwrapData<{ buckets: Bucket[] }>(seriesRes).buckets || []);
    const alertPayload = unwrapData<{ open_count: number; items: AlertItem[] }>(alertRes);
    setAlerts(alertPayload.items || []);
    setOpenCount(alertPayload.open_count || 0);
    setInfra(unwrapData<Infra>(infraRes));
    setRates(unwrapData<{ rates: RateRow[] }>(priceRes).rates || []);
    setEvents(unwrapData<{ items: UsageEvent[] }>(eventRes).items || []);
  }, []);

  useEffect(() => {
    load(hours).catch((err: unknown) => setError(apiErrorMessage(err, "โหลดข้อมูลการใช้งานไม่สำเร็จ")));
  }, [hours, load]);

  async function acknowledge(id: string) {
    setError(null);
    try {
      await apiClient.post(`/admin/usage/alerts/${id}/ack`);
      setStatus("รับทราบการแจ้งเตือนแล้ว");
      await load(hours);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "รับทราบไม่สำเร็จ"));
    }
  }

  function updateRate(
    index: number,
    field: "input_per_million" | "output_per_million" | "cache_write_per_million" | "cache_read_per_million",
    value: string
  ) {
    setRates((current) =>
      current.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: Number(value) } : row
      )
    );
  }

  async function savePricing() {
    setError(null);
    try {
      await apiClient.put("/admin/usage/pricing", { rates });
      setStatus("บันทึกราคาแล้ว");
      await load(hours);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "บันทึกราคาไม่สำเร็จ"));
    }
  }

  const maxRequests = Math.max(1, ...buckets.map((bucket) => bucket.requests));

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="admin-usage-page">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-extrabold text-navy">การใช้งานระบบ</h1>
        <div className="flex gap-2">
          <Button type="button" variant={hours === 24 ? "default" : "outline"} data-testid="usage-range-24" onClick={() => setHours(24)}>
            24 ชั่วโมง
          </Button>
          <Button type="button" variant={hours === 168 ? "default" : "outline"} data-testid="usage-range-168" onClick={() => setHours(168)}>
            7 วัน
          </Button>
        </div>
      </div>
      {error ? (
        <p className="rounded-md border border-destructive/50 p-3 text-sm text-destructive" data-testid="usage-error" role="alert">
          {error}
        </p>
      ) : null}
      {status ? (
        <p className="text-sm text-navy" data-testid="usage-status">
          {status}
        </p>
      ) : null}

      <section className="gov-card space-y-3" data-testid="admin-usage-alerts">
        <h2 className="font-bold text-navy">การแจ้งเตือน ({openCount})</h2>
        {alerts.length === 0 ? <p data-testid="usage-alerts-empty">ไม่มีการแจ้งเตือน</p> : null}
        <ul className="space-y-2">
          {alerts.map((alert) => (
            <li key={alert.id} className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2" data-testid="usage-alert">
              <div>
                <p className="font-medium">{alert.title}</p>
                <p className="text-xs text-muted-foreground">
                  {alert.severity} · {alert.rule_id} · {alert.subject_key}
                </p>
              </div>
              {alert.open ? (
                <Button type="button" size="sm" data-testid={`usage-alert-ack-${alert.id}`} onClick={() => { void acknowledge(alert.id); }}>
                  รับทราบ
                </Button>
              ) : (
                <span className="text-xs text-muted-foreground">รับทราบแล้ว</span>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section className="grid gap-3 sm:grid-cols-3" data-testid="admin-usage-kpis">
        <Kpi label="คำขอ" value={String(summary.requests)} testId="usage-kpi-requests" />
        <Kpi label="โทเคนเข้า" value={String(summary.prompt_tokens)} testId="usage-kpi-prompt" />
        <Kpi label="โทเคนออก" value={String(summary.completion_tokens)} testId="usage-kpi-completion" />
        <Kpi label="แคชเขียน" value={String(summary.cache_creation_input_tokens)} testId="usage-kpi-cache-write" />
        <Kpi label="แคชอ่าน" value={String(summary.cache_read_input_tokens)} testId="usage-kpi-cache-read" />
        <Kpi label="ค่าใช้จ่าย (USD)" value={summary.cost_usd.toFixed(4)} testId="usage-kpi-cost" />
        <Kpi label="ครั้งต่อชั่วโมง" value={String(summary.calls_per_hour)} testId="usage-kpi-rate" />
        <Kpi label="โทเคนรวม" value={String(summary.total_tokens)} testId="usage-kpi-total" />
      </section>

      <section className="gov-card space-y-3" data-testid="admin-usage-frequency">
        <h2 className="font-bold text-navy">ความถี่</h2>
        <div className="flex h-24 items-end gap-1">
          {buckets.map((bucket) => (
            <div
              key={bucket.start}
              data-testid="usage-bucket"
              title={`${bucket.start} ${bucket.requests}`}
              className="w-2 bg-navy"
              style={{ height: `${Math.max(4, (bucket.requests / maxRequests) * 96)}px` }}
            />
          ))}
        </div>
        <p className="text-sm text-muted-foreground" data-testid="usage-top-model">
          โมเดลที่ใช้มาก: {summary.by_model[0]?.key || "—"}
        </p>
        <p className="text-sm text-muted-foreground" data-testid="usage-top-user">
          ผู้ใช้ที่ใช้มาก: {summary.by_user[0]?.key || "—"}
        </p>
      </section>

      <section className="gov-card space-y-2" data-testid="admin-usage-infra">
        <h2 className="font-bold text-navy">โครงสร้างพื้นฐาน ({infra?.status || "—"})</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(infra?.services || {}).map(([name, state]) => (
            <span key={name} className="rounded border px-2 py-1 text-xs" data-testid={`usage-service-${name}`}>
              {name}: {state}
            </span>
          ))}
        </div>
        <p className="text-sm" data-testid="usage-rate-limit">
          จำกัด AI {infra?.rate_limit.limit_per_minute ?? "—"} ครั้ง/นาที · Redis {infra?.rate_limit.redis || "—"} · สูงสุด {infra?.rate_limit.highest_count ?? 0}
        </p>
        <p className="text-sm" data-testid="usage-queue">
          คิวรอ {infra?.admission.waiting ?? "—"} · p95 {infra?.admission.wait_p95_ms ?? "—"} ms
        </p>
      </section>

      <section className="gov-card space-y-2" data-testid="admin-usage-events">
        <h2 className="font-bold text-navy">คำขอล่าสุด</h2>
        <ul>
          {events.map((event) => (
            <li key={event.id} data-testid="usage-event">
              {event.provider} · {event.model} · {event.task} · {event.total_tokens} · {event.status}
            </li>
          ))}
        </ul>
      </section>

      <section className="gov-card space-y-3" data-testid="admin-usage-pricing">
        <h2 className="font-bold text-navy">ราคาต่อ 1 ล้านโทเคน (USD)</h2>
        {rates.map((rate, index) => (
          <div key={`${rate.provider}-${rate.model}`} className="grid gap-2 sm:grid-cols-6">
            <Label className="sm:col-span-2">
              {rate.provider}/{rate.model}
            </Label>
            <Input
              aria-label={`ราคาเข้า ${rate.provider}`}
              data-testid={index === 0 ? "usage-rate-input" : undefined}
              type="number"
              value={rate.input_per_million}
              onChange={(event) => updateRate(index, "input_per_million", event.target.value)}
            />
            <Input
              aria-label={`ราคาออก ${rate.provider}`}
              type="number"
              value={rate.output_per_million}
              onChange={(event) => updateRate(index, "output_per_million", event.target.value)}
            />
            <Input
              aria-label={`แคชเขียน ${rate.provider}`}
              type="number"
              value={rate.cache_write_per_million}
              onChange={(event) => updateRate(index, "cache_write_per_million", event.target.value)}
            />
            <Input
              aria-label={`แคชอ่าน ${rate.provider}`}
              type="number"
              value={rate.cache_read_per_million}
              onChange={(event) => updateRate(index, "cache_read_per_million", event.target.value)}
            />
          </div>
        ))}
        <Button type="button" data-testid="usage-pricing-save" onClick={() => { void savePricing(); }}>
          บันทึกราคา
        </Button>
      </section>
    </div>
  );
}

function Kpi({ label, value, testId }: Readonly<{ label: string; value: string; testId: string }>) {
  return (
    <div className="gov-card">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-bold text-navy" data-testid={testId}>
        {value}
      </p>
    </div>
  );
}
