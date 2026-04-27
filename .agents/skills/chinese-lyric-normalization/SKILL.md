---
name: chinese-lyric-normalization
description: Offline audit workflow for Mandarin lyric study-target normalization in anki-chinese, especially distinguishing traditional particle 著 from lexical 著.
---

# Chinese Lyric Normalization

## When to use

Use this GitHub Copilot CLI skill when auditing or updating Chinese lyric files
for this repository's mainland Mandarin, simplified-first study target. It is
especially relevant when the task involves:

- `著` vs `着`
- Taiwanese/traditional lyric forms in otherwise Mandarin lyrics
- deciding whether a lyric character should activate a simplified study card
- creating or reviewing song-planning normalization changes in `anki-chinese`

## Instructions

Do not add an LLM, network call, or remote API dependency to runtime song
planning. Runtime commands such as `uv run anki-chinese songs analyze`,
`songs next`, and `songs activate` should remain deterministic, fast,
credential-free, and testable.

Treat lyric normalization as offline curation, not runtime inference.

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

## Recommended workflow

1. Read the project policy docs first:
   - `docs/decisions/ADR-003-study-target-policy.md`
   - `docs/guides/mainland-mandarin.md`
   - `docs/guides/song-activation.md`
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
