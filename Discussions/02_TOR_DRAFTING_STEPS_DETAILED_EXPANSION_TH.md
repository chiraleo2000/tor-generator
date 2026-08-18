# ขั้นตอนการร่าง TOR แบบละเอียดทีละขั้น
## 4 Phase รายการบ่อยครั้ง ตัวอย่าง ปัญหา ทำแบบไหน

---

## 📅 ภาพรวมเวลาและ Phase ทั้งหมด

```
เวลา: 3-6 สัปดาห์ (ไม่รวม Approval ของผู้บริหาร)

PHASE 0: PRE-DRAFTING (1-2 สัปดาห์ก่อนร่าง)
├─ Task: รวบรวมเอกสาร, ประชุม, อนุมัติข้อมูล
├─ Output: เอกสารพื้นฐาน 11 ฉบับ, Meeting Minutes
└─ Success Criteria: ได้ Approval ให้เริ่มร่าง

PHASE 1: ANALYSIS (Week 1, 1 สัปดาห์)
├─ Task: ศึกษาเอกสาร, ถาม, วิเคราะห์ Requirements
├─ Output: Q&A Log, Requirements List, Specifications
└─ Success Criteria: ความเข้าใจ 100% ก่อนร่าง

PHASE 2: DRAFTING (Week 2-3, 1.5-2 สัปดาห์)
├─ Task: เขียน TOR ส่วนที่ 1-10
├─ Output: Draft TOR 6000-8500 คำ
└─ Success Criteria: ร่างครั้งแรก ไม่มี Placeholder

PHASE 3: REVIEW & REVISE (Week 4-5, 1.5-2 สัปดาห์)
├─ Task: ทบทวน แก้ไข อนุมัติ
├─ Output: Final TOR ที่ได้ Management Approval
└─ Success Criteria: Management Approved ✅

PHASE 4: PUBLISHING (1-2 วัน)
├─ Task: Final Check, Format, Upload
├─ Output: TOR ลงในระบบ e-Bidding
└─ Success Criteria: Public Announcement ได้
```

---

## 🔧 PHASE 0: เตรียมข้อมูลตั้งต้น (Pre-Drafting) - 1-2 สัปดาห์

### ขั้นที่ 0.1: รวบรวมเอกสารพื้นฐาน (Day 1-3)

#### **Task 0.1.1: เก็บเอกสารเกี่ยวกับ Approval & Budget**

**เอกสารที่ต้องหา:**

| # | เอกสาร | ไฟล์/หลักฐาน | สถานะ | หมายเหตุ |
|---|--------|----------|-------|---------|
| 1 | Announced Price (ประกาศราคากลาง) | ประกาศราคากลาง official | ☐ | ต้องใช้เป็นข้อมูล Section 7 |
| 2 | Budget Approval Document | Resolution/Memo from Finance | ☐ | บอก: ว่าอนุมัติให้ใช้งบ |
| 3 | Fiscal Year | Document from Finance | ☐ | ตัวอย่าง: FY 2570 |
| 4 | Project Charter (ถ้ามี) | Initial Project Document | ☐ | บอก: Project Goals |
| 5 | Sponsor Endorsement | Letter/Memo from Project Sponsor | ☐ | บอก: Sponsor ยอมรับโครงการ |

**How to Get:**
```
1. ติดต่อ Finance Officer ขอ:
   └─ Announced Price Certification Letter
   └─ Budget Allocation Letter
   └─ Fiscal Year Confirmation

2. ติดต่อ Sponsor ขอ:
   └─ Project Charter (ถ้ามี)
   └─ Initial Scope Document
   └─ Approval Letter เพื่อเริ่มร่าง TOR

3. เก็บไฟล์ใน Folder:
   └─ /TOR_Project/Phase_0/Budget_Documents/
```

#### **Task 0.1.2: เก็บเอกสารเกี่ยวกับ Project**

| # | เอกสาร | หลักฐาน | สถานะ |
|---|--------|---------|-------|
| 1 | Project Proposal / Brief | เอกสารข้างต้นที่บอกว่า "ต้องทำอะไร" | ☐ |
| 2 | Current System Documentation | เอกสารระบบเดิม, Flow Diagram | ☐ |
| 3 | Problem Statement | บอกว่า "มีปัญหาอะไร" | ☐ |
| 4 | Stakeholder List | ชื่อ, โทรศัพท์ผู้เกี่ยวข้อง | ☐ |
| 5 | Policy Documents | นโยบายสูงสุด, Strategy Documents | ☐ |
| 6 | Hardware/Software Inventory | บัญชี Servers, License (ถ้ามี) | ☐ |
| 7 | Budget Breakdown (Preliminary) | งบกำหนดแบ่ง: SW/HW/Services | ☐ |
| 8 | Timeline Requirements | ตั้งแต่เมื่อ-ถึงเมื่อ | ☐ |

**How to Get:**
```
ติดต่อ:
- IT Manager: Hardware/Software Inventory, Current System Docs
- Project Sponsor: Problem Statement, Timeline
- Policy Officer: Related Policies
- Finance: Budget Breakdown

ช่องทาง: Email + Meeting (ไม่ต้องรอ อาจต้อง Clarify ข้อมูล)
```

#### **Task 0.1.3: เตรียม e-Bidding Documents (ร่างเบื้องต้น)**

| # | เอกสาร | ผู้รับผิดชอบ | หมายเหตุ |
|---|--------|----------|---------|
| 1 | E-Bidding Tender Document (Draft) | Procurement Officer | เอกสารประกวดราคา |
| 2 | Technical Specification (Draft) | Technical Officer | Spec ของ HW/SW |
| 3 | Bill of Quantities (ถ้ามี) | Procurement | รายการที่ต้องการ |

**How to Prepare:**
```
สำหรับ Procurement Officer:
1. ใช้ Template จาก Previous TOR (ถ้ามี)
2. ระบุ: Contract Type, Duration, Budget
3. บันทึก: Submission & Evaluation Timeline
4. เตรียม: Scoring Criteria (ร่าง)
```

---

### ขั้นที่ 0.2: ประชุม Kickoff & Requirement Clarification (Day 3-5)

#### **Meeting #1: Kickoff & Requirement Clarification Meeting**

**Timing:** Day 3-5 (หลังได้ Documents แล้ว)

**Duration:** 2-3 ชั่วโมง (แบ่งเป็น 2-3 sessions)

**Attendees (ต้องลงนาม Minutes):**
```
1. Project Sponsor (Chairperson)
2. End-users Representative (1-2 คน สำคัญที่สุด)
3. IT Manager / System Admin
4. Procurement Officer
5. Finance Officer
6. TOR Drafting Team Lead (Scribe - คนที่จดบันทึก)
```

**Agenda & Detailed Discussion Points:**

```
========== SESSION 1: CONTEXT & SCOPE (30-45 นาที) ==========

1.1 Background Briefing (15 นาที)
└─ Sponsor/PM อธิบาย:
   ├─ "ทำไมถึงต้องจัดจ้างนี้?"
   ├─ "ปัญหาปัจจุบันคืออะไร? (specific, not generic)"
   ├─ "พยายามแก้ยังไงบ้าง? (past attempts)"
   └─ "เป้าหมายสุดท้ายคืออะไร?"
   
   📝 Record: ใจความสำคัญทั้งหมด (ไม่จำเป็นต้องเขียนทุกคำ)

1.2 Stakeholders Introduction (15 นาที)
└─ ทุกคน introduce ตัวเอง:
   ├─ "ชื่อ, หน้าที่, interest ในโครงการ"
   ├─ "หน้าที่ที่ต้อง Interact กับ TOR"
   └─ Contact Details (Phone/Email)

   📝 Record: ใครรับผิดชอบอะไร
   💾 Create: Contact List for Future Reference

1.3 Objectives Alignment (15 นาที)
└─ Sponsor ชี้แจง Objectives ที่คาดหวัง:
   ├─ "Success Criteria คืออะไร?"
   ├─ "ประมาณการเกี่ยวกับ Timeline/Budget?"
   └─ "มี Constraints หรือ Assumptions อะไร?"
   
   📝 Record: ทั้งหมด ลงสมุด/Form


========== SESSION 2: DETAILED SCOPE DISCUSSION (60-75 นาที) ==========

2.1 Current System Deep Dive (20 นาที)
└─ IT Manager/System Admin อธิบายระบบเดิม:
   ├─ "Architecture เป็นยังไง?"
   ├─ "Hardware/Software Specs?"
   ├─ "Performance Issues? (Uptime, Response time, Capacity)"
   ├─ "Integration Points? (ระบบอื่นที่เชื่อมต่อ)"
   └─ "Known Limitations? (ไม่รองรับ...)"

   ❓ Ask More Questions:
      - "ปัญหากำหนดมาจากไหน? (เก่ามากมั้ย)"
      - "สามารถอัพเกรดระบบเดิมได้หรือ? (ทำไมต้องใหม่)"
      - "มีผู้ใช้ที่ไหน? (Location, Time Zone)"
      - "Support Hours คืออะไร? (24/7 หรือ Business Hours)"

   📝 Record: Architecture Sketch, Detailed Issues, Performance Metrics

2.2 Requirements & Desired Features (25 นาที)
└─ End-users บอก "เอากะไร":
   ├─ "What are the TOP 3 Must-Have Features?"
   ├─ "What is currently NOT possible? (ทำไมเสี่ยง)"
   ├─ "Performance expectation? (Response time, Uptime)"
   ├─ "Scalability needs? (how many users/transactions per day)"
   ├─ "Integration requirements? (ต้องต่อกับระบบอื่นไหม)"
   └─ "Data/Security concerns?"

   ❓ Challenge them:
      - "ถ้าเลือก 3 features สำคัญ Features อื่นจะทิ้งได้หรือ?"
      - "ความเร็ว Target เท่าไหร่? (ตัวเลข ไม่ใช่ 'เร็ว')"
      - "ต้อง 24/7 support หรือ Business Hours พอ?"

   📝 Record: Requirements List ตามหมวด (Functional, Non-Functional, Operational)

2.3 Timeline & Budget Expectation (10 นาที)
└─ Sponsor ยืนยัน:
   ├─ "Go-Live ต้องเมื่อไหร่? (Fixed หรือ Flexible?)"
   ├─ "Budget ซึ่ง 93M ตัวไหน? (ตาม Announced Price?)"
   ├─ "มี Constraints อื่นไหม? (e.g., must use local vendor, must complete before year-end)"
   └─ "Payment schedule preference?"

   📝 Record: Hard deadline vs Flexible


========== SESSION 3: PLANNING & NEXT STEPS (15-30 นาที) ==========

3.1 TOR Drafting Approach (10 นาที)
└─ TOR Team อธิบาย:
   ├─ "จะร่าง 4 Phase"
   ├─ "Timeline ประมาณ 5-6 สัปดาห์"
   ├─ "ต้องมี Data Gathering Meeting อีก 1 ครั้ง"
   ├─ "Stakeholder Review Meeting ระหว่างร่าง"
   └─ "Expected deliverables"

3.2 Data Gathering Requirements (10 นาที)
└─ บอก IT Manager/System Admin:
   ├─ "ต้องเตรียมข้อมูล: Hardware Inventory, Software License List"
   ├─ "Performance Data: Current uptime %, response time, user count"
   ├─ "Man-days estimate: ประมาณใช้คนกี่คน"
   └─ "Data Migration needs: ข้อมูลจากระบบเดิมต้อง Migrate หรือไม่"

3.3 Decision Points & Approvals (10 นาที)
└─ Sponsor confirm:
   ├─ "ใครทำเป็น Project Owner? (ผู้ลงนาม TOR)"
   ├─ "ใครเป็น Primary Contact? (สำหรับคำถามระหว่างร่าง)"
   └─ "เมื่อไหร่จะจัด Review Meeting ครั้งต่อไป?"
```

