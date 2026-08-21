"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { MappingBox } from "@/components/brand/mapping-box";
import {
  HITL_SECTIONS,
  SCOPE_SUBSECTIONS,
  SECTION_FIELDS,
  serializeSectionDraft,
  type SectionField,
} from "@/lib/tor-sections";
import { cn } from "@/lib/utils";
import type { SectionPayload } from "@/components/draft/draft-types";
import { DraftChat } from "@/components/draft/draft-chat";

function parseFields(content: string): Record<string, string> {
  if (!content) return {};
  try {
    const parsed = JSON.parse(content) as unknown;
    if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
      return parsed as Record<string, string>;
    }
  } catch {
    return { body: content };
  }
  return { body: content };
}

function displayExtracted(value: unknown): string {
  if (typeof value === "string" || typeof value === "number") {
    return String(value);
  }
  return "";
}

function sectionCircleClass(filled: boolean, expanded: boolean): string {
  if (filled) return "border-[#0f5c22] bg-brand-green text-white";
  if (expanded) return "border-crimson bg-brand-orange text-navy";
  return "border-gray-300 bg-gray-200 text-gray-700";
}

function previewText(content: string): string {
  const fields = parseFields(content);
  return (fields.body || Object.values(fields).filter(Boolean).join(" ") || content).slice(0, 240);
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
}>) {
  return (
    <div className="space-y-4" data-testid="phase3-draft">
      <div className="gov-card">
        <h3 className="mb-1 text-navy">Phase 3: ร่างเนื้อหา TOR — คุยแล้วให้ระบบร่าง</h3>
        <p className="mb-4 text-xs text-muted-foreground">
          ระบบร่างทั้ง 13 หมวดจากข้อมูล Phase 1–2 อัตโนมัติ — ถ้าต้องการแก้ ให้คุยในแชท เช่น แก้ความเป็นมาให้เน้นกฎหมาย
          หมวดกฎหมายยังต้องกดยืนยันโดยเจ้าหน้าที่
        </p>
        {busy ? (
          <p className="mb-3 text-sm text-navy">
            {actionInfo || "กำลังร่างด้วย AI..."}
          </p>
        ) : null}
        {actionError ? (
          <p className="mb-3 text-sm text-destructive" role="alert">
            {actionError}
          </p>
        ) : null}
        {actionInfo ? <p className="mb-3 text-sm text-brand-green">{actionInfo}</p> : null}
      </div>
      {projectId ? (
        <DraftChat
          projectId={projectId}
          onAllDrafted={() => onRefresh?.()}
          onSectionDone={onRefresh}
        />
      ) : null}
      <div className="gov-card">
      <div className="flex flex-col">
        {sections.map((section, index) => (
          <SectionCard
            key={section.key}
            section={section}
            index={index}
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
        <Button onClick={() => { onConfirm().catch(() => undefined); }} data-testid="phase3-confirm">
          ยืนยันด้วยตนเอง — ไปทบทวน/เผยแพร่
        </Button>
      </div>
      </div>
    </div>
  );
}

function SectionCard({
  section,
  index,
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
  index: number;
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
  const baseFields = SECTION_FIELDS[section.key] || [
    { key: "body", label: section.title, type: "textarea" as const },
  ];
  const values = parseFields(section.content);
  const fields =
    values.body && !baseFields.some((item) => item.key === "body")
      ? [
          {
            key: "body",
            label: "เนื้อหาร่าง (จากเอกสาร/AI)",
            type: "textarea" as const,
          },
          ...baseFields,
        ]
      : baseFields;
  const [draft, setDraft] = useState(values);
  useEffect(() => {
    setDraft(parseFields(section.content));
  }, [section.content]);

  function suggested(mapField?: string) {
    if (!mapField) return "";
    return displayExtracted(extracted[mapField]);
  }

  return (
    <div className="flex gap-3.5">
      <div className="flex w-9 shrink-0 flex-col items-center">
        <div
          className={cn(
            "z-[1] flex h-[34px] w-[34px] items-center justify-center rounded-full border-2 text-[13px] font-extrabold",
            sectionCircleClass(section.filled, expanded)
          )}
        >
          {section.filled ? "✓" : index + 1}
        </div>
        {!last ? (
          <div className={cn("w-0.5 flex-1", section.filled ? "bg-brand-green" : "bg-gray-300")} />
        ) : null}
      </div>
      <div
        className={cn(
          "mb-3.5 flex-1 overflow-hidden rounded-[10px] border",
          expanded ? "border-crimson shadow-[0_4px_14px_rgba(196,30,58,0.12)]" : "border-gray-200"
        )}
      >
        <button
          type="button"
          className="flex w-full items-center justify-between bg-gray-50 px-4 py-3 text-left"
          onClick={onToggle}
        >
          <div>
            <h3 className="text-[14.5px] text-navy">
              หมวด {section.key.replace("s", "")}: {section.title}
            </h3>
            <p className="text-[11.5px] text-muted-foreground">
              {section.filled ? "ร่างแล้ว" : "รอร่าง"}
              {section.hitl ? " · ต้องให้เจ้าหน้าที่ยืนยัน" : ""}
            </p>
            <p
              data-testid={`section-preview-${section.key}`}
              className="mt-1 line-clamp-2 text-[12px] text-navy"
            >
              {previewText(section.content) || "รอระบบร่างจากข้อมูลที่คุยมา..."}
            </p>
          </div>
          <span className="text-xs text-muted-foreground">{expanded ? "▴ ย่อ" : "▾ ขยาย"}</span>
        </button>
        {expanded ? (
          <div className="space-y-3 border-t p-4">
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
                ร่างด้วย AI
              </Button>
                <Button
                  size="sm"
                  variant="outline"
                  data-testid={`save-section-${section.key}`}
                  onClick={() => onSave(section.key, serializeSectionDraft(draft), false)}
                >
                  บันทึกหมวดนี้
                </Button>
              {HITL_SECTIONS.includes(section.key) ? (
                <Button
                  size="sm"
                  data-testid={`hitl-confirm-${section.key}`}
                  onClick={() => onSave(section.key, serializeSectionDraft(draft), true)}
                >
                  เจ้าหน้าที่ยืนยันแล้ว
                </Button>
              ) : null}
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
  const chips = subs || SCOPE_SUBSECTIONS.map((item) => ({
    ...item,
    content: "",
    filled: false,
  }));
  const openItem = (subs || []).find((sub) => sub.key === openSub);
  return (
    <>
      <p className="text-xs text-muted-foreground">
        หมวด 4 แบ่งเป็น {SCOPE_SUBSECTIONS.length} หัวข้อย่อย
      </p>
      <div className="flex flex-wrap gap-1.5">
        {chips.map((sub) => (
          <button
            key={sub.key}
            type="button"
            className={cn(
              "rounded-md border px-2.5 py-1 text-[11.5px] font-semibold",
              sub.filled
                ? "border-green-300 bg-green-50 text-green-800"
                : "border-gray-200 bg-gray-100"
            )}
            onClick={() => onOpenSub(openSub === sub.key ? "" : sub.key)}
          >
            {sub.key.replace("s4.", "4.")} {sub.title}
          </button>
        ))}
      </div>
      {openItem ? (
        <div className="rounded-lg border-l-[3px] border-navy bg-gray-50 p-3">
          <Label>{openItem.title}</Label>
          <Textarea
            className="mt-1"
            defaultValue={openItem.content}
            onBlur={(event) => onSave(openItem.key, event.target.value)}
          />
        </div>
      ) : null}
    </>
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
