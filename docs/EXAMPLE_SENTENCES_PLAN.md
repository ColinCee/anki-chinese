# Example Sentences for Character Audio

## Problem

Currently each note has three audio types:
1. **Character** — single character pronunciation (e.g., 一 → "yī")
2. **Example phrase** — a 2-3 character word using the character (e.g., 一起)
3. *(missing)* **Example sentence** — a short sentence showing natural usage

Hearing a character in escalating contexts (isolation → phrase → sentence) reinforces
both pronunciation and real-world usage patterns. This is a proven spaced repetition
technique.

## Requirements

Sentences must be:
- **Short** — 6-10 characters max (fits on a flashcard, quick to listen to)
- **Simple vocabulary** — HSK 1-3 level so learners understand the surrounding words
- **Natural** — things native speakers actually say, not textbook-sounding
- **Contextual** — the target character should be used in its primary meaning

## Data Source Options

### 1. Tatoeba (open-source sentence corpus)
- **Pros**: Large corpus, CC-licensed, community-reviewed, searchable by character
- **Cons**: Uneven quality, many sentences too long or unnatural, no HSK grading
- **Approach**: Query API for sentences containing the character, filter by length,
  cross-reference vocabulary against HSK word lists

### 2. HSK graded readers / textbook sentences
- **Pros**: Already difficulty-graded, natural, pedagogically sound
- **Cons**: Copyright concerns, limited coverage for rarer characters
- **Approach**: Curate manually from open HSK resources

### 3. LLM-generated sentences
- **Pros**: Fast, can specify exact constraints (length, HSK level, naturalness),
  covers every character
- **Cons**: Needs human review, may produce unnatural phrasing
- **Approach**: Prompt with character + meaning + HSK level constraint, batch generate,
  human review flagged ones

### 4. Hybrid (recommended)
- Use Tatoeba as primary source (filter: 6-10 chars, HSK 1-3 vocab)
- Fall back to LLM generation for characters with no good Tatoeba match
- Human review pass on all sentences before committing

## Implementation Plan

### Note model changes
- Add `example_sentence: str` field to `CharacterNote`
- Add `example_sentence_pinyin: str` for pronunciation control
- Add `example_sentence_audio: str` for the audio tag

### Audio generation
- New provider method: `generate_sentence_audio(sentence, pinyin)` — or reuse
  `generate_example_audio` with different filename prefix (`sent_` vs `cmn_`)
- Google TTS with `custom_pronunciations` for pinyin control
- MiniMax for expression/naturalness (better for longer text)

### Data pipeline
- New enrichment step: look up or generate example sentence per character
- Store in enriched notes JSON alongside existing fields
- `audio` command generates sentence audio alongside existing types

### Deck template
- Add sentence audio field to Anki card template
- Play after character + phrase audio on reveal

## Open Questions

- Should sentence audio use a different provider than character audio?
  (MiniMax sounds more expressive for longer text, Google more accurate for
  single characters)
- Should sentences be Mandarin-only or also Cantonese?
- How to handle characters that appear in many common sentences — which one to pick?
- Should the sentence be shown as text on the card, or audio-only?

## Priority

This is a **Phase 2 enhancement** — the current character + phrase audio is functional.
Sentence audio adds learning value but requires a data sourcing pipeline first.
