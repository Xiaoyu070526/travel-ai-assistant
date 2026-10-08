"""聊天对话持久化模块测试（保留对话 / 上下文注入）。

运行：pytest tests/test_chat_history.py
"""

import json

from src.utils.chat_history import (
    ChatHistoryStore,
    build_conversation_block,
    format_conversation,
)


def _sample() -> list[dict]:
    return [
        {"role": "user", "content": "故宫怎么用护照订票？"},
        {"role": "assistant", "content": "🤖 **护照订票**\n\n可通过官网/携程用护照实名预约。"},
        {"role": "user", "content": "那第二天的安排呢？"},
    ]


def test_save_then_load_roundtrip(tmp_path):
    store = ChatHistoryStore(path=tmp_path / "chat.json")
    store.save(_sample())
    loaded = store.load()
    assert loaded == _sample()


def test_load_missing_file_returns_empty(tmp_path):
    store = ChatHistoryStore(path=tmp_path / "nope.json")
    assert store.load() == []


def test_load_corrupt_file_returns_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{这不是合法json", encoding="utf-8")
    store = ChatHistoryStore(path=p)
    assert store.load() == []


def test_load_drops_invalid_records(tmp_path):
    p = tmp_path / "mix.json"
    p.write_text(
        json.dumps(
            [
                {"role": "user", "content": "正常消息"},
                {"role": "system", "content": "应被丢弃"},
                "纯字符串也应被丢弃",
                {"role": "assistant", "content": 123},  # content 非字符串
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    store = ChatHistoryStore(path=p)
    assert store.load() == [{"role": "user", "content": "正常消息"}]


def test_clear_removes_file(tmp_path):
    p = tmp_path / "chat.json"
    store = ChatHistoryStore(path=p)
    store.save(_sample())
    assert p.exists()
    store.clear()
    assert not p.exists()
    assert store.load() == []


def test_format_conversation_caps_recent_turns(tmp_path):
    # 造 30 轮（60 条），只应保留最近 20 轮
    many = []
    for i in range(30):
        many.append({"role": "user", "content": f"问题{i}"})
        many.append({"role": "assistant", "content": f"回答{i}"})
    txt = format_conversation(many, max_turns=20)
    assert "问题0" not in txt
    assert "问题29" in txt
    assert txt.count("游客：") == 20
    assert txt.count("助手：") == 20


def test_build_conversation_block_empty_for_no_history():
    assert build_conversation_block([]) == ""


def test_build_conversation_block_includes_transcript():
    block = build_conversation_block(_sample())
    assert "故宫怎么用护照订票？" in block
    assert "那第二天的安排呢？" in block
    assert "此前的对话记录" in block
