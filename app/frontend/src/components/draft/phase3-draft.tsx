"use client";

import { useEffect, useRef, useState } from "react";
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

type DraftResult = { sectionKey: string; draftContent: string } | null | void;

function RedraftPromptPanel({
  open,
  busy,
  value,
  onChange,
  onCancel,
  onSubmit,
  testId,
}: Readonly<{
  open: boolean;
  busy: boolean;
  value: string;
  onChange: (next: string) => void;
  onCancel: () => void;
  onSubmit: () => void;
  testId: string;
}>) {
  if (!open) return null;
  return (
    <div
      className="mt-2 space-y-2 border border-navy/25 bg-slate-50/90 p-3"
      data-testid={testId}
    >
      <Label htmlFor={`${testId}-input`}>ความคิดเห็น</Label>
      <p className="text-xs text-muted-foreground">
        พิมพ์สิ่งที่ต้องการให้แก้ในหัวข้อนี้เท่านั้น ระบบจะส่งร่างเดิมพร้อมความคิดเห็นไปให้โมเดลของหัวข้อนี้
      </p>
      <Textarea
        id={`${testId}-input`}
        data-testid={`${testId}-input`}
        className="mt-1"
        rows={3}
        value={value}
        disabled={busy}
        placeholder="เช่น ปรับให้เป็นตารางมาร์กดาวน์คอลัมน์เดียว ลบหัวตารางซ้ำ และใส่คำว่า ใช้ ในเกณฑ์กลาง ICT"
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="flex justify-end gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={busy}
          data-testid={`${testId}-cancel`}
          onClick={onCancel}
        >
          ยกเลิก
        </Button>
        <Button
          type="button"
          size="sm"
          disabled={busy || !value.trim()}
          data-testid={`${testId}-submit`}
          onMouseDown={(event) => event.preventDefault()}
          onClick={onSubmit}
        >
          ส่งให้ร่างใหม่
        </Button>
      </div>
    </div>
  );
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
  onDraft: (
    key: string,
    context?: Record<string, unknown>
  ) => void | Promise<DraftResult>;
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
  onDraft: (
    key: string,
    context?: Record<string, unknown>
  ) => void | Promise<DraftResult>;
}>) {
  const fields = SECTION_FIELDS[section.key] || [
    { key: "body", label: section.title, type: "textarea" as const },
  ];
  const values = parseFields(section.key, section.content);
  const [draft, setDraft] = useState(values);
  const [scopeDrafts, setScopeDrafts] = useState<Record<string, string>>({});
  const [promptOpen, setPromptOpen] = useState(false);
  const [feedback, setFeedback] = useState("");
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

  useEffect(() => {
    setPromptOpen(false);
    setFeedback("");
  }, [section.key, openSub]);

  function suggested(mapField?: string) {
    if (!mapField) return "";
    return displayExtracted(extracted[mapField]);
  }

  function draftContext(
    focusSub?: string,
    userFeedback?: string
  ): Record<string, unknown> | undefined {
    const note = (userFeedback || "").trim();
    if (section.big) {
      const focus = (focusSub || openSub || "").trim();
      if (focus) {
        const text = String(scopeDrafts[focus] || "").trim();
        return {
          focus_sub_key: focus,
          current_draft_fields: { [focus]: text },
          current_draft: text,
          redraft: Boolean(text) || Boolean(note),
          user_feedback: note || undefined,
          revision_instruction: note
            ? "แก้ไขเฉพาะหัวข้อย่อยนี้ตามความคิดเห็นผู้ใช้ — ห้ามแก้หัวข้ออื่น"
            : text
              ? "ร่างใหม่เฉพาะหัวข้อย่อยนี้เท่านั้น ตามกฎเจ้าของสาระ — ห้ามแก้หัวข้อย่อยอื่น"
              : "ร่างเฉพาะหัวข้อย่อยนี้จากเอกสารขั้นที่ ๐ ตามกฎเจ้าของสาระ ห้ามดึงหัวข้ออื่นมาปน",
        };
      }
      const hasContent = Object.values(scopeDrafts).some((value) =>
        String(value || "").trim()
      );
      if (!hasContent && !note) return undefined;
      return {
        current_draft_fields: scopeDrafts,
        redraft: true,
        user_feedback: note || undefined,
        revision_instruction: note
          ? "แก้ไขเฉพาะหมวดขอบเขตตามความคิดเห็นผู้ใช้"
          : "คงสาระที่ผู้ใช้แก้ในแต่ละข้อย่อยไว้ แล้วเติมส่วนที่ยังว่างจากเอกสารขั้นที่ ๐ ให้ครบ",
      };
    }
    const hasContent = Object.values(draft).some((value) => String(value || "").trim());
    if (!hasContent && !note) return undefined;
    return {
      current_draft_fields: draft,
      redraft: true,
      user_feedback: note || undefined,
      revision_instruction: note
        ? "แก้ไขเฉพาะหมวดนี้ตามความคิดเห็นผู้ใช้ ส่งร่างใหม่ทั้งก้อนของหมวดนี้เท่านั้น"
        : "ต้องเขียนร่างใหม่ให้ต่างจากร่างเดิมอย่างมีสาระ ห้ามคืนข้อความเดิมทั้งก้อน คงสาระที่ผู้ใช้แก้แล้วไว้",
    };
  }

  async function runDraft(focus?: string, userFeedback?: string) {
    const target = (focus || "").trim();
    const ctx = draftContext(target || undefined, userFeedback);
    const result = await onDraft(target || section.key, ctx);
    if (!result?.draftContent) return;
    setPromptOpen(false);
    setFeedback("");
    if (section.big && result.sectionKey) {
      setScopeDrafts((prev) => ({ ...prev, [result.sectionKey]: result.draftContent }));
      return;
    }
    const parsed = parseFields(section.key, result.draftContent);
    if (Object.keys(parsed).length) {
      setDraft((prev) => ({ ...prev, ...parsed }));
    } else {
      setDraft((prev) => ({ ...prev, body: result.draftContent }));
    }
  }

  const filled = isSectionFilled(section);
  const indexPad = sectionIndexPad(section.key);
  const focusedSub = section.big ? (openSub || "").trim() : "";
  const hasEditableContent = section.big
    ? Boolean(
        (focusedSub && String(scopeDrafts[focusedSub] || "").trim()) ||
          (!focusedSub &&
            Object.values(scopeDrafts).some((value) => String(value || "").trim()))
      )
    : Object.values(draft).some((value) => String(value || "").trim());
  const draftButtonLabel = promptOpen
    ? "ปิดช่องความคิดเห็น"
    : hasEditableContent
      ? focusedSub
        ? "ขอร่างใหม่หัวข้อย่อยนี้"
        : "ขอร่างใหม่จากข้อมูลที่กรอก"
      : "ร่างด้วยระบบอัจฉริยะ";

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
                busy={busy}
                onOpenSub={onOpenSub}
                onSave={onSave}
                onDraft={onDraft}
                onDraftsChange={setScopeDrafts}
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
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => {
                  if (!hasEditableContent) {
                    void runDraft(focusedSub);
                    return;
                  }
                  setPromptOpen((prev) => !prev);
                }}
              >
                {draftButtonLabel}
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
            <RedraftPromptPanel
              open={promptOpen}
              busy={busy}
              value={feedback}
              testId={`redraft-prompt-${section.key}`}
              onChange={setFeedback}
              onCancel={() => {
                setPromptOpen(false);
                setFeedback("");
              }}
              onSubmit={() => {
                void runDraft(focusedSub, feedback);
              }}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ScopeSubsectionEditor({
  subs,
  openSub,
  busy,
  onOpenSub,
  onSave,
  onDraft,
  onDraftsChange,
}: Readonly<{
  subs: SectionPayload["subs"];
  openSub: string;
  busy: boolean;
  onOpenSub: (key: string) => void;
  onSave: (key: string, content: string, confirmed?: boolean) => Promise<void>;
  onDraft: (
    key: string,
    context?: Record<string, unknown>
  ) => void | Promise<DraftResult>;
  onDraftsChange?: (drafts: Record<string, string>) => void;
}>) {
  const chips = subs || scopeSubsectionsFor().map((item) => ({
    key: item.key,
    title: item.title,
    content: "",
    filled: false,
  }));
  const contentSig = chips.map((sub) => `${sub.key}:${sub.content || ""}`).join("|");
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [promptKey, setPromptKey] = useState("");
  const [feedback, setFeedback] = useState("");
  const skipBlurSave = useRef(false);
  useEffect(() => {
    const next: Record<string, string> = {};
    for (const sub of chips) {
      next[sub.key] = sub.content || "";
    }
    setDrafts(next);
    onDraftsChange?.(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- รีเฟรชเมื่อลายเซ็นเนื้อหาจากเอพีไอเปลี่ยน
  }, [contentSig]);
  useEffect(() => {
    setPromptKey("");
    setFeedback("");
  }, [openSub]);
  const filledN = chips.filter((sub) => sub.filled).length;

  function applyLocalDraft(subKey: string, content: string) {
    setDrafts((prev) => {
      const next = { ...prev, [subKey]: content };
      onDraftsChange?.(next);
      return next;
    });
  }

  async function submitRedraft(subKey: string, text: string, note: string) {
    skipBlurSave.current = true;
    try {
      const result = await onDraft(subKey, {
        focus_sub_key: subKey,
        current_draft_fields: { [subKey]: text },
        current_draft: text,
        redraft: true,
        user_feedback: note.trim(),
        revision_instruction:
          "แก้ไขเฉพาะหัวข้อย่อยนี้ตามความคิดเห็นผู้ใช้ — ห้ามแก้หัวข้อย่อยอื่น",
      });
      if (result?.draftContent) {
        applyLocalDraft(result.sectionKey || subKey, result.draftContent);
      }
      setPromptKey("");
      setFeedback("");
    } finally {
      window.setTimeout(() => {
        skipBlurSave.current = false;
      }, 500);
    }
  }

  return (
    <div className="space-y-3" data-testid="scope-subsection-editor">
      <p className="text-xs text-muted-foreground">
        ขอบเขตงาน — หัวข้อย่อย ({filledN}/{chips.length} มีเนื้อหา) · กด«ขอร่างใหม่หัวข้อนี้»แล้วพิมพ์ความคิดเห็นก่อนส่ง
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
          const text = drafts[sub.key] ?? sub.content ?? "";
          const hasText = Boolean(String(text).trim());
          return (
            <div
              key={sub.key}
              className="border-l-2 border-navy/40 bg-white py-2 pl-3"
              data-testid={`scope-sub-${sub.key}`}
            >
              <Label className="font-mono text-xs tabular-nums">
                {formatScopeSubHeading(sub.key, sub.title)}
              </Label>
              {text.trim() ? (
                <div className="mt-1 mb-2 border bg-slate-50/80 p-2">
                  <RichDraftText text={text} />
                </div>
              ) : null}
              <Textarea
                className="mt-1"
                value={text}
                rows={5}
                onChange={(event) => {
                  const value = event.target.value;
                  setDrafts((prev) => {
                    const next = { ...prev, [sub.key]: value };
                    onDraftsChange?.(next);
                    return next;
                  });
                }}
                onBlur={(event) => {
                  if (busy || skipBlurSave.current) return;
                  void onSave(sub.key, event.target.value);
                }}
              />
              <div className="mt-2 flex justify-end">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  data-testid={`draft-ai-sub-${sub.key}`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    skipBlurSave.current = true;
                  }}
                  onClick={() => {
                    if (!hasText) {
                      void (async () => {
                        const result = await onDraft(sub.key, {
                          focus_sub_key: sub.key,
                          current_draft_fields: { [sub.key]: "" },
                          current_draft: "",
                          revision_instruction:
                            "ร่างเฉพาะหัวข้อย่อยนี้จากเอกสารขั้นที่ ๐ ตามกฎเจ้าของสาระ ห้ามดึงหัวข้ออื่นมาปน",
                        });
                        if (result?.draftContent) {
                          applyLocalDraft(
                            result.sectionKey || sub.key,
                            result.draftContent
                          );
                        }
                      })();
                      return;
                    }
                    setPromptKey((prev) => (prev === sub.key ? "" : sub.key));
                    setFeedback("");
                  }}
                >
                  {promptKey === sub.key
                    ? "ปิดช่องความคิดเห็น"
                    : hasText
                      ? "ขอร่างใหม่หัวข้อนี้"
                      : "ร่างหัวข้อนี้"}
                </Button>
              </div>
              <RedraftPromptPanel
                open={promptKey === sub.key}
                busy={busy}
                value={feedback}
                testId={`redraft-prompt-sub-${sub.key}`}
                onChange={setFeedback}
                onCancel={() => {
                  setPromptKey("");
                  setFeedback("");
                }}
                onSubmit={() => {
                  void submitRedraft(sub.key, text, feedback);
                }}
              />
            </div>
          );
        })}
      </div>
      {!openSub && filledN === 0 ? (
        <p className="text-xs text-amber-800">
          ยังไม่มีหัวข้อย่อย — เลือกหัวข้อด้านบนแล้วกด«ร่างหัวข้อนี้»หรือพิมพ์ความคิดเห็นหลังขอร่างใหม่
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