**Meeting Output (Deliverables):**
```
1️⃣ Meeting Minutes (3-5 หน้า)
   ├─ Attendees (ชื่อ ตำแหน่ง ลายมือชื่อ)
   ├─ Date/Time/Location
   ├─ Agenda items + Discussion summary
   ├─ Decisions made
   └─ Action items with owners & deadlines

2️⃣ Requirements Summary (Draft)
   ├─ Background/Problem Summary (1 page)
   ├─ Key Objectives (bullet points)
   ├─ Must-Have vs Nice-to-Have Features
   └─ Top Risks/Assumptions

3️⃣ Scope Boundaries Document
   ├─ In Scope: อะไรที่ต้องทำ
   ├─ Out of Scope: อะไรที่ไม่รวม (สำคัญ! ป้องกันมี Dispute)
   └─ Constraints: Timeline, Budget, Other

4️⃣ Contact List
   └─ Name, Title, Phone, Email of all stakeholders

5️⃣ Data Gathering Checklist
   └─ List of information needed for Phase 1
```

**📋 Template Meeting Minutes:**
```
═══════════════════════════════════════════════════════════
        TOR DRAFTING KICKOFF MEETING MINUTES
═══════════════════════════════════════════════════════════

Project: e-Payment System Modernization
Date: 1 August 2569, 10:00-12:30
Location: Conference Room A, Ministry of Revenue
Facilitator: [TOR Lead Name]
Scribe: [Note Taker Name]

ATTENDEES:
┌─────────────────────────────────────────────────────┐
│ Name          │ Title                    │ Signature │
├─────────────────────────────────────────────────────┤
│ Mr. Somchai   │ Deputy Director (Sponsor) │ _________ │
│ Ms. Noi       │ System Admin             │ _________ │
│ Mr. Ananda    │ Finance Officer          │ _________ │
│ Ms. Pranee    │ IT Manager               │ _________ │
│ Mr. Nithi     │ Procurement Officer      │ _________ │
│ Ms. Suda      │ TOR Team Lead            │ _________ │
└─────────────────────────────────────────────────────┘

AGENDA & DISCUSSIONS:

1. PROJECT BACKGROUND (Discussed by: Mr. Somchai)
   - Current system: e-Payment developed in 2560, now 9 years old
   - Problem: 95% uptime, response time 5-10 sec, can't handle growth
   - Goal: Modernize to support 500 users, 99.9% uptime, <2 sec response
   - Timeline: Must go-live before end of FY 2570 (September 2570)

2. STAKEHOLDERS INTRODUCTION
   [List of participants and their roles]

3. REQUIREMENTS DISCUSSION (Discussed by: Ms. Noi + Team)
   
   Must-Have Features:
   ✓ Increase performance: Response < 2 seconds
   ✓ Increase uptime: 99.9%
   ✓ Support 500 concurrent users
   ✓ Add mobile app support
   ✓ Implement ISO 27001 security
   
   Nice-to-Have:
   - Multi-currency support
   - Advanced reporting
   - Machine Learning for fraud detection

4. CURRENT SYSTEM DETAILS
   - Architecture: Monolithic .NET on Windows Server 2016
   - Hardware: 1 web server, 1 DB server, 100 Mbps network
   - Database: SQL Server 2012 (outdated, needs upgrade)
   - Performance Issues:
     * CPU spikes to 90% during peak hours (10am-2pm)
     * Memory leak every 5-7 days
     * Slow queries (some taking 30+ seconds)
   
5. TIMELINE & BUDGET
   ✓ Budget: 93,004,500 baht (as per Announced Price)
   ✓ Duration: 12 months (Oct 2569 - Sep 2570)
   ✓ Go-Live: By September 2570
   ✓ Vendor selection: Q4 2569

6. NEXT STEPS & DATA GATHERING
   - Data Gathering Meeting: 5 August 2569 (Day 3)
   - Need IT to provide:
     * Detailed Hardware Inventory (with specs)
     * Software License List
     * Performance Metrics (6-month data)
     * Man-days estimate
   
DECISIONS MADE:
☑ Proceed with TOR drafting
☑ Schedule Data Gathering Meeting for 5 Aug
☑ Project Sponsor: Mr. Somchai
☑ Primary Contact: Ms. Pranee (IT Manager)
☑ Stakeholder Review Meeting: Tentatively Week 3

ACTION ITEMS:
┌────────────────────────────────────────────────────────┐
│ Item  │ Owner        │ Deadline   │ Status │ Notes    │
├────────────────────────────────────────────────────────┤
│ 1     │ Ms. Noi      │ 5 Aug      │ ☐      │ Hw Inv  │
│ 2     │ Ms. Pranee   │ 5 Aug      │ ☐      │ Perf    │
│ 3     │ Ms. Suda     │ 7 Aug      │ ☐      │ Draft   │
│ 4     │ Mr. Somchai  │ 6 Aug      │ ☐      │ Budget  │
└────────────────────────────────────────────────────────┘

Prepared by: Ms. Suda
Approved by: Mr. Somchai (Sponsor)
Date: 1 August 2569
```

---

#### **Meeting #2: Data Gathering Meeting**

**Timing:** Day 5-7 (หลังจาก Kickoff Meeting 2-3 วัน)

**Duration:** 1.5-2 ชั่วโมง

**Attendees:**
```
1. System Admin / IT Operations Manager (ผู้ให้ข้อมูล)
2. Database Administrator (สำหรับ DB Specs)
3. Network Administrator (สำหรับ Network Specs)
4. Finance Officer (สำหรับ Cost Estimates)
5. TOR Team Lead (Record & Clarify)
```

**Data to Collect (ต้อง Specific & Detailed):**

