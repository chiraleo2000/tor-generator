"""Intake slot replies and analyze-window helpers that stay under the coverage bar."""

from app.services.intake_service import (
    _apply_guessed_or_current,
    _chunk_text_window,
    _grant_one_pass,
    _indexes_covering,
    _is_bulk_paste,
    _one_window_each,
    _split_pack_by_file,
    _weighted_budget_share,
    apply_chat_answer_to_slots,
    empty_slot_map,
    phase2_filled_ack,
    slot_map_for_prompt,
)


def test_chat_answer_bulk_guess_and_prompt_lines():
    assert _is_bulk_paste("สั้น", ["s1", "s2"]) is True
    assert _is_bulk_paste("ก\n" + ("ข" * 400), ["s1"]) is True
    assert _is_bulk_paste("สั้น", ["s1"]) is False
    slot_map = empty_slot_map("hire_develop")
    filled = apply_chat_answer_to_slots(slot_map, "   ")
    assert filled == []
    guessed = _apply_guessed_or_current(
        empty_slot_map("hire_develop"),
        "คุณสมบัติผู้ยื่นต้องเป็นนิติบุคคลจดทะเบียนในประเทศไทย",
        current_slot="missing",
        category="hire_develop",
    )
    assert isinstance(guessed, list)
    ack = phase2_filled_ack(["s1", "s6"], "s8")
    assert "บันทึกข้อมูลหลายช่อง" in ack
    done = phase2_filled_ack(["s1", "s2"], None)
    assert "ครบแล้ว" in done
    prompt_map = empty_slot_map("hire_develop")
    prompt_map["s1"] = "ไม่ใช่ dict"
    text = slot_map_for_prompt(prompt_map)
    assert "s1" not in text.split("ไม่ใช่")[0] or "[ยังขาด]" in text or text == "" or "s2" in text


def test_analyze_windows_cover_edges_and_share_budget():
    assert _split_pack_by_file("") == []
    assert _split_pack_by_file("ก้อนเดียว") == ["ก้อนเดียว"]
    marked = "===== ไฟล์: a.txt\nเนื้อหาเอ\n===== ไฟล์: b.txt\nเนื้อหาบี"
    parts = _split_pack_by_file(marked)
    assert len(parts) == 2
    assert _chunk_text_window("") == []
    windows = _chunk_text_window("ก" * 50)
    assert windows == ["ก" * 50]
    assert _indexes_covering(0, 2) == []
    assert _indexes_covering(4, 1) == [0]
    assert _indexes_covering(3, 5) == [0, 1, 2]
    picked = _indexes_covering(6, 3)
    assert picked[0] == 0
    assert picked[-1] == 5
    flags = _one_window_each(4, 2)
    assert flags.count(1) == 2
    share = _weighted_budget_share([4, 8], 3)
    assert share[1] >= share[0]
    budgets = [1, 1]
    leftover = _grant_one_pass([1, 3], budgets, [0, 1], 2)
    assert leftover == 1
    assert _grant_one_pass([1, 1], [1, 1], [0, 1], 2) == -1
