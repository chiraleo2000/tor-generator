"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { useProjectStore } from "@/stores/project-store";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import type { ProjectType } from "@/types";
import { PROCUREMENT_CATEGORIES } from "@/lib/tor-profiles";

function isAsciiDigitString(value: string): boolean {
  if (!value) {
    return false;
  }
  for (const ch of value) {
    if (ch < "0" || ch > "9") {
      return false;
    }
  }
  return true;
}

/** Strip commas, then accept ASCII digits only. Thai digits fail. */
export function parseProjectBudget(raw: string): number | null {
  const digits = raw.replaceAll(",", "").trim();
  if (!isAsciiDigitString(digits)) {
    return null;
  }
  const value = Number.parseInt(digits, 10);
  if (!Number.isFinite(value) || value < 1) {
    return null;
  }
  return value;
}

interface NewProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NewProjectDialog({
  open,
  onOpenChange,
}: Readonly<NewProjectDialogProps>) {
  const router = useRouter();
  const createProject = useProjectStore((s) => s.createProject);
  const [name, setName] = useState("");
  const [ministry, setMinistry] = useState("");
  const [budget, setBudget] = useState("");
  const [projectType, setProjectType] = useState<ProjectType | "">("");
  const [templateId, setTemplateId] = useState("");
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!open) {
      return;
    }
    apiClient
      .get("/templates", { params: { status: "published" } })
      .then((res) => {
        const payload = unwrapData<{ items?: { id: string; name: string }[] }>(res);
        setTemplates(payload.items || []);
      })
      .catch(() => setTemplates([]));
  }, [open]);

  async function handleCreate() {
    setError(null);
    if (!name.trim() || !ministry.trim()) {
      setError("กรุณากรอกชื่อโครงการ และหน่วยงาน");
      return;
    }
    if (!projectType) {
      setError("กรุณาเลือกหมวดใหญ่ประเภทการจัดซื้อจัดจ้าง");
      return;
    }
    const trimmedBudget = budget.trim();
    let budgetNum: number | undefined;
    if (trimmedBudget) {
      const parsed = parseProjectBudget(budget);
      if (parsed === null) {
        setError("งบประมาณต้องเป็นจำนวนเต็มบวก (เลข ASCII)");
        return;
      }
      budgetNum = parsed;
    }
    setSaving(true);
    try {
      const project = await createProject({
        name: name.trim(),
        ministry: ministry.trim(),
        ...(budgetNum !== undefined ? { budget: budgetNum } : {}),
        projectType,
        templateId: templateId || undefined,
      });
      onOpenChange(false);
      router.push(`/projects/${project.id}/draft`);
    } catch (err: unknown) {
      setError(apiErrorMessage(err, "สร้างโครงการไม่สำเร็จ กรุณาลองใหม่"));
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogHeader>
        <DialogTitle>สร้างโครงการใหม่</DialogTitle>
        <DialogDescription>
          กรอกข้อมูลพื้นฐานแล้วเข้าสู่กระบวนการร่างห้าขั้น
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-3 px-1 py-2" data-testid="new-project-dialog">
        {error ? (
          <p className="text-sm text-destructive" data-testid="new-project-error">
            {error}
          </p>
        ) : null}
        <div className="space-y-1">
          <Label htmlFor="np-name">ชื่อโครงการ</Label>
          <Input
            id="np-name"
            data-testid="new-project-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            lang="th"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-ministry">หน่วยงาน</Label>
          <Input
            id="np-ministry"
            data-testid="new-project-ministry"
            value={ministry}
            onChange={(e) => setMinistry(e.target.value)}
            lang="th"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-budget">งบประมาณ (บาท) — ไม่บังคับ</Label>
          <Input
            id="np-budget"
            data-testid="new-project-budget"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            inputMode="numeric"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-type">หมวดใหญ่ประเภทการจัดซื้อจัดจ้าง</Label>
          <Select
            id="np-type"
            data-testid="new-project-type"
            value={projectType}
            onChange={(e) => setProjectType(e.target.value as ProjectType)}
            placeholder="เลือกหมวดใหญ่"
            options={PROCUREMENT_CATEGORIES.map((item) => ({
              value: item.key,
              label: item.label,
            }))}
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="np-template">แม่แบบ</Label>
          <Select
            id="np-template"
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            options={[
              { value: "", label: "-- ไม่เลือก --" },
              ...templates.map((t) => ({ value: t.id, label: t.name })),
            ]}
          />
        </div>
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
          ยกเลิก
        </Button>
        <Button
          onClick={handleCreate}
          disabled={saving}
          data-testid="create-project-submit"
        >
          {saving ? "กำลังสร้าง..." : "สร้างและเริ่มร่าง"}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
