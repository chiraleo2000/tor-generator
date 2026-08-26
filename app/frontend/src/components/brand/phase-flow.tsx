"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { canSelectPhase } from "@/lib/phase-gate";

const THAI_PHASE = ["๐", "๑", "๒", "๓", "๔"] as const;

export const PHASES = [
  { id: 0, title: "เตรียมข้อมูล", sub: "อัปโหลดและวิเคราะห์" },
  { id: 1, title: "ผลวิเคราะห์", sub: "ตารางช่องจากเอกสาร" },
  { id: 2, title: "สอบถามเพิ่ม", sub: "เติมช่องและกฎระเบียบ" },
  { id: 3, title: "ร่างเนื้อหา", sub: "สิบสามหมวดรวมหัวข้อย่อย" },
  { id: 4, title: "ทบทวนและส่งออก", sub: "ตรวจกฎและเผยแพร่" },
] as const;

export function PhaseFlow({
  current,
  unlocked = 0,
  onSelect,
}: Readonly<{
  current: number;
  unlocked?: number;
  onSelect: (phase: number) => void;
}>) {
  return (
    <div className="mb-5 flex items-start overflow-x-auto pb-1">
      {PHASES.map((phase, index) => {
        const done = phase.id < current;
        const active = phase.id === current;
        const locked = !canSelectPhase(current, unlocked, phase.id);
        return (
          <div key={phase.id} className="flex min-w-[150px] flex-1 items-start">
            <button
              type="button"
              aria-label={`ขั้นที่ ${THAI_PHASE[phase.id]} ${phase.title}`}
              aria-disabled={locked}
              aria-current={active ? "step" : undefined}
              data-testid={`phase-${phase.id}`}
              onClick={() => {
                if (locked) return;
                onSelect(phase.id);
              }}
              className={cn(
                "flex-1 text-center",
                locked && "cursor-not-allowed opacity-40",
                active && "scale-110"
              )}
            >
              <span
                className={cn(
                  "mx-auto mb-2 flex h-[52px] w-[52px] items-center justify-center rounded-full border-[3px] text-lg font-extrabold",
                  done && "border-[#0f5c22] bg-brand-green text-white",
                  active &&
                    "scale-110 border-crimson bg-brand-orange text-navy",
                  !done &&
                    !active &&
                    "border-gray-200 bg-gray-200 text-gray-600"
                )}
              >
                {done ? <Check className="h-5 w-5" /> : THAI_PHASE[phase.id]}
              </span>
              <span className="block text-[13px] font-bold text-gray-700">
                ขั้นที่ {THAI_PHASE[phase.id]}
              </span>
              <span className="block text-[11px] text-muted-foreground">
                {phase.title}
              </span>
              <span className="mt-0.5 block text-[10px] text-muted-foreground">
                {phase.sub}
              </span>
            </button>
            {index < PHASES.length - 1 ? (
              <span
                className={cn(
                  "mt-[26px] h-[3px] w-[30px] shrink-0",
                  phase.id < current ? "bg-brand-green" : "bg-gray-200"
                )}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
