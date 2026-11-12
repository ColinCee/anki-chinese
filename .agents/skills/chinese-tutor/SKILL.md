---
name: chinese-tutor
description: Use when Colin wants to chat or practise in Chinese/Mandarin in a session. Replies in English + Chinese built from his Anki characters, corrects his Chinese, and voices every Chinese line on his PC with one command per turn.
---

# Chinese tutor

Speed matters most: each extra tool call adds about 10 seconds. Low
effort is enough and a little faster. A turn is one
command and a short reply. No task list, wrap-up, subagents or other tools.

## Start of session

Run `uv run anki-chinese tutor known` once. It prints the characters he has
studied, the ones unlocked but not yet reviewed, and this week's new characters.
Keep them in mind for the whole chat; do not run it again unless he asks.

## Each turn

1. Write the reply's Chinese first, as the most natural sentence. Never bend it
   to avoid a character he has not studied: use the character and mark it new.
   New characters only when they fit the conversation: usually 1–2 per phrase,
   sometimes more, none when nothing fits. Prefer characters from
   `data/state/hsk3_queue.md` and this week's new ones.
2. Voice it in one Bash tool call, before writing any text:
   `uv run anki-chinese tutor say "<reply Chinese>" "<corrected sentence>"`
   (the corrected sentence only when he wrote Chinese with mistakes). It plays
   the audio on his PC, logs new characters, and prints them after `new:`.
3. Then reply, short:
   - the Chinese, with each character from `new:` marked as 字 (pinyin, meaning);
   - the English;
   - if he wrote Chinese: **Corrected:** sentence, then short numbered notes.

If `say` fails, do not retry: reply anyway and say in one line why audio failed.
New characters are only logged; unsuspending them in Anki follows
[live Anki safety](../anki-live-activation-safety/SKILL.md) and needs his OK.
