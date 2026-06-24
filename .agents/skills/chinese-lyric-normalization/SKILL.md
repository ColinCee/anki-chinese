---
name: chinese-lyric-normalization
description: Use when auditing or changing anki-chinese song lyrics, song planning, or mainland-simplified study normalization. Distinguishes traditional particle 著 -> 着 from lexical 著 and keeps runtime song commands deterministic.
when_to_use: Trigger on requests mentioning lyric normalization, Taiwanese/traditional lyric variants, 著/着, mainland Mandarin study target, song activation character planning, or reviews of src/anki_chinese/songs and data/songs/lyrics changes.
argument-hint: "[lyric-file-or-pr]"
---

# Chinese Lyric Normalization

## First response checklist

When this skill is relevant:

1. Treat lyric normalization as **offline curation**, not runtime inference.
2. Do not add an LLM, network call, OpenCC pass, or pypinyin-based guess to
   `songs analyze`, `songs next`, or `songs activate`.
3. Read the relevant lyric line and nearby context before classifying a variant.
4. Preserve source fidelity with explicit metadata if direct lyric edits are not
   desired.
5. Add regression coverage for the curated decision.

## Instructions

Do not add an LLM, network call, or remote API dependency to runtime song
planning. Runtime commands such as `uv run anki-chinese songs analyze`,
`songs next`, and `songs activate` should remain deterministic, fast,
credential-free, and testable.

For each candidate traditional form:

1. Decide whether the lyric usage maps to the mainland simplified study form.
2. Apply that decision explicitly in curated lyric text or in sidecar metadata.
3. Add a regression/audit test so future song planning does not silently drift.

For `著` specifically:

- Normalize aspect/state particle uses to `着`.
  Examples: `看著 -> 看着`, `忙著 -> 忙着`, `抱著 -> 抱着`, `带著 -> 带着`.
- Preserve lexical `zhù` words that are still written with `著` in simplified.
  Examples: `著名`, `著作`, `著书`, `专著`, `原著`, `显著`, `名著`, `拙著`, `巨著`.
- Mark genuinely ambiguous cases for human review instead of guessing.

Do not treat `著` as globally wrong. Remaining lexical `著` can be correct.

## Recommended workflow

1. Read the project policy docs first:
   - `docs/decisions/study-target-policy.md`
   - `docs/workflows.md`
   - `docs/architecture.md`
2. Collect candidate occurrences from lyric files:
   ```bash
   rg -n "著|臺|台|妳|裏|裡" data/songs/lyrics
   ```
3. For each occurrence, inspect the full lyric line and neighboring lines.
4. Classify each occurrence as:
   - `normalize`: source form should map to a simplified study form
   - `preserve`: source form is lexical, a name, a quote, or intentionally traditional
   - `review`: ambiguous or not enough context
5. Prefer editing curated lyric files directly when the repo policy allows
   simplified-mainland lyrics.
6. If source fidelity must be preserved, use explicit metadata or a sidecar
   mapping instead of a heuristic hidden inside `extract_cjk`.
7. Add tests that lock in the curation outcome.

## If reviewing a PR

Focus on whether the PR:

1. Makes normalization decisions explicit and testable.
2. Keeps song planning deterministic and credential-free.
3. Avoids broad neighbor-character heuristics for `著`.
4. Avoids blind OpenCC or pypinyin discrimination for `著`.
5. Does not reject valid lexical `著` in future lyrics.

## Output format for audits

When asked to audit, return a compact table:

| File | Line | Text | Decision | Study form | Reason |
| --- | ---: | --- | --- | --- | --- |
| `data/songs/lyrics/example.md` | 12 | `看著你` | normalize | `看着你` | aspect particle `zhe` |
| `data/songs/lyrics/example.md` | 20 | `著名` | preserve | `著名` | lexical `zhù`; simplified also uses `著` |

Then summarize:

- number normalized
- number preserved
- number requiring review
- files changed, if edits were requested

## Test guidance

Avoid tests like "no lyric file contains `著`"; they reject valid lexical `著`.
Prefer one of these:

- explicit audited-file expectations for known replacements
- an allowlist of remaining lexical `著` occurrences with reasons
- a sidecar-normalization test that verifies runtime song planning uses curated mappings

Good regression examples:

```python
assert normalize_lyric_text_for_study("我看著你") == "我看着你"
assert normalize_lyric_text_for_study("這本專著很著名") == "這本專著很著名"
```

If the implementation relies on curated text rather than a runtime normalizer,
test the actual lyric files or sidecar mapping instead.

## Review guidance

Flag PRs that:

- add broad neighbor-character heuristics for `著`
- make runtime song planning call an LLM or remote API
- use OpenCC blindly for `著`, because common configurations either leave
  particle `著` unchanged or incorrectly convert lexical words like `專著`
- use pypinyin as the discriminator for traditional particle `著`, because it
  commonly reads lyric contexts like `看著` as `zhù`

Prefer PRs that:

- make curation decisions explicit
- preserve runtime determinism
- include audit coverage for remaining traditional/variant forms
- document ambiguous cases instead of hiding guesses in code
