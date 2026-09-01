export function pageMeta(pathname: string): { title: string; sub: string } {
  if (pathname.startsWith("/knowledge-base") || pathname.startsWith("/admin/knowledge-base")) {
    return {
      title: "ฐานความรู้",
      sub: "คลังกฎหมาย ระเบียบ และเอกสารอ้างอิงสำหรับค้นหา",
    };
  }
  if (pathname.includes("/draft") || pathname.includes("/wizard")) {
    return {
      title: "ร่าง TOR",
      sub: "กระบวนการร่างเอกสารกำหนดขอบเขตงานห้าขั้น",
    };
  }
  if (pathname.startsWith("/chat")) {
    return {
      title: "ถาม-ตอบ",
      sub: "ดึงคลังกฎหมายจาก pgvector หลายชิ้น แล้วตอบเป็นย่อหน้าเนื้อหาพร้อมอ้างอิง inline",
    };
  }
  if (pathname.startsWith("/review")) {
    return {
      title: "ตรวจสอบ TOR",
      sub: "ตรวจสอบความถูกต้องตามกฎหมายและเทียบเคียงโครงการ",
    };
  }
  if (pathname.startsWith("/help")) {
    return {
      title: "คู่มือการใช้งาน",
      sub: "คำอธิบายและภาพประกอบแต่ละส่วนของระบบ",
    };
  }
  if (pathname.startsWith("/admin/ai-settings")) {
    return { title: "การตั้งค่า AI", sub: "เลือกแชทและฝังเวกเตอร์อิสระ (ในเครื่อง / คลาวด์)" };
  }
  if (pathname.startsWith("/admin/users")) {
    return { title: "ผู้ใช้", sub: "บัญชีเจ้าหน้าที่และสิทธิ์" };
  }
  if (pathname.startsWith("/admin/templates")) {
    return { title: "แม่แบบ", sub: "โครงร่าง TOR ตามประเภทงาน" };
  }
  return { title: "แดชบอร์ด", sub: "ภาพรวมโครงการ TOR ทั้งหมด" };
}
