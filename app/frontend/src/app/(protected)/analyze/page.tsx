"use client";

import { useEffect, useState } from "react";
import { Scale, ShieldAlert, Briefcase, Lightbulb } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { CheckItem } from "@/components/brand/check-item";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { useProjectStore } from "@/stores/project-store";
import { cn } from "@/lib/utils";
import type { AnalyzerFindingView, PartScoreView, TorPartScoresView } from "@/components/review/three-part-scores";

type AnalyzePanel = "legal" | "lock_in" | "project" | "recommendations";

type AnalyzeSource = {
  title?: string;
  url?: string;
  snippet?: string;
  published?: string | null;
  conflicts_with_legal_kb?: boolean;
};

type AnalyzeSuggestion = AnalyzerFindingView & {
  part?: string;
  part_label?: string;
  sources?: AnalyzeSource[];
  source_count?: number;
};

type AnalyzeRecommendation = {
  section_key: string;
  section_label?: string;
  suggestions?: AnalyzeSuggestion[];
  sources?: AnalyzeSource[];
  source_count?: number;
  source_count_note?: string;
  prefer_legal_corpus?: boolean;
  legal_corpus_note?: string;
};

type AnalyzeResult = TorPartScoresView & {
  recommendations?: AnalyzeRecommendation[];
  prefer_legal_corpus_note?: string;
  suggested_text_note?: string;
};

const PANELS: Array<{
  id: AnalyzePanel;
  label: string;
  icon: typeof Scale;
}> = [
  { id: "legal", label: "ส่วนที่คาดว่าผิดกฎหมาย", icon: Scale },
  { id: "lock_in", label: "ความเสี่ยง lock specs รวม Oracle/IVM", icon: ShieldAlert },
  { id: "project", label: "ความเสี่ยงบริหารโครงการ (เข้างาน, ต้นทุนต่ำสุด, price-performance)", icon: Briefcase },
  { id: "recommendations", label: "ข้อเสนอแนะตามหมวดที่ควรแก้", icon: Lightbulb },
];

function isAnalyzeResult(value: unknown): value is AnalyzeResult {
  if (!value || typeof value !== "object") return false;
  const raw = value as Record<string, unknown>;
  return Boolean(raw.legal) && Boolean(raw.lock_in) && Boolean(raw.project);
}

async function copySuggestedText(text: string): Promise<boolean> {
  const value = text.trim();
  if (!value) return false;
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}

function PartPanel({ part }: Readonly<{ part: PartScoreView }>) {
  const findings = part.findings || [];
  return (
    <section className="space-y-3" data-testid={`analyze-panel-${part.key}`}>
      <CheckItem
        tone={part.score >= 70 ? "pass" : "warn"}
        title={`${part.label} — ${part.score}/100`}
        detail={part.explanation}
      />
      {findings.length === 0 ? (
        <p className="text-sm text-muted-foreground">ไม่พบประเด็นในด้านนี้จากข้อความที่มี</p>
      ) : (
        findings.map((item, index) => (
          <article
            key={`${part.key}-${index}`}
            className="rounded-lg border border-navy/15 bg-white p-3"
            data-testid={`analyze-finding-${part.key}-${index}`}
          >
            <p className="text-sm font-semibold text-navy">{item.reason || "ประเด็นที่ตรวจพบ"}</p>
            {item.source_quote ? (
              <p className="mt-1 text-xs text-muted-foreground">ข้อความในร่าง: {item.source_quote}</p>
            ) : null}
            {item.suggested_text ? (
              <p className="mt-2 text-sm text-navy">ข้อความที่แนะนำ: {item.suggested_text}</p>
            ) : null}
            {item.legal_basis ? (
              <p className="mt-1 text-[12px] text-muted-foreground">{item.legal_basis}</p>
            ) : null}
          </article>
        ))
      )}
    </section>
  );
}

