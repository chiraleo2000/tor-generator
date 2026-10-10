"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";

export type BidderRiskRowView = {
  issue?: string;
  requirement?: string;
  quote?: string;
  page_ref?: string;
  impact?: string;
  level?: string;
  mitigation?: string;
  signal?: string;
};

export type BidderRiskCategoryView = {
  key: string;
  label: string;
  rows?: BidderRiskRowView[];
};

export type BidderPenaltyView = {
  budget?: number | null;
  percent_per_day?: number | null;
  baht_per_day?: number | null;
  amount_30_days?: number | null;
  amount_60_days?: number | null;
  base?: string;
  base_label?: string;
  hourly_note?: string;
  phase_penalty_note?: string;
  overlap_note?: string;
  amount_note?: string;
};

export type BidderRiskView = {
  recommendation?: string;
  recommendation_kind?: string;
  disclaimer?: string;
  gates?: string[];
  penalty?: BidderPenaltyView | null;
  categories?: BidderRiskCategoryView[];
  markdown?: string;
};

function formatBaht(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "";
  return `${value.toLocaleString("th-TH")} บาท`;
}

function cell(value: string | undefined): string {
  return (value || "").replaceAll("|", String.raw`\|`).replaceAll("\n", " ");
}

export function bidderRiskMarkdown(report: BidderRiskView): string {
  const ready = (report.markdown || "").trim();
  if (ready) return report.markdown || ready;
  const lines = ["# ความเสี่ยงก่อนตัดสินใจยื่น", "", report.recommendation || "", ""];
  const penalty = report.penalty;
  lines.push("## ค่าปรับ", "");
  if (penalty?.base_label) lines.push(`- ฐาน: ${penalty.base_label}`);
  if (penalty?.amount_note) lines.push(`- ${penalty.amount_note}`);
  if (penalty?.hourly_note) lines.push(`- ${penalty.hourly_note}`);
  if (penalty?.phase_penalty_note) lines.push(`- ${penalty.phase_penalty_note}`);
  if (penalty?.overlap_note) lines.push(`- ${penalty.overlap_note}`);
  lines.push("");
  for (const category of report.categories || []) {
    lines.push(
      `## ${category.label}`,
      "",
      "| ประเด็น | ข้อกำหนด | ผลกระทบ | ระดับ | สิ่งที่ต้องตรวจ |",
      "| --- | --- | --- | --- | --- |",
    );
    const rows = category.rows || [];
    if (!rows.length) {
      lines.push("| ไม่พบประเด็นจากข้อความที่มี |  |  |  |  |");
    }
    for (const row of rows) {
      lines.push(
        `| ${cell(row.issue)} | ${cell(row.requirement)} | ${cell(row.impact)} | ${cell(row.level)} | ${cell(row.mitigation)} |`
      );
    }
    lines.push("");
  }
  return lines.join("\n");
}

function PenaltyBox({ penalty }: Readonly<{ penalty?: BidderPenaltyView | null }>) {
  if (!penalty) return null;
  return (
    <div className="rounded-lg border border-navy/15 bg-slate-50 p-3 text-sm text-navy" data-testid="bidder-risk-penalty">
      <p className="font-bold">ค่าปรับ</p>
      <p className="mt-1">ฐาน: {penalty.base_label || "ข้อความไม่ได้ระบุฐานค่าปรับ"}</p>
      {penalty.baht_per_day != null ? (
        <p className="mt-1" data-testid="bidder-risk-penalty-amounts">
          {formatBaht(penalty.baht_per_day)}/วัน
          {penalty.amount_30_days != null ? ` · 30 วัน ${formatBaht(penalty.amount_30_days)}` : ""}
          {penalty.amount_60_days != null ? ` · 60 วัน ${formatBaht(penalty.amount_60_days)}` : ""}
        </p>
      ) : (
        <p className="mt-1">{penalty.amount_note || "ไม่แสดงจำนวนเงินเพราะไม่มีวงเงินหรืออัตราในเอกสาร"}</p>
      )}
      {penalty.hourly_note ? <p className="mt-1">{penalty.hourly_note}</p> : null}
      {penalty.phase_penalty_note ? <p className="mt-1">{penalty.phase_penalty_note}</p> : null}
      {penalty.overlap_note ? <p className="mt-1">{penalty.overlap_note}</p> : null}
    </div>
  );
}

export function BidderRiskPanel({ report }: Readonly<{ report: BidderRiskView }>) {
  const [copied, setCopied] = useState(false);
  const categories = report.categories || [];

  async function copyReport() {
    try {
      await navigator.clipboard.writeText(bidderRiskMarkdown(report));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="space-y-4" data-testid="bidder-risk-panel">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="text-base font-bold text-navy">ความเสี่ยงก่อนตัดสินใจยื่น</h2>
        <Button type="button" variant="outline" size="sm" data-testid="bidder-risk-copy" onClick={() => { copyReport().catch(() => undefined); }}>
          {copied ? "คัดลอกแล้ว" : "คัดลอกรายงานเป็นมาร์กดาวน์"}
        </Button>
      </div>
      <p className="text-sm font-semibold text-navy" data-testid="bidder-risk-recommendation">
        {report.recommendation || "ข้อมูลไม่พอสำหรับประเมินความเสี่ยงก่อนยื่น"}
      </p>
      {report.gates?.length ? (
        <p className="text-xs text-muted-foreground" data-testid="bidder-risk-gates">
          ด่านที่ยังเปิด: {report.gates.join(", ")}
        </p>
      ) : null}
      <PenaltyBox penalty={report.penalty} />
      {categories.map((category) => {
        const rows = category.rows || [];
        return (
          <div key={category.key} className="overflow-x-auto" data-testid={`bidder-risk-table-${category.key}`}>
            <h3 className="mb-2 text-sm font-bold text-navy">{category.label}</h3>
            <table className="w-full min-w-[640px] border-collapse text-left text-xs">
              <thead>
                <tr className="border-b border-navy/20 text-navy">
                  <th className="px-2 py-1 font-bold">ประเด็น</th>
                  <th className="px-2 py-1 font-bold">ข้อกำหนด</th>
                  <th className="px-2 py-1 font-bold">ผลกระทบ</th>
                  <th className="px-2 py-1 font-bold">ระดับ</th>
                  <th className="px-2 py-1 font-bold">สิ่งที่ต้องตรวจ</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 ? (
                  <tr>
                    <td className="px-2 py-2 text-muted-foreground" colSpan={5}>
                      ไม่พบประเด็นจากข้อความที่มี
                    </td>
                  </tr>
                ) : (
                  rows.map((row, index) => (
                    <tr key={`${category.key}-${index}`} className="border-b border-gray-100 align-top">
                      <td className="px-2 py-2">{row.issue}</td>
                      <td className="px-2 py-2">{row.requirement}</td>
                      <td className="px-2 py-2">{row.impact}</td>
                      <td className="px-2 py-2 whitespace-nowrap">{row.level}</td>
                      <td className="px-2 py-2">{row.mitigation}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        );
      })}
    </section>
  );
}
