# เอกสารโครงสร้าง TOR ที่ถูกต้องและครอบคลุมทั้งหมด
## 10 ส่วนหลักกับการเขียนแบบละเอียดตรวจสอบได้ทีละขั้น

---

## 📌 บทนำและประเด็นที่สำคัญ

### TOR คืออะไร และทำไมถึงสำคัญ?

**TOR (Terms of Reference)** คือเอกสารอย่างเป็นทางการที่ใช้ในการ:
- กำหนดรายละเอียดของงานที่จะจ้างอย่างชัดเจน
- ระบุเงื่อนไข ข้อกำหนด และความคาดหวังที่เป็นรูปธรรม
- ป้องกันข้อพิพาท ความเข้าใจผิด และการท้าทายภายหลัง
- ให้สิทธิท้ายธุรกิจ (Bidders) เข้าใจสิ่งที่ต้องทำ
- เป็นเอกสารหลักฐานกฎหมายเมื่อสัญญาเกิดข้อโต้แย้ง

TOR ที่ดี = ร่างสัญญาที่ชัดเจน → ลดปัญหา → ประหยัดเวลา/เงิน

---

## 🏗️ โครงสร้าง 10 ส่วน - คำอธิบายอย่างละเอียด

### ⭐ ส่วนที่ 1: ความเป็นมา (Background & Rationale) - 500-800 คำ

#### **1.1 จุดประสงค์และความสำคัญ**

ส่วน "ความเป็นมา" ต้องตอบคำถาม: **"ทำไมถึงต้องจ้าง? ปัญหาคืออะไร? ทำไมไม่สร้างเองด้วยเจ้าหน้าที่?"**

ส่วนนี้เป็นการสร้างพื้นฐานให้กับทั้ง TOR เพราะ:
- ทำให้เข้าใจบริบท (Context) ของโครงการ
- ทำให้ Bidders เข้าใจว่า "ลูกค้า" มีปัญหาอะไร
- เป็นหลักฐานกฎหมายว่า "มีเหตุผลในการจัดจ้าง"
- ถ้าเขียนได้ดี จะเบลจำนวน Protests (การท้าทาย) ได้

#### **1.2 องค์ประกอบที่ต้องเขียน**

**A. ประวัติของระบบ/บริการเดิม (2-3 ย่อหน้า)**

ต้องเขียนให้อ่านแล้วทราบว่า:
- ระบบ/บริการนี้เกิดขึ้นเมื่อไหร่? ปี พ.ศ. เท่าไหร่?
- ใครสร้างมา? บริษัทใด? หรือทำเองด้วยเจ้าหน้าที่?
- ถูกสร้างมาเพื่อทำอะไร? เป้าหมายเดิมคืออะไร?
- ตอนนี้ยังใช้งานอยู่หรือ? จำนวนผู้ใช้กี่คน?
- เคยอัพเกรด/บำรุงรักษามั้ย? ครั้งล่าสุดเมื่อไหร่?

**ตัวอย่างที่ดี:**
```
"ระบบ e-Payment ได้รับการพัฒนาและอัปเดตครั้งแรก ในปี พ.ศ. 2560 
โดยบริษัท XYZ Technology Co., Ltd. ด้วยงบประมาณ 20 ล้านบาท 
โดยระบบนี้ได้รับการออกแบบเพื่อรองรับการชำระเงินแบบอิเล็กทรอนิกส์ 
สำหรับกระทรวงสรรพากร รองรับผู้ใช้ประมาณ 100-200 ราย ต่อวัน 
ระบบนี้ยังคงปฏิบัติงานอยู่ในปัจจุบัน แต่เริ่มมีปัญหาเนื่องจากอายุของระบบ"
```

**B. สถานการณ์ปัจจุบัน (3-4 ย่อหน้า)**

ต้องอธิบายสถานการณ์ "ตอนนี้" อย่างเป็นรูปธรรมด้วยตัวเลข:
- จำนวนผู้ใช้ปัจจุบันเท่าไหร่? เปรียบเทียบกับ Capacity
- ขนาดของข้อมูล (Data volume) เท่าไหร่? เช่น TB หรือ GB
- ความเร็วระบบ (Response time) ปัจจุบันเท่าไหร่? (เช่น 5-10 วินาที)
- Uptime/Downtime สถิติเท่าไหร่? (เช่น 95% uptime = 5% downtime)
- ยังรองรับการเติบโต (Scalability) ได้หรือไม่?

**ตัวอย่างที่ดี:**
```
"ตามสถิติการใช้งานระบบ e-Payment ในปี พ.ศ. 2569 พบว่า:
- จำนวนผู้ใช้ที่เข้ามาใช้งาน: ประมาณ 500-800 คน/วัน (เพิ่มขึ้น 300% จากปี 2568)
- ขนาดของฐานข้อมูล: ประมาณ 500 GB (เพิ่มขึ้น 150% ต่อปี)
- Average Response Time: 5-10 วินาทีต่อ Transaction (ช้ากว่าเป้าหมาย 2 วินาที)
- System Availability: 95% (มีการ Downtime เฉลี่ย 7 วันต่อเดือน)
- Current System Capacity: รองรับไม่ถึง 200 concurrent users 
  แต่ความต้องการปัจจุบัน: 500 concurrent users"
```

**C. ปัญหาที่พบ (3-5 ข้อ พร้อมหลักฐาน)**

ต้องแสดงรายชื่อปัญหา พร้อมหลักฐานและความหนักแน่นของปัญหา:
- ปัญหา: ทำให้เกิดอะไร? 
- ความหนัก: ส่งผลกระทบเท่าไหร่? (เช่น เสียรายได้กี่บาท? ผู้ใช้โกรธหรือ?)
- ความถี่: เกิดบ่อยแค่ไหน? (เช่น 2-3 ครั้งต่อเดือน)

**ตัวอย่างที่ดี:**
```
ปัญหาที่ 1: ระบบขัดข้องและช้า
└─ สาเหตุ: Hardware เก่า (5 ปี), Database ไม่ได้ Optimize
└─ ผลกระทบ: Downtime เฉลี่ย 7 วัน/เดือน, ผู้ใช้เสียไป 2-3 พันครั้ง/วัน
└─ ความสูญเสีย: ประมาณ 50,000-100,000 บาท/เดือน

ปัญหาที่ 2: ไม่รองรับการเติบโต (Scalability Issue)
└─ สาเหตุ: ระบบออกแบบมาเพื่อ 100 users แต่ตอนนี้ 500 users
└─ ผลกระทบ: เมื่อ Peak Time ระบบช้าและ Hang
└─ ความสูญเสีย: ลูกค้าไปใช้บริการอื่น ประมาณ 10-15% ต่อเดือน

ปัญหาที่ 3: ไม่มีความปลอดภัยเพียงพอ
└─ สาเหตุ: ระบบเก่า ไม่มี Encryption, ไม่ใช้ HTTPS, ไม่มี MFA
└─ ผลกระทบ: ความเสี่ยงต่อการถูก Hack/ประมาณอาจถูกบันทึกเงินผิดเสีย
└─ ความสูญเสีย: ความเสี่ยงด้านกฎหมายและชื่อเสียง
```

**D. นโยบายที่เกี่ยวข้อง (1-2 ย่อหน้า)**

ระบุนโยบายสูงสุดที่สนับสนุนการจัดจ้างนี้:
- นโยบายรัฐบาล (เช่น Digital Transformation Strategy)
- นโยบายสาขา (เช่น ภายในกระทรวง)
- กฎหมายที่เกี่ยวข้อง (เช่น พระราชบัญญัติ จัดซื้อจัดจ้าง)

**ตัวอย่างที่ดี:**
```
"การจัดจ้างนี้สอดคล้องกับ:
1. นโยบาย 'ดิจิทัล ไทยแลนด์' ของรัฐบาล พ.ศ. 2563-2570 
   ซึ่งมุ่งเพื่อ Modern Government Infrastructure
2. National Strategy ในการสนับสนุน Financial System Modernization
3. กฎระเบียบกระทรวงสรรพากร ว่าด้วยการใช้งานระบบ IT ให้ทันสมัย"
```

**E. เหตุผลในการจัดจ้างภายนอก (1-2 ย่อหน้า)**

ต้องอธิบายว่า "ทำไมไม่สร้างเองด้วยเจ้าหน้าที่ภายใน?" 

**ตัวอย่างที่ดี:**
```
"กองเทคโนโลยีของกระทรวง มีบุคลากร IT ประมาณ 15 คน ซึ่งปัจจุบัน
ทั้งหมดต่างมีการมอบหมายงานบำรุงรักษา Hardware/Network ตามปกติแล้ว 
นอกจากนี้ยังขาดความเชี่ยวชาญเฉพาะด้าน:
- Cloud Architecture & Microservices (ไม่มีใครรู้)
- Security Hardening (มี 1 คนแต่ยุ่งเพราะแต่ละสิ่ง)
- DevOps & CI/CD Pipeline (ไม่มี)

ดังนั้น เพื่อให้ได้ผลงานที่มีคุณภาพและมีมาตรฐาน จึงจำเป็นต้องจัดจ้าง
ผู้เชี่ยวชาญจากภายนอกที่มีประสบการณ์ในด้านนี้"
```

**F. ผลกระทบหากไม่ดำเนินการ (0.5-1 ย่อหน้า - Optional แต่ดี)**

บอกว่า "ถ้าไม่จ้าง จะเสียอะไร?"

**ตัวอย่างที่ดี:**
```
"หากไม่ดำเนินการจัดจ้างนี้ ระบบอาจวิกฤติหลัง 6-12 เดือนโดยเสียเสมอ:
- ระบบอาจหยุดทำงานโดยสิ้นเชิง → ไม่สามารถ Collect Revenue
- Downtime ต่างประมาณ 30 วัน/เดือน → สูญรายได้ 15 ล้านบาท/เดือน
- ข้อมูลเสี่ยงต่อการถูก Hack → ความเสี่ยงกฎหมายและชื่อเสียง
- ลูกค้าอาจเทศนาโครงการไป Platform อื่น → สูญลูกค้า 30% ขึ้นไป"
```

---

### ⭐ ส่วนที่ 2: วัตถุประสงค์ (Objectives) - 300-500 คำ

#### **2.1 จุดประสงค์และความสำคัญ**

ส่วนนี้ตอบคำถาม: **"เราอยากได้อะไร? เมื่อโครงการสิ้นสุด ระบบต้องมี Features/Characteristics อะไร?"**

ข้อแตกต่างกับส่วนที่ 1:
- **ส่วนที่ 1 (Background)**: บอกว่า "มีปัญหาอะไร"
- **ส่วนที่ 2 (Objectives)**: บอกว่า "เราอยากได้ผลลัพธ์อะไร" (Solution)

#### **2.2 องค์ประกอบที่ต้องเขียน**

**A. วัตถุประสงค์หลัก (Main/General Objective) - 1 ข้อ**

เขียนเป้าหมายโดยรวมที่สุด ซึ่งมักจะแก้ปัญหาสำคัญจากส่วนที่ 1

**ตัวอย่างที่ดี:**
```
"เพื่อ Modernize และ Upgrade ระบบ e-Payment ให้มี:
 - ความพร้อมใช้งาน (Availability) สูง (99.9% ขึ้นไป)
 - รองรับการเติบโตของผู้ใช้ (Scalability) จาก 100 เป็น 500 users
 - ความปลอดภัยระดับสากล (ตามมาตรฐาน ISO 27001)
 - ประสิทธิภาพสูง (Response Time < 2 วินาที)"
```

**B. วัตถุประสงค์เฉพาะ (Specific Objectives) - 3-5 ข้อ**

เนื้อหาเจาะจงแต่ละด้าน แต่ละข้อต้อง "SMART" คือ:
- **S**pecific: เจาะจง (ไม่เรียบง่ายเกิน)
- **M**easurable: วัดได้ (มีตัวเลข/ตัวชี้วัด)
- **A**chievable: สำเร็จได้ (ไม่เป็นฝัน)
- **R**elevant: เกี่ยวข้อง (ตรงกับปัญหา)
- **T**ime-bound: มีเวลา (ต้องเสร็จภายในเท่าไหร่)

**ตัวอย่างที่ดี:**
```
Objective 1: ปรับปรุงประสิทธิภาพและความเร็ว
└─ SMART Details:
   - Specific: ลด Response Time จาก 5-10 วินาที เหลือ < 2 วินาที
   - Measurable: วัดจาก Server Logs (90th percentile)
   - Achievable: ผ่านการ Infrastructure Upgrade + Code Optimization
   - Relevant: แก้ปัญหา "ระบบช้า" จากส่วนที่ 1
   - Time-bound: ต้องเสร็จภายในโครงการ (เดือนที่ 6)

Objective 2: เพิ่มความสามารถรองรับผู้ใช้ (Scalability)
└─ SMART Details:
   - Specific: รองรับจาก 100 concurrent users → 500 concurrent users
   - Measurable: Load Test ผ่าน 500 concurrent users โดยไม่ Error
   - Achievable: ผ่านการ Re-architect + Cloud Infrastructure
   - Relevant: แก้ปัญหา "ไม่รองรับการเติบโต"
   - Time-bound: ต้องเสร็จทำ UAT ภายในเดือนที่ 5

Objective 3: เพิ่มความปลอดภัยตามมาตรฐาน ISO 27001
└─ SMART Details:
   - Specific: ผ่าน ISO 27001 Certification
   - Measurable: Security Audit ผ่านทั้งหมด 50/50 checklist items
   - Achievable: ติดตั้ง Encryption, Firewalls, MFA, ฯลฯ
   - Relevant: แก้ปัญหา "ความปลอดภัยไม่เพียงพอ"
   - Time-bound: ต้องเสร็จทำ Audit ภายในเดือนที่ 6

Objective 4: ฝึกอบรมบุคลากรภายใน
└─ SMART Details:
   - Specific: ฝึกอบรมเจ้าหน้าที่ 20 คน ให้สามารถจัดการระบบเอง
   - Measurable: ผ่าน Certification Test โดยได้คะแนน >= 70%
   - Achievable: ผ่านการฝึกอบรม 5 วัน (40 ชั่วโมง)
   - Relevant: เตรียมให้เจ้าหน้าฯ Maintain ระบบได้เอง
   - Time-bound: ต้องเสร็จฝึกอบรมภายในเดือนที่ 5-6

Objective 5: เขียน Documentation ให้สมบูรณ์
└─ SMART Details:
   - Specific: เขียน User Manual, Admin Guide, Runbook
   - Measurable: 100+ หน้า Documentation พร้อม Screenshots
   - Achievable: มี Technical Writer + SMEs
   - Relevant: เพื่อให้ Support & Maintenance ทำได้เอง
   - Time-bound: ต้องเสร็จพร้อมกับ Go-Live
```

**C. ผู้ใช้เป้าหมาย (Target Users/Stakeholders)**

บอกว่าใครเป็นผู้ใช้ระบบ มีกี่กลุ่ม?

**ตัวอย่างที่ดี:**
```
Target Users ประกอบด้วย 3 กลุ่ม:

1. Internal Users (เจ้าหน้าที่สรรพากร)
   └─ จำนวน: ประมาณ 100-150 คน
   └─ หน้าที่: ใช้ระบบเพื่อ Process Payment Requests
   └─ Frequency: Daily (วันละ 500-800 transactions)

2. External Partners (สถาบันการเงิน)
   └─ จำนวน: ประมาณ 5-7 สถาบัน (ธนาคาร, Payment Gateway)
   └─ หน้าที่: Integration กับระบบของเรา
   └─ Frequency: 24/7 (Real-time data exchange)

3. End Users (ผู้เสียภาษี)
   └─ จำนวน: ประมาณ 100,000+ คน
   └─ หน้าที่: ชำระเงินผ่าน Web Portal หรือ Mobile App
   └─ Frequency: Occasional (เมื่อต้องชำระ)
```

**D. ตัวชี้วัดผลการสำเร็จ (KPIs - Key Performance Indicators) - 3-5 ข้อ**

KPI ต้องเป็นตัวเลข วัดได้ และสัมพันธ์กับ Objectives

**ตัวอย่างที่ดี:**
```
KPI 1: System Uptime
└─ ตัวชี้วัด: ≥ 99.9% per month (allowed downtime 43.2 minutes/month)
└─ วิธีวัด: Monitoring Tool (Prometheus/Grafana)
└─ Acceptance: ต้องผ่าน 3 เดือนติดต่อกัน

KPI 2: Response Time
└─ ตัวชี้วัด: 90th Percentile Response Time < 2 seconds
└─ วิธีวัด: Server Logs + Load Testing
└─ Acceptance: ต้องผ่าน UAT Load Test

KPI 3: Transaction Success Rate
└─ ตัวชี้วัด: ≥ 99.5% of transactions สำเร็จโดยไม่มี Error
└─ วิธีวัด: Database Transaction Log
└─ Acceptance: ต้องผ่าน 1 เดือน Production Usage

KPI 4: System Scalability
└─ ตัวชี้วัด: ต้องรองรับ 500 concurrent users โดยไม่ Degrade Performance
└─ วิธีวัด: Load Testing (Apache JMeter / LoadRunner)
└─ Acceptance: ต้องผ่าน Load Test 500 concurrent users

KPI 5: Security Compliance
└─ ตัวชี้วัด: ผ่าน ISO 27001 Security Audit โดยไม่มี Critical/High findings
└─ วิธีวัด: Third-party Security Auditor
└─ Acceptance: ต้องได้ ISO 27001 Certificate
```

**E. SLA (Service Level Agreement) - ถ้ามี (1-2 ย่อหน้า)**

ระบุเงื่อนไขการใช้งาน:

**ตัวอย่างที่ดี:**
```
SLA Details:
- Availability: 24/7 × 365 days (No planned downtime except maintenance)
- Planned Maintenance Window: Sunday 02:00-04:00 AM (2 hours max/week)
- Incident Response Time:
  * P1 (Critical/Down): Response within 4 hours, Resolve within 8 hours
  * P2 (High/Degraded): Response within 8 hours, Resolve within 24 hours
  * P3 (Medium/Minor): Response within 24 hours, Resolve within 72 hours
- Escalation Path:
  * L1 Support: Help Desk (8am-5pm BKT, Mon-Fri)
  * L2 Support: Technical Team (24/7 on-call)
  * L3 Support: Vendor Management (Business Hours + On-Demand)
```

---

### ⭐ ส่วนที่ 3: คุณสมบัติ (Qualifications) - 800-1200 คำ

#### **3.1 จุดประสงค์และความสำคัญ**

