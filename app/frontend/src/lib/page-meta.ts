export function pageMeta(pathname: string): { title: string; sub: string } {
  if (pathname.startsWith("/knowledge-base") || pathname.startsWith("/admin/knowledge-base")) {
    return {
      title: "ฐานความรู้",
      sub: "คลังกฎหมาย ระเบียบ และเอกสารอ้างอิงสำหรับ RAG",
    };
  }
  if (pathname.includes("/draft") || pathname.includes("/wizard")) {
    return {
      title: "ร่าง TOR",
      sub: "กระบวนการร่างเอกสาร TOR แบบ Flow 5 Phase",
    };
  }
  if (pathname.startsWith("/chat")) {
    return {
      title: "ถาม-ตอบ",
      sub: "ห้องแชทรายคน ค้นคลังกลางและเอกสารของคุณด้วย RAG + กราฟกฎหมาย",
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
