import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { NewProjectDialog, parseProjectBudget } from "./new-project-dialog";
import { apiClient } from "@/lib/api-client";

const { createProject, push } = vi.hoisted(() => ({
  createProject: vi.fn(),
  push: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/stores/project-store", () => ({
  useProjectStore: (selector: (state: { createProject: typeof createProject }) => unknown) =>
    selector({ createProject }),
}));

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
  },
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

describe("parseProjectBudget", () => {
  it("strips commas and accepts ASCII digits only", () => {
    expect(parseProjectBudget("1,000,000")).toBe(1000000);
    expect(parseProjectBudget("0")).toBeNull();
    expect(parseProjectBudget("๑๐๐๐")).toBeNull();
    expect(parseProjectBudget("1000บาท")).toBeNull();
  });
});

describe("NewProjectDialog", () => {
  beforeEach(() => {
    createProject.mockReset();
    push.mockReset();
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { ok: true, data: { items: [] } },
    });
  });

  it("opens the intake form", async () => {
    render(<NewProjectDialog open onOpenChange={() => undefined} />);
    expect(await screen.findByTestId("new-project-dialog")).toBeInTheDocument();
    expect(screen.getByText(/กระบวนการร่าง TOR แบบ 5 Phase/)).toBeInTheDocument();
  });

  it("shows a validation error when required fields are missing", async () => {
    render(<NewProjectDialog open onOpenChange={() => undefined} />);
    fireEvent.click(await screen.findByTestId("create-project-submit"));
    expect(await screen.findByTestId("new-project-error")).toHaveTextContent(
      "กรุณากรอกชื่อโครงการ หน่วยงาน และงบประมาณ"
    );
    expect(createProject).not.toHaveBeenCalled();
  });

  it("creates a project and navigates to the 5-phase draft", async () => {
    createProject.mockResolvedValue({ id: "proj-9" });
    const onOpenChange = vi.fn();
    render(<NewProjectDialog open onOpenChange={onOpenChange} />);
    fireEvent.change(await screen.findByTestId("new-project-name"), {
      target: { value: "โครงการทดสอบ" },
    });
    fireEvent.change(screen.getByTestId("new-project-ministry"), {
      target: { value: "กรมบัญชีกลาง" },
    });
    fireEvent.change(screen.getByTestId("new-project-budget"), {
      target: { value: "1,500,000" },
    });
    fireEvent.click(screen.getByTestId("create-project-submit"));
    await waitFor(() => expect(createProject).toHaveBeenCalled());
    expect(createProject).toHaveBeenCalledWith({
      name: "โครงการทดสอบ",
      ministry: "กรมบัญชีกลาง",
      budget: 1500000,
      projectType: "general",
      templateId: undefined,
    });
    expect(onOpenChange).toHaveBeenCalledWith(false);
    expect(push).toHaveBeenCalledWith("/projects/proj-9/draft");
    expect(push).not.toHaveBeenCalledWith(expect.stringContaining("/wizard"));
  });

  it("surfaces apiErrorMessage when create fails", async () => {
    createProject.mockRejectedValue({
      response: { data: { error: { message: "ชื่อซ้ำ" } } },
    });
    render(<NewProjectDialog open onOpenChange={() => undefined} />);
    fireEvent.change(await screen.findByTestId("new-project-name"), {
      target: { value: "โครงการทดสอบ" },
    });
    fireEvent.change(screen.getByTestId("new-project-ministry"), {
      target: { value: "กรมบัญชีกลาง" },
    });
    fireEvent.change(screen.getByTestId("new-project-budget"), {
      target: { value: "1000" },
    });
    fireEvent.click(screen.getByTestId("create-project-submit"));
    expect(await screen.findByTestId("new-project-error")).toHaveTextContent("ชื่อซ้ำ");
    expect(push).not.toHaveBeenCalled();
  });
});
