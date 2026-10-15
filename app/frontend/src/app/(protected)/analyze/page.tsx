"use client";

import { useState } from "react";
import { Scale, ShieldAlert, Briefcase, Lightbulb, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { UploadArea } from "@/components/brand/upload-area";
import { CheckItem } from "@/components/brand/check-item";
import { apiClient } from "@/lib/api-client";
import { apiErrorMessage } from "@/lib/api-error";
import { unwrapData } from "@/lib/api-unwrap";
import { cn } from "@/lib/utils";
import type { AnalyzerFindingView, PartScoreView, TorPartScoresView } from "@/components/review/three-part-scores";
import { BidderRiskPanel } from "@/components/review/bidder-risk-panel";
import { CostTopicsPanel } from "@/components/review/cost-topics-panel";
import { useElapsedStatus } from "@/lib/elapsed-status";

type AnalyzePanel = "legal" | "lock_in" | "project" | "bidder_risk" | "cost_topics" | "recommendations";

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
  { id: "bidder_risk", label: "ความเสี่ยงก่อนตัดสินใจยื่น", icon: AlertTriangle },
  { id: "cost_topics", label: "ประมาณงบประมาณ ต้นทุน บุคลากร และค่าอบรม", icon: Briefcase },
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

type AnalyzeSetters = {
  setBusy: (value: boolean) => void;
  setStatus: (value: string) => void;
  setError: (value: string | null) => void;
  setCopiedKey: (value: string | null) => void;
  setResult: (value: AnalyzeResult | null) => void;
  setPanel: (value: AnalyzePanel) => void;
};

const EMPTY_ANALYSIS_MESSAGE = "อัปโหลดไฟล์ TOR แล้วสกัดข้อความก่อนวิเคราะห์";
const PREVIEW_MAX = 20000;
const ANALYZE_STEPS = ["เลือกไฟล์", "สกัดข้อความ", "วิเคราะห์"] as const;

type AnalyzeStep = 1 | 2 | 3;

type ExtractPayload = {
  extracted_text?: string;
  method?: string;
  warnings?: string[];
};

function stripPageMarkers(text: string): string {
  return text
    .replaceAll("\f", "\n")
    .replaceAll(/\[\[page\b[^\]]*\]\]/gi, "")
    .replaceAll(/\[\[หน้า:[^\]]+\]\]/g, "")
    .replaceAll(/<!--\s*page\b[^>]*-->/gi, "")
    .replaceAll(/^---\s*(?:page|หน้า)\s+\d+\s*---\s*$/gim, "")
    .replaceAll(/^\[PAGE\s+\d+\]\s*$/gim, "");
}

function previewSnippet(text: string): string {
  const trimmed = stripPageMarkers(text).trim();
  if (trimmed.length <= PREVIEW_MAX) return trimmed;
  return `${trimmed.slice(0, PREVIEW_MAX)}\n…`;
}

function methodLabel(method: string | undefined): string {
  if (method === "ocr") return "อ่านด้วย OCR";
  if (method === "mixed") return "ดึงข้อความและ OCR";
  return "ดึงข้อความจากไฟล์";
}

async function postTorAnalysis(text: string): Promise<AnalyzeResult> {
  const response = await apiClient.post("/analyze", { text }, { timeout: 2_700_000 });
  const payload = unwrapData<unknown>(response);
  if (!isAnalyzeResult(payload)) {
    throw new Error("รูปแบบผลวิเคราะห์ไม่ถูกต้อง");
  }
  return payload;
}

async function extractAnalyzeFile(file: File): Promise<ExtractPayload> {
  const body = new FormData();
  body.append("file", file);
  return unwrapData<ExtractPayload>(
    await apiClient.post("/analyze/extract", body, { timeout: 300_000 })
  );
}

async function runAnalysis(text: string, actions: AnalyzeSetters): Promise<void> {
  const trimmed = text.trim();
  if (!trimmed) {
    actions.setError(EMPTY_ANALYSIS_MESSAGE);
    actions.setStatus(EMPTY_ANALYSIS_MESSAGE);
    return;
  }
  actions.setBusy(true);
  actions.setStatus("กำลังวิเคราะห์");
  actions.setError(null);
  actions.setCopiedKey(null);
  try {
    const payload = await postTorAnalysis(trimmed);
    actions.setResult(payload);
    actions.setPanel("legal");
    actions.setStatus(`วิเคราะห์เสร็จ — คะแนนรวม ${payload.total}/100`);
  } catch (err: unknown) {
    const message = apiErrorMessage(err, "วิเคราะห์ TOR ไม่สำเร็จ");
    actions.setResult(null);
    actions.setError(message);
    actions.setStatus(message);
  } finally {
    actions.setBusy(false);
  }
}