ส่วนนี้ตอบคำถาม: **"ผู้รับจ้างต้องเป็นอย่างไร? มีความสามารถ เงิน และประสบการณ์พอหรือ?"**

นี่คือส่วนที่ "โดดเด่น" เพราะ:
- เป็นตัวกรอง Bidders (คัด Out ผู้ที่ไม่มีสมบัติ)
- ป้องกันไม่ให้ Bidder "ผ่ชี้" (ไม่มี Qualification แต่เสนอราคาต่ำ)
- ลดความเสี่ยงโครงการล่มสลาย
- เป็นพื้นฐานของการคัดเลือก (Section 6)

#### **3.2 องค์ประกอบที่ต้องเขียน**

**A. คุณสมบัติทั่วไป (General Qualifications)**

ต้องเป็นบริษัท/องค์กรที่ "ปกติสุข" และ "ถูกกฎหมาย"

**ตัวอย่างที่ดี:**
```
ผู้รับจ้างต้องเป็นไปตามเงื่อนไขต่อไปนี้:

ก. ต้องเป็นบุคคลธรรมชาติหรือนิติบุคคล (บริษัท) ที่มีสัญชาติไทย
   └─ หรือหากเป็นสาขาของบริษัท Foreign ต้องเป็นสาขา Thailand
   └─ เสนอหลักฐาน: Certificate of Incorporation + Company Registry

ข. ต้องลงทะเบียนกับ DBD (Department of Business Development)
   └─ ต้องเป็น Active Status (ไม่ Revoked/Suspended)
   └─ เสนอหลักฐาน: Business Registration Certificate

ค. ต้องลงทะเบียนกับ Revenue Department (สรรพากร)
   └─ ต้องเป็น Tax Compliant (ไม่มีหนี้ภาษี)
   └─ เสนอหลักฐาน: Tax ID Certificate

ง. ต้องไม่มีประวัติถูกรองเรียน หรือการบ่งชี้เจ้าหนี้ใหม่ๆ
   └─ (ไม่มี Outstanding Legal Cases ที่เป็น Fraud/Corruption)
   └─ เสนอหลักฐาน: Board Resolution / Affidavit

จ. ต้องเป็นปกติสุขทางการเงิน (Not Bankrupt)
   └─ ไม่เคยมีคำสั่งจำหน่ายล้มละลาย
   └─ เสนอหลักฐาน: Affidavit + Bank Statement

ฉ. ต้องไม่อยู่ในบัญชี "Blacklist" ของ Procurement
   └─ (ตามประกาศของหน่วยงาน)
   └─ เสนอหลักฐาน: Affidavit
```

**B. คุณสมบัติด้านการเงิน (Financial Qualification) ⭐ สำคัญมาก**

นี่คือตัวกรองที่สำคัญที่สุด เพราะบอกว่า:
- "บริษัท มีเงินทุนเพียงพอทำ Project นี้หรือ?"
- "ถ้า Project ต้องใช้ 100 ล้านบาท บริษัยต้องมี 25 ล้านบาท ขึ้นไป"

**ตัวอย่างที่ดี:**
```
ข้อ 2.1: ทุนจดทะเบียน (Paid-up Capital)

ผู้รับจ้างต้องมี Paid-up Capital ≥ 25,251,125 บาท 
(= 101,004,500 ÷ 4, คิดจาก Announced Price)

Calculation Logic:
└─ งบประมาณรวม: 101,004,500 บาท
└─ หารด้วย 4 (Standard Ratio): 101,004,500 ÷ 4 = 25,251,125 บาท
└─ เงื่อนไขในพระราชบัญญัติฯ กำหนดให้ผู้รับจ้างต้องมี Paid-up Capital 
   ≥ 1/4 ของมูลค่างบประมาณ

หลักฐานที่ต้องเสนอ:
├─ Bank Statement (ย้อนหลัง 6 เดือน ล่าสุด)
├─ Certificate of Paid-up Capital (จากธนาคาร)
├─ Company Registry Extract (แสดง Registered Capital)
└─ Financial Statements ที่ Audited (ประจำปีล่าสุด)

⚠️ สำคัญ: 
- Paid-up Capital หมายถึง "เงินที่ out แล้ว" ไม่ใช่ "Authorized Capital"
- ต้องวาง Margin จำนวนนี้ ไม่สามารถนำไปใช้ Project อื่น
- ถ้าต่ำกว่า จะถูก Disqualify เลย (ไม่มีการ Appeal)
```

**ข้อ 2.2: งบการเงินอดีต (Financial Statements)**

ต้องแสดงว่า "บริษัยมีรายได้และการดำเนินการปกติ"

**ตัวอย่างที่ดี:**
```
ผู้รับจ้างต้องเสนอ Financial Statements ที่ผ่านการตรวจสอบ (Audited)
ย้อนหลัง 2 ปีจากปีปัจจุบัน:

ตัวอย่าง: งบประมาณประจำปี 2570 → ต้องเสนอ Financial Statements ของ
          - ปี 2568 (Audited โดย Certified Auditor)
          - ปี 2569 (Audited โดย Certified Auditor)

หลักฐานที่ต้องเสนอ:
├─ Balance Sheet (แสดง Assets, Liabilities, Equity)
├─ Income Statement (แสดง Revenues, Expenses, Profits)
├─ Cash Flow Statement
└─ Auditor's Report (ต้องมี "Unqualified Opinion" หรือ "Clean Opinion")

ตัวชี้วัดที่ดู (บอกว่า บริษัยมีประสบการณ์/ปกติสุข):
- Revenue Trend: ต้องมีรายได้ Stable หรือ Growing (ไม่ Loss)
- Profit Margin: ≥ 5-10% (ไม่可以 Break Even อย่างจำเพาะ)
- Current Ratio: ≥ 1.5 (สภาพคล่องสำหรับจ่ายเงิน)
- Debt-to-Equity: ≤ 2.0 (ไม่ติดหนี้เกินไป)

⚠️ Red Flags ที่ต้องระวัง:
- บริษัย Loss ย้อนหลังหลายปี → อาจไม่มีเงินจริง
- Cash ต่ำแต่หนี้เยอะ → อาจไม่จ่ายได้
- Rapid Growth ที่ไม่ Normal → อาจเป็น Money Laundering
```

**C. คุณสมบัติด้านประสบการณ์ (Experience Qualification)**

บอกว่า "บริษัยเคยทำ Project แบบนี้มั้ย? เสร็จได้หรือ?"

**ตัวอย่างที่ดี:**
```
ข้อ 3.1: ประวัติบริษัท

ผู้รับจ้างต้อง:
- ก่อตั้งขึ้นตั้งแต่ เมื่อ 3 ปี ขึ้นไป (ไม่เกิน 15 ปี)
  └─ ตัวอย่าง: ถ้าวันนี้เป็น 2570 ต้องก่อตั้งมาตั้งแต่ 2567 ขึ้นไป
  └─ หลักฐาน: Certificate of Incorporation + Company Registry
  
- มี Track Record ในธุรกิจ IT/Software Development อย่างต่อเนื่อง
  └─ หลักฐาน: Portfolio ของโครงการที่เคยทำ + Reference Letters

ข้อ 3.2: โครงการอ้างอิง (Reference Projects) ⭐ สำคัญมาก

ผู้รับจ้างต้องมี Reference Projects ที่สำเร็จแล้ว:

จำนวน: 3-5 โครงการ (ไม่เกิน 5 เพราะไม่สร้างสรรค์)

มูลค่า: แต่ละโครงการต้องมีมูลค่า ≥ 30-50% ของงบประมาณนี้
└─ ตัวอย่าง: งบ 100 ล้าน → แต่ละ Ref Project ≥ 30-50 ล้านบาท
└─ ตัวอย่าง: ต้องมี Ref Projects ที่มูลค่า
   • Project A: 35 ล้านบาท (30%)
   • Project B: 40 ล้านบาท (40%)
   • Project C: 45 ล้านบาท (45%)

ความสม่ำเสมอ: โครงการต้องเสร็จภายในเวลา ≤ 5 ปี
└─ ตัวอย่าง: ถ้าวันนี้เป็น 30 กรกฎาคม 2570
   Ref Projects ต้องเสร็จไม่ก่อน 30 กรกฎาคม 2565
└─ (ไม่เก่าเกิน 5 ปี เพราะ Technology เปลี่ยน)

ความเหมาะสม: โครงการต้องเป็นแบบนี้หรือคล้ายกัน
└─ ตัวอย่าง: ถ้า Project นี้ "e-Payment System Development"
   Ref Projects ควรเป็น Financial System / Payment Gateway / Banking System
   ❌ ไม่ควร: Social Media App / E-commerce Platform (แม้ว่ามูลค่าเท่าก็ตาม)

หลักฐานที่ต้องเสนอ:
├─ Reference Letters จากลูกค้าเดิม (ลงลายมือชื่อ + Seal)
│  └─ บอก: Project Name, Duration, Contract Value, Status (Completed)
├─ Certificate of Project Completion (จากลูกค้า)
│  └─ ลงวันที่เสร็จ, ชื่อ Project, มูลค่า
├─ Performance Evaluation from Clients (ถ้ามี)
│  └─ บอก: Quality, On-Time Delivery, Support ฯลฯ
└─ Case Study / Portfolio
   └─ System Architecture, Features, Technology Used, Results

⚠️ การตรวจสอบ Reference:
- ผู้ประเมิน (Evaluator) มีสิทธิตรวจสอบ Reference โดย Call/Visit
- ถ้า Reference ไม่ตรง ↔ Disqualify ทั้ง Bidder
- ตัวอย่าง: "บอกว่า Project A สำเร็จ 50 ล้านบาท แต่จริงๆ 30 ล้าน" → Out
```

**D. คุณสมบัติด้านบุคลากร (Personnel Qualification)**

บอกว่า "บริษัยมี Key People พอหรือไม่?"

**ตัวอย่างที่ดี:**
```
ข้อ 4.1: Project Manager

จำนวน: 1 คน (Full-time ตั้งแต่ต้นจนจบ Project)

ต้องมี:
- ใบประกาศนียบัตร: PMP (Project Management Professional) หรือ PRINCE2
  └─ ต้องยังใช้ได้ (ไม่หมดอายุ)
  └─ เสนอหลักฐาน: Copy ใบประกาศนียบัตร
  
- ประสบการณ์: ≥ 5 ปี ด้าน IT Project Management
  └─ ต้องมี min 3 โครงการ IT (ไม่ใช่ Construction/Other)
  └─ เสนอหลักฐาน: CV + Reference Letters from Previous Projects
  
- ทักษะด้าน: Software Development Process, SDLC, Risk Management

ข้อ 4.2: System/Solution Architect

จำนวน: 1 คน (Full-time ระยะ Design, Part-time ระยะ Development)

ต้องมี:
- ใบประกาศนียบัตร: TOGAF (The Open Group Architecture Framework)
              หรือ EA (Enterprise Architecture) Certificate
  └─ เสนอหลักฐาน: Copy ใบประกาศนียบัตร
  
- ประสบการณ์: ≥ 5-7 ปี ด้าน System Architecture Design
  └─ ต้องมี min 5 โครงการ (ไม่ใช่ Dev หรือ QA อย่างเดียว)
  └─ เสนอหลักฐาน: CV + Architecture Designs ตัวอย่าง
  
- ทักษะด้าน: Cloud Architecture, Microservices, System Design Patterns

ข้อ 4.3: Database Administrator / Data Architect

จำนวน: 1 คน (Full-time ระยะ Design, Part-time ระยะ Operation)

ต้องมี:
- ใบประกาศนียบัตร: Oracle DBA / SQL Server / PostgreSQL DBA Certificate
  └─ หรือ MySQL/MongoDB/NoSQL Specialist Certificate
  └─ เสนอหลักฐาน: Copy ใบประกาศนียบัตร
  
- ประสบการณ์: ≥ 5 ปี ด้าน Database Administration / Design
  └─ ต้องมี min 3 โครงการ Large-Scale Database (ไม่ใช่ Small App)
  └─ เสนอหลักฐาน: CV + Database Design Documents ตัวอย่าง

ข้อ 4.4: Network / Infrastructure Engineer

จำนวน: 1 คน (Part-time ระยะ Design & Implementation)

ต้องมี:
- ใบประกาศนียบัตร: CCNA (Cisco Certified Network Associate) หรือเทียบเท่า
  └─ หรือ CompTIA Network+ / Linux LPIC-1
  └─ เสนอหลักฐาน: Copy ใบประกาศนียบัตร
  
- ประสบการณ์: ≥ 3-5 ปี ด้าน Infrastructure / Cloud Deployment
  └─ ต้องมี min 2 โครงการ Cloud Infrastructure (AWS/Azure/GCP)
  └─ เสนอหลักฐาน: CV + Infrastructure Design Examples

ข้อ 4.5: Security / Security Engineer

จำนวน: 1 คน (Part-time ระยะ Design & Testing)

ต้องมี:
- ใบประกาศนียบัตร: CISSP (Certified Information Systems Security Professional)
              หรือ CEH (Certified Ethical Hacker)
              หรือ Security+ CompTIA
  └─ เสนอหลักฐาน: Copy ใบประกาศนียบัตร
  
- ประสบการณ์: ≥ 3-5 ปี ด้าน Application Security / System Security
  └─ ต้องเคยทำ Penetration Testing หรือ Security Audit
  └─ เสนอหลักฐาน: CV + Security Audit Reports ตัวอย่าง (Anonymized)

ข้อ 4.6: Lead Developer / Senior Developer (Team Lead)

จำนวน: 1 คน (Full-time จนจบ Project)

ต้องมี:
- ใบประกาศนียบัตร: Optional (แต่ต้องมี Technical Skills)
  └─ ประสบการณ์แทนที่ได้ Certifications
  
- ประสบการณ์: ≥ 5-7 ปี ด้าน Software Development
  └─ ต้องเคยเป็น Lead Developer ใน min 3 Projects
  └─ ต้องมีความรู้ Tech Stack ของ Project (Python/Java/Node.js/etc)
  └─ เสนอหลักฐาน: CV + GitHub Portfolio / Source Code Examples

⚠️ สำคัญ: Key Personnel Policy
- บริษัยต้องสัญญาว่า "Key Personnel ไม่สามารถเปลี่ยนได้ระหว่าง Project"
- ถ้าต้องเปลี่ยน ต้องขออนุญาตจากผู้วางจ้าง
- Replacement ต้องมี Qualification ไม่ต่ำกว่าคนเดิม
- บริษัยต้องจ่ายค่าปรับถ้าเปลี่ยน Key Personnel โดยไม่อนุญาต
```

**E. คุณสมบัติด้านกระบวนการ/ISO (Process Qualification)**

บอกว่า "บริษัยมี Process ที่เป็นไปตามมาตรฐานหรือไม่?"

**ตัวอย่างที่ดี:**
```
ข้อ 5.1: ISO 9001 (Quality Management System)

บริษัยต้องมี ISO 9001 Certification (หรือ TQM Award เทียบเท่า)
└─ แสดงว่า บริษัยมี "Quality Control Process"
└─ มี Documentation, Testing, Process Improvement
└─ หลักฐาน: Copy ใบ ISO 9001 Certificate (ต้องยังใช้ได้)

ข้อ 5.2: ISO 27001 (Information Security Management System)

บริษัยต้องมี ISO 27001 Certification (หรือกำลังสมัคร)
└─ แสดงว่า บริษัยมี "Security Controls"
└─ มี Access Control, Encryption, Audit Logging, Incident Response
└─ หลักฐาน: Copy ใบ ISO 27001 Certificate หรือ Audit Report

ข้อ 5.3: Project Management Methodology

บริษัยต้องมี Formal Project Management Methodology
└─ เช่น: Agile, Waterfall, Hybrid, Scrum, Kanban (เลือกอันไหนก็ได้)
└─ ต้องมี Process Document ที่อธิบาย: Planning, Execution, Monitoring, Closing
└─ หลักฐาน: Copy Process Document / Methodology Guide

ข้อ 5.4: Change Management Process

บริษัยต้องมี Change Management Process ที่เป็นทางการ
└─ เมื่อ Scope เปลี่ยน/เพิ่ม ต้องผ่าน Change Request Process
└─ ต้องมี Change Board/Committee ที่ Review & Approve
└─ หลักฐาน: Copy Change Management Procedure Document

ข้อ 5.5: Risk Management Process

บริษัยต้องมี Risk Management Process
└─ Identify Risks, Assess Impact, Plan Mitigation, Monitor
└─ หลักฐาน: Copy Risk Management Procedure + ตัวอย่าง Risk Register
```

**F. คุณสมบัติพิเศษ (Special Requirements) - ถ้ามี**

อื่นๆที่ต้องสำเร็จ

**ตัวอย่างที่ดี:**
```
ข้อ 6.1: สำหรับ Consulting Services (ถ้า TOR มี Consulting)

บริษัยต้อง:
- ลงทะเบียนสำนักที่ปรึกษา (Consultant Registration)
  └─ ตาม พระราชบัญญัติ จัดซื้อจัดจ้างฯ พ.ศ. 2560
  └─ หลักฐาน: Copy Consultant Registration Certificate
  
- มีระดับ ก (Grade A) หรือ ข (Grade B)
  └─ ขึ้นอยู่กับความเชี่ยวชาญ
  └─ หลักฐาน: Copy Consultant Grade Certificate

ข้อ 6.2: สำหรับ Software Licensing (ถ้า Project ต้อง License)

ถ้า Project ใช้ Commercial Software (ไม่ใช่ Open Source):
- บริษัยต้องเป็น Authorized Partner/Reseller ของ Software Vendor
- มี OEM License Agreement ที่ยังใช้ได้
- มีสิทธิ Distribute/Resell ตามสัญญา
- หลักฐาน: Copy OEM Authorization Letter + License Agreement

ข้อ 6.3: สำหรับ Cloud Infrastructure (ถ้า Project ใช้ Cloud)

บริษัยต้อง:
- เป็น Certified Partner ของ Cloud Provider (AWS/Azure/GCP)
  └─ ตัวอย่าง: AWS Advanced Consulting Partner, Azure Expert MSP
  └─ หลักฐาน: Copy Partner Status Certificate
  
- มี Track Record การ Deploy บน Cloud Platform
  └─ min 2-3 Production Projects บน Cloud
  └─ หลักฐาน: Case Studies / Reference Letters

ข้อ 6.4: สำหรับ Data Protection (GDPR/PDPA Compliance)

ถ้า Project จัดการข้อมูลส่วนบุคคล:
- บริษัยต้องมี Data Protection Officer (DPO) หรือ PDPA Compliance Officer
- มี Data Handling Process ที่ Compliant
- เคยผ่าน Data Protection Audit
- หลักฐาน: Copy Certification / Audit Report
```

