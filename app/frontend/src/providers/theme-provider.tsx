"use client";

import { useEffect } from "react";
import { useUIStore } from "@/stores/ui-store";

interface ThemeProviderProps {
  children: React.ReactNode;
}

/**
 * ThemeProvider reads theme from useUIStore and applies the `dark` class to <html>.
 * Default is light; the header toggle persists the user's choice.
 */
export function ThemeProvider({ children }: Readonly<ThemeProviderProps>) {
  const theme = useUIStore((state) => state.theme);

  // Keep the default light theme unless the user has already chosen one.
  // Auto-following OS dark mode made headed tests and first visits look broken.

  // Apply dark class to html element whenever theme changes
  useEffect(() => {
    const root = document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }, [theme]);

  return <>{children}</>;
}
