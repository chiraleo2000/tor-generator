"use client";

import Image from "next/image";
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
  { id: "faq", label: "คำถามที่พบบ่อย", icon: CircleHelp },
] as const;

export default function HelpPage() {
  const [tab, setTab] = useState<(typeof TABS)[number]["id"]>("overview");
  return (
    <div data-testid="help-page" className="max-w-4xl">
      <div className="mb-2">
        <h1 className="text-2xl font-extrabold text-navy">คู่มือการใช้งาน</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          คำอธิบายและภาพประกอบแต่ละส่วนของระบบ — สรุปจาก discussions/13–30 (v0.2.5)
        </p>
      </div>
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
      {tab === "overview" ? <OverviewTab /> : null}
      {tab === "login" ? <LoginTab /> : null}
      {tab === "dashboard" ? <DashboardTab /> : null}
      {tab === "draft" ? <DraftTab /> : null}
      {tab === "chat" ? <ChatTab /> : null}
      {tab === "kb" ? <KbTab /> : null}
      {tab === "review" ? <ReviewTab /> : null}
      {tab === "admin" ? <AdminTab /> : null}
      {tab === "faq" ? <FaqTab /> : null}
    </div>
  );
}

function OverviewTab() {
  return (
    <GuideBlock title="ภาพรวมระบบ">
      <p>
        ระบบช่วยเจ้าหน้าที่พัสดุ<strong>ร่างและตรวจสอบ TOR</strong> ตาม พ.ร.บ. การจัดซื้อจัดจ้างและการบริหารพัสดุภาครัฐ
        พ.ศ. 2560 บังคับโครง 13 ส่วน (<code>s1</code>–<code>s13</code>) + ขอบเขตงานย่อย{" "}
        <code>s4.1</code>–<code>s4.14</code> รวม 27 ช่อง
      </p>
      <p>
        เส้นทางหลักบนหน้าจอคือ<strong>พื้นที่ทำงานห้าขั้น</strong> (ไม่ใช่วิซาร์ดแปดขั้น) แยกจากเมนู{" "}
        <strong>ถาม-ตอบ</strong> (คลังความรู้) และ <strong>ตรวจสอบ TOR</strong> (ไฟล์ภายนอก)
      </p>
      <Flow steps={["เข้าสู่ระบบ", "แดชบอร์ด", "ร่างห้าขั้น", "ถาม-ตอบ", "ตรวจสอบ"]} />
      <Figure src="/help/19-diagram-architecture.png" alt="สถาปัตยกรรมระบบ" caption="สถาปัตยกรรม: ผู้ใช้ → Next.js :3000 → FastAPI :4000 → คลังข้อมูล / LLM / Rule Engine" />
      <Figure src="/help/19-diagram-phases.png" alt="ห้าขั้น" caption="พื้นที่ทำงานห้าขั้น — เส้นทางหลักบนหน้าจอ" />
      <h3>สามเครื่องมือของเจ้าหน้าที่</h3>
      <table>
        <thead>
          <tr>
            <th>เครื่องมือ</th>
            <th>เมนู / หน้า</th>
            <th>ผลที่ควรเห็น</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>ร่าง TOR</td>
            <td>
              <code>/projects/&#123;id&#125;/draft</code>
            </td>
            <td>เนื้อหา s1–s13 พร้อมส่งตรวจ</td>
          </tr>
          <tr>
            <td>ตรวจสอบ TOR</td>
            <td>Phase 4 + <code>/review</code></td>
            <td>คะแนน ≥ 70 / findings / suggestions</td>
          </tr>
          <tr>
            <td>ถาม-ตอบ</td>
            <td>
              <code>/chat</code>
            </td>
            <td>คำตอบ SSE + ชิปอ้างอิงจากคลัง</td>
          </tr>
        </tbody>
      </table>
      <h3>สแตกที่รันจริง</h3>
      <table>
        <thead>
          <tr>
            <th>ชั้น</th>
            <th>ค่า</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>UI</td>
            <td>Next.js 14 · พอร์ต 3000 · ภาษาไทยทั้งหน้าจอ</td>
          </tr>
          <tr>
            <td>API</td>
            <td>FastAPI · พอร์ต 4000 · <code>/api/v1</code></td>
          </tr>
          <tr>
            <td>AI ค่าเริ่มต้น</td>
            <td>
              LM Studio · แชท <code>google/gemma-4-e4b</code> · ฝังเวกเตอร์ EmbeddingGemma 768-d
            </td>
          </tr>
          <tr>
            <td>คลัง</td>
            <td>PostgreSQL+pgvector · Mongo GridFS · Neo4j · Redis · MinIO</td>
          </tr>
        </tbody>
      </table>
      <DocLinks />
    </GuideBlock>
  );
}

