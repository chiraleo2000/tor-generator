"use client";

import { useParams, useRouter } from "next/navigation";
import { useEffect } from "react";

export default function WizardRedirectPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  useEffect(() => {
    if (id) router.replace(`/projects/${id}/draft`);
  }, [id, router]);
  return <p>กำลังเปิดกระบวนการร่างห้าขั้น...</p>;
}
