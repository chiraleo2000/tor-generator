"use client";

import { Database } from "lucide-react";
import { splitDraftBlocks } from "@/components/draft/rich-draft-text";
import type { ChatCitation } from "@/lib/chat-sse";
import { cn } from "@/lib/utils";

export type ChatBlock =
  | { kind: "heading"; text: string }
  | { kind: "para"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "table"; rows: string[][] }
  | { kind: "source"; text: string };

export type ChatSection = { heading: string | null; blocks: ChatBlock[] };

const SOURCE_LINE = /^(แหล่งข้อมูล|แหล่งอ้างอิง)\s*[:：]/;
const LIST_ITEM = /^\s*(?:[-*•]|\d+[.)])\s+(.+)$/;
const SECTION_TITLES = new Set([
  "สรุปคำตอบ",
  "สรุปภาพรวม",
  "หลักที่เกี่ยวข้อง",
  "เงื่อนไข ข้อยกเว้น และวงเงิน",
  "ข้อควรระวัง",
  "ข้อสังเกตเชิงนโยบาย",
  "สาระสำคัญ",
]);

export function looksLikeNoRetrieve(
  content: string,
  citations: ChatCitation[] | undefined
): boolean {
  if (citations && citations.length > 0) return false;
  const text = content.trim();
  if (!text) return false;
  return /ไม่พบ|ยังไม่มีข้อมูลในคลัง|ไม่มีข้อมูลในคลัง|ดึงคลังไม่ได้|ไม่มีสิทธิ์|ไม่สามารถเข้าถึง|ไม่สามารถให้ข้อมูล|ไม่มีการเรียกใช้ข้อมูล/.test(
    text
  );
}

export function citationChipText(cite: ChatCitation): string {
  return `${cite.type}: ${cite.label}`;
}

export function isNumericCell(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  const compact = trimmed.replace(/,/g, "").replace(/\s/g, "");
  return /^[+-]?\d+(\.\d+)?%?$/.test(compact);
}

function stripMarkdown(value: string): string {
  return value.replace(/\*\*/g, "").trim();
}

function looksLikeSectionTitle(title: string): boolean {
  return SECTION_TITLES.has(stripMarkdown(title));
}

function headingText(line: string): string | null {
  const trimmed = line.trim();
  const hash = trimmed.match(/^#{1,3}\s+(.+)$/);
  if (hash) return stripMarkdown(hash[1]);
  const boldOnly = trimmed.match(/^\*\*(.+?)\*\*\s*$/);
  if (boldOnly) {
    const title = stripMarkdown(boldOnly[1]);
    if (looksLikeSectionTitle(title) || (title.length <= 40 && !/[.。]/.test(title))) {
      return title;
    }
  }
  if (looksLikeSectionTitle(trimmed) && !LIST_ITEM.test(trimmed)) {
    return stripMarkdown(trimmed);
  }
  return null;
}

function splitInlineHeading(line: string): { heading: string; rest: string } | null {
  const match = line.trim().match(/^\*\*(.+?)\*\*\s+(.+)$/);
  if (match && looksLikeSectionTitle(match[1])) {
    return { heading: stripMarkdown(match[1]), rest: match[2].trim() };
  }
  return null;
}

function listItemText(line: string): string | null {
  const match = line.match(LIST_ITEM);
  return match ? match[1].trim() : null;
}

export function parseChatBlocks(text: string): ChatBlock[] {
  const out: ChatBlock[] = [];
  for (const block of splitDraftBlocks(text)) {
    if (block.kind === "table") {
      out.push(block);
      continue;
    }
    out.push(...parseRichParagraph(block.text));
  }
  return out;
}

export function groupChatSections(blocks: ChatBlock[]): ChatSection[] {
  const sections: ChatSection[] = [];
  let current: ChatSection = { heading: null, blocks: [] };
  for (const block of blocks) {
    if (block.kind === "heading") {
      if (current.heading || current.blocks.length) sections.push(current);
      current = { heading: block.text, blocks: [] };
      continue;
    }
    current.blocks.push(block);
  }
  if (current.heading || current.blocks.length) sections.push(current);
  return sections;
}

function parseRichParagraph(text: string): ChatBlock[] {
  const lines = text.replaceAll("\r\n", "\n").split("\n");
  const blocks: ChatBlock[] = [];
  let para: string[] = [];
  let list: string[] = [];

  const flushPara = () => {
    const body = para.join("\n").trim();
    if (body) blocks.push({ kind: "para", text: body });
    para = [];
  };
  const flushList = () => {
    if (list.length) blocks.push({ kind: "list", items: list });
    list = [];
  };

  for (const line of lines) {
    const inline = splitInlineHeading(line);
    if (inline) {
      flushPara();
      flushList();
      blocks.push({ kind: "heading", text: inline.heading });
      if (inline.rest) para.push(inline.rest);
      continue;
    }
    const heading = headingText(line);
    if (heading) {
      flushPara();
      flushList();
      blocks.push({ kind: "heading", text: heading });
      continue;
    }
    if (SOURCE_LINE.test(line.trim())) {
      flushPara();
      flushList();
      blocks.push({ kind: "source", text: line.trim() });
      continue;
    }
    const item = listItemText(line);
    if (item) {
      flushPara();
      list.push(item);
      continue;
    }
    if (!line.trim()) {
      flushPara();
      flushList();
      continue;
    }
    flushList();
    para.push(line);
  }
  flushPara();
  flushList();
  return blocks;
}

function InlineMd({ text }: Readonly<{ text: string }>) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) => {
        const bold = part.match(/^\*\*(.+)\*\*$/);
        if (bold) {
          return (
            <strong key={`b-${index}-${bold[1].slice(0, 12)}`} className="font-semibold text-slate-800">
              {bold[1]}
            </strong>
          );
        }
        return <span key={`t-${index}-${part.slice(0, 12)}`}>{part}</span>;
      })}
    </>
  );
}