function LoginTab() {
  return (
    <GuideBlock title="เข้าสู่ระบบ">
      <ol>
        <li>
          เปิด <code>http://localhost:3000</code> — ระบบพาไป <code>/login</code>
        </li>
        <li>
          บัญชีทดลอง (รัน <code>python -m app.seed_db</code> จาก <code>app/backend</code> ก่อน):
        </li>
      </ol>
      <table>
        <thead>
          <tr>
            <th>บทบาท</th>
            <th>อีเมล</th>
            <th>รหัสผ่าน</th>
            <th>ใช้ทำอะไร</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>เจ้าหน้าที่</td>
            <td>
              <code>officer@example.go.th</code>
            </td>
            <td>
              <code>Passw0rd!</code>
            </td>
            <td>ร่างห้าขั้น, ถาม-ตอบ, ส่งออก, ตรวจไฟล์ภายนอก</td>
          </tr>
          <tr>
            <td>ผู้ตรวจสอบ</td>
            <td>
              <code>reviewer@example.go.th</code>
            </td>
            <td>
              <code>Passw0rd!</code>
            </td>
            <td>เห็นทุกโครงการ · อนุมัติ / ส่งกลับ</td>
          </tr>
          <tr>
            <td>ผู้ดูแล</td>
            <td>
              <code>admin@example.go.th</code>
            </td>
            <td>
              <code>Passw0rd!</code>
            </td>
            <td>แม่แบบ · คลังกลาง · ผู้ใช้ · การตั้งค่า AI</td>
          </tr>
        </tbody>
      </table>
      <p className="rounded-md bg-amber-50 p-2 text-amber-900">
        รหัสผ่านต้องมีตัวพิมพ์ใหญ่ เล็ก ตัวเลข และอักขระพิเศษ — ค่าทดลองคือ <code>Passw0rd!</code>
      </p>
      <ol start={3}>
        <li>
          เซสชันอยู่ในคุกกี้ HttpOnly <code>tor_access_token</code> (SameSite=Lax) —{" "}
          <strong>ไม่เก็บ JWT ใน localStorage</strong>
        </li>
        <li>
          สมัครสมาชิกที่ <code>/register</code> — บัญชีใหม่ได้บทบาทเจ้าหน้าที่
        </li>
      </ol>
      <Figure src="/help/00-login.png" alt="หน้าเข้าสู่ระบบ" caption="หน้าเข้าสู่ระบบ — กล่อง Demo ใต้ปุ่ม" />
      <Figure src="/help/00c-login-error.png" alt="รหัสผ่านผิด" caption="อีเมล/รหัสผิด — แถบข้อผิดพลาด ไม่เข้าแดชบอร์ด" />
      <Figure src="/help/00b-register.png" alt="สมัครสมาชิก" caption="ฟอร์มสมัครสมาชิก" />
    </GuideBlock>
  );
}

