import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { Phase3Draft } from "@/components/draft/phase3-draft";
import type { SectionPayload } from "@/components/draft/draft-types";

vi.mock("@/components/draft/draft-chat", () => ({
  DraftChat: ({
    onAllDrafted,
    onSectionDone,
  }: {
    onAllDrafted: () => void;
    onSectionDone?: () => void;
  }) => (
    <div data-testid="mock-draft-chat">
      <button type="button" data-testid="mock-all-drafted" onClick={onAllDrafted}>
        all
      </button>
      <button type="button" data-testid="mock-section-done" onClick={() => onSectionDone?.()}>
        section
      </button>
    </div>
  ),
}));

const s1: SectionPayload = {
  key: "s1",
  title: "ความเป็นมา",
  filled: true,
  content: JSON.stringify({ body: "โครงการจัดซื้อระบบคอมพิวเตอร์" }),
  human_confirmed: false,
  hitl: false,
  matchStatus: "matched",
};

const s3: SectionPayload = {
  key: "s3",
  title: "คุณสมบัติของผู้เสนอราคา",
  filled: false,
  content: "",
  human_confirmed: false,
  hitl: true,
  matchStatus: "partial",
};

const s4: SectionPayload = {
  key: "s4",
  title: "ขอบเขตของงาน",
  filled: false,
  content: "",
  human_confirmed: false,
  hitl: false,
  matchStatus: "partial",
  big: true,
  subs: [
    { key: "s4.1", title: "สรุปขอบเขตงาน", content: "พัฒนาโมดูล", filled: true },
  ],
};

