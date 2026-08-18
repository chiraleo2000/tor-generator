import { Check, CircleAlert, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function CheckItem({
  tone,
  title,
  detail,
}: Readonly<{
  tone: "pass" | "warn" | "fail";
  title: string;
  detail?: string;
}>) {
  const Icon = { pass: Check, warn: CircleAlert, fail: X }[tone];
  const color = {
    pass: "text-brand-green",
    warn: "text-amber-700",
    fail: "text-crimson",
  }[tone];
  return (
    <div className="mb-2.5 flex gap-2.5 rounded-md border bg-white p-3">
      <Icon className={cn("mt-0.5 h-5 w-5 shrink-0", color)} aria-hidden />
      <div>
        <p className="text-sm font-semibold">{title}</p>
        {detail ? <p className="text-[12px] text-muted-foreground">{detail}</p> : null}
      </div>
    </div>
  );
}