function DashboardTab() {
  return (
    <GuideBlock title="แดชบอร์ด">
      <p>
        หัวข้อหน้า: <strong>แดชบอร์ด</strong> — ภาพรวมโครงการ TOR · มุมขวาบนแสดงอีเมลที่ล็อกอิน
      </p>
      <h3>แถบซ้าย</h3>
      <table>
        <thead>
          <tr>
            <th>กลุ่ม</th>
            <th>เมนู</th>
            <th>ไปที่</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>หลัก</td>
            <td>แดชบอร์ด</td>
            <td>
              <code>/projects</code>
            </td>
          </tr>
          <tr>
            <td>หลัก</td>
            <td>ฐานความรู้</td>
            <td>
              <code>/knowledge-base</code>
            </td>
          </tr>
          <tr>
            <td>การทำงาน</td>
            <td>ร่าง TOR · ตรวจสอบ TOR · ถาม-ตอบ</td>
            <td>
              <code>/draft</code> · <code>/review</code> · <code>/chat</code>
            </td>
          </tr>
          <tr>
            <td>อื่นๆ</td>
            <td>คู่มือ</td>
            <td>
              <code>/help</code>
            </td>
          </tr>
          <tr>
            <td>ผู้ดูแล (admin)</td>
            <td>แม่แบบ · คลัง · ผู้ใช้ · ตั้งค่า AI</td>
            <td>
              <code>/admin/...</code>
            </td>
          </tr>
        </tbody>
      </table>
      <h3>สถานะในตาราง</h3>
      <table>
        <thead>
          <tr>
            <th>ป้าย</th>
            <th>ความหมาย</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>ร่าง</td>
            <td>แก้ห้าขั้นได้</td>
          </tr>
          <tr>
            <td>กำลังดำเนินการ</td>
            <td>ส่งขออนุมัติแล้ว — ปิดแก้</td>
          </tr>
          <tr>
            <td>เสร็จแล้ว</td>
            <td>อนุมัติแล้ว · ดู / ปรับปรุง</td>
          </tr>
          <tr>
            <td>ส่งกลับ</td>
            <td>ผู้ตรวจสอบส่งกลับ — ส่งใหม่ได้</td>
          </tr>
        </tbody>
      </table>
      <ol>
        <li>กด <strong>สร้างโครงการ</strong> กรอกชื่อ หน่วยงาน งบ (เลข ASCII) ประเภทงาน</li>
        <li>
          เปิดโครงการแล้วเข้า <code>/projects/&#123;id&#125;/draft</code> ที่ Phase 0
        </li>
        <li>ผู้ตรวจสอบเห็นปุ่มอนุมัติ/ส่งกลับเมื่อสถานะกำลังดำเนินการ</li>
      </ol>
      <Figure src="/help/02-dashboard.png" alt="แดชบอร์ด" caption="แดชบอร์ดหลังล็อกอินเจ้าหน้าที่" />
      <Figure src="/help/02b-create-dialog.png" alt="สร้างโครงการ" caption="กล่องสร้างโครงการใหม่" />
      <Figure
        src="/help/02c-reviewer-dashboard.png"
        alt="แดชบอร์ดผู้ตรวจสอบ"
        caption="แดชบอร์ดผู้ตรวจสอบ — ปุ่มอนุมัติ/ส่งกลับ"
      />
    </GuideBlock>
  );
}

