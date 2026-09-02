"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  BookOpen,
  PenLine,
  ScanSearch,
  HelpCircle,
  FileText,
  Users,
  Cpu,
  ClipboardList,
  MessagesSquare,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth-store";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  testId: string;
}

const mainItems: NavItem[] = [
  { href: "/projects", label: "แดชบอร์ด", icon: LayoutDashboard, testId: "nav-projects" },
  { href: "/knowledge-base", label: "ฐานความรู้", icon: BookOpen, testId: "nav-knowledge-base" },
];

const workItems: NavItem[] = [
  { href: "/draft", label: "ร่าง TOR", icon: PenLine, testId: "nav-draft" },
  { href: "/review", label: "ตรวจสอบ TOR", icon: ScanSearch, testId: "nav-review" },
  { href: "/chat", label: "ถาม-ตอบ", icon: MessagesSquare, testId: "nav-chat" },
];

const otherItems: NavItem[] = [
  { href: "/help", label: "คู่มือ", icon: HelpCircle, testId: "nav-help" },
];

const adminItems: NavItem[] = [
  { href: "/admin/templates", label: "แม่แบบ", icon: FileText, testId: "nav-admin-templates" },
  { href: "/admin/knowledge-base", label: "ฐานความรู้ (จัดการ)", icon: BookOpen, testId: "nav-admin-knowledge-base" },
  { href: "/admin/users", label: "ผู้ใช้", icon: Users, testId: "nav-admin-users" },
  { href: "/admin/ai-settings", label: "การตั้งค่า AI", icon: Cpu, testId: "nav-admin-ai-settings" },
];

export function SidebarNav() {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const isAdmin = user?.role === "admin";

  return (
    <aside className="fixed inset-y-0 left-0 z-30 flex w-[255px] flex-col overflow-y-auto bg-gradient-to-b from-navy to-navy-dark p-[18px] text-white">
      <div className="mb-6 flex items-center gap-2.5 border-b border-white/12 pb-4">
        <div className="flex h-[38px] w-[38px] items-center justify-center rounded-lg bg-brand-orange font-extrabold text-navy">
          <ClipboardList className="h-5 w-5" />
        </div>
        <div>
          <h1 className="text-[17px] font-bold leading-tight">TOR Generator</h1>
          <p className="text-[11px] text-white/75">ระบบจัดซื้อจัดจ้างภาครัฐ</p>
        </div>
      </div>

      <nav className="flex-1 space-y-5" aria-label="เมนูหลัก">
        <NavSection title="หลัก" items={mainItems} pathname={pathname} />
        <NavSection title="การทำงาน" items={workItems} pathname={pathname} />
        <NavSection title="อื่นๆ" items={otherItems} pathname={pathname} />
        {isAdmin ? (
          <NavSection title="ผู้ดูแลระบบ" items={adminItems} pathname={pathname} />
        ) : null}
      </nav>

      <p className="mt-3 rounded-lg bg-white/5 p-3 text-[12px] leading-relaxed text-white/80">
        ประมวลผลเอกสาร + ค้นหาคลังความรู้ด้วย PageIndex + Claude Sonnet 4.6
      </p>
      <button
        type="button"
        data-testid="logout"
        className="mt-2.5 text-center text-[12.5px] text-red-200 hover:underline"
        onClick={() => {
          logout();
          router.push("/login");
        }}
      >
        ออกจากระบบ
      </button>
    </aside>
  );
}

function NavSection({
  title,
  items,
  pathname,
}: Readonly<{ title: string; items: NavItem[]; pathname: string }>) {
  return (
    <div>
      <p className="mb-2 text-[11px] uppercase tracking-wider text-white/55">{title}</p>
      {items.map((item) => {
        const Icon = item.icon;
        const active =
          pathname === item.href || pathname.startsWith(`${item.href}/`);
        return (
          <Link
            key={item.href}
            href={item.href}
            data-testid={item.testId}
            className={cn(
              "mb-1 flex items-center gap-2.5 rounded-lg border-l-[3px] px-3 py-2.5 text-sm transition-colors",
              active
                ? "border-crimson bg-brand-orange font-bold text-navy"
                : "border-transparent text-white hover:bg-white/10"
            )}
          >
            <Icon className="h-[18px] w-[18px] shrink-0" />
            {item.label}
          </Link>
        );
      })}
    </div>
  );
}
