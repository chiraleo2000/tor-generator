import { cn } from "@/lib/utils";

export function StatCard({
  title,
  value,
  hint,
  tone,
}: Readonly<{
  title: string;
  value: number;
  hint: string;
  tone: "draft" | "progress" | "done";
}>) {
  const border = {
    draft: "border-t-[#f59e0b]",
    progress: "border-t-navy",
    done: "border-t-brand-green",
  }[tone];
  return (
    <div className={cn("gov-card border-t-4", border)}>
      <h3 className="mb-2 text-[12.5px] uppercase tracking-wide text-muted-foreground">
        {title}
      </h3>
      <p className="text-[30px] font-extrabold text-navy">{value}</p>
      <p className="mt-1 text-[12.5px] text-muted-foreground">{hint}</p>
    </div>
  );
}