function DraftTab() {
  return (
    <GuideBlock title="กระบวนการร่างห้าขั้น">
      <Flow
        steps={[
          "ขั้นที่ ๐ อัปโหลด",
          "ขั้นที่ ๑ ผลวิเคราะห์",
          "ขั้นที่ ๒ สอบถามเพิ่ม",
          "ขั้นที่ ๓ ร่างสิบสามหมวด",
          "ขั้นที่ ๔ ทบทวน-เผยแพร่",
        ]}
      />
      <table>
        <thead>
          <tr>
            <th>ขั้น</th>
            <th>ทำอะไร</th>
            <th>เกต</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>
              <strong>๐</strong>
            </td>
            <td>วางข้อความ / อัปโหลดหลายครั้ง — กดเริ่มต้นครั้งเดียว (ยังไม่วิเคราะห์)</td>
            <td>กดเริ่มต้น → วิเคราะห์ เข้าขั้นที่ ๑</td>
          </tr>
          <tr>
            <td>
              <strong>๑</strong>
            </td>
            <td>ดูตารางผลวิเคราะห์จากเอกสารโครงการ แล้วกดไปขั้นที่ ๒ — ดึงมาตรฐานกลางด้วยปุ่มในขั้นที่ ๒</td>
            <td>กดปุ่มไปขั้นที่ ๒ (ไม่มีไดอะล็อก)</td>
          </tr>
          <tr>
            <td>
              <strong>๒</strong>
            </td>
            <td>ตารางสถานะคู่แชทถามช่องข้อเท็จจริงที่ขาด · ไม่มีปุ่มต่อแถว · กดใช้มาตรฐานกลางเติมช่องว่างได้ · ติ๊กแนบอ้างอิงกฎหมายตอนส่งคำตอบ</td>
            <td>
              ยืนยันพร้อมร่าง → ปลดขั้นที่ ๓
            </td>
          </tr>
          <tr>
            <td>
              <strong>๓</strong>
            </td>
            <td>ระบบร่างทั้งสิบสามหมวดอัตโนมัติ · หมวดขอบเขตงานเติมลงหัวข้อย่อย · แก้ในแชทได้ · เอกสารขั้นที่ ๐ ใช้เฉพาะโครงการนี้</td>
            <td>ร่างครบสิบสามหมวด → ไปทบทวน (ขั้นที่ ๔)</td>
          </tr>
          <tr>
            <td>
              <strong>๔</strong>
            </td>
            <td>แชทรีวิวสรุปคะแนน · ตรวจด้วยกฎอัตโนมัติเมื่อเข้าขั้น · ส่งขออนุมัติ · ส่งออกเวิร์ด/พีดีเอฟ</td>
            <td>ผู้ตรวจ/ผู้ดูแลอนุมัติหรือส่งกลับ</td>
          </tr>
        </tbody>
      </table>
      <h3>สถานะช่อง (ขั้นที่ ๑–๒)</h3>
      <table>
        <thead>
          <tr>
            <th>สถานะ</th>
            <th>ความหมาย</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>มีข้อมูล</td>
            <td>ข้อเท็จจริงจากเอกสารหรือคำตอบในแชท</td>
          </tr>
          <tr>
            <td>ส่วนขาด</td>
            <td>ยังขาด — บอทถามต่อ</td>
          </tr>
          <tr>
            <td>อ้างกฎหมายเท่านั้น</td>
            <td>อ้างกฎหมายได้ แต่ยังไม่ใช่ข้อเท็จจริงโครงการ (วงเงิน/ชื่อใช้สถานะนี้ไม่ได้)</td>
          </tr>
        </tbody>
      </table>
      <ol>
        <li>
          ขั้นที่ ๐: อัปโหลดหรือวางข้อความ แล้วกดเริ่มวิเคราะห์ — ต้องยืนยันในกล่องโต้ตอบ (ยังไม่วิเคราะห์ตอนอัปโหลด)
        </li>
        <li>
          ขั้นที่ ๑: ดูตารางความครบจากเอกสารที่วิเคราะห์ แล้วกด{" "}
          <strong>ไปขั้นที่ ๒</strong>
        </li>
        <li>
          ขั้นที่ ๒: แชทถามช่องข้อเท็จจริงที่ขาด กด <strong>ใช้มาตรฐานกลางเติมช่องว่าง</strong> ถ้ายังขาดช่องกฎหมาย
          ติ๊ก <strong>แนบอ้างอิงกฎหมายประกอบคำตอบนี้</strong> ตอนส่ง แล้วกดพร้อมร่าง
        </li>
        <li>
          ขั้นที่ ๓: ระบบร่างสิบสามหมวดอัตโนมัติถ้ายังไม่ครบ — แก้ในแชทแล้วกด{" "}
          <strong>ไปทบทวน (ขั้นที่ ๔)</strong>
        </li>
        <li>
          ขั้นที่ ๔: แชทรีวิว + ตรวจด้วยกฎอัตโนมัติเมื่อเข้าขั้น ส่งขออนุมัติ และส่งออกเวิร์ด/พีดีเอฟ
        </li>
      </ol>
      <p className="rounded-md bg-amber-50 p-2 text-amber-900">
        อย่าเริ่มจากเมนูร่าง TOR ถ้ายังไม่มีโครงการ — สร้างจากแดชบอร์ดก่อน
        เอกสารที่อัปโหลดในขั้นที่ ๐ ใช้เฉพาะโครงการนั้น ตรวจกับ พ.ร.บ. และกฎระเบียบกลางเมื่อเข้าทบทวน
      </p>
      <Figure src="/help/03-phase-0-upload.png" alt="ขั้นที่ ๐" caption="ขั้นที่ ๐ — อัปโหลดหรือวางข้อความ แล้วกดเริ่มต้น (ยังไม่วิเคราะห์)" />
      <Figure src="/help/e2e-phase-1-coverage.png" alt="ขั้นที่ ๑" caption="ขั้นที่ ๑ — ตารางผลวิเคราะห์ แล้วกดไปคุยต่อขั้นที่ ๒" />
      <Figure src="/help/e2e-phase-2-qa.png" alt="ขั้นที่ ๒" caption="ขั้นที่ ๒ — ตารางสถานะ คู่แชทถามช่องที่ขาด และตัวเลือกแนบอ้างอิงตอนส่งคำตอบ" />
      <Figure src="/help/e2e-phase-3-draft.png" alt="ขั้นที่ ๓" caption="ขั้นที่ ๓ — ร่างสิบสามหมวดและหัวข้อย่อย แล้วกดไปทบทวน" />
      <Figure src="/help/e2e-phase-4-review-chat.png" alt="ขั้นที่ ๔" caption="ขั้นที่ ๔ — แชทรีวิว คะแนนจากกฎ และส่งออก" />
    </GuideBlock>
  );
}

