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
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, body: null }));
    await expect(
      streamSsePost("/chat", { content: "hi" }, "token", () => undefined)
    ).rejects.toThrow("สตรีมแชทไม่สำเร็จ");
  });
});