```
════════════════════════════════════════════════════════════
SECTION 1: HARDWARE INVENTORY (สำคัญ!)
════════════════════════════════════════════════════════════

Requirement: Bill of Materials (BOM) ของระบบปัจจุบัน

Data Points (must have):
├─ Server Types: Web Server, Database, File Server, etc.
│  └─ Qty, Brand/Model, Processor Type, Cores, RAM, Storage Size
│
├─ Network Equipment: Switch, Router, Firewall, Load Balancer
│  └─ Qty, Model, Throughput, Ports, Management Method
│
├─ Storage: SAN, NAS, Tape Backup, Disaster Recovery
│  └─ Capacity, Type (SSD/HDD), Replication Method
│
├─ Disaster Recovery: Remote Site Availability?
│  └─ Do you have DR site? Distance? Connection Type?
│
└─ Current Utilization: Hardware ปัจจุบันใช้งานแค่ไหน?
   └─ CPU: Average %, Peak %
   └─ Memory: Average GB, Peak GB
   └─ Storage: Current GB used, Growth per month
   └─ Network: Average Mbps, Peak Mbps

Example Output (Table):

| Component | Current | Qty | Brand/Model | Processor | RAM | Storage |
|-----------|---------|-----|------------|-----------|-----|---------|
| Web Server | Yes | 1 | Lenovo | Intel Xeon 4-core | 16GB | 500GB |
| DB Server | Yes | 1 | Dell | Intel Xeon 8-core | 32GB | 1TB |
| Switch | Yes | 2 | Cisco | 2960 | - | - |
| Firewall | Yes | 1 | Palo Alto | PA-1000 | - | - |
| Storage | Yes | 1 | HP | SAN 100TB | - | 100TB |
| Network | 100 Mbps | N/A | Fiber to ISP | - | - | - |


════════════════════════════════════════════════════════════
SECTION 2: SOFTWARE & LICENSES
════════════════════════════════════════════════════════════

Requirement: โปรแกรมและ License ที่ใช้งานอยู่

Data Points:
├─ Operating Systems: Windows Server version, Linux version
│  └─ License Type, Number of Licenses
│
├─ Database: Type (SQL Server, Oracle, PostgreSQL), Version
│  └─ License Type, Number, Cost
│
├─ Application Middleware: Java, .NET, Apache, Tomcat
│  └─ Version, License Type
│
├─ Commercial Software: Any paid software?
│  └─ Product Name, License Type (Perpetual/Subscription), Cost
│
└─ Support Contracts: Any active support contracts?
   └─ Product, Vendor, End Date, Cost

Example Output:

| Software | Version | License Type | Qty | Cost | Expiry |
|----------|---------|--------------|-----|------|--------|
| Windows Server | 2016 | Standard | 2 | $3,600 | 2026 |
| SQL Server | 2012 | Standard | 1 | $5,000 | - |
| .NET Framework | 4.5 | Perpetual | - | - | - |
| IIS | 10 | Included | - | - | - |


════════════════════════════════════════════════════════════
SECTION 3: PERFORMANCE & USAGE DATA
════════════════════════════════════════════════════════════

Requirement: ข้อมูลสถิติการใช้งานจากที่ผ่านมา

Must Have (ย้อนหลัง 3-6 เดือน):
├─ User Statistics:
│  ├─ Concurrent Users: Average, Peak (at what time of day?)
│  ├─ Daily Transactions: Average, Peak
│  ├─ Monthly Active Users
│  └─ Growth Trend: % increase per month
│
├─ System Uptime:
│  ├─ Monthly Availability: % (Target: 99.9% = 43.2 min downtime/month)
│  ├─ Incidents: Frequency, Duration, Root Cause
│  ├─ Planned Maintenance: How often? How long?
│  └─ Unplanned Downtime: Reasons
│
├─ Performance Metrics:
│  ├─ Average Response Time: How many seconds?
│  ├─ 95th Percentile Response Time: (Peak traffic response time)
│  ├─ Transaction Success Rate: % (Target: 99.5%)
│  ├─ Error Rate: % of failed transactions
│  └─ API Call Volume: if applicable
│
├─ Resource Utilization:
│  ├─ CPU: Average %, Peak %, When peak?
│  ├─ Memory: Average GB, Peak GB, Growth trend
│  ├─ Disk I/O: IOPS, Latency
│  ├─ Network Bandwidth: Average Mbps, Peak Mbps
│  └─ Database: Query count per second, Slow queries identified?
│
└─ Issues Log:
   ├─ Known Issues & their frequency
   ├─ Performance Bottlenecks
   ├─ Storage bottlenecks
   ├─ Scalability limits
   └─ Security concerns

Example Output:

Daily Transactions:
├─ Average: 1,000 transactions/day
├─ Peak: 3,000 transactions/day (noon time)
└─ Growth: +15% per month

System Uptime:
├─ July: 94.2% (downtime: 10.7 hours)
├─ June: 96.1% (downtime: 5.9 hours)
├─ May: 92.3% (downtime: 18.3 hours) - Major DB crash
└─ Trend: Declining

Response Time:
├─ Average: 7.3 seconds
├─ 95th Percentile: 12.5 seconds
├─ Peak hour (12pm): 15 seconds
└─ Target: 2 seconds (MUCH NEEDED)


════════════════════════════════════════════════════════════
SECTION 4: INTEGRATION POINTS & DEPENDENCIES
════════════════════════════════════════════════════════════

Requirement: ระบบอื่นที่เชื่อมต่อ

Data Points:
├─ Systems that SEND data to this system
│  └─ System Name, Connection Type (Direct DB, API, File transfer), Frequency
│
├─ Systems that RECEIVE data from this system
│  └─ System Name, Connection Type, Data Format, Frequency
│
├─ External Services/APIs:
│  └─ Service Name (e.g., payment gateway), Provider, SLA
│
├─ Data Migration Needs:
│  └─ Will old data need to migrate? Volume? Important?
│
└─ User Access Methods:
   ├─ Web Portal (Desktop)
   ├─ Mobile App (if applicable)
   ├─ API Access (if applicable)
   └─ File Uploads/Downloads

Example:

Integration Diagram:
┌──────────────────────────┐
│   e-Payment System       │
├──────────────────────────┤
│  Integration Points:     │
├──────────────────────────┤
│ 1. Bank API              │ (Outbound) Real-time payment status
│ 2. Ministry of Commerce  │ (Inbound) Tax data
│ 3. Treasury System       │ (Outbound) Settlement data
│ 4. Email Server          │ (Outbound) Transaction notifications
│ 5. Reporting System      │ (Inbound) Request for reports
└──────────────────────────┘


════════════════════════════════════════════════════════════
SECTION 5: ESTIMATE MAN-DAYS / EFFORT
════════════════════════════════════════════════════════════

Requirement: Rough estimate ของ effort needed

For Sponsor/PM to estimate:
├─ Based on similar projects in the past
├─ Breakdown: Analysis, Design, Development, Testing, Training
├─ Consider: Team size, complexity, timeline constraints
└─ Output: Total man-days estimate (rough)

Example:
Total Effort: ~3,500 man-days over 12 months
├─ Analysis & Design: 600 man-days (Month 1-2.5)
├─ Development: 1,400 man-days (Month 2-8)
├─ Testing: 600 man-days (Month 6-9)
├─ Training & Documentation: 300 man-days (Month 8-11)
├─ Go-Live & Support: 400 man-days (Month 10-12)
└─ Contingency: 200 man-days


════════════════════════════════════════════════════════════
SECTION 6: ORGANIZATIONAL STRUCTURE & CONTACTS
════════════════════════════════════════════════════════════

Requirement: List of key contacts & approvers

Who needs to approve what during project:
├─ IT Director: Technical decisions
├─ Finance Director: Budget changes
├─ Project Sponsor: Overall approval
├─ End-user Representatives: Functional requirements
├─ Security Officer: Security-related decisions
└─ Compliance Officer: Regulatory approvals

Contact List:
┌─────────────────────────────────────────────────────┐
│ Role               │ Name      │ Phone      │ Email  │
├─────────────────────────────────────────────────────┤
│ Project Sponsor    │ Somchai   │ 02-xxx-001 │ s@... │
│ Technical Decision │ Pranee    │ 02-xxx-002 │ p@... │
│ End-user Rep       │ Ananda    │ 02-xxx-003 │ a@... │
│ Finance Approver   │ Noi       │ 02-xxx-004 │ n@... │
└─────────────────────────────────────────────────────┘
```

**Meeting Output (Deliverables):**
```
1️⃣ Hardware & Software Inventory Report
   └─ Complete list with specs (1-2 pages)

2️⃣ Performance Metrics Summary
   └─ Current statistics & SLA gaps (1 page)

3️⃣ Integration Points Diagram
   └─ Data flow between systems (1 diagram)

4️⃣ Effort Estimation
   └─ Total man-days estimate (1 page)

5️⃣ Organizational Structure & Contact List
   └─ Complete contact information
```

---

### ขั้นที่ 0.3: อนุมัติความพร้อม Phase 0

**Checklist ก่อนจบ Phase 0:**

```
✅ MUST-HAVE (ต้องมี ไม่ได้ละ):

☐ 1. Budget Approval Document
      └─ สถาบัน Finance/Management อนุมัติให้ใช้งบ

☐ 2. Announced Price Official
      └─ ประกาศราคากลาง + สมอดุกทรรง + Certificate

☐ 3. Project Charter / Scope Document
      └─ Sponsor ลงนามว่าเห็นด้วย Scope & Timeline

☐ 4. Kickoff Meeting Minutes
      └─ ทุก Attendee ลงนาม, ประกอบจด Decisions

☐ 5. Requirements Summary (Draft)
      └─ Key Objectives, Must-Have Features

☐ 6. Hardware & Software Inventory
      └─ Complete list with current specs

☐ 7. Performance Data (3-6 months)
      └─ Uptime %, Response Time, User Count

☐ 8. Integration Points Documented
      └─ List of systems that connect

☐ 9. Effort Estimation
      └─ Man-days estimate from IT

☐ 10. Stakeholder List with Contacts
       └─ Name, Phone, Email, Role

☐ 11. TOR Drafting Team Assigned
       └─ Team Lead, Writers, Reviewers identified


✅ NICE-TO-HAVE (ควรมี):

☐ 1. Preliminary Budget Breakdown
      └─ SW, HW, Services allocation

☐ 2. Similar Project References
      └─ Case studies from past projects

☐ 3. Preliminary Timeline
      └─ High-level schedule

☐ 4. Risk Identification
      └─ Preliminary list of risks
```

**Sign-Off Checkpoint:**

```
When all MUST-HAVE items ready:
1. Sponsor signs off: "Ready to proceed with Phase 1"
2. TOR Lead confirms: "Got all data needed"
3. Kickoff Phase 1

If any item missing:
→ STOP, don't proceed
→ Collect missing information
→ Re-check before proceeding
```

---

## 📖 PHASE 1: วิเคราะห์ความต้องการ (Analysis) - 1 สัปดาห์

### ขั้นที่ 1.1: ศึกษาเอกสารรายละเอียด (Day 1-2)

**Task: อ่านและเข้าใจเอกสาร ทั้งหมด**

```
Reading List (in priority order):

MUST READ:
1. Project Proposal / Charter
   └─ Time: 30 min, Purpose: Understand business context
   └─ Record: Key objectives, stakeholders

2. Current System Documentation
   └─ Time: 60 min, Purpose: Understand As-Is system
   └─ Record: Architecture, issues, constraints

3. Requirements Summary (from Kickoff)
   └─ Time: 30 min, Purpose: What's needed
   └─ Record: Must-Have vs Nice-to-Have

4. Policy Documents
   └─ Time: 45 min, Purpose: Government requirements
   └─ Record: Compliance needs

5. Budget & Timeline Documents
   └─ Time: 20 min, Purpose: Financial & schedule constraints
   └─ Record: Budget breakdown, milestones

SHOULD READ:
6. Similar Project Case Studies
   └─ Time: 60 min, Purpose: Learn from past
   └─ Record: What worked, what didn't

7. Hardware/Software Inventory
   └─ Time: 30 min, Purpose: Technical foundation
   └─ Record: Current state, upgrade needs

Total Time: ~4 hours


Activity: Create "Reading Notes" Document
├─ Template columns:
│  ├─ Source Document
│  ├─ Key Findings (bullet points)
│  ├─ Questions/Clarifications Needed
│  ├─ Constraints/Assumptions
│  └─ Impact on TOR
│
└─ Example Entry:
   Document: Current System Architecture
   Key Finding: System is monolithic .NET on Windows Server 2016
   Question: Can we modernize to cloud-native or must stay on-premises?
   Constraint: 2 years old, support ending in 2026
   Impact on TOR: Section 4.2 must specify new architecture
```

---

### ขั้นที่ 1.2: ถามข้อสงสัยและชี้แจง (Day 2-3)

**Task: Clarification Questions & Interviews**

