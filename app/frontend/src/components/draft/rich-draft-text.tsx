"use client";

/** Render plain TOR draft text with markdown pipe tables as HTML tables.
 * Also converts tab/space-aligned ICT license tables so Phase 3 preview
 * is never stuck showing raw plain-text columns.
 */

function isSepRow(line: string): boolean {
  return /^\|[\s\-:|]+\|$/.test(line.trim());
}

function isPipeRow(line: string): boolean {
  const t = line.trim();
  return t.startsWith("|") && t.endsWith("|");
}

function parseCells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function splitLooseCells(line: string): string[] {
  const trimmed = line.trim();
  if (!trimmed) return [];
  if (trimmed.includes("|")) {
    return parseCells(trimmed.startsWith("|") ? trimmed : `|${trimmed}|`);
  }
  if (trimmed.includes("\t")) {
    return trimmed.split(/\t+/).map((cell) => cell.trim()).filter(Boolean);
  }
  return trimmed.split(/ {2,}/).map((cell) => cell.trim()).filter(Boolean);
}

function isLicenseHeader(cells: string[]): boolean {
  const joined = cells.join("");
  return joined.includes("ลำดับ") && joined.includes("รายการ");
}

function isUseSubheader(cells: string[]): boolean {
  const nonempty = cells.filter((cell) => cell.trim());
  if (!nonempty.length) return true;
  return nonempty.every((cell) =>
    ["ใช้", "ไม่ใช้", "เกณฑ์กลาง ICT", "เกณฑ์กลาง"].includes(cell)
  );
}

function ictUse(...candidates: string[]): string {
  for (const raw of candidates) {
    const token = (raw || "").trim();
    if (!token) continue;
    if (/[✔✓√]/.test(token) || token === "ใช้" || token === "ใช่") return "ใช้";
    if (token === "ไม่ใช้" || token === "ไม่") return "ไม่ใช้";
  }
  return "";
}

/** Best-effort conversion of pasted Word/TSV ICT tables into pipe markdown. */
export function coerceLicenseMarkdown(text: string): string {
  if (!text?.trim()) return text;
  if (text.includes("| ลำดับ |") && text.includes("| ---")) return text;
  if (!(text.includes("ลำดับ") && text.includes("รายการ"))) return text;

  const lines = text.replaceAll("\r\n", "\n").split("\n");
  const rows: string[][] = [];
  const seen = new Set<string>();
  let inTable = false;

  for (const line of lines) {
    const cells = splitLooseCells(line);
    if (!cells.length) continue;
    if (isLicenseHeader(cells)) {
      inTable = true;
      continue;
    }
    if (inTable && isUseSubheader(cells)) continue;
    if (!inTable) continue;
    const first = cells[0] || "";
    if (!/^[0-9๐-๙]+$/.test(first) && first !== "รวม" && first !== "รวมทั้งสิ้น") {
      inTable = false;
      continue;
    }
    const padded = [...cells, "", "", "", "", "", "", ""];
    const use =
      cells.length >= 7 ? ictUse(padded[5], padded[6]) : ictUse(padded[5]);
    const row = [
      padded[0],
      padded[1],
      padded[2],
      padded[3],
      padded[4],
      use,
      cells.length >= 8 ? padded[7] : "",
    ];
    const key = row.join("|");
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push(row);
  }

  if (!rows.length) return text;
  const header = [
    "ลำดับ",
    "รายการ",
    "จำนวนสิทธิ์",
    "ราคาต่อหน่วย (บาท)",
    "ราคารวม (บาท)",
    "ใช้เกณฑ์กลาง ICT",
    "กรณีไม่ใช้เกณฑ์กลางให้ระบุเหตุผล",
  ];
  const md = [
    `| ${header.join(" | ")} |`,
    "| --- | --- | --- | --- | --- | --- | --- |",
    ...rows.map((row) => `| ${row.join(" | ")} |`),
  ];
  return md.join("\n");
}

type Block = { kind: "para"; text: string } | { kind: "table"; rows: string[][] };

export function splitDraftBlocks(text: string): Block[] {
  const lines = coerceLicenseMarkdown(text).replaceAll("\r\n", "\n").split("\n");
  const blocks: Block[] = [];
  let i = 0;
  let para: string[] = [];

  const flush = () => {
    const body = para.join("\n").trim();
    if (body) blocks.push({ kind: "para", text: body });
    para = [];
  };

  while (i < lines.length) {
    const line = lines[i];
    if (isPipeRow(line) && i + 1 < lines.length && isSepRow(lines[i + 1])) {
      flush();
      const rows: string[][] = [];
      while (i < lines.length && isPipeRow(lines[i])) {
        if (!isSepRow(lines[i])) rows.push(parseCells(lines[i]));
        i += 1;
      }
      if (rows.length) blocks.push({ kind: "table", rows });
      continue;
    }
    para.push(line);
    i += 1;
  }
  flush();
  return blocks;
}

function blockKey(block: Block, index: number): string {
  if (block.kind === "para") {
    return `p-${index}-${block.text.slice(0, 24)}`;
  }
  const head = block.rows[0]?.join("|") ?? "";
  return `t-${index}-${head.slice(0, 24)}`;
}

export function RichDraftText({
  text,
  className,
}: Readonly<{ text: string; className?: string }>) {
  if (!text?.trim()) return null;
  const blocks = splitDraftBlocks(text);
  return (
    <div className={className} data-testid="rich-draft-text">
      {blocks.map((block, index) => {
        if (block.kind === "table") {
          return (
            <div key={blockKey(block, index)} className="my-2 overflow-x-auto">
              <table className="w-full border-collapse text-left text-sm">
                <tbody>
                  {block.rows.map((row, rIdx) => {
                    const rowKey = `${rIdx}:${row.join("|")}`;
                    return (
                      <tr
                        key={rowKey}
                        className={rIdx === 0 ? "bg-gray-50 font-semibold" : ""}
                      >
                        {row.map((cell, cIdx) => (
                          <td
                            key={`${rowKey}:${cIdx}:${cell}`}
                            className="border border-gray-300 px-2 py-1 align-top"
                          >
                            {cell}
                          </td>
                        ))}
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        }
        return (
          <p key={blockKey(block, index)} className="whitespace-pre-wrap text-sm leading-relaxed">
            {block.text}
          </p>
        );
      })}
    </div>
  );
}
