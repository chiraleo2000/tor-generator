"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function WizardIndexRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/draft");
  }, [router]);
  return <p>กำลังเปิดร่าง TOR...</p>;
}