function SourceList({
  sources,
  sectionKey,
}: Readonly<{ sources: AnalyzeSource[]; sectionKey: string }>) {
  if (!sources.length) return null;
  return (
    <ul className="mt-2 space-y-1.5" data-testid={`analyze-sources-${sectionKey}`}>
      {sources.map((source, index) => (
        <li key={`${source.url || source.title || index}`} className="text-[12px] leading-relaxed">
          {source.url ? (
            <a href={source.url} className="font-semibold text-navy underline" target="_blank" rel="noreferrer">
              {source.title || source.url}
            </a>
          ) : (
            <span className="font-semibold text-navy">{source.title || "แหล่งออนไลน์"}</span>
          )}
          {source.snippet ? <span className="text-muted-foreground"> — {source.snippet}</span> : null}
          {source.conflicts_with_legal_kb ? (
            <span className="ml-1 text-crimson">ยึดคลังกฎหมายก่อน</span>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

function RecommendationsPanel({
  result,
  copiedKey,
  onCopy,
}: Readonly<{
  result: AnalyzeResult;
  copiedKey: string | null;
  onCopy: (key: string, text: string) => void;
}>) {
  const rows = result.recommendations || [];
  return (
    <section className="space-y-4" data-testid="analyze-panel-recommendations">
      {result.prefer_legal_corpus_note ? (
        <p className="rounded-md border border-crimson/30 bg-rose-50 p-3 text-sm text-navy" data-testid="analyze-prefer-legal">
          {result.prefer_legal_corpus_note}
        </p>
      ) : null}
      {result.suggested_text_note ? (
        <p className="text-xs text-muted-foreground">{result.suggested_text_note}</p>
      ) : null}
      {rows.length === 0 ? (
        <p className="text-sm text-muted-foreground">ยังไม่มีหมวดที่ควรแก้จากผลวิเคราะห์นี้</p>
      ) : (
        rows.map((row) => (
          <article
            key={row.section_key}
            className="rounded-lg border border-navy/15 bg-white p-3"
            data-testid={`analyze-recommendation-${row.section_key}`}
          >
            <h3 className="text-sm font-bold text-navy">
              {row.section_label || row.section_key}
            </h3>
            <p className="mt-1 text-xs text-muted-foreground" data-testid={`analyze-source-count-${row.section_key}`}>
              {row.source_count_note || `พบ ${row.source_count ?? 0} แหล่งออนไลน์ประกอบหมวดนี้`}
            </p>
            {row.legal_corpus_note ? (
              <p className="mt-1 text-xs text-navy">{row.legal_corpus_note}</p>
            ) : null}
            {(row.suggestions || []).map((item, index) => {
              const copyKey = `${row.section_key}-${index}`;
              const text = item.suggested_text || "";
              return (
                <div key={copyKey} className="mt-3 rounded-md bg-slate-50 p-3">
                  <p className="text-xs font-semibold text-navy">{item.part_label || item.part}</p>
                  <p className="mt-1 text-sm">{item.reason}</p>
                  {text ? (
                    <pre className="mt-2 whitespace-pre-wrap rounded-md bg-white p-2 text-[13px] text-navy">
                      {text}
                    </pre>
                  ) : (
                    <p className="mt-2 text-xs text-muted-foreground">ไม่มีข้อความแนะนำจากตัววิเคราะห์</p>
                  )}
                  <Button
                    className="mt-2"
                    variant="outline"
                    size="sm"
                    data-testid={`analyze-copy-${copyKey}`}
                    disabled={!text}
                    onClick={() => onCopy(copyKey, text)}
                  >
                    {copiedKey === copyKey ? "คัดลอกแล้ว — นำไปวางในร่างเอง" : "คัดลอกข้อความที่แนะนำ"}
                  </Button>
                  <SourceList sources={item.sources || row.sources || []} sectionKey={`${row.section_key}-${index}`} />
                </div>
              );
            })}
          </article>
        ))
      )}
    </section>
  );
}

export default function AnalyzePage() {
  const { projects, fetchProjects } = useProjectStore();
  const [text, setText] = useState("");
  const [projectId, setProjectId] = useState("");
  const [panel, setPanel] = useState<AnalyzePanel>("legal");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    fetchProjects(1).catch(() => undefined);
  }, [fetchProjects]);

  async function runAnalysis() {
    const trimmed = text.trim();
    if (!trimmed && !projectId) {
      setError("วางข้อความ TOR หรือเลือกร่างจากโครงการก่อนวิเคราะห์");
      return;
    }
    setBusy(true);
    setError(null);
    setCopiedKey(null);
    try {
      const response = await apiClient.post("/analyze", {
        text: trimmed || undefined,
        project_id: projectId || undefined,
      });
      const payload = unwrapData<unknown>(response);
      if (!isAnalyzeResult(payload)) {
        throw new Error("รูปแบบผลวิเคราะห์ไม่ถูกต้อง");
      }
      setResult(payload);
      setPanel("legal");
    } catch (err: unknown) {
      setResult(null);
      setError(apiErrorMessage(err, "วิเคราะห์ TOR ไม่สำเร็จ"));
    } finally {
      setBusy(false);
    }
  }

  async function handleCopy(key: string, value: string) {
    const ok = await copySuggestedText(value);
    if (ok) setCopiedKey(key);
  }

  return (
    <div className="min-w-0" data-testid="analyze-page">
      <h1 className="text-2xl font-extrabold text-navy">วิเคราะห์ TOR</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        วางข้อความหรือเลือกร่างจากโครงการ แล้วดูสามด้านและข้อเสนอแนะพร้อมแหล่งออนไลน์ต่อหมวด
        ระบบจะไม่เขียนทับร่างให้อัตโนมัติ
      </p>

      <div className="mt-4 space-y-3 rounded-xl bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
        <label className="block text-sm font-bold text-navy" htmlFor="analyze-text">
          วางข้อความ TOR
        </label>
        <Textarea
          id="analyze-text"
          data-testid="analyze-text"
          rows={8}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="วางร่าง TOR ที่นี่"
        />
        <label className="block text-sm font-bold text-navy" htmlFor="analyze-project">
          หรือเลือกร่างจากโครงการ
        </label>
        <Select
          id="analyze-project"
          data-testid="analyze-project"
          placeholder="เลือกโครงการ"
          value={projectId}
          onChange={(event) => setProjectId(event.target.value)}
          options={projects.map((item) => ({ value: item.id, label: item.name }))}
        />
        <Button data-testid="analyze-run" onClick={runAnalysis} disabled={busy}>
          {busy ? "กำลังวิเคราะห์..." : "วิเคราะห์ TOR"}
        </Button>
        {error ? (
          <p className="text-sm text-destructive" role="alert">
            {error}
          </p>
        ) : null}
      </div>

      <div className="mt-5 flex min-w-0 flex-col gap-4 lg:flex-row">
        <nav
          className="w-full shrink-0 rounded-xl bg-gradient-to-b from-navy to-navy-dark p-3 text-white lg:w-[240px]"
          aria-label="แผงวิเคราะห์"
          data-testid="analyze-panels"
        >
          <p className="mb-2 text-[11px] uppercase tracking-wider text-white/55">ในเครื่องมือนี้</p>
          {PANELS.map((item) => {
            const Icon = item.icon;
            const active = panel === item.id;
            return (
              <button
                key={item.id}
                type="button"
                data-testid={`analyze-tab-${item.id}`}
                onClick={() => setPanel(item.id)}
                className={cn(
                  "mb-1 flex w-full items-start gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-left text-sm transition-colors",
                  active
                    ? "border-crimson bg-brand-orange font-bold text-navy"
                    : "border-transparent text-white hover:bg-white/10"
                )}
              >
                <Icon className="mt-0.5 h-[18px] w-[18px] shrink-0" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="min-w-0 flex-1 rounded-xl bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
          {!result ? (
            <p className="py-10 text-center text-sm text-muted-foreground">
              วางข้อความหรือเลือกโครงการ แล้วกดวิเคราะห์เพื่อดูผลทั้งสี่แผง
            </p>
          ) : (
            <>
              <p className="mb-3 text-sm text-navy" data-testid="analyze-summary">
                คะแนนรวม {result.total}/100 — {result.summary}
              </p>
              {panel === "legal" ? <PartPanel part={result.legal} /> : null}
              {panel === "lock_in" ? <PartPanel part={result.lock_in} /> : null}
              {panel === "project" ? <PartPanel part={result.project} /> : null}
              {panel === "recommendations" ? (
                <RecommendationsPanel result={result} copiedKey={copiedKey} onCopy={handleCopy} />
              ) : null}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
