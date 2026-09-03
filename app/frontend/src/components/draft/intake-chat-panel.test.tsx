import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { IntakeChatPanel } from "@/components/draft/intake-chat-panel";
import { apiClient } from "@/lib/api-client";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock("@/components/draft/draft-conversation", () => ({
  DraftConversation: () => <div data-testid="draft-conversation" />,
}));

beforeAll(() => {
  if (typeof HTMLDialogElement === "undefined") {
    return;
  }
  HTMLDialogElement.prototype.showModal = function showModal() {
    this.setAttribute("open", "");
  };
  HTMLDialogElement.prototype.close = function close() {
    this.removeAttribute("open");
  };
});

function coveragePayload(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      ok: true,
      data: {
        coverage: [],
        gap_questions: [],
        ready_to_compose: false,
        has_material: false,
        ...overrides,
      },
    },
  };
}

describe("IntakeChatPanel", () => {
  const onAnalyzed = vi.fn();
  const onEnterQa = vi.fn();
  const onReady = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiClient.get).mockResolvedValue(coveragePayload() as never);
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true, data: {} } } as never);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not call analyze on upload", async () => {
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    await screen.findByTestId("phase0-upload");
    const input = screen.getByTestId("intake-upload") as HTMLInputElement;
    const file = new File(["pack"], "pack.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => expect(apiClient.post).toHaveBeenCalled());
    const paths = vi.mocked(apiClient.post).mock.calls.map((call) => String(call[0]));
    expect(paths.some((path) => path.includes("/intake/upload"))).toBe(true);
    expect(paths.some((path) => path.includes("/intake/analyze"))).toBe(false);
    expect(onAnalyzed).not.toHaveBeenCalled();
  });

  it("disables analyze when there is no material", async () => {
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const button = await screen.findByTestId("intake-start-analyze");
    expect(button).toBeDisabled();
  });

  it("posts analyze after the user confirms", async () => {
    const mapped = coveragePayload({
      analyzed: true,
      has_material: true,
      coverage: [
        {
          key: "s1",
          label: "ชื่อโครงการ",
          status: "filled",
          filled: true,
          fact_required: true,
        },
      ],
    });
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce(coveragePayload({ has_material: true }) as never)
      .mockResolvedValue(mapped as never);
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const paste = await screen.findByTestId("intake-paste");
    fireEvent.change(paste, {
      target: { value: "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งปี" },
    });
    await waitFor(() => expect(screen.getByTestId("intake-start-analyze")).toBeEnabled());
    fireEvent.click(screen.getByTestId("intake-start-analyze"));
    expect(await screen.findByTestId("confirm-phase-dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("confirm-phase-ok"));
    await waitFor(() =>
      expect(
        vi.mocked(apiClient.post).mock.calls.some(
          (call) =>
            call[0] === "/projects/p1/intake/analyze" &&
            call[2]?.timeout === 900_000
        )
      ).toBe(true)
    );
    await waitFor(() => expect(onAnalyzed).toHaveBeenCalled(), { timeout: 3000 });
  });

  it("confirms ready from Phase 2", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({
        coverage: [
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "filled",
            filled: true,
            fact_required: true,
          },
        ],
        ready_to_compose: false,
        has_material: true,
      }) as never
    );
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={2}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    fireEvent.click(await screen.findByTestId("intake-confirm-ready"));
    expect(await screen.findByTestId("confirm-phase-dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("confirm-phase-ok"));
    await waitFor(() =>
      expect(
        vi.mocked(apiClient.post).mock.calls.some((call) =>
          String(call[0]).includes("/intake/confirm-ready")
        )
      ).toBe(true)
    );
    expect(onReady).toHaveBeenCalled();
  });

  it("can post fill-references from Phase 2 standards button", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({
        has_material: true,
        analyzed: true,
        ready_to_compose: false,
        coverage: [
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "filled",
            filled: true,
            fact_required: true,
            preview: "โครงการทดสอบ",
          },
          {
            key: "s3",
            label: "คุณสมบัติ",
            status: "gap",
            filled: false,
            fact_required: false,
          },
        ],
      }) as never
    );
    vi.mocked(apiClient.post).mockResolvedValue({
      data: {
        ok: true,
        data: {
          filled_keys: ["s3"],
          coverage: [
            {
              key: "s3",
              label: "คุณสมบัติ",
              status: "filled",
              filled: true,
              fact_required: false,
              preview: "มาตรฐานกลาง",
            },
          ],
        },
      },
    } as never);
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={2}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    await screen.findByTestId("phase2-qa");
    fireEvent.click(await screen.findByTestId("phase2-apply-standards"));
    await waitFor(() =>
      expect(
        vi.mocked(apiClient.post).mock.calls.some((call) =>
          String(call[0]).includes("/intake/fill-references")
        )
      ).toBe(true)
    );
  });

  it("enters QA from Phase 1 via skip", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({
        has_material: true,
        analyzed: true,
        ready_to_compose: false,
        coverage: [
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "gap",
            filled: false,
            fact_required: true,
          },
        ],
      }) as never
    );
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={1}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const skipBtn = await screen.findByTestId("phase1-skip");
    expect(skipBtn).toBeEnabled();
    fireEvent.click(skipBtn);
    await waitFor(() => expect(onEnterQa).toHaveBeenCalled());
  });

  it("shows upload and confirm-ready errors, and ignores empty files", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { error: { message: "อัปโหลดไม่สำเร็จ" } } },
    });
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const input = await screen.findByTestId("intake-upload");
    fireEvent.change(input, { target: { files: null } });
    expect(apiClient.post).not.toHaveBeenCalled();
    const file = new File(["pack"], "pack.pdf", { type: "application/pdf" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(await screen.findByRole("alert")).toHaveTextContent("อัปโหลดไม่สำเร็จ");

    fireEvent.change(screen.getByTestId("intake-paste"), {
      target: { value: "ข้อความยาวพอสำหรับเริ่มวิเคราะห์ขั้นที่ศูนย์" },
    });
    fireEvent.blur(screen.getByTestId("intake-paste"));
    const analyze = screen.getByTestId("intake-start-analyze");
    await waitFor(() => expect(analyze).toBeEnabled());
    fireEvent.click(analyze);
    expect(await screen.findByTestId("confirm-phase-dialog")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("confirm-phase-cancel"));
    expect(
      vi.mocked(apiClient.post).mock.calls.some((call) =>
        String(call[0]).includes("/intake/analyze")
      )
    ).toBe(false);
  });

  it("saves long paste on blur and reports confirm-ready failures", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({
        has_material: true,
        coverage: [
          {
            key: "s1",
            label: "ชื่อโครงการ",
            status: "filled",
            filled: true,
            fact_required: true,
          },
        ],
      }) as never
    );
    vi.mocked(apiClient.post)
      .mockResolvedValueOnce({ data: { ok: true, data: {} } } as never)
      .mockRejectedValueOnce({
        response: { data: { error: { message: "ยังไม่ครบช่องข้อเท็จจริงที่บังคับ" } } },
      });
    const { rerender } = render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const paste = await screen.findByTestId("intake-paste");
    fireEvent.change(paste, {
      target: { value: "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งปี" },
    });
    fireEvent.blur(paste);
    await waitFor(() =>
      expect(
        vi.mocked(apiClient.post).mock.calls.some((call) =>
          String(call[0]).includes("/intake/text")
        )
      ).toBe(true)
    );
    rerender(
      <IntakeChatPanel
        projectId="p1"
        phase={2}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    fireEvent.click(await screen.findByTestId("intake-confirm-ready"));
    fireEvent.click(await screen.findByTestId("confirm-phase-ok"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ยังไม่ครบช่องข้อเท็จจริงที่บังคับ"
    );
  });

  it("reports incomplete analyze when coverage never maps", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({ has_material: true, analyzed: true, coverage: [] }) as never
    );
    vi.mocked(apiClient.post).mockResolvedValue({ data: { ok: true, data: {} } } as never);
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const paste = await screen.findByTestId("intake-paste");
    fireEvent.change(paste, {
      target: { value: "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งปี" },
    });
    fireEvent.click(screen.getByTestId("intake-start-analyze"));
    fireEvent.click(await screen.findByTestId("confirm-phase-ok"));
    vi.useFakeTimers();
    await vi.advanceTimersByTimeAsync(35_000);
    vi.useRealTimers();
    expect(await screen.findByRole("alert")).toHaveTextContent("วิเคราะห์ยังไม่ครบ");
  });

  it("recovers from a failed analyze when coverage later maps", async () => {
    vi.mocked(apiClient.get)
      .mockResolvedValueOnce(coveragePayload({ has_material: true }) as never)
      .mockResolvedValue(
        coveragePayload({
          analyzed: true,
          has_material: true,
          coverage: [
            {
              key: "s1",
              label: "ชื่อโครงการ",
              status: "filled",
              filled: true,
              fact_required: true,
            },
          ],
        }) as never
      );
    vi.mocked(apiClient.post).mockImplementation(async (url: string) => {
      if (String(url).includes("/analyze")) {
        throw { response: { data: { error: { message: "วิเคราะห์ไม่สำเร็จ" } } } };
      }
      return { data: { ok: true, data: {} } } as never;
    });
    render(
      <IntakeChatPanel
        projectId="p1"
        phase={0}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    const paste = await screen.findByTestId("intake-paste");
    fireEvent.change(paste, {
      target: { value: "โครงการทดสอบวงเงินหนึ่งแสนบาท ระยะเวลาหนึ่งปี" },
    });
    fireEvent.click(screen.getByTestId("intake-start-analyze"));
    fireEvent.click(await screen.findByTestId("confirm-phase-ok"));
    vi.useFakeTimers();
    await vi.advanceTimersByTimeAsync(5_000);
    vi.useRealTimers();
    await waitFor(() => expect(onAnalyzed).toHaveBeenCalled());
  });
});
