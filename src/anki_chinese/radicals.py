"""Analyze radical exposure in saved character notes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .data_sources._hsk import _load_raw
from .notes import CharacterNote


@dataclass(frozen=True)
class RadicalInfo:
    """Study label for a radical or common radical variant."""

    meaning: str
    nickname: str


@dataclass(frozen=True)
class RadicalExposure:
    radical: str
    count: int
    examples: tuple[str, ...]
    meaning: str
    nickname: str
    priority: str


@dataclass(frozen=True)
class RadicalReport:
    rows: tuple[RadicalExposure, ...]
    total_characters: int
    matched_characters: int
    unmatched_characters: int
    total_radicals: int


RADICAL_INFOS: dict[str, RadicalInfo] = {
    "一": RadicalInfo("one", "横 héng"),
    "丨": RadicalInfo("line", "竖 shù"),
    "丶": RadicalInfo("dot", "点 diǎn"),
    "丿": RadicalInfo("slash", "撇 piě"),
    "乙": RadicalInfo("second; bend", "乙字旁 yǐ zì páng"),
    "乚": RadicalInfo("second; hook", "乙字钩 yǐ zì gōu"),
    "乛": RadicalInfo("bend", "横钩 héng gōu"),
    "亅": RadicalInfo("hook", "竖钩 shù gōu"),
    "二": RadicalInfo("two", "二字旁 èr zì páng"),
    "亠": RadicalInfo("lid", "点横头 diǎn héng tóu"),
    "人": RadicalInfo("person", "人字旁 rén zì páng"),
    "亻": RadicalInfo("person", "单人旁 dān rén páng"),
    "儿": RadicalInfo("legs", "儿字底 ér zì dǐ"),
    "入": RadicalInfo("enter", "入字头 rù zì tóu"),
    "八": RadicalInfo("eight; divide", "八字旁 bā zì páng"),
    "丷": RadicalInfo("eight/divide top", "八字头 bā zì tóu"),
    "冂": RadicalInfo("open box", "同字框 tóng zì kuàng"),
    "冖": RadicalInfo("cover", "秃宝盖 tū bǎo gài"),
    "冫": RadicalInfo("ice", "两点水 liǎng diǎn shuǐ"),
    "⺀": RadicalInfo("ice dots", "两点水 liǎng diǎn shuǐ"),
    "几": RadicalInfo("small table", "几字旁 jǐ zì páng"),
    "凵": RadicalInfo("open box", "凶字框 xiōng zì kuàng"),
    "刀": RadicalInfo("knife", "刀字旁 dāo zì páng"),
    "刂": RadicalInfo("knife", "立刀旁 lì dāo páng"),
    "刁": RadicalInfo("tricky; old knife-like form", "刁字旁 diāo zì páng"),
    "力": RadicalInfo("strength", "力字旁 lì zì páng"),
    "勹": RadicalInfo("wrap", "包字头 bāo zì tóu"),
    "匕": RadicalInfo("spoon", "匕字旁 bǐ zì páng"),
    "匚": RadicalInfo("box", "三框儿 sān kuàng ér"),
    "匸": RadicalInfo("hiding enclosure", "匚字框 fāng zì kuàng"),
    "十": RadicalInfo("ten", "十字旁 shí zì páng"),
    "卜": RadicalInfo("divination", "卜字边 bǔ zì biān"),
    "⺊": RadicalInfo("divination", "占字头 zhān zì tóu"),
    "卩": RadicalInfo("seal", "单耳旁 dān ěr páng"),
    "㔾": RadicalInfo("kneeling person", "硬耳旁 yìng ěr páng"),
    "厂": RadicalInfo("cliff", "厂字头 hàn zì tóu"),
    "厶": RadicalInfo("private", "私字旁 sī zì páng"),
    "又": RadicalInfo("again; right hand", "又字旁 yòu zì páng"),
    "口": RadicalInfo("mouth", "口字旁 kǒu zì páng"),
    "囗": RadicalInfo("enclosure", "国字框 guó zì kuàng"),
    "土": RadicalInfo("earth", "提土旁 tí tǔ páng"),
    "士": RadicalInfo("scholar", "士字旁 shì zì páng"),
    "夂": RadicalInfo("go", "折文 zhǐ wén"),
    "夊": RadicalInfo("go slowly", "夊字底 suī zì dǐ"),
    "夕": RadicalInfo("evening", "夕字旁 xī zì páng"),
    "大": RadicalInfo("big", "大字头 dà zì tóu"),
    "女": RadicalInfo("woman", "女字旁 nǚ zì páng"),
    "子": RadicalInfo("child", "子字旁 zǐ zì páng"),
    "宀": RadicalInfo("roof", "宝盖头 bǎo gài tóu"),
    "寸": RadicalInfo("inch", "寸字旁 cùn zì páng"),
    "小": RadicalInfo("small", "小字头 xiǎo zì tóu"),
    "⺌": RadicalInfo("small", "小字头 xiǎo zì tóu"),
    "尢": RadicalInfo("lame leg", "尢字旁 yóu zì páng"),
    "尸": RadicalInfo("corpse; body", "尸字头 shī zì tóu"),
    "屮": RadicalInfo("sprout", "屮字旁 chè zì páng"),
    "山": RadicalInfo("mountain", "山字旁 shān zì páng"),
    "巛": RadicalInfo("river", "三拐 sān guǎi"),
    "川": RadicalInfo("river", "川字旁 chuān zì páng"),
    "工": RadicalInfo("work", "工字旁 gōng zì páng"),
    "己": RadicalInfo("self", "己字旁 jǐ zì páng"),
    "巳": RadicalInfo("sixth earthly branch", "巳字旁 sì zì páng"),
    "巾": RadicalInfo("cloth", "巾字旁 jīn zì páng"),
    "干": RadicalInfo("dry; shield", "干字旁 gān zì páng"),
    "幺": RadicalInfo("tiny", "幺字旁 yāo zì páng"),
    "广": RadicalInfo("shelter", "广字旁 guǎng zì páng"),
    "廴": RadicalInfo("long stride", "建字底 jiàn zì dǐ"),
    "廾": RadicalInfo("two hands", "弄字底 nòng zì dǐ"),
    "弋": RadicalInfo("shoot", "弋字旁 yì zì páng"),
    "弓": RadicalInfo("bow", "弓字旁 gōng zì páng"),
    "彐": RadicalInfo("snout; hand", "雪字底 xuě zì dǐ"),
    "彡": RadicalInfo("bristle; pattern", "三撇儿 sān piě ér"),
    "彳": RadicalInfo("step", "双人旁 shuāng rén páng"),
    "心": RadicalInfo("heart", "心字底 xīn zì dǐ"),
    "忄": RadicalInfo("heart; feeling", "竖心旁 shù xīn páng"),
    "⺗": RadicalInfo("heart; feeling", "心字底 xīn zì dǐ"),
    "戈": RadicalInfo("spear", "戈字旁 gē zì páng"),
    "户": RadicalInfo("door", "户字头 hù zì tóu"),
    "手": RadicalInfo("hand", "手字旁 shǒu zì páng"),
    "扌": RadicalInfo("hand; action", "提手旁 tí shǒu páng"),
    "支": RadicalInfo("branch", "支字旁 zhī zì páng"),
    "攴": RadicalInfo("tap", "攴字旁 pū zì páng"),
    "攵": RadicalInfo("tap; strike", "反文旁 fǎn wén páng"),
    "文": RadicalInfo("writing", "文字旁 wén zì páng"),
    "斗": RadicalInfo("dipper", "斗字旁 dǒu zì páng"),
    "斤": RadicalInfo("axe", "斤字旁 jīn zì páng"),
    "方": RadicalInfo("square; direction", "方字旁 fāng zì páng"),
    "旡": RadicalInfo("choke", "旡字旁 jì zì páng"),
    "无": RadicalInfo("not have", "无字旁 wú zì páng"),
    "日": RadicalInfo("sun; day", "日字旁 rì zì páng"),
    "曰": RadicalInfo("say", "曰字头 yuē zì tóu"),
    "月": RadicalInfo("moon", "月字旁 yuè zì páng"),
    "⺼": RadicalInfo("meat; body", "肉月旁 ròu yuè páng"),
    "木": RadicalInfo("wood; tree", "木字旁 mù zì páng"),
    "欠": RadicalInfo("lack; yawn", "欠字旁 qiàn zì páng"),
    "止": RadicalInfo("stop", "止字旁 zhǐ zì páng"),
    "歹": RadicalInfo("death", "歹字旁 dǎi zì páng"),
    "殳": RadicalInfo("weapon", "殳字旁 shū zì páng"),
    "母": RadicalInfo("mother", "母字旁 mǔ zì páng"),
    "比": RadicalInfo("compare", "比字旁 bǐ zì páng"),
    "毛": RadicalInfo("hair", "毛字旁 máo zì páng"),
    "民": RadicalInfo("people", "民字旁 mín zì páng"),
    "氏": RadicalInfo("clan", "氏字旁 shì zì páng"),
    "气": RadicalInfo("steam; air", "气字头 qì zì tóu"),
    "水": RadicalInfo("water", "水字旁 shuǐ zì páng"),
    "氵": RadicalInfo("water", "三点水 sān diǎn shuǐ"),
    "氺": RadicalInfo("water", "水字底 shuǐ zì dǐ"),
    "火": RadicalInfo("fire", "火字旁 huǒ zì páng"),
    "灬": RadicalInfo("fire", "四点底 sì diǎn dǐ"),
    "爪": RadicalInfo("claw", "爪字旁 zhǎo zì páng"),
    "爫": RadicalInfo("claw", "爪字头 zhǎo zì tóu"),
    "父": RadicalInfo("father", "父字头 fù zì tóu"),
    "爻": RadicalInfo("lines; mix", "爻字旁 yáo zì páng"),
    "爿": RadicalInfo("split wood", "爿字旁 pán zì páng"),
    "丬": RadicalInfo("split wood", "将字旁 jiàng zì páng"),
    "片": RadicalInfo("slice", "片字旁 piàn zì páng"),
    "牙": RadicalInfo("tooth", "牙字旁 yá zì páng"),
    "牛": RadicalInfo("cow", "牛字旁 niú zì páng"),
    "牜": RadicalInfo("cow", "牛字旁 niú zì páng"),
    "犬": RadicalInfo("dog", "犬字旁 quǎn zì páng"),
    "犭": RadicalInfo("dog; animal", "反犬旁 fǎn quǎn páng"),
    "玄": RadicalInfo("dark; mysterious", "玄字旁 xuán zì páng"),
    "玉": RadicalInfo("jade", "玉字旁 yù zì páng"),
    "王": RadicalInfo("jade; king", "王字旁 wáng zì páng"),
    "瓜": RadicalInfo("melon", "瓜字旁 guā zì páng"),
    "瓦": RadicalInfo("tile", "瓦字旁 wǎ zì páng"),
    "甘": RadicalInfo("sweet", "甘字旁 gān zì páng"),
    "生": RadicalInfo("life; birth", "生字旁 shēng zì páng"),
    "用": RadicalInfo("use", "用字旁 yòng zì páng"),
    "田": RadicalInfo("field", "田字旁 tián zì páng"),
    "疋": RadicalInfo("bolt of cloth", "疋字旁 pǐ zì páng"),
    "疒": RadicalInfo("sickness", "病字旁 bìng zì páng"),
    "癶": RadicalInfo("footsteps", "登字头 dēng zì tóu"),
    "白": RadicalInfo("white", "白字旁 bái zì páng"),
    "皮": RadicalInfo("skin", "皮字旁 pí zì páng"),
    "皿": RadicalInfo("dish", "皿字底 mǐn zì dǐ"),
    "目": RadicalInfo("eye", "目字旁 mù zì páng"),
    "矛": RadicalInfo("spear", "矛字旁 máo zì páng"),
    "矢": RadicalInfo("arrow", "矢字旁 shǐ zì páng"),
    "石": RadicalInfo("stone", "石字旁 shí zì páng"),
    "示": RadicalInfo("altar; spirit", "示字旁 shì zì páng"),
    "礻": RadicalInfo("altar; spirit", "示字旁 shì zì páng"),
    "禸": RadicalInfo("track", "禸字旁 róu zì páng"),
    "禾": RadicalInfo("grain", "禾木旁 hé mù páng"),
    "穴": RadicalInfo("cave", "穴宝盖 xué bǎo gài"),
    "立": RadicalInfo("stand", "立字旁 lì zì páng"),
    "竹": RadicalInfo("bamboo", "竹字头 zhú zì tóu"),
    "⺮": RadicalInfo("bamboo", "竹字头 zhú zì tóu"),
    "米": RadicalInfo("rice", "米字旁 mǐ zì páng"),
    "糸": RadicalInfo("silk", "糸字旁 mì zì páng"),
    "纟": RadicalInfo("silk; thread", "绞丝旁 jiǎo sī páng"),
    "缶": RadicalInfo("jar", "缶字旁 fǒu zì páng"),
    "网": RadicalInfo("net", "网字旁 wǎng zì páng"),
    "罒": RadicalInfo("net", "四字头 sì zì tóu"),
    "⺳": RadicalInfo("net", "网字头 wǎng zì tóu"),
    "羊": RadicalInfo("sheep", "羊字旁 yáng zì páng"),
    "羽": RadicalInfo("feather", "羽字旁 yǔ zì páng"),
    "老": RadicalInfo("old", "老字旁 lǎo zì páng"),
    "耂": RadicalInfo("old", "老字头 lǎo zì tóu"),
    "而": RadicalInfo("and; beard", "而字旁 ér zì páng"),
    "耒": RadicalInfo("plow", "耒字旁 lěi zì páng"),
    "耳": RadicalInfo("ear", "耳字旁 ěr zì páng"),
    "聿": RadicalInfo("brush", "聿字旁 yù zì páng"),
    "肉": RadicalInfo("meat", "肉字旁 ròu zì páng"),
    "臣": RadicalInfo("minister", "臣字旁 chén zì páng"),
    "自": RadicalInfo("self", "自字旁 zì zì páng"),
    "至": RadicalInfo("arrive", "至字旁 zhì zì páng"),
    "臼": RadicalInfo("mortar", "臼字旁 jiù zì páng"),
    "舌": RadicalInfo("tongue", "舌字旁 shé zì páng"),
    "舛": RadicalInfo("opposite feet", "舛字旁 chuǎn zì páng"),
    "舟": RadicalInfo("boat", "舟字旁 zhōu zì páng"),
    "艮": RadicalInfo("stopping", "艮字旁 gèn zì páng"),
    "色": RadicalInfo("color", "色字旁 sè zì páng"),
    "艹": RadicalInfo("grass; plants", "草字头 cǎo zì tóu"),
    "虍": RadicalInfo("tiger", "虎字头 hǔ zì tóu"),
    "虎": RadicalInfo("tiger", "虎字旁 hǔ zì páng"),
    "虫": RadicalInfo("insect", "虫字旁 chóng zì páng"),
    "血": RadicalInfo("blood", "血字旁 xuè zì páng"),
    "行": RadicalInfo("walk; go", "行字旁 xíng zì páng"),
    "衣": RadicalInfo("clothing", "衣字旁 yī zì páng"),
    "衤": RadicalInfo("clothing", "衣字旁 yī zì páng"),
    "西": RadicalInfo("west", "西字旁 xī zì páng"),
    "覀": RadicalInfo("west", "西字头 xī zì tóu"),
    "见": RadicalInfo("see", "见字旁 jiàn zì páng"),
    "角": RadicalInfo("horn", "角字旁 jiǎo zì páng"),
    "言": RadicalInfo("speech", "言字旁 yán zì páng"),
    "讠": RadicalInfo("speech", "言字旁 yán zì páng"),
    "谷": RadicalInfo("valley", "谷字旁 gǔ zì páng"),
    "豆": RadicalInfo("bean", "豆字旁 dòu zì páng"),
    "豕": RadicalInfo("pig", "豕字旁 shǐ zì páng"),
    "豸": RadicalInfo("badger; beast", "豸字旁 zhì zì páng"),
    "贝": RadicalInfo("shell; money", "贝字旁 bèi zì páng"),
    "赤": RadicalInfo("red", "赤字旁 chì zì páng"),
    "走": RadicalInfo("walk; run", "走字旁 zǒu zì páng"),
    "足": RadicalInfo("foot", "足字旁 zú zì páng"),
    "身": RadicalInfo("body", "身字旁 shēn zì páng"),
    "车": RadicalInfo("vehicle", "车字旁 chē zì páng"),
    "辛": RadicalInfo("bitter", "辛字旁 xīn zì páng"),
    "辰": RadicalInfo("morning; dragon", "辰字旁 chén zì páng"),
    "辶": RadicalInfo("walk; movement", "走之旁 zǒu zhī páng"),
    "邑": RadicalInfo("city", "邑字旁 yì zì páng"),
    "阝": RadicalInfo("mound; city", "双耳旁 shuāng ěr páng"),
    "酉": RadicalInfo("wine", "酉字旁 yǒu zì páng"),
    "釆": RadicalInfo("distinguish", "釆字旁 biàn zì páng"),
    "里": RadicalInfo("village; inside", "里字旁 lǐ zì páng"),
    "金": RadicalInfo("metal; gold", "金字旁 jīn zì páng"),
    "钅": RadicalInfo("metal; gold", "金字旁 jīn zì páng"),
    "长": RadicalInfo("long", "长字旁 cháng zì páng"),
    "门": RadicalInfo("gate", "门字框 mén zì kuàng"),
    "隶": RadicalInfo("slave; official script", "隶字旁 lì zì páng"),
    "隹": RadicalInfo("short-tailed bird", "隹字旁 zhuī zì páng"),
    "雨": RadicalInfo("rain", "雨字头 yǔ zì tóu"),
    "青": RadicalInfo("blue-green", "青字旁 qīng zì páng"),
    "非": RadicalInfo("not; wrong", "非字旁 fēi zì páng"),
    "面": RadicalInfo("face; surface", "面字旁 miàn zì páng"),
    "革": RadicalInfo("leather", "革字旁 gé zì páng"),
    "韦": RadicalInfo("soft leather", "韦字旁 wéi zì páng"),
    "音": RadicalInfo("sound", "音字旁 yīn zì páng"),
    "页": RadicalInfo("page; head", "页字旁 yè zì páng"),
    "风": RadicalInfo("wind", "风字旁 fēng zì páng"),
    "飞": RadicalInfo("fly", "飞字旁 fēi zì páng"),
    "食": RadicalInfo("food", "食字旁 shí zì páng"),
    "饣": RadicalInfo("food", "食字旁 shí zì páng"),
    "首": RadicalInfo("head", "首字旁 shǒu zì páng"),
    "香": RadicalInfo("fragrant", "香字旁 xiāng zì páng"),
    "马": RadicalInfo("horse", "马字旁 mǎ zì páng"),
    "骨": RadicalInfo("bone", "骨字旁 gǔ zì páng"),
    "高": RadicalInfo("tall", "高字旁 gāo zì páng"),
    "髟": RadicalInfo("long hair", "髟字头 biāo zì tóu"),
    "鬯": RadicalInfo("sacrificial wine", "鬯字旁 chàng zì páng"),
    "鬲": RadicalInfo("cauldron", "鬲字旁 lì zì páng"),
    "鬼": RadicalInfo("ghost", "鬼字旁 guǐ zì páng"),
    "鱼": RadicalInfo("fish", "鱼字旁 yú zì páng"),
    "鸟": RadicalInfo("bird", "鸟字旁 niǎo zì páng"),
    "卤": RadicalInfo("salt; brine", "卤字旁 lǔ zì páng"),
    "鹿": RadicalInfo("deer", "鹿字旁 lù zì páng"),
    "麦": RadicalInfo("wheat", "麦字旁 mài zì páng"),
    "麻": RadicalInfo("hemp", "麻字旁 má zì páng"),
    "黄": RadicalInfo("yellow", "黄字旁 huáng zì páng"),
    "黍": RadicalInfo("millet", "黍字旁 shǔ zì páng"),
    "黑": RadicalInfo("black", "黑字旁 hēi zì páng"),
    "黹": RadicalInfo("embroidery", "黹字旁 zhǐ zì páng"),
    "黾": RadicalInfo("frog", "黾字旁 mǐn zì páng"),
    "鼎": RadicalInfo("tripod", "鼎字旁 dǐng zì páng"),
    "鼓": RadicalInfo("drum", "鼓字旁 gǔ zì páng"),
    "鼠": RadicalInfo("rat", "鼠字旁 shǔ zì páng"),
    "鼻": RadicalInfo("nose", "鼻字旁 bí zì páng"),
    "齐": RadicalInfo("even; uniform", "齐字旁 qí zì páng"),
    "齿": RadicalInfo("tooth", "齿字旁 chǐ zì páng"),
    "龙": RadicalInfo("dragon", "龙字旁 lóng zì páng"),
    "龟": RadicalInfo("turtle", "龟字旁 guī zì páng"),
    "龠": RadicalInfo("flute", "龠字旁 yuè zì páng"),
}


def _priority(count: int) -> str:
    if count >= 3:
        return "learn now"
    if count == 2:
        return "notice"
    return "later"


def _extract_hsk_word(entry: dict) -> str:
    word = entry.get("s") or entry.get("simplified") or ""
    return word if isinstance(word, str) else ""


def _extract_hsk_radical(entry: dict) -> str:
    radical = entry.get("r") or entry.get("radical") or ""
    return radical if isinstance(radical, str) else ""


def build_hanzi_radical_map(path: Path) -> dict[str, str]:
    """Build {hanzi -> primary radical} from the local HSK dataset."""
    exact: dict[str, str] = {}
    first_char_fallback: dict[str, str] = {}

    for entry in _load_raw(path):
        if not isinstance(entry, dict):
            continue

        word = _extract_hsk_word(entry)
        radical = _extract_hsk_radical(entry)
        if not word or not radical:
            continue

        if len(word) == 1:
            exact[word] = radical
        else:
            first_char_fallback.setdefault(word[0], radical)

    radical_map = {**first_char_fallback, **exact}
    for radical in RADICAL_INFOS:
        radical_map.setdefault(radical, radical)
    return radical_map


def analyze_radical_exposure(
    notes: list[CharacterNote],
    hsk_path: Path,
    *,
    scope_chars: set[str] | None = None,
    min_seen: int = 1,
    limit: int = 0,
) -> RadicalReport:
    """Summarize primary radicals encountered in saved notes."""
    radical_map = build_hanzi_radical_map(hsk_path)
    selected_notes = [
        note
        for note in notes
        if len(note.hanzi) == 1 and (scope_chars is None or note.hanzi in scope_chars)
    ]

    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    unmatched = 0

    for note in selected_notes:
        radical = radical_map.get(note.hanzi)
        if not radical:
            unmatched += 1
            continue

        counts[radical] += 1
        examples.setdefault(radical, [])
        if len(examples[radical]) < 6:
            examples[radical].append(note.hanzi)

    rows = [
        RadicalExposure(
            radical=radical,
            count=count,
            examples=tuple(examples[radical]),
            meaning=RADICAL_INFOS.get(radical, RadicalInfo("unknown", "—")).meaning,
            nickname=RADICAL_INFOS.get(radical, RadicalInfo("unknown", "—")).nickname,
            priority=_priority(count),
        )
        for radical, count in counts.items()
        if count >= min_seen
    ]
    rows.sort(key=lambda row: (-row.count, row.radical))
    if limit > 0:
        rows = rows[:limit]

    matched = sum(counts.values())
    return RadicalReport(
        rows=tuple(rows),
        total_characters=len(selected_notes),
        matched_characters=matched,
        unmatched_characters=unmatched,
        total_radicals=len(counts),
    )