---

### ⭐ ส่วนที่ 4: ขอบเขตการจ้าง (Scope of Work) - 2000-3000 คำ ⭐ ยากสุด

#### **4.1 ความสำคัญและคำอธิบายทั่วไป**

ส่วนนี้เป็น "หัวใจ" ของ TOR เพราะ:
- **ยาว** (2000-3000 คำ ≈ 6-10 หน้า)
- **ซับซ้อน** (14 subsections ต่างโครงสร้าง)
- **รายละเอียด** (ต้องเจาะจงทุกด้าน)
- **ความเสี่ยง** (ถ้าไม่ละเอียด → Bidders จะไม่เข้าใจ → ปัญหาระหว่างทำงาน)

Section 4 ตอบคำถาม: **"ต้องทำอะไรบ้าง? ต้องใช้อะไร? ต้องให้อะไร?"**

#### **4.2 โครงสร้าง 14 Subsections**

```
4.0 Introduction (สั้นๆ บอกว่า Section 4 ทำอะไร)
4.1 Summary of Scope (สรุปวัตถุประสงค์ 100-200 คำ)
4.2 As-Is System Description (ระบบเดิมเป็นยังไง)
4.3 Main Tasks & Activities (งานหลัก ต้องทำอะไร)
4.4 Hardware Requirements & Inventory (ต้องใช้ Hardware อะไร)
4.5 Software & Licenses (ต้องใช้ Software อะไร)
4.6 Integration Points (ต้องเชื่อมต่อกับระบบอื่นไหม)
4.7 Reference Designs / Standards (ให้ดูตัวอย่างอะไร)
4.8 Deliverables (ต้องให้ผลลัพธ์อะไร)
4.9 Support & Maintenance Duration (Support นานเท่าไหร่)
4.10 Personnel & Team Requirements (ต้องมี Staff กี่คน)
4.11 Maintenance Model (บำรุงรักษาแบบไหน)
4.12 Operations & Management (ใช้งานแบบไหน)
4.13 Contingency & Disaster Recovery (ถ้าเกิดปัญหา ยังไง)
4.14 Security Requirements (ต้องปลอดภัยยังไง)
```

#### **4.3 รายละเอียดแต่ละ Subsection**

**4.1 สรุปวัตถุประสงค์ (100-200 คำ)**

สรุปสั้นว่า Section 4 ทำอะไร (ช่วยให้ Bidders เข้าใจภาพรวม)

**ตัวอย่างที่ดี:**
```
"ขอบเขตการจ้างนี้มีจุดมุ่งหมายเพื่อปรับปรุง บำรุงรักษา และอัปเกรด
ระบบ e-Payment ของกระทรวงสรรพากรให้มีความสามารถในการ:

(1) รองรับจำนวนผู้ใช้ที่เพิ่มขึ้นจาก 100-200 users ปัจจุบันเป็น 
    500 concurrent users

(2) ปรับปรุงประสิทธิภาพ โดยลด Response Time จากเดิม 5-10 วินาที 
    เป็น < 2 วินาที

(3) เพิ่มมาตรฐานความปลอดภัยให้เป็นไปตามมาตรฐาน ISO 27001

(4) ฝึกอบรมบุคลากรภายในให้สามารถจัดการ ดูแล และบำรุงรักษา
    ระบบได้เอง

โดยท้ายสุด ต้องให้ระบบพร้อมใช้งาน (Go-Live) ภายในระยะเวลา 12 เดือน
พร้อมการสนับสนุนตั้งแต่ Go-Live จนสิ้นสุดโครงการ"
```

**4.2 ลักษณะของระบบที่มีอยู่เดิม (As-Is System Description) - 300-400 คำ**

บอกว่า "ตอนนี้ระบบเป็นยังไง?" ให้ละเอียด เพราะ Bidder ต้องเข้าใจ

**ตัวอย่างที่ดี:**
```
4.2.1 System Architecture (สถาปัตยกรรมระบบ)

ระบบ e-Payment ปัจจุบันมีสถาปัตยกรรมแบบ Monolithic ดังนี้:

Infrastructure:
└─ Web Server: 1 unit Lenovo Xeon (4-core, 16GB RAM)
└─ Database Server: 1 unit Dell PowerEdge (8-core, 32GB RAM)
└─ File Server: 1 unit HP ProLiant (Network Attached Storage, 100TB)
└─ Firewall: 1 unit Palo Alto Networks PA-2000
└─ Switch: 2 units Cisco Catalyst 2960

Software Stack:
└─ OS: Windows Server 2016 (Support soonจะหมดแล้ว)
└─ Web Server: IIS 10
└─ Database: SQL Server 2012 (Version เก่า, Security Issues มี)
└─ Application Framework: .NET Framework 4.5
└─ Authentication: Username/Password (ไม่มี MFA)

Network:
└─ Connection: 100 Mbps (ช้าเกินสำหรับจำนวน Users ปัจจุบัน)
└─ No redundancy (ถ้า Network down → System down ทั้งหมด)
└─ No load balancing (ไม่สามารถ Scale)

Backup & Recovery:
└─ Backup: Manual, ทำทุกสัปดาห์ (เสี่ยงสูง)
└─ Recovery: Estimated 24-48 hours (ช้า)
└─ No DR site (ไม่มี Backup Location)

4.2.2 Applications & Modules (โปรแกรมย่อยที่มี)

ระบบประกอบด้วย 3 Applications หลัก:

1) Payment Processing Module (ส่วนสำคัญที่สุด)
   └─ Handle: Transaction Processing, Payment Gateway Integration
   └─ Current Issue: ช้า, ไม่ Support Payment Methods ใหม่ (Mobile Wallet)
   └─ User Count: 100-150 internal users

2) Reporting Portal (สำหรับ Reporting/Analytics)
   └─ Handle: Generate Reports, Analytics, Dashboard
   └─ Current Issue: Data ล่าช้า (T+2, ไม่ Real-time), Limited Reports
   └─ User Count: 30-50 management users

3) Admin Portal (สำหรับ Administration)
   └─ Handle: User Management, System Configuration, Log Viewing
   └─ Current Issue: Limited Function, ไม่ Support Multi-level Approval
   └─ User Count: 20-30 admin users

4.2.3 Performance & Issues (ปัญหาและสถิติปัจจุบัน)

Performance Metrics:
└─ Average Response Time: 5-10 seconds (Target: < 2 seconds)
└─ System Uptime: 95% (Target: 99.9%)
└─ Average Downtime: 7 days per month (ลด 100%)
└─ Transaction Success Rate: 98% (Target: 99.5%)
└─ Peak Concurrent Users: 100 (Target: 500)
└─ Database Size: 500 GB, Growing 150% per year

Issues Identified:
└─ High CPU Usage: ระหว่าง 10:00-14:00 น. (Peak time) CPU > 90%
└─ Memory Leak: ทุก 5-7 วัน ต้อง Restart Server
└─ Slow Queries: บาง SQL Queries ใช้เวลา > 30 seconds
└─ No Monitoring: ไม่มี Real-time Monitoring Tool, ทรายได้หลัง
└─ Limited Scalability: Database Indexes ไม่ optimize, ไม่มี Clustering

4.2.4 Known Limitations (ข้อจำกัดที่รู้อยู่แล้ว)

└─ Not Support Mobile: ไม่มี Mobile App (ลูกค้าต้องใช้ Desktop)
└─ Not Support Multiple Payment Methods: Support เพียง Bank Transfer
└─ Not Support Multi-currency: Support THB only
└─ No API: ไม่มี API สำหรับ Third-party Integration
└─ No Audit Trail: ไม่ Record ทุก Transaction Detail (Compliance Risk)
└─ No Encryption: Data transmitted in Plain Text (Security Risk)
```

**4.3 งานหลักและกิจกรรม (Main Tasks & Activities) - 400-500 คำ**

จดรายการ Tasks ที่ต้องทำ พร้อมระยะเวลา (เพื่อ Bidder จะรู้ว่าต้องทำอะไร)

**ตัวอย่างที่ดี:**
```
ผู้รับจ้างต้องดำเนินการตามงานหลักต่อไปนี้:

Task 1: System Analysis & Requirements Refinement (30 days)
└─ Activity 1.1: Conduct Detailed System Analysis
    ├─ Interview Stakeholders & Users
    ├─ Document Current System in Detail
    ├─ Identify Performance Bottlenecks
    └─ Deliverable: Detailed System Analysis Report (20 pages)

└─ Activity 1.2: Refine & Prioritize Requirements
    ├─ Gather Detailed Requirements from Users
    ├─ Organize by Functional/Non-Functional/Technical
    ├─ Create Requirements Traceability Matrix
    └─ Deliverable: Requirements Specification Document (30 pages)

└─ Activity 1.3: Risk Assessment
    ├─ Identify Project Risks
    ├─ Assess Impact & Probability
    ├─ Create Risk Mitigation Plan
    └─ Deliverable: Risk Register & Mitigation Plan (15 pages)

Estimated Effort: 400 man-hours
Timeline: Week 1-4 (Day 1-30 of Project)
Key Deliverable: Approved Requirements Document


Task 2: System Design & Architecture (45 days)
└─ Activity 2.1: System Architecture Design
    ├─ Design High-level System Architecture (Microservices vs Monolithic)
    ├─ Design Components & Modules
    ├─ Design Integration Points
    └─ Deliverable: System Architecture Document with Diagrams (25 pages)

└─ Activity 2.2: Database Design
    ├─ Design Database Schema
    ├─ Normalize Tables
    ├─ Plan Indexes & Performance Tuning
    └─ Deliverable: ER Diagram + Database Design Document (20 pages)

└─ Activity 2.3: Security & Infrastructure Design
    ├─ Design Security Controls (Encryption, Auth, etc.)
    ├─ Design Infrastructure (Servers, Network, Firewalls)
    ├─ Design Disaster Recovery Architecture
    └─ Deliverable: Security Design & Infrastructure Design (20 pages)

└─ Activity 2.4: Design Review & Approval
    ├─ Technical Review Meeting with Stakeholders
    ├─ Incorporate Feedback
    └─ Deliverable: Approved Design Documents

Estimated Effort: 600 man-hours
Timeline: Week 5-10 (Day 31-75 of Project)
Key Deliverable: Approved Technical Design


Task 3: Infrastructure Setup & Development Environment (30 days)
└─ Procure Hardware (Servers, Storage, Network)
└─ Install OS & Database
└─ Configure Network & Firewall
└─ Setup Development & Test Environments
└─ Configure Monitoring Tools

Estimated Effort: 250 man-hours
Timeline: Week 5-10 (Parallel with Design)


Task 4: Application Development (90 days)
└─ Develop Payment Processing Module (40 days)
└─ Develop Reporting Module (25 days)
└─ Develop Admin Portal (25 days)
└─ API Development for Integration (20 days)

Estimated Effort: 1200 man-hours
Timeline: Week 11-27 (Day 76-180 of Project)
Key Deliverable: Working Applications ready for Testing


Task 5: System Testing & Quality Assurance (35 days)
└─ Unit Testing (Developer)
└─ Integration Testing
└─ System Testing
└─ User Acceptance Testing (UAT)
└─ Performance & Load Testing
└─ Security Testing (Penetration Test)

Estimated Effort: 400 man-hours
Timeline: Week 24-30 (Day 165-210 of Project)
Key Deliverable: Test Report + Defect Log + Approved UAT Results


Task 6: Training & Documentation (20 days)
└─ Write User Manual (in Thai & English)
└─ Write System Administrator Guide
└─ Write API Documentation
└─ Conduct Training Sessions (5 days)
└─ Prepare Training Materials & Handouts

Estimated Effort: 200 man-hours
Timeline: Week 26-30 (Day 180-210 of Project)
Key Deliverable: Complete Documentation + Training Certificates


Task 7: Go-Live & Support (60 days)
└─ Data Migration from Old System
└─ Parallel Run (Old & New System Running Together)
└─ Final Testing & Sign-Off
└─ Go-Live Execution
└─ 24/7 On-site Support (30 days)
└─ On-call Support (30 days)

Estimated Effort: 500 man-hours
Timeline: Week 29-42 (Day 195-360 of Project)
Key Deliverable: System Live & Stabilized, Support Handover


TOTAL PROJECT EFFORT: ~3550 man-hours
TOTAL PROJECT DURATION: 52 weeks (12 months, approximately 1 year)
```

**4.4 Hardware Requirements & Current Inventory - 300-400 คำ**

**ตัวอย่างที่ดี:**
```
ผู้รับจ้างต้องใช้ Hardware ตามที่ระบุด้านล่าง เพื่อให้ Project สำเร็จ:

SECTION A: SERVERS (Production Environment)

Web/Application Servers:
└─ Qty: 2 units (Redundancy/Load Balance)
└─ Spec:
   ├─ Brand/Model: Dell PowerEdge R750 (2U Rack Server)
   ├─ Processor: 2x Intel Xeon Gold 6348 (28-core, 3.3 GHz)
   ├─ Memory: 256 GB RAM (DDR4-3200)
   ├─ Storage: 2x 1.2 TB 10K RPM SAS Drives (Mirrored)
   ├─ Network: 2x 25 Gbps Network Interface Cards
   └─ Power: Redundant Power Supplies (N+1)

Database Servers:
└─ Qty: 2 units (Primary + Hot Standby)
└─ Spec:
   ├─ Brand/Model: HP ProLiant DL560 Gen10 Plus
   ├─ Processor: 4x Intel Xeon Platinum 8380 (28-core each)
   ├─ Memory: 512 GB RAM
   ├─ Storage: 8x 2.4 TB 15K RPM SAS Drives (RAID 10)
   ├─ Network: 2x 25 Gbps NIC
   └─ Power: Redundant PSU

File/Storage Servers:
└─ Qty: 2 units (Active-Active)
└─ Spec:
   ├─ Brand/Model: NetApp AFF A900 (Flash Storage Array)
   ├─ Capacity: 80 TB Usable (with Redundancy)
   ├─ Network: 10 Gbps (FC/Ethernet)
   └─ Replication: Synchronous to Secondary Site

SECTION B: NETWORKING EQUIPMENT

Core Network Switch:
└─ Qty: 2 units (Redundancy)
└─ Spec:
   ├─ Brand/Model: Cisco Nexus 9372PX
   ├─ Ports: 54 x 10/25/40/100 Gbps Ports
   ├─ Throughput: 25.6 Tbps
   └─ Features: VLANs, ACLs, QoS

Firewall/Security Appliances:
└─ Qty: 2 units (Active-Active)
└─ Spec:
   ├─ Brand/Model: Palo Alto Networks PA-5220
   ├─ Throughput: 100 Gbps
   ├─ Features: IPS, Anti-malware, Application Control
   └─ Management: Centralized via Panorama

SECTION C: BACKUP & DISASTER RECOVERY

Backup Appliance:
└─ Qty: 1 unit (Local Backup)
└─ Spec:
   ├─ Brand/Model: Commvault MediaAgent with Disk Storage
   ├─ Capacity: 50 TB
   ├─ Backup Window: Daily Full (Sunday), Daily Incremental (Mon-Sat)
   └─ Retention: 30 days Local, 90 days Archive

DR Site Equipment:
└─ Secondary Data Center (20 km away)
└─ Equipment: Mirror of Production Environment
└─ Replication: Real-time Synchronous Replication
└─ RTO (Recovery Time Objective): 4 hours
└─ RPO (Recovery Point Objective): 1 hour

SECTION D: MONITORING & MANAGEMENT TOOLS (Software-based, covered in Section 4.5)

SECTION E: EXISTING HARDWARE (To be Re-used or Decomissioned)

Current Hardware to be Decommissioned:
└─ Lenovo Xeon Server (5 years old) - To be Retired & Donated
└─ Dell PowerEdge (4 years old) - To be Recycled
└─ Cisco Switches (3x, 6 years old) - To be Retired or Sold

SUMMARY: Bill of Materials (BoM)

| Component | Current | New | Action |
|-----------|---------|-----|--------|
| App Servers | 1 | 2 | Add 1 more |
| DB Servers | 1 | 2 | Add 1 more + Upgrade |
| Storage | 100 TB | 80 TB Usable | Replace with SAN |
| Network Bandwidth | 100 Mbps | 10+ Gbps | Upgrade 100x |
| Backup | Manual | Automated | Implement Tool |
```

**4.5 Software & Licenses - 300-400 คำ**

