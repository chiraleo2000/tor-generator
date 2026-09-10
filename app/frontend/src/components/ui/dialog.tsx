"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
}

function Dialog({ open, onOpenChange, children }: Readonly<DialogProps>) {
  const dialogRef = React.useRef<HTMLDialogElement>(null);
  const onOpenChangeRef = React.useRef(onOpenChange);
  onOpenChangeRef.current = onOpenChange;

  // Open/close only when `open` flips — do not close during listener refresh,
  // or chat re-renders will dismiss the confirm dialog while ask() is pending.
  React.useLayoutEffect(() => {
    const node = dialogRef.current;
    if (!node) return;
    if (open) {
      if (!node.open) {
        node.showModal();
      }
      return;
    }
    if (node.open) {
      node.close();
    }
  }, [open]);

  React.useLayoutEffect(() => {
    const node = dialogRef.current;
    if (!open || !node) return;

    const handleCancel = (event: Event) => {
      event.preventDefault();
      onOpenChangeRef.current(false);
    };
    const handleBackdropClick = (event: MouseEvent) => {
      if (event.target === node) {
        onOpenChangeRef.current(false);
      }
    };

    node.addEventListener("cancel", handleCancel);
    node.addEventListener("click", handleBackdropClick);
    return () => {
      node.removeEventListener("cancel", handleCancel);
      node.removeEventListener("click", handleBackdropClick);
    };
  }, [open]);

  if (!open) {
    return null;
  }

  return (
    <dialog
      ref={dialogRef}
      className="fixed left-1/2 top-1/2 z-[100] w-[min(100%-2rem,32rem)] max-h-[90vh] -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border bg-background p-0 shadow-lg backdrop:bg-black/50"
      aria-modal="true"
    >
      <div className="p-6">{children}</div>
    </dialog>
  );
}

function DialogHeader({
  className,
  ...props
}: Readonly<React.HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={cn("flex flex-col space-y-1.5 text-center sm:text-left", className)}
      {...props}
    />
  );
}

function DialogTitle({
  className,
  children,
  ...props
}: Readonly<React.HTMLAttributes<HTMLHeadingElement>>) {
  return (
    <h2
      className={cn("text-lg font-semibold leading-none tracking-tight", className)}
      {...props}
    >
      {children}
    </h2>
  );
}

function DialogDescription({
  className,
  children,
  ...props
}: Readonly<React.HTMLAttributes<HTMLParagraphElement>>) {
  return (
    <p
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    >
      {children}
    </p>
  );
}

function DialogFooter({
  className,
  ...props
}: Readonly<React.HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={cn(
        "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2 mt-4",
        className
      )}
      {...props}
    />
  );
}

export { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter };
