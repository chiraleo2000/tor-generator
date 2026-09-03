import { describe, expect, it, vi, afterEach } from "vitest";
import { streamSsePost } from "@/lib/chat-sse";

describe("streamSsePost", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses token and done events", async () => {
    const encoder = new TextEncoder();
    const chunks = [
      'event: token\ndata: {"text":"ก"}\n\n',
      'event: done\ndata: {"content":"ก","citations":[]}\n\n',
    ];
    let index = 0;
    const body = new ReadableStream({
      pull(controller) {
        if (index < chunks.length) {
          controller.enqueue(encoder.encode(chunks[index]));
          index += 1;
          return;
        }
        controller.close();
      },
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({ ok: true, body })
    );
    const events: string[] = [];
    await streamSsePost("/chat", { content: "hi" }, null, (event) => {
      events.push(event);
    });
    expect(events).toEqual(["token", "done"]);
  });

  it("throws when the response is not ok", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        body: null,
        json: async () => {
          throw new Error("empty");
        },
      })
    );
    await expect(
      streamSsePost("/chat", { content: "hi" }, "token", () => undefined)
    ).rejects.toThrow("สตรีมแชทไม่สำเร็จ");
  });

  it("uses the API error message when the stream fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        body: null,
        json: async () => ({ error: { message: "ห้องไม่พบ" } }),
      })
    );
    await expect(
      streamSsePost("/chat", { content: "hi" }, null, () => undefined)
    ).rejects.toThrow("ห้องไม่พบ");
  });

  it("treats non-JSON data lines as text", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode("event: token\ndata: not-json\n\n"));
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body }));
    const events: Array<{ event: string; data: Record<string, unknown> }> = [];
    await streamSsePost("/chat", { content: "hi" }, null, (event, data) => {
      events.push({ event, data });
    });
    expect(events).toEqual([{ event: "token", data: { text: "not-json" } }]);
  });

  it("flushes a trailing SSE block without a blank line", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('event: done\ndata: {"content":"จบ"}'));
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body }));
    const events: string[] = [];
    await streamSsePost("/chat", { content: "hi" }, null, (event) => {
      events.push(event);
    });
    expect(events).toEqual(["done"]);
  });

  it("parses mcp_degraded and citations on done", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(
          encoder.encode(
            'event: done\ndata: {"content":"ตอบ","mcp_degraded":true,"citations":[{"type":"mcp","label":"stub"}]}\n\n'
          )
        );
        controller.close();
      },
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body }));
    const payloads: Array<{ event: string; data: Record<string, unknown> }> = [];
    await streamSsePost("/chat", { content: "hi" }, null, (event, data) => {
      payloads.push({ event, data });
    });
    expect(payloads[0]?.data.mcp_degraded).toBe(true);
    expect(payloads[0]?.data.citations).toEqual([{ type: "mcp", label: "stub" }]);
  });

  it("maps fetch network failures to Thai", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))
    );
    await expect(
      streamSsePost("/chat", { content: "hi" }, null, () => undefined)
    ).rejects.toThrow(/เชื่อมต่อเซิร์ฟเวอร์ไม่ได้/);
  });

  it("skips empty SSE data lines and forwards extra headers", async () => {
    const encoder = new TextEncoder();
    const body = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode("event: ping\n\n"));
        controller.enqueue(encoder.encode('event: done\ndata: {"content":"จบ"}\n\n'));
        controller.close();
      },
    });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, body });
    vi.stubGlobal("fetch", fetchMock);
    const events: string[] = [];
    await streamSsePost(
      "/chat",
      { content: "hi" },
      "tok",
      (event) => {
        events.push(event);
      },
      undefined,
      { "X-Extra": "1" }
    );
    expect(events).toEqual(["done"]);
    const headers = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer tok");
    expect(headers["X-Extra"]).toBe("1");
  });
});

describe("formatChatTimestamp", () => {
  it("returns empty for missing or invalid values", async () => {
    const { formatChatTimestamp } = await import("@/lib/chat-sse");
    expect(formatChatTimestamp(null)).toBe("");
    expect(formatChatTimestamp(undefined)).toBe("");
    expect(formatChatTimestamp("not-a-date")).toBe("");
  });

  it("formats a valid ISO timestamp", async () => {
    const { formatChatTimestamp } = await import("@/lib/chat-sse");
    const formatted = formatChatTimestamp("2026-08-20T08:00:00.000Z");
    expect(formatted.length).toBeGreaterThan(0);
    expect(formatted).not.toBe("not-a-date");
  });

  it("builds attach ingest feedback from the API payload", async () => {
    const { attachIngestFeedback } = await import("@/lib/chat-sse");
    expect(
      attachIngestFeedback(
        { name: "reg.pdf", status: "completed", chunk_count: 2 },
        "reg.pdf"
      )
    ).toContain("ถูกเพิ่มเข้าคลังของฉันแล้ว");
    expect(attachIngestFeedback({ status: "failed", name: "bad.pdf" }, "bad.pdf")).toContain(
      "ไม่สามารถประมวลผล"
    );
    expect(attachIngestFeedback({ status: "processing" }, "wait.pdf")).toContain(
      "กำลังประมวลผล"
    );
    expect(
      attachIngestFeedback({ document_id: "d1", status: "pending", name: "note.txt" }, "note.txt")
    ).toContain("ถูกเพิ่มเข้าคลังของฉันแล้ว");
  });
});
