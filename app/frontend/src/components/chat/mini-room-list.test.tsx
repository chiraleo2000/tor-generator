import { describe, expect, it, vi } from "vitest";
import { MiniRoomList } from "@/components/chat/mini-room-list";
import { render, screen, fireEvent } from "@testing-library/react";

describe("MiniRoomList", () => {
  it("renders room cards and fires new-room", () => {
    const onNew = vi.fn();
    render(
      <MiniRoomList
        rooms={[
          {
            id: "r1",
            kind: "kb",
            project_id: null,
            title: "งวดจ่าย",
            updated_at: new Date().toISOString(),
            last_message: "อ้างระเบียบข้อ 85",
            last_role: "assistant",
          },
        ]}
        activeId="r1"
        search=""
        collapsed={false}
        onSearch={() => undefined}
        onSelect={() => undefined}
        onNew={onNew}
        onRename={() => undefined}
        onDelete={() => undefined}
        onToggleCollapse={() => undefined}
      />
    );
    expect(screen.getByTestId("chat-room-list")).toBeInTheDocument();
    expect(screen.getByText("งวดจ่าย")).toBeInTheDocument();
    expect(screen.getByText("อ้างระเบียบข้อ 85")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("chat-new-room"));
    expect(onNew).toHaveBeenCalled();
  });
});