```
Interview Sessions (30 min each, 1-on-1):

SESSION 1: IT Manager/System Admin
├─ Topic: Current System Deep Dive
├─ Questions:
│  ├─ "What are the top 3 performance issues?"
│  ├─ "Can you show me the architecture diagram?"
│  ├─ "How often does the system go down? Why?"
│  ├─ "What's the data volume growth rate?"
│  ├─ "Do you have monitoring/logging?"
│  ├─ "What's the backup/recovery process?"
│  └─ "Can the current system be scaled up?"
│
└─ Document: System Deep Dive Notes (2-3 pages)

SESSION 2: End-User Representatives
├─ Topic: Functional Requirements & Pain Points
├─ Questions:
│  ├─ "What do you do with the system daily?"
│  ├─ "What's NOT possible now that you need?"
│  ├─ "How many users access at peak time?"
│  ├─ "What features would make your job 10x easier?"
│  ├─ "Are there any security/compliance concerns?"
│  ├─ "What's the worst outage you've experienced?"
│  └─ "If you had to rank improvements, what's #1?"
│
└─ Document: User Requirements Summary (2-3 pages)

SESSION 3: Finance Officer
├─ Topic: Budget, Cost Estimates, Payment Timeline
├─ Questions:
│  ├─ "How was the budget of 93M calculated?"
│  ├─ "Is this budget fixed or can it increase?"
│  ├─ "What are the top cost drivers?"
│  ├─ "Preferred payment schedule?"
│  ├─ "Any cost constraints on specific areas?"
│  └─ "What's the ROI expectation?"
│
└─ Document: Budget Clarification Notes (1 page)

SESSION 4: Project Sponsor
├─ Topic: Overall Goals, Constraints, Success Criteria
├─ Questions:
│  ├─ "What does SUCCESS look like for this project?"
│  ├─ "What's the #1 risk if we fail?"
│  ├─ "Are there any political/organizational constraints?"
│  ├─ "Who is the Executive Sponsor? Are they fully committed?"
│  ├─ "Will there be organizational changes?"
│  └─ "What's the post-project support plan?"
│
└─ Document: Sponsor Alignment Notes (1-2 pages)

Create Q&A Log:
┌─────────────────────────────────────────────────────────┐
│ # │ Question           │ Asked to │ Answer │ Date │ Impact│
├─────────────────────────────────────────────────────────┤
│1  │ Current uptime %   │ IT Mgr   │ 95%    │ 2Aug │ High  │
│2  │ Top pain point     │ User     │ Speed  │ 3Aug │ High  │
│3  │ Budget flexibility │ Finance  │ Fixed  │ 3Aug │ Medium│
│...│                    │          │        │      │       │
└─────────────────────────────────────────────────────────┘
```

---

### ขั้นที่ 1.3: วิเคราะห์และจัดกลุ่ม Requirements (Day 3-4)

**Task: Organize Requirements by Type**

```
CREATE: REQUIREMENTS MATRIX

Template:
┌────────────────────────────────────────────────────────────┐
│ Requirement ID: REQ-001                                     │
│ Type: FUNCTIONAL                                            │
│ Category: Performance                                       │
│ Priority: HIGH                                              │
├────────────────────────────────────────────────────────────┤
│ Requirement:                                                │
│ "System must support 500 concurrent users with <2 sec     │
│  response time for all transactions"                        │
│                                                             │
│ Rationale:                                                  │
│ Current system can only handle 100 users and is slow       │
│ (5-10 sec). User growth is 15% per month.                  │
│                                                             │
│ Acceptance Criteria:                                        │
│ - Load test with 500 concurrent users must pass           │
│ - 90th percentile response time < 2 seconds                │
│ - No errors during sustained load                          │
│                                                             │
│ Related Sections (in TOR):                                  │
│ - Section 2 (Objectives): Objective #1                     │
│ - Section 4.3 (Tasks): Performance optimization task      │
│ - Section 4.8 (Deliverables): Load test report            │
│                                                             │
│ Source: Kickoff meeting + User interviews                  │
│ Assigned to: System Architect                              │
│ Status: ☐ Confirmed ☑ Tentative                           │
└────────────────────────────────────────────────────────────┘

EXAMPLE FULL REQUIREMENTS MATRIX:

FUNCTIONAL REQUIREMENTS (What the system must DO):
├─ REQ-F001: Online Payment Processing
├─ REQ-F002: Mobile App Interface
├─ REQ-F003: Real-time Reporting
├─ REQ-F004: User Role Management (Admin, Officer, Viewer)
├─ REQ-F005: Payment Method Support (Bank Transfer, E-wallet, Card)
├─ REQ-F006: Data Export (CSV, Excel, PDF)
└─ REQ-F007: Audit Trail & Logging of all transactions

NON-FUNCTIONAL REQUIREMENTS (How the system must DO it):
├─ REQ-NF001: Performance: <2 sec response time (90th percentile)
├─ REQ-NF002: Availability: 99.9% uptime (43.2 min downtime/month max)
├─ REQ-NF003: Scalability: Support 500 concurrent users
├─ REQ-NF004: Security: ISO 27001 compliance
├─ REQ-NF005: Data Protection: AES-256 encryption
├─ REQ-NF006: Disaster Recovery: RTO 4 hours, RPO 1 hour
├─ REQ-NF007: Compatibility: Support Chrome, Firefox, Safari, Edge
└─ REQ-NF008: Localization: All UI text in Thai

OPERATIONAL REQUIREMENTS (How to maintain/support it):
├─ REQ-OP001: 24/7 monitoring with automated alerts
├─ REQ-OP002: Automated daily backups with weekly tested restore
├─ REQ-OP003: Monthly security patches within 48 hours of release
├─ REQ-OP004: Quarterly performance review & optimization
├─ REQ-OP005: Annual penetration testing
├─ REQ-OP006: Documentation in Thai & English
├─ REQ-OP007: Training for 20 internal staff
└─ REQ-OP008: Transition plan: knowledge handover by month 11

CONSTRAINTS & ASSUMPTIONS:
├─ CONSTRAINT-1: Budget is fixed at 93,004,500 baht
├─ CONSTRAINT-2: Timeline: Must go-live by September 30, 2570
├─ CONSTRAINT-3: Must maintain backward compatibility with legacy data
├─ CONSTRAINT-4: Key Personnel cannot be changed without approval
├─ ASSUMPTION-1: Current hardware can be repurposed/upgraded
├─ ASSUMPTION-2: Data migration time < 48 hours
├─ ASSUMPTION-3: No user acceptance training issues
└─ ASSUMPTION-4: Government regulations won't change during project
```

---

### ขั้นที่ 1.4: สรุปและเตรียม Specification (Day 4-5)

**Task: Create Detailed Specification Document**

```
OUTPUT DOCUMENT: "Phase 1 Analysis Report" (15-20 pages)

Structure:
1. Executive Summary (1 page)
   └─ High-level findings, key decisions

2. Current State (As-Is) Analysis (3-4 pages)
   ├─ System architecture & components
   ├─ Performance issues & bottlenecks
   ├─ User pain points
   ├─ Compliance gaps
   └─ Risk assessment

3. Future State (To-Be) Vision (2-3 pages)
   ├─ Desired system architecture
   ├─ Performance targets
   ├─ New capabilities
   └─ Risk mitigation strategies

4. Requirements Summary (5-6 pages)
   ├─ Functional requirements (with acceptance criteria)
   ├─ Non-functional requirements
   ├─ Operational requirements
   ├─ Constraints & Assumptions
   └─ Prioritized requirements matrix

5. Change Impact Analysis (2-3 pages)
   ├─ Organizational changes needed
   ├─ Training needs
   ├─ Change management approach
   └─ Risks & mitigation

6. Data Gathering Results (2 pages)
   ├─ Hardware inventory summary
   ├─ Software inventory
   ├─ Performance metrics
   └─ Effort estimation

7. Recommendations (1-2 pages)
   ├─ Technology stack recommended
   ├─ Architecture approach recommended
   ├─ Team composition recommended
   └─ Timeline feasibility assessment

8. Q&A Log (Appendix)
   └─ Complete Q&A records from interviews

9. Glossary & Acronyms
   └─ Definitions of technical terms
```

---

## ✏️ PHASE 2: ร่าง TOR (Drafting) - 1.5-2 สัปดาห์

**Total Time: 10-12 working days**

### ขั้นที่ 2.1: ร่าง Section 1-3 (Day 1-4)

**Day 1: Section 1 - ความเป็นมา (Background)**

```
Time: 6-8 hours (1 full day)

Outline:
└─ 500-800 words total (2-3 pages)

Content Structure:
1. History of System (150 words)
   └─ When built, by whom, for what purpose
   └─ Source: Project Charter + System Docs

2. Current Situation (150 words)
   └─ Current state, statistics, usage
   └─ Source: Performance data from Phase 1

3. Problems Identified (150 words)
   └─ 3-5 specific problems with evidence
   └─ Source: Q&A log, user interviews, performance data

4. Related Policies (100 words)
   └─ Government policies supporting this project
   └─ Source: Policy documents

5. Justification for Outsourcing (100-150 words)
   └─ Why not build internally
   └─ Source: Sponsor & IT discussion

6. Impact of Inaction (100 words) - Optional
   └─ What happens if we don't do this
   └─ Source: Risk analysis

WRITING TIPS FOR SECTION 1:
- Use Thai government writing style (formal, clear, no jargon)
- Include numbers/statistics (not subjective)
- Reference policies/regulations
- Tell the story: What → Why → How
- Make it compelling (so evaluators understand the need)

CHECKLIST BEFORE MOVING TO SECTION 2:
☐ Word count 500-800 words
☐ All 6 components covered
☐ Has specific numbers/data
☐ Policies referenced
☐ English version done (if bilingual required)
☐ No typos/grammar errors
```

**Day 2: Section 2 - วัตถุประสงค์ (Objectives)**

