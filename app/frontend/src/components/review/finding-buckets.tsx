"use client";

import { CheckItem } from "@/components/brand/check-item";
import {
  findingCheckTone,
  findingDetail,
  splitReviewFindings,
  type ReviewFinding,
} from "@/lib/review-findings";

export function ReviewFindingBuckets({
  findings,
}: Readonly<{ findings: ReviewFinding[] }>) {
  const { legal, risk } = splitReviewFindings(findings);
  return (
    <div className="space-y-3" data-testid="review-finding-buckets">
      <FindingGroup
        testId="review-legal-findings"
        title="กลุ่ม ก — ผิดกฎหมาย / ระเบียบ"
        hint="ข้อที่ขัด พ.ร.บ. จัดซื้อจัดจ้าง ระเบียบกระทรวงการคลัง หรือหลักเกณฑ์ที่อ้างได้"
        items={legal}
      />
      <FindingGroup
        testId="review-risk-findings"
        title="กลุ่ม ข — ความเสี่ยงจากความผิดปกติ"
        hint="ภาษาคลุมเครือ ราคา/ต้นทุนผิดสัดส่วน หรือเนื้อหาขัดกัน แม้ยังไม่ชี้ชัดว่าผิดมาตรา"
        items={risk}
      />
    </div>
  );
}

function FindingGroup({
  testId,
  title,
  hint,
  items,
}: Readonly<{
  testId: string;
  title: string;
  hint: string;
  items: ReviewFinding[];
}>) {
  return (
    <section data-testid={testId}>
      <h4 className="text-sm font-bold text-navy">{title}</h4>
      <p className="mb-2 text-xs text-muted-foreground">{hint}</p>
      {items.length === 0 ? (
        <p className="text-xs text-muted-foreground">ไม่พบรายการในกลุ่มนี้</p>
      ) : (
        items.map((finding, index) => (
          <CheckItem
            key={`${finding.rule}-${index}`}
            tone={findingCheckTone(finding.severity)}
            title={finding.message}
            detail={findingDetail(finding)}
          />
        ))
      )}
    </section>
  );
}
