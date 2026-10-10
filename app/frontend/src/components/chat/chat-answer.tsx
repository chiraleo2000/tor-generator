"use client";

import { Database } from "lucide-react";
import { splitDraftBlocks } from "@/components/draft/rich-draft-text";
import type { ChatCitation } from "@/lib/chat-sse";
import { cn } from "@/lib/utils";

export type OnlineSourceItem = { title: string; url: string; date?: string };

export type ChatBlock =
  | { kind: "heading"; text: string }
  | { kind: "para"; text: string }
  | { kind: "list"; items: string[] }
  | { kind: "table"; rows: string[][] }
  | { kind: "source"; text: string }
  | { kind: "online"; items: OnlineSourceItem[] };

export type ChatSection = { heading: string | null; blocks: ChatBlock[] };

const SOURCE_LINE = /^(แหล่งข้อมูล|แหล่งอ้างอิง|แหล่งออนไลน์|เอกสารในคลัง)\s*[:：]/;
const LIST_BULLETS = new Set(["-", "*", "•"]);
const SOURCE_SEPARATORS = "—–-|:";
const ONLINE_HEADINGS = new Set([
  "แหล่งออนไลน์",
  "แหล่งจากเว็บ",
  "แหล่งข้อมูลออนไลน์",
]);
const SECTION_TITLES = new Set([
  "สรุปคำตอบ",
  "สรุปภาพรวม",
  "หลักที่เกี่ยวข้อง",
  "เงื่อนไข ข้อยกเว้น และวงเงิน",
  "ข้อควรระวัง",
  "ข้อสังเกตเชิงนโยบาย",
  "สาระสำคัญ",
  "เอกสารในคลัง",
  ...Array.from(ONLINE_HEADINGS),
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

export const MAX_VISIBLE_CITATION_CHIPS = 8;

function _citationRank(type: string): number {
  if (type === "document") return 0;
  if (type === "article") return 1;
  if (type === "mcp") return 2;
  return 3;
}

/** Collapse mcp+document duplicates of the same file so Gemini RAG does not flood the bar. */
export function uniqueCitations(citations: ChatCitation[]): ChatCitation[] {
  const byLabel = new Map<string, ChatCitation>();
  for (const cite of citations) {
    const label = (cite.label || "").trim();
    if (!label) continue;
    const key = label.toLowerCase();
    const existing = byLabel.get(key);
    if (!existing || _citationRank(cite.type) < _citationRank(existing.type)) {
      byLabel.set(key, cite);
    }
  }
  return Array.from(byLabel.values());
}

function isWhitespace(ch: string): boolean {
  return ch.trim() === "";
}

function isAsciiDigit(ch: string): boolean {
  return ch >= "0" && ch <= "9";
}

function skipWhitespace(text: string, index: number): number {
  let cursor = index;
  while (cursor < text.length && isWhitespace(text[cursor])) cursor += 1;
  return cursor;
}

function listMarkerEnd(text: string, index: number): number {
  if (index >= text.length) return -1;
  if (LIST_BULLETS.has(text[index])) return index + 1;
  if (!isAsciiDigit(text[index])) return -1;
  let cursor = index;
  while (cursor < text.length && isAsciiDigit(text[cursor])) cursor += 1;
  if (cursor < text.length && (text[cursor] === "." || text[cursor] === ")")) return cursor + 1;
  return -1;
}

function listItemCapture(line: string): string | null {
  const marker = listMarkerEnd(line, skipWhitespace(line, 0));
  if (marker < 0 || marker >= line.length || !isWhitespace(line[marker])) return null;
  const rest = line.slice(marker);
  if (rest.length < 2) return null;
  let splitAt = 0;
  while (splitAt < rest.length - 1 && isWhitespace(rest[splitAt])) splitAt += 1;
  return rest.slice(splitAt);
}

function hashHeadingBody(trimmed: string): string | null {
  let hashes = 0;
  while (hashes < trimmed.length && hashes < 3 && trimmed[hashes] === "#") hashes += 1;
  if (hashes < 1 || (hashes < trimmed.length && trimmed[hashes] === "#")) return null;
  if (hashes >= trimmed.length || !isWhitespace(trimmed[hashes])) return null;
  const rest = trimmed.slice(hashes);
  if (rest.length < 2) return null;
  let splitAt = 0;
  while (splitAt < rest.length - 1 && isWhitespace(rest[splitAt])) splitAt += 1;
  return rest.slice(splitAt);
}

function boldWrapped(text: string): string | null {
  if (!text.startsWith("**") || !text.endsWith("**") || text.length < 5) return null;
  return text.slice(2, -2);
}

export function isNumericCell(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;
  let compact = "";
  for (const ch of trimmed) {
    if (ch !== "," && !isWhitespace(ch)) compact += ch;
  }
  return /^[+-]?\d+(\.\d+)?%?$/.test(compact);
}

function stripMarkdown(value: string): string {
  return value.replaceAll("**", "").trim();
}

function looksLikeSectionTitle(title: string): boolean {
  return SECTION_TITLES.has(stripMarkdown(title));
}

function headingText(line: string): string | null {
  const trimmed = line.trim();
  const hashed = hashHeadingBody(trimmed);
  if (hashed !== null) return stripMarkdown(hashed);
  const boldOnly = boldOnlyTitle(trimmed);
  if (boldOnly !== null) {
    const title = stripMarkdown(boldOnly);
    if (looksLikeSectionTitle(title) || (title.length <= 40 && !title.includes(".") && !title.includes("。"))) {
      return title;
    }
  }
  if (looksLikeSectionTitle(trimmed) && listItemCapture(trimmed) === null) {
    return stripMarkdown(trimmed);
  }
  return null;
}

function boldOnlyTitle(trimmed: string): string | null {
  if (!trimmed.startsWith("**") || !trimmed.endsWith("**")) return null;
  const close = trimmed.lastIndexOf("**");
  if (close <= 2) return null;
  return trimmed.slice(2, close);
}

function splitInlineHeading(line: string): { heading: string; rest: string } | null {
  const trimmed = line.trim();
  if (!trimmed.startsWith("**")) return null;
  const close = trimmed.indexOf("**", 2);
  if (close <= 2) return null;
  const after = trimmed.slice(close + 2);
  if (!after || !isWhitespace(after[0]) || after.length < 2) return null;
  let splitAt = 0;
  while (splitAt < after.length - 1 && isWhitespace(after[splitAt])) splitAt += 1;
  const heading = trimmed.slice(2, close);
  if (!looksLikeSectionTitle(heading)) return null;
  return { heading: stripMarkdown(heading), rest: after.slice(splitAt).trim() };
}

function listItemText(line: string): string | null {
  const capture = listItemCapture(line);
  return capture === null ? null : capture.trim();
}

function isHttpUrl(url: string): boolean {
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function httpAt(text: string, from = 0): number {
  const secure = text.indexOf("https://", from);
  const plain = text.indexOf("http://", from);
  if (secure < 0) return plain;
  if (plain < 0) return secure;
  return Math.min(secure, plain);
}

function isSourceSeparator(ch: string): boolean {
  return SOURCE_SEPARATORS.includes(ch);
}

function trimEdgeDecor(value: string): string {
  let start = 0;
  let end = value.length;
  const decor = (ch: string) => isSourceSeparator(ch) || ch === "." || isWhitespace(ch);
  while (start < end && decor(value[start])) start += 1;
  while (end > start && decor(value[end - 1])) end -= 1;
  return value.slice(start, end);
}

function trimLeadingDecor(value: string): string {
  let start = 0;
  const decor = (ch: string) => isSourceSeparator(ch) || ch === "." || ch === "," || isWhitespace(ch);
  while (start < value.length && decor(value[start])) start += 1;
  return value.slice(start);
}

function readUrlToken(text: string, start: number): string {
  let end = start;
  while (end < text.length && !isWhitespace(text[end]) && text[end] !== ")") end += 1;
  return text.slice(start, end);
}

function markdownLink(text: string): { title: string; url: string; raw: string } | null {
  let from = 0;
  while (from < text.length) {
    const open = text.indexOf("[", from);
    if (open < 0) return null;
    const close = text.indexOf("]", open + 1);
    if (close < 0) return null;
    const title = text.slice(open + 1, close);
    if (title && text[close + 1] === "(") {
      const url = readUrlToken(text, close + 2);
      if ((url.startsWith("https://") || url.startsWith("http://")) && text[close + 2 + url.length] === ")") {
        const rawEnd = close + 2 + url.length + 1;
        return { title, url, raw: text.slice(open, rawEnd) };
      }
    }
    from = open + 1;
  }
  return null;
}

function labeledSource(plain: string): OnlineSourceItem | null {
  const urlAt = httpAt(plain);
  if (urlAt <= 0) return null;
  let cursor = urlAt;
  while (cursor > 0 && isWhitespace(plain[cursor - 1])) cursor -= 1;
  if (cursor === 0 || !isSourceSeparator(plain[cursor - 1])) return null;
  const url = readUrlToken(plain, urlAt);
  if (!isHttpUrl(url)) return null;
  let date = plain.slice(urlAt + url.length).trim();
  if (date && isSourceSeparator(date[0])) date = date.slice(1).trim();
  else date = "";
  const title = plain.slice(0, cursor - 1).trim();
  return { title: title || url, url, date: date || undefined };
}

export function parseOnlineSourceItem(text: string): OnlineSourceItem | null {
  const markdown = markdownLink(text);
  if (markdown && isHttpUrl(markdown.url)) {
    const rest = trimLeadingDecor(text.replace(markdown.raw, "")).trim();
    return { title: stripMarkdown(markdown.title), url: markdown.url, date: rest || undefined };
  }
  const labeled = labeledSource(stripMarkdown(text));
  if (labeled) return labeled;
  const plain = stripMarkdown(text);
  const bareAt = httpAt(plain);
  if (bareAt < 0) return null;
  const bare = readUrlToken(plain, bareAt);
  if (!isHttpUrl(bare)) return null;
  const title = trimEdgeDecor(plain.replace(bare, "")).trim();
  return { title: title || bare, url: bare };
}

function collectOnlineItems(blocks: ChatBlock[]): OnlineSourceItem[] {
  const items: OnlineSourceItem[] = [];
  for (const block of blocks) {
    if (block.kind === "list") {
      for (const item of block.items) {
        const parsed = parseOnlineSourceItem(item);
        if (parsed) items.push(parsed);
      }
    } else if (block.kind === "para" || block.kind === "source") {
      const parsed = parseOnlineSourceItem(block.text);
      if (parsed) items.push(parsed);
    } else if (block.kind === "online") {
      items.push(...block.items);
    }
  }
  return items;
}

function attachOnlineBlocks(blocks: ChatBlock[]): ChatBlock[] {
  const out: ChatBlock[] = [];
  let index = 0;
  while (index < blocks.length) {
    const block = blocks[index];
    if (block.kind === "heading" && ONLINE_HEADINGS.has(block.text)) {
      index += 1;
      const consumed: ChatBlock[] = [];
      while (index < blocks.length && blocks[index].kind !== "heading") {
        consumed.push(blocks[index]);
        index += 1;
      }
      const items = collectOnlineItems(consumed);
      if (items.length) {
        out.push({ kind: "online", items });
      } else {
        out.push(block, ...consumed);
      }
      continue;
    }
    out.push(block);
    index += 1;
  }
  return out;
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
  return attachOnlineBlocks(out);
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

type ParagraphAcc = { blocks: ChatBlock[]; para: string[]; list: string[] };

function flushParagraph(acc: ParagraphAcc) {
  const body = acc.para.join("\n").trim();
  if (body) acc.blocks.push({ kind: "para", text: body });
  acc.para = [];
}

function flushList(acc: ParagraphAcc) {
  if (acc.list.length) acc.blocks.push({ kind: "list", items: acc.list });
  acc.list = [];
}

function absorbSourceLine(acc: ParagraphAcc, sourceLine: string) {
  flushParagraph(acc);
  flushList(acc);
  if (sourceLine.startsWith("แหล่งออนไลน์")) {
    const parsed = parseOnlineSourceItem(sourceLine);
    if (parsed) {
      acc.blocks.push({ kind: "online", items: [parsed] });
      return;
    }
  }
  acc.blocks.push({ kind: "source", text: sourceLine });
}

function absorbParagraphLine(acc: ParagraphAcc, line: string) {
  const inline = splitInlineHeading(line);
  if (inline) {
    flushParagraph(acc);
    flushList(acc);
    acc.blocks.push({ kind: "heading", text: inline.heading });
    if (inline.rest) acc.para.push(inline.rest);
    return;
  }
  const heading = headingText(line);
  if (heading) {
    flushParagraph(acc);
    flushList(acc);
    acc.blocks.push({ kind: "heading", text: heading });
    return;
  }
  if (SOURCE_LINE.test(line.trim())) {
    absorbSourceLine(acc, line.trim());
    return;
  }
  const item = listItemText(line);
  if (item) {
    flushParagraph(acc);
    acc.list.push(item);
    return;
  }
  if (!line.trim()) {
    flushParagraph(acc);
    flushList(acc);
    return;
  }
  flushList(acc);
  acc.para.push(line);
}

function parseRichParagraph(text: string): ChatBlock[] {
  const acc: ParagraphAcc = { blocks: [], para: [], list: [] };
  for (const line of text.replaceAll("\r\n", "\n").split("\n")) {
    absorbParagraphLine(acc, line);
  }
  flushParagraph(acc);
  flushList(acc);
  return acc.blocks;
}

function InlineMd({ text }: Readonly<{ text: string }>) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return (
    <>
      {parts.map((part, index) => {
        const bold = boldWrapped(part);
        if (bold) {
          return (
            <strong key={`b-${index}-${bold.slice(0, 12)}`} className="font-semibold text-slate-800">
              {bold}
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
  if (block.kind === "online") return `o-${index}-${block.items[0]?.url || ""}`;
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
    <div className="max-w-full min-w-0 overflow-x-auto">
      <table className="w-full min-w-[28rem] border-collapse text-[13.5px]">
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
  if (block.kind === "online") {
    return (
      <div
        key={key}
        data-testid="chat-online-sources"
        className="rounded-xl border border-slate-200 bg-slate-50/80 px-3 py-2.5"
      >
        <p className="text-[12px] font-medium text-slate-500">แหล่งออนไลน์</p>
        <ul className="mt-1.5 space-y-1.5">
          {block.items.map((item) => (
            <li key={`${item.url}-${item.title}`} className="text-[13px] leading-relaxed">
              <a
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-navy underline-offset-2 hover:underline"
              >
                {item.title}
              </a>
              {item.date ? <span className="text-slate-500"> · {item.date}</span> : null}
            </li>
          ))}
        </ul>
      </div>
    );
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
    <div className={cn("min-w-0 max-w-full space-y-5", className)}>
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
  const unique = uniqueCitations(citations);
  if (!unique.length) return null;
  const visible = unique.slice(0, MAX_VISIBLE_CITATION_CHIPS);
  const extra = unique.length - visible.length;
  return (
    <div
      className="mt-4 flex max-w-full min-w-0 flex-wrap items-center gap-1.5 border-t border-slate-100 pt-3"
      data-testid="chat-source-bar"
    >
      <span className="inline-flex items-center gap-1 rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-600">
        <Database className="h-3 w-3" />
        แหล่งข้อมูล
      </span>
      {visible.map((cite) => (
        <span
          key={`${cite.type}-${cite.label}`}
          data-testid="chat-citation"
          className="max-w-[16rem] truncate rounded-full bg-slate-50 px-2 py-0.5 text-[11px] text-navy"
          title={citationChipText(cite)}
        >
          {citationChipText(cite)}
        </span>
      ))}
      {extra > 0 ? (
        <span
          className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600"
          data-testid="chat-citation-more"
        >
          +{extra}
        </span>
      ) : null}
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