function ChatTab() {
  return (
    <GuideBlock title="ถาม-ตอบ">
      <p>
        เมนู <strong>ถาม-ตอบ</strong> เปิด <code>/chat</code> — ห้องคลังความรู้รายคน (SSE + ชิปอ้างอิง)
        คนละประวัติกับแชทร่าง Phase 2 ระบบดึงชิ้นข้อความจาก pgvector หลายสิบชิ้นภายในหน้าต่าง 128K
        ของ Gemma แล้วตอบแบบบันทึกของเจ้าหน้าที่พัสดุ
      </p>
      <ol>
        <li>ซ้าย: รายการห้องย่อ (ชื่อ · ข้อความล่าสุด · เวลา) — สร้าง เปลี่ยนชื่อ ลบได้</li>
        <li>
          แนบไฟล์ด้วยไอคอนคลิป — ระบบสร้างห้องถ้ายังไม่มี แล้วแสดงข้อความ ingest เช่น *ถูกเพิ่มเข้าคลังของฉันแล้ว*
          (หมวดข้อมูลอื่น ๆ) จากนั้นถามด้วย RAG และเปิดดูที่ฐานความรู้ได้
        </li>
        <li>สลับแหล่งค้น: คลังกลาง / ของฉัน / ทั้งคู่</li>
        <li>ระหว่างรอมีจุดพิมพ์ · ข้อความแสดงเวลาเมื่อ API ส่งมา</li>
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
            <td>
              <code>kb</code>
            </td>
            <td>
              <code>/chat</code>
            </td>
            <td>คลังกลาง + เอกสารของฉัน</td>
          </tr>
          <tr>
            <td>
              <code>draft_intake</code>
            </td>
            <td>Phase 2 ของโครงการ</td>
            <td>Phase 2 ของโครงการ (`POST .../intake/chat`) — แนบอ้างอิงกฎหมายได้ ไม่ใช่ห้อง `/chat`</td>
          </tr>
        </tbody>
      </table>
      <p className="rounded-md bg-amber-50 p-2 text-amber-900">
        ถ้าคำตอบว่างหรือไม่มี citation — รัน <code>python -m app.seed_raw_docs</code> และตรวจ Mongo + Neo4j
        healthy
      </p>
      <Figure src="/help/13-kb-chat.png" alt="ถาม-ตอบ" caption="หน้าถาม-ตอบ — ห้องย่อและแชทคลังความรู้" />
      <Figure src="/help/13b-chat-attach.png" alt="แนบไฟล์" caption="แนบไฟล์แล้วเห็นข้อความเพิ่มเข้าคลังของฉัน" />
    </GuideBlock>
  );
}

