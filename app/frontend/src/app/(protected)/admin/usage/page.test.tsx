import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import AdminUsagePage from "./page";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    put: vi.fn(),
    post: vi.fn(),
  },
}));

const summary = {
  requests: 4,
  prompt_tokens: 100,
  completion_tokens: 40,
  cache_creation_input_tokens: 5,
  cache_read_input_tokens: 15,
  total_tokens: 140,
  cost_usd: 1.25,
  calls_per_hour: 0.5,
  by_user: [{ key: "officer-1", requests: 4, tokens: 140, cost_usd: 1.25 }],
  by_model: [{ key: "claude-sonnet", requests: 4, tokens: 140, cost_usd: 1.25 }],
};

function mockGets() {
  vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
    if (url.includes("/summary")) return { data: { ok: true, data: summary } };
    if (url.includes("/timeseries")) {
      return {
        data: {
          ok: true,
          data: { buckets: [{ start: "2026-10-21T10:00:00+00:00", requests: 4, tokens: 140, cost_usd: 1.25 }] },
        },
      };
    }
    if (url.includes("/alerts")) {
      return {
        data: {
          ok: true,
          data: {
            open_count: 1,
            items: [
              {
                id: "a1",
                title: "การใช้โทเคนสูงผิดปกติ",
                severity: "critical",
                rule_id: "user_token_spike",
                subject_key: "officer-1",
                open: true,
                detail: {},
              },
              {
                id: "a2",
                title: "ค่าใช้จ่ายวันนี้เกินงบ",
                severity: "critical",
                rule_id: "global_cost_daily",
                subject_key: "org",
                open: false,
                detail: {},
              },
            ],
          },
        },
      };
    }
    if (url.includes("/infra")) {
      return {
        data: {
          ok: true,
          data: {
            status: "degraded",
            services: { postgres: "up", redis: "down" },
            rate_limit: { limit_per_minute: 30, redis: "down", active_keys: 0, highest_count: 0 },
            admission: { waiting: 2, wait_p95_ms: 80, queues: [] },
          },
        },
      };
    }
    if (url.includes("/pricing")) {
      return {
        data: {
          ok: true,
          data: {
            rates: [
              {
                provider: "claude",
                model: "*",
                input_per_million: 3,
                output_per_million: 15,
                cache_write_per_million: 3.75,
                cache_read_per_million: 0.3,
              },
            ],
          },
        },
      };
    }
    return {
      data: {
        ok: true,
        data: {
          items: [
            {
              id: "e1",
              provider: "claude",
              model: "claude-sonnet",
              task: "draft",
              total_tokens: 140,
              cost_usd: 1.25,
              status: "ok",
            },
          ],
        },
      },
    };
  });
}

