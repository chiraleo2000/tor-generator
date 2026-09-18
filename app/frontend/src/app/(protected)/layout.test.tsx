import { describe, expect, it, vi, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import ProtectedLayout from "./layout";
import { useUIStore } from "@/stores/ui-store";

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

vi.mock("@/components/auth/auth-guard", () => ({
  AuthGuard: ({ children }: { children: ReactNode }) => children,
}));

vi.mock("@/stores/auth-store", () => ({
  useAuthStore: (select: (state: { user: { name: string; email: string; role: string }; logout: () => void }) => unknown) =>
    select({
      user: { name: "Officer", email: "officer@example.com", role: "officer" },
      logout: vi.fn(),
    }),
}));

describe("ProtectedLayout", () => {
  beforeEach(() => {
    useUIStore.setState({ sidebarOpen: false });
  });

  it("keeps the drawer closed until the mobile menu is opened", () => {
    render(
      <ProtectedLayout>
        <p>เครื่องมือ</p>
      </ProtectedLayout>
    );
    expect(screen.getByTestId("app-sidebar")).toBeInTheDocument();
    expect(screen.queryByTestId("nav-overlay")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("nav-toggle"));
    expect(screen.getByTestId("nav-overlay")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("nav-overlay"));
    expect(screen.queryByTestId("nav-overlay")).not.toBeInTheDocument();
    expect(screen.getByText("เครื่องมือ")).toBeInTheDocument();
  });
});
