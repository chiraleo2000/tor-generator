import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Toast, ToastType } from '@/types';

export interface UIState {
  theme: 'light' | 'dark';
  sidebarOpen: boolean;
  isLoading: boolean;
  toasts: Toast[];
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setLoading: (loading: boolean) => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}

let toastIdCounter = 0;

function generateToastId(): string {
  toastIdCounter += 1;
  return `toast-${Date.now()}-${toastIdCounter}`;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      theme: 'light',
      sidebarOpen: true,
      isLoading: false,
      toasts: [],

      toggleTheme: () => {
        set((state) => ({
          theme: state.theme === 'light' ? 'dark' : 'light',
        }));
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarOpen: !state.sidebarOpen }));
      },

      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open });
      },

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      addToast: (toast: Omit<Toast, 'id'>) => {
        const id = generateToastId();
        const newToast: Toast = { ...toast, id };
        set((state) => ({
          toasts: [...state.toasts, newToast],
        }));

        // Auto-remove toast after duration (default 5000ms)
        const duration = toast.duration ?? 5000;
        if (duration > 0) {
          setTimeout(() => {
            set((state) => ({
              toasts: state.toasts.filter((t) => t.id !== id),
            }));
          }, duration);
        }
      },

      removeToast: (id: string) => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      },
    }),
    {
      name: 'tor-ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarOpen: state.sidebarOpen,
      }),
    }
  )
);
