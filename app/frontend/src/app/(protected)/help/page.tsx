"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "ภาพรวม" },
  { id: "dashboard", label: "แดชบอร์ด" },
  { id: "kb", label: "ฐานความรู้" },
  { id: "draft", label: "ร่าง TOR" },
  { id: "review", label: "ตรวจสอบ" },
  { id: "faq", label: "FAQ" },
] as const;

export default function HelpPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("overview");
  return (
    <div data-testid="help-page">
      <div className="mb-5 flex flex-wrap gap-1.5 border-b-2 pb-0">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            data-testid={`help-tab-${item.id}`}
            onClick={() => setTab(item.id)}
            className={cn(
              "border-b-[3px] px-4 py-2.5 text-[13.5px] font-bold",
              tab === item.id
                ? "border-crimson text-navy"
                : "border-transparent text-muted-foreground"
            )}
          >
            {item.label}
          </button>
        ))}
      </div>
      {tab === "overview" ? (
        <GuideBlock title="ภาพรวมระบบ">
          <p>
            ระบบช่วยเจ้าหน้าที่พัสดุร่างและตรวจสอบ TOR ตาม พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560
            มี 13 หมวด และรองรับร่างด้วย AI (Gemma ในเครื่อง หรือคลาวด์)
          </p>
          <Flow
            steps={["เข้าสู่ระบบ", "แดชบอร์ด", "ฐานความรู้", "ร่าง 5 Phase", "ตรวจสอบ"]}
          />
        </GuideBlock>
      ) : null}
      {tab === "dashboard" ? (
        <GuideBlock title="แดชบอร์ด">
          <p>การ์ดสถานะสามใบ: ร่าง / กำลังดำเนินการ / เสร็จแล้ว และตารางโครงการ</p>
          <p>กดสร้างโครงการใหม่แล้วกรอกฟอร์มสร้างโครงการ แล้วเข้า Phase 0</p>
        </GuideBlock>
      ) : null}
      {tab === "kb" ? (
        <GuideBlock title="ฐานความรู้">
          <p>คลังกฎหมายกลาง เอกสารที่ผ่านการ chunk เข้า RAG และไฟล์ที่ผู้ใช้อัปโหลด</p>
        </GuideBlock>
      ) : null}
      {tab === "draft" ? (
        <GuideBlock title="กระบวนการร่าง 5 Phase">
          <Flow
            steps={[
              "Phase 0 อัปโหลด",
              "Phase 1 วิเคราะห์",
              "Phase 2 13 หมวด",
              "Phase 3 ทบทวน",
              "Phase 4 ส่งออก",
            ]}
          />
          <p>
            กดร่างด้วย AI ในแต่ละหมวด ช่องที่ระบบเติมจากไฟล์มีแท็กจับคู่
            หมวดคุณสมบัติ งบ งวดจ่าย ค่าปรับ และเงื่อนไขอื่นต้องให้เจ้าหน้าที่ยืนยัน
          </p>
        </GuideBlock>
      ) : null}
      {tab === "review" ? (
        <GuideBlock title="ตรวจสอบ TOR">
          <p>
            อัปโหลดไฟล์ที่มีอยู่แล้ว ระบบอ้างอิงกฎหมายบังคับเสมอ เทียบเคียงไฟล์อื่นด้วย Jaccard
            และแสดงผลเป็นรายการผ่าน/เตือน/ไม่ผ่าน
          </p>
        </GuideBlock>
      ) : null}
      {tab === "faq" ? (
        <GuideBlock title="คำถามที่พบบ่อย">
          <p>ลืมรหัสผ่าน: ให้ผู้ดูแลระบบรีเซ็ตที่หน้าผู้ใช้</p>
          <p>
            LLM ไม่ตอบ: เปิด LM Studio ที่ http://127.0.0.1:1234 โหลดแชท google/gemma-4-e4b และ embeddings
            text-embedding-embeddinggemma-300m หรือสลับ Local/Cloud ที่หน้าการตั้งค่า AI
          </p>
          <p>โหมด on-prem ไม่ส่งเนื้อหาโครงการออกนอกเครื่อง</p>
        </GuideBlock>
      ) : null}
    </div>
  );
}

function GuideBlock({
  title,
  children,
}: Readonly<{ title: string; children: React.ReactNode }>) {
  return (
    <div className="guide-content space-y-3">
      <h2 className="text-[19px] font-bold text-navy">{title}</h2>
      <div className="space-y-2 text-[13.8px] leading-relaxed text-gray-700">{children}</div>
    </div>
  );
}

function Flow({ steps }: Readonly<{ steps: string[] }>) {
  return (
    <div className="illus-flow my-4 flex flex-wrap items-center justify-center gap-2 rounded-xl border bg-gradient-to-br from-indigo-50 to-orange-50 p-5">
      {steps.map((step, index) => (
        <span key={step} className="flex items-center gap-2">
          <span className="min-w-[90px] rounded-lg border-2 border-navy bg-white px-3 py-2 text-center text-xs font-bold text-navy">
            {step}
          </span>
          {index < steps.length - 1 ? (
            <span className="font-extrabold text-crimson">→</span>
          ) : null}
        </span>
      ))}
    </div>
  );
}
