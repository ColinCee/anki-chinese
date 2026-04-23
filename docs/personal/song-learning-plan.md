# Song-Based Character Learning Plan

## Why Songs?

- **Emotional hooks** — music makes characters stickier than isolated drilling
- **Context** — characters appear in natural phrases and grammar
- **Effortless repetition** — choruses repeat key vocabulary dozens of times
- **Pronunciation & tones** — singing trains tonal patterns
- **Concrete milestones** — "I can read this entire song" beats abstract character counts

## How Songs Complement RSH Order

1. **Fill frequency gaps** — Heisig's sequence optimises for components, not usage. Songs pull in high-frequency characters you'd otherwise encounter months later.
2. **Build reading fluency** — recognising characters in flowing lyrics trains speed.
3. **Cultural literacy** — universally known songs; social superpower at KTV.
4. **Compounding overlap** — shared characters across songs reduce marginal cost.

## Song Sequence

Songs are ordered by a greedy algorithm that minimises new characters at each step, building cumulative knowledge progressively. Run the analysis script for the current state:

```bash
uv run scripts/analyze_songs.py
```

### Adding new songs

```bash
# 1. Fetch lyrics from LRCLIB (auto-converts Traditional → Simplified)
uv run scripts/analyze_songs.py fetch "song name" "artist"

# 2. Re-run analysis to see where it fits in the greedy sequence
uv run scripts/analyze_songs.py

# 3. Renumber files to match the new sequence
```

### Current song list

Lyrics live in `scripts/lyrics/` numbered by greedy order. As of April 2025 (21 songs):

01. 学猫叫 (小潘潘)
02. 月亮代表我的心 (邓丽君)
03. 童话 (光良)
04. 星辰大海 (黄霄云)
05. 搁浅 (周杰伦)
06. 说好不哭 (周杰伦)
07. 你好不好 (周兴哲)
08. 年少有为 (李荣浩)
09. 怎么了 (周兴哲)
10. 潮汐 (傅梦彤)
11. 泡沫 (邓紫棋)
12. 如果可以 (韦礼安)
13. 小幸运 (田馥甄)
14. 不舍 (王晰)
15. 平凡之路 (朴树)
16. 小苹果 (筷子兄弟)
17. 丑八怪 (薛之谦)
18. 像晴天像雨天 (汪苏泷)
19. 起风了 (买辣椒也用券)
20. 立冬 (音阙诗听)
21. 孤勇者 (陈奕迅)

## Finding Lyric Videos

Search YouTube: `[song name in Chinese] 歌词 pinyin`. Add `简体` if results default to traditional characters.

## Study Routine Integration

| Activity | Purpose | Frequency |
| --- | --- | --- |
| **Anki SRS** | Character recognition & recall (RSH order) | Daily, 5 new/day |
| **Song learning** | Motivation, context, pronunciation, tones | Alongside Anki |
| **DuChinese** | Graded reading comprehension | Regular |
| **HelloChinese** | Structured grammar & vocabulary | Regular |
| **Private tutoring** | Speaking, correction, cultural nuance | 2 hrs/week |

## Research: Why Multi-Modal Works

- **Spaced repetition (Anki)** — most proven technique for long-term retention via active recall + optimal spacing
- **Songs as mnemonic hooks** — melody creates additional memory cues beyond isolated flashcards ([Cambridge](https://www.cambridge.org/core/journals/language-and-cognition/article/working-memory-modulates-the-effect-of-music-on-word-learning/3C3A31EE290FA601AB601FE1C4602A9E))
- **Music + standard learning > either alone** for verbal memory ([Frontiers in Psychology, 2025](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2025.1659705/pdf))
- **Graded reading (DuChinese)** — reinforces recognition at speed in natural sentences
- **Structured apps (HelloChinese)** — fill grammar gaps that songs and flashcards miss
- **Tutoring** — real-time output practice no app can replicate

**Caveat:** Don't study Anki cards while listening to music with lyrics — processing two verbal streams hurts retention ([PMC, 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10162369/)).

## Notes

- "Non-RSH" characters are mostly onomatopoeia and literary compounds — see [song-characters-not-in-deck.md](song-characters-not-in-deck.md) for study guidance
- Continue RSH-order study alongside songs; many characters will be learned naturally through Anki, shortening the timeline
- After unsuspending a batch, expect a review spike — see the [Retention Guide](anki-retention-guide.md) for pacing adjustments
- Pace: 5 new chars/day (10 cards: production + recognition). Tried 6/day but recall dropped to low 80s.
