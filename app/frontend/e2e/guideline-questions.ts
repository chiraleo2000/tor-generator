/** Questions for the 1920x1080 guideline chat clip. One session, four turns. */

export const RATE_PDF_NAME = "อัตราค่าจ้างที่ปรึกษา ประชาสัมพันธ์ อบรม .pdf";

export const SHORT_RATE_QUESTION =
  "อัตราค่าจ้างที่ปรึกษาภาคเอกชน ปริญญาโท อายุงาน 2 ปี ใช้แถวใด";

export const LONG_RATE_QUESTION = [
  "ขออัตราค่าจ้างที่ปรึกษาภาคเอกชน",
  "จัดทีมปริญญาโทแล้วปริญญาเอก",
  "อายุงาน 2 ปี",
  "อบรมครึ่งวันคิดอาหาร 1 มื้อและอาหารว่าง 1 มื้อ",
  "อบรมเต็มวันคิดอาหาร 2 มื้อและอาหารว่าง 2 มื้อ",
  "ค่าเอกสารคิดตามจำนวนผู้เข้าอบรมแต่ละคน",
  "สถานที่ค่าเริ่มต้นเป็นโรงแรมหรือสถานที่เอกชน",
].join(" ");

export const CIRCULAR_QUESTION =
  "หนังสือ ว56 แนวทางปฏิบัติสำหรับการส่งเสริมหรือสนับสนุนกำหนดแนวทางอย่างไร";

export const JUDGMENT_QUESTION =
  "คำพิพากษาหมายเลข 01012-610054 ศาลวินิจฉัยประเด็นใด";

export const GUIDELINE_CHAT_TURNS = [
  SHORT_RATE_QUESTION,
  LONG_RATE_QUESTION,
  CIRCULAR_QUESTION,
  JUDGMENT_QUESTION,
] as const;

export const RATE_QUESTIONS = [SHORT_RATE_QUESTION, LONG_RATE_QUESTION];

export const CHAT_QUESTIONS = [...GUIDELINE_CHAT_TURNS];