**ตัวอย่างที่ดี:**
```
ผู้รับจ้างต้องใช้ Software ตามต่อไปนี้:

SECTION A: OPERATING SYSTEM (OS)

Primary OS:
└─ Product: Ubuntu Linux 22.04 LTS (Long-Term Support)
└─ Qty: 8 licenses (4 Web Servers, 2 DB Servers, 2 File Servers)
└─ Cost: FREE (Open Source)
└─ Support: Canonical (5 years standard + 5 years extended)
└─ Notes: Better Security Updates, Community Support

Database OS (Windows) - if needed:
└─ Product: Windows Server 2022 Standard
└─ Qty: 2 licenses (DB Servers)
└─ Cost: ~$1,800 per license (~3,600 total)
└─ Note: Opsional, preferred Ubuntu

SECTION B: DATABASE MANAGEMENT SYSTEM

Primary Database:
└─ Product: PostgreSQL 14 (Open Source)
└─ Qty: 2 installations (Production + Standby)
└─ Cost: FREE
└─ Support: Community + Optional Commercial Support (EDB)
└─ Alternative: Oracle Database 21c (Licensed, Cost Included in Project Budget)

Cache Layer:
└─ Product: Redis 6.2 (Open Source)
└─ Qty: 2 instances (Primary + Replica)
└─ Cost: FREE
└─ Purpose: Session Storage, Caching Layer

SECTION C: APPLICATION DEVELOPMENT & RUNTIME

Backend Framework:
└─ Product: Java OpenJDK 17 LTS
└─ Qty: Unlimited (Open Source)
└─ Cost: FREE
└─ Runtime: Apache Tomcat 10 (Open Source, FREE)

Alternative (If Python):
└─ Product: Python 3.10 + FastAPI Framework
└─ Cost: FREE (Open Source)

Frontend Framework:
└─ Product: React.js 18 + Node.js 18 LTS
└─ Cost: FREE (Open Source)

SECTION D: MIDDLEWARE & INTEGRATION

API Management:
└─ Product: Kong API Gateway (Open Source Version)
└─ Cost: FREE
└─ Alternative: AWS API Gateway (Usage-based, Included in AWS Budget)

Message Queue:
└─ Product: RabbitMQ (Open Source)
└─ Cost: FREE
└─ Purpose: Asynchronous Processing, Event-driven Architecture

Service Bus (if Cloud):
└─ Product: AWS SQS / Azure Service Bus
└─ Cost: Usage-based (Included in Cloud Budget)

SECTION E: MONITORING & LOGGING

Monitoring Tools:
└─ Prometheus + Grafana (Open Source, FREE)
└─ Features: Metrics Collection, Dashboard, Alerting
└─ Alternative: DataDog (Paid, ~$15-40/month per host)

Logging & Analytics:
└─ ELK Stack (Elasticsearch + Logstash + Kibana)
└─ Cost: FREE (Open Source)
└─ Storage: ~1 TB for logs per month

SECTION F: SECURITY & COMPLIANCE

Web Application Firewall:
└─ Product: Cloudflare WAF (or AWS WAF)
└─ Cost: Included in Cloud Budget

VPN & Access Control:
└─ Product: OpenVPN (Open Source)
└─ Cost: FREE

SSL/TLS Certificates:
└─ Product: Let's Encrypt (FREE) or DigiCert (Paid, ~$200-500/year)
└─ Duration: 1 year (Renewable)

SECTION G: DEVELOPMENT TOOLS

Version Control:
└─ Product: GitLab Community Edition (Self-hosted)
└─ Cost: FREE
└─ Alternative: GitHub (FREE for Public, $21/month for Private)

CI/CD Platform:
└─ Product: GitLab CI/CD (included) or Jenkins (Open Source, FREE)
└─ Cost: FREE

Project Management:
└─ Product: Jira Server (Self-hosted)
└─ Cost: Perpetual License $1,200-2,000 (One-time)
└─ Alternative: Open Source (OpenProject, Taiga) - FREE

SECTION H: OFFICE & COLLABORATION

Office Suite:
└─ LibreOffice / OnlyOffice (Open Source, FREE)
└─ Alternative: Microsoft Office 365 (~$10-30/user/month)

Collaboration Platform:
└─ Mattermost (Open Source, Self-hosted) - FREE
└─ Alternative: Slack ($6.67-12.50/user/month)

SECTION I: SUMMARY TABLE

| Software | Type | Cost | License | Support |
|----------|------|------|---------|---------|
| Ubuntu | OS | FREE | GPL | Community |
| PostgreSQL | Database | FREE | POSTGRESQL | Community/EDB |
| Java/Spring | Backend | FREE | GPL/Apache | Community |
| React | Frontend | FREE | MIT | Community |
| ELK Stack | Logging | FREE | Elastic/SSPL | Community |
| Prometheus | Monitoring | FREE | Apache 2.0 | Community |
| Total 1st Year Cost | | ~$5,000-10,000 | | |
| Maintenance Cost/Year | | ~$3,000-5,000 | | |

Note: All licenses ต้องสอดคล้องกับ Open Source Policy ของกระทรวง
และต้อง Properly Licensed (ห้าม Pirated Software)
```

### **4.6 สถาบันการเงินที่เกี่ยวข้อง / Integration Points - 250-300 คำ**

**จุดประสงค์:** ระบุว่า "ระบบนี้ต้องเชื่อมต่อกับระบบอื่นอะไรบ้าง"

**ตัวอย่างที่ดี:**

```
4.6 จุดเชื่อมต่อและการบูรณาการระบบ

ระบบ e-Payment ใหม่ต้องเชื่อมต่อและติดต่อระหว่างกับระบบอื่นต่อไปนี้:

A. OUTBOUND INTEGRATION (ระบบนี้ส่งข้อมูลไปให้ระบบอื่น)

1. Bank Payment Gateway API
   ├─ Purpose: ส่ง Payment Request ไป Bank และรับ Status
   ├─ Connection: Real-time via HTTPS API
   ├─ Frequency: Per transaction (1,000+ times/day)
   ├─ Data Format: JSON/XML (ตัวอย่าง: {"amount": 1000, "ref": "ORD001"})
   ├─ SLA: Response < 5 seconds
   ├─ Responsibility: ผู้รับจ้างต้อง Handle retry & error cases
   └─ Example Banks: Kasikornbank, Siam Commercial Bank, Bangkok Bank

2. Ministry of Commerce Online System
   ├─ Purpose: Send Daily Settlement Report
   ├─ Connection: File transfer (SFTP) or API
   ├─ Frequency: Daily at 10:00 PM
   ├─ Data: CSV/XML with transaction summary
   ├─ Validation: Checksum for data integrity
   └─ Contact: MOC IT Department

3. Treasury System
   ├─ Purpose: Send Fund Transfer Instructions
   ├─ Connection: Direct Database Link (Private Network)
   ├─ Frequency: Daily after transaction cut-off
   ├─ Data: Account number, amount, reference
   └─ SLA: Delivery by 6:00 AM next day

4. Email Server (Internal)
   ├─ Purpose: Send Transaction Notification to Users/Customers
   ├─ Connection: SMTP over TLS
   ├─ Frequency: Per transaction
   ├─ Data: HTML email with transaction details
   ├─ DKIM/SPF: Must be configured
   └─ Rate Limit: 10,000 emails/hour

B. INBOUND INTEGRATION (ระบบอื่นส่งข้อมูลมาให้ระบบนี้)

1. Government Tax Database
   ├─ Purpose: Query Tax Information for validation
   ├─ Connection: HTTPS REST API
   ├─ Frequency: Per transaction (Optional, for validation)
   ├─ Data Format: JSON
   ├─ Timeout: 2 seconds (if timeout, continue without validation)
   └─ Fallback: Continue transaction if external system down

2. Mobile Authentication Service
   ├─ Purpose: Verify User MFA (Multi-Factor Authentication)
   ├─ Connection: Web Service over HTTPS
   ├─ Frequency: Per login
   ├─ Response Time: < 1 second
   └─ Support: 24/7

3. Reporting Portal
   ├─ Purpose: Query Transaction Data for Reports
   ├─ Connection: Read-only database access
   ├─ Frequency: Ad-hoc queries
   ├─ Data Lag: Must be < 1 hour (near real-time)
   └─ Performance: Query response < 10 seconds

C. BIDIRECTIONAL INTEGRATION

1. Data Warehouse / Analytics Platform
   ├─ Purpose: Send transaction data for analytics, Receive insights
   ├─ Connection: Direct database sync or ETL pipeline
   ├─ Frequency: Real-time or batch (nightly)
   ├─ Data: All transactions with full details
   ├─ Format: JSON or CSV
   └─ Retention: 7 years (regulatory requirement)

D. INTEGRATION REQUIREMENTS FOR VENDOR

ผู้รับจ้างต้อง:
├─ Develop API adapters สำหรับแต่ละ integration point
├─ Implement error handling & retry logic
├─ Document API specifications (10 pages minimum)
├─ Conduct integration testing with each external system
├─ Maintain 99.9% integration uptime
├─ Provide integration support 24/7 for 6 months
└─ Create integration troubleshooting guide

E. DATA SECURITY FOR INTEGRATIONS

├─ All APIs must use HTTPS/TLS 1.2+
├─ API Authentication: OAuth 2.0 or API Key
├─ Data encryption: AES-256 for sensitive data
├─ API rate limiting: Implement to prevent abuse
├─ Logging: All API calls must be logged (for audit)
└─ Monitoring: Real-time monitoring of integration health

DELIVERABLE RELATED TO SECTION 4.6:
└─ Integration Architecture Document (15-20 pages)
   ├─ Diagram: Data flow between systems
   ├─ API Specifications: For each integration
   ├─ Error handling procedures
   └─ Testing & validation criteria
```

---

### **4.7 ตัวอย่างของระบบที่พัฒนาหรือคล้ายกัน / Reference Designs - 200-250 คำ**

**จุดประสงค์:** ให้ Bidders ดูตัวอย่างระบบที่เหมือน/คล้ายกัน เพื่อให้เข้าใจสิ่งที่ต้องการ

**ตัวอย่างที่ดี:**

```
4.7 ตัวอย่างและสถาปัตยกรรมอ้างอิง

เพื่อให้ผู้รับจ้างเข้าใจว่าระบบ e-Payment ใหม่ควรมีลักษณะอย่างไร
กระทรวงได้จัดเตรียมตัวอย่างอ้างอิงต่อไปนี้:

A. REFERENCE SYSTEMS (ระบบที่คล้ายกัน ที่เคยสำเร็จแล้ว)

1. Bank of Thailand Online Payment System
   ├─ Link: www.bot.or.th/payment-system (Public Demo)
   ├─ Features to observe:
   │  ├─ User Interface (Desktop & Mobile)
   │  ├─ Payment flow (how users make payments)
   │  ├─ Error handling (what happens when transaction fails)
   │  ├─ Confirmation screen (how results are shown)
   │  └─ Receipt/Email notification
   ├─ Architecture: Can request from BoT (Contact: CIO Office)
   └─ Performance: Check response time (target < 2 seconds)

2. Thailand Revenue Department Tax Payment Portal
   ├─ Link: www.rd.go.th/tax-payment (Live System)
   ├─ Features to study:
   │  ├─ Multiple payment methods (Bank, Credit Card, e-Wallet)
   │  ├─ Security (MFA, SSL, Encryption)
   │  ├─ Mobile app interface
   │  ├─ Reporting dashboard
   │  └─ Integration with Thai banks
   ├─ Available: Request demo account from Revenue Dept
   └─ Note: This is an ACTUAL SYSTEM that works well

3. Stock Exchange of Thailand (SET) Payment System
   ├─ Link: www.set.or.th/investor-services
   ├─ Focus on: High-volume transaction handling
   ├─ Study: How they handle peak traffic (market opening hours)
   ├─ Security: How they protect trader information
   └─ Available: Request case study from SET

B. REFERENCE ARCHITECTURE DOCUMENTS

1. Cloud Native Payment System Architecture
   ├─ Document: "Microservices Architecture for Financial Systems" (Public)
   ├─ Download: Available on AWS/Azure/GCP whitepapers
   ├─ Key sections to study:
   │  ├─ API Gateway design
   │  ├─ Microservices breakdown
   │  ├─ Database design (NoSQL vs RDBMS)
   │  ├─ Caching strategy
   │  ├─ Message queue implementation
   │  └─ Security controls
   └─ Reference: Open Standards (OWASP, PCI-DSS, ISO 27001)

2. High-Performance Payment Processing
   ├─ Technology: Stripe, Square, 2Checkout architecture
   ├─ Study: How they achieve < 1 second response time
   ├─ Note: Public case studies available
   └─ Key: Load balancing, caching, database optimization

C. UI/UX REFERENCE DESIGNS

Vendor ต้อง:
├─ Study modern payment UI (e.g., PayPal, Google Pay, Apple Pay)
├─ Use Thai language throughout
├─ Support Thai keyboard & number input
├─ Implement Thai date format (Buddhist Era)
├─ Test on both web & mobile browsers
└─ Design should be accessible to users with disabilities (WCAG 2.1)

D. SECURITY STANDARDS & FRAMEWORKS

Vendor ต้อง:
├─ Follow PCI-DSS (Payment Card Industry Data Security Standard)
├─ Implement OWASP Top 10 protections
├─ Use Thai Government IT Security Standards
├─ Reference: ISO 27001 certification requirements
├─ Penetration testing standards: OWASP Testing Guide
└─ Compliance: Thai Data Protection Act (PDPA)

E. DELIVERABLES RELATED TO SECTION 4.7

Vendor ต้องจัดเตรียม:
├─ System Architecture Diagram (similar to reference systems)
├─ UI/UX Mockup Screenshots (showing payment flow)
├─ Security Architecture Diagram (showing how data is protected)
├─ Performance Benchmark (comparing to reference systems)
└─ Compliance Checklist (showing PCI-DSS, ISO 27001, etc.)

NOTES FOR EVALUATORS:
└─ Use reference systems as comparison point
├─ If vendor's proposal is worse than reference → Red flag
├─ If vendor's proposal is similar to reference → Good
└─ If vendor's proposal is better than reference → Excellent
```

---

### **4.8 ผลิตภัณฑ์ที่จะส่งมอบ / Deliverables - 400-500 คำ (ยาวที่สุด)**

**นี่คือส่วนที่สำคัญที่สุด เพราะ Bidders ต้องรู้ว่าต้อง "ให้" อะไร**

**ตัวอย่างที่ดี:**

