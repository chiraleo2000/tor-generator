"""Strip chain-of-thought so callers receive only the final answer."""

from app.providers.llm_output import (
    OUTPUT_CONTRACT,
    ThinkingStreamFilter,
    messages_with_output_contract,
    strip_thinking,
)

USER_THINKING_LEAK = """
Here's a thinking process to construct the answer:

1.  **Analyze the Request:** The user wants me to extract and summarize the payment installment (งวดจ่าย) criteria from the knowledge base.

2.  **Examine the Sources for "Payment Installment":**
    *   `[ระเบียบวงเงิน-e2e-1787642638038.txt]`: No content provided.

6.  **Final Output Generation.** (This leads to the provided Thai response.)
"""


def test_strip_thinking_keeps_plain_thai():
    text = "ตามระเบียบกระทรวงการคลัง งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด"
    assert strip_thinking(text) == text


def test_strip_thinking_drops_english_cot_without_answer():
    assert strip_thinking(USER_THINKING_LEAK) == ""


def test_strip_thinking_keeps_thai_after_final_marker():
    raw = (
        USER_THINKING_LEAK
        + "\nตามระเบียบกระทรวงการคลังว่าด้วยการจัดซื้อจัดจ้าง "
        "งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด"
    )
    result = strip_thinking(raw)
    assert "thinking process" not in result.lower()
    assert "งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด" in result


def test_strip_thinking_removes_think_tags():
    raw = "<think>secret prompt</think>\nต้องส่งมอบงานภายในกำหนดสัญญา"
    result = strip_thinking(raw)
    assert "secret prompt" not in result
    assert "ต้องส่งมอบงานภายในกำหนดสัญญา" in result


def test_strip_thinking_keeps_json():
    payload = '{"slot_map": {"s1": {"status": "filled"}}}'
    assert strip_thinking(payload) == payload


def test_messages_with_output_contract_injects_once():
    first = messages_with_output_contract(
        [{"role": "user", "content": "ถาม"}]
    )
    assert first[0]["role"] == "system"
    assert OUTPUT_CONTRACT in first[0]["content"]
    second = messages_with_output_contract(first)
    assert second[0]["content"].count("ห้ามแสดงกระบวนการคิด") == 1


def test_stream_filter_passes_short_thai_live():
    filt = ThinkingStreamFilter()
    out = [filt.push("ตาม"), filt.push("ระเบียบ"), filt.flush()]
    assert "".join(out) == "ตามระเบียบ"


def test_strip_thinking_keeps_thai_glued_after_final_polish():
    raw = (
        "Here's a thinking process to construct the answer:\n\n"
        "1.  **Analyze the Request:** extract งวดจ่าย from the knowledge base.\n"
        "7.  **Final Polish:** (The resulting Thai answer is structured.)"
        "ตามข้อมูลที่ปรากฏในบริบทของเอกสาร ได้มีการกำหนดหลักเกณฑ์งวดงาน"
        "และการจ่ายเงินไว้ โดยแบ่งเป็นสี่งวด"
    )
    result = strip_thinking(raw)
    assert "thinking process" not in result.lower()
    assert "Analyze the Request" not in result
    assert "Final Polish" not in result
    assert "ตามข้อมูลที่ปรากฏในบริบทของเอกสาร" in result


def test_stream_filter_holds_short_english_tokens_then_drops_cot():
    filt = ThinkingStreamFilter()
    pieces = []
    for token in ["H", "ere's a thinking process to construct the answer:\n"]:
        pieces.append(filt.push(token))
    pieces.append(
        filt.push("ตามข้อมูลที่ปรากฏในบริบทของเอกสารกำหนดหลักเกณฑ์งวดงานและการจ่ายเงิน")
    )
    pieces.append(filt.flush())
    text = "".join(pieces)
    assert "thinking process" not in text.lower()
    assert "ตามข้อมูลที่ปรากฏในบริบทของเอกสาร" in text


def test_stream_filter_drops_cot_until_thai():
    filt = ThinkingStreamFilter()
    pieces = []
    pieces.append(filt.push("Here's a thinking process to construct the answer:\n"))
    pieces.append(filt.push("Analyze the Request then cite sources.\n"))
    pieces.append(filt.push("**Final Output Generation.**\n"))
    pieces.append(
        filt.push("ตามระเบียบกระทรวงการคลัง งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด")
    )
    pieces.append(filt.flush())
    text = "".join(pieces)
    assert "thinking process" not in text.lower()
    assert "งวดงานและการจ่ายเงินแบ่งเป็นสี่งวด" in text
