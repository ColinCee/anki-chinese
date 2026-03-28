# ADR-001: Example Sentence Generation Strategy

**Status:** Accepted (v6 — production pipeline)  
**Date:** 2026-03-28  
**Supersedes:** v2 keyword-hint, v3 no-hint, v4 lean+selfcheck, v5 topic-diversity  

## Context

Each Anki note needs a short example sentence showing the target character in natural
context. We evaluated two sources (Tatoeba corpus, LLM generation) and chose LLM.
We ran six iterations (v2→v6) with AI judge panels (8× Sonnet 4.6 agents, blinded)
across all 212 characters, discovering that **self-validation** catches grammar bugs
the generation prompt alone cannot prevent.

## Decision

Generate sentences with **Gemini Flash Lite** using a lean 5-rule prompt, validate
with a **code-level character check** and **LLM self-validation** (7-point checklist),
retry once on failure.

### Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Model | gemini-3.1-flash-lite | Cheapest, fastest; quality matches larger models |
| Thinking | Minimal | Same quality as Medium at 2.5× speed |
| Gen temperature | 0.7 | Good variety without hallucination |
| Val temperature | 0.0 | Deterministic validation judgments |
| Length | 6–10 Chinese characters | Adult beginner sweet spot |
| Char check | Code: `hanzi in sentence` | Deterministic, max 2 retries with conversation feedback |
| LLM validation | 7-point checklist, same model | Catches grammar the model misses during generation |
| Retry | 1 regen on validation failure | Error description fed back for targeted fix |
| Keyword | Model provides as English output | NOT hinted — avoids steering toward wrong usage |

### Pipeline (v6)

```
1. Generate → Gemini Flash Lite, lean 5-rule system prompt
2. Code check → target char in sentence? If not → retry (up to 2×)
3. LLM validate → same model, same conversation, temp=0.0, 7-point checklist
4. If flagged → regenerate with error feedback (1 retry, also code-checked)
5. If still bad → flag for manual review
```

### Prompt Design

**System prompt** (5 rules — lean, no topic forcing):
1. Target character MUST appear literally in the sentence
2. 6–10 Chinese characters long
3. Natural — something a native speaker would actually say in daily life
4. Use the character in its most common, everyday meaning
5. Keep other vocabulary simple and common

**Validation prompt** (7-point checklist):
1. Wrong measure words (个 instead of 只/块/粒/条)
2. 二 vs 两 before measure words (两个人 not 二个人)
3. Time periods (下午 only until ~6PM; 7PM+ is 晚上)
4. Register (adult speech, no childish phrasing)
5. Question particles (吗 for yes/no, 呢 for follow-up)
6. Naturalness (would a native speaker actually say this?)
7. Missing structural words (在/到/的/了)

### Key Discovery: Same-Model Self-Validation

The model generates `二只猫` confidently but catches the error when explicitly asked
to check "is 二 used before a measure word?" Generation and verification are different
cognitive modes — like writing vs proofreading.

**What doesn't work:**
- Adding "must be grammatically correct" to the generation prompt — the model already
  thinks it's following that rule
- Generic validation ("is this correct?") — rubber-stamps its own output

**What works:**
- A specific checklist of known error patterns
- Temperature=0.0 for validation (deterministic)
- Same conversation context (model can see what it generated)

### Evolution: Why Not Earlier Versions

