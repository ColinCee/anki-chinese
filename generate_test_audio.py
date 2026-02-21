"""Generate a test audio file for comparison.

Usage:
    uv run python generate_test_audio.py "早下"
    uv run python generate_test_audio.py "早上"

NOTE: Prefer using the CLI command instead:
    uv run anki-chinese test-tts --word "早上"
    uv run anki-chinese test-tts --char 早
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from anki_chinese.tts import _ssml_plain, _generate_audio, MANDARIN_VOICE
from anki_chinese.config import TEST_MEDIA_DIR


def main():
    if len(sys.argv) < 2:
        print("Usage: uv run python generate_test_audio.py <text>")
        print("       uv run anki-chinese test-tts --word <text>  (preferred)")
        sys.exit(1)

    text = sys.argv[1]
    filename = f"test_{text}.mp3"
    TEST_MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    output = TEST_MEDIA_DIR / filename

    ssml = _ssml_plain(text=text, voice=MANDARIN_VOICE, lang="zh-CN")
    print(f"SSML:\n{ssml}\n")
    print(f"Generating: {output}")
    _generate_audio(ssml, output)
    print(f"Done: {output} ({output.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