describe("Phase3Draft", () => {
  it("renders sections, drafts with AI, and confirms", async () => {
    const onDraft = vi.fn();
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    const onExpand = vi.fn();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <Phase3Draft
        sections={[s1]}
        expanded=""
        openSub=""
        extracted={{ project_name: "โครงการทดสอบ" }}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={onExpand}
        onOpenSub={vi.fn()}
        onSave={onSave}
        onDraft={onDraft}
        onBack={vi.fn()}
        onConfirm={onConfirm}
      />
    );
    expect(screen.getByTestId("phase3-draft")).toHaveTextContent("ร่างเนื้อหา");
    expect(screen.queryByText("เนื้อหาร่าง (จากเอกสารหรือระบบ)")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /หมวด 1: ความเป็นมา/ }));
    expect(onExpand).toHaveBeenCalledWith("s1");
    fireEvent.click(screen.getByTestId("phase3-confirm"));
    expect(onConfirm).toHaveBeenCalled();
  });

  it("expands a section to show AI draft and save", () => {
    const onDraft = vi.fn();
    const onSave = vi.fn().mockResolvedValue(undefined);
    render(
      <Phase3Draft
        sections={[s3]}
        expanded="s3"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo="ร่างแล้ว"
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={onSave}
        onDraft={onDraft}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    fireEvent.click(screen.getByTestId("draft-ai-s3"));
    expect(onDraft).toHaveBeenCalledWith("s3");
    expect(screen.queryByTestId("hitl-confirm-s3")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("save-section-s3"));
    expect(onSave).toHaveBeenCalledTimes(1);
  });

  it("opens a scope subsection and reports errors while busy", () => {
    const onOpenSub = vi.fn();
    const onBack = vi.fn();
    render(
      <Phase3Draft
        sections={[s4]}
        expanded="s4"
        openSub="s4.1"
        extracted={{}}
        busy
        actionError="ร่างด้วย AI ไม่สำเร็จ"
        actionInfo="กำลังร่างด้วย AI..."
        onExpand={vi.fn()}
        onOpenSub={onOpenSub}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={onBack}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByRole("alert")).toHaveTextContent("ร่างด้วย AI ไม่สำเร็จ");
    fireEvent.click(screen.getByRole("button", { name: /สรุปขอบเขตงาน/ }));
    expect(onOpenSub).toHaveBeenCalledWith("");
    fireEvent.click(screen.getByTestId("phase2-back"));
    expect(onBack).toHaveBeenCalled();
  });

  it("renders unfilled sections and plain-text content", () => {
    const onExpand = vi.fn();
    render(
      <Phase3Draft
        sections={[
          {
            ...s1,
            filled: false,
            content: "ข้อความร่างแบบไม่ใช่ JSON",
          },
        ]}
        expanded="s1"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={onExpand}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("รอร่าง")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /หมวด 1: ความเป็นมา/ }));
    expect(onExpand).toHaveBeenCalledWith("");
  });

  it("edits number and select fields", () => {
    const s6: SectionPayload = {
      key: "s6",
      title: "วงเงินงบประมาณ",
      filled: true,
      content: JSON.stringify({ budgetAmount: "5000000" }),
      human_confirmed: false,
      hitl: true,
      matchStatus: "matched",
    };
    const s11: SectionPayload = {
      key: "s11",
      title: "หลักเกณฑ์การพิจารณาคัดเลือกข้อเสนอ",
      filled: false,
      content: "",
      human_confirmed: false,
      hitl: false,
      matchStatus: "partial",
    };
    const { rerender } = render(
      <Phase3Draft
        sections={[s6]}
        expanded="s6"
        openSub=""
        extracted={{ budget: 5000000 }}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByDisplayValue("5000000")).toBeInTheDocument();
    fireEvent.change(screen.getByDisplayValue("5000000"), { target: { value: "6000000" } });
    expect(screen.getByDisplayValue("6000000")).toBeInTheDocument();
    rerender(
      <Phase3Draft
        sections={[s11]}
        expanded="s11"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByRole("combobox")).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "เกณฑ์ราคา" },
    });
    expect(screen.getByRole("combobox")).toHaveValue("เกณฑ์ราคา");
  });

  it("treats JSON arrays as raw body text", () => {
    render(
      <Phase3Draft
        sections={[{ ...s1, content: "[1,2]", filled: true }]}
        expanded="s1"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByTestId("phase3-draft")).toBeInTheDocument();
  });

  it("puts AI prose into subsection fields instead of a combined body box", () => {
    render(
      <Phase3Draft
        sections={[s1]}
        expanded="s1"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
        projectId="p1"
      />
    );
    expect(screen.queryByText("เนื้อหาร่าง (จากเอกสารหรือระบบ)")).not.toBeInTheDocument();
    expect(screen.getByText(/ประวัติ\/สถานการณ์ปัจจุบัน/)).toBeInTheDocument();
    expect(screen.getByDisplayValue("โครงการจัดซื้อระบบคอมพิวเตอร์")).toBeInTheDocument();
  });

  it("uses Thai-only workflow copy for subsections", () => {
    render(
      <Phase3Draft
        sections={[s4]}
        expanded="s4"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    const root = screen.getByTestId("phase3-draft");
    expect(root).toHaveTextContent("ขั้นที่ ๓");
    expect(root).toHaveTextContent("๔.๑–๔.๑๔");
    expect(screen.queryByText("Phase 3")).not.toBeInTheDocument();
    expect(screen.queryByText("As-Is")).not.toBeInTheDocument();
    expect(screen.getByTestId("scope-sub-s4.1")).toBeInTheDocument();
  });

  it("keeps Thai chip labels when the API still sends As-Is titles", () => {
    render(
      <Phase3Draft
        sections={[
          {
            ...s4,
            subs: [
              {
                key: "s4.2",
                title: "ระบบงานปัจจุบัน (As-Is)",
                content: "ระบบงานเดิมใช้เอกสารกระดาษทั้งสายงาน",
                filled: true,
              },
            ],
          },
        ]}
        expanded="s4"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByTestId("phase3-heading")).toHaveTextContent("ขั้นที่ ๓");
    expect(screen.getByTestId("scope-sub-s4.2")).toHaveTextContent("ระบบงานปัจจุบัน");
    expect(screen.getByTestId("phase3-draft").textContent).not.toContain("As-Is");
  });

  it("falls back to a body field, mapping hints, and empty-scope copy", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onOpenSub = vi.fn();
    render(
      <Phase3Draft
        sections={[
          {
            key: "s99",
            title: "หมวดพิเศษ",
            filled: false,
            content: "ข้อความอิสระ",
            human_confirmed: false,
            hitl: false,
            matchStatus: "partial",
          },
          {
            ...s3,
            content: JSON.stringify({ paidup: "ทุนจดทะเบียน 5 ล้าน" }),
          },
          { ...s4, subs: [] },
        ]}
        expanded="s3"
        openSub=""
        extracted={{ paidupSuggest: "5,000,000" }}
        busy={false}
        actionError="บันทึกไม่สำเร็จ"
        actionInfo="ร่างแล้ว"
        onExpand={vi.fn()}
        onOpenSub={onOpenSub}
        onSave={onSave}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    expect(screen.getByText("บันทึกไม่สำเร็จ")).toBeInTheDocument();
    expect(screen.getByText("ร่างแล้ว")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /หมวด 99/ }));
    fireEvent.click(screen.getByRole("button", { name: /หมวด 4/ }));
  });

  it("opens an unfilled subsection chip and saves on blur", () => {
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onOpenSub = vi.fn();
    render(
      <Phase3Draft
        sections={[
          {
            ...s4,
            subs: [
              { key: "s4.1", title: "สรุปขอบเขตงาน", content: "พัฒนาโมดูล", filled: true },
              { key: "s4.3", title: "ความต้องการ", content: "", filled: false },
            ],
          },
        ]}
        expanded="s4"
        openSub="s4.3"
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={onOpenSub}
        onSave={onSave}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
      />
    );
    fireEvent.click(screen.getByRole("button", { name: /4.3/ }));
    expect(onOpenSub).toHaveBeenCalled();
    const area = screen.getByTestId("scope-sub-s4.3").querySelector("textarea");
    expect(area).toBeTruthy();
    fireEvent.change(area as HTMLTextAreaElement, { target: { value: "ความต้องการใหม่" } });
    fireEvent.blur(area as HTMLTextAreaElement);
    expect(onSave).toHaveBeenCalledWith("s4.3", "ความต้องการใหม่");
  });

  it("edits a textarea body field and marks all drafted from chat", () => {
    const onRefresh = vi.fn();
    render(
      <Phase3Draft
        sections={[s1]}
        expanded="s1"
        openSub=""
        extracted={{}}
        busy={false}
        actionError={null}
        actionInfo={null}
        onExpand={vi.fn()}
        onOpenSub={vi.fn()}
        onSave={vi.fn().mockResolvedValue(undefined)}
        onDraft={vi.fn()}
        onBack={vi.fn()}
        onConfirm={vi.fn().mockResolvedValue(undefined)}
        projectId="p-chat"
        onRefresh={onRefresh}
      />
    );
    const history = screen.getByDisplayValue("โครงการจัดซื้อระบบคอมพิวเตอร์");
    fireEvent.change(history, { target: { value: "สถานการณ์ใหม่ของหน่วยงาน" } });
    expect(screen.getByDisplayValue("สถานการณ์ใหม่ของหน่วยงาน")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("mock-all-drafted"));
    expect(screen.getByTestId("phase3-all-drafted")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("mock-section-done"));
    expect(onRefresh).toHaveBeenCalled();
  });
});