```
Time: 6-8 hours

Outline:
└─ 300-500 words total (1-2 pages)

Content Structure:
1. Main Objective (50-100 words)
   └─ 1 overall objective that addresses main problem
   └─ Must be SMART (Specific, Measurable, Achievable, Relevant, Time-bound)

2. Specific Objectives (150-200 words)
   └─ 3-5 objectives, each addressing part of solution
   └─ Each must be SMART

3. Target Users (50 words)
   └─ Who uses this system? Internal, external, both?
   └─ How many users?

4. KPIs (100 words)
   └─ 3-5 Key Performance Indicators
   └─ How will we measure success
   └─ Must be measurable & verifiable

5. SLA (optional, 50-100 words)
   └─ Service Level Agreement
   └─ System availability, response time, support hours

SMART OBJECTIVE EXAMPLES:

❌ BAD: "Improve system performance"
   → Too vague, not measurable

✅ GOOD: "Reduce average response time from 5-10 seconds to less than 2 
   seconds (measured at 90th percentile), to be verified through load 
   testing before go-live"
   → Specific (response time), Measurable (< 2 seconds), 
     Achievable (yes), Relevant (main problem), Time-bound (before go-live)

WRITING TIPS FOR SECTION 2:
- Each objective must solve a problem from Section 1
- Use action verbs: Improve, Increase, Reduce, Implement, Develop
- Include measurement method
- Include timeline
- Align with government/organizational strategy

CHECKLIST BEFORE MOVING TO SECTION 3:
☐ Main Objective 1, SMART formatted
☐ Specific Objectives 3-5, each SMART
☐ KPIs have measurement method
☐ All objectives relate back to Section 1 problems
☐ Word count 300-500
☐ No vague language ("improve", "better" without metrics)
```

**Day 3: Section 3 - คุณสมบัติ (Qualifications)**

```
Time: 8-10 hours (1.5 days)

Outline:
└─ 800-1200 words total (3-4 pages)

Content Structure (5-6 subsections):

A. General Qualifications (150 words)
   └─ Thai nationals/entities, registered, not blacklisted, etc.
   └─ 5-6 general criteria

B. Financial Qualifications (200 words)
   ├─ Paid-up Capital ≥ Budget/4
   ├─ Audited Financial Statements (2 years)
   ├─ Financial ratios (current ratio, debt-to-equity)
   └─ Bank statement requirements

C. Experience Qualifications (250 words)
   ├─ Company age: 3-5 years minimum
   ├─ Reference Projects: 3-5 projects
   │  ├─ Value: ≥ 30-50% of this project budget
   │  ├─ Recency: ≤ 5 years old
   │  └─ Relevance: Similar type of project
   ├─ Track Record: Success rate, Client testimonials
   └─ Methodology: Has formal SDLC methodology

D. Personnel Qualifications (250 words)
   ├─ Project Manager: PMP or PRINCE2, 5+ years
   ├─ System Architect: TOGAF or EA cert, 5-7 years
   ├─ Database Admin: DBA cert, 5+ years
   ├─ Network/Security Engineer: CCNA/CISSP, 3-5 years
   ├─ Lead Developer: 5-7 years, relevant tech stack
   └─ Key Personnel: Cannot change without approval

E. Process/Methodology (100 words)
   ├─ ISO 9001 (Quality)
   ├─ ISO 27001 (Security)
   ├─ Project Management Methodology
   └─ Change Management Process

F. Special Requirements (100 words) - if any
   ├─ Consultant Registration (if consulting)
   ├─ OEM Authorization (if software licensing)
   ├─ Cloud Partner Status (if cloud-based)
   └─ Domain-specific certifications

WRITING TIPS FOR SECTION 3:
- Be specific about credentials (not just "IT background")
- Include certification names, not generic "IT knowledge"
- Explain WHY each requirement (link to Section 4 complexity)
- Make requirements achievable (not impossible) but rigorous
- Balance: Not too narrow (no bidders), not too loose (bad bidders)

WHAT NOT TO DO:
❌ "Must be a large company" → Discriminatory
❌ "Must use specific vendor's products" → Discriminatory
❌ "Must have exactly 50+ staff" → Too restrictive

WHAT TO DO:
✅ "Must have successfully delivered 3 similar projects in past 5 years"
✅ "Key personnel must have relevant certifications or 10+ years experience"
✅ "Company must have ISO 9001 or equivalent quality standard"

CHECKLIST BEFORE MOVING TO SECTION 4:
☐ All 6 subsections covered
☐ Paid-up capital calculated correctly (Budget/4)
☐ Reference project criteria clear (count, value %, age)
☐ Personnel requirements list specific certs + years
☐ Key personnel change policy mentioned
☐ Total word count 800-1200
☐ Requirements are reasonable (not impossible)
☐ Requirements relate to Section 4 complexity
```

---

### ขั้นที่ 2.2: ร่าง Section 4 (Day 4-9) ⭐ LONGEST SECTION

**This is the critical section, takes 5-7 days**

