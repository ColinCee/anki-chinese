# Song Characters Not in RSH Deck

41 unique characters appear across the 21 song lyrics but are absent from the RSH (Remembering Simplified Hanzi) deck. These characters fall outside Heisig's curated set — most are literary, onomatopoeic, or only meaningful as part of a compound.

This doc categorises each character to guide study priorities. To regenerate the raw character list:

```bash
uv run scripts/analyze_songs.py non-rsh
```

## Worth Learning (~15)

Characters that appear in everyday reading, news, or conversation. Worth adding to active vocabulary.

| Char | Pinyin | Key Compound | Meaning | Song(s) |
|------|--------|-------------|---------|---------|
| 疚 | jiù | 内疚 | guilt, remorse | 搁浅 |
| 狈 | bèi | 狼狈 | in a difficult/awkward situation | 如果可以 |
| 堕 | duò | 堕落 | to degenerate, fall | 平凡之路 |
| 怯 | qiè | 胆怯 | timid, cowardly | 起风了 |
| 溺 | nì | 溺水, 沉溺 | to drown, indulge | 起风了 |
| 拽 | zhuài | 拽住 | to drag, pull (very colloquial) | 小苹果 |
| 褪 | tuì | 褪色 | to fade (colour) | 立冬 |
| 掐 | qiā | 掐指 | to pinch, count on fingers | 立冬 |
| 垢 | gòu | 污垢 | dirt, filth | 孤勇者 |
| 诀 | jué | 秘诀, 诀别 | secret/knack; to bid farewell | 不舍 |
| 弈 | yì | 博弈 | game theory, to play chess | 孤勇者 |
| 炽 | chì | 炽热 | blazing, fervent | 星辰大海, 泡沫 |
| 峙 | zhì | 对峙 | to stand off, confront | 孤勇者 |
| 冥 | míng | 冥想, 冥冥 | meditation; fate/darkness | 平凡之路 |
| 暧 | ài | 暧昧 | ambiguous, flirtatious | 丑八怪 |

## Literary Pairs (~10 chars, 5 compounds)

These characters only ever appear as part of a fixed two-character compound. Learn the compound, not the individual character.

| Compound | Pinyin | Meaning | Song(s) |
|----------|--------|---------|---------|
| 憧憬 | chōngjǐng | to long for, yearn | 潮汐, 不舍 |
| 蹒跚 | pánshān | to stagger, toddle | 起风了 |
| 徜徉 | chángyáng | to wander leisurely | 小苹果 |
| 褴褛 | lánlǚ | ragged, tattered | 孤勇者 |
| 聆听 | língtīng | to listen attentively | 潮汐, 不舍 |

## Onomatopoeia & Interjections (~3)

Just recognise from context — no formal study needed.

| Char | Pinyin | Usage | Note |
|------|--------|-------|------|
| 喵 | miāo | meow | Appears dozens of times in 学猫叫. Impossible to forget. |
| 怦 | pēng | 怦怦跳 (heart thumping) | Sound-symbolic, self-explanatory in context. |
| 唔 | wú/ń | hmm, interjection | Cantonese-flavoured filler, very informal. |

## Poetic / Low Priority (~10)

Literary vocabulary that enriches reading but rarely appears in daily life. Recognise passively.

| Char | Pinyin | Key Compound | Meaning | Song(s) |
|------|--------|-------------|---------|---------|
| 谧 | mì | 静谧 | tranquil, serene | 潮汐 |
| 眸 | móu | 眸子 | eye, pupil (poetic) | 不舍 |
| 扉 | fēi | 心扉 | door (literary); heart's door | 立冬 |
| 汐 | xī | 潮汐 | evening tide | 潮汐 |
| 鬓 | bìn | 鬓角 | temple hair (sideburns) | 起风了 |
| 凋 | diāo | 凋零 | to wither, wilt | 泡沫 |
| 绚 | xuàn | 绚丽 | gorgeous, dazzling | 像晴天像雨天 |
| 汲 | jí | 汲取 | to draw (water/lessons) | 像晴天像雨天 |
| 叩 | kòu | 叩门 | to knock (formal) | 立冬 |
| 晦 | huì | 晦涩 | obscure, hard to understand | 立冬 |
| 迂 | yū | 迂回 | roundabout, circuitous | 立冬 |

## Suspect / Not Worth Learning (~3)

Likely data issues or non-standard characters.

| Char | Pinyin | Issue | Action |
|------|--------|-------|--------|
| 妳 | nǐ | Traditional Chinese form of 你 (female). Not used in Simplified Chinese — opencc should have converted this. | Check lyrics files for 妳 and replace with 你. |
| 蛞 | kuò | As in 蛞蝓 (slug). Extremely unusual in song lyrics — likely an LRCLIB transcription error. | Check which song contains it and verify lyrics. |
| 墟 | xū | Archaic variant meaning ruins. Extremely rare in modern Chinese. | May be intentional poetic usage in 孤勇者 — verify. |

## Summary

| Category | Count | Study Approach |
|----------|-------|---------------|
| Worth learning | 15 | Active study — add to personal vocab list |
| Literary pairs | 10 | Learn as compounds, not solo characters |
| Onomatopoeia | 3 | No study needed — context is enough |
| Poetic / low priority | 10 | Passive recognition from reading |
| Suspect / skip | 3 | Verify and fix in lyrics data |
| **Total** | **41** | |