describe("AdminUsagePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGets();
  });

  it("shows tokens, frequency, infra, alerts, and pricing", async () => {
    render(<AdminUsagePage />);
    expect(await screen.findByTestId("usage-kpi-requests")).toHaveTextContent("4");
    expect(screen.getByTestId("usage-kpi-prompt")).toHaveTextContent("100");
    expect(screen.getByTestId("usage-kpi-completion")).toHaveTextContent("40");
    expect(screen.getByTestId("usage-kpi-cache-read")).toHaveTextContent("15");
    expect(screen.getByTestId("usage-kpi-cost")).toHaveTextContent("1.2500");
    expect(screen.getByTestId("usage-kpi-rate")).toHaveTextContent("0.5");
    expect(screen.getByTestId("usage-top-model")).toHaveTextContent("claude-sonnet");
    expect(screen.getByTestId("usage-top-user")).toHaveTextContent("officer-1");
    expect(screen.getByTestId("usage-bucket")).toBeInTheDocument();
    expect(screen.getByTestId("usage-service-postgres")).toHaveTextContent("up");
    expect(screen.getByTestId("usage-service-redis")).toHaveTextContent("down");
    expect(screen.getByTestId("usage-rate-limit")).toHaveTextContent("30");
    expect(screen.getByTestId("usage-queue")).toHaveTextContent("2");
    expect(screen.getByTestId("usage-event")).toHaveTextContent("draft");
    expect(screen.getByTestId("usage-alert-ack-a1")).toBeInTheDocument();
    expect(screen.getByText("รับทราบแล้ว")).toBeInTheDocument();
    expect(screen.getByTestId("usage-rate-input")).toHaveValue(3);
  });

  it("acknowledges an alert and saves a price", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true, data: {} } });
    vi.mocked(apiClient.put).mockResolvedValue({ data: { ok: true, data: { rates: [] } } });
    render(<AdminUsagePage />);
    await screen.findByTestId("usage-alert-ack-a1");
    fireEvent.click(screen.getByTestId("usage-alert-ack-a1"));
    expect(await screen.findByTestId("usage-status")).toHaveTextContent("รับทราบ");
    expect(apiClient.post).toHaveBeenCalledWith("/admin/usage/alerts/a1/ack");

    fireEvent.change(screen.getByTestId("usage-rate-input"), { target: { value: "1.5" } });
    fireEvent.click(screen.getByTestId("usage-pricing-save"));
    expect(await screen.findByTestId("usage-status")).toHaveTextContent("บันทึกราคา");
    expect(apiClient.put).toHaveBeenCalled();
    const payload = vi.mocked(apiClient.put).mock.calls[0][1] as { rates: Array<{ input_per_million: number }> };
    expect(payload.rates[0].input_per_million).toBe(1.5);

    fireEvent.click(screen.getByTestId("usage-range-168"));
    await screen.findByTestId("usage-kpi-requests");
    const urls = vi.mocked(apiClient.get).mock.calls.map((call) => String(call[0]));
    expect(urls.some((url) => url.includes("grain=day"))).toBe(true);
  });

  it("shows load, acknowledge, and pricing errors", async () => {
    vi.mocked(apiClient.get).mockRejectedValue({
      response: { data: { error: { message: "โหลดไม่ได้" } } },
    });
    render(<AdminUsagePage />);
    expect(await screen.findByTestId("usage-error")).toHaveTextContent("โหลดไม่ได้");
  });

  it("shows an empty alert list and action failures", async () => {
    vi.mocked(apiClient.get).mockImplementation(async (url: string) => {
      if (url.includes("/alerts")) return { data: { ok: true, data: { open_count: 0, items: [] } } };
      if (url.includes("/pricing")) return { data: { ok: true, data: { rates: [] } } };
      if (url.includes("/timeseries")) return { data: { ok: true, data: { buckets: [] } } };
      if (url.includes("/infra")) {
        return {
          data: {
            ok: true,
            data: {
              status: "unhealthy",
              services: {},
              rate_limit: { limit_per_minute: 30, redis: "down", active_keys: 0, highest_count: 0 },
              admission: { waiting: null, wait_p95_ms: null, queues: [] },
            },
          },
        };
      }
      if (url.includes("/summary")) {
        return { data: { ok: true, data: { ...summary, by_model: [], by_user: [] } } };
      }
      return { data: { ok: true, data: { items: [] } } };
    });
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "รับทราบไม่สำเร็จ" } } },
    });
    vi.mocked(apiClient.put).mockRejectedValue({
      response: { data: { error: { message: "บันทึกราคาไม่สำเร็จ" } } },
    });
    render(<AdminUsagePage />);
    expect(await screen.findByTestId("usage-alerts-empty")).toBeInTheDocument();
    expect(screen.getByTestId("usage-top-model")).toHaveTextContent("—");
    fireEvent.click(screen.getByTestId("usage-pricing-save"));
    expect(await screen.findByTestId("usage-error")).toHaveTextContent("บันทึกราคาไม่สำเร็จ");
  });
});
