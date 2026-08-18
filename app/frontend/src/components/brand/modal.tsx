"use client";

import { Button } from "@/components/ui/button";

export function Modal({
  open,
  title,
  onClose,
  children,
}: Readonly<{
  open: boolean;
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}>) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-lg rounded-[14px] bg-white p-5 shadow-xl">
        <div className="mb-3 flex items-start justify-between gap-3">
          <h2 className="text-lg font-extrabold text-navy">{title}</h2>
          <Button variant="outline" size="sm" onClick={onClose}>
            ปิด
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}