function blockKey(block: ChatBlock, index: number): string {
  if (block.kind === "heading") return `h-${index}-${block.text.slice(0, 20)}`;
  if (block.kind === "source") return `s-${index}-${block.text.slice(0, 20)}`;
  if (block.kind === "list") return `l-${index}-${block.items[0]?.slice(0, 16) || ""}`;
  if (block.kind === "table") {
    return `t-${index}-${block.rows[0]?.join("|").slice(0, 20) || ""}`;
  }
  return `p-${index}-${block.text.slice(0, 20)}`;
}

function BriefTable({ rows, blockKey: key }: Readonly<{ rows: string[][]; blockKey: string }>) {
  if (!rows.length) return null;
  const [header, ...body] = rows;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-[13.5px]">
        <thead>
          <tr>
            {header.map((cell, cIdx) => (
              <th
                key={`${key}-h-${cIdx}-${cell}`}
                className={cn(
                  "border-b border-slate-200 pb-2 pr-4 text-left text-[12.5px] font-medium text-slate-500",
                  cIdx > 0 && "text-right"
                )}
              >
                <InlineMd text={cell} />
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {body.map((row, rIdx) => {
            const rowKey = `${key}-${rIdx}:${row.join("|")}`;
            return (
              <tr key={rowKey} className="border-b border-slate-100 last:border-0">
                {row.map((cell, cIdx) => (
                  <td
                    key={`${rowKey}:${cIdx}`}
                    className={cn(
                      "py-2.5 pr-4 align-top text-slate-700",
                      cIdx === 0 ? "font-medium text-slate-800" : "",
                      cIdx > 0 && isNumericCell(cell) ? "text-right tabular-nums" : ""
                    )}
                  >
                    <InlineMd text={cell} />
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

function renderBodyBlock(block: ChatBlock, index: number) {
  const key = blockKey(block, index);
  if (block.kind === "list") {
    return (
      <ul key={key} className="space-y-1.5 pl-5 text-[14.5px] leading-[1.7] text-slate-600">
        {block.items.map((item) => (
          <li key={`${key}-${item.slice(0, 24)}`} className="list-disc marker:text-slate-400">
            <InlineMd text={item} />
          </li>
        ))}
      </ul>
    );
  }
  if (block.kind === "table") {
    return <BriefTable key={key} rows={block.rows} blockKey={key} />;
  }
  if (block.kind === "source") {
    return (
      <p key={key} className="pt-1 text-[12.5px] leading-relaxed text-slate-400">
        {block.text}
      </p>
    );
  }
  if (block.kind === "heading") {
    return (
      <h3 key={key} className="text-[15px] font-bold text-slate-800">
        {block.text}
      </h3>
    );
  }
  return (
    <p key={key} className="text-[14.5px] leading-[1.75] text-slate-600">
      <InlineMd text={block.text} />
    </p>
  );
}

export function ChatAnswerBody({
  text,
  className,
}: Readonly<{ text: string; className?: string }>) {
  if (!text.trim()) return null;
  const sections = groupChatSections(parseChatBlocks(text));
  return (
    <div className={cn("space-y-5", className)}>
      {sections.map((section, sIdx) => (
        <section
          key={`sec-${sIdx}-${section.heading || section.blocks[0]?.kind || "body"}`}
          className="space-y-2"
        >
          {section.heading ? (
            <h3 className="text-[15px] font-bold tracking-tight text-slate-800">
              {section.heading}
            </h3>
          ) : null}
          {section.blocks.map((block, index) => renderBodyBlock(block, index))}
        </section>
      ))}
    </div>
  );
}

export function ChatCitationBar({
  citations,
}: Readonly<{ citations: ChatCitation[] }>) {
  if (!citations.length) return null;
  return (
    <div
      className="mt-4 flex flex-wrap items-center gap-1.5 border-t border-slate-100 pt-3"
      data-testid="chat-source-bar"
    >
      <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
        <Database className="h-3 w-3" />
        แหล่งข้อมูล
      </span>
      {citations.map((cite) => (
        <span
          key={`${cite.type}-${cite.label}`}
          data-testid="chat-citation"
          className="rounded-full bg-slate-50 px-2 py-0.5 text-[11px] text-navy"
        >
          {citationChipText(cite)}
        </span>
      ))}
    </div>
  );
}

export function ChatSourceCards({
  citations,
}: Readonly<{ citations: ChatCitation[] }>) {
  if (citations.length < 2) return null;
  return (
    <div className="mt-3 grid gap-2 sm:grid-cols-2" data-testid="chat-source-cards">
      {citations.slice(0, 8).map((cite) => (
        <article
          key={`card-${cite.type}-${cite.label}`}
          className="rounded-xl border border-slate-200 bg-slate-50/80 p-3"
        >
          <p className="text-[13px] font-semibold text-navy">{cite.label}</p>
          <p className="mt-1 text-[11px] text-muted-foreground">{cite.type}</p>
        </article>
      ))}
    </div>
  );
}
