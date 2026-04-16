# Anki Retention & Pacing Guide

## The 85–90% Rule

Research (Wozniak/SuperMemo, FSRS) shows **90% retention** minimises total study time per remembered item.

| Target Retention | Outcome |
| --- | --- |
| < 80% | Forgetting too much — review death spiral. Reduce new cards. |
| 80–85% | Inefficient — relearning many failed cards. Hold or reduce. |
| **85–90%** | **Sweet spot.** Efficient, sustainable. Safe to hold or cautiously increase. |
| 90–95% | Strong but review-heavy. Fine if you have time. |
| > 95% | Diminishing returns — 90→95% nearly doubles reviews. |

Sources: [FSRS Optimal Retention](https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-optimal-retention) · [Wozniak](https://supermemo.guru/wiki/Optimum_retention) · [FSRS vs SM-2](https://memstride.com/blog/fsrs-vs-sm2-algorithm-comparison/)

## Reading Your Stats

Deck → gear → **Statistics**. Key metric: **True Retention Rate** — pass rate of cards with interval ≥ 1 day (filters out same-day learning steps).

- **Young cards** (interval < 21 d) — naturally lower retention.
- **Mature cards** (interval ≥ 21 d) — reflects long-term memory.
- **Focus on "Last month"** — smooths daily variance.

| Monthly Retention | Interpretation | Action |
| --- | --- | --- |
| < 80% | Overloaded | Reduce new cards/day by 2–4. Clear backlog. |
| 80–85% | Borderline | Hold pace. Don't add until > 85%. |
| 85–90% | Healthy | Safe to increase by 1–2 cards/day. |
| > 90% | Strong capacity | Try +2–4 cards/day for a week, then re-check. |

## Adjusting New Cards/Day

### Increasing (currently 6/day)

Increase only if **all** hold:

1. Monthly retention **> 85%**
2. No review backlog building
3. Daily reviews feel manageable

Safe method: raise by **2 cards/day** (6→8), run for **2 full weeks**, drop back if retention falls below 85%.

### Decreasing

Decrease if **any** hold:

1. Monthly retention **< 80%**
2. Reviews consistently piling up
3. Mature retention **< 85%**

### After Unsuspending Song Characters

Unsuspending a batch (e.g. 62 from 学猫叫) causes a review spike over 1–2 weeks and a temporary retention dip. Consider reducing regular new cards (e.g. 6→4/day) to compensate.

## Button Strategy

Goal: **maximum retention per review spent**.

| Button | Effect | Review Cost |
| --- | --- | --- |
| **Again** | Resets to learning steps; wipes interval. | Very high — dozens of reviews to rebuild |
| **Hard** | Shortens next interval; preserves progress. | Low — one extra cycle |
| **Good** | Normal interval progression. | Baseline |
| **Easy** | Longer-than-normal interval. | Lowest |

| Button | Use When |
| --- | --- |
| **Again** | Wrong character, blank, or totally wrong sound. True failure. |
| **Hard** | Right character but wrong tone, or significant hesitation. |
| **Good** | Correct character and tone with reasonable recall. |
| **Easy** | Instant recognition — zero thought needed. |

### Why Hard Matters

Pressing Again on a 30-day card sends it to step 1 — dozens of unnecessary reviews for something you partially knew. Hard preserves progress while scheduling an earlier review. Use it for tone errors.

### Note on My w1 Parameter

Current w1 (Hard stability) is 0.10, nearly identical to w0 (Again). FSRS sees little difference between Hard and Again outcomes, likely because:

1. Only ~2,277 reviews — model still noisy
2. Tone errors are genuinely hard to fix
3. Prior character knowledge creates a bimodal pattern

As data accumulates, w1 should separate from w0. **Re-optimise monthly.**

## FSRS

Anki's old SM-2 uses one fixed formula for everyone. FSRS models your **personal** forgetting curve via ML trained on your review history.

- **Personalised scheduling** — learns how fast *you* forget
- **~20–30% fewer reviews** for the same retention vs SM-2
- **Adapts over time** — re-optimising updates the model
- Based on Wozniak's DSR memory model

Sources: [FSRS technical](https://expertium.github.io/Algorithm.html) · [FSRS vs SM-2](https://memstride.com/blog/fsrs-vs-sm2-algorithm-comparison/) · [Parameter interpretation](https://deepwiki.com/open-spaced-repetition/fsrs-optimizer/7.1-parameter-interpretation)

### "Optimize All"

Analyses your review history and trains 21 weights controlling: forgetting rates (new vs mature), difficulty effects, stability growth after success, and lapse impact.

**Re-optimise every 1–2 months** or after a big change (e.g. unsuspending 62 song characters).

### My Parameters (April 2025)

```
0.1013, 0.1013, 0.6393, 19.8303, 6.6198, 0.5322, 3.0858, 0.1049,
1.7148, 0.2659, 0.6517, 1.4864, 0.0937, 0.2831, 1.7131, 0.4232,
2.0748, 0.6312, 0.0656, 0.0741, 0.1331
```

Compared to FSRS-6 defaults (`0.212, 1.293, 2.307, 8.296, ...`):

| Parameter | Mine | Default | Meaning |
| --- | --- | --- | --- |
| w0 (Again stability) | **0.10** | 0.21 | Failed cards fade faster (~2.4 hrs vs ~5 hrs) |
| w1 (Hard stability) | **0.10** | 1.29 | Hard cards also fade very quickly — behave like Again |
| w2 (Good stability) | **0.64** | 2.31 | Good cards stick ~15 hrs vs ~2.3 days — need more early reps |
| w3 (Easy stability) | **19.83** | 8.30 | Easy cards stick much longer (~20 days vs ~8) — when it clicks, it stays |

**Pattern: "slow start, strong finish."** New cards need heavy early repetition (low w0–w2), but once something sticks it's durable (high w3). Normal for character-based learning. This is exactly why FSRS beats SM-2 for me — SM-2 gives intervals too long early and too short later.

## My Stats (April 2025)

| Period | Young | Mature | Total |
| --- | --- | --- | --- |
| Today | 89.7% | 100.0% | 90.7% |
| Yesterday | 91.2% | 100.0% | 92.1% |
| Last week | 88.8% | 92.6% | 89.1% |
| Last month | 83.1% | 86.0% | 83.2% |
| Last year | 81.9% | 86.4% | 82.0% |

**Assessment:** Monthly retention at 83% — hold at 6 cards/day. Upward trend (82% yearly → 89% weekly) is encouraging. After 学猫叫 batch stabilises, if monthly hits 85%+, try 8/day.
