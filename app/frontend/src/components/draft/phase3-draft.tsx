"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { MappingBox } from "@/components/brand/mapping-box";
import { scopeSubsectionsFor } from "@/lib/tor-profiles";
import {
  SECTION_FIELDS,
  formatScopeSubHeading,
  isSectionFilled,
  parseSectionDraft,
  previewSectionDraft,
  sectionIndexPad,
  serializeSectionDraft,
  type SectionField,
} from "@/lib/tor-sections";
import { cn } from "@/lib/utils";
import type { SectionPayload } from "@/components/draft/draft-types";
import { DraftChat } from "@/components/draft/draft-chat";
import { RichDraftText } from "@/components/draft/rich-draft-text";

function parseFields(sectionKey: string, content: string): Record<string, string> {
  return parseSectionDraft(sectionKey, content);
}

function displayExtracted(value: unknown): string {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return "";
}

function sectionIndexClass(filled: boolean, expanded: boolean): string {
  if (filled) return "text-brand-green";
  if (expanded) return "text-navy";
  return "text-muted-foreground";
}

function previewText(sectionKey: string, content: string): string {
  return previewSectionDraft(sectionKey, content);
}

export function Phase3Draft({
  sections,
  expanded,
  openSub,
  extracted,
  busy,
  actionError,
  actionInfo,
  onExpand,
  onOpenSub,
  onSave,
  onDraft,
  onBack,
  onConfirm,
  projectId,
  onRefresh,
  onDraftingChange,
}: Readonly<{
  sections: SectionPayload[];
  expanded: string;
  openSub: string;
  extracted: Record<string, unknown>;
  busy: boolean;
  actionError: string | null;
  actionInfo: string | null;
  onExpand: (key: string) => void;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
  onDraft: (key: string) => void;
  onBack: () => void;
  onConfirm: () => Promise<void>;
  projectId?: string;
  onRefresh?: () => void;
  onDraftingChange?: (busy: boolean) => void;
}>) {
  const [allDrafted, setAllDrafted] = useState(false);
  const filledCount = sections.filter((section) => isSectionFilled(section)).length;
  // Require persisted section content — chat "all drafted" alone used to enable
  // the button while confirm still blocked on empty filled flags.
  const draftedEnough = sections.length > 0 && filledCount >= sections.length;
  const canReview = !projectId || draftedEnough;

  return (
    <div className="space-y-4" data-testid="phase3-draft">
      <div className="gov-card">
        <h3 className="mb-1 text-navy" data-testid="phase3-heading">
          ขั้นที่ ๓: ร่างเนื้อหา — คุยแล้วให้ระบบร่าง
        </h3>
        <p className="mb-4 text-xs text-muted-foreground">
          ระบบร่างหมวดตามประเภทงานที่เลือก เป็นภาษาไทยจากเอกสารขั้นที่ ๐ ของโครงการนี้และกฎหมายกลาง
          แล้วใส่ลงหัวข้อย่อยของแต่ละหมวดโดยตรง
          กดไปทบทวนแล้วระบบตรวจกับ พ.ร.บ. การจัดซื้อจัดจ้าง กฎระเบียบ และเอกสารที่อัปโหลดในขั้นที่ ๐ ของโครงการนี้
          ตารางในเนื้อหาจะกลายเป็นตารางจริงในไฟล์เวิร์ด/พีดีเอฟ
        </p>
        {busy ? (
          <p className="mb-3 text-sm text-navy">
            {actionInfo || "กำลังร่างด้วยระบบอัจฉริยะ..."}
          </p>
        ) : null}
        {actionError ? (
          <p className="mb-3 text-sm text-destructive" role="alert">
            {actionError}
          </p>
        ) : null}
        {actionInfo ? <p className="mb-3 text-sm text-brand-green">{actionInfo}</p> : null}
        {allDrafted && draftedEnough ? (
          <p className="mb-3 text-sm font-bold text-green-800" data-testid="phase3-all-drafted">
            ร่างครบทุกหมวดตามประเภทงานแล้ว — กดไปทบทวน (ขั้นที่ ๔) เพื่อตรวจกฎและส่งออก
          </p>
        ) : null}
        {allDrafted && !draftedEnough ? (
          <p className="mb-3 text-sm text-amber-800" data-testid="phase3-draft-pending-save">
            ระบบร่างครบแล้ว แต่บางหมวดยังไม่มีเนื้อหาที่บันทึก — กดบันทึกหมวดหรือรอรีเฟรชรายการหมวดก่อนเข้าทบทวน
          </p>
        ) : null}
      </div>
      {projectId ? (
        <DraftChat
          projectId={projectId}
          onAllDrafted={() => {
            setAllDrafted(true);
            onRefresh?.();
          }}
          onSectionDone={onRefresh}
          onDraftingChange={onDraftingChange}
        />
      ) : null}
      <div className="gov-card">
      <div className="flex flex-col">
        {sections.map((section, index) => (
          <SectionCard
            key={section.key}
            section={section}
            last={index === sections.length - 1}
            expanded={expanded === section.key}
            openSub={openSub}
            extracted={extracted}
            busy={busy}
            onToggle={() => onExpand(expanded === section.key ? "" : section.key)}
            onOpenSub={onOpenSub}
            onSave={onSave}
            onDraft={onDraft}
          />
        ))}
      </div>
      <div className="mt-4 flex justify-between">
        <Button variant="secondary" onClick={onBack} data-testid="phase2-back">
          ย้อนกลับ
        </Button>
        <Button
          onClick={() => {
            void onConfirm();
          }}
          disabled={!canReview}
          data-testid="phase3-confirm"
        >
          ไปทบทวน (ขั้นที่ ๔)
        </Button>
      </div>
      </div>
    </div>
  );
}

