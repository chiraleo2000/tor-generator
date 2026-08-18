"use client";

import { useState } from "react";
import {
  BookOpen,
  CircleHelp,
  Cpu,
  Home,
  LayoutDashboard,
  LogIn,
  MessagesSquare,
  PenLine,
  ScanSearch,
} from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "overview", label: "ภาพรวม", icon: Home },
  { id: "login", label: "เข้าสู่ระบบ", icon: LogIn },
  { id: "dashboard", label: "แดชบอร์ด", icon: LayoutDashboard },
  { id: "draft", label: "ร่าง TOR", icon: PenLine },
  { id: "chat", label: "ถาม-ตอบ", icon: MessagesSquare },
  { id: "kb", label: "ฐานความรู้", icon: BookOpen },
  { id: "review", label: "ตรวจสอบ", icon: ScanSearch },
  { id: "admin", label: "ผู้ดูแล", icon: Cpu },
  { id: "faq", label: "FAQ", icon: CircleHelp },
] as const;

export default function HelpPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("overview");
  return (
    <div data-testid="help-page">
      <div className="mb-5 flex flex-wrap gap-1.5 border-b-2 pb-0">
        {TABS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              data-testid={`help-tab-${item.id}`}
              onClick={() => setTab(item.id)}
              className={cn(
                "inline-flex items-center gap-1.5 border-b-[3px] px-3 py-2.5 text-[13.5px] font-bold",
                tab === item.id
                  ? "border-crimson text-navy"
                  : "border-transparent text-muted-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {item.label}
            </button>
          );
        })}
      </div>
      {tab === "overview" ? (
        <GuideBlock title="ภาพรวมระบบ">
          <p>
            ระบบช่วยเจ้าหน้าที่พัสดุร่างและตรวจสอบ TOR ตาม พ.ร.บ. การจัดซื้อจัดจ้างฯ พ.ศ. 2560
            มี 13 หมวด แชทร่างใน Phase 0–1 และถาม-ตอบคลังความรู้แยกต่างหาก
          </p>
          <Flow steps={["เข้าสู่ระบบ", "แดชบอร์ด", "แชทร่าง 5 Phase", "ถาม-ตอบ", "ตรวจสอบ"]} />
        </GuideBlock>
      ) : null}
      {tab === "login" ? (
        <GuideBlock title="เข้าสู่ระบบ">
          <ol>
            <li>เปิด http://localhost:3000 — ระบบพาไป /login</li>
            <li>บัญชีทดลอง: officer@example.go.th / Passw0rd! (รัน python -m app.seed_db ก่อน)</li>
            <li>ผู้ดูแล admin@example.go.th และผู้ตรวจ reviewer@example.go.th ใช้รหัสเดียวกัน</li>
            <li>สมัครสมาชิกได้ที่ /register — บัญชีใหม่ได้บทบาทเจ้าหน้าที่</li>
          </ol>
          <table>
            <thead>
              <tr>
                <th>บทบาท</th>
                <th>อีเมล</th>
                <th>ใช้ทำอะไร</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>เจ้าหน้าที่</td>
                <td>officer@example.go.th</td>
                <td>ร่าง 5 Phase, ถาม-ตอบ, ส่งออก</td>
              </tr>
              <tr>
                <td>ผู้ตรวจสอบ</td>
                <td>reviewer@example.go.th</td>
                <td>อนุมัติหรือส่งกลับ</td>
              </tr>
              <tr>
                <td>ผู้ดูแล</td>
                <td>admin@example.go.th</td>
                <td>แม่แบบ คลังกลาง การตั้งค่า AI</td>
              </tr>
            </tbody>
          </table>
          <p className="rounded-md bg-amber-50 p-2 text-amber-900">
            รหัสผ่านต้องมีตัวพิมพ์ใหญ่ เล็ก ตัวเลข และอักขระพิเศษ — ค่าทดลองคือ Passw0rd!
          </p>
        </GuideBlock>
      ) : null}
      {tab === "dashboard" ? (
        <GuideBlock title="แดชบอร์ด">
          <ol>
            <li>การ์ดสถานะ: ร่าง / กำลังดำเนินการ / เสร็จแล้ว</li>
            <li>กดสร้างโครงการ กรอกชื่อ หน่วยงาน งบ ประเภทงาน</li>
            <li>เปิดโครงการแล้วเข้ากระบวนการ 5 Phase ที่ /projects/&#123;id&#125;/draft</li>
          </ol>
        </GuideBlock>
      ) : null}
      {tab === "draft" ? (
        <GuideBlock title="กระบวนการร่าง 5 Phase">
          <Flow
            steps={[
              "Phase 0 อัปโหลดชุดใหญ่",
              "Phase 1 แชทถามส่วนขาด",
              "Phase 2 ร่าง 13 หมวด",
              "Phase 3 ทบทวน HITL",
              "Phase 4 ส่งออก",
            ]}
          />
          <ol>
            <li>Phase 0–1 เป็นแชทโครงการ — อัปโหลดหลายไฟล์ได้โดยไม่ต้องเลือก 9 ประเภท</li>
            <li>บอทจัดเข้า s1–s13 และ s4.1–s4.14 แล้วถามช่องที่ขาด</li>
            <li>ปุ่มดึงอ้างอิงกฎหมายใส่เป็น Reference ไม่สวมเป็นข้อเท็จจริงโครงการ</li>
            <li>เมื่อครบเกณฑ์ กดพร้อมร่าง แล้วเข้า Phase 2 เอดิเตอร์ 13 หมวด</li>
            <li>ร่างด้วย AI เขียนลงช่องที่เห็นในหน้าจอ — หมวด s3 s6 s8 s10 s13 ต้องยืนยันโดยเจ้าหน้าที่</li>
          </ol>
          <table>
            <thead>
              <tr>
                <th>สถานะช่อง</th>
                <th>ความหมาย</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>filled</td>
                <td>มีข้อเท็จจริงจากเอกสารหรือคำตอบในแชท</td>
              </tr>
              <tr>
                <td>gap</td>
                <td>ยังขาด — บอทจะถามต่อ</td>
              </tr>
              <tr>
                <td>reference_only</td>
                <td>อ้างกฎหมายได้ แต่ยังไม่ใช่ข้อเท็จจริงโครงการ (วงเงิน/ชื่อโครงการใช้สถานะนี้ไม่ได้)</td>
              </tr>
            </tbody>
          </table>
          <p className="rounded-md bg-amber-50 p-2 text-amber-900">
            อย่าเริ่มจากเมนูร่าง TOR ถ้ายังไม่มีโครงการ — สร้างจากแดชบอร์ดก่อน
          </p>
        </GuideBlock>
      ) : null}
      {tab === "chat" ? (
        <GuideBlock title="ถาม-ตอบ">
          <ol>
            <li>เมนูการทำงาน → ถาม-ตอบ เปิด /chat</li>
            <li>ซ้ายเป็นห้องย่อ (ชื่อ ข้อความล่าสุด เวลา) — สร้าง เปลี่ยนชื่อ ลบได้</li>
            <li>แนบไฟล์เข้าคลังส่วนตัว (Mongo) แล้วถามด้วย RAG + กราฟกฎหมาย</li>
            <li>สลับแหล่งค้น: คลังกลาง / ของฉัน / ทั้งคู่</li>
            <li>ประวัติห้องร่างไม่ปนกับห้องถาม-ตอบ</li>
          </ol>
          <table>
            <thead>
              <tr>
                <th>ชนิดห้อง</th>
                <th>ที่อยู่</th>
                <th>แหล่งค้น</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>kb</td>
                <td>/chat</td>
                <td>คลังกลาง + เอกสารของฉัน</td>
              </tr>
              <tr>
                <td>draft_intake</td>
                <td>Phase 0–1 ของโครงการ</td>
                <td>เอกสารชุดร่าง + กฎหมายอ้างอิง</td>
              </tr>
            </tbody>
          </table>
        </GuideBlock>
      ) : null}
      {tab === "kb" ? (
        <GuideBlock title="ฐานความรู้">
          <p>
            คลังกลาง seed จาก PDF ข้อมูลดิบด้วย python -m app.seed_raw_docs (EmbeddingGemma จริง)
            ไม่ใช้ JSON extracts เก่าเป็นคลังใช้งาน
          </p>
          <p>ผู้ดูแลอัปโหลดคลังกลาง ผู้ใช้ทั่วไปอัปโหลดได้เฉพาะคลังส่วนตัวจากหน้าแชท</p>
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
      {tab === "admin" ? (
        <GuideBlock title="ผู้ดูแลระบบ">
          <p>หน้าแม่แบบ ผู้ใช้ และ การตั้งค่า AI — ค่าเริ่มต้น LM Studio ที่พอร์ต 1234</p>
          <p>
            สลับไป Anthropic / OpenAI / Gemini / Bedrock / Azure Foundry / OpenAI-compatible ได้
            บันทึกแล้วมีผลทันที คีย์ไม่โชว์เต็ม
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
          <p>
            Seed คลังจากโฮสต์ถ้า bind-mount ไทยพัง: POSTGRES_HOST=127.0.0.1 และ
            python -m app.seed_raw_docs
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
      <div className="space-y-2 text-[13.8px] leading-relaxed text-gray-700 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_table]:w-full [&_table]:text-left [&_td]:border-t [&_td]:py-1.5 [&_td]:pr-3 [&_th]:py-1.5 [&_th]:pr-3 [&_th]:text-navy">
        {children}
      </div>
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
