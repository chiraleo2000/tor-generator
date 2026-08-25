"use client";

import { cn } from "@/lib/utils";

export function UploadArea({
  hint,
  label,
  onFiles,
}: Readonly<{
  label: string;
  hint: string;
  onFiles: (files: FileList) => void;
}>) {
  return (
    <label
      className={cn(
        "block cursor-pointer rounded-[10px] border-2 border-dashed border-navy bg-gray-50 p-6 text-center transition-colors",
        "hover:border-crimson hover:bg-brand-orange"
      )}
    >
      <input
        type="file"
        className="hidden"
        multiple
        accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg"
        onChange={(event) => {
          if (event.target.files?.length) onFiles(event.target.files);
        }}
      />
      <p className="text-sm font-semibold text-navy">{label}</p>
      <p className="mt-1 text-[11.5px] text-muted-foreground">{hint}</p>
    </label>
  );
}
