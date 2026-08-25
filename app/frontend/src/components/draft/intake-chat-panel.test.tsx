import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
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
            call[2]?.timeout === 90_000
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

  it("does not post fill-references on Phase 1 or Phase 2", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({ has_material: true, ready_to_compose: false }) as never
    );
    const { rerender } = render(
      <IntakeChatPanel
        projectId="p1"
        phase={1}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    await screen.findByTestId("phase1-coverage");
    rerender(
      <IntakeChatPanel
        projectId="p1"
        phase={2}
        onAnalyzed={onAnalyzed}
        onEnterQa={onEnterQa}
        onReady={onReady}
      />
    );
    await screen.findByTestId("phase2-qa");
    expect(
      vi.mocked(apiClient.post).mock.calls.filter((call) =>
        String(call[0]).includes("/intake/fill-references")
      )
    ).toHaveLength(0);
  });

  it("enters QA from Phase 1 via skip", async () => {
    vi.mocked(apiClient.get).mockResolvedValue(
      coveragePayload({ has_material: true, ready_to_compose: false }) as never
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
    fireEvent.click(skipBtn);
    await waitFor(() => expect(onEnterQa).toHaveBeenCalled());
  });
});
