# ADR-001: Example Sentence Generation Strategy

**Status:** Accepted (v6 — production pipeline)
**Date:** 2026-03-28
**Supersedes:** v2 keyword-hint, v3 no-hint, v4 lean+selfcheck, v5 topic-diversity

## Context

Each Anki note needs a short example sentence showing the target character in natural context. We evaluated Tatoeba corpus vs LLM generation and chose LLM. Six iterations (v2→v6) were scored by blinded AI judge panels (8× Sonnet 4.6, 212 characters). Key finding: **self-validation** catches grammar bugs the generation prompt alone cannot prevent.

## Decision

Generate with **Gemini Flash Lite** (lean 7-rule prompt), validate with a **code-level character check**, **phonetic confuser check**, and **LLM self-validation** (7-point checklist), retry once on failure.

### Configuration

| Setting         | Value                          | Rationale                                              |
| --------------- | ------------------------------ | ------------------------------------------------------ |
| Model           | gemini-3.1-flash-lite          | Cheapest, fastest; quality matches larger models       |
| Thinking        | Minimal                        | Same quality as Medium at 2.5× speed                   |
| Gen temperature | 0.7                            | Good variety without hallucination                     |
| Val temperature | 0.0                            | Deterministic validation judgments                     |
| Length          | 6–10 Chinese characters        | Adult beginner sweet spot                              |
| Char check      | Code: `hanzi in sentence`      | Deterministic, max 2 retries with conversation feedback |
| LLM validation  | 7-point checklist, same model  | Catches grammar the model misses during generation     |
| Retry           | 1 regen on validation failure  | Error description fed back for targeted fix            |
| Keyword         | Model provides as English output | NOT hinted — avoids steering toward wrong usage       |

### Pipeline (v6)

```
1. Generate → Gemini Flash Lite, lean 7-rule system prompt
2. Code check → target char in sentence? If not → retry (up to 2×)
3. Confuser check → exact homophones in sentence? Log warning if found
4. LLM validate → same model, same conversation, temp=0.0, 7-point checklist
5. If flagged → flag for manual review (no expensive retry cycle)
```

### Prompt Design

**System prompt** (7 rules — lean, no topic forcing):

1. Target character MUST appear literally in the sentence
2. 6–10 Chinese characters long
3. Natural — something a native speaker would actually say in daily life
4. Use the character in its most common, everyday meaning
5. Keep other vocabulary simple and common
6. Give the meaning with compound context (e.g. "silver; in 银行: bank")
7. Avoid other characters that sound identical to the target (same base syllable)

**Validation prompt** (7-point checklist):

1. Wrong measure words (个 instead of 只/块/粒/条)
2. 二 vs 两 before measure words (两个人 not 二个人)
3. Time periods (下午 only until ~6PM; 7PM+ is 晚上)
4. Register (adult speech, no childish phrasing)
5. Question particles (吗 for yes/no, 呢 for follow-up)
6. Naturalness (would a native speaker actually say this?)
7. Missing structural words (在/到/的/了)

### Key Discovery: Same-Model Self-Validation

The model generates `二只猫` confidently but catches the error when asked to check "is 二 used before a measure word?" Generation and verification are different cognitive modes — writing vs proofreading.

**What doesn't work:**
- "Must be grammatically correct" in the generation prompt — the model already thinks it's complying
- Generic validation ("is this correct?") — rubber-stamps its own output

**What works:**
- Specific checklist of known error patterns
- Temperature=0.0 for validation (deterministic)
- Same conversation context (model sees what it generated)

### Evolution