```
4.8 ผลิตภัณฑ์และผลงานที่ต้องส่งมอบ

ผู้รับจ้างต้องส่งมอบผลิตภัณฑ์ต่อไปนี้ตามกำหนดเวลา:

═══════════════════════════════════════════════════════════════
PHASE 1: ANALYSIS & DESIGN (Month 0-2.5, By Nov 30, 2569)
═══════════════════════════════════════════════════════════════

DELIVERABLE 1.1: System Analysis Report
├─ Length: 30-40 pages
├─ Content:
│  ├─ Executive summary (2 pages)
│  ├─ Current system analysis (5 pages)
│  ├─ Problems & root causes (5 pages)
│  ├─ Industry best practices (5 pages)
│  ├─ Technology recommendations (5 pages)
│  ├─ Risk assessment (5 pages)
│  └─ Appendices (diagrams, references)
├─ Format: Microsoft Word (.docx) + PDF
├─ Language: Thai & English
├─ Approval: Must be signed off by IT Manager & Sponsor
└─ Delivery: By Nov 15, 2569

DELIVERABLE 1.2: Requirements Specification Document
├─ Length: 40-50 pages
├─ Content:
│  ├─ Functional requirements (15 pages)
│  │  └─ Each requirement must have:
│  │     ├─ ID (REQ-F-001, etc.)
│  │     ├─ Description (1-2 paragraphs)
│  │     ├─ Priority (HIGH, MEDIUM, LOW)
│  │     └─ Acceptance criteria (measurable)
│  ├─ Non-functional requirements (10 pages)
│  │  └─ Performance, security, scalability, etc.
│  ├─ Operational requirements (5 pages)
│  │  └─ Maintenance, support, monitoring
│  ├─ Constraints & assumptions (5 pages)
│  ├─ Use case diagrams (5 pages)
│  └─ Glossary & acronyms
├─ Format: Visio diagrams + Word document
├─ Approval: Stakeholder sign-off
└─ Delivery: By Nov 15, 2569

DELIVERABLE 1.3: System Architecture Design Document
├─ Length: 25-30 pages
├─ Must include:
│  ├─ High-level system architecture diagram
│  │  └─ Show: Components, interfaces, technologies
│  ├─ Technology stack justification
│  │  └─ Why Java? Why PostgreSQL? Why Cloud?
│  ├─ Deployment diagram
│  │  └─ Show: Servers, network, load balancers
│  ├─ Microservices breakdown (if applicable)
│  │  └─ Each service: Purpose, API, dependencies
│  ├─ Scalability approach
│  │  └─ How to scale from 100 to 500 users
│  ├─ Performance strategy
│  │  └─ Caching, database optimization, CDN
│  └─ Technology decisions & trade-offs
├─ Format: Lucidchart/Visio diagrams + Word
├─ Approval: Architecture Review Board
└─ Delivery: By Dec 15, 2569

DELIVERABLE 1.4: Database Design & Schema Document
├─ Length: 20-25 pages
├─ Must include:
│  ├─ Entity-Relationship (ER) Diagram
│  │  └─ All tables, fields, relationships
│  ├─ Normalization explanation
│  │  └─ Why normalized to 3NF?
│  ├─ Indexes strategy
│  │  └─ Which fields indexed? Why?
│  ├─ Data retention policy
│  │  └─ How long to keep old data?
│  ├─ Backup strategy
│  │  └─ Daily full? Incremental?
│  ├─ SQL scripts
│  │  └─ CREATE TABLE statements (for all tables)
│  └─ Data dictionary
│     └─ Describe each field (type, size, constraint)
├─ Format: Visio/ERDPlus + SQL scripts + Word
├─ Delivery: By Dec 15, 2569
└─ Note: Must support 500 concurrent users

DELIVERABLE 1.5: Security Architecture Document
├─ Length: 20-25 pages
├─ Must cover:
│  ├─ Authentication & Authorization
│  │  └─ How to prove "you are who you say"?
│  │  └─ What can each user do?
│  ├─ Encryption strategy
│  │  └─ Data at rest (AES-256)
│  │  └─ Data in transit (TLS 1.2+)
│  ├─ Network security
│  │  └─ Firewall rules, DDoS protection
│  ├─ Application security
│  │  └─ SQL injection prevention, XSS prevention
│  ├─ Compliance controls
│  │  └─ ISO 27001, PCI-DSS, OWASP Top 10
│  ├─ Disaster recovery
│  │  └─ Backup & restore procedures
│  ├─ Incident response
│  │  └─ What if system is hacked?
│  └─ Security testing plan
│     └─ Penetration test, vulnerability scan
├─ Format: Word + Diagrams
├─ Approval: Security Officer
└─ Delivery: By Dec 15, 2569

DELIVERABLE 1.6: Project Plan & Schedule
├─ Length: 10-15 pages
├─ Must include:
│  ├─ Work breakdown structure (WBS)
│  │  └─ All tasks and sub-tasks
│  ├─ Gantt chart
│  │  └─ Timeline for all phases
│  ├─ Resource plan
│  │  └─ Who does what? (Team structure)
│  ├─ Risk register
│  │  └─ Known risks & mitigation
│  ├─ Communication plan
│  │  └─ How to update Sponsor?
│  ├─ Quality assurance plan
│  │  └─ How to ensure quality?
│  └─ Approval process
│     └─ Who signs off at each milestone?
├─ Format: MS Project / Excel + Word
└─ Delivery: By Dec 15, 2569

═══════════════════════════════════════════════════════════════
PHASE 2: DEVELOPMENT (Month 3-7, By May 15, 2570)
═══════════════════════════════════════════════════════════════

DELIVERABLE 2.1: Source Code
├─ Location: Git Repository (GitLab/GitHub)
├─ Must include:
│  ├─ Backend code (100% tested)
│  │  ├─ Java/Spring Boot or Python/FastAPI
│  │  ├─ RESTful APIs for all features
│  │  ├─ Unit tests (≥80% code coverage)
│  │  └─ Integration tests
│  ├─ Frontend code (React)
│  │  ├─ Web interface (Desktop)
│  │  ├─ Mobile interface (iOS/Android compatible)
│  │  ├─ Component library
│  │  └─ Unit tests for components
│  ├─ Database scripts
│  │  ├─ Schema creation (DDL)
│  │  ├─ Stored procedures
│  │  └─ Data migration scripts
│  ├─ Infrastructure as Code
│  │  ├─ Terraform/CloudFormation scripts
│  │  ├─ Docker images (if containerized)
│  │  └─ Kubernetes manifests (if using K8s)
│  └─ CI/CD pipeline
│     ├─ GitLab CI/Jenkins configuration
│     ├─ Automated tests on every commit
│     └─ Automated deployment to staging
├─ Code quality:
│  ├─ Code review: Every commit must pass 2 reviewers
│  ├─ Static analysis: SonarQube score ≥ A
│  ├─ Security scan: No HIGH/CRITICAL vulnerabilities
│  └─ Performance: No memory leaks (verified by tools)
├─ Access: Read-only access for auditors/government
└─ Delivery: Continuous (Daily commits), Final by May 15

DELIVERABLE 2.2: Installation & Deployment Guide
├─ Length: 15-20 pages
├─ Step-by-step instructions for:
│  ├─ Prerequisites (Hardware, OS, Software)
│  ├─ Database setup
│  ├─ Application deployment
│  ├─ Configuration
│  ├─ Security setup (SSL, Firewall, etc.)
│  ├─ Testing verification
│  └─ Troubleshooting common issues
├─ Include: Screenshots, commands, expected output
├─ Format: Word + PDF
└─ Delivery: By May 15, 2570

DELIVERABLE 2.3: Configuration Guide
├─ Length: 10-15 pages
├─ Document all configurable parameters:
│  ├─ Database connection strings
│  ├─ Email server settings
│  ├─ Payment gateway credentials
│  ├─ Security parameters (key rotation, etc.)
│  ├─ Performance tuning parameters
│  └─ Monitoring & alerting thresholds
├─ Format: Word + Configuration templates
└─ Delivery: By May 15, 2570

DELIVERABLE 2.4: API Documentation
├─ Length: 20-25 pages (comprehensive)
├─ For EACH API endpoint:
│  ├─ Purpose (what does this API do?)
│  ├─ HTTP method (GET, POST, PUT, DELETE)
│  ├─ URL endpoint
│  ├─ Required parameters (with types)
│  ├─ Response format (JSON example)
│  ├─ Error codes (what can go wrong?)
│  ├─ Example request & response
│  └─ Rate limits (how many calls per minute?)
├─ Tools: Swagger/OpenAPI format (machine-readable)
├─ Format: HTML (auto-generated from Swagger) + PDF
└─ Delivery: By May 15, 2570

═══════════════════════════════════════════════════════════════
PHASE 3: TESTING & QA (Month 6-7, By Jun 30, 2570)
═══════════════════════════════════════════════════════════════

DELIVERABLE 3.1: Test Plan & Test Cases
├─ Test cases: 100+ test cases
├─ Coverage:
│  ├─ Functional tests (all features)
│  ├─ Regression tests (ensure old features still work)
│  ├─ Security tests (SQL injection, XSS, etc.)
│  ├─ Performance tests (load, stress)
│  ├─ Usability tests (user interface)
│  └─ Integration tests (with Bank API, etc.)
├─ Format: Excel or TestRail (test management tool)
└─ Delivery: By Jun 1, 2570

DELIVERABLE 3.2: Test Results & Defect Log
├─ Document: All bugs found and status
├─ For each defect:
│  ├─ ID, Title, Severity (Critical, High, Medium, Low)
│  ├─ Description, Steps to reproduce
│  ├─ Status (New, Open, Fixed, Verified, Closed)
│  ├─ Assigned to, Target fix date
│  └─ Comments (investigation notes)
├─ Must-have: Zero CRITICAL/HIGH defects before go-live
├─ Format: Excel or Jira
└─ Delivery: Continuous, Final by Jun 30

DELIVERABLE 3.3: User Acceptance Testing (UAT) Sign-off
├─ Conducted by: End-users (government staff)
├─ Duration: 2 weeks
├─ UAT script: 50+ test scenarios for end-users to try
├─ Sign-off: UAT Manager must approve before go-live
├─ Format: Signed document + video recording of UAT
└─ Delivery: By Jun 30, 2570

DELIVERABLE 3.4: Performance Test Results
├─ Load testing:
│  ├─ Simulate 500 concurrent users
│  ├─ Run for 2 hours
│  ├─ Verify response time < 2 seconds
│  └─ Verify error rate < 0.1%
├─ Stress testing:
│  ├─ Increase users beyond 500
│  ├─ Find breaking point
│  └─ Verify system recovers gracefully
├─ Spike testing:
│  ├─ Sudden increase in traffic
│  ├─ Verify system handles without crashing
│  └─ Response time degradation acceptable?
├─ Report: 10-15 pages with graphs & analysis
└─ Delivery: By Jun 30, 2570

DELIVERABLE 3.5: Security Audit Report
├─ Conducted by: Third-party security firm
├─ Scope:
│  ├─ Penetration testing (attempt to hack)
│  ├─ Vulnerability scanning
│  ├─ Code review for security issues
│  ├─ Compliance check (PCI-DSS, ISO 27001)
│  └─ Security controls verification
├─ Must have: ≥ ISO 27001 certification level
├─ Report: Professional 20-30 page report
└─ Delivery: By Jun 30, 2570

═══════════════════════════════════════════════════════════════
PHASE 4: TRAINING & DOCUMENTATION (Month 7-8, By Aug 31, 2570)
═══════════════════════════════════════════════════════════════

DELIVERABLE 4.1: User Manual
├─ Length: 30-40 pages
├─ Content (in Thai & English):
│  ├─ Overview of system
│  ├─ How to log in (step-by-step with screenshots)
│  ├─ How to process a payment (detailed walkthrough)
│  ├─ How to view transaction history
│  ├─ How to print receipts
│  ├─ How to resolve common issues
│  ├─ FAQs (20+ frequently asked questions)
│  └─ Contact information for support
├─ Format: Word + PDF (optimized for printing)
├─ Screenshots: 50+ labeled screenshots showing every screen
└─ Delivery: By Aug 15, 2570

DELIVERABLE 4.2: System Administrator Guide
├─ Length: 25-30 pages
├─ Content:
│  ├─ How to start/stop the system
│  ├─ How to manage users & permissions
│  ├─ How to view system logs
│  ├─ How to backup and restore data
│  ├─ How to tune performance
│  ├─ How to handle emergencies (system down)
│  ├─ Common problems & solutions
│  ├─ Security best practices
│  └─ Contacts for emergency support
├─ Format: Word + PDF
└─ Delivery: By Aug 15, 2570

DELIVERABLE 4.3: Training Materials & Presentation
├─ PowerPoint deck: 50-60 slides
├─ Content:
│  ├─ System overview (10 slides)
│  ├─ User guide walk-through (20 slides)
│  ├─ Common scenarios (15 slides)
│  ├─ Q&A section (10 slides)
│  └─ Support information (5 slides)
├─ Handouts: Printed copies for all trainees
├─ Format: PPTX + PDF
└─ Delivery: By Aug 15, 2570

DELIVERABLE 4.4: Video Tutorials
├─ Minimum: 5 videos
├─ Topics:
│  ├─ Video 1: System Login & Overview (5 min)
│  ├─ Video 2: Process a Payment (7 min)
│  ├─ Video 3: Generate Reports (5 min)
│  ├─ Video 4: Troubleshoot Common Issues (8 min)
│  └─ Video 5: Admin Tasks (7 min)
├─ Production:
│  ├─ Professional quality (HD 1080p)
│  ├─ Thai narration + English subtitles
│  ├─ Screen capture + voiceover
│  └─ Hosted on YouTube (unlisted)
├─ Format: MP4
└─ Delivery: By Aug 15, 2570

DELIVERABLE 4.5: Training Delivery & Certification
├─ Classroom training:
│  ├─ 5 days (8 hours per day)
│  ├─ Groups: Max 20 people per session
│  ├─ Venue: Government training room
│  ├─ Trainer: Certified trainer from vendor
│  └─ Schedule: To be confirmed with Sponsor
├─ Training certificate:
│  ├─ Issued to participants who pass test
│  ├─ Test: 50 questions, pass ≥70%
│  └─ Certificate: Signed by Vendor + Government
├─ Train-the-trainer:
│  ├─ Government staff trained to train others
│  ├─ 3 staff members
│  └─ Duration: 2 days
└─ Delivery: By Aug 31, 2570

═══════════════════════════════════════════════════════════════
PHASE 5: GO-LIVE & SUPPORT (Month 9-12, By Sep 30, 2570)
═══════════════════════════════════════════════════════════════

DELIVERABLE 5.1: Data Migration Services
├─ From: Old e-Payment system
├─ To: New e-Payment system
├─ Data to migrate:
│  ├─ Historical transactions (500 GB)
│  ├─ User accounts (5,000 users)
│  ├─ Configuration settings
│  └─ Reports & templates
├─ Validation: Automated scripts to verify data integrity
│  └─ Must match: Record count, checksums, date ranges
├─ Cutover plan: Detailed step-by-step procedure
├─ Rollback plan: How to revert if something goes wrong
├─ Delivery: By Aug 31, 2570 (before go-live)
└─ Testing: Dry-run migration 1 week before actual cutover

DELIVERABLE 5.2: Parallel Run Support (1-2 weeks)
├─ Old & new system run together
├─ All transactions processed by both systems
├─ Results compared daily (must match 100%)
├─ Issues logged & resolved within 24 hours
├─ Vendor provides 24/7 on-site support
├─ Sponsor sign-off required before cutover
└─ Delivery: Sep 1-15, 2570

DELIVERABLE 5.3: Go-Live Execution (1 day)
├─ Date: To be confirmed (likely Sep 6, 2570)
├─ Timeline:
│  ├─ 9:00 PM: Final backup of old system
│  ├─ 10:00 PM: Data migration starts
│  ├─ 11:00 PM: Validation & verification
│  ├─ 12:00 AM: Switch to new system
│  ├─ 6:00 AM: Morning operational checks
│  └─ 8:00 AM: System available to users
├─ Vendor: Dedicated team on-site
├─ Government: IT team on standby
└─ Sponsor: Available for emergency decisions

DELIVERABLE 5.4: Post-Go-Live Support (8 weeks)
├─ Duration: Sep 6 - Oct 31, 2570 (8 weeks)
├─ On-site support: 24/7 for first 4 weeks
├─ Remote support: 24/7 for all 8 weeks
├─ Help desk: Respond to calls within 30 min
├─ On-call team: For critical issues
├─ Services:
│  ├─ Bug fixes (same day for critical)
│  ├─ Performance tuning
│  ├─ User issue resolution
│  ├─ System optimization
│  └─ Capacity planning
├─ Success criteria: System stable & 99.9% uptime
└─ Delivery: Continuous, ending Sep 30, 2570

DELIVERABLE 5.5: Knowledge Transfer & System Handover
├─ Documentation:
│  ├─ Final runbook (how to run system daily)
│  ├─ Troubleshooting guide (how to fix problems)
│  ├─ Update procedures (how to apply patches)
│  └─ Monitoring procedures (what to watch)
├─ Training of government staff:
│  ├─ System administrators (3 people)
│  ├─ Help desk operators (2 people)
│  └─ IT support team (5 people)
├─ Vendor source code & documentation handed over
├─ License keys & access credentials transferred
├─ Vendor responsibility ends Sep 30
└─ Delivery: By Sep 30, 2570

═══════════════════════════════════════════════════════════════
SUMMARY OF ALL DELIVERABLES
═══════════════════════════════════════════════════════════════

Total Deliverables: 30+ documents, diagrams, code, & certifications

By Phase:
├─ Phase 1: 6 documents (Requirements, Design, Architecture)
├─ Phase 2: 4 documents (Source Code, Installation, API Docs)
├─ Phase 3: 5 documents (Test Results, UAT Sign-off, Audit Reports)
├─ Phase 4: 5 deliverables (Training materials, Manuals, Videos)
└─ Phase 5: 5 deliverables (Data migration, Support, Handover)

Quality assurance:
├─ All deliverables must pass quality review
├─ No typos, grammar errors, incomplete documents
├─ All diagrams must be professional quality
├─ All code must pass code review
├─ All tests must be comprehensive
└─ All documents must be in Thai & English

Acceptance process:
├─ Government reviews each deliverable
├─ May request changes/clarifications
├─ Must sign off before proceeding to next phase
├─ Final sign-off required before project completion
└─ Non-conforming deliverables = delayed payment
```

---

### **4.9 ระยะเวลาบำรุงรักษา / Support Duration - 150-200 คำ**

```
4.9 ระยะเวลาการให้บริการและการรับประกัน

A. SUPPORT PERIOD (ระยะเวลาหลังจาก Go-Live)

Phase 1: Intensive On-site Support
├─ Duration: First 4 weeks after go-live (Sep 6 - Oct 3, 2570)
├─ Presence: Full-time on-site at customer location
├─ Coverage: 24 hours per day, 7 days per week
├─ Response time: Immediate (on-site team present)
├─ Vendor personnel: 5-7 engineers on-site
└─ Services:
   ├─ Fix bugs & issues
   ├─ Tune performance
   ├─ Resolve user problems
   ├─ Optimize system configuration
   └─ Provide day-to-day operational support

Phase 2: Remote Support
├─ Duration: Following 4 weeks (Oct 4 - Nov 1, 2570)
├─ Presence: Remote (phone, email, video call)
├─ Coverage: 24 hours per day (on-call team)
├─ Response time:
│  ├─ Critical issues: Within 1 hour
│  ├─ High issues: Within 4 hours
│  └─ Medium issues: Within 8 hours
├─ Vendor personnel: 3-4 senior engineers on-call
└─ Services: Same as Phase 1

Phase 3: Managed Support
├─ Duration: Months 3-12 (Nov 2570 - Sep 2571)
├─ Support hours: Mon-Fri 8am-5pm, On-call 24/7
├─ Response time:
│  ├─ Critical: 1 hour, Resolve 4 hours
│  ├─ High: 4 hours, Resolve 24 hours
│  └─ Medium: 8 hours, Resolve 48 hours
├─ Vendor dedicated: Help desk + on-call engineer
└─ Services: Maintenance, monitoring, optimization

B. WARRANTY PERIOD (รับประกันระบบ)

Duration: 12 months from go-live (Sep 6, 2570 - Sep 5, 2571)

Covered:
├─ All bugs found during operation
├─ Performance issues (resolution within SLA)
├─ System crashes (root cause analysis)
├─ Data corruption (recovery from backup)
└─ Security vulnerabilities (patching within 48 hours)

Not covered:
├─ Damage from user error
├─ Hardware failures (vendor not responsible)
├─ Network outages (third-party, not vendor's fault)
├─ Changes to requirements (paid separately)
└─ Force majeure (natural disasters, war)

C. POST-SUPPORT MAINTENANCE

After 12-month warranty:
├─ Vendor can offer extended support contract
├─ Cost: TBD (typically 15-20% of project cost annually)
├─ Services: 
│  ├─ Security patches
│  ├─ Performance optimization
│  ├─ Consultation services
│  └─ Emergency support
├─ This is OPTIONAL (government can choose another vendor)
└─ Contract: To be negotiated separately
```

---

### **4.10 บุคลากรและทีมงาน / Personnel Requirements - 150-200 คำ**

```
4.10 บุคลากรที่ต้องจัดหา

Vendor ต้องจัดเตรียมบุคลากรตามต่อไปนี้:

A. PROJECT MANAGEMENT & LEADERSHIP

Project Manager (1 person)
├─ Full-time, throughout project (12 months)
├─ Responsibility:
│  ├─ Overall project success
│  ├─ Schedule management
│  ├─ Budget management
│  ├─ Stakeholder communication
│  └─ Risk management
├─ Qualifications:
│  ├─ PMP or PRINCE2 certification
│  ├─ 5+ years IT project management
│  ├─ Experience with government projects (preferred)
│  └─ Thai language proficiency
└─ Cannot be changed without government approval

Technical Lead / Architect (1 person)
├─ Full-time, throughout project
├─ Responsibility:
│  ├─ Overall technical decisions
│  ├─ Architecture design
│  ├─ Code quality assurance
│  ├─ Performance optimization
│  └─ Technology selection
├─ Qualifications:
│  ├─ TOGAF or Enterprise Architecture cert
│  ├─ 5-7 years system architecture experience
│  ├─ Expertise in Java/Python, Cloud, Databases
│  └─ Published papers or case studies (preferred)
└─ Key person - cannot change

B. DEVELOPMENT TEAM

Senior Developers (2 people)
├─ Full-time, 10+ months
├─ Focus: Backend development & core features
├─ Qualifications:
│  ├─ 5+ years software development
│  ├─ Expertise in Java/Spring Boot or Python/FastAPI
│  ├─ Database design experience
│  └─ Published code (GitHub portfolio)
└─ Key person - cannot change

Mid-level Developers (3 people)
├─ Full-time, 10+ months
├─ Focus: Feature development & API integration
├─ Qualifications:
│  ├─ 3-5 years development experience
│  ├─ Proficiency in assigned tech stack
│  └─ Ability to work independently
└─ Can be replaced with approval (same skill level)

Junior Developers (2-3 people)
├─ Full-time, 8+ months
├─ Focus: UI development, testing support
├─ Qualifications:
│  ├─ 1-3 years experience
│  ├─ Knowledge of React or frontend frameworks
│  └─ Ability to follow coding standards
└─ Can be replaced without approval

C. QUALITY ASSURANCE & TESTING

QA Lead (1 person)
├─ Duration: 8+ months
├─ Responsibility:
│  ├─ Test planning & strategy
│  ├─ Test case design
│  ├─ Quality assurance oversight
│  └─ Defect management
├─ Qualifications: ISTQB certification, 5+ years QA
└─ Key person - cannot change

QA Engineers / Testers (2 people)
├─ Duration: 8+ months
├─ Responsibility:
│  ├─ Execute test cases
│  ├─ Log defects
│  ├─ Regression testing
│  └─ Performance/load testing
├─ Qualifications: 3-5 years QA experience
└─ Can be replaced if necessary

D. DATABASE & INFRASTRUCTURE

Database Administrator (1 person)
├─ Duration: 7+ months (Part-time, 50%)
├─ Responsibility:
│  ├─ Database design
│  ├─ Performance tuning
│  ├─ Backup/recovery procedures
│  └─ Data migration
├─ Qualifications: Oracle/SQL Server/PostgreSQL DBA cert, 5+ years
└─ Key person - cannot change

System Administrator / DevOps (1 person)
├─ Duration: 8+ months (Part-time, 50%)
├─ Responsibility:
│  ├─ Infrastructure setup
│  ├─ Deployment automation
│  ├─ Monitoring & alerting
│  └─ Disaster recovery setup
├─ Qualifications: AWS/Azure cert, Linux/Cloud experience
└─ Can be replaced if necessary

E. SUPPORT & MAINTENANCE

Support Lead / Help Desk Manager (1 person)
├─ Duration: 6-12 months
├─ Responsibility: Manage help desk, prioritize issues
├─ Qualifications: 5+ years support management
└─ Key person - cannot change

Help Desk Engineers (3 people)
├─ Duration: 8 weeks intensive + 6 months on-call
├─ Responsibility: Answer user questions, troubleshoot
├─ Qualifications: 2-3 years IT support experience
└─ Can be rotated if necessary

On-call Support (2-3 people)
├─ Duration: 8 weeks 24/7 on-call
├─ Qualifications: Senior engineer level
└─ For critical issues outside business hours

F. TRAINING & DOCUMENTATION

Technical Writer (1 person)
├─ Duration: 5-6 months (Part-time, 50%)
├─ Responsibility: Write all documentation
├─ Qualifications: 3+ years technical writing, Thai fluency
└─ Can be replaced if necessary

Training Coordinator (1 person)
├─ Duration: 2 months intensive
├─ Responsibility: Organize & conduct training
├─ Qualifications: Training background preferred
└─ Can be temporary hire

TOTAL TEAM SIZE: 15-20 people
- Peak: Month 3-6 (all 20 people)
- Ramp down: Month 8-12 (5-10 people on-site + remote support)

TEAM AVAILABILITY:
├─ Key persons: Cannot be changed without government approval
├─ Other persons: Can be replaced if skill level maintained
├─ Holiday coverage: Vendor must arrange backups
├─ Vacation: Planned in advance, replacements provided

COMMUNICATION:
├─ Vendor must assign primary contact
├─ Government can request specific personnel changes
├─ Performance issues: Can trigger personnel replacement
├─ Incompatibility: Government can request removal
```

