from src.anki_chinese.data_sources._cedict import _download_and_cache, build_index
from src.anki_chinese.data_sources._hsk import build_index as hsk_index
from pathlib import Path

cedict_path = Path("data/cedict_1_0_ts_utf-8_mdbg.txt")
hsk_path = Path("data/hsk_complete.min.json")

if not cedict_path.exists():
    print("Downloading CC-CEDICT...")
    _download_and_cache(cedict_path)
    print("  saved.")
else:
    kb = cedict_path.stat().st_size // 1024
    print(f"CC-CEDICT cached ({kb} KB)")

print()
print("Building HSK index...")
hsk = hsk_index(hsk_path)
print("Building CC-CEDICT index...")
cedict = build_index(cedict_path)

print(f"HSK index: {len(hsk)} chars  |  CC-CEDICT index: {len(cedict)} chars")
print()
for ch in ["昭", "刃", "丁", "乙", "孔", "九"]:
    h_entries = hsk.get(ch, [])
    c_entries = cedict.get(ch, [])
    h_word = h_entries[0][0] if h_entries else "—"
    c_word = c_entries[0][0] if c_entries else "—"
    c_meaning = c_entries[0][1] if c_entries else ""
    print(f"  {ch}:  HSK={h_word:<8}  CEDICT={c_word:<8}  ({c_meaning[:45]})")
