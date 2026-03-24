# MiniMax TTS decision note for `anki-chinese`

## Decision

We are standardizing the next TTS migration wave on **MiniMax `speech-2.8-turbo`**.

This is no longer a broad candidate-comparison plan. The decision has been narrowed intentionally so the repo can move forward with one clear target.

## Why MiniMax

MiniMax is the best fit for the repo’s current needs because it gives us:

- a premium Chinese-first speech product
- explicit `language_boost` support for:
  - `Chinese`
  - `Chinese,Yue`
- `pronunciation_dict` support
- a modern speech model family
- up to 10,000 characters per request
- streaming and non-streaming API options

That combination is enough to justify a focused migration without building a wide provider matrix first.

## How API setup and credits should work

The MiniMax setup story should stay simple:

### API access

- create the API key from:
  - `API Keys > Create new secret key`
  - <https://platform.minimax.io/user-center/basic-information/interface-key>

### Billing / credits

- pay-as-you-go balance is managed from:
  - <https://platform.minimax.io/user-center/payment/balance>
- speech subscription credits are purchased from:
  - <https://platform.minimax.io/subscribe/audio-subscription>

### Repo implication

The repo should not care whether speech usage is paid for by:

- free promotional credits
- pay-as-you-go balance
- audio subscription credits

It should only care about:

- having a valid MiniMax API key
- targeting `speech-2.8-turbo`
- sending correctly formed speech requests

That keeps billing logic out of the codebase, where it belongs.

## Python SDK assessment

I checked MiniMax’s official docs for Python integration.

What looks good:

- MiniMax documents an official SDK path via the **Anthropic Python SDK**
- MiniMax also has official **Python MCP** tooling

What matters for this repo:

- the clearly documented Anthropic SDK path is for **text models**
- the clearly documented speech path is still the **T2A HTTP / WebSocket API**
- I did **not** find a similarly strong official Python SDK story specifically for `speech-2.8-turbo`

Conclusion:

- for `anki-chinese`, the safer design is to use a small direct Python HTTP client for TTS
- that matches the speech docs more closely
- it also avoids pulling in an abstraction that is better suited to text or MCP workflows than to this repo’s audio pipeline

## Current repo workload and cost

Using the source text in the current `data/state/enriched.json` data:

- 3,018 Mandarin audio items -> **3,018 characters**
- 3,018 Cantonese audio items -> **3,018 characters**
- 3,015 example-word audio items -> **6,188 characters**
- **12,224 synthesized characters total** for one full current rebuild

The formula is:

- `3,018` Mandarin characters
- `+ 3,018` Cantonese characters
- `+ 6,188` example-word characters
- `= 12,224` total synthesized characters

Example-word length distribution:

- 2-character examples: `2,910`
- 3-character examples: `55`
- 4-character examples: `49`
- 7-character examples: `1`

This is based on the source text the repo intends to synthesize, not the current generated `*_audio` fields. Those generated fields are incomplete and would understate the true workload.

MiniMax pricing from the fetched docs:

- `speech-2.8-turbo`: **`$60 / 1M` characters**
- full current rebuild: about **`$0.73`**

Free usage:

- if MiniMax audio credits track characters the way the pricing pages imply, **10,000 monthly credits are slightly short of one full current rebuild**
- shortfall after one current rebuild: about **2,224 characters**
- paygo equivalent of that shortfall: about **`$0.13`**

Paid fallback:

- MiniMax Audio Subscription Starter: **`$5 / month`**
- includes **100,000 credits / month**
- enough for about **8.2 current full rebuilds**

At the current repo scale, MiniMax is still cheap enough that reliability and simplicity matter more than price optimization. The free credits are close, but the paid starter tier gives much cleaner operational headroom.

## Architectural implication

The repo should keep its existing narrow `TTSProvider` boundary, but it should **not** build out a wide multi-provider platform right now.

The right shape is:

- one narrow shared interface
- one deep MiniMax implementation
- provider-neutral CLI behavior
- stable filename and sound-tag behavior

That preserves future flexibility without paying today’s complexity cost.

## Planned implementation steps

1. Remove provider leakage from shared audio and CLI surfaces
2. Document MiniMax local setup:
   - create API key
   - verify credits or balance
   - run one smoke request
3. Add MiniMax-owned configuration and default to `speech-2.8-turbo`
4. Implement `MiniMaxTTSProvider` with direct Python HTTP calls to the MiniMax T2A API
5. Route the CLI test path through the shared provider boundary
6. Add a small regression corpus for Mandarin, Cantonese, and example-word audio
7. Cut over to MiniMax and remove the legacy code and dependency from the repo

## Deferred on purpose

The following are intentionally out of scope for this wave:

- multi-provider bake-offs
- Google / Inworld / Alibaba provider spikes
- keeping a parallel legacy backend

If MiniMax later fails the quality or reliability bar, the repo can reopen provider comparison from a cleaner architecture.