---

### **4.11 รูปแบบการบำรุงรักษา / Maintenance Model - 150-200 คำ**

```
4.11 แผนการบำรุงรักษาและดูแลระบบ

A. PREVENTIVE MAINTENANCE (บำรุงรักษาป้องกัน)

Monthly Maintenance Window
├─ Schedule: Every 2nd Sunday, 2:00 AM - 4:00 AM (2 hours)
├─ Activity:
│  ├─ Security patches (OS, Database, Libraries)
│  ├─ Database optimization (Rebuild indexes)
│  ├─ Performance analysis & tuning
│  ├─ Log cleanup & archiving
│  └─ Backup verification (test restore)
├─ Notification: Sent to users 1 week in advance
├─ Execution: Only if patches are available
└─ Rollback: Plan to revert if issues occur

Quarterly Performance Tuning (Every 3 months)
├─ Activity:
│  ├─ Analyze query performance
│  ├─ Review system logs for issues
│  ├─ Analyze user feedback for slow features
│  ├─ Optimize problematic areas
│  └─ Capacity planning (predict growth)
├─ Duration: 2-3 days on-site
└─ Report: Performance tuning recommendations

Annual Security Audit (Once per year)
├─ Activity:
│  ├─ Penetration testing
│  ├─ Vulnerability scanning
│  ├─ Code security review
│  ├─ Compliance check (ISO 27001, PCI-DSS)
│  └─ User access review
├─ Duration: 5-7 days
└─ Report: Professional audit report with findings

B. CORRECTIVE MAINTENANCE (บำรุงรักษาแก้ไข)

Bug Fixes
├─ Response time:
│  ├─ Critical (System down): 1 hour
│  ├─ High (Feature broken): 4 hours
│  └─ Medium (Minor issue): 8 hours
├─ Resolution time:
│  ├─ Critical: 4 hours
│  ├─ High: 24 hours
│  └─ Medium: 48 hours
├─ Testing: Bug fix must include regression test
└─ Deployment: After government approval

Emergency Maintenance
├─ Trigger: Critical issue (system down, data loss, security breach)
├─ Response: Immediate (within 30 minutes)
├─ Team: Vendor's senior engineers
├─ Escalation: Direct to vendor management
└─ Post-incident: Root cause analysis within 24 hours

C. INFRASTRUCTURE MAINTENANCE

Hardware Maintenance
├─ Vendor responsibility: Monitor hardware health
├─ Action:
│  ├─ Replace failing disks before failure
│  ├─ Update firmware (coordinated with maintenance window)
│  ├─ Upgrade RAM if performance degradation detected
│  └─ Replace aging servers (every 5 years)
├─ Downtime: Minimize, use redundancy when possible
└─ Vendor cost: Hardware replacement NOT vendor's cost (government pays)

Network Maintenance
├─ Vendor responsibility: Monitor network health
├─ Action:
│  ├─ Monitor bandwidth utilization
│  ├─ Identify & fix network bottlenecks
│  ├─ Update network configurations
│  └─ Test failover links
├─ Downtime: Coordinate with government IT team
└─ Note: Network owned by government ISP, vendor coordinates

D. DATABASE MAINTENANCE

Regular Backups
├─ Schedule:
│  ├─ Full backup: Every Sunday, 10:00 PM
│  ├─ Incremental: Daily, 11:00 PM
│  └─ Transaction logs: Every hour
├─ Retention:
│  ├─ Daily: 7 days
│  ├─ Weekly: 4 weeks
│  ├─ Monthly: 12 months
│  └─ Yearly: 7 years (regulatory requirement)
├─ Testing: Monthly restore test from backup
└─ Storage: Offsite (different geographic location)

Index Maintenance
├─ Schedule: Monthly during maintenance window
├─ Activity:
│  ├─ Rebuild fragmented indexes
│  ├─ Remove unused indexes
│  └─ Analyze index effectiveness
├─ Monitoring: Continuous (automated tools)
└─ Result: Improved query performance

Statistics Update
├─ Schedule: Monthly
├─ Purpose: Help database optimizer make good decisions
├─ Monitoring: Automated job (runs nightly)
└─ Result: Better query performance

E. PATCH MANAGEMENT

Operating System Patches
├─ Schedule: Monthly, on Patch Tuesday + 2 weeks
├─ Process:
│  ├─ Test patches in staging environment
│  ├─ Plan deployment window
│  ├─ Apply patches
│  ├─ Verify system still works
│  └─ Document changes
├─ Critical security patches: Applied within 48 hours
└─ Minor patches: Applied monthly

Application Patches
├─ Libraries & frameworks: Update monthly
├─ Java/Python: Update as needed (with testing)
├─ Third-party components: Update quarterly
├─ Testing: Full regression test required
└─ Risk: Backward compatibility assessment needed

F. DOCUMENTATION MAINTENANCE

System Documentation
├─ Update: Every time something changes
├─ Maintenance:
│  ├─ Architecture diagrams updated
│  ├─ Configuration documentation updated
│  ├─ API documentation updated
│  └─ Troubleshooting guide updated
├─ Review: Quarterly accuracy check
└─ Responsibility: Shared between vendor & government

Knowledge Transfer
├─ Ongoing: Transfer knowledge to government staff
├─ Monthly: Training sessions for new features
├─ Quarterly: Refresher training
└─ Goal: Reduce dependency on vendor over time
```

---

### **4.12 วิธีการจัดการระบบ / Operations & Management - 150-200 คำ**

```
4.12 การดำเนิน ติดตาม และบริหารจัดการระบบ

A. DAILY OPERATIONS

Morning Health Check (8:00 AM)
├─ Activity:
│  ├─ Check system status (all servers up)
│  ├─ Review error logs from overnight
│  ├─ Verify backups completed successfully
│  ├─ Check disk usage (alerts if >80%)
│  └─ Prepare daily report
├─ Time: 30 minutes
├─ Responsibility: Government admin (first) + Vendor help desk
└─ Report: Email to Sponsor & IT Manager

Transaction Monitoring
├─ Throughout the day:
│  ├─ Monitor transaction volume (normal vs spike)
│  ├─ Monitor error rates (should be <0.1%)
│  ├─ Monitor response time (should be <2 sec)
│  ├─ Check for bottlenecks
│  └─ Alert on any anomalies
├─ Tools: Prometheus/Grafana (monitoring dashboard)
├─ Responsibility: Government admin, on-site vendor support
└─ Action: Immediate escalation if critical

End-of-Day Close
├─ Activity:
│  ├─ Finalize daily transactions (no new transactions after 5pm)
│  ├─ Generate reconciliation report
│  ├─ Verify transaction count matches bank
│  ├─ Archive logs
│  └─ Prepare for next day
├─ Time: 1 hour
├─ Responsibility: Finance team + IT admin
└─ Report: Daily settlement report to Treasury

B. 24/7 MONITORING & ALERTING

Automated Monitoring
├─ Tools:
│  ├─ Prometheus (metrics collection)
│  ├─ Grafana (visualization & alerts)
│  ├─ ELK Stack (log analysis)
│  └─ PagerDuty (incident alerting)
├─ Metrics monitored:
│  ├─ System uptime (target 99.9%)
│  ├─ Response time (target <2 sec)
│  ├─ Error rate (target <0.1%)
│  ├─ CPU usage (alert if >80%)
│  ├─ Memory usage (alert if >80%)
│  ├─ Disk usage (alert if >80%)
│  ├─ Database connections (alert if >80% of max)
│  └─ Network bandwidth (alert if >70%)
├─ Alerts: Sent via email, SMS, mobile app
└─ Escalation: Automatic to senior engineer if not resolved in 30 min

On-Call Support
├─ Schedule: 24/7 rotation
├─ Team: 2-3 senior engineers
├─ Response time: 30 minutes max
├─ Contact: Phone, email, SMS
├─ Coverage: Holidays & weekends too
└─ Compensation: On-call pay for vendor staff

Incident Management
├─ Severity levels:
│  ├─ P1 (Critical): System down → Immediate action
│  ├─ P2 (High): Feature broken → Within 1 hour
│  ├─ P3 (Medium): Slow → Within 4 hours
│  └─ P4 (Low): Minor → Schedule for next maintenance
├─ Process:
│  ├─ Incident logged in system
│  ├─ Assigned to engineer
│  ├─ Root cause investigated
│  ├─ Fix implemented & tested
│  ├─ Deployed (after approval)
│  └─ Post-mortem if critical
└─ Communication: Regular updates to Sponsor

C. CAPACITY MANAGEMENT

Growth Monitoring
├─ Quarterly review:
│  ├─ Transaction volume trend
│  ├─ User growth
│  ├─ Data size growth
│  ├─ Current capacity remaining
│  └─ Projected capacity needs
├─ Tools: Excel reports + capacity planning tools
└─ Goal: Proactive scaling before hitting limits

Capacity Planning
├─ Planning:
│  ├─ If >80% capacity used → Plan upgrade
│  ├─ Lead time: 2-3 months for hardware
│  ├─ Recommendation: Add servers/storage
│  ├─ Cost: Approved separately from this contract
│  └─ Installation: Planned during maintenance window
├─ Report: Quarterly capacity report to management
└─ Responsibility: Vendor recommends, government approves & funds

D. CHANGE MANAGEMENT

Change Advisory Board (CAB)
├─ Members: IT Manager, Sponsor, Vendor lead
├─ Meeting: Monthly (or as needed)
├─ Purpose: Approve changes to system
├─ Process:
│  ├─ Request submitted with business case
│  ├─ CAB reviews impact & risks
│  ├─ Approved/Rejected/Deferred
│  ├─ Scheduled for implementation
│  ├─ Communication to users 1 week before
│  └─ Post-change verification

Types of Changes:
├─ Emergency (security/system down): Immediate approval
├─ Urgent (urgent fix): Expedited (next business day)
├─ Normal (features/updates): Monthly window
└─ Minor (documentation): No CAB required

Change Log
├─ Every change documented:
│  ├─ What changed & why
│  ├─ Who approved & when
│  ├─ When deployed
│  ├─ Any issues encountered
│  └─ Rollback plan if needed
├─ Kept for audit purposes (7 years)
└─ Report: Monthly change summary

E. DISASTER RECOVERY

Backup Execution
├─ Frequency:
│  ├─ Full backup: Weekly (Sundays)
│  ├─ Incremental: Daily (Monday-Saturday)
│  ├─ Transaction logs: Every hour (for point-in-time recovery)
│  └─ Off-site: Daily (copies to secondary location)
├─ Verification: Monthly restore test from backup
├─ Tool: Automated backup software (Commvault, etc.)
└─ Responsibility: Vendor manages, government verifies

Disaster Recovery Testing
├─ Quarterly DR drill:
│  ├─ Simulate full data center failure
│  ├─ Restore from backup to secondary location
│  ├─ Verify all systems work
│  ├─ Measure RTO (Recovery Time Objective) & RPO (Recovery Point Objective)
│  ├─ Document findings & improvements
│  └─ Provide report to management
├─ Failure criteria: >1 hour downtime = failure
└─ Goal: RTO = 4 hours, RPO = 1 hour

Business Continuity
├─ If primary data center fails:
│  ├─ Automatic failover to secondary location (if configured)
│  ├─ Systems restored within 4 hours
│  ├─ Users redirected to backup system
│  ├─ Communication to users every 30 min
│  └─ Recovery process begins immediately
├─ Post-incident: Investigation & improvements
└─ Cost: Secondary data center rental = separate line item

F. USER SUPPORT & HELP DESK

Help Desk Operation
├─ Hours: Mon-Fri 8am-5pm, On-call 24/7
├─ Channels:
│  ├─ Phone: Main help desk number
│  ├─ Email: For non-urgent issues
│  ├─ Ticketing system: Track all issues
│  └─ Knowledge base: Self-service articles
├─ Average response: 15 minutes
└─ Resolution: 80% on first contact

Issue Categories:
├─ Login problems: Reset password, account unlock
├─ Feature questions: How to use, documentation
├─ Data issues: Missing data, wrong data
├─ System performance: Slow, timeout
├─ Error messages: Explain & resolve
└─ Integration issues: Problems with Bank API, etc.

Escalation Path:
├─ L1 Help Desk: Basic issues (30% resolved here)
├─ L2 Technical Support: Complex issues (50% resolved here)
├─ L3 Senior Engineer: Critical issues (20% escalated)
└─ Vendor CTO: Architecture/design issues (rare)

Knowledge Base
├─ Content: 100+ articles
├─ Topics:
│  ├─ FAQs (20+ common questions)
│  ├─ How-to guides (step-by-step)
│  ├─ Troubleshooting (common problems & solutions)
│  └─ Best practices (how to use system effectively)
├─ Maintenance: Updated as new issues found
└─ Tool: Wiki or knowledge base software (Confluence, etc.)
```

---

### **4.13 แผนสำรองอัตราการสูญเสีย / Contingency & Disaster Recovery - 150-200 คำ**

```
4.13 แผนการสำรองและจัดการเหตุจำเป็น

A. DISASTER RECOVERY STRATEGY

RTO & RPO Targets
├─ RTO (Recovery Time Objective): 4 hours max
│  └─ If system fails at 12:00 noon, must be back up by 4:00 PM
├─ RPO (Recovery Point Objective): 1 hour max
│  └─ Maximum 1 hour of data loss acceptable
├─ Critical transactions: None should be lost (transaction logs every hour)
└─ Priority: Government operations must not stop

Secondary Site Setup
├─ Location: 20+ km away from primary (different building)
├─ Infrastructure: Mirrored (same servers as primary)
├─ Data replication: Synchronous (real-time copy)
├─ Network: Separate from primary (different ISP if possible)
├─ Cost: Shared infrastructure, included in annual maintenance
└─ Testing: Quarterly failover tests

B. FAILOVER PROCEDURES

Automatic Failover (if configured)
├─ Trigger: Primary site unreachable for 5 minutes
├─ Process:
│  ├─ Monitoring detects failure
│  ├─ DNS updated (users directed to secondary)
│  ├─ Database failover: Secondary becomes primary
│  ├─ Application servers: Secondary activated
│  └─ Users automatically redirected (no action needed)
├─ Time: 5-15 minutes (fully automatic)
└─ Testing: Quarterly to ensure works

Manual Failover (backup option)
├─ Trigger: Automatic failover unavailable or needs confirmation
├─ Process:
│  ├─ IT Manager authorizes failover
│  ├─ Vendor executes manual procedures
│  ├─ Database promoted to primary
│  ├─ Application restarted on secondary
│  ├─ DNS manually updated
│  └─ Users notified (brief downtime)
├─ Time: 30-60 minutes
└─ Responsibility: Vendor with government approval

C. DATA RECOVERY

Point-in-Time Recovery
├─ Capability: Restore system to any point in last 7 days
├─ Process:
│  ├─ Request: "Restore to 2:00 PM yesterday"
│  ├─ Vendor: Restore from transaction logs
│  ├─ Time: 30-60 minutes
│  ├─ Verification: Compare data before/after
│  └─ Approval: Government confirms before final restore
├─ Use case: User accidentally deleted important data
└─ Cost: Included in support contract

Partial Recovery
├─ Capability: Recover single transaction or record
├─ Process:
│  ├─ Identify specific item to recover
│  ├─ Extract from backup
│  ├─ Verify & import back
│  └─ Test & approve
├─ Time: 1-2 hours
├─ Use case: Specific customer data needs to be recovered
└─ Cost: Included in support contract

Full System Restore
├─ Capability: Restore entire system from backup
├─ Trigger:
│  ├─ Major corruption detected
│  ├─ Ransomware attack
│  ├─ Multiple hardware failures
│  └─ After thorough investigation & approval
├─ Process:
│  ├─ Latest backup identified
│  ├─ Restore to empty infrastructure
│  ├─ Data integrity verified
│  ├─ Users notified of data loss (if any)
│  └─ System cut over to restored environment
├─ Time: 4-8 hours
├─ Data loss: Up to 1 hour of transactions
└─ Communication: Hourly updates to Sponsor

D. BUSINESS CONTINUITY MEASURES

Backup Data Centers
├─ Hot Standby: Fully operational, synchronized real-time
├─ Cost: ~30% of primary (shared infrastructure)
├─ Failover: Automatic or manual within 4 hours
├─ Testing: Monthly failover test
└─ Goal: Zero downtime during failover

Vendor Business Continuity
├─ If vendor company fails:
│  ├─ Source code & documentation handed over
│  ├─ Government can hire another vendor for support
│  ├─ Escrow: Vendor deposits source code in escrow
│  └─ No vendor lock-in
├─ Responsibility: Government protects itself
└─ Contract: Escrow clause required

E. INCIDENT RESPONSE PLAN

Incident Notification
├─ Timeline: Notify Sponsor within 30 minutes of discovery
├─ Content: What happened, current status, ETA to fix
├─ Updates: Every 1 hour (more if critical)
├─ Channels: Phone call + email + SMS
├─ Escalation: Above vendor manager if not resolved in 2 hours

Investigation & Root Cause Analysis
├─ P1 incidents: RCA within 24 hours
├─ P2 incidents: RCA within 3 days
├─ P3 incidents: RCA within 1 week
├─ Content:
│  ├─ What happened
│  ├─ Why it happened
│  ├─ How to prevent next time
│  ├─ Recommendations for improvements
│  └─ Preventive actions (if needed)
├─ Report: Professional report to management
└─ Follow-up: Implement preventive actions

Post-Incident Improvement
├─ Actions: Implement preventive measures
├─ Monitoring: Enhanced monitoring for similar issues
├─ Training: Staff trained to prevent recurrence
├─ Documentation: Update procedures & runbooks
└─ Review: Quarterly review of all incidents

F. CONTINGENCY BUDGET

Unexpected Issues
├─ Budget: 10% of annual support cost reserved for contingencies
├─ Use: Unexpected repairs, emergency services
├─ Approval: Sponsor must approve use
├─ Reporting: Detailed breakdown of how contingency used
└─ Carryover: Unused contingency returns to government

Major Incidents
├─ If >2 hours downtime: Reduce payment by 5%
├─ If >4 hours downtime: Reduce payment by 10%
├─ If >8 hours downtime: Reduce payment by 20%
├─ Unless caused by: External factors (network down, ISP failure)
└─ Negotiation: Case-by-case assessment
```

