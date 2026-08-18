import { create } from "zustand";
import axios from "axios";
import type { User, LoginResponse } from "@/types";
import { unwrapData, asString } from "@/lib/api-unwrap";
import { apiClient } from "@/lib/api-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

function mapUser(raw: Record<string, unknown> | User): User {
  const r = raw as Record<string, unknown>;
  return {
    id: asString(r.id),
    name: asString(r.name),
    email: asString(r.email),
    organization: asString(r.organization),
    role: (r.role as User["role"]) || "officer",
    createdAt: asString(r.created_at) || asString(r.createdAt),
    updatedAt: asString(r.updated_at) || asString(r.updatedAt),
  };
}

export interface AuthState {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  restoreSession: () => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>()((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  isLoading: true,

  login: async (email: string, password: string) => {
    set({ isLoading: true });
    try {
      const response = await axios.post<LoginResponse>(
        `${API_URL}/auth/login`,
        { email, password },
        { withCredentials: true }
      );
      const payload = unwrapData<LoginResponse & { user: Record<string, unknown> }>(
        response
      );
      set({
        token: payload.token || null,
        user: mapUser(payload.user as unknown as Record<string, unknown>),
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      set({ isLoading: false });
      throw error;
    }
  },

  logout: () => {
    apiClient.post("/auth/logout").catch(() => undefined);
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
    if (typeof window !== "undefined") {
      window.location.assign("/login");
    }
  },

  clearSession: () => {
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
    });
  },

  restoreSession: () => {
    apiClient
      .get("/auth/me")
      .then((response) => {
        set({
          user: mapUser(unwrapData<Record<string, unknown>>(response)),
          isAuthenticated: true,
          isLoading: false,
        });
      })
      .catch(() => {
        set({
          token: null,
          user: null,
          isAuthenticated: false,
          isLoading: false,
        });
      });
  },
}));
