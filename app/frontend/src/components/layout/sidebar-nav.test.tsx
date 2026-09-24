import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { SidebarNav } from "./sidebar-nav";

vi.mock("next/navigation", () => ({
  usePathname: () => "/chat",
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
    ...props
  }: {
    children: ReactNode;
    href: string;
  }) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (
    select: (state: { user: { role: string }; logout: () => void }) => unknown
  ) =>
    select({
      user: { role: "officer" },
      logout: vi.fn(),
    }),
}));

describe("SidebarNav work items", () => {
  it("keeps the first three tools and adds วิเคราะห์ TOR after ถาม-ตอบ", () => {
    render(<SidebarNav />);
    const draft = screen.getByTestId("nav-draft");
    const review = screen.getByTestId("nav-review");
    const chat = screen.getByTestId("nav-chat");
    const analyze = screen.getByTestId("nav-analyze");

    expect(draft).toHaveTextContent("ร่าง TOR");
    expect(review).toHaveTextContent("ตรวจสอบ TOR");
    expect(chat).toHaveTextContent("ถาม-ตอบ");
    expect(analyze).toHaveTextContent("วิเคราะห์ TOR");
    expect(analyze).toHaveAttribute("href", "/analyze");
    expect(draft.compareDocumentPosition(review) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(review.compareDocumentPosition(chat) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(chat.compareDocumentPosition(analyze) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });
});
