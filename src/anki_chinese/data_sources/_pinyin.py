"""
Pinyin lookup using pypinyin.

Falls back to the existing pinyin from the parsed deck if available.
Flags polyphonic characters for manual review.
"""

from __future__ import annotations

from pypinyin import Style, pinyin

# Characters with multiple common readings — flag for review.
# This is not exhaustive; the CLI 'validate' command will catch more.
KNOWN_POLYPHONIC: set[str] = {
    "行",
    "了",
    "得",
    "地",
    "的",
    "还",
    "看",
    "觉",
    "长",
    "乐",
    "说",
    "为",
    "要",
    "好",
    "中",
    "大",
    "少",
    "重",
    "会",
    "发",
    "没",
    "过",
    "给",
    "着",
    "都",
    "把",
    "教",
    "种",
    "干",
    "参",
    "藏",
    "弹",
    "称",
    "处",
    "传",
    "创",
    "倒",
    "调",
    "分",
    "更",
    "冠",
    "和",
    "划",
    "角",
    "结",
    "尽",
    "卷",
    "空",
    "累",
    "量",
    "率",
    "落",
    "模",
    "难",
    "片",
    "期",
    "强",
    "切",
    "曲",
    "圈",
    "塞",
    "散",
    "扇",
    "省",
    "盛",
    "识",
    "数",
    "弄",
    "宿",
    "汤",
    "提",
    "铁",
    "通",
    "吐",
    "系",
    "鲜",
    "相",
    "兴",
    "应",
    "与",
    "载",
    "脏",
    "择",
    "占",
    "涨",
    "正",
    "只",
    "转",
}


def lookup_pinyin(hanzi: str, existing: str = "") -> tuple[str, bool]:
    """Look up pinyin for a single character.

    Returns:
        (pinyin_string, needs_review)

    If the character is polyphonic, we still return pypinyin's default
    but flag it for review. Use `card set` to write corrections into source.
    """
    if len(hanzi) != 1:
        result = pinyin(hanzi, style=Style.TONE, errors="ignore")
        return "".join(r[0] for r in result), False

    result = pinyin(hanzi, style=Style.TONE, errors="ignore")
    py = result[0][0] if result and result[0] else ""
    is_polyphonic = hanzi in KNOWN_POLYPHONIC

    # If we have an existing pinyin from the old deck, prefer it —
    # the user (or old deck author) already chose the right reading.
    if existing and is_polyphonic:
        return existing, True

    return py, is_polyphonic


def lookup_pinyin_word(word: str) -> str:
    """Look up pinyin for a multi-character word (e.g. example words)."""
    result = pinyin(word, style=Style.TONE, errors="ignore")
    return " ".join(r[0] for r in result)