```
Day 4-5: 4.1-4.3 (Summary, As-Is, Main Tasks)

Day 5-6: 4.4-4.7 (Hardware, Software, Integration, References)

Day 6-7: 4.8 (Deliverables) - LONGEST SUBSECTION

Day 8-9: 4.9-4.14 (Support, Personnel, Maintenance, Operations, DR, Security)

DETAILED BREAKDOWN:

DAY 4: 4.1 Summary + 4.2 As-Is System

4.1 Summary (100-200 words):
└─ Brief description of what Section 4 covers
└─ Connect to Section 2 Objectives
└─ Show the "big picture" of scope

Example:
"ขอบเขตการจ้างนี้มีจุดมุ่งหมายเพื่อปรับปรุง บำรุงรักษา อัปเกรด และ Modernize
ระบบ e-Payment ของกระทรวงสรรพากร โดยให้ระบบใหม่มี Capability ดังต่อไปนี้:
(1) รองรับจำนวนผู้ใช้เพิ่มขึ้นจาก 100 เป็น 500 users
(2) ปรับปรุงประสิทธิภาพให้เร็วขึ้น (Response Time < 2 sec)
(3) ส่งมอบระบบที่ปลอดภัย (ISO 27001)
(4) ฝึกอบรมบุคลากรเพื่อให้รับผิดชอบได้เอง
..."

4.2 As-Is System Description (300-400 words):
├─ Current Architecture (100 words)
│  └─ Component overview, technology stack, deployment
├─ Performance & Issues (100 words)
│  └─ Current metrics, problems, root causes
├─ Integration Points (50 words)
│  └─ Systems that connect
├─ Limitations (100 words)
│  └─ What it can't do now
└─ Data Volume & Growth (50 words)
   └─ Size, growth rate

Example Section 4.2:
"4.2 ลักษณะของระบบที่มีอยู่เดิม

ระบบ e-Payment ปัจจุบัน (เรียกว่า 'ระบบเดิม') ตัวมีลักษณะดังต่อไปนี้:

4.2.1 สถาปัตยกรรมระบบ
ระบบเดิมเป็นสถาปัตยกรรมแบบ Monolithic (รวมทั้งหมดในเซิร์ฟเวอร์เดียว) 
สร้างบน Platform ดังต่อไปนี้:
- OS: Windows Server 2016 (Support สิ้นสุด 2026)
- Application: .NET Framework 4.5 บน IIS 10
- Database: Microsoft SQL Server 2012 (ค่อนข้างเก่า)
- Web Server: Single server (ไม่มี redundancy)
- Hardware: 1x Lenovo Xeon (4-core, 16GB RAM)
- Network: 100 Mbps (ช้าสำหรับ Current Usage)

4.2.2 ปัญหาและข้อจำกัด
ระบบเดิมมีปัญหาดังต่อไปนี้:
1) Performance ช้า: Average Response Time 5-10 seconds
   ↳ แล้ว Peak time เข้าไปถึง 15-20 seconds ซึ่ง User ไม่พอใจ
2) Availability ต่ำ: System Uptime เพียง 95% (ลงหลัง 7 วัน/เดือน)
   ↳ Downtime มักเกิดจาก Memory Leak, Database Deadlock
3) Scalability ไม่ได้: ไม่สามารถ Scale ขึ้น
   ↳ Database Queries ช้า, ไม่มี Caching, ไม่มี Load Balancer
4) Security ไม่เพียงพอ: ไม่มี Encryption, ไม่มี MFA, ไม่มี WAF
   ↳ ส่วนข้อมูลส่งผ่าน Plain Text (ความเสี่ยง High)
5) Maintainability: Code เก่า, ไม่มี Unit Tests, ไม่มี Documentation
   ↳ Dev Team ยาก ที่จะ Fix Bug หรือ Add Feature

4.2.3 ข้อมูลและการใช้งาน
- จำนวนผู้ใช้: ปัจจุบัน 100-150 users, ปีนี้ 3 ปี
- Transactions/วัน: ประมาณ 1,000 transactions/วัน, ปีละ +150%
- Database Size: ประมาณ 500 GB, Growth 150% ต่อปี
- Peak Time: 10:00-14:00 (Lunch time)

4.2.4 Integration Points
ระบบเดิมเชื่อมต่อกับระบบอื่นดังต่อไปนี้:
- Bank API: สำหรับ Verify payment & Get transaction status
- Ministry of Commerce: สำหรับ Query Tax Data
- Treasury System: สำหรับ Settlement & Reconciliation
- Email Server: สำหรับ Send transaction notification"

DAY 5: 4.3 Main Tasks

4.3 Main Tasks & Activities (400-500 words):
├─ 8-10 major tasks with timeline & effort
├─ Breakdown by phase (Analysis, Design, Dev, Testing, Training, Go-Live)
└─ Each task must have: Description, Deliverable, Timeline, Effort

Example Tasks:

"4.3 งานหลักที่ต้องจ้าง

ผู้รับจ้างต้องดำเนินการตามงานหลักต่อไปนี้เพื่อให้ Project สำเร็จ:

Task 1: System Analysis & Requirements Refinement (30 days)
Objectives:
└─ Conduct detailed analysis ของระบบเดิม
└─ Refine Requirements และ Create detailed specifications
└─ Identify Risks & Create Risk Mitigation Plan

Activities:
├─ 1.1 Interview Stakeholders & Document Current System
│     └─ Duration: 10 days, Effort: 80 man-days
├─ 1.2 Create Detailed Requirements Specification
│     └─ Duration: 15 days, Effort: 120 man-days
└─ 1.3 Risk Assessment & Mitigation Planning
      └─ Duration: 5 days, Effort: 40 man-days

Deliverables:
├─ Detailed System Analysis Report (30 pages)
├─ Requirements Specification Document (40 pages)
└─ Risk Register & Mitigation Plan (15 pages)

Timeline: Week 1-4 (Day 1-30)
Responsible: System Analyst, Business Analyst, IT Manager

Task 2: System Architecture & Design (45 days)
Objectives:
└─ Design High-level System Architecture
└─ Design Database Schema
└─ Design Security & Infrastructure

Deliverables:
├─ System Architecture Document (25 pages)
├─ ER Diagram & Database Design (20 pages)
└─ Security & Infrastructure Design (20 pages)

Timeline: Week 4-10 (Day 31-75)
Responsible: System Architect, Database Architect, Security Engineer

..." (and so on for all tasks)

DAY 5-6: 4.4-4.5 Hardware & Software

4.4 Hardware Requirements (200-300 words):

Example:
"4.4 ห้องแบบและครุภัณฑ์ฮาร์ดแวร์

ผู้รับจ้างต้องจัดเตรียม Hardware ตามต่อไปนี้:

A. PRODUCTION SERVERS (ส่วนหลัก)

1. Web/Application Servers (จำนวน 2 units, Redundancy)
   Specification:
   ├─ Brand/Model: Dell PowerEdge R750 (2U Rack)
   ├─ Processor: 2x Intel Xeon Gold 6348 (28-core, 3.3 GHz)
   ├─ Memory: 256 GB RAM (DDR4-3200)
   ├─ Storage: 2x 1.2 TB 10K RPM SAS Drives (RAID 1)
   ├─ Network: 2x 25 Gbps NIC (High-speed redundancy)
   ├─ Power: Redundant Power Supplies (N+1)
   └─ OS: Ubuntu Linux 22.04 LTS

2. Database Servers (จำนวน 2 units, Primary + Standby)
   ├─ Model: HP ProLiant DL560 Gen10 Plus
   ├─ Memory: 512 GB RAM
   ├─ Storage: 8x 2.4 TB 15K RPM SAS (RAID 10)
   ├─ Network: 2x 25 Gbps NIC
   └─ Purpose: High-performance database with replication

3. Storage Array (จำนวน 1 unit)
   ├─ Model: NetApp AFF A900 (SAN)
   ├─ Capacity: 80 TB Usable (with redundancy)
   ├─ Purpose: Shared storage for all servers
   └─ Replication: Sync to secondary DR site

B. NETWORKING

Core Switch (จำนวน 2, Redundancy):
├─ Model: Cisco Nexus 9372PX
├─ Capacity: 25.6 Tbps throughput
└─ Features: VLAN, QoS, Link Aggregation

Firewall (จำนวน 2, Active-Active):
├─ Model: Palo Alto Networks PA-5220
├─ Throughput: 100 Gbps
└─ Features: IPS, DPI, Threat Prevention

C. BACKUP & DISASTER RECOVERY

Backup Appliance:
├─ Capacity: 50 TB
├─ Method: Daily incremental, Weekly full
├─ Retention: 30 days local, 90 days archive
└─ Testing: Monthly restore test

D. SUMMARY BoM (Bill of Materials)

| Item | Current | New | Action |
|------|---------|-----|--------|
| App Servers | 1 | 2 | Add 1 |
| DB Servers | 1 | 2 | Add 1 |
| Storage | 100 TB | 80 TB | Upgrade |
| Network | 100 Mbps | 10+ Gbps | Upgrade 100x |

TOTAL HARDWARE COST: ประมาณ 8-10 ล้านบาท
DELIVERY TIMELINE: 4-6 weeks after PO
WARRANTY: 3-year on-site support"

4.5 Software & Licenses (200-300 words):

Example:
"4.5 ซอฟต์แวร์และ License

ผู้รับจ้างต้องใช้ Software ตามต่อไปนี้:

A. OPERATING SYSTEMS (FREE Open Source)

Linux: Ubuntu 22.04 LTS
├─ Qty: 8 installations (Web, DB, File servers)
├─ Cost: FREE
└─ Support: Canonical 5-year standard + 5-year extended

B. DATABASE (FREE Open Source)

PostgreSQL 14:
├─ Qty: 2 instances (Primary + Standby)
├─ Cost: FREE
├─ Support: Community + Optional EDB Subscription
└─ Alternative: Oracle Database 21c (Commercial, Cost ~2M)

C. APPLICATION RUNTIME & FRAMEWORK (FREE)

Java OpenJDK 17 LTS:
├─ Cost: FREE
├─ Runtime: Apache Tomcat 10 (FREE)

Alternative: Python 3.10 + FastAPI (FREE)

Frontend: React.js 18 + Node.js 18 (FREE)

D. MONITORING & LOGGING (FREE/PAID OPTIONS)

Prometheus + Grafana (FREE Open Source):
├─ Metrics collection
├─ Dashboard
├─ Alerting
└─ Cost: FREE (self-hosted)

ELK Stack (Elasticsearch + Logstash + Kibana):
├─ Centralized logging
├─ Full-text search
├─ Cost: FREE (open source version)

E. SECURITY (FREE/PAID MIX)

Firewalls & WAF:
├─ Cloudflare WAF (Included in Cloud budget)
└─ OpenVPN (FREE, open source)

SSL/TLS Certificates:
├─ Let's Encrypt (FREE)
└─ DigiCert (Commercial, ~200K baht/year)

F. VERSION CONTROL & CI/CD (FREE)

GitLab Community Edition (FREE):
├─ Self-hosted Git repository
├─ CI/CD pipeline
└─ Project management

G. SUMMARY TABLE

| Software | Type | Cost | License | Support |
|----------|------|------|---------|---------|
| Ubuntu | OS | FREE | GPL | Community |
| PostgreSQL | Database | FREE | POSTGRESQL | Community/EDB |
| Java/Spring | Backend | FREE | GPL/Apache | Community |
| React | Frontend | FREE | MIT | Community |
| Prometheus | Monitoring | FREE | Apache 2.0 | Community |
| **TOTAL** | | **~5-10M** | | |

NOTE: All licenses ต้อง Compliant กับ Open Source Policy
ของกระทรวง ห้ามใช้ Pirated Software"

DAY 7: 4.8 Deliverables (200-300 words, most important)

"4.8 ผลิตภัณฑ์ที่ต้องส่งมอบ (Deliverables)

ผู้รับจ้างต้องส่งมอบผลิตภัณฑ์ตามต่อไปนี้:

PHASE 1: ANALYSIS & DESIGN (By Month 2.5)

Documents:
├─ System Analysis Report (30 pages)
│  └─ Current state, issues, recommendations
├─ Requirements Specification (40 pages)
│  └─ Functional, Non-functional, Operational requirements
├─ System Architecture Document (25 pages)
│  └─ Components, technologies, deployment design
├─ Database Design Document (20 pages)
│  └─ ER Diagram, schema, indexes
├─ Security Architecture Document (20 pages)
│  └─ Encryption, authentication, compliance controls
└─ Project Plan (10 pages)
   └─ Schedule, resources, risks, milestones

Diagrams:
├─ System Architecture Diagram (Visio/DrawIO)
├─ ER Diagram (Database schema)
├─ Network Topology Diagram
├─ Data Flow Diagram (DFD)
└─ Use Case Diagrams (for major features)

Approval:
└─ Design Review & Sign-off from Sponsor & Technical Lead

PHASE 2: DEVELOPMENT (By Month 6)

Source Code:
├─ Backend Source Code (Git Repository)
│  └─ 100% code coverage with unit tests
├─ Frontend Source Code
│  └─ React components, state management, responsive design
├─ Database Scripts
│  └─ Schema, stored procedures, triggers
└─ Infrastructure as Code (Terraform/CloudFormation)
   └─ Server provisioning, network setup

Documentation:
├─ Installation Guide (10 pages)
│  └─ Step-by-step deployment instructions
├─ Configuration Guide (10 pages)
│  └─ Environment setup, parameters
├─ API Documentation (15 pages)
│  └─ Endpoints, parameters, examples, error codes
└─ Deployment Manual (5 pages)
   └─ How to deploy updates

PHASE 3: TESTING & UAT (By Month 7)

Test Artifacts:
├─ Test Plan (10 pages)
│  └─ Test strategy, scope, schedule
├─ Test Cases (100+ test cases)
│  └─ For all major features
├─ Test Results & Defect Log
│  └─ Issues found, severity, status
├─ UAT Sign-off
│  └─ User acceptance testing completed & approved
└─ Performance Test Results
   └─ Load test report, response time metrics

Certifications:
├─ Security Audit Report
├─ Penetration Test Report
└─ ISO 27001 Compliance Assessment

PHASE 4: TRAINING & DOCUMENTATION (By Month 8)

Training Materials:
├─ User Manual (Thai & English, 30 pages)
│  └─ Screenshots, step-by-step procedures
├─ Administrator Guide (20 pages)
│  └─ System configuration, user management, troubleshooting
├─ Training Presentation (PowerPoint)
│  └─ Overview, features, best practices
└─ Video Tutorials (5-10 videos, 5-10 minutes each)
   └─ Common tasks, FAQ

Training Delivery:
├─ Classroom Training (5 days)
│  └─ 20 internal staff members
├─ Training Certificates
│  └─ Issued to attendees who pass test
└─ Train-the-Trainer Sessions
   └─ To enable internal staff to train others

PHASE 5: GO-LIVE & SUPPORT (By Month 12)

Support Services:
├─ Data Migration Services
│  └─ Migrate data from old system to new
├─ Parallel Run Support
│  └─ Both old & new system running together (1-2 weeks)
├─ Go-Live Support
│  └─ On-site 24/7 support for 2-4 weeks post go-live
├─ Post-Go-Live Optimization
│  └─ Performance tuning, bug fixes
└─ Knowledge Transfer Documentation
   └─ How to manage/maintain system

TOTAL DELIVERABLES: 50+ documents, diagrams, code, & certifications

Acceptance Criteria:
- All deliverables must be reviewed & approved
- Documentation must be complete & in Thai/English
- Code must have 80%+ test coverage
- Performance must meet KPIs (defined in Section 2)
- Security must pass ISO 27001 audit"

DAY 8-9: 4.9-4.14 (Support, Personnel, Maintenance, Operations, DR, Security)

These are shorter subsections (each 100-150 words):

"4.9 ระยะเวลาบำรุงรักษา (Support Duration)
└─ On-site Support: 3 months (intensive support during ramp-up)
└─ Remote Support: 12 months (bug fixes, consultation)
└─ Help Desk: 24/7 on-call support
└─ Support Hours: Mon-Fri 8am-5pm (BKT) for normal support

4.10 บุคลากร (Personnel)
└─ Project Manager: 1 (Full-time, throughout project)
└─ Technical Lead: 1 (Full-time, throughout project)
└─ Developers: 5 (4 full-time, 1 part-time)
└─ QA/Tester: 2 (Full-time)
└─ System Admin: 1 (Part-time, 3 days/week)
└─ Database Admin: 1 (Part-time, 2 days/week)

4.11 Maintenance Model
└─ Preventive Maintenance: Monthly (Sunday 2-4am, 2-hour window)
└─ Corrective Maintenance: ASAP for critical issues
└─ Security Patching: Within 48 hours of release
└─ Performance Tuning: Quarterly

4.12 Operations & Management
└─ Daily Backup: Automated, tested weekly
└─ Monitoring: 24/7 automated alerts via Nagios/Prometheus
└─ Log Management: Centralized logging with ELK stack
└─ Change Management: Follow Change Advisory Board process
└─ Capacity Planning: Quarterly reviews

4.13 Disaster Recovery (Contingency Plan)
└─ RTO (Recovery Time Objective): 4 hours
└─ RPO (Recovery Point Objective): 1 hour (max data loss)
└─ Backup Location: 20+ km away
└─ Testing: Quarterly DR drills
└─ Communication: Incident escalation procedures defined

4.14 Security Requirements
└─ Encryption: AES-256 for data at rest, TLS 1.2+ for transit
└─ Authentication: Multi-factor authentication (MFA)
└─ Access Control: Role-based (RBAC)
└─ Audit: ISO 27001 compliant
└─ Penetration Testing: Annual"
```

