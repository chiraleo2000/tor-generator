"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/stores/project-store";
import { Button } from "@/components/ui/button";
import { apiErrorMessage } from "@/lib/api-error";

export default function DraftIndexPage() {
  const router = useRouter();
  const { projects, fetchProjects, createProject, isLoading } = useProjectStore();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects(1).catch((err: unknown) =>
      setError(apiErrorMessage(err, "โหลดโครงการไม่สำเร็จ"))
    );
  }, [fetchProjects]);

  useEffect(() => {
    if (isLoading) return;
    const draft = projects.find((item) => item.status === "draft") || projects[0];
    if (draft) {
      router.replace(`/projects/${draft.id}/draft`);
    }
  }, [isLoading, projects, router]);

  async function createAndOpen() {
    const project = await createProject({
      name: "โครงการใหม่ #1",
      ministry: "ยังไม่ระบุ",
      budget: 1,
      projectType: "general",
    });
    router.push(`/projects/${project.id}/draft`);
  }

  return (
    <div className="py-16 text-center" data-testid="draft-index">
      {error ? (
        <p className="mb-4 text-sm text-destructive" role="alert">
          {error}
        </p>
      ) : null}
      <p className="mb-4">ยังไม่มีโครงการ — สร้างโครงการใหม่เพื่อเริ่ม Phase 0</p>
      <Button data-testid="new-project" onClick={createAndOpen}>
        + สร้างโครงการ TOR ใหม่
      </Button>
    </div>
  );
}
