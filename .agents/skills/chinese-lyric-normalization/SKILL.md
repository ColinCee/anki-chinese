---
name: chinese-lyric-normalization
description: Use when auditing or changing anki-chinese song lyrics, song planning, or mainland-simplified study normalization. Distinguishes traditional particle 著 -> 着 from lexical 著 and keeps runtime song commands deterministic.
when_to_use: Trigger on requests mentioning lyric normalization, Taiwanese/traditional lyric variants, 著/着, mainland Mandarin study target, song activation character planning, or reviews of src/anki_chinese/songs and data/songs/lyrics changes.
argument-hint: "[lyric-file-or-pr]"
---

# Chinese Lyric Normalization

Treat normalization as offline curation. Runtime song planning must remain
deterministic, credential-free, and testable: no LLM, translation service,
OpenCC pass, or pypinyin guess.

For each candidate traditional form:

1. Read the full line and neighboring context.
2. Classify it as `normalize`, `preserve`, or `review`.
3. Encode the decision in curated lyric text or explicit sidecar metadata.
4. Add regression coverage for that decision.

For `著`, normalize aspect/state particle uses such as `看著` to `看着`.
Preserve lexical `zhù` words still written with `著` in simplified Chinese,
including `著名`, `著作`, `专著`, and `原著`. Send ambiguous cases to human
review; never use a global replacement or broad neighboring-character
heuristic.

Search candidates with:

```bash
rg -n "著|臺|台|妳|裏|裡" data/songs/lyrics
```

Prefer explicit expectations for audited files or an allowlist with reasons.
Do not test that all `著` characters are absent. Audit results should identify
the file, line, source text, decision, study form, and reason, followed by
counts for each decision.

The canonical policy is `docs/decisions/study-target-policy.md`; commands live
in `docs/workflows.md`.