function SectionCard({
  section,
  last,
  expanded,
  openSub,
  extracted,
  busy,
  onToggle,
  onOpenSub,
  onSave,
  onDraft,
}: Readonly<{
  section: SectionPayload;
  last: boolean;
  expanded: boolean;
  openSub: string;
  extracted: Record<string, unknown>;
  busy: boolean;
  onToggle: () => void;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
  onDraft: (key: string) => void;
}>) {
  const fields = SECTION_FIELDS[section.key] || [
    { key: "body", label: section.title, type: "textarea" as const },
  ];
  const values = parseFields(section.key, section.content);
  const [draft, setDraft] = useState(values);
  useEffect(() => {
    const parsed = parseFields(section.key, section.content);
    const fieldList = SECTION_FIELDS[section.key] || [];
    const next = { ...parsed };
    for (const field of fieldList) {
      if (next[field.key]?.trim()) continue;
      if (!field.mapField) continue;
      const hint = displayExtracted(extracted[field.mapField]);
      if (hint) next[field.key] = hint;
    }
    setDraft(next);
  }, [section.content, section.key, extracted]);

  function suggested(mapField?: string) {
    if (!mapField) return "";
    return displayExtracted(extracted[mapField]);
  }

  const filled = isSectionFilled(section);
  const indexPad = sectionIndexPad(section.key);

  return (
    <div className="flex gap-3">
      <div className="flex w-10 shrink-0 flex-col items-center pt-3.5">
        <span
          className={cn(
            "font-mono text-[11px] font-semibold tabular-nums tracking-wide",
            sectionIndexClass(filled, expanded)
          )}
          aria-hidden
        >
          {indexPad}
        </span>
        {!last ? (
          <div
            className={cn(
              "mt-2 w-px flex-1",
              filled ? "bg-brand-green/40" : "bg-gray-200"
            )}
          />
        ) : null}
      </div>
      <div
        className={cn(
          "mb-2 flex-1 overflow-hidden border-b",
          expanded ? "border-navy/25 bg-slate-50/80" : "border-gray-100"
        )}
      >
        <button
          type="button"
          className="flex w-full items-start justify-between gap-3 px-1 py-3 text-left"
          onClick={onToggle}
          aria-expanded={expanded}
        >
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
              <h3 className="text-sm font-semibold text-navy">{section.title}</h3>
              <span
                className={cn(
                  "text-[10px] tracking-wide text-muted-foreground",
                  filled ? "text-brand-green" : ""
                )}
              >
                {filled ? "ร่างแล้ว" : "รอร่าง"}
              </span>
            </div>
            <p
              data-testid={`section-preview-${section.key}`}
              className="mt-1 line-clamp-2 text-xs leading-relaxed text-muted-foreground"
            >
              {previewText(section.key, section.content) || "รอระบบร่างจากข้อมูลที่คุยมา..."}
            </p>
          </div>
          <span className="shrink-0 pt-0.5 font-mono text-[10px] text-muted-foreground">
            {expanded ? "−" : "+"}
          </span>
        </button>
        {expanded ? (
          <div className="space-y-3 border-t border-gray-100 px-1 pb-4 pt-3">
            {section.big ? (
              <ScopeSubsectionEditor
                subs={section.subs}
                openSub={openSub}
                onOpenSub={onOpenSub}
                onSave={onSave}
              />
            ) : (
              <StandardSectionFields
                fields={fields}
                draft={draft}
                extracted={extracted}
                suggested={suggested}
                onChange={(key, next) =>
                  setDraft((prev) => ({ ...prev, [key]: next }))
                }
              />
            )}
            <div className="flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={busy}
                data-testid={`draft-ai-${section.key}`}
                onClick={() => onDraft(section.key)}
              >
                ร่างด้วยระบบอัจฉริยะ
              </Button>
              <Button
                size="sm"
                variant="outline"
                data-testid={`save-section-${section.key}`}
                onClick={() => onSave(section.key, serializeSectionDraft(draft), false)}
              >
                บันทึกหมวดนี้
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ScopeSubsectionEditor({
  subs,
  openSub,
  onOpenSub,
  onSave,
}: Readonly<{
  subs: SectionPayload["subs"];
  openSub: string;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
}>) {
  const chips = subs || scopeSubsectionsFor().map((item) => ({
    key: item.key,
    title: item.title,
    content: "",
    filled: false,
  }));
  const contentSig = chips.map((sub) => `${sub.key}:${sub.content || ""}`).join("|");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  useEffect(() => {
    const next: Record<string, string> = {};
    for (const sub of chips) {
      next[sub.key] = sub.content || "";
    }
    setDrafts(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- รีเฟรชเมื่อลายเซ็นเนื้อหาจากเอพีไอเปลี่ยน
  }, [contentSig]);
  const filledN = chips.filter((sub) => sub.filled).length;
  return (
    <div className="space-y-3" data-testid="scope-subsection-editor">
      <p className="text-xs text-muted-foreground">
        ขอบเขตงาน — หัวข้อย่อย ({filledN}/{chips.length} มีเนื้อหา) · รวมเป็นเอกสารเดียวตอนส่งออก
      </p>
      <div className="flex flex-wrap gap-1">
        {chips.map((sub) => (
          <button
            key={sub.key}
            type="button"
            className={cn(
              "border px-2 py-0.5 font-mono text-[11px] tabular-nums",
              sub.filled
                ? "border-brand-green/30 bg-green-50 text-green-900"
                : "border-gray-200 bg-white text-muted-foreground",
              openSub === sub.key ? "border-navy text-navy" : ""
            )}
            onClick={() => onOpenSub(openSub === sub.key ? "" : sub.key)}
          >
            {formatScopeSubHeading(sub.key, sub.title)}
          </button>
        ))}
      </div>
      <div className="max-h-[28rem] space-y-3 overflow-y-auto pr-1">
        {chips.map((sub) => {
          const expanded = openSub === sub.key || (!openSub && sub.filled);
          if (!expanded && openSub) return null;
          if (!openSub && !sub.filled) return null;
          return (
            <div
              key={sub.key}
              className="border-l-2 border-navy/40 bg-white py-2 pl-3"
              data-testid={`scope-sub-${sub.key}`}
            >
              <Label className="font-mono text-xs tabular-nums">
                {formatScopeSubHeading(sub.key, sub.title)}
              </Label>
              {sub.content ? (
                <div className="mt-1 mb-2 border bg-slate-50/80 p-2">
                  <RichDraftText text={sub.content} />
                </div>
              ) : null}
              <Textarea
                className="mt-1"
                value={drafts[sub.key] ?? sub.content}
                rows={5}
                onChange={(event) =>
                  setDrafts((prev) => ({ ...prev, [sub.key]: event.target.value }))
                }
                onBlur={(event) => onSave(sub.key, event.target.value)}
              />
            </div>
          );
        })}
      </div>
      {!openSub && filledN === 0 ? (
        <p className="text-xs text-amber-800">
          ยังไม่มีหัวข้อย่อย — กด «ร่างด้วยระบบอัจฉริยะ» เพื่อเติมตามประเภทงาน หรือเลือกหัวข้อด้านบนเพื่อพิมพ์เอง
        </p>
      ) : null}
    </div>
  );
}

function StandardSectionFields({
  fields,
  draft,
  extracted,
  suggested,
  onChange,
}: Readonly<{
  fields: SectionField[];
  draft: Record<string, string>;
  extracted: Record<string, unknown>;
  suggested: (mapField?: string) => string;
  onChange: (key: string, next: string) => void;
}>) {
  return (
    <>
      {fields.map((field) => {
        const value = draft[field.key] || suggested(field.mapField);
        const tag = field.mapField && extracted[field.mapField] ? "matched" : "partial";
        return (
          <div key={field.key}>
            <Label>{field.label}</Label>
            <SectionFieldControl
              field={field}
              value={value}
              onChange={(next) => onChange(field.key, next)}
            />
            {field.mapField ? (
              <MappingBox
                rows={[
                  {
                    field: field.mapField,
                    label: field.label,
                    value: suggested(field.mapField),
                    tag,
                  },
                ]}
              />
            ) : null}
          </div>
        );
      })}
    </>
  );
}

function SectionFieldControl({
  field,
  value,
  onChange,
}: Readonly<{
  field: SectionField;
  value: string;
  onChange: (next: string) => void;
}>) {
  if (field.type === "textarea") {
    return (
      <Textarea
        className="mt-1"
        value={value}
        maxLength={50000}
        onChange={(event) => onChange(event.target.value)}
      />
    );
  }
  if (field.type === "select") {
    return (
      <select
        className="mt-1 h-10 w-full rounded-md border px-3 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">เลือก</option>
        {(field.options || []).map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    );
  }
  return (
    <Input
      className="mt-1"
      type={field.type === "number" ? "text" : field.type}
      value={value}
      maxLength={2000}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}