---

### ขั้นที่ 2.3: ร่าง Section 5-10 (Day 10)

**Day 10: Sections 5-10 (each is short, 200-400 words)**

```
TIME ALLOCATION (1 full day, 8-10 hours):

Section 5: Timeline (200-300 words) - 60 min
└─ Phases, milestones, duration
└─ Create Gantt chart or timeline table

Section 6: Evaluation Criteria (300-400 words) - 90 min
└─ Price vs Quality weights
└─ Scoring method, passing score
└─ Evaluation panel composition

Section 7: Budget (100-150 words) - 30 min
└─ Total amount (in figures + Thai words)
└─ Budget source
└─ Notes on price variation

Section 8: Payment Schedule (300-400 words) - 90 min
└─ 3-4 payment milestones
└─ % per milestone
└─ Acceptance criteria for each
└─ Payment conditions

Section 9: Penalties & Warranty (300-400 words) - 90 min
└─ Late completion penalty (%)
└─ Performance penalty (if metrics not met)
└─ Warranty period & support terms
└─ Defect correction responsibility

Section 10: Supporting Documents (200-300 words) - 60 min
└─ Checklist of required documents
└─ Certification requirements
└─ Financial documents needed
└─ Reference documents needed

EXAMPLE SECTION 5 (Timeline):

"5.0 ระยะเวลาการจ้าง

ระยะเวลาการจ้างนี้มีรายละเอียดดังต่อไปนี้:

วันเริ่มต้น: 1 ตุลาคม พ.ศ. 2569 (ปี FY 2570)
วันสิ้นสุด: 30 กันยายน พ.ศ. 2570 (ระยะเวลารวม: 365 วัน = 52 สัปดาห์)

PHASES & MILESTONES:

Phase 0: Pre-Drafting & Approval (Week -2 to 0, Before project start)
└─ Complete by: 30 Sept 2569

Phase 1: Analysis & Requirements (Week 1-4, Month 1)
├─ Start: 1 Oct 2569
├─ End: 30 Oct 2569
└─ Deliverable: Approved Requirements Specification

Phase 2: Design & Architecture (Week 5-10, Month 2-2.5)
├─ Start: 1 Nov 2569
├─ End: 15 Dec 2569
└─ Deliverable: Design Document Review & Sign-off

Phase 3: Development (Week 11-27, Month 3-7)
├─ Start: 16 Dec 2569
├─ Infrastructure Setup (Week 11-14): By 20 Jan 2570
├─ Backend Development (Week 15-23): By 30 Mar 2570
├─ Frontend Development (Week 15-25): By 15 Apr 2570
├─ Integration (Week 24-27): By 15 May 2570
└─ End: 15 May 2570

Phase 4: Testing & QA (Week 24-30, Month 6-7.5)
├─ Start: 1 May 2570 (Parallel with Development)
├─ Unit Testing: Ongoing during development
├─ Integration Testing (Week 24-27): By 15 May 2570
├─ System Testing (Week 27-29): By 1 Jun 2570
├─ UAT (Week 28-30): By 15 Jun 2570
└─ Approval: By 30 Jun 2570

Phase 5: Training & Documentation (Week 28-36, Month 7-9)
├─ Documentation: By 30 Aug 2570
├─ Training: 15-19 Aug 2570 (5 days)
└─ Training Certification: By 31 Aug 2570

Phase 6: Go-Live & Support (Week 37-52, Month 9-12)
├─ Data Migration: 20-25 Aug 2570
├─ Parallel Run: 26 Aug - 5 Sep 2570
├─ Go-Live: 6 Sep 2570
├─ On-site Support: 6 Sep - 30 Oct 2570 (8 weeks)
├─ Stabilization Period: 6 Sep - 30 Nov 2570 (12 weeks)
└─ End: 30 Sep 2570

KEY MILESTONES (Important Dates):

1. Kickoff Meeting: 1 Oct 2569
2. Requirements Approved: 30 Oct 2569
3. Design Review: 15 Dec 2569
4. Infrastructure Ready: 20 Jan 2570
5. Development Half-way: 1 Mar 2570
6. Development Complete: 15 May 2570
7. UAT Start: 1 Jun 2570
8. UAT Approved: 30 Jun 2570
9. Training Complete: 31 Aug 2570
10. Go-Live: 6 Sep 2570
11. Project End: 30 Sep 2570

TIMELINE ASSUMPTIONS:
├─ No major obstacles or requirement changes
├─ Key Personnel remain assigned throughout
├─ Vendor provides equipment on schedule
├─ Government approvals obtained timely
└─ User availability for meetings/testing

TIMELINE FLEXIBILITY:
├─ ±2 weeks allowed for Phases 1-3
├─ Go-Live date is FIXED (non-negotiable)
├─ Any delays in earlier phases must be absorbed in later phases
└─ Compression only possible by adding resources

Gantt Chart: [See Attached Diagram]"
```

**End of Phase 2: Day 10, Draft TOR 1 is complete (~6000-8500 words)**

---

## 🔍 PHASE 3: ทบทวน แก้ไข อนุมัติ (Review & Revision) - 1.5-2 สัปดาห์

### ขั้นที่ 3.1: ทบทวนภายใน (Day 1-2)

```
INTERNAL REVIEW TEAM:

Reviewer 1: Technical Lead
├─ Check: Scope technical feasibility
├─ Check: Hardware/Software specs correct
├─ Check: Timeline realistic
└─ Check: Deliverables match technical complexity

Reviewer 2: Procurement Officer
├─ Check: Qualifications legally sound
├─ Check: Evaluation criteria fair & objective
├─ Check: No discriminatory language
└─ Check: Process complies with regulations

Reviewer 3: Finance Officer
├─ Check: Budget covered
├─ Check: Payment schedule reasonable
├─ Check: Cost breakdown makes sense
└─ Check: Penalties reasonable

ISSUE LOG TEMPLATE:

| ID | Section | Issue | Type | Priority | Reviewer | Status |
|----|---------|-------|------|----------|----------|--------|
| 1 | 4 | Hardware spec outdated | Minor | Medium | Tech Lead | New |
| 2 | 3 | Paid-up capital too high | Major | High | Proc Off | New |
| 3 | 8 | Payment schedule unclear | Major | High | Finance | New |

CLASSIFICATION:
- Type: Technical, Compliance, Clarity, Accuracy
- Priority: Critical (stop work), High (must fix), Medium (should fix), Low (nice to fix)
- Status: New, In Review, Discussed, Resolved, Closed
```

### ขั้นที่ 3.2: Stakeholder Review Meeting (Day 3)

```
MEETING: TOR STAKEHOLDER REVIEW

TIME: 2-3 hours, Day 3 (After internal review done)

ATTENDEES:
├─ Project Sponsor (Chairperson)
├─ End-user Representatives (1-2 key users)
├─ IT Manager
├─ Procurement Officer
├─ Finance Officer
├─ TOR Team Lead
└─ (Optional) Legal Advisor

AGENDA:

1. Presentation of Draft TOR (30 min)
   └─ TOR Lead presents highlights: Section 1-4 are most important

2. Q&A on Content (60 min)
   └─ Stakeholders ask questions about requirements
   └─ TOR Team clarifies
   └─ Record: All questions & answers

3. Feedback Discussion (45 min)
   ├─ Present issues found by internal reviewers
   ├─ Discuss: Should we change or keep?
   ├─ Record: Decisions made
   └─ High-priority items: Get immediate decision

4. Revision Plan & Next Steps (15 min)
   └─ What will be changed
   └─ When will revised version be ready
   └─ When is next review

OUTPUT:
├─ Meeting Minutes (with all issues & decisions)
├─ Issues List (High/Medium/Low priority)
└─ Revision Action Items (with owners)
```

### ขั้นที่ 3.3: แก้ไขตาม Feedback (Day 4-8)

