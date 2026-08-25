"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/stores/project-store";
import { useAuthStore } from "@/stores/auth-store";
import { NewProjectDialog } from "@/components/projects/new-project-dialog";
import { ProjectRowActions } from "@/components/projects/project-row-actions";
import { StatCard } from "@/components/brand/stat-card";
import { StatusPill } from "@/components/brand/status-pill";
import { Modal } from "@/components/brand/modal";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api-error";
import { decideArchiveProject } from "@/lib/drafting-guard";
import type { Project } from "@/types";

function formatBudget(value: number) {
  return value.toLocaleString("th-TH");
}

function formatDate(value: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString("th-TH");
}

export default function ProjectsPage() {
  const router = useRouter();
  const role = useAuthStore((state) => state.user?.role);
  const { projects, isLoading, fetchProjects, archiveProject, decideProject } =
    useProjectStore();
  const [creatingOpen, setCreatingOpen] = useState(false);
  const [viewing, setViewing] = useState<Project | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects(1).catch((err: unknown) =>
      setError(apiErrorMessage(err, "โหลดโครงการไม่สำเร็จ"))
    );
  }, [fetchProjects]);

  const stats = useMemo(() => {
    return {
      draft: projects.filter((p) => p.status === "draft").length,
      progress: projects.filter((p) => p.status === "in_review").length,
      done: projects.filter((p) => p.status === "approved").length,
    };
  }, [projects]);

  return (
    <div data-testid="projects-page">
      {error ? (
        <p className="mb-4 text-sm rounded-md border border-destructive/50 text-destructive p-3" role="alert">
          {error}
        </p>
      ) : null}
      <div className="mb-5 grid gap-4 sm:grid-cols-3">
        <StatCard title="ร่าง (Draft)" value={stats.draft} hint="แก้ไขได้ ยังไม่ส่งสร้าง" tone="draft" />
        <StatCard
          title="กำลังดำเนินการ"
          value={stats.progress}
          hint="ระบบกำลังประมวลผล"
          tone="progress"
        />
        <StatCard title="เสร็จแล้ว" value={stats.done} hint="ดูและปรับปรุงได้" tone="done" />
      </div>

      <div className="overflow-hidden rounded-xl bg-white shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
        <div className="border-b px-5 py-4 text-base font-extrabold text-navy">
          รายการโครงการ TOR
        </div>
        {isLoading ? (
          <p className="p-8 text-sm text-muted-foreground">กำลังโหลดข้อมูล...</p>
        ) : (
          <table className="w-full text-left text-[13.5px]">
            <thead>
              <tr className="bg-gray-100 text-[12.5px] uppercase text-gray-700">
                <th className="px-4 py-3">ชื่อโครงการ</th>
                <th className="px-4 py-3">หน่วยงาน</th>
                <th className="px-4 py-3">งบประมาณ</th>
                <th className="px-4 py-3">สถานะ</th>
                <th className="px-4 py-3">วันที่อัปเดต</th>
                <th className="px-4 py-3">การกระทำ</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((project) => (
                <tr key={project.id} className="border-t hover:bg-gray-50">
                  <td className="px-4 py-3.5 font-medium">{project.name}</td>
                  <td className="px-4 py-3.5">{project.ministry}</td>
                  <td className="px-4 py-3.5">{formatBudget(project.budget)} บาท</td>
                  <td className="px-4 py-3.5">
                    <StatusPill status={project.status} />
                  </td>
                  <td className="px-4 py-3.5">{formatDate(project.updatedAt)}</td>
                  <td className="px-4 py-3.5">
                    <ProjectRowActions
                      project={project}
                      role={role}
                      onView={() => setViewing(project)}
                      onEdit={() => router.push(`/projects/${project.id}/draft`)}
                      onArchive={() => {
                        const decision = decideArchiveProject(
                          project.id,
                          project.name,
                          (message) => window.confirm(message)
                        );
                        if (decision === "blocked") {
                          setError("ไม่สามารถลบโครงการที่กำลังร่างอยู่");
                          return;
                        }
                        if (decision === "cancelled") return;
                        setError(null);
                        archiveProject(project.id).catch((err: unknown) =>
                          setError(apiErrorMessage(err, "ลบโครงการไม่สำเร็จ"))
                        );
                      }}
                      onDecide={(decision) => {
                        setError(null);
                        decideProject(project.id, decision)
                          .then(() => fetchProjects(1))
                          .catch((err: unknown) =>
                            setError(apiErrorMessage(err, "ดำเนินการไม่สำเร็จ"))
                          );
                      }}
                    />
                  </td>
                </tr>
              ))}
              {projects.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-10 text-center text-muted-foreground">
                    ยังไม่มีโครงการ
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        )}
      </div>
      <div className="mt-4 text-right">
        <Button data-testid="new-project" onClick={() => setCreatingOpen(true)}>
          + สร้างโครงการ TOR ใหม่
        </Button>
      </div>
      <NewProjectDialog open={creatingOpen} onOpenChange={setCreatingOpen} />
      <Modal
        open={Boolean(viewing)}
        title={viewing?.name || "โครงการ"}
        onClose={() => setViewing(null)}
      >
        {viewing ? (
          <div className="space-y-2 text-sm">
            <p>หน่วยงาน: {viewing.ministry}</p>
            <p>งบประมาณ: {formatBudget(viewing.budget)} บาท</p>
            <p>
              สถานะ: <StatusPill status={viewing.status} />
            </p>
            <Button
              className="mt-3"
              onClick={() => {
                router.push(`/projects/${viewing.id}/draft`);
                setViewing(null);
              }}
            >
              ปรับปรุงกลับไป Draft
            </Button>
          </div>
        ) : null}
      </Modal>
    </div>
  );
}
