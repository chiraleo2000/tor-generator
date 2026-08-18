"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useProjectStore } from "@/stores/project-store";
import { Button } from "@/components/ui/button";

export default function DraftIndexPage() {
  const router = useRouter();
  const { projects, fetchProjects, createProject, isLoading } = useProjectStore();

  useEffect(() => {
    fetchProjects(1)
      .then(() => undefined)
      .catch(() => undefined);
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
      <p className="mb-4">ยังไม่มีโครงการ — สร้างโครงการใหม่เพื่อเริ่ม Phase 0</p>
      <Button data-testid="new-project" onClick={createAndOpen}>
        + สร้างโครงการ TOR ใหม่
      </Button>
    </div>
  );
}
