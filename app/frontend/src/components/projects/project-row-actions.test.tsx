import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ProjectRowActions } from "./project-row-actions";
import type { Project } from "@/types";

const base: Project = {
  id: "p1",
  ownerId: "u1",
  name: "ทดสอบ",
  ministry: "กรม",
  budget: 1,
  projectType: "general",
  status: "in_review",
  currentStep: 7,
  currentPhase: 3,
  qualityScore: null,
  templateId: null,
  createdAt: "2026-08-18",
  updatedAt: "2026-08-18",
};

describe("ProjectRowActions", () => {
  it("shows approve and reject for a reviewer when the project is in review", () => {
    const onDecide = vi.fn();
    render(
      <ProjectRowActions
        project={base}
        role="reviewer"
        onView={vi.fn()}
        onEdit={vi.fn()}
        onArchive={vi.fn()}
        onDecide={onDecide}
      />
    );
    fireEvent.click(screen.getByTestId("approve-project"));
    expect(onDecide).toHaveBeenCalledWith("approved");
    fireEvent.click(screen.getByTestId("reject-project"));
    expect(onDecide).toHaveBeenCalledWith("rejected");
  });

  it("hides decide buttons for an officer", () => {
    render(
      <ProjectRowActions
        project={base}
        role="officer"
        onView={vi.fn()}
        onEdit={vi.fn()}
        onArchive={vi.fn()}
        onDecide={vi.fn()}
      />
    );
    expect(screen.queryByTestId("approve-project")).toBeNull();
    expect(screen.getByRole("button", { name: "แก้ไข" })).toBeDisabled();
  });

  it("exposes archive-project for an officer draft", () => {
    const onArchive = vi.fn();
    render(
      <ProjectRowActions
        project={{ ...base, status: "draft" }}
        role="officer"
        onView={vi.fn()}
        onEdit={vi.fn()}
        onArchive={onArchive}
        onDecide={vi.fn()}
      />
    );
    fireEvent.click(screen.getByTestId("archive-project"));
    expect(onArchive).toHaveBeenCalledTimes(1);
  });
});
