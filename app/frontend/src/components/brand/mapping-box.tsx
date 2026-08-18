export interface MappingRow {
  field: string;
  label: string;
  value: string;
  tag: "matched" | "partial" | "missing";
}

export function MappingBox({ rows }: Readonly<{ rows: MappingRow[] }>) {
  if (!rows.length) return null;
  const tagClass = {
    matched: "bg-[#dcfce7] text-[#166534]",
    partial: "bg-[#fef3e2] text-[#92400e]",
    missing: "bg-[#fee2e2] text-[#b91c1c]",
  };
  const tagLabel = {
    matched: "สอดคล้อง",
    partial: "ยังไม่พบ — กรอกเอง",
    missing: "ขาด",
  };
  return (
    <div className="mt-2.5 rounded-lg border border-blue-200 bg-[#f0f7ff] p-3 text-[12.5px]">
      {rows.map((row) => (
        <div
          key={row.field}
          className="flex items-center justify-between gap-3 border-b border-dashed border-blue-100 py-1.5 last:border-0"
        >
          <span>
            {row.label}
            {row.value ? (
              <>
                : <strong>{row.value}</strong>
              </>
            ) : null}
          </span>
          <span className={`rounded px-2 py-0.5 text-[11px] font-bold ${tagClass[row.tag]}`}>
            {tagLabel[row.tag]}
          </span>
        </div>
      ))}
    </div>
  );
}