async function rememberCopy(
  key: string,
  value: string,
  setCopiedKey: (next: string | null) => void
): Promise<void> {
  const ok = await copySuggestedText(value);
  if (ok) setCopiedKey(key);
}

function runLabel(busy: boolean): string {
  if (busy) return "กำลังวิเคราะห์...";
  return "วิเคราะห์ TOR";
}

function AnalyzeStatus({ status }: Readonly<{ status: string }>) {
  if (!status) return null;
  return (
    <output className="block text-sm text-navy" data-testid="analyze-status">
      {status}
    </output>
  );
}

function AnalyzeError({ error }: Readonly<{ error: string | null }>) {
  if (!error) return null;
  return (
    <p className="text-sm text-destructive" role="alert">
      {error}
    </p>
  );
}

function PanelNav({
  panel,
  onSelect,
}: Readonly<{ panel: AnalyzePanel; onSelect: (panel: AnalyzePanel) => void }>) {
  return (
    <nav
      className="w-full shrink-0 rounded-xl bg-gradient-to-b from-navy to-navy-dark p-3 text-white lg:w-[240px]"
      aria-label="แผงวิเคราะห์"
      data-testid="analyze-panels"
    >
      <p className="mb-2 text-[11px] uppercase tracking-wider text-white/55">ในเครื่องมือนี้</p>
      {PANELS.map((item) => {
        const Icon = item.icon;
        const active = panel === item.id;
        const tone = active
          ? "border-crimson bg-brand-orange font-bold text-navy"
          : "border-transparent text-white hover:bg-white/10";
        return (
          <button
            key={item.id}
            type="button"
            data-testid={`analyze-tab-${item.id}`}
            onClick={() => onSelect(item.id)}
            className={cn(
              "mb-1 flex w-full items-start gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-left text-sm transition-colors",
              tone
            )}
          >
            <Icon className="mt-0.5 h-[18px] w-[18px] shrink-0" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

function BidderRiskSlot({ report }: Readonly<{ report: AnalyzeResult["bidder_risk"] }>) {
  if (report) return <BidderRiskPanel report={report} />;
  return (
    <p className="text-sm text-muted-foreground" data-testid="bidder-risk-panel">
      ยังไม่มีรายงานความเสี่ยงก่อนยื่นจากผลนี้
    </p>
  );
}

function AnalyzePanelBody({
  result,
  panel,
  copiedKey,
  onCopy,
}: Readonly<{
  result: AnalyzeResult;
  panel: AnalyzePanel;
  copiedKey: string | null;
  onCopy: (key: string, value: string) => void;
}>) {
  if (panel === "legal") return <PartPanel part={result.legal} />;
  if (panel === "lock_in") return <PartPanel part={result.lock_in} />;
  if (panel === "project") return <PartPanel part={result.project} />;
  if (panel === "bidder_risk") return <BidderRiskSlot report={result.bidder_risk} />;
  if (panel === "cost_topics") return <CostTopicsPanel report={result.cost_topics} />;
  if (panel === "recommendations") {
    return <RecommendationsPanel result={result} copiedKey={copiedKey} onCopy={onCopy} />;
  }
  return null;
}

function AnalyzeBody({
  result,
  panel,
  copiedKey,
  onCopy,
}: Readonly<{
  result: AnalyzeResult | null;
  panel: AnalyzePanel;
  copiedKey: string | null;
  onCopy: (key: string, value: string) => void;
}>) {
  if (!result) {
    return (
      <p className="py-10 text-center text-sm text-muted-foreground">
        อัปโหลดไฟล์แล้วสกัดข้อความ จากนั้นกดวิเคราะห์เพื่อดูผล
      </p>
    );
  }
  return (
    <>
      <p className="mb-3 text-sm text-navy" data-testid="analyze-summary">
        คะแนนรวม {result.total}/100 — {result.summary}
      </p>
      <AnalyzePanelBody result={result} panel={panel} copiedKey={copiedKey} onCopy={onCopy} />
    </>
  );
}

function AnalyzeStepper({ step }: Readonly<{ step: AnalyzeStep }>) {
  return (
    <ol className="mb-4 flex flex-wrap gap-2 text-[12px]" data-testid="analyze-stepper">
      {ANALYZE_STEPS.map((label, index) => {
        const id = (index + 1) as AnalyzeStep;
        return (
          <li
            key={label}
            className={cn(
              "rounded-full border px-3 py-1 font-bold",
              step === id
                ? "border-crimson bg-brand-orange text-navy"
                : "border-gray-200 bg-gray-50 text-muted-foreground"
            )}
          >
            {id}. {label}
          </li>
        );
      })}
    </ol>
  );
}

export default function AnalyzePage() {
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState<AnalyzeStep>(1);
  const [extracted, setExtracted] = useState("");
  const [methodNote, setMethodNote] = useState("");
  const [panel, setPanel] = useState<AnalyzePanel>("legal");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);
  const shownStatus = useElapsedStatus(busy && status.startsWith("กำลัง"), status);
  const actions: AnalyzeSetters = { setBusy, setStatus, setError, setCopiedKey, setResult, setPanel };

  function resetUpload(next: File | null) {
    setFile(next);
    setStep(1);
    setExtracted("");
    setMethodNote("");
    setResult(null);
    setError(null);
    setStatus("");
    setCopiedKey(null);
  }

  async function extract() {
    if (!file) return;
    setBusy(true);
    setStatus("กำลังสกัดข้อความ...");
    setError(null);
    setResult(null);
    setCopiedKey(null);
    try {
      const payload = await extractAnalyzeFile(file);
      const text = (payload.extracted_text || "").trim();
      if (!text) {
        throw new Error("สกัดข้อความจากไฟล์ไม่ได้");
      }
      setExtracted(text);
      setStep(2);
      const warnings = (payload.warnings || []).filter(Boolean).join(" ");
      setMethodNote([methodLabel(payload.method), warnings].filter(Boolean).join(" — "));
      setStatus("สกัดข้อความสำเร็จ — ตรวจตัวอย่างแล้วกดวิเคราะห์ TOR");
    } catch (err: unknown) {
      const message = apiErrorMessage(err, "สกัดข้อความไม่สำเร็จ");
      setStatus(message);
      setError(message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-w-0" data-testid="analyze-page">
      <h1 className="text-2xl font-extrabold text-navy">วิเคราะห์ TOR</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        อัปโหลดไฟล์ TOR แล้วให้ระบบ OCR หรือดึงข้อความ จากนั้นดูสามด้านและข้อเสนอแนะพร้อมแหล่งออนไลน์ต่อหมวด
        ระบบจะไม่เขียนทับร่างให้อัตโนมัติ
      </p>

      <div className="mt-4 space-y-3 rounded-xl bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
        <AnalyzeStepper step={result ? 3 : step} />
        <p className="text-sm text-muted-foreground">
          เลือกไฟล์แล้วสกัดข้อความก่อน — ระบบจะไม่วิเคราะห์จนกว่าคุณยืนยัน
        </p>
        <UploadArea
          label="ลากไฟล์ TOR วาง หรือคลิกเพื่อเลือก"
          hint="PDF, Word (.docx), ข้อความ (.txt) หรือรูปภาพสแกน"
          onFiles={(list) => resetUpload(list[0] || null)}
        />
        {file ? (
          <p className="text-[12.5px]" data-testid="analyze-file-name">
            {file.name} · {Math.round(file.size / 1024)} KB
          </p>
        ) : null}
        {step === 1 ? (
          <Button
            data-testid="analyze-extract"
            onClick={() => {
              void extract();
            }}
            disabled={!file || busy}
          >
            {busy ? "กำลังสกัดข้อความ..." : "อัปโหลดและสกัดข้อความ"}
          </Button>
        ) : null}
        {step >= 2 && extracted ? (
          <div data-testid="analyze-extract-preview">
            <h2 className="text-sm font-bold text-navy">ตัวอย่างข้อความที่สกัดได้</h2>
            {methodNote ? (
              <p className="mt-1 text-xs text-muted-foreground" data-testid="analyze-extract-note">
                {methodNote}
              </p>
            ) : null}
            <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-md bg-gray-50 p-3 text-[12px]">
              {previewSnippet(extracted)}
            </pre>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                variant="outline"
                data-testid="analyze-back"
                onClick={() => {
                  setStep(1);
                  setResult(null);
                  setStatus("");
                  setError(null);
                }}
                disabled={busy}
              >
                ย้อนกลับ
              </Button>
              <Button
                data-testid="analyze-run"
                onClick={() => {
                  void runAnalysis(extracted, actions);
                }}
                disabled={busy}
              >
                {runLabel(busy)}
              </Button>
            </div>
          </div>
        ) : null}
        <AnalyzeStatus status={shownStatus} />
        <AnalyzeError error={error} />
      </div>

      <div className="mt-5 flex min-w-0 flex-col gap-4 lg:flex-row">
        <PanelNav panel={panel} onSelect={setPanel} />
        <div className="min-w-0 flex-1 rounded-xl bg-white p-4 shadow-[0_2px_8px_rgba(0,0,0,0.07)]">
          <AnalyzeBody
            result={result}
            panel={panel}
            copiedKey={copiedKey}
            onCopy={(key, value) => {
              void rememberCopy(key, value, setCopiedKey);
            }}
          />
        </div>
      </div>
    </div>
  );
}
