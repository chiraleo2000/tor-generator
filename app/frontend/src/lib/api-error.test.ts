import { describe, it, expect } from "vitest";
import { apiErrorMessage } from "./api-error";

describe("apiErrorMessage", () => {
  it("reads FastAPI error.message", () => {
    expect(
      apiErrorMessage(
        { response: { data: { error: { message: "ต้องใส่ OPENAI_API_KEY" } } } },
        "fallback"
      )
    ).toBe("ต้องใส่ OPENAI_API_KEY");
  });

  it("uses fallback when the payload is missing or not a string", () => {
    expect(apiErrorMessage(null, "fallback")).toBe("fallback");
    expect(apiErrorMessage({}, "fallback")).toBe("fallback");
    expect(
      apiErrorMessage({ response: { data: { error: { message: 12 } } } }, "fallback")
    ).toBe("fallback");
  });

  it("explains Axios timeouts in Thai", () => {
    expect(apiErrorMessage({ code: "ECONNABORTED" }, "fallback")).toMatch(/หมดเวลารอโมเดล/);
    expect(apiErrorMessage({ message: "timeout of 90000ms exceeded" }, "fallback")).toMatch(
      /หมดเวลารอโมเดล/
    );
  });

  it("explains browser and Axios network failures in Thai", () => {
    expect(apiErrorMessage({ message: "Failed to fetch" }, "fallback")).toMatch(
      /เชื่อมต่อเซิร์ฟเวอร์ไม่ได้/
    );
    expect(apiErrorMessage({ code: "ERR_NETWORK" }, "fallback")).toMatch(
      /เชื่อมต่อเซิร์ฟเวอร์ไม่ได้/
    );
  });

  it("maps AbortError from DOMException and plain objects", () => {
    expect(apiErrorMessage(new DOMException("stop", "AbortError"), "fallback")).toMatch(
      /ยกเลิกการสตรีมแล้ว/
    );
    expect(apiErrorMessage({ name: "AbortError" }, "fallback")).toMatch(/ยกเลิกการสตรีมแล้ว/);
    expect(apiErrorMessage("string", "fallback")).toBe("fallback");
  });
});
