import { create } from "zustand";
import { apiClient } from "@/lib/api-client";
import { snakeToCamelProject, unwrapData, asString } from "@/lib/api-unwrap";
import type { Project, Pagination, CreateProjectInput } from "@/types";

interface ListPayload {
  items?: Record<string, unknown>[];
  pagination?: {
    page: number;
    per_page?: number;
    pageSize?: number;
    total: number;
  };
}

export interface ProjectState {
  projects: Project[];
  activeProject: Project | null;
  pagination: Pagination;
  isLoading: boolean;
  fetchProjects: (page?: number, status?: string) => Promise<void>;
  fetchProject: (id: string) => Promise<Project>;
  setActiveProject: (project: Project) => void;
  createProject: (data: CreateProjectInput) => Promise<Project>;
  updateProject: (id: string, data: Partial<CreateProjectInput> & { status?: string }) => Promise<Project>;
  submitProject: (id: string) => Promise<Project>;
  decideProject: (id: string, decision: "approved" | "rejected") => Promise<Project>;
  restoreVersion: (id: string, version: number) => Promise<void>;
  fetchVersions: (id: string) => Promise<{ version_number: number; step_number: number; created_at: string }[]>;
  archiveProject: (id: string) => Promise<void>;
  clearActiveProject: () => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  projects: [],
  activeProject: null,
  pagination: { page: 1, pageSize: 20, total: 0 },
  isLoading: false,

  fetchProjects: async (page = 1, status?: string) => {
    set({ isLoading: true });
    try {
      const params: Record<string, string | number> = { page, per_page: 20 };
      if (status) params.status = status;
      const response = await apiClient.get("/projects", { params });
      const payload = unwrapData<ListPayload>(response);
      const items = (payload.items || []).map((row) =>
        snakeToCamelProject(row)
      );
      const pagination = payload.pagination;
      set({
        projects: items,
        pagination: {
          page: pagination?.page ?? page,
          pageSize: pagination?.per_page ?? pagination?.pageSize ?? 20,
          total: pagination?.total ?? items.length,
        },
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  fetchProject: async (id: string) => {
    const response = await apiClient.get(`/projects/${id}`);
    const project = snakeToCamelProject(
      unwrapData<Record<string, unknown>>(response)
    );
    set({ activeProject: project });
    return project;
  },

  setActiveProject: (project: Project) => {
    set({ activeProject: project });
  },

  createProject: async (data: CreateProjectInput) => {
    set({ isLoading: true });
    try {
      const response = await apiClient.post("/projects", {
        name: data.name,
        ministry: data.ministry,
        budget: data.budget,
        project_type: data.projectType,
        template_id: data.templateId || null,
      });
      const newProject = snakeToCamelProject(
        unwrapData<Record<string, unknown>>(response)
      );
      set((state) => ({
        projects: [newProject, ...state.projects],
        activeProject: newProject,
        isLoading: false,
      }));
      return newProject;
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  updateProject: async (id: string, data: Partial<CreateProjectInput> & { status?: string }) => {
    const response = await apiClient.put(`/projects/${id}`, {
      name: data.name,
      ministry: data.ministry,
      budget: data.budget,
      project_type: data.projectType,
      template_id: data.templateId,
      status: data.status,
    });
    const project = snakeToCamelProject(
      unwrapData<Record<string, unknown>>(response)
    );
    set({ activeProject: project });
    return project;
  },

  submitProject: async (id: string) => {
    const response = await apiClient.post(`/projects/${id}/submit`);
    const project = snakeToCamelProject(
      unwrapData<Record<string, unknown>>(response)
    );
    set({ activeProject: project });
    return project;
  },

  decideProject: async (id: string, decision: "approved" | "rejected") => {
    const response = await apiClient.post(`/projects/${id}/${decision === "approved" ? "approve" : "reject"}`);
    const project = snakeToCamelProject(
      unwrapData<Record<string, unknown>>(response)
    );
    set({ activeProject: project });
    return project;
  },

  restoreVersion: async (id: string, version: number) => {
    await apiClient.post(`/projects/${id}/versions/${version}/restore`);
  },

  fetchVersions: async (id: string) => {
    const response = await apiClient.get(`/projects/${id}/versions`);
    const payload = unwrapData<{ items?: Record<string, unknown>[] }>(response);
    return (payload.items || []).map((item) => ({
      version_number: Number(item.version_number),
      step_number: Number(item.step_number),
      created_at: asString(item.created_at),
    }));
  },

  archiveProject: async (id: string) => {
    await apiClient.delete(`/projects/${id}`);
    set((state) => ({
      projects: state.projects.filter((item) => item.id !== id),
    }));
  },

  clearActiveProject: () => {
    set({ activeProject: null });
  },
}));