---

### **4.14 ความปลอดภัยของระบบ / Security Requirements - 200-250 คำ**

```
4.14 ความปลอดภัยและการป้องกันอันตราย

A. ENCRYPTION & DATA PROTECTION

Data at Rest (Data ไว้ static ในเซิร์ฟเวอร์)
├─ Encryption: AES-256
├─ Key Management:
│  ├─ Keys stored in Hardware Security Module (HSM)
│  ├─ Key rotation: Every 90 days
│  ├─ Only authorized staff can access keys
│  └─ Backup keys: Encrypted & stored separately
├─ Database: Transparent Data Encryption (TDE) enabled
├─ Files: At rest encryption for sensitive files
└─ Compliance: PCI-DSS requirement 3.2.1

Data in Transit (Data ระหว่างส่ง over network)
├─ Protocol: HTTPS/TLS 1.2 or higher (not HTTP)
├─ Certificate: SSL/TLS certificate from trusted CA
│  ├─ Certificate type: Extended Validation (EV)
│  ├─ Provider: DigiCert or GlobalSign
│  ├─ Renewal: Before expiration (auto-renewal)
│  └─ Domain verification: Annual
├─ API: OAuth 2.0 with HTTPS
├─ Email: TLS for SMTP (encrypted email)
└─ Testing: Regular SSL/TLS configuration audit

B. AUTHENTICATION & ACCESS CONTROL

User Authentication
├─ Method: Multi-Factor Authentication (MFA) required
│  ├─ Factor 1: Username & strong password
│  │  └─ Password: Min 12 characters, special chars, numbers
│  ├─ Factor 2: Time-based OTP (Google Authenticator)
│  │  or SMS OTP (less preferred, less secure)
│  └─ Backup: Recovery codes (stored securely)
├─ Session: Timeout after 30 minutes inactivity
├─ Password: Change required every 90 days
├─ Login attempts: Max 5 failed attempts → Account locked (30 min)
└─ Requirement: ISO 27001 standard

Role-Based Access Control (RBAC)
├─ Roles defined:
│  ├─ Admin: Full system access
│  ├─ Officer: Can process payments
│  ├─ Supervisor: Can approve transactions >threshold
│  ├─ Auditor: Read-only access to logs
│  ├─ Manager: Dashboard & reports only
│  └─ User: Can view own transactions
├─ Principle: Least privilege (users only get minimum needed)
├─ Implementation: Database-level + application-level
├─ Review: Quarterly access review (ensure still needed)
└─ Audit: All access changes logged

C. NETWORK SECURITY

Firewall Rules
├─ Inbound: Only required ports open (443/HTTPS)
├─ Outbound: Restricted to necessary services (Bank API, etc.)
├─ Rules: Documented & reviewed quarterly
├─ Failure: Firewall failure → Automatic failover
├─ Logging: All firewall blocks logged
└─ Alert: Unusual traffic patterns alert admin

WAF (Web Application Firewall)
├─ Protection: SQL injection, XSS, DDoS attacks
├─ Rules: OWASP Top 10 protection rules
├─ False positives: Regular tuning to minimize
├─ Monitoring: Real-time, alerts on attacks
└─ Updates: Signature updates daily

DDoS Protection
├─ Service: Cloudflare or similar CDN with DDoS protection
├─ Detection: Automatic, no manual intervention needed
├─ Mitigation: Traffic scrubbing, rate limiting
├─ Testing: Annual DDoS simulation test
└─ SLA: 99.9% availability even during DDoS

VPN for Vendors
├─ Access: Vendor remote access via VPN only
├─ Authentication: Certificate-based (most secure)
├─ Logging: All VPN connections logged
├─ Audit: Quarterly VPN access review
└─ Requirement: No direct internet access to systems

D. APPLICATION SECURITY

Code Security
├─ Development: Secure coding standards (OWASP, CWE Top 25)
├─ Review: Code review by 2+ reviewers before merge
├─ Testing: Static code analysis (SonarQube)
│  └─ No CRITICAL/HIGH severity issues allowed
├─ Dependencies: Regular scan for vulnerable libraries
│  └─ Update vulnerable components immediately
├─ SAST Tool: Automated security scanning
└─ Training: Developers trained on secure coding

Input Validation
├─ All inputs: Validated on server side (not just client)
├─ SQL injection: Parameterized queries (prepared statements)
├─ XSS prevention: HTML encoding, CSP headers
├─ File uploads: Restrict file types, scan for malware
├─ Request size: Limit payload to prevent resource exhaustion
└─ Testing: OWASP Top 10 security testing

Session Management
├─ Tokens: Use secure session tokens (not simple cookies)
├─ Storage: Tokens stored encrypted
├─ Lifetime: Short-lived (30 minutes), refresh token mechanism
├─ CSRF protection: CSRF tokens on all state-changing requests
├─ Cookie flags: HttpOnly, Secure, SameSite flags set
└─ Logout: Clear session on logout

E. AUDIT & LOGGING

Audit Trail
├─ Scope: Every action logged (login, data access, changes, approvals)
├─ Data logged:
│  ├─ Who (user ID)
│  ├─ What (action taken)
│  ├─ When (timestamp)
│  ├─ Where (IP address, session ID)
│  ├─ Result (success/failure)
│  └─ Why (reason/comment)
├─ Retention: 7 years (regulatory requirement)
├─ Immutable: Logs cannot be changed or deleted (WORM - Write Once Read Many)
├─ Centralized: All logs sent to central logging server
└─ Analysis: Regular audit log analysis for suspicious activity

Monitoring & Alerting
├─ Real-time: Alerts for suspicious activities
│  ├─ Multiple failed logins from same IP
│  ├─ Access to sensitive data outside normal hours
│  ├─ Rapid transactions from unusual locations
│  ├─ Database queries to sensitive tables
│  └─ File access outside application
├─ Response: Automatic lock/alert admin within 5 minutes
├─ Escalation: Critical alerts → SMS + phone call
└─ Review: Daily log review by security officer

F. SECURITY COMPLIANCE

ISO 27001 Certification
├─ Scope: Information Security Management System
├─ Requirements: 114 controls to implement
├─ Annual audit: Third-party certification audit
├─ Maintenance: Continuous improvement process
├─ Cost: Included in vendor support contract
└─ Goal: Maintain ISO 27001 certification throughout

PCI-DSS Compliance (Payment Card Industry)
├─ Requirement: Because system processes payments
├─ Level: Level 1 (highest for < 6M transactions/year)
├─ Requirements:
│  ├─ Strong encryption
│  ├─ Access control
│  ├─ Regular security testing
│  ├─ Security monitoring
│  └─ Incident response plan
├─ Annual audit: By PCI-certified auditor
└─ Scope: Credit card data protection

OWASP Top 10 Compliance
├─ Top 10 common web vulnerabilities:
│  ├─ 1. Broken Access Control
│  ├─ 2. Cryptographic Failures
│  ├─ 3. Injection
│  ├─ 4. Insecure Design
│  ├─ 5. Security Misconfiguration
│  ├─ 6. Vulnerable & Outdated Components
│  ├─ 7. Authentication Failures
│  ├─ 8. Software & Data Integrity Failures
│  ├─ 9. Logging & Monitoring Failures
│  └─ 10. Server-Side Request Forgery
├─ Testing: Regular OWASP Top 10 testing
├─ Fixes: Found issues fixed within SLA
└─ Report: Annual OWASP compliance report

G. SECURITY TESTING

Penetration Testing (Ethical Hacking)
├─ Frequency: Annual (or after major changes)
├─ Scope: All systems (web, API, network, infrastructure)
├─ Depth: Comprehensive, white-box testing (tester has internal access)
├─ Tools: Burp Suite, Metasploit, custom scripts
├─ Report: Detailed findings with remediation recommendations
├─ Follow-up: Re-testing of fixed issues
└─ Cost: ~200-400K baht per year (separate from support)

Vulnerability Scanning
├─ Frequency: Monthly automated, quarterly manual
├─ Scope: Network, applications, databases
├─ Tools: Qualys, Rapid7, OpenVAS
├─ False positives: Regular tuning to reduce
├─ Response: Critical vulnerabilities fixed within 48 hours
└─ Report: Monthly vulnerability summary

Security Awareness Training
├─ Frequency: Annual for all staff
├─ Topics:
│  ├─ Password security
│  ├─ Phishing attacks
│  ├─ Social engineering
│  ├─ Secure coding (for developers)
│  ├─ Incident response
│  └─ Compliance requirements
├─ Testing: Quiz after training
├─ Certification: Training certificate issued
└─ Responsibility: Vendor provides training (first year)

H. INCIDENT RESPONSE & FORENSICS

Security Incident Handling
├─ Detection: Automated + manual (user reports)
├─ Response time: <1 hour for confirmed breach
├─ Investigation: Preserve evidence, identify scope
├─ Containment: Isolate affected systems
├─ Communication: Notify affected users within 24 hours (if required by law)
├─ Recovery: Restore from clean backup if needed
├─ Post-mortem: Root cause analysis + preventive actions
└─ Report: Detailed incident report to management

Forensic Capabilities
├─ Evidence preservation: Logs, file backups, memory dumps
├─ Chain of custody: Document who accessed evidence when
├─ Analysis: Determine attack vector, impact, duration
├─ Expert: Vendor has forensics expert available
├─ Report: Suitable for legal/regulatory requirements
└─ Cost: Included in critical incident support

SUMMARY OF SECURITY REQUIREMENTS:
├─ Encryption: AES-256 at rest, TLS 1.2+ in transit
├─ Authentication: MFA (password + OTP/hardware token)
├─ Access: RBAC, least privilege principle
├─ Audit: 100% activity logging, 7-year retention
├─ Compliance: ISO 27001, PCI-DSS, OWASP Top 10
├─ Testing: Annual pen testing, monthly vulnerability scanning
├─ Monitoring: 24/7 monitoring with real-time alerts
└─ Incident Response: <1 hour response time for breaches
```

---

## ⭐ ส่วนที่ 5-10 (สั้นขึ้น แต่ยังละเอียด)

### **ส่วนที่ 5: ระยะเวลา (Timeline) - 200-300 คำ**

```
5.0 ระยะเวลาการจ้าง

วันเริ่มต้น: 1 ตุลาคม พ.ศ. 2569
วันสิ้นสุด: 30 กันยายน พ.ศ. 2570
ระยะเวลารวม: 365 วัน / 52 สัปดาห์ / 12 เดือน

PHASES:
├─ Phase 0: Pre-Drafting & Setup (Week -2 to 0, Complete by Sep 30)
├─ Phase 1: Analysis (Week 1-4, Oct 1 - Oct 31)
├─ Phase 2: Design & Planning (Week 5-10, Nov 1 - Dec 15)
├─ Phase 3: Development (Week 11-27, Dec 16 - May 15)
├─ Phase 4: Testing & QA (Week 24-30, May 1 - Jun 30)
├─ Phase 5: Training (Week 28-36, Jul 1 - Aug 31)
└─ Phase 6: Go-Live & Support (Week 37-52, Sep 1 - Sep 30)

KEY MILESTONES:
├─ Oct 15: Requirements Approved
├─ Dec 15: Design Review & Sign-off
├─ Feb 1: Infrastructure Ready
├─ Apr 1: Development Half-way Complete
├─ May 15: Development Complete & Testing Begins
├─ Jun 30: UAT Completed & Approved
├─ Aug 31: Training Complete
├─ Sep 6: Go-Live Date
└─ Sep 30: Project End & Support Handover

TIMELINE NOTES:
├─ Go-Live date is FIXED (cannot be delayed)
├─ Earlier phases must be compressed if delays occur
├─ Resource allocation: Peak team size in Month 3-6
├─ Ramp down: 70% reduction in Month 9-12
└─ Flexibility: ±2 weeks allowed for Phases 1-3 only

GANTT CHART:
[See detailed timeline diagram attached]
```

---

### **ส่วนที่ 6: เกณฑ์การคัดเลือก (Evaluation Criteria) - 250-300 คำ**

```
6.0 เกณฑ์การคัดเลือกและการให้คะแนน

A. BIDDING PROCESS

Method: Two-Stage One-Envelope
├─ Stage 1: Envelope containing:
│  ├─ Qualification documents (Certificates, Reference letters, etc.)
│  ├─ Technical proposal (System design, approach)
│  └─ Implementation plan (Timeline, resources)
├─ Stage 2: Envelope containing:
│  └─ Financial proposal (Price breakdown)
└─ Evaluation: Qual first, Price only for qualified bidders

B. EVALUATION CRITERIA & WEIGHTAGE

Total Score: 100 points

Technical Proposal (35 points)
├─ System Architecture Design (10 points)
├─ Technology Stack & Justification (8 points)
├─ Risk Management Plan (7 points)
├─ Quality Assurance Approach (10 points)

Personnel & Team (20 points)
├─ Project Manager Qualifications (5 points)
├─ Technical Lead Qualifications (5 points)
├─ Team Composition & Experience (5 points)
├─ Key Personnel Commitment (5 points)

Methodology & Process (15 points)
├─ Project Management Methodology (5 points)
├─ SDLC Process (5 points)
├─ Quality Standards (ISO 9001, etc.) (5 points)

Schedule & Plan (10 points)
├─ Timeline Realism (5 points)
├─ Milestone Definition (5 points)

Support Plan (10 points)
├─ Post-Go-Live Support (5 points)
├─ Training & Documentation Plan (5 points)

Price Proposal (10 points)
├─ Lowest price gets 10 points
├─ Others: (Lowest price / This price) × 10

C. SCORING METHOD

Qualitative Scoring (Technical, Personnel, etc.):
├─ Scale: 0-10 per criterion
├─ Scoring: Average of 3 evaluators' scores
├─ Justification: Evaluators must document reasoning

Price Scoring:
├─ Formula: (Lowest price / Bid price) × 10 × 0.10
├─ Example: If lowest = 90M, bid = 95M
│  Score = (90/95) × 10 × 0.10 = 0.947 points

Total Score:
├─ Formula: Qual (35+20+15+10+10) × Normalization + Price (10)
├─ Final score: 0-100 points
└─ Winner: Highest total score (not lowest price)

D. MINIMUM PASSING SCORE

├─ Overall: ≥60 points (out of 100)
├─ Technical: ≥50% of technical points (≥19/38 points)
├─ Below minimum: Bidder is rejected (not considered further)
└─ Conditional approval: At 60-70 points (negotiations allowed)

E. EVALUATION COMMITTEE

Composition (7-9 members):
├─ Sponsor or representative (Chairperson)
├─ Technical representative (IT Manager)
├─ Finance representative
├─ Procurement specialist
├─ End-user representative
├─ External expert (optional, for complex projects)
├─ Project management expert
└─ Legal representative (observer)

Evaluation Timeline:
├─ Days 1-2: Technical evaluation (scoring)
├─ Day 3: Price envelope opening
├─ Day 4: Price evaluation
├─ Day 5: Final scoring & winner selection
├─ Day 6-7: Negotiations with selected bidder
└─ Day 8: Contract award

F. AWARD DECISION

Winner Selection:
├─ Bidder with highest total score (quality + price balanced)
├─ If tied: Bidder with highest technical score wins
├─ Announcement: Within 48 hours of decision
├─ Appeal period: 5 days (bidders can protest)

Contract Award:
├─ Terms: To be negotiated in detail
├─ Insurance: Vendor must provide performance bond
├─ Start date: Within 30 days of contract signing
└─ Kickoff: Within 1 week of start date

NOTES FOR BIDDERS:
├─ Price alone does not win (quality is important)
├─ Don't bid too low (unsustainable = quality issues)
├─ Don't bid too high (non-competitive)
├─ Be realistic: ±10% of budget estimate is reasonable
└─ Quality matters more than price in this procurement
```

---

### **ส่วนที่ 7: วงเงินงบประมาณ (Budget) - 100-150 คำ**

```
7.0 วงเงินงบประมาณ

จำนวนเงินรวมทั้งสิ้น:

NINETY-THREE MILLION
FOUR THOUSAND FIVE HUNDRED BAHT ONLY
(93,004,500 บาท)

แหล่งที่มา:
เงินงบประมาณประจำปีงบประมาณ พ.ศ. 2570
ตามประกาศราคากลาง ลงวันที่ 31 กรกฎาคม พ.ศ. 2569

ประเภทของงบประมาณ:
งบประมาณปกติ (ไม่ใช่เงินสำรอง หรืองบประมาณพิเศษ)

หมายเหตุ:
├─ งบประมาณนี้ รวมทุก Phase (Analysis, Design, Development, Testing, Training, Support)
├─ Hardware costs: Included ในงบประมาณนี้
├─ Software licenses: Included ในงบประมาณนี้
├─ บำรุงรักษา 12 เดือน: Included ในงบประมาณนี้
├─ Hardware replacement after year 1: NOT included (separate contract)
├─ Third-party penetration testing: NOT included (optional, ~200-400K separately)
└─ Contingency: 10% of annual support reserved for unexpected

ความเห็นต่างเกี่ยวกับราคา:
├─ ต่ำกว่าประกาศราคากลาง: ต้องให้เหตุผล (cost reduction initiatives, etc.)
├─ สูงกว่าประกาศราคากลาง: ต้องได้รับอนุมัติ จากผู้บริหาร
└─ การเจรจาราคา: ไม่อนุญาต (fixed price contract)
```

