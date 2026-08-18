import { cn } from "@/lib/utils";

export function StatusPill({
  status,
}: Readonly<{ status: string }>) {
  const map: Record<string, { label: string; className: string }> = {
    draft: { label: "ร่าง", className: "bg-[#fef3e2] text-[#92400e]" },
    in_review: { label: "กำลังดำเนินการ", className: "bg-[#dbeafe] text-[#1e40af]" },
    progress: { label: "กำลังดำเนินการ", className: "bg-[#dbeafe] text-[#1e40af]" },
    approved: { label: "เสร็จแล้ว", className: "bg-[#dcfce7] text-[#166534]" },
    done: { label: "เสร็จแล้ว", className: "bg-[#dcfce7] text-[#166534]" },
    rejected: { label: "ส่งกลับ", className: "bg-[#fee2e2] text-[#b91c1c]" },
    archived: { label: "เก็บถาวร", className: "bg-gray-100 text-gray-600" },
  };
  const item = map[status] || map.draft;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold",
        item.className
      )}
    >
      {item.label}
    </span>
  );
}