function KbTab() {
  return (
    <GuideBlock title="ฐานความรู้">
      <p>
        คลังกลางใส่จาก PDF ใน <code>documents/sources/</code> ด้วย{" "}
        <code>python -m app.seed_raw_docs</code> (ฝังเวกเตอร์จริง) —{" "}
        <strong>ไม่ ingest JSON extracts เก่าเป็นคลังใช้งาน</strong>
      </p>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          เจ้าหน้าที่: ดูคลังกลาง + เอกสารของฉันด้านบนสุดที่ <code>/knowledge-base</code> — แสดงสถานะประมวลผลและหมวด
          (รวม <strong>ข้อมูลอื่น ๆ</strong>) ลบ/ดาวน์โหลดได้เฉพาะของตัวเอง ไม่แชร์ข้ามคน
        </li>
        <li>ผู้ดูแล: อัปโหลดคลังกลางที่หน้าฐานความรู้ (จัดการ)</li>
        <li>ยังแนบไฟล์เข้าคลังส่วนตัวจากหน้าถาม-ตอบได้</li>
      </ul>
      <Figure src="/help/11-knowledge-base.png" alt="ฐานความรู้" caption="หน้าฐานความรู้ — เอกสารของฉันด้านบน พร้อมสถานะประมวลผลและหมวด" />
      <Figure src="/help/17-admin-kb.png" alt="คลังผู้ดูแล" caption="ฐานความรู้ฝั่งผู้ดูแล (คลังกลาง)" />
    </GuideBlock>
  );
}

function ReviewTab() {
  return (
    <GuideBlock title="ตรวจสอบ TOR">
      <p>มีสองเส้นทาง:</p>
      <ol>
        <li>
          <strong>ในโครงการขั้นที่ ๔</strong> — แชทรีวิว + ตรวจด้วยกฎอัตโนมัติเมื่อเข้าขั้น (คะแนน ≥ 70 เป็นโทนผ่านบนจอ ไม่ล็อกส่งตรวจ) + ข้อเสนอแนะจากการทบทวน
        </li>
        <li>
          <strong>
            หน้า <code>/review</code>
          </strong>{" "}
          — ตรวจไฟล์ TOR ภายนอก โดยไม่ต้องสร้างโครงการ · สามขั้น: เลือกไฟล์ → สกัดข้อความ → ยืนยันเริ่มตรวจสอบ · อ้างอิงกฎหมายบังคับ · เทียบเคียงไฟล์อื่นด้วยความคล้ายข้อความ
        </li>
      </ol>
      <p>
        คะแนนต่ำกว่า 70 = ยังไม่ผ่านเกณฑ์เบื้องต้น · น้ำหนักหลัก: กฎหมาย 40% · ความครบ 30% · ความสอดคล้อง 20% ·
        รูปแบบ 10%
      </p>
      <Figure src="/help/12-standalone-review.png" alt="ตรวจสอบ TOR" caption="หน้าตรวจสอบ TOR — ขั้น 1 เลือกไฟล์ ปุ่มสกัดข้อความยังกดไม่ได้" />
      <Figure src="/help/12a-review-detail.png" alt="ผลตรวจสอบ" caption="ขั้น 2–3 — ตัวอย่างข้อความที่สกัดได้ คะแนน Rule Engine หลังยืนยันเริ่มตรวจสอบ" />
    </GuideBlock>
  );
}