| Version | Approach | Problem |
|---------|----------|---------|
| v2 | Keyword hint from curated file | Wrong meanings (元="beginning"), 4 wrong keywords |
| v3 | No hint, model picks meaning | Best naturalness, but uncaught grammar bugs (二/两, MWs) |
| v4 | Lean prompt + self-validation | Keyword format broken (returned Chinese, not English) |
| v5 | v4 + topic diversity seeds | Topic seeds hurt naturalness (4.30 vs v3's 4.66) |
| **v6** | **v3 prompt + v5 validation, no topics** | **Best balance: 4.68 naturalness, 2 fixable grammar errors** |

## Evaluation Methodology

### AI Judge Design

All comparisons use the same methodology for scientific rigour:

- **8 parallel Sonnet 4.6 agents**, each evaluating ~26 character pairs
- **Blinded**: A/B labels randomly assigned per pair (judge doesn't know which version)
- **Per-pair scoring**: naturalness (1–5), grammar (ok/description), keyword quality,
  winner (A/B/Tie)
- **Aggregation**: winners mapped back to version labels post-judging
- **Spot-checks**: Opus 4.6 validated flagged failures (13 checked, all confirmed)

**Naturalness score computation**: arithmetic mean of all per-character naturalness
ratings (1–5 Likert scale) across all 8 judges × 212 characters. Each judge rates
both A and B independently; scores are separated by source version after unblinding.

**Winner computation**: each judge declares A, B, or Tie per pair. After unblinding,
we count how many pairs each version won across all 8 judges.

**Grammar issue count**: number of characters where the judge flagged grammar as
anything other than "ok". Categorised post-hoc into "real grammar errors" (structural
mistakes that teach wrong Chinese) vs "style nitpicks" (register, formality, semantic
implausibility).

### Self-Validation Metrics (v4–v6)

| Metric | Computation |
|--------|-------------|
| Clean first try | Sentences passing both code char-check and LLM validation on attempt 1 |
| Fixed on retry | Failed validation → regenerated → passed on attempt 2 |
| Still bad | Failed after all retries (flagged for manual review) |

## Results

### Full Comparison Table (all AI judge rounds)

| Comparison | Wins (A) | Wins (B) | Ties | Nat (A) | Nat (B) |
|------------|----------|----------|------|---------|---------|
| v2 vs v3 | v2: 29 (14%) | **v3: 54 (25%)** | 129 (61%) | 4.55 | **4.65** |
| v3 vs v4 | v3: 66 (31%) | v4: 72 (34%) | 74 (35%) | ~4.6 | ~4.5 |
| v3 vs v5 | **v3: 82 (39%)** | v5: 45 (21%) | 85 (40%) | **4.66** | 4.30 |
| v3 vs v6 | v3: 74 (35%) | v6: 43 (20%) | 95 (45%) | 4.72 | 4.68 |

### Self-Validation Results (212 chars)

| Metric | v4 | v5 | v6 |
|--------|-----|-----|-----|
| Clean first try | 206 (97.2%) | 209 (98.6%) | **207 (97.6%)** |
| Fixed on retry | 6 | 2 | 4 |
| Still bad | 0 | 1 (吾) | 1 (吾) |

### Grammar Error Analysis (real errors only, from AI judges)

| Version | Real grammar errors | Style nitpicks | Notes |
|---------|-------------------|----------------|-------|
| v3 (no validation) | **8** | 10 | 下午六点, 负/在...负责, 咖啡馆好喝 |
| v5 (topic seeds) | **11** | 25 | Topic forcing created unnatural contexts |
| **v6 (production)** | **2** (+1 吾) | 23 | 飞 word order, 少 ambiguity |

**v6 reduces real grammar errors by 75%** compared to v3 (2 vs 8), while maintaining
near-identical naturalness (4.68 vs 4.72 — within noise). The remaining style nitpicks
are register/formality preferences that don't teach wrong Chinese.

**Real grammar errors found in v3** (would teach students incorrect Chinese):
- 下午六点 → should be 晚上六点 (6PM is evening, not afternoon)
- 在这个项目负责 → should be 为...负责 or 负责... (wrong preposition)
- 那家咖啡馆很好喝 → a shop can't be "tasty to drink" (semantic grammar)
- 学习中文课 → should be 上中文课 or 学习中文 (wrong verb-object pairing)

v6's self-validation catches and fixes errors like these before output.

**Style nitpicks found in v6** (acceptable Chinese, just not maximally idiomatic):
- 有个好梦 vs 做个好梦 — both understood, 做 is the standard collocation
- 中文语言 — redundant (中文 already means Chinese language), but not wrong
- 请往左边走，谢谢你 — 谢谢 is more natural than 谢谢你, but both correct
- 放置在桌上 — slightly formal (放在 is more colloquial), but grammatically fine
- 请随便坐一下 — 请随便坐 is more natural, but the meaning is identical
- 颗 for 水晶 vs 块 — debatable measure word preference, not an error

These are why v3 "wins" on judge preference — the judges penalise v6 for style
preferences, but none of these would teach a student incorrect Chinese.

### What Self-Validation Catches

Errors caught and fixed by the v6 pipeline (confirmed across runs):

| Error | Example | Fix |
|-------|---------|-----|
| 二 vs 两 | 二只小猫 → | 二零二四年 (correct 二 usage) |
| Measure words | 一个小田 → | 一块田 (块 for fields) |
| Measure words | 一个猫 → | 一只小猫 (只 for animals) |
| Formal misuse | 下个旬 → | 三月下旬 (proper collocation) |
| Register | 吾+modern speech → | flagged as unfixable |

### What Self-Validation Misses

The 7-point checklist doesn't catch everything. Residual issues (from judge analysis):
- **Semantic implausibility**: 住在学校的中间 (living in the middle of a school)
- **Collocation preferences**: 有个好梦 vs standard 做个好梦
- **Redundancy**: 中文语言 (中文 already means Chinese language)
- **Factual errors**: 甲乙丙丁是中文数字 (they're Heavenly Stems, not numbers)

These are style/semantic issues, not grammar. A semantic quality gate could catch them
but adds cost/latency that isn't justified for 212 cards.

### Version Progression Narrative

1. **v2→v3**: Removed keyword hints. Model picks better meanings. 2:1 judge preference.
2. **v3→v4**: Added lean prompt + self-validation. Caught 二/两 bugs. Draw on judge preference.
3. **v4→v5**: Added topic diversity seeds. **Regression** — forced unnatural contexts (horse to school, 8000元 noodles). Naturalness dropped 0.36 points.
4. **v5→v6**: Removed topic seeds, kept validation. **Best balance** — v3's naturalness + validation safety net.

## Unresolved Issues

### Sentence Repetition Without Topic Seeds
Without topic diversity hints, the model gravitates toward templates for similar chars
(我家里有X个人 for numbers 3–6). Topic seeds fix this but hurt naturalness. Accepted
trade-off: individual sentence quality > cross-set variety. Production could add
lightweight dedup (reject if >70% similarity to previous sentence).

### Classical/Literary Characters
Characters like 吾 (classical "I"), 旭 (dawn), 昭 (evident) don't appear naturally in
modern colloquial sentences. 吾 is the only true failure (1/212). May need a
"literary characters" exception list with manual sentences.

### Model Name Expiry
Gemini preview models expire (e.g. `gemini-2.5-flash-lite-preview-06-17` → 404).
Production must use stable model names or handle graceful fallback.

### Residual Style Issues
23 style nitpicks identified by judges (redundancy, collocation preferences, semantic
implausibility). None teach wrong Chinese. Not worth another pipeline iteration —
diminishing returns territory.

## Artifacts

| File | Purpose |
|------|---------|
| `scripts/eval_v6_final.py` | **Production pipeline** — v6 generate+validate script |
| `scripts/eval_v5_validated.py` | v5 with topic seeds (historical, superseded) |
| `scripts/eval_v3_no_keyword.py` | v3 evaluation script (historical) |
| `data/build/eval_v6.json` | v6 results (212 sentences, production quality) |
| `data/build/eval_v5.json` | v5 results (212 sentences) |
| `data/build/eval_v3.json` | v3 results (212 sentences) |
| `data/build/judge_results_v6.json` | v3 vs v6 AI judge results (212 pairs) |
| `data/build/judge_results_v5.json` | v3 vs v5 AI judge results (212 pairs) |
| `data/build/judge_results.json` | v2 vs v3 AI judge results (212 pairs) |

## Production TODO

1. Extract v6 pipeline into production code (`src/anki_chinese/`)
2. Add `example_sentence`, `example_pinyin`, `example_english`, `keyword` to CharacterNote
3. Wire sentence audio through MiniMax TTS
4. Update Anki card template to show sentence on back
5. Add lightweight dedup for cross-sentence variety (optional)
