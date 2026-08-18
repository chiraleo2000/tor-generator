import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "@/stores/auth-store";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

export const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export function applyRequestAuth(
  config: InternalAxiosRequestConfig,
  token: string | null
): InternalAxiosRequestConfig {
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    delete config.headers["Content-Type"];
  }
  return config;
}

export function shouldRedirectToLogin(status: number, pathname: string): boolean {
  return status === 401 && !pathname.startsWith("/login") && !pathname.startsWith("/register");
}

apiClient.interceptors.request.use(
  (config) => applyRequestAuth(config, useAuthStore.getState().token),
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (typeof window !== "undefined") {
      const status = error.response?.status ?? 0;
      if (shouldRedirectToLogin(status, window.location.pathname)) {
        useAuthStore.getState().clearSession();
        window.location.assign("/login");
      }
    }
    return Promise.reject(error);
  }
);
