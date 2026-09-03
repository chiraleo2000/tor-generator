import { describe, expect, it, vi } from "vitest";
import { MiniRoomList } from "@/components/chat/mini-room-list";
import { render, screen, fireEvent } from "@testing-library/react";

const todayRoom = {
  id: "r1",
  kind: "kb" as const,
  project_id: null,
  title: "งวดจ่าย",
  updated_at: new Date().toISOString(),
  last_message: "อ้างระเบียบข้อ 85",
  last_role: "assistant" as const,
};

const oldRoom = {
  id: "r2",
  kind: "kb" as const,
  project_id: null,
  title: "หลักประกัน",
  updated_at: "2020-01-01T00:00:00.000Z",
  last_message: "",
  last_role: null,
};

describe("MiniRoomList", () => {
  it("renders room cards and fires new-room", () => {
    const onNew = vi.fn();
    render(
      <MiniRoomList
        rooms={[todayRoom]}
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
    expect(screen.getByTestId("chat-room-item")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("chat-new-room"));
    expect(onNew).toHaveBeenCalled();
  });

  it("filters by search, selects, renames, and deletes", () => {
    const onSearch = vi.fn();
    const onSelect = vi.fn();
    const onRename = vi.fn();
    const onDelete = vi.fn();
    const onToggle = vi.fn();
    const { rerender } = render(
      <MiniRoomList
        rooms={[todayRoom, oldRoom]}
        activeId="r1"
        search=""
        collapsed={false}
        onSearch={onSearch}
        onSelect={onSelect}
        onNew={() => undefined}
        onRename={onRename}
        onDelete={onDelete}
        onToggleCollapse={onToggle}
      />
    );
    fireEvent.change(screen.getByTestId("chat-room-search"), {
      target: { value: "หลัก" },
    });
    expect(onSearch).toHaveBeenCalledWith("หลัก");
    rerender(
      <MiniRoomList
        rooms={[todayRoom, oldRoom]}
        activeId="r1"
        search="หลัก"
        collapsed={false}
        onSearch={onSearch}
        onSelect={onSelect}
        onNew={() => undefined}
        onRename={onRename}
        onDelete={onDelete}
        onToggleCollapse={onToggle}
      />
    );
    expect(screen.getByText("หลักประกัน")).toBeInTheDocument();
    expect(screen.getByText("ยังไม่มีข้อความ")).toBeInTheDocument();
    fireEvent.click(screen.getAllByTestId("chat-room-item")[0]);
    expect(onSelect).toHaveBeenCalledWith("r2");
    fireEvent.click(screen.getByTitle("เปลี่ยนชื่อ"));
    expect(onRename).toHaveBeenCalledWith("r2");
    fireEvent.click(screen.getByTitle("ลบ"));
    expect(onDelete).toHaveBeenCalledWith("r2");
    fireEvent.click(screen.getByTitle("ยุบแถบ"));
    expect(onToggle).toHaveBeenCalled();
  });

  it("hides search when collapsed", () => {
    render(
      <MiniRoomList
        rooms={[todayRoom]}
        activeId="r1"
        search=""
        collapsed
        onSearch={() => undefined}
        onSelect={() => undefined}
        onNew={() => undefined}
        onRename={() => undefined}
        onDelete={() => undefined}
        onToggleCollapse={() => undefined}
      />
    );
    expect(screen.queryByTestId("chat-room-search")).not.toBeInTheDocument();
  });
});