---

### **ส่วนที่ 8: จ่ายเงิน (Payment Schedule) - 250-300 คำ**

```
8.0 งวดและเงื่อนไขการจ่ายเงิน

Total Budget: 93,004,500 บาท แบ่งเป็น 4 งวด

MILESTONE 1: Contract Signing & Project Kickoff (30%)
├─ Percentage: 30% × 93,004,500 = 27,901,350 บาท
├─ Conditions for payment:
│  ├─ Signed contract between government & vendor
│  ├─ Performance bond (5-10% of contract) submitted
│  ├─ Insurance certificate submitted
│  ├─ Kickoff meeting completed
│  └─ Project team assigned & ready
├─ Payment timing: Within 15 days of contract signing
├─ Retention: None (full 30% paid)
└─ Acceptance: IT Manager verifies conditions met

MILESTONE 2: Design Review & Approved (20%)
├─ Percentage: 20% × 93,004,500 = 18,600,900 บาท
├─ Conditions for payment:
│  ├─ System Architecture Design Document submitted
│  ├─ Database Design Document submitted
│  ├─ Security Architecture Design submitted
│  ├─ Design Review meeting completed
│  ├─ Committee approves design (>80% committee votes YES)
│  └─ Design document signed off by Sponsor
├─ Payment timing: Within 15 days of design approval
├─ Retention: 10% retained (~1.86M) until next milestone
├─ Due date: By December 15, 2569
└─ Acceptance: Sponsor signs design approval document

MILESTONE 3: Development & Testing Complete (30%)
├─ Percentage: 30% × 93,004,500 = 27,901,350 บาท
├─ Conditions for payment:
│  ├─ Development complete (100% of features)
│  ├─ System testing passed (95%+ test cases pass)
│  ├─ UAT completed & approved by end-users
│  ├─ Performance testing passed (< 2 sec response time)
│  ├─ Security audit passed (no CRITICAL/HIGH issues)
│  ├─ Code review completed (all code reviewed)
│  ├─ Documentation complete (User Manual, Admin Guide, etc.)
│  └─ UAT Sign-off document from government
├─ Payment timing: Within 15 days of UAT approval
├─ Retention: 10% retained (~2.79M) until next milestone
├─ Due date: By June 30, 2570
└─ Acceptance: UAT committee approves (majority vote)

MILESTONE 4: Go-Live & Stabilization (20%)
├─ Percentage: 20% × 93,004,500 = 18,600,900 บาท
├─ Conditions for payment:
│  ├─ Go-Live executed successfully (Sep 6, 2570)
│  ├─ System stabilized (≥99.9% uptime for 4 weeks)
│  ├─ Post-Go-Live support completed (8 weeks)
│  ├─ Training completed (20 staff certified)
│  ├─ Knowledge transfer documentation submitted
│  ├─ All issues from go-live resolved
│  ├─ System performance metrics met (< 2 sec)
│  └─ Final handover sign-off from Sponsor
├─ Payment timing: Within 30 days of project completion
├─ Retention: 5% retained (~0.93M) for 6 months (hold-back period)
├─ Hold-back release: When system stable 6 months
├─ Due date: By September 30, 2570
└─ Acceptance: Sponsor & IT Manager joint sign-off

TOTAL PAYMENT SCHEDULE:
│ Milestone │ Description │ % │ Amount │ Retention │ Timing │
│ 1 │ Contract signing │ 30 │ 27.9M │ 0 │ Oct 2569 │
│ 2 │ Design approved │ 20 │ 18.6M │ 10% │ Dec 2569 │
│ 3 │ Development done │ 30 │ 27.9M │ 10% │ Jun 2570 │
│ 4 │ Go-Live stable │ 20 │ 18.6M │ 5% │ Sep 2570 │
│ Total │ │ 100 │ 93.0M │ 3.72M held │ 12 months │

PAYMENT CONDITIONS:
├─ Payment method: Bank transfer (government to vendor bank)
├─ Currency: Thai Baht (THB)
├─ Bank details: Provided by vendor
├─ Withholding tax: 3% withheld (government requirement)
├─ Invoice: Vendor submits invoice with supporting documents
├─ Approval: Government approves invoice within 7 days
├─ Processing: Bank transfer within 15 days of approval
└─ Proof: Vendor receives bank confirmation within 3-5 days

PENALTY FOR NON-COMPLIANCE:
├─ Delayed payment (> 15 days): Interest 7.5% per annum
├─ Incomplete deliverable: Milestone payment delayed until complete
├─ Quality issues: 10-20% payment reduction until fixed
└─ Schedule delay: 0.5% payment reduction per week delayed

DISPUTE RESOLUTION:
├─ Disagreement on acceptance: Try to resolve within 7 days
├─ Escalation: Project Steering Committee reviews
├─ If still unresolved: Arbitration (Thai Arbitration Commission)
└─ Payment held: Until dispute resolved
```

---

### **ส่วนที่ 9: ค่าปรับและรับประกัน (Penalties & Warranty) - 250-300 คำ**

```
9.0 ค่าปรับ รับประกัน และเงื่อนไขการดำเนินการ

A. LATE COMPLETION PENALTY

If project not completed by Sep 30, 2570:

Daily Penalty:
├─ Formula: 0.1% × Remaining contract value per day late
├─ Example: If 1 week late, penalty = 0.1% × 93M × 7 = 6.51M baht
├─ Maximum: 5% of total contract value (4.65M baht cap)
├─ Calculation: Daily from Oct 1 until completion
├─ Payment: Deducted from final milestone or paid separately
├─ Waiver: Only if delay caused by government (e.g., slow approval)

Go-Live Delay Penalty:
├─ If Go-Live delayed beyond Sep 6, 2570: 1% per week
├─ Maximum: 10% total (9.3M baht)
└─ Note: Government can choose to extend timeline instead

B. PERFORMANCE PENALTIES

System Uptime Below 99.9%:
├─ If uptime < 99.9% in any month:
├─ Penalty: 0.05% × monthly amount for each 0.1% miss
├─ Example: 99.8% uptime = 0.05% × payment = penalty
├─ Maximum: 5% per month
├─ Reset: Each month penalty calculation independent
├─ Waiver: External causes (ISP down, natural disaster)

Response Time > 2 seconds:
├─ If 90th percentile response time > 2 sec for 5+ consecutive days:
├─ Penalty: 0.05% × monthly payment per 0.5 sec overage
├─ Action: Vendor must submit performance improvement plan
├─ Resolution: Fix within 3 days or penalty applies
├─ Maximum: 5% per month
└─ Testing: Measured by government monitoring tools

Error Rate > 0.1%:
├─ If transaction error rate > 0.1%:
├─ Penalty: 0.1% × monthly payment per 0.05% overage
├─ Investigation: Vendor must investigate root cause within 24 hours
├─ Fix: Resolution required within 48 hours
├─ Maximum: 5% per month
└─ Example: 0.15% error rate = penalty applies

C. WARRANTY PERIOD

Duration: 12 months from Go-Live (Sep 6, 2570 - Sep 5, 2571)

Covered Under Warranty:
├─ Software bugs & defects
├─ Performance issues
├─ Data loss & corruption
├─ System crashes
├─ Security vulnerabilities
├─ Integration problems
└─ Design flaws

Not Covered:
├─ Hardware failures (replaced by equipment provider)
├─ User errors (deleted data, wrong input)
├─ Third-party system failures (Bank API, ISP network)
├─ Customization requests (beyond original scope)
├─ Training & support (covered separately)
└─ Force majeure events

Warranty Services:
├─ Bug fix: Within SLA (4-48 hours depending on severity)
├─ Defect elimination: 100% defect-free or penalty
├─ Performance guarantee: Maintain <2 sec response time
├─ Availability: 99.9% uptime maintained
└─ Cost: Included in contract (no additional charge)

D. POST-WARRANTY SUPPORT

After 12-month warranty ends (Sep 6, 2571):
├─ Warranty ends, support becomes optional
├─ Extended support available at ~15-20% annual rate
├─ Government can choose another vendor for support
├─ Source code ownership: Government has full ownership
├─ Continued support: Negotiated separately, not mandatory
└─ Contract: New contract required for any extension

E. DEFECT MANAGEMENT

Defect Reporting:
├─ Any defect reported by government
├─ Logged in tracking system (Jira or similar)
├─ Priority assigned: Critical, High, Medium, Low
├─ Target resolution date set based on severity

Severity Levels:
├─ Critical: System down or data loss risk
│  └─ Response: 1 hour, Resolution: 4 hours
├─ High: Feature broken or serious impact
│  └─ Response: 4 hours, Resolution: 24 hours
├─ Medium: Minor impact, workaround available
│  └─ Response: 8 hours, Resolution: 48 hours
├─ Low: Cosmetic or minor issue
│  └─ Response: 24 hours, Resolution: 72 hours
└─ SLA: Measured by actual response & resolution times

Defect Fix Process:
├─ Vendor investigates & identifies root cause
├─ Develops fix
├─ Tests fix (must not break other functionality)
├─ Submits for government review
├─ Government approves (or requests changes)
├─ Deployed (during maintenance window if possible)
├─ Verified by government (defect closed)
└─ Documentation: Updated to reflect fix

Defect Trends:
├─ Tracked monthly: Number of defects, resolution time
├─ Report: Monthly defect summary to Sponsor
├─ Trend: Should decrease over time (sign of stabilization)
├─ Quality gate: >5 Critical defects/month = failure
└─ Action: If quality gate failed → escalate to vendor management

F. SERVICE LEVEL AGREEMENT (SLA)

Response Time:
├─ Critical issue: 1 hour response
├─ High issue: 4 hours response
├─ Medium issue: 8 hours response
├─ Low issue: 24 hours response

Resolution Time:
├─ Critical issue: 4 hours (or issue escalated)
├─ High issue: 24 hours (or issue escalated)
├─ Medium issue: 48 hours (or issue escalated)
├─ Low issue: 72 hours

Availability Target:
├─ 99.9% uptime (43.2 minutes max downtime/month)
├─ Planned maintenance: Excluded from downtime calculation
├─ Unplanned outage: Included in downtime
├─ Calculation: (Uptime hours / Total hours) × 100 = Uptime %

Support Escalation:
├─ L1 Help Desk: Try to resolve within 1 hour
├─ L2 Technical Support: Escalate if not resolved
├─ L3 Senior Engineer: For complex technical issues
├─ L4 Vendor Management: If SLA at risk
└─ L5 Executive Escalation: Critical business impact

G. REMEDIES FOR NON-COMPLIANCE

If vendor fails to meet SLA/penalties:

Financial Remedies:
├─ Payment deductions (up to 20% total)
├─ Reimbursement for emergency support cost
├─ Compensation for downtime impact
└─ Interest on delayed payment (7.5% per annum)

Operational Remedies:
├─ Require performance improvement plan
├─ Increase on-site support requirement
├─ Assign senior personnel
├─ Daily monitoring until improvement shown
└─ Vendor improvement: 30 days to demonstrate

Termination Rights:
├─ If vendor fails critical requirements:
│  ├─ 30-day notice period to cure
│  ├─ If not cured: Termination for cause
│  └─ Government can hire replacement vendor
├─ Cost: Vendor liable for additional cost
├─ Penalty: Breach of contract damages
└─ Impact: Vendor removed from future bids (blacklist)
```

---

### **ส่วนที่ 10: เอกสารหลักฐาน (Supporting Documents) - 150-200 คำ**

```
10.0 เอกสารประกอบและการยื่นข้อเสนอ

ผู้เสนอราคาต้องยื่นเอกสารต่อไปนี้:

A. LEGAL & REGISTRATION DOCUMENTS

├─ Company Registration Certificate
│  └─ Issued by: Department of Business Development
├─ Tax ID Certificate
│  └─ Proof that company is registered for tax purposes
├─ Board Resolution (for companies)
│  └─ Approval to participate in tender
└─ Affidavit (ค.ร.ม.)
   └─ Certification of company status & truthfulness

B. FINANCIAL DOCUMENTS (ย้อนหลัง 2 ปี)

├─ Financial Statements (Audited)
│  ├─ Balance Sheet
│  ├─ Income Statement
│  ├─ Cash Flow Statement
│  └─ Auditor's Report (signed by certified auditor)
├─ Bank Statement
│  └─ Showing company's bank balance (last 6 months)
├─ Proof of Paid-up Capital
│  └─ From bank (Certificate showing capital deposited)
└─ Tax Clearance Certificate
   └─ Showing no outstanding tax debt

C. EXPERIENCE DOCUMENTS

├─ Reference Letters
│  └─ From 3-5 previous clients (on their letterhead, signed)
├─ Certificate of Project Completion
│  └─ For each reference project (from client)
├─ Performance Evaluation
│  └─ How clients rate vendor's work
└─ Case Studies
   └─ Description of past projects, results achieved

D. PERSONNEL DOCUMENTS

├─ Key Personnel CVs
│  └─ Resume showing experience & qualifications
├─ Educational Certificates
│  └─ Diplomas, degrees (certified copies)
├─ Professional Certifications
│  ├─ PMP, PRINCE2, TOGAF, CCNA, CISSP, DBA, etc.
│  └─ Copies of certificates
└─ Work Experience Letters
   └─ From previous employers

E. QUALITY & COMPLIANCE DOCUMENTS

├─ ISO 9001 Certificate
│  └─ Quality Management System certification
├─ ISO 27001 Certificate
│  └─ Information Security Management
├─ Quality Policy Document
│  └─ Company's quality standards & procedures
├─ Security Policy Document
│  └─ How company protects information
└─ Project Management Methodology Document
   └─ Process used for managing projects

F. TECHNICAL PROPOSAL (Main Document - 20-30 pages)

├─ Executive Summary (2 pages)
├─ System Architecture Design (5-8 pages)
│  └─ Diagram + explanation of proposed solution
├─ Technology Stack (3-5 pages)
│  └─ Justification for each technology choice
├─ Database Design (3-4 pages)
├─ Security Approach (3-4 pages)
├─ Implementation Plan (3-5 pages)
│  └─ Phase breakdown, timeline, risks
├─ Quality Assurance Plan (2-3 pages)
├─ Support & Maintenance Plan (2-3 pages)
└─ Risk Management Plan (2 pages)

G. FINANCIAL PROPOSAL

├─ Cost Breakdown (Required)
│  ├─ Hardware: (amount)
│  ├─ Software: (amount)
│  ├─ Development labor: (amount)
│  ├─ Testing: (amount)
│  ├─ Training: (amount)
│  ├─ Support (12 months): (amount)
│  ├─ Contingency (10%): (amount)
│  └─ Total: 93,004,500 baht
├─ Payment Terms (as per Section 8)
├─ Assumptions (if price varies from proposal)
└─ Cost Escalation (if project extends beyond 12 months)

H. SUBMISSION REQUIREMENTS

Submission Format:
├─ Two separate sealed envelopes:
│  ├─ Envelope 1: Technical proposal (+ all supporting docs)
│  └─ Envelope 2: Financial proposal (Price only)
├─ Both envelopes in one larger sealed envelope
├─ Label: "Tender for e-Payment System Modernization"
├─ Date/Time: Must arrive by submission deadline
└─ Late submission: Rejected automatically

Number of Copies:
├─ Technical proposal: 5 copies (1 original + 4 copies)
├─ Financial proposal: 3 copies (1 original + 2 copies)
├─ All documents: Original signatures & company seal
└─ Originals verified: Notarized copies acceptable

Document Language:
├─ All documents: Thai language (required)
├─ English: Optional (for additional clarity)
├─ Translation: If English provided, must match Thai (certified)
└─ Format: PDF (preferred) + hardcopy

Submission Address:
├─ Location: [Government address to be specified]
├─ Deadline: [Date/Time to be announced]
├─ Submission: Hand delivery or courier (with tracking)
├─ Late receipt: Not accepted (even if mailed on time)
└─ Confirmation: Bidder receives acknowledgment receipt

I. EVALUATION OF DOCUMENTS

Process:
├─ Completeness check: All required documents present?
├─ Responsiveness: Proposal addresses requirements?
├─ Compliance: Meets all TOR specifications?
├─ Quality: Professional presentation & clarity?
└─ Deficiencies: Opportunity to clarify (48-hour extension)

Missing Documents:
├─ Vendor has 48 hours to submit missing items
├─ If not submitted: Disqualified automatically
├─ Exception: Minor/non-material documents waived by committee
└─ Late submission of missing docs: Not accepted

Clarification Questions:
├─ Committee may ask for clarifications
├─ Vendor has 48-72 hours to respond
├─ Answers: In writing (email OK, no price changes)
└─ Material changes: Require re-evaluation

J. DOCUMENT RETENTION

Government retains all submitted documents:
├─ Duration: 5 years minimum (regulatory requirement)
├─ Purpose: Audit trail, legal protection
├─ Access: Only authorized personnel
├─ Confidentiality: Respect bidder confidential information
└─ Return: After retention period, government can destroy
```
---

**ใช้เอกสารนี้สำหรับ:**
1. ✅ **ร่าง TOR** - ใช้ตัวอย่างโดยตรง เปลี่ยนแต่ตัวเลขและบริบท
2. ✅ **ฝึกอบรม Team** - ให้ทีมอ่านเข้าใจรายละเอียด
3. ✅ **ตรวจสอบ TOR** - ใช้ Checklist ในแต่ละส่วน
4. ✅ **เจรจา Bidders** - ใช้ข้อมูลนี้ตอบคำถาม/ชี้แจง
5. ✅ **จัดการ Project** - ใช้ Timeline, Milestone, Payment Schedule ข้างต้น

---

### 🎯 สิ่งที่สำคัญต้องจำ

1. **Specificity**: ทุกๆ ข้อต้องเป็นรูปธรรม ไม่ขาดแต่คำนิยาม
2. **Measurable**: ต้องมีตัวเลข สถิติ หลักฐาน
3. **Reasonable**: ไม่แคบเกินจนประหยาดสร้างเสรรค์ แต่ไม่กว้างเกินจนลืมความต้องการ
4. **Complete**: ครบถ้วนทุกมิติ ตัวเลข ช่วงเวลา บุคลากร
5. **Aligned**: ทั้ง 10 ส่วนต้องสอดประสานกัน (Section 2 ← Section 1, Section 3 ← Section 1-2, ฯลฯ)

---

**ต่อไปอ่าน**: เอกสารส่วนที่ 2 เกี่ยวกับ "ขั้นตอนการร่าง" แบบละเอียด
