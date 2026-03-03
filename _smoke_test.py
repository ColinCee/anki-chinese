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
    h = hsk.get(ch, ("—", ""))
    c = cedict.get(ch, ("—", ""))
    print(f"  {ch}:  HSK={h[0]:<8}  CEDICT={c[0]:<8}  ({c[1][:45]})")
