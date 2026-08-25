"use client";

import { Button } from "@/components/ui/button";
import type { Project, UserRole } from "@/types";

export function canDecideReview(role: UserRole | undefined): boolean {
  return role === "reviewer" || role === "admin";
}

export function ProjectRowActions({
  project,
  role,
  onView,
  onEdit,
  onArchive,
  onDecide,
}: Readonly<{
  project: Project;
  role: UserRole | undefined;
  onView: () => void;
  onEdit: () => void;
  onArchive: () => void;
  onDecide: (decision: "approved" | "rejected") => void;
}>) {
  const waitingReview = project.status === "in_review";
  if (waitingReview && canDecideReview(role)) {
    return (
      <div className="flex flex-wrap gap-1.5">
        <Button
          size="sm"
          data-testid="approve-project"
          onClick={() => onDecide("approved")}
        >
          อนุมัติ
        </Button>
        <Button
          size="sm"
          variant="outline"
          data-testid="reject-project"
          onClick={() => onDecide("rejected")}
        >
          ส่งกลับ
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5">
      {project.status === "approved" ? (
        <Button size="sm" variant="outline" onClick={onView}>
          ดู
        </Button>
      ) : null}
      <Button
        size="sm"
        variant={waitingReview ? "secondary" : "default"}
        disabled={waitingReview}
        onClick={onEdit}
      >
        {project.status === "approved" ? "ปรับปรุง" : "แก้ไข"}
      </Button>
      <Button
        size="sm"
        variant="outline"
        data-testid="archive-project"
        aria-label={`ลบโครงการ ${project.name}`}
        onClick={onArchive}
      >
        ลบ
      </Button>
    </div>
  );
}
