import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiClient } from "@/lib/api-client";
import { useProjectStore } from "./project-store";

vi.mock("@/lib/api-client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const projectRow = {
  id: "p1",
  owner_id: "u1",
  name: "โครงการทดสอบ",
  ministry: "กระทรวงดิจิทัลฯ",
  budget: 1000000,
  project_type: "it",
  status: "draft",
  current_step: 1,
  current_phase: 0,
  quality_score: null,
  template_id: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("project-store", () => {
  beforeEach(() => {
    useProjectStore.setState({
      projects: [],
      activeProject: null,
      pagination: { page: 1, pageSize: 20, total: 0 },
      isLoading: false,
    });
    vi.clearAllMocks();
  });

  it("createProject posts snake_case and stores the camelCase project", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: projectRow },
    });
    const created = await useProjectStore.getState().createProject({
      name: "โครงการทดสอบ",
      ministry: "กระทรวงดิจิทัลฯ",
      budget: 1000000,
      projectType: "it",
    });
    expect(apiClient.post).toHaveBeenCalledWith("/projects", {
      name: "โครงการทดสอบ",
      ministry: "กระทรวงดิจิทัลฯ",
      budget: 1000000,
      project_type: "it",
      template_id: null,
    });
    expect(created.id).toBe("p1");
    expect(created.projectType).toBe("it");
    expect(useProjectStore.getState().activeProject?.name).toBe("โครงการทดสอบ");
  });

  it("fetchProjects maps pagination", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: {
        ok: true,
        data: { items: [projectRow], pagination: { page: 1, per_page: 20, total: 1 } },
      },
    });
    await useProjectStore.getState().fetchProjects(1, "draft");
    expect(useProjectStore.getState().projects).toHaveLength(1);
    expect(useProjectStore.getState().pagination.total).toBe(1);
  });

    it("submitProject updates the active project status", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { ...projectRow, status: "in_review" } },
    });
    const project = await useProjectStore.getState().submitProject("p1");
    expect(project.status).toBe("in_review");
    expect(useProjectStore.getState().activeProject?.status).toBe("in_review");
  });

  it("covers fetch, update, decide, versions, and archive", async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { ok: true, data: projectRow },
    });
    const fetched = await useProjectStore.getState().fetchProject("p1");
    expect(fetched.id).toBe("p1");

    useProjectStore.getState().setActiveProject(fetched);
    vi.mocked(apiClient.put).mockResolvedValue({
      data: { ok: true, data: { ...projectRow, name: "อัปเดต" } },
    });
    const updated = await useProjectStore.getState().updateProject("p1", { name: "อัปเดต" });
    expect(updated.name).toBe("อัปเดต");

    vi.mocked(apiClient.post).mockResolvedValue({
      data: { ok: true, data: { ...projectRow, status: "approved" } },
    });
    const decided = await useProjectStore.getState().decideProject("p1", "approved");
    expect(decided.status).toBe("approved");
    await useProjectStore.getState().decideProject("p1", "rejected");
    await useProjectStore.getState().restoreVersion("p1", 2);

    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        ok: true,
        data: { items: [{ version_number: 1, step_number: 2, created_at: "2026-01-01T00:00:00Z" }] },
      },
    });
    const versions = await useProjectStore.getState().fetchVersions("p1");
    expect(versions[0].version_number).toBe(1);

    useProjectStore.setState({ projects: [fetched] });
    vi.mocked(apiClient.delete).mockResolvedValue({ data: { ok: true } });
    await useProjectStore.getState().archiveProject("p1");
    expect(useProjectStore.getState().projects).toHaveLength(0);
    useProjectStore.getState().clearActiveProject();
    expect(useProjectStore.getState().activeProject).toBeNull();
  });

  it("clears loading when fetchProjects fails", async () => {
    vi.mocked(apiClient.get).mockRejectedValue(new Error("offline"));
    await expect(useProjectStore.getState().fetchProjects()).rejects.toThrow("offline");
    expect(useProjectStore.getState().isLoading).toBe(false);
  });

  it("clears loading when createProject fails", async () => {
    vi.mocked(apiClient.post).mockRejectedValue(new Error("create-fail"));
    await expect(
      useProjectStore.getState().createProject({
        name: "ล้ม",
        ministry: "กระทรวง",
        budget: 1,
        projectType: "it",
      })
    ).rejects.toThrow("create-fail");
    expect(useProjectStore.getState().isLoading).toBe(false);
  });
});
