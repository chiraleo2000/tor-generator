"use client";

import { useEffect, useState } from "react";
import { X, CheckCircle, AlertCircle, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUIStore } from "@/stores/ui-store";
import type { Toast, ToastType } from "@/types";

const toastConfig: Record<
  ToastType,
  { icon: React.ElementType; className: string }
> = {
  success: {
    icon: CheckCircle,
    className: "border-green-500 bg-green-50 text-green-900 dark:bg-green-950 dark:text-green-100",
  },
  error: {
    icon: AlertCircle,
    className: "border-red-500 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100",
  },
  warning: {
    icon: AlertTriangle,
    className: "border-yellow-500 bg-yellow-50 text-yellow-900 dark:bg-yellow-950 dark:text-yellow-100",
  },
  info: {
    icon: Info,
    className: "border-blue-500 bg-blue-50 text-blue-900 dark:bg-blue-950 dark:text-blue-100",
  },
};

export function ToastContainer() {
  const toasts = useUIStore((state) => state.toasts);
  const removeToast = useUIStore((state) => state.removeToast);

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex flex-col gap-2"
      aria-live="polite"
      aria-label="การแจ้งเตือน"
      data-testid="toast-region"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onDismiss={removeToast} />
      ))}
    </div>
  );
}

function ToastItem({
  toast,
  onDismiss,
}: Readonly<{
  toast: Toast;
  onDismiss: (id: string) => void;
}>) {
  const [isVisible, setIsVisible] = useState(false);

  // Animate in on mount
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 10);
    return () => clearTimeout(timer);
  }, []);

  const config = toastConfig[toast.type];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex w-80 items-start gap-3 rounded-lg border-l-4 p-4 shadow-lg transition-all duration-300",
        config.className,
        isVisible
          ? "translate-x-0 opacity-100"
          : "translate-x-full opacity-0"
      )}
      role="alert"
    >
      <Icon className="mt-0.5 h-5 w-5 shrink-0" />
      <div className="flex-1 space-y-1">
        <p className="text-sm font-medium">{toast.title}</p>
        {toast.message && (
          <p className="text-xs opacity-80">{toast.message}</p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onDismiss(toast.id)}
        className="shrink-0 rounded-md p-1 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="ปิดการแจ้งเตือน"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
