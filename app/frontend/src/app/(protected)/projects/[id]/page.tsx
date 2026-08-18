"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;

  useEffect(() => {
    if (id) router.replace(`/projects/${id}/draft`);
  }, [id, router]);

  return <p className="text-sm text-muted-foreground">กำลังเปิดร่าง TOR...</p>;
}