```
REVISION PROCESS:

For EACH Issue in the Issue Log:

1. High Priority Issues (MUST FIX):
   ├─ Paid-up capital requirement
   ├─ Timeline feasibility
   ├─ Payment schedule accuracy
   ├─ Budget coverage
   └─ Any compliance concerns

   Action: 
   ├─ Discuss with stakeholders (if needed)
   ├─ Make the change
   ├─ Document: "What changed" & "Why"
   └─ Verify: Get agreement

2. Medium Priority Issues (SHOULD FIX):
   ├─ Clarifications on requirements
   ├─ Better wording for evaluation criteria
   ├─ Additional details in Section 4
   └─ Timeline adjustments

   Action:
   ├─ TOR Team decides on best approach
   ├─ Make the change
   └─ Document: What changed & Why

3. Low Priority Issues (NICE TO FIX):
   ├─ Grammar/spelling corrections
   ├─ Minor clarifications
   ├─ Format improvements
   └─ Additional examples

   Action:
   ├─ Fix if time permits
   ├─ Otherwise, leave for final proofreading

CREATE: REVISION SUMMARY DOCUMENT

"Change Log from Draft 1 to Draft 2:

Section 1 (Background):
- Added statistics: User growth +15% per month
- Clarified: Why internal team can't do this project
- Added policy reference: Digital Transformation Strategy

Section 3 (Qualifications):
- Revised Paid-up Capital: From 30M to 25M (based on Finance feedback)
- Changed Reference Project value: From ≥50% to ≥30% (to allow more bidders)
- Added: Security certifications (CISSP or CEH required for Security Engineer)

Section 4 (Scope):
- Expanded 4.8 Deliverables: Added API documentation requirement
- Clarified 4.12 Operations: Added specific monitoring tools (Prometheus)
- Added 4.15 (New): Change Management Process during project

Section 8 (Payment Schedule):
- Revised percentages: 30% > 20% > 30% > 20% (from 30% > 20% > 40% > 10%)
- Added clarity on acceptance criteria for each payment milestone

Overall:
- Word count increased from 6,200 to 7,100 (still within 6000-8500 range)
- 15 issues from review incorporated
- 3 issues deferred (pending executive decision)"
```

### ขั้นที่ 3.4: Legal Review (Day 9)

```
LEGAL REVIEW BY: Legal/Compliance Officer

CHECKLIST:

☑ Language & Style:
  ☐ Thai government writing style used
  ☐ No informal language
  ☐ No grammatical errors
  ☐ Consistent terminology throughout
  ☐ Acronyms defined (first use)

☑ Compliance & Regulations:
  ☐ Complies with Procurement Act B.E. 2560
  ☐ Complies with government regulations
  ☐ Qualifications are reasonable (not discriminatory)
  ☐ Evaluation criteria are objective (not subjective)
  ☐ Payment terms are standard
  ☐ Penalties are proportionate
  ☐ No conflicts with government policy

☑ Legal Clarity:
  ☐ Scope is clearly defined (no ambiguity)
  ☐ In-scope and Out-of-scope explicitly listed
  ☐ Deliverables are measurable/verifiable
  ☐ Acceptance criteria are clear
  ☐ Penalty conditions specified
  ☐ Warranty terms specified
  ☐ Liability limitations defined

☑ Risk Mitigation:
  ☐ TOR protects government interests
  ☐ TOR protects vendor interests (fair)
  ☐ Dispute resolution mechanism defined
  ☐ Change management process defined
  ☐ Contract termination conditions defined

LEGAL APPROVAL OUTPUT:

If no issues:
"This TOR is approved from a legal/compliance perspective.
Recommendation: Proceed to executive approval."

If minor issues:
"This TOR is approved with following minor suggestions:
1. [Suggestion 1]
2. [Suggestion 2]
Recommendation: Proceed with changes"

If major issues:
"This TOR has compliance concerns that must be resolved:
1. [Issue 1]
2. [Issue 2]
Recommendation: Revise and re-submit for legal review"
```

### ขั้นที่ 3.5: Executive/Management Approval (Day 10)

```
PRESENTATION TO: Director/Management/Executive Committee

DELIVERABLES FOR APPROVAL:

1. Final TOR Document (Revised, ~7000 words)
2. Executive Summary (1-2 pages)
   ├─ What: What is the project?
   ├─ Why: Why do we need it? (business case)
   ├─ Cost: 93M baht
   ├─ Timeline: 12 months
   ├─ Benefit: Expected outcomes
   └─ Risk: Major risks & mitigation

3. Change Summary (1 page)
   └─ What changed from draft to final

4. Risk Assessment (1 page)
   ├─ Major risks identified
   ├─ Impact if project fails
   └─ Mitigation strategies

5. Stakeholder Sign-offs
   ├─ IT Manager approval
   ├─ Procurement Officer approval
   ├─ Finance Officer approval
   ├─ Legal Officer approval
   └─ Project Sponsor approval

EXECUTIVE REVIEW CHECKLIST:

☐ Business case is clear
☐ Budget is realistic & approved
☐ Timeline is achievable
☐ Major risks are identified & mitigated
☐ Qualifications ensure vendor capability
☐ Scope is clear to avoid disputes
☐ Payment terms are reasonable
☐ All stakeholders have signed off
☐ Legal & compliance requirements met
☐ Organization is ready for this project

APPROVAL OPTIONS:

1. APPROVED ✅
   "This TOR is approved. Proceed to publishing & bidding process."

2. APPROVED WITH CONDITIONS ⚠️
   "Approved. Conditions:
    - Address issue #X before publishing
    - Address issue #Y during vendor selection
    - Report progress to steering committee monthly"

3. NOT APPROVED ❌
   "Not approved. Reasons:
    - Issue #1 must be resolved
    - Issue #2 must be addressed
    Recommendation: Revise and resubmit"
```

---

## ✅ PHASE 4: เตรียมเผยแพร่ (Publishing) - 1-2 วัน

```
FINAL QUALITY CHECKS:

☑ Proof-reading (2 hours)
  ├─ Check for typos/spelling errors
  ├─ Check for grammar
  ├─ Check numbers/calculations
  └─ Cross-reference: Section references correct?

☑ Formatting (2 hours)
  ├─ Font: TH SarabunPSK 12 pt (or government standard)
  ├─ Spacing: 1.5 line spacing
  ├─ Margins: 2.5 cm all sides
  ├─ Headers: Ministry name, TOR title, page number
  ├─ Footers: Document version, date
  └─ Numbering: Consistent section numbering

☑ Structure & Navigation (1 hour)
  ├─ Table of Contents (with page numbers)
  ├─ Section numbering (1, 1.1, 1.1.1, etc.)
  ├─ Index (if document > 50 pages)
  └─ Cross-references updated

☑ Signature & Approval (2 hours)
  ├─ Signature page created (Cover Page)
  ├─ Signature blocks for:
  │  ├─ Project Sponsor
  │  ├─ Director (Finance)
  │  ├─ Director (Procurement)
  │  └─ Authorized Approver
  ├─ Ensure all signers sign in person (or e-signature)
  └─ Scanned copies for audit trail

DOCUMENT STRUCTURE (FINAL):

1. Cover Page
   ├─ Ministry/Department name
   ├─ "TERMS OF REFERENCE"
   ├─ Project name
   ├─ Document version (e.g., v2.0 Final)
   ├─ Date
   ├─ Signature blocks (3-4 approvers)
   └─ Official seal/stamp

2. Table of Contents
   └─ All sections with page numbers

3. Main TOR Document (Sections 1-10)

4. Appendices (if any)
   ├─ Acronyms & Definitions
   ├─ Reference Documents
   ├─ Sample Forms
   └─ Evaluation Criteria Details

5. Sign-off Page
   └─ List of reviewers & their approval dates

PUBLISHING STEPS:

1. Save as PDF (with signatures)
   └─ Filename: TOR_e-Payment_2569_v2.0_FINAL.pdf

2. Upload to e-Bidding System
   └─ Follow system instructions
   └─ Confirm upload success
   └─ Get receipt/confirmation number

3. Create public announcement
   ├─ Publish on government website
   ├─ Send to potential vendors
   ├─ Announce in news/media (if large project)
   └─ Opening & closing dates clearly stated

4. Prepare for bidder Q&A
   ├─ Create Q&A portal
   ├─ Assign response owner
   ├─ Create schedule for Q&A period (typically 7-14 days)
   └─ Prepare FAQ for common questions

LAUNCH CHECKLIST:

☐ Final TOR document signed by all approvers
☐ Uploaded to e-Bidding system
☐ Public announcement made
☐ Vendors can access document
☐ Q&A period scheduled
☐ Submission deadline set
☐ Evaluation committee appointed
☐ Evaluation schedule agreed

DONE! ✅ TOR is now public and bidders can submit proposals
```

---

## 📊 OVERALL PROJECT CHECKLIST (All Phases)

```
PHASE 0 COMPLETE:
☑ 11 documents collected
☑ 2 kickoff meetings held
☑ Data gathering completed
☑ Sponsor approved to proceed

PHASE 1 COMPLETE:
☑ All source documents read
☑ Requirements interviews completed
☑ Q&A log with 20+ items
☑ Requirements matrix created
☑ Phase 1 analysis report submitted

PHASE 2 COMPLETE:
☑ Section 1-10 drafted
☑ Word count 6000-8500
☑ All sections have content (no placeholders)
☑ Draft 1 TOR submitted for review

PHASE 3 COMPLETE:
☑ Internal review completed (3 reviewers)
☑ Stakeholder review meeting held
☑ Issues incorporated (High, Medium priorities)
☑ Legal review approved
☑ Executive approval obtained
☑ Final TOR version 2.0 signed

PHASE 4 COMPLETE:
☑ Proof-reading done
☑ Formatting perfect
☑ Signature page complete
☑ Uploaded to e-Bidding system
☑ Public announcement made
☑ Bidders can access & submit

TIMELINE SUMMARY:
- Phase 0: 1-2 weeks (pre-work)
- Phase 1: 1 week (Week 1)
- Phase 2: 1.5-2 weeks (Week 2-3)
- Phase 3: 1.5-2 weeks (Week 4-5)
- Phase 4: 1-2 days (Week 6)
- TOTAL: 5-6 weeks from kickoff to public announcement

SUCCESS MEASURES:
☑ TOR is comprehensive & clear
☑ Bidders have no ambiguity
☑ Qualifications are rigorous
☑ Budget is realistic
☑ Timeline is achievable
☑ Scope prevents disputes
☑ Organization is aligned
☑ No protests/legal challenges
```

---

**✅ END OF TOR DRAFTING PROCESS**

**ตอนนี้พร้อมให้ Bidders ยื่นข้อเสนอแล้ว!**
