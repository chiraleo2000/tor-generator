"use client";

import { ThemeProvider } from "@/providers/theme-provider";
import { ToastContainer } from "@/components/layout/toast-container";
import { ErrorBoundary } from "@/components/layout/error-boundary";

/**
 * Root-level providers wrapping the entire app.
 * Includes ThemeProvider, global ErrorBoundary, and ToastContainer.
 */
export function Providers({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        {children}
        <ToastContainer />
      </ErrorBoundary>
    </ThemeProvider>
  );
}
