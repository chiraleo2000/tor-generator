"use client";

import Link from "next/link";
import type { Project, ProjectStatus } from "@/types";
import { cn } from "@/lib/utils";

/** Status display configuration */
const STATUS_CONFIG: Record<
  ProjectStatus,
  { label: string; className: string }
> = {
  draft: {
    label: "ร่าง",
    className: "bg-gray-100 text-gray-700 border-gray-300",
  },
  in_review: {
    label: "ตรวจสอบ",
    className: "bg-yellow-100 text-yellow-800 border-yellow-300",
  },
  approved: {
    label: "อนุมัติ",
    className: "bg-green-100 text-green-800 border-green-300",
  },
  rejected: {
    label: "ปฏิเสธ",
    className: "bg-red-100 text-red-800 border-red-300",
  },
  archived: {
    label: "เก็บถาวร",
    className: "bg-slate-100 text-slate-700 border-slate-300",
  },
};

/** Format number as Thai Baht currency */
function formatBaht(amount: number): string {
  return new Intl.NumberFormat("th-TH", {
    style: "currency",
    currency: "THB",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/** Format date to Thai locale */
function formatThaiDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("th-TH", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Quality score color based on value */
function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

export interface ProjectCardProps {
  project: Project;
}

export function ProjectCard({ project }: Readonly<ProjectCardProps>) {
  const statusConfig = STATUS_CONFIG[project.status];

  return (
    <Link
      href={`/projects/${project.id}`}
      data-testid={`project-card-${project.id}`}
      className="block rounded-lg border bg-card p-5 shadow-sm transition-shadow hover:shadow-md"
    >
      {/* Header: Name + Status badge */}
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-base font-semibold text-card-foreground line-clamp-2">
          {project.name}
        </h3>
        <span
          className={cn(
            "inline-flex shrink-0 items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
            statusConfig.className
          )}
        >
          {statusConfig.label}
        </span>
      </div>

      {/* Ministry / Organization */}
      {project.ministry && (
        <p className="mt-2 text-sm text-muted-foreground truncate">
          {project.ministry}
        </p>
      )}

      {/* Budget */}
      <p className="mt-1 text-sm font-medium text-foreground">
        {formatBaht(project.budget)}
      </p>

      {/* Footer: Date + Quality Score */}
      <div className="mt-3 flex items-center justify-between border-t pt-3">
        <span className="text-xs text-muted-foreground">
          แก้ไขล่าสุด: {formatThaiDate(project.updatedAt)}
        </span>
        {project.qualityScore !== null && (
          <span
            className={cn(
              "text-xs font-semibold",
              getScoreColor(project.qualityScore)
            )}
          >
            คะแนน: {project.qualityScore}/100
          </span>
        )}
      </div>
    </Link>
  );
}
