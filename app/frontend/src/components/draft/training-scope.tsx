"use client";

import { useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  TRAINING_FIELD_KEYS,
  TRAINING_FIELD_LABELS,
  emptyTrainingScope,
  fetchTrainingScope,
  normalizeTrainingScope,
  parseTrainingFromContent,
  saveTrainingScope,
  trainingScopeProse,
  type TrainingFieldKey,
  type TrainingScopeFields,
} from "@/lib/training-scope";

export function TrainingScopeEditor({
  projectId,
  hint,
  content,
  onDraftChange,
  onSave,
}: Readonly<{
  projectId?: string;
  hint?: string;
  content?: string;
  onDraftChange?: (prose: string, fields: TrainingScopeFields) => void;
  onSave?: (prose: string) => void | Promise<void>;
}>) {
  const [fields, setFields] = useState<TrainingScopeFields>(
    () => parseTrainingFromContent(content || "") || emptyTrainingScope()
  );
  const prose = trainingScopeProse(fields, hint);

  useEffect(() => {
    if (!projectId) return;
    let cancelled = false;
    fetchTrainingScope(projectId)
      .then((payload) => {
        if (cancelled) return;
        setFields(payload.fields);
        onDraftChange?.(payload.prose, payload.fields);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- load once per project
  }, [projectId]);

  function updateField(key: TrainingFieldKey, value: string) {
    const next = normalizeTrainingScope({ ...fields, [key]: value });
    setFields(next);
    onDraftChange?.(trainingScopeProse(next, hint), next);
  }

  async function persist() {
    const text = trainingScopeProse(fields, hint);
    if (projectId) {
      try {
        const saved = await saveTrainingScope(projectId, fields);
        setFields(saved.fields);
        onDraftChange?.(saved.prose, saved.fields);
        await onSave?.(saved.prose);
        return;
      } catch {
        // fall through to local section save
      }
    }
    await onSave?.(text);
  }

  return (
    <div
      className="mb-3 space-y-2 border border-navy/20 bg-slate-50/80 p-3"
      data-testid="training-scope"
    >
      <p className="text-xs font-semibold text-navy">ร่างขอบเขตอบรม</p>
      <p className="text-xs text-muted-foreground">
        จากหัวข้อการฝึกอบรมของประเภทจ้างพัฒนาและจัดซื้อครุภัณฑ์ — จำนวนรุ่น ชั่วโมง ผู้เข้าอบรม
        และเอกสารส่งมอบ
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {TRAINING_FIELD_KEYS.filter((key) => key !== "documents").map((key) => (
          <div key={key}>
            <Label htmlFor={`training-${key}`}>{TRAINING_FIELD_LABELS[key]}</Label>
            <Input
              id={`training-${key}`}
              className="mt-1"
              value={fields[key]}
              data-testid={`training-scope-${key}`}
              onChange={(event) => updateField(key, event.target.value)}
              onBlur={() => {
                void persist();
              }}
            />
          </div>
        ))}
      </div>
      <div>
        <Label htmlFor="training-documents">{TRAINING_FIELD_LABELS.documents}</Label>
        <Textarea
          id="training-documents"
          className="mt-1"
          rows={3}
          value={fields.documents}
          data-testid="training-scope-documents"
          onChange={(event) => updateField("documents", event.target.value)}
          onBlur={() => {
            void persist();
          }}
        />
      </div>
      <p className="text-xs text-muted-foreground" data-testid="training-scope-preview">
        {prose}
      </p>
    </div>
  );
}
