"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { apiClient } from "@/lib/api-client";
import { unwrapData } from "@/lib/api-unwrap";
import { TOR_SECTION_LABELS, TOR_SECTION_ORDER } from "@/lib/tor-sections";

interface TemplateRow {
  id: string;
  name: string;
  industry: string;
  status: string;
}

const defaultStructure = JSON.stringify(
  {
    sections: TOR_SECTION_ORDER.map((key) => ({
      key,
      title: TOR_SECTION_LABELS[key],
    })),
  },
  null,
  2
);

export default function AdminTemplatesPage() {
  const [items, setItems] = useState<TemplateRow[]>([]);
  const [name, setName] = useState("");
  const [industry, setIndustry] = useState("general");
  const [structure, setStructure] = useState(defaultStructure);
  const [guidance, setGuidance] = useState('{"s1":"อธิบายความเป็นมา"}');
  const [editing, setEditing] = useState<string | null>(null);
  const [warning, setWarning] = useState<string | null>(null);

  async function load() {
    const response = await apiClient.get("/templates");
    const payload = unwrapData<{ items?: TemplateRow[] }>(response);
    setItems(payload.items || []);
  }

  useEffect(() => {
    load().catch(() => setItems([]));
  }, []);

  async function save() {
    const body = {
      name,
      industry,
      section_structure: JSON.parse(structure),
      placeholder_guidance: JSON.parse(guidance),
    };
    if (editing) {
      await apiClient.put(`/templates/${editing}`, body);
    } else {
      await apiClient.post("/templates", body);
    }
    setName("");
    setEditing(null);
    await load();
  }

  async function publish(id: string) {
    await apiClient.put(`/templates/${id}/publish`);
    await load();
  }

  async function unpublish(id: string, confirm = false) {
    const response = await apiClient.put(`/templates/${id}/unpublish`, null, {
      params: { confirm },
    });
    const data = unwrapData<{ warning?: string; affected_count?: number }>(response);
    if (data.warning && !confirm) {
      setWarning(
        `${data.warning} (โครงการที่กระทบ ${data.affected_count ?? 0}) — กดอีกครั้งเพื่อยืนยัน`
      );
      return;
    }
    setWarning(null);
    await load();
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6" data-testid="admin-templates-page">
      <h1 className="text-2xl font-extrabold text-navy">จัดการแม่แบบ</h1>
      {warning && <p className="text-sm text-amber-700">{warning}</p>}
      <div className="gov-card space-y-3">
        <h2 className="font-medium text-navy">{editing ? "แก้ไขแม่แบบ" : "สร้างแม่แบบ"}</h2>
        <Label>ชื่อ</Label>
        <Input value={name} onChange={(e) => setName(e.target.value)} lang="th" />
        <Label>ประเภท</Label>
        <Select
          value={industry}
          onChange={(e) => setIndustry(e.target.value)}
          options={[
            { value: "it", label: "IT" },
            { value: "construction", label: "ก่อสร้าง" },
            { value: "consulting", label: "ที่ปรึกษา" },
            { value: "general", label: "ทั่วไป" },
          ]}
        />
        <Label>โครงสร้างส่วน (JSON)</Label>
        <Textarea
          className="font-mono text-xs min-h-[140px]"
          value={structure}
          onChange={(e) => setStructure(e.target.value)}
        />
        <Label>คำแนะนำช่องว่าง (JSON)</Label>
        <Textarea
          className="font-mono text-xs min-h-[100px]"
          value={guidance}
          onChange={(e) => setGuidance(e.target.value)}
        />
        <Button onClick={save}>{editing ? "บันทึก" : "สร้างร่าง"}</Button>
      </div>
      <div className="space-y-2">
        {items.map((item) => (
          <div
            key={item.id}
            className="gov-card flex items-center justify-between gap-3"
          >
            <div>
              <p className="font-medium">{item.name}</p>
              <p className="text-xs text-muted-foreground">
                {item.industry} · {item.status}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={async () => {
                  const response = await apiClient.get(`/templates/${item.id}`);
                  const detail = unwrapData<{
                    name: string;
                    industry: string;
                    section_structure: unknown;
                    placeholder_guidance: unknown;
                  }>(response);
                  setEditing(item.id);
                  setName(detail.name);
                  setIndustry(detail.industry);
                  setStructure(JSON.stringify(detail.section_structure, null, 2));
                  setGuidance(JSON.stringify(detail.placeholder_guidance, null, 2));
                }}
              >
                แก้ไข
              </Button>
              {item.status === "draft" ? (
                <Button size="sm" onClick={() => publish(item.id)}>
                  เผยแพร่
                </Button>
              ) : (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => unpublish(item.id, Boolean(warning))}
                >
                  ยกเลิกเผยแพร่
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