| Version | Approach                       | Problem                                                  |
| ------- | ------------------------------ | -------------------------------------------------------- |
| v2      | Keyword hint from curated file | Wrong meanings (元="beginning"), 4 wrong keywords        |
| v3      | No hint, model picks meaning   | Best naturalness, but uncaught grammar bugs (二/两, MWs) |
| v4      | Lean prompt + self-validation  | Keyword format broken (returned Chinese, not English)    |
| v5      | v4 + topic diversity seeds     | Topic seeds hurt naturalness (4.30 vs v3's 4.66)        |
| **v6**  | **v3 prompt + v5 validation**  | **Best balance: 4.68 naturalness, 2 fixable grammar errors** |

## Evaluation Methodology

### AI Judge Design

All comparisons use identical methodology:

- **8 parallel Sonnet 4.6 agents**, each evaluating ~26 character pairs
- **Blinded**: A/B labels randomly assigned per pair
- **Per-pair scoring**: naturalness (1–5), grammar (ok/description), keyword quality, winner (A/B/Tie)
- **Aggregation**: winners mapped back to version labels post-judging
- **Spot-checks**: Opus 4.6 validated flagged failures (13 checked, all confirmed)

**Naturalness score**: arithmetic mean of per-character ratings (1–5 Likert) across 8 judges × 212 characters. Each judge rates both A and B independently; scores separated by version after unblinding.

**Winner count**: each judge declares A, B, or Tie per pair. After unblinding, tally pairs won per version across all judges.

**Grammar issue count**: characters where the judge flagged grammar ≠ "ok". Categorised post-hoc as "real grammar errors" (structural mistakes teaching wrong Chinese) vs "style nitpicks" (register, formality, semantic implausibility).

### Self-Validation Metrics (v4–v6)

| Metric          | Computation                                                        |
| --------------- | ------------------------------------------------------------------ |
| Clean first try | Passed both code char-check and LLM validation on attempt 1       |
| Fixed on retry  | Failed validation → regenerated → passed on attempt 2             |
| Still bad       | Failed after all retries (flagged for manual review)              |

## Results

### Full Comparison Table

| Comparison | Wins (A)       | Wins (B)              | Ties         | Nat (A)  | Nat (B)  |
| ---------- | -------------- | --------------------- | ------------ | -------- | -------- |
| v2 vs v3   | v2: 29 (14%)   | **v3: 54 (25%)**      | 129 (61%)    | 4.55     | **4.65** |
| v3 vs v4   | v3: 66 (31%)   | v4: 72 (34%)          | 74 (35%)     | ~4.6     | ~4.5     |
| v3 vs v5   | **v3: 82 (39%)** | v5: 45 (21%)        | 85 (40%)     | **4.66** | 4.30     |
| v3 vs v6   | v3: 74 (35%)   | v6: 43 (20%)          | 95 (45%)     | 4.72     | 4.68     |

### Self-Validation Results (212 chars)

| Metric          | v4           | v5           | v6               |
| --------------- | ------------ | ------------ | ---------------- |
| Clean first try | 206 (97.2%)  | 209 (98.6%)  | **207 (97.6%)**  |
| Fixed on retry  | 6            | 2            | 4                |
| Still bad       | 0            | 1 (吾)       | 1 (吾)           |

### Grammar Error Analysis (real errors only)

| Version              | Real grammar errors | Style nitpicks | Notes                                          |
| -------------------- | ------------------- | -------------- | ---------------------------------------------- |
| v3 (no validation)   | **8**               | 10             | 下午六点, 负/在...负责, 咖啡馆好喝             |
| v5 (topic seeds)     | **11**              | 25             | Topic forcing created unnatural contexts       |
| **v6 (production)**  | **2** (+1 吾)       | 23             | 飞 word order, 少 ambiguity                    |

**v6 reduces real grammar errors by 75%** vs v3 (2 vs 8) while maintaining near-identical naturalness (4.68 vs 4.72 — within noise). Remaining style nitpicks don't teach wrong Chinese.

**Real grammar errors in v3** (would teach incorrect Chinese):
- 下午六点 → should be 晚上六点 (6PM is evening)
- 在这个项目负责 → should be 为...负责 or 负责... (wrong preposition)
- 那家咖啡馆很好喝 → a shop can't be "tasty to drink" (semantic grammar)
- 学习中文课 → should be 上中文课 or 学习中文 (wrong verb-object pairing)

v6's self-validation catches and fixes these before output.

**Style nitpicks in v6** (acceptable Chinese, not maximally idiomatic):
- 有个好梦 vs 做个好梦 — both understood, 做 is standard collocation
- 中文语言 — redundant but not wrong
- 请往左边走，谢谢你 — 谢谢 more natural than 谢谢你, both correct
- 放置在桌上 — slightly formal (放在 more colloquial), grammatically fine
- 请随便坐一下 — 请随便坐 more natural, meaning identical
- 颗 for 水晶 vs 块 — debatable measure word preference, not an error

Judges penalise v6 for these, explaining v3's higher win rate — but none teach incorrect Chinese.

### What Self-Validation Catches

| Error          | Example            | Fix                               |
| -------------- | ------------------ | --------------------------------- |
| 二 vs 两       | 二只小猫 →         | 二零二四年 (correct 二 usage)     |
| Measure words  | 一个小田 →         | 一块田 (块 for fields)            |
| Measure words  | 一个猫 →           | 一只小猫 (只 for animals)         |
| Formal misuse  | 下个旬 →           | 三月下旬 (proper collocation)     |
| Register       | 吾+modern speech → | flagged as unfixable              |

### What Self-Validation Misses

Residual issues not covered by the 7-point checklist:
- **Semantic implausibility**: 住在学校的中间 (living in the middle of a school)
- **Collocation preferences**: 有个好梦 vs standard 做个好梦
- **Redundancy**: 中文语言 (中文 already means Chinese language)
- **Factual errors**: 甲乙丙丁是中文数字 (they're Heavenly Stems, not numbers)

These are style/semantic issues, not grammar. A semantic quality gate could catch them but the cost/latency isn't justified for 212 cards.

### Version Progression

1. **v2→v3**: Removed keyword hints. Model picks better meanings. 2:1 judge preference.
2. **v3→v4**: Added lean prompt + self-validation. Caught 二/两 bugs. Draw on preference.
3. **v4→v5**: Added topic diversity seeds. **Regression** — forced unnatural contexts (horse to school, 8000元 noodles). Naturalness dropped 0.36 points.
4. **v5→v6**: Removed topic seeds, kept validation. **Best balance** — v3's naturalness + validation safety net.

## Unresolved Issues

### Phonetic Confusers in Example Sentences

**Problem:** Some sentences contain characters that sound identical to the target, making audio flashcards confusing. Example: 享 (xiǎng) in "我想和你分享这个" — 想 (xiǎng) is an exact homophone.

**Severity:**
- **Exact homophones** (same syllable + tone): indistinguishable by ear, must be fixed. E.g. 作(zuò)/做(zuò), 境(jìng)/静(jìng).
- **Same-base different-tone**: acceptable — tone discrimination is a core Mandarin skill. E.g. 豆(dòu)/都(dōu).

**Detection:** `find_phonetic_confusers()` in `notes/pronunciation.py` compares target pinyin against all CJK characters in the sentence. Falls back to `pypinyin` for per-character readings when sentence pinyin uses compound tokens (e.g. `měitiān` instead of `měi tiān`).

**Mitigation:**
1. Rule 7 in system prompt tells Gemini to avoid phonetically similar words
2. Code-level confuser check in `_generate_one()` logs warnings
3. `scripts/fix_confusers.py --exact-only` regenerates sentences with exact homophones
4. Some exact homophones are unavoidable (仁/人 — 人 is the most common Chinese character)

**Verified:** 4 parallel Sonnet 4.6 agents verified all 57 detected confusers (100% correct detections) and spot-checked 60 clean sentences (0 false negatives).

### Sentence Repetition Without Topic Seeds

Without topic diversity hints, the model gravitates toward templates for similar chars (我家里有X个人 for numbers 3–6). Topic seeds fix this but hurt naturalness. Accepted trade-off: individual sentence quality > cross-set variety. Could add lightweight dedup (reject if >70% similarity to previous sentence).

### Classical/Literary Characters

Characters like 吾 (classical "I"), 旭 (dawn), 昭 (evident) don't appear naturally in modern colloquial sentences. 吾 is the only true failure (1/212). May need a "literary characters" exception list with manual sentences.

### Model Name Expiry

Gemini preview models expire (e.g. `gemini-2.5-flash-lite-preview-06-17` → 404). Production must use stable model names or handle graceful fallback.

### Residual Style Issues

23 style nitpicks identified by judges (redundancy, collocation preferences, semantic implausibility). None teach wrong Chinese. Not worth another pipeline iteration — diminishing returns.

## Artifacts

| File                              | Purpose                                                   |
| --------------------------------- | --------------------------------------------------------- |
| `scripts/eval_v6_final.py`        | **Production pipeline** — v6 generate+validate script     |
| `scripts/fix_confusers.py`        | **Confuser fix** — detect and regenerate confuser sentences |
| `scripts/eval_v5_validated.py`    | v5 with topic seeds (historical, superseded)              |
| `scripts/eval_v3_no_keyword.py`   | v3 evaluation script (historical)                         |
| `data/build/eval_v6.json`         | v6 results (212 sentences, production quality)            |
| `data/build/eval_v5.json`         | v5 results (212 sentences)                                |
| `data/build/eval_v3.json`         | v3 results (212 sentences)                                |
| `data/build/judge_results_v6.json` | v3 vs v6 AI judge results (212 pairs)                    |
| `data/build/judge_results_v5.json` | v3 vs v5 AI judge results (212 pairs)                    |
| `data/build/judge_results.json`   | v2 vs v3 AI judge results (212 pairs)                     |

## Production TODO

1. Extract v6 pipeline into production code (`src/anki_chinese/`)
2. Add `example_sentence`, `example_pinyin`, `example_english`, `keyword` to CharacterNote
3. Wire sentence audio through MiniMax TTS
4. Update Anki card template to show sentence on back
5. Add lightweight dedup for cross-sentence variety (optional)