function AdminTab() {
  return (
    <GuideBlock title="ผู้ดูแลระบบ">
      <p>
        เฉพาะบัญชี <code>admin</code>: แม่แบบ · ฐานความรู้ (จัดการ) · ผู้ใช้ ·{" "}
        <strong>การตั้งค่า AI</strong>
      </p>
      <h3>การตั้งค่า AI</h3>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          โหมด (<code>on_prem</code> / <code>cloud</code> / <code>hybrid</code>) เป็นป้ายเท่านั้น —{" "}
          <strong>ไม่สลับคู่</strong> แชทกับฝังเวกเตอร์
        </li>
        <li>
          ค่าเริ่มต้น: LM Studio <code>google/gemma-4-e4b</code> + EmbeddingGemma · timeout 600s · pgvector
        </li>
        <li>
          <strong>ทดสอบการเชื่อมต่อ</strong> ยิงทั้งแชทและฝังเวกเตอร์ ·{" "}
          <strong>บันทึกมีผลทันที</strong> ไม่ต้องรีสตาร์ท backend
        </li>
      </ul>
      <h3>สูตรที่ใช้บ่อย</h3>
      <table>
        <thead>
          <tr>
            <th>เป้าหมาย</th>
            <th>แชท</th>
            <th>ฝังเวกเตอร์</th>
            <th>ต้อง seed ใหม่?</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Gemma ในเครื่อง</td>
            <td>LM Studio</td>
            <td>EmbeddingGemma</td>
            <td>ไม่</td>
          </tr>
          <tr>
            <td>Claude + ฝังเวกเตอร์ในเครื่อง</td>
            <td>Claude</td>
            <td>ในเครื่อง</td>
            <td>ไม่ (ถ้าเคยใช้ EmbeddingGemma)</td>
          </tr>
          <tr>
            <td>Claude + OpenAI embeddings</td>
            <td>Claude</td>
            <td>OpenAI</td>
            <td>
              <strong>ใช่</strong> — <code>python -m app.seed_raw_docs</code>
            </td>
          </tr>
        </tbody>
      </table>
      <Figure src="/help/16-admin-templates.png" alt="แม่แบบ" caption="จัดการแม่แบบ" />
      <Figure src="/help/18-admin-users.png" alt="ผู้ใช้" caption="จัดการผู้ใช้และบทบาท" />
      <Figure src="/help/09-admin-ai-lm-studio.png" alt="ตั้งค่า AI" caption="การตั้งค่า AI — ทดสอบเชื่อมต่อ LM Studio" />
      <Figure src="/help/09a-admin-ai-local.png" alt="เซิร์ฟเวอร์ในเครื่อง" caption="ฟอร์มเซิร์ฟเวอร์ในเครื่อง" />
      <Figure src="/help/09b-admin-ai-cloud.png" alt="คีย์คลาวด์" caption="เลือก Claude แล้วใส่คีย์คลาวด์" />
    </GuideBlock>
  );
}

function FaqTab() {
  return (
    <GuideBlock title="คำถามที่พบบ่อย">
      <h3>ติดตั้งและสุขภาพระบบ</h3>
      <ul className="list-disc space-y-1 pl-5">
        <li>
          คู่มือติดตั้งเต็ม: <code>discussions/14-INSTALLATION.md</code> — Docker compose โปรเจกต์{" "}
          <code>tor-app</code> + LM Studio ที่ <code>127.0.0.1:1234</code>
        </li>
        <li>
          Dev ค่าเริ่มต้น: แชท <code>google/gemma-4-e4b</code> · ฝังเวกเตอร์{" "}
          <code>text-embedding-embeddinggemma-300m</code> (768 มิติ)
        </li>
        <li>
          Production แนะนำ: Amazon Bedrock — คู่มือ <code>discussions/20-AWS_BEDROCK_SETUP.md</code>
        </li>
        <li>
          ตรวจสุขภาพ: <code>http://localhost:4000/health</code> ต้อง healthy (postgres redis minio mongo neo4j)
        </li>
        <li>
          seed ผู้ใช้: <code>python -m app.seed_db</code> · seed คลัง:{" "}
          <code>python -m app.seed_raw_docs</code>
        </li>
      </ul>
      <h3>แก้ปัญหาใช้งาน</h3>
      <table>
        <thead>
          <tr>
            <th>อาการ</th>
            <th>สิ่งที่ตรวจ</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>เข้าสู่ระบบแล้วเด้งกลับ</td>
            <td>
              รหัส <code>Passw0rd!</code> · backend :4000 · คุกกี้ไม่ถูกบล็อก
            </td>
          </tr>
          <tr>
            <td>ถาม-ตอบว่าง / ไม่มี citation</td>
            <td>
              <code>seed_raw_docs</code> · Mongo + Neo4j healthy
            </td>
          </tr>
          <tr>
            <td>ร่างด้วย AI ไม่ตอบ</td>
            <td>
              LM Studio :1234 โหลด Gemma + EmbeddingGemma หรือใส่คีย์คลาวด์ที่การตั้งค่า AI
            </td>
          </tr>
          <tr>
            <td>พร้อมร่างกดไม่ได้</td>
            <td>ช่องข้อเท็จจริงบังคับต้องเป็น filled ไม่ใช่แค่ reference กฎหมาย</td>
          </tr>
          <tr>
            <td>ส่งขออนุมัติกดไม่ได้</td>
            <td>ครบ 13 หมวด</td>
          </tr>
          <tr>
            <td>สร้างโครงการไม่ได้</td>
            <td>งบประมาณต้องเป็นเลข ASCII ไม่ใช่เลขไทย</td>
          </tr>
          <tr>
            <td>อัปโหลดคลังกลางไม่ได้</td>
            <td>เจ้าหน้าที่ใช้ “เอกสารของฉัน” — คลังกลางสงวนไว้ผู้ดูแล</td>
          </tr>
          <tr>
            <td>ลืมรหัสผ่าน</td>
            <td>ผู้ดูแลสร้างบัญชีใหม่หรือตั้งรหัสตอนสร้าง (ยังไม่มีปุ่มรีเซ็ตแถวเดิม)</td>
          </tr>
        </tbody>
      </table>
      <h3>คุณภาพและความครอบคลุม (รอบ 20 ส.ค. 2026)</h3>
      <table>
        <thead>
          <tr>
            <th>ชุด</th>
            <th>ผล</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>pytest (ไม่รวม live_llm)</td>
            <td>1448 ผ่าน</td>
          </tr>
          <tr>
            <td>pytest live_llm</td>
            <td>10 ผ่าน (LM Studio)</td>
          </tr>
          <tr>
            <td>Vitest</td>
            <td>128 ผ่าน</td>
          </tr>
          <tr>
            <td>Playwright headed</td>
            <td>15 ผ่าน</td>
          </tr>
        </tbody>
      </table>
      <p>
        รายละเอียดและภาพหลักฐาน: <code>discussions/18-TEST_EVIDENCE.md</code> · รายงานการทำงานครบ:{" "}
        <code>discussions/19-APPLICATION_OPERATING_REPORT.md</code> (มี PDF / DOCX / PPTX)
      </p>
      <p className="rounded-md bg-slate-50 p-2 text-slate-800">
        การตั้งค่าโมเดลและคลังความรู้เป็นหน้าที่<strong>ผู้ดูแล</strong> — เจ้าหน้าที่ใช้เมนูร่าง TOR /
        ตรวจสอบ / ถาม-ตอบ บนหน้าจอหลักเท่านั้น
      </p>
      <DocLinks />
    </GuideBlock>
  );
}

