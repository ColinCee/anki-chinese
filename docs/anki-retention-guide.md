# Anki Retention & Pacing Guide

A reference for how to read your Anki stats and when to adjust your new cards per day.

## The Core Principle: The 85-90% Rule

Spaced repetition research (Piotr Wozniak/SuperMemo, and the modern FSRS algorithm) consistently shows that **90% retention** is the sweet spot — it minimises total study time per remembered item.

| Target retention | What happens |
|---|---|
| Below 80% | You're forgetting too much. Cards keep coming back as lapses, creating a review death spiral. Reduce new cards. |
| 80–85% | Workable but inefficient — you're relearning a lot of failed cards. Hold steady or reduce new cards until this climbs. |
| **85–90%** | **The sweet spot.** Efficient learning with sustainable review load. Safe to hold or cautiously increase new cards. |
| 90–95% | Strong retention but review load is significantly higher. Good if you have the time and want near-perfect recall. |
| Above 95% | Diminishing returns. Going from 90% → 95% nearly doubles daily reviews for marginal gain. |

Sources:
- [FSRS Optimal Retention Wiki](https://github.com/open-spaced-repetition/fsrs4anki/wiki/The-optimal-retention)
- [Wozniak's SuperMemo research](https://supermemo.guru/wiki/Optimum_retention)
- [FSRS vs SM-2 comparison](https://memstride.com/blog/fsrs-vs-sm2-algorithm-comparison/)

## How to Read Your Stats

In Anki, go to the deck → gear icon → **Statistics**. The key numbers:

### True Retention Rate

`Pass rate of cards with an interval ≥ 1 day`

This filters out same-day learning steps (which are always low) and gives your real retention. Look at:

- **Young cards** (interval < 21 days) — recently learned, naturally lower retention
- **Mature cards** (interval ≥ 21 days) — these reflect long-term memory
- **Focus on the "Last month" row** — this smooths out daily variance and reflects your actual pace

### What the numbers mean

| Your monthly retention | Interpretation | Action |
|---|---|---|
| Below 80% | Overloaded — too many new cards or cards are too hard | Reduce new cards/day by 2–4. Let the backlog clear. |
| 80–85% | Borderline — you're managing but close to the edge | Hold current pace. Don't add more until this climbs above 85%. |
| 85–90% | Healthy — reviews are sustainable | Safe to increase by 1–2 cards/day if desired. |
| Above 90% | Strong — you likely have capacity for more | Try increasing by 2–4 cards/day for a week, then re-check. |

## When to Adjust New Cards Per Day

### Increasing (currently at 6/day)

Only increase if ALL of these are true:
1. Monthly retention is **above 85%**
2. You're completing all daily reviews (no backlog building)
3. Daily review count feels manageable (not dreading opening Anki)

How to increase safely:
- Go up by **2 cards/day** (6 → 8), not more
- Run it for **2 full weeks** before evaluating
- If monthly retention drops below 85%, drop back immediately

### Decreasing

Decrease if ANY of these are true:
1. Monthly retention is **below 80%**
2. Daily reviews are piling up (consistently not finishing)
3. You're hitting "Again" on mature cards frequently (mature retention below 85%)

### After Unsuspending Song Characters

When you unsuspend a batch of characters (like the 62 from 学猫叫), expect:
- A **spike in daily reviews** over the next 1–2 weeks as those new cards enter rotation
- A **temporary dip in retention** as you absorb the new load
- Consider **reducing your regular new cards** to compensate (e.g. 6 → 4/day for a week)

## Button Strategy: Maximise Retention Per Review

The goal isn't maximum retention (review everything daily) or minimum reviews (never study). It's the **best ratio of the two** — maximum retention per review spent.

Each button has a different cost:

| Button | Mechanical effect | Review cost |
|---|---|---|
| **Again** | Resets card to learning steps. Wipes interval progress. | **Very high** — potentially dozens of reviews to rebuild |
| **Hard** | Shortens next interval but keeps card in review queue. Progress preserved. | **Low** — one extra review cycle |
| **Good** | Normal interval progression. | **Baseline** |
| **Easy** | Longer-than-normal interval. | **Lowest** — fewer future reviews |

### When to press each button

| Button | Use when |
|---|---|
| **Again** | Wrong character, completely blank, or totally wrong sound. True failure. |
| **Hard** | Right character but wrong tone, or needed significant hesitation. Partial recall. |
| **Good** | Correct character and tone with reasonable recall. |
| **Easy** | Instant recognition — zero thought needed. |

### Why Hard matters

Pressing Again on a card with a 30-day interval sends it back to step 1. If you *mostly* knew the character but got the tone wrong, Again forces you to rebuild from scratch — that's dozens of unnecessary reviews for something you partially knew.

Hard preserves your progress while scheduling an earlier review. For tone errors (where you *did* recall the character, just imprecisely), this is far more efficient.

### A note on my w1 parameter

My current w1 (Hard stability) is 0.10 — almost identical to w0 (Again). This means FSRS currently sees little difference between my Hard and Again outcomes. This is likely because:
1. Only ~2,277 reviews so far — the model is still noisy
2. Tone errors are genuinely difficult to fix, so Hard cards do come back quickly
3. Prior character knowledge creates a bimodal pattern that confuses the model fit

As more review data accumulates, w1 should drift upward and separate from w0. **Re-optimise monthly** to check this.

## FSRS: A Better Algorithm

Anki's old SM-2 scheduler uses the same fixed formula for everyone. FSRS (Free Spaced Repetition Scheduler) models your **personal** forgetting curve using machine learning trained on your review history.

### Why FSRS is optimal

- **Personalised scheduling** — it learns how fast *you* forget, not some average person
- **~20-30% fewer reviews** for the same retention compared to SM-2
- **Adapts over time** — re-optimising updates the model as your memory improves
- Based on Piotr Wozniak's DSR (Difficulty, Stability, Retrievability) memory model, backed by decades of research

Sources:
- [FSRS technical explanation](https://expertium.github.io/Algorithm.html)
- [FSRS vs SM-2 comparison](https://memstride.com/blog/fsrs-vs-sm2-algorithm-comparison/)
- [FSRS parameter interpretation](https://deepwiki.com/open-spaced-repetition/fsrs-optimizer/7.1-parameter-interpretation)

### What "Optimize All" does

It analyses your entire review history and trains a machine learning model on your patterns. Specifically it calculates 21 parameters (weights) that control:

- How quickly you forget new vs mature cards
- How difficulty affects your retention
- How your memory stability grows after successful reviews
- How lapses (pressing "Again") affect future intervals

You should **re-optimise every 1-2 months** or after a big change (like unsuspending 62 song characters). More review data = more accurate model.

### My Current Parameters (April 2025)

```
0.1013, 0.1013, 0.6393, 19.8303, 6.6198, 0.5322, 3.0858, 0.1049,
1.7148, 0.2659, 0.6517, 1.4864, 0.0937, 0.2831, 1.7131, 0.4232,
2.0748, 0.6312, 0.0656, 0.0741, 0.1331
```

#### What these reveal about my learning

Comparing to FSRS-6 defaults (`0.212, 1.293, 2.307, 8.296, ...`):

| Parameter | Mine | Default | What it means |
|---|---|---|---|
| w0 (Again stability) | **0.10** | 0.21 | I forget failed cards faster than average — they need to come back sooner (~2.4 hrs vs ~5 hrs) |
| w1 (Hard stability) | **0.10** | 1.29 | "Hard" cards also fade very quickly for me — these behave almost like "Again" |
| w2 (Good stability) | **0.64** | 2.31 | "Good" cards stick for ~15 hrs vs the average ~2.3 days — I need more early repetitions |
| w3 (Easy stability) | **19.83** | 8.30 | But "Easy" cards stick much longer than average (~20 days vs ~8 days) — when something clicks, it really clicks |

**The pattern:** I'm a "slow start, strong finish" learner. New cards need heavy early repetition (lower w0-w2), but once something truly sticks it stays very well (high w3). This is completely normal for character-based learning where initial recognition is hard but visual memory is durable.

This is why FSRS matters for me specifically — SM-2 would give me intervals that are too long early on (causing failures) and too short later (wasting review time on cards I already know well).

## My Current Stats (April 2025)

| Period | Young | Mature | Total |
|---|---|---|---|
| Today | 89.7% | 100.0% | 90.7% |
| Yesterday | 91.2% | 100.0% | 92.1% |
| Last week | 88.8% | 92.6% | 89.1% |
| Last month | 83.1% | 86.0% | 83.2% |
| Last year | 81.9% | 86.4% | 82.0% |

**Assessment:** Monthly retention at 83% means I should hold at 6 cards/day. The upward trend (82% yearly → 89% this week) is encouraging. Revisit after the 学猫叫 batch stabilises — if monthly retention reaches 85%+, try increasing to 8/day.
