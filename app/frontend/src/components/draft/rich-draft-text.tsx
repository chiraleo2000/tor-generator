"use client";

/** Render plain TOR draft text with markdown pipe tables as HTML tables. */

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

type Block = { kind: "para"; text: string } | { kind: "table"; rows: string[][] };

export function splitDraftBlocks(text: string): Block[] {
  const lines = text.replaceAll("\r\n", "\n").split("\n");
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