function DocLinks() {
  return (
    <p className="text-xs text-muted-foreground">
      อ่านเพิ่มใน repo: <code>13-USER_GUIDELINE</code> · <code>14-INSTALLATION</code> ·{" "}
      <code>15-APPLICATION_DESCRIPTION</code> · <code>16-BACKEND</code> · <code>17-FRONTEND</code> ·{" "}
      <code>18-TEST_EVIDENCE</code> · <code>19-OPERATING_REPORT</code>
    </p>
  );
}

function Figure({
  src,
  alt,
  caption,
}: Readonly<{ src: string; alt: string; caption: string }>) {
  return (
    <figure className="my-4 overflow-hidden rounded-lg border bg-white">
      <Image
        src={src}
        alt={alt}
        width={1440}
        height={900}
        className="h-auto w-full object-contain"
        unoptimized
      />
      <figcaption className="border-t bg-slate-50 px-3 py-2 text-center text-xs text-muted-foreground">
        {caption}
      </figcaption>
    </figure>
  );
}

interface GuideBlockProps {
  title: string;
  children: React.ReactNode;
}

function GuideBlock({ title, children }: Readonly<GuideBlockProps>) {
  return (
    <div className="guide-content space-y-3">
      <h2 className="text-[19px] font-bold text-navy">{title}</h2>
      <div className="space-y-3 text-[13.8px] leading-relaxed text-gray-700 [&_code]:rounded [&_code]:bg-slate-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-[12px] [&_h3]:mt-3 [&_h3]:text-[15px] [&_h3]:font-bold [&_h3]:text-navy [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_table]:w-full [&_table]:text-left [&_td]:border-t [&_td]:py-1.5 [&_td]:pr-3 [&_th]:py-1.5 [&_th]:pr-3 [&_th]:text-navy">
        {children}
      </div>
    </div>
  );
}

interface FlowProps {
  steps: string[];
}

function Flow({ steps }: Readonly<FlowProps>) {
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
