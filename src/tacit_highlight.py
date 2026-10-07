"""
tacit_highlight.py — 把編碼標回原始逐字稿，輸出螢光筆標記的 Word 檔
====================================================================

分析表把逐字稿切成一段一段；讀的人看不到那幾句話在原文裡的位置，也看不到
沒被標到的部分。這個模組反過來做：拿整份逐字稿當底稿，把每個段落的引文
找回原文的位置，用螢光筆標出來，一個維度一個顏色，句尾附上段落編號與碼。

三種輸出：

  current  目前的編碼（複核之後；已刪除的段落不標，人工新增的段落照標）
  model    模型的原始草稿（複核前的碼；研究者後來刪掉的也標，人工新增的不標）
  blank    不標任何東西，只有逐字稿與顏色圖例——給人工編碼者用同一套顏色
           在 Word 裡手動畫螢光筆

碼寫在 Word 的註解裡，螢光筆只是讓人一眼看到位置。一段話常常同時屬於
兩個維度，而螢光筆一次只能一個顏色，後畫的會蓋掉先畫的；註解沒有這個
問題，一個註解可以寫好幾個碼，同一段話也可以掛好幾個註解。

所以反方向也成立：人在 Word 裡選取一段話、加上註解、在註解裡寫碼
（例如 ANT-P; REF-N），read_marked_docx 讀得回來，變成一份人工編碼，
可以與模型的編碼在同一個抽樣框上算一致性。

顏色用 Word 的螢光筆（w:highlight），不是字元網底：人在 Word 裡用螢光筆
工具畫出來的就是同一種標記。Word 的螢光筆只有十五色，黑字看得清楚的是
其中六色；維度超過六個時顏色循環，分辨要靠註解裡的碼。

不呼叫模型，只讀紀錄。
"""
import bisect
import difflib
import io
import re
import zipfile

from docx import Document
from docx.enum.text import WD_COLOR_INDEX
from docx.shared import Pt, RGBColor

import tacit_framework as F
import tacit_i18n as I
import tacit_irr as IRR
import tacit_schema as S

SOURCE_CURRENT = "current"
SOURCE_MODEL = "model"
SOURCE_BLANK = "blank"
SOURCES = [SOURCE_CURRENT, SOURCE_MODEL, SOURCE_BLANK]

# 黑字疊在上面仍然讀得清楚的螢光筆顏色，依辨識度排序。
PALETTE = [WD_COLOR_INDEX.YELLOW, WD_COLOR_INDEX.BRIGHT_GREEN,
           WD_COLOR_INDEX.TURQUOISE, WD_COLOR_INDEX.PINK,
           WD_COLOR_INDEX.GRAY_25, WD_COLOR_INDEX.DARK_YELLOW]

# 逐字稿本文之前的分隔線。讀回標記過的檔案時，這一行之後才是逐字稿。
SEPARATOR = "_" * 40
COMMENT_AUTHOR = {SOURCE_CURRENT: "TACIT (current coding)",
                  SOURCE_MODEL: "TACIT (model draft)", SOURCE_BLANK: "TACIT"}

_OPEN_SEGMENTS = "open_segments"
_OPEN_CODES = "open_codes"
_TAG_GREY = RGBColor(0x55, 0x55, 0x55)


# =====================================================================
# 1. 從紀錄取出要標的段落
# =====================================================================
def _open_labels(seg):
    out = []
    for c in seg.get(_OPEN_CODES) or []:
        label = c.get("label") if isinstance(c, dict) else c
        if label:
            out.append(str(label))
    return out


def marks_of(rec, source=SOURCE_CURRENT):
    """
    這份紀錄在指定來源下要標的段落：[{id, title, texts, codes}]。
    texts 是找原文位置時依序嘗試的字串（完整段落優先，再來才是短引文）。
    """
    if source == SOURCE_BLANK:
        return []
    marks = []

    def add(seg, codes, texts):
        codes = [c for c in codes if c]
        texts = [t for t in texts if t and t.strip()]
        if codes and texts:
            marks.append({"id": seg.get(S.SEGMENT_ID, ""), "title": seg.get(S.TITLE, ""),
                          "texts": texts, "codes": codes})

    for seg in rec.get(_OPEN_SEGMENTS) or []:
        add(seg, _open_labels(seg), [seg.get(S.FULL_TEXT), seg.get(S.QUOTE)])

    if source == SOURCE_CURRENT:
        for seg in rec.get(S.SEGMENTS) or []:
            add(seg, S.codes_of(seg), [seg.get(S.FULL_TEXT), seg.get(S.QUOTE)])
        return marks

    # 模型的原始草稿：用複核前的快照；研究者後來刪掉的段落也算模型標過的，
    # 研究者自己新增的不算。沒有複核欄位的段落就是還沒被動過的模型輸出。
    for seg in list(rec.get(S.SEGMENTS) or []) + list(rec.get(S.DELETED_SEGMENTS) or []):
        rv = seg.get(S.REVIEW) or {}
        if rv.get(S.SOURCE, S.SOURCE_AI) != S.SOURCE_AI:
            continue
        codes = rv.get(S.ORIGINAL_CODES)
        if codes is None:
            codes = S.codes_of(seg)
        add(seg, codes, [seg.get(S.FULL_TEXT), rv.get(S.ORIGINAL_QUOTE), seg.get(S.QUOTE)])
    return marks


# =====================================================================
# 2. 把引文找回原文的位置
# =====================================================================
_PUNCT = re.compile(r"[\s，。！？；：、,.!?;:「」『』（）()〈〉《》【】\-—…·\"'’‘“”　]+")
_norm_cache = {}


def _normalized_index(transcript):
    """逐字稿去掉標點與空白後的字串，以及每個字元對回原文的位置。"""
    key = (id(transcript), len(transcript))
    hit = _norm_cache.get(key)
    if hit and hit[0] is transcript:
        return hit[1], hit[2]
    chars, pos = [], []
    for i, ch in enumerate(transcript):
        if not _PUNCT.match(ch):
            chars.append(ch.casefold()); pos.append(i)
    norm = "".join(chars)
    _norm_cache.clear(); _norm_cache[key] = (transcript, norm, pos)
    return norm, pos


def locate(transcript, text):
    """
    引文在逐字稿裡的 (起, 迄) 字元位置；找不到回 None。
    三層：一模一樣；放寬空白（模型常把換行寫成空格）；最後忽略標點、
    大小寫與空白（模型常改掉句點、逗號或把「of」寫成「Of」），其餘字元
    仍須逐字相同，找到後把位置對回原文。
    """
    if not transcript or not text or not text.strip():
        return None
    text = text.strip()
    i = transcript.find(text)
    if i != -1:
        return i, i + len(text)
    parts = [re.escape(p) for p in text.split()]
    if not parts:
        return None
    m = re.search(r"\s+".join(parts), transcript)
    if m:
        return m.start(), m.end()
    norm, pos = _normalized_index(transcript)
    q = "".join(ch.casefold() for ch in text if not _PUNCT.match(ch))
    if len(q) < 10:
        return None
    j = norm.find(q)
    if j != -1:
        return pos[j], pos[j + len(q) - 1] + 1
    return _locate_with_gaps(norm, pos, q)


def _locate_with_gaps(norm, pos, q, min_block=25, min_cover=0.85, max_gap=400):
    """
    模型常把被訪員短句隔開的兩段發言接成一段引文，或漏掉中間幾個字。
    這裡找引文在逐字稿裡的幾塊逐字相同的片段：片段都夠長、合起來涵蓋引文
    的大部分、片段之間在逐字稿裡相隔不遠，就把整個範圍當成位置。
    """
    sm = difflib.SequenceMatcher(None, norm, q, autojunk=False)
    blocks = [b for b in sm.get_matching_blocks() if b.size >= min_block]
    if not blocks:
        return None
    covered = sum(b.size for b in blocks)
    if covered < min_cover * len(q):
        return None
    first, last = blocks[0], blocks[-1]
    for x, y in zip(blocks, blocks[1:]):
        if y.a - (x.a + x.size) > max_gap:
            return None
    return pos[first.a], pos[last.a + last.size - 1] + 1


def place_marks(rec, source=SOURCE_CURRENT):
    """回傳 (找到位置的段落, 找不到的段落)。找到的每筆多出 start / end。"""
    transcript = rec.get(S.TRANSCRIPT) or ""
    placed, missing = [], []
    for mk in marks_of(rec, source):
        span = None
        for t in mk["texts"]:
            span = locate(transcript, t)
            if span:
                break
        if span:
            placed.append(dict(mk, start=span[0], end=span[1]))
        else:
            missing.append(mk)
    placed.sort(key=lambda m: (m["start"], m["end"]))
    return placed, missing


# =====================================================================
# 3. 顏色
# =====================================================================
def _group_of(code):
    """一個碼屬於哪個顏色群：框架的碼依維度，開放編碼的碼依碼本身。"""
    try:
        d, _ = S.split_code(code)
    except Exception:                                     # noqa: BLE001
        d = None
    return d or code


def colour_map(records, source=SOURCE_CURRENT):
    """
    顏色群 → 螢光筆顏色。作用中框架的維度依框架順序先佔位，同一個維度在
    每一份逐字稿、每一種來源都是同一色；框架以外的碼依出現順序接在後面。
    """
    groups = list(F.active().dimensions)
    for rec in records:
        for src in ([source] if source != SOURCE_BLANK else [SOURCE_CURRENT, SOURCE_MODEL]):
            for mk in marks_of(rec, src):
                for c in mk["codes"]:
                    g = _group_of(c)
                    if g not in groups:
                        groups.append(g)
    return {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(groups)}


def _group_label(group):
    return I.dim(group) if group in F.active().dimensions else str(group)


# =====================================================================
# 4. 產生 Word 檔
# =====================================================================
_TITLES = {
    SOURCE_CURRENT: {"en": "Transcript with the current coding highlighted",
                     "zh": "逐字稿：目前編碼的螢光筆標記"},
    SOURCE_MODEL: {"en": "Transcript with the model's original coding highlighted",
                   "zh": "逐字稿：模型原始編碼的螢光筆標記"},
    SOURCE_BLANK: {"en": "Transcript for hand coding",
                   "zh": "逐字稿：供人工編碼"},
}
_TEXT = {
    "legend": {"en": "Colour key", "zh": "顏色圖例"},
    "blank_note": {"en": "How to code this transcript: select a passage, add a comment "
                         "(Review > New Comment) and type its code or codes in the comment, "
                         "for example {example}. A passage may carry several codes, and "
                         "passages may overlap. The codes are read from the comments; "
                         "highlighting is not needed. The codebook below gives the rules.",
                   "zh": "編碼方式：選取一段話，加上註解（校閱 > 新增註解），在註解裡寫這段話的碼，"
                         "例如 {example}。一段話可以有好幾個碼，段落之間也可以重疊。"
                         "程式讀的是註解裡的碼，不必畫螢光筆。下面的編碼簿是編碼的規則。"},
    "tag_note": {"en": "Each highlighted passage carries a comment with its codes; the "
                       "bracket after it repeats the segment number and codes for print. "
                       "A passage with codes from two dimensions takes the colour of the "
                       "first.",
                 "zh": "每段螢光筆標記都掛著一個寫有編碼的註解；後面的括號重複段落編號與編碼，"
                       "供列印時閱讀。一段話若同時帶兩個維度的碼，顏色取第一個。"},
    "counts": {"en": "{n} passages highlighted; {m} could not be located in the transcript.",
               "zh": "標出 {n} 段；另有 {m} 段的引文在逐字稿裡找不到。"},
    "counts_ok": {"en": "{n} passages highlighted.", "zh": "標出 {n} 段。"},
    "missing": {"en": "Passages not located in the transcript",
                "zh": "在逐字稿裡找不到位置的段落"},
    "framework": {"en": "Framework", "zh": "框架"},
    "endpoint": {"en": "Model endpoint", "zh": "模型端點"},
    "no_transcript": {"en": "This record holds no transcript text.",
                      "zh": "這筆紀錄沒有逐字稿內容。"},
    "codebook": {"en": "Codebook", "zh": "編碼簿"},
    "definition": {"en": "Definition", "zh": "定義"},
    "indicators": {"en": "Indicators", "zh": "指標"},
    "exclusions": {"en": "Not this dimension", "zh": "不屬於這個維度"},
}


def _tx(key, lang, **kw):
    s = (_TEXT.get(key) or _TITLES.get(key) or {}).get(lang) or \
        (_TEXT.get(key) or _TITLES.get(key) or {}).get("en", "")
    return s.format(**kw) if kw else s


def _tag(mk):
    return "[" + " ".join(x for x in (str(mk["id"]), ", ".join(mk["codes"])) if x) + "]"


def _write_line(par, line, offset, placed, colours, runs_of):
    """
    把一行逐字稿寫成數個 run：有標記的部分上螢光筆，標記結束處接上括號。
    runs_of 收集每個段落涵蓋的 run，之後把註解掛在上面。
    """
    end = offset + len(line)
    cuts = {offset, end}
    for mk in placed:
        if mk["end"] > offset and mk["start"] < end:
            cuts.add(max(mk["start"], offset))
            cuts.add(min(mk["end"], end))
    cuts = sorted(cuts)
    for a, b in zip(cuts, cuts[1:]):
        if b <= a:
            continue
        active = [mk for mk in placed if mk["start"] <= a and mk["end"] >= b]
        run = par.add_run(line[a - offset:b - offset])
        if active:
            run.font.highlight_color = colours[_group_of(active[0]["codes"][0])]
        for mk in active:
            runs_of.setdefault(id(mk), []).append(run)
        for mk in placed:
            if mk["end"] == b:
                t = par.add_run(" " + _tag(mk))
                t.font.size = Pt(8)
                t.font.color.rgb = _TAG_GREY


def _write_codebook(doc, fw, lang):
    """人工編碼版附上編碼簿：每個維度的定義、各極性的指標、排除條件。編碼者要有規則才能編。"""
    doc.add_heading(_tx("codebook", lang), level=2)
    for d in fw.dimensions:
        p = doc.add_paragraph()
        codes = [c for c in fw.codes if _group_of(c) == d]
        p.add_run(fw.label(d, lang)).bold = True
        p.add_run("   " + ", ".join(codes)).font.size = Pt(10)
        definition = fw.definition(d, lang) or fw.definition(d, "en")
        if definition:
            q = doc.add_paragraph(); q.add_run(_tx("definition", lang) + ": ").bold = True
            q.add_run(definition)
        if fw.has_polarity:
            for pol in fw.polarity_values:
                ind = fw.indicators(d, pol, lang) or fw.indicators(d, pol, "en") or []
                if ind:
                    q = doc.add_paragraph()
                    q.add_run(f"{fw.code_of(d, pol)} ({fw.polarity_label(d, pol, lang)}) "
                              f"{_tx('indicators', lang)}: ").bold = True
                    q.add_run("; ".join(ind))
        else:
            ind = fw.indicators(d, None, lang) or fw.indicators(d, None, "en") or []
            if ind:
                q = doc.add_paragraph(); q.add_run(_tx("indicators", lang) + ": ").bold = True
                q.add_run("; ".join(ind))
        exc = fw.exclusions(d, lang) or fw.exclusions(d, "en") or []
        if exc:
            q = doc.add_paragraph(); q.add_run(_tx("exclusions", lang) + ": ").bold = True
            q.add_run(" ".join(exc))


def build_docx(rec, source=SOURCE_CURRENT, colours=None, lang=None, list_unlocated=False):
    """
    一份逐字稿的螢光筆標記版，回傳 .docx 的位元組。
    引文對不回原文的段落預設不列在文件裡（數量在介面上顯示）；
    list_unlocated=True 時附在文末。
    """
    lang = lang or I.get_lang()
    lang = lang if lang in ("en", "zh") else "en"
    colours = colours or colour_map([rec], source)
    placed, missing = place_marks(rec, source)
    transcript = rec.get(S.TRANSCRIPT) or ""

    doc = Document()
    cp = doc.core_properties
    cp.author = "TACIT"
    cp.comments = ""
    cp.title = str(rec.get(S.RESPONDENT, ""))
    doc.styles["Normal"].font.size = Pt(11)

    doc.add_heading(str(rec.get(S.RESPONDENT, "")), level=1)
    doc.add_paragraph(_tx(source, lang))
    meta = rec.get(S.META) or {}
    fw = F.active()
    info = [f"{_tx('framework', lang)}: {fw.name(lang) or fw.id}"]
    if source == SOURCE_MODEL and meta.get("endpoint"):
        info.append(f"{_tx('endpoint', lang)}: {meta.get('endpoint')}")
    p = doc.add_paragraph("; ".join(info))
    p.runs[0].font.size = Pt(9)

    if source == SOURCE_BLANK:
        example = "; ".join(fw.codes[:1] + fw.codes[2:3]) or "CODE"
        doc.add_paragraph(_tx("blank_note", lang, example=example))
        _write_codebook(doc, fw, lang)
        doc.add_paragraph(SEPARATOR)
        runs_of = {}
        if not transcript.strip():
            doc.add_paragraph(_tx("no_transcript", lang))
        for line in transcript.split(chr(10)):
            doc.add_paragraph(line)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    doc.add_heading(_tx("legend", lang), level=2)
    used = {_group_of(c) for mk in placed for c in mk["codes"]}
    shown = [g for g in colours if g in used or g in fw.dimensions]
    for g in shown:
        p = doc.add_paragraph()
        r = p.add_run(f"  {_group_label(g)}  ")
        r.font.highlight_color = colours[g]
        codes = [c for c in fw.codes if _group_of(c) == g] or \
            sorted({c for mk in placed for c in mk["codes"] if _group_of(c) == g})
        if codes and codes != [g]:
            p.add_run("  " + ", ".join(codes)).font.size = Pt(9)
    doc.add_paragraph(_tx("tag_note", lang)).runs[0].font.size = Pt(9)
    doc.add_paragraph(_tx("counts_ok" if not (missing and list_unlocated) else "counts", lang,
                          n=len(placed), m=len(missing))).runs[0].font.size = Pt(9)

    doc.add_paragraph(SEPARATOR)
    runs_of = {}
    if not transcript.strip():
        doc.add_paragraph(_tx("no_transcript", lang))
    offset = 0
    for line in transcript.split("\n"):
        par = doc.add_paragraph()
        if line:
            _write_line(par, line, offset, placed, colours, runs_of)
        offset += len(line) + 1

    author = COMMENT_AUTHOR[source]
    for mk in placed:
        runs = runs_of.get(id(mk))
        if runs:
            doc.add_comment(runs, text="; ".join(mk["codes"]), author=author, initials="T")

    if missing and list_unlocated:
        doc.add_heading(_tx("missing", lang), level=2)
        for mk in missing:
            p = doc.add_paragraph()
            r = p.add_run(mk["texts"][0])
            r.font.highlight_color = colours.get(_group_of(mk["codes"][0]), PALETTE[0])
            t = p.add_run(" " + _tag(mk))
            t.font.size = Pt(8)
            t.font.color.rgb = _TAG_GREY

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _safe_name(text):
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", str(text or "")).strip("_")
    return name[:80] or "transcript"


def build_zip(records, source=SOURCE_CURRENT, lang=None, list_unlocated=False):
    """每份逐字稿一個 .docx，打包成 zip；同一個維度在所有檔案裡同一色。"""
    colours = colour_map(records, source)
    buf = io.BytesIO()
    seen = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for rec in records:
            base = _safe_name(rec.get(S.RESPONDENT))
            seen[base] = seen.get(base, 0) + 1
            if seen[base] > 1:
                base = f"{base}_{seen[base]}"
            z.writestr(f"{base}_{source}.docx", build_docx(rec, source, colours, lang, list_unlocated))
    return buf.getvalue()


# =====================================================================
# 5. 讀回標記過的 Word 檔
# =====================================================================
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _is_tag_run(run_el):
    """匯出時接在段落後面的小字括號，不是逐字稿的一部分。"""
    rpr = run_el.find(_W + "rPr")
    if rpr is None:
        return False
    sz = rpr.find(_W + "sz")
    text = "".join(t.text or "" for t in run_el.findall(_W + "t"))
    return sz is not None and sz.get(_W + "val") == "16" and text.startswith(" [")


def _run_highlight(run_el):
    rpr = run_el.find(_W + "rPr")
    h = rpr.find(_W + "highlight") if rpr is not None else None
    v = h.get(_W + "val") if h is not None else None
    return v if v and v != "none" else None


_INLINE_TAG = re.compile(r"(【[^【】\n]{1,400}】|\[\[[^\[\]\n]{1,400}\]\]|\[[^\[\]\n]{1,400}\])")
_INLINE_PREFIX = re.compile(r"\s*(?:註解|批註|備註|注解|註|comment|codes?)?\s*[:：]?\s*", re.IGNORECASE)
_LABEL_AT_START = re.compile(r"\s*(?:\[[^\]\n]*\]|【[^】\n]*】)\s*(?:\([^)\n]*\))?\s*")


def _inline_tags(full, cut, limit):
    """
    逐字稿本文裡用括號寫的碼，例如「【註解：ANT-P; 理由】」或「[[ENG-N]]」：
    每個括號標的是從上一個括號（或該段發言的開頭，講者標籤除外）到括號
    為止的那段話。認不出碼的括號不算標記，也不會被移除。
    """
    tags = []
    for m in _INLINE_TAG.finditer(full, cut, limit):
        raw_tag = m.group(0)
        inner = raw_tag[2:-2] if raw_tag.startswith("[[") else raw_tag[1:-1]
        inner = inner[_INLINE_PREFIX.match(inner).end():].strip()
        codes = parse_codes(inner)
        if not codes:
            continue
        p0 = max(full.rfind("\n", cut, m.start()) + 1, cut)
        if tags and tags[-1]["tag_end"] > p0:
            start = tags[-1]["tag_end"]
        else:
            lab = _LABEL_AT_START.match(full, p0, m.start())
            start = lab.end() if lab else p0
        raw = full[start:m.start()]
        text = raw.strip()
        a = start + (len(raw) - len(raw.lstrip()))
        tags.append({"tag_start": m.start(), "tag_end": m.end(), "start": a, "end": a + len(text),
                     "text": text, "comment": inner, "codes": codes})
    return tags


def _strip_spans(full, spans):
    """把 spans（已排序、不重疊）從字串移除；回傳新字串與舊位置→新位置的函式。"""
    out, ends, cum, last, total = [], [], [], 0, 0
    for a, b in spans:
        out.append(full[last:a])
        total += b - a
        ends.append(b)
        cum.append(total)
        last = b
    out.append(full[last:])

    def remap(pos):
        i = bisect.bisect_right(ends, pos)
        if i < len(spans) and pos > spans[i][0]:
            pos = spans[i][0]
        return pos - (cum[i - 1] if i else 0)
    return "".join(out), remap


def parse_codes(text):
    """
    註解文字裡出現的碼，依框架順序。認兩種寫法：碼的識別字（ANT-P，大小寫
    不拘；兩三個字母、沒有連字號的識別字要大小寫相符，免得把一般單字當成
    碼）與碼的完整標籤（任一種介面語言）。認不出任何碼時回空清單。
    """
    fw = F.active()
    t = text or ""
    low = t.casefold()
    found = []
    for c in fw.codes:
        loose = "-" in c or len(c) >= 4
        pat = r"(?<![A-Za-z0-9])" + re.escape(c) + r"(?![A-Za-z0-9])"
        hit = re.search(pat, t, re.IGNORECASE if loose else 0)
        if not hit:
            for lg in ("en", "zh"):
                lab = (I.code_label(c, lg) or "").strip().casefold()
                if lab and lab in low:
                    hit = True
                    break
        if hit and c not in found:
            found.append(c)
    return found


def read_marked_docx(file):
    """
    讀一份有註解（與螢光筆）的逐字稿 Word 檔。

    回傳 dict：
      transcript       逐字稿文字，一段一行
      respondent       檔案開頭的標題（由本模組匯出的檔案才有）
      marks            每個註解一筆：start / end / text（註解掛著的那段話）、
                       comment（註解原文）、author、codes（認出來的碼）
      highlight_only   畫了螢光筆卻沒有掛註解的段落：start / end / text / colour
    由本模組匯出的檔案，分隔線之前的標題與圖例、文末「找不到位置的段落」
    都不算逐字稿；別處來的檔案整份都當逐字稿。
    """
    doc = Document(file)
    bodies = {}
    try:
        for c in doc.comments:
            bodies[str(c.comment_id)] = (c.text or "", c.author or "")
    except Exception:                                     # noqa: BLE001
        bodies = {}

    parts, pos = [], 0
    open_at, ranges, lights = {}, [], []
    cut, stop, title = 0, None, ""
    missing_titles = set(_TEXT["missing"].values())
    paragraphs = doc.paragraphs
    for k, par in enumerate(paragraphs):
        p_start, n0 = pos, len(parts)
        skipped = set()
        for el in par._p.iter():
            tag = el.tag
            if tag == _W + "commentRangeStart":
                open_at[el.get(_W + "id")] = pos
            elif tag == _W + "commentRangeEnd":
                cid = el.get(_W + "id")
                if cid in open_at:
                    ranges.append((cid, open_at.pop(cid), pos))
            elif tag == _W + "r":
                if _is_tag_run(el):
                    skipped.add(el)
            elif tag in (_W + "t", _W + "tab", _W + "br", _W + "cr"):
                run = el.getparent()
                if run in skipped:
                    continue
                piece = (el.text or "") if tag == _W + "t" else ("\t" if tag == _W + "tab" else "\n")
                if not piece:
                    continue
                colour = _run_highlight(run)
                if colour:
                    lights.append((pos, pos + len(piece), colour))
                parts.append(piece)
                pos += len(piece)
        ptext = "".join(parts[n0:]).strip()
        if k == 0 and ptext:
            title = ptext
        if ptext == SEPARATOR and not cut:
            cut = pos + 1
        elif cut and stop is None and ptext in missing_titles:
            stop = p_start
        parts.append("\n")
        pos += 1
    for cid, start in open_at.items():                  # 沒有結尾標記的註解範圍
        ranges.append((cid, start, pos))

    full = "".join(parts)
    # 本文裡的括號標記：讀出來之後從逐字稿移除，讓文字與原稿一致
    inline = _inline_tags(full, cut, stop if stop is not None else len(full))
    if inline:
        full, remap = _strip_spans(full, [(t["tag_start"], t["tag_end"]) for t in inline])
        ranges = [(cid, remap(a), remap(b)) for cid, a, b in ranges]
        lights = [(remap(a), remap(b), colour) for a, b, colour in lights]
        cut = remap(cut)
        stop = remap(stop) if stop is not None else None
        for t in inline:
            t["start"], t["end"] = remap(t["start"]), remap(t["end"])
    end = stop if stop is not None else len(full)
    transcript = full[cut:end].rstrip("\n")
    limit = cut + len(transcript)

    marks = []
    for cid, a, b in sorted(ranges, key=lambda r: (r[1], r[2])):
        a, b = max(a, cut), min(b, limit)
        if b <= a:
            continue
        raw = full[a:b]
        text = raw.strip()
        if not text:
            continue
        a += len(raw) - len(raw.lstrip())
        body, author = bodies.get(str(cid), ("", ""))
        marks.append({"start": a - cut, "end": a - cut + len(text), "text": text,
                      "comment": body, "author": author, "codes": parse_codes(body)})

    for t in inline:                                   # 括號標記；與註解重複的不再收
        if not t["text"]:
            continue
        a, b = t["start"], t["end"]
        if any(m["start"] < b - cut and m["end"] > a - cut and set(m["codes"]) == set(t["codes"])
               for m in marks):
            continue
        marks.append({"start": a - cut, "end": b - cut, "text": t["text"], "comment": t["comment"],
                      "author": "", "codes": t["codes"], "inline": True})
    marks.sort(key=lambda m: (m["start"], m["end"]))

    merged = []
    for a, b, colour in lights:
        if b <= cut or a >= limit:
            continue
        if merged and merged[-1][2] == colour and not full[merged[-1][1]:a].strip():
            merged[-1] = (merged[-1][0], b, colour)
        else:
            merged.append((a, b, colour))
    covered = [(m["start"] + cut, m["end"] + cut) for m in marks]
    highlight_only = [{"start": a - cut, "end": b - cut, "text": full[a:b].strip(), "colour": colour}
                      for a, b, colour in merged
                      if full[a:b].strip() and not any(x < b and y > a for x, y in covered)]

    return {"transcript": transcript, "respondent": title if cut else "",
            "marks": marks, "highlight_only": highlight_only}


def record_from_marked(parsed, respondent, coder=""):
    """
    讀回來的標記 → 一筆分析紀錄。只收認得出碼的註解。
    review 記為 confirmed / human、原始編碼留空：沒有模型草稿被覆蓋，
    修正比例在這種紀錄上不該有數字。
    """
    segments = []
    for mk in parsed["marks"]:
        codes = []
        for c in mk["codes"]:
            dim, pol = S.split_code(c)
            if dim:
                codes.append(S.make_code(dim, pol))
        if not codes:
            continue
        segments.append({
            S.SEGMENT_ID: f"S{len(segments) + 1:03d}", S.TITLE: "",
            S.QUOTE: mk["text"], S.FULL_TEXT: mk["text"], S.CODES_F: codes,
            S.REVIEW: {S.STATUS: S.STATUS_CONFIRMED, S.SOURCE: S.SOURCE_HUMAN,
                       S.ORIGINAL_CODES: [],
                       S.HISTORY: [{"by": coder or mk.get("author") or "",
                                    "comment": mk.get("comment") or ""}]}})
    return {S.RESPONDENT: respondent, S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
            S.TRANSCRIPT: parsed["transcript"], S.SEGMENTS: segments,
            S.DELETED_SEGMENTS: [],
            S.META: {"source": f"human-marked/{coder or 'coder'}", "endpoint": None,
                     "framework_id": F.active().id}}


# =====================================================================
# 6. 人工標記與模型編碼的一致性
# =====================================================================
def _unit_coding(transcript, marks, interviewers=None):
    """把一組標記（text + codes）放到逐字稿的抽樣框上：{單元編號: 碼的集合}。"""
    segs = []
    for mk in marks:
        codes = []
        for c in mk["codes"]:
            dim, pol = S.split_code(c)
            if dim:
                codes.append(S.make_code(dim, pol))
        if codes and mk.get("text"):
            segs.append({S.QUOTE: mk["text"], S.FULL_TEXT: mk["text"], S.CODES_F: codes})
    frame, diag = IRR.build_frame([{S.RESPONDENT: "_", S.SEGMENTS: segs}], {"_": transcript},
                                  interviewers=interviewers)
    return frame, diag


def compare_marks(transcript, human_marks, model_marks, interviewers=None):
    """
    同一份逐字稿上兩組標記的一致性，以受訪者發言單元 × 碼為格。
    人工標記當參照：precision 是模型標的有多少人也標了，recall 是人標的
    有多少模型也標了。回傳 pooled 係數、各碼係數與兩邊不同的單元清單。
    """
    fh, dh = _unit_coding(transcript, human_marks, interviewers)
    fm, dm = _unit_coding(transcript, model_marks, interviewers)
    units = [u[S.UNIT_ID] for u in fh]
    a = {u[S.UNIT_ID]: set(u[S.AI_CODES]) for u in fh}
    b = {u[S.UNIT_ID]: set(u[S.AI_CODES]) for u in fm}
    pooled = IRR.pooled_kappa(a, b, units) if units else None
    tp = fn = fp = 0
    if pooled:
        tp, fn, fp = pooled[IRR.BOTH], pooled[IRR.ONLY_A], pooled[IRR.ONLY_B]
    differ = [{"unit": u[S.UNIT_ID], "text": u[S.TEXT],
               "human": sorted(a[u[S.UNIT_ID]]), "model": sorted(b[u[S.UNIT_ID]])}
              for u in fh if a[u[S.UNIT_ID]] != b[u[S.UNIT_ID]]]
    return {
        "units": len(units), "a": a, "b": b, "unit_ids": units, "pooled": pooled,
        "precision": round(tp / (tp + fp), 3) if tp + fp else None,
        "recall": round(tp / (tp + fn), 3) if tp + fn else None,
        "per_code": IRR.per_code_agreement(a, b, units) if units else [],
        "differ": differ,
        "frame": [{"unit": u[S.UNIT_ID], "speaker": u.get(S.SPEAKER, ""), "text": u[S.TEXT]} for u in fh],
        "human_not_placed": sum(dh["unmatched_quotes"].values()) + sum(dh["quotes_on_excluded_units"].values()),
        "model_not_placed": sum(dm["unmatched_quotes"].values()) + sum(dm["quotes_on_excluded_units"].values()),
    }


def model_marks_of(rec, source=SOURCE_MODEL, transcript=None):
    """一筆紀錄的標記，轉成 compare_marks 吃的格式（text 取自逐字稿原文）。"""
    view = dict(rec)
    if transcript is not None:
        view[S.TRANSCRIPT] = transcript
    placed, missing = place_marks(view, source)
    text = view.get(S.TRANSCRIPT) or ""
    return ([{"text": text[m["start"]:m["end"]], "codes": m["codes"]} for m in placed],
            len(missing))


def match_record(parsed, records, file_name=""):
    """
    這份標記過的檔案對應哪一筆紀錄：逐字稿文字相同的優先；不然看檔名或
    檔案標題裡有沒有受訪者名稱或其開頭的編號。找不到回 None。
    """
    want = IRR.normalize(parsed.get("transcript") or "")
    for i, rec in enumerate(records):
        if want and IRR.normalize(rec.get(S.TRANSCRIPT) or "") == want:
            return i
    hay = f"{file_name} {parsed.get('respondent') or ''}".casefold()
    for i, rec in enumerate(records):
        name = str(rec.get(S.RESPONDENT) or "").strip()
        if not name:
            continue
        if name.casefold() in hay:
            return i
        words = [w.strip(".,;:()[]") for w in name.split()]
        for w in words:
            if len(w) >= 3 and w.casefold() not in _NAME_TITLES and re.search(
                    r"(?<![a-z0-9])" + re.escape(w.casefold()) + r"(?![a-z0-9])", hay):
                return i
    # 檔名與紀錄的逐字稿開頭共有的識別碼（例如 CHRG-118shrg52785）
    ids = {t for t in re.findall(r"[a-z0-9][a-z0-9-]{6,}", hay) if re.search(r"\d", t)}
    for i, rec in enumerate(records):
        head = (rec.get(S.TRANSCRIPT) or "")[:300].casefold()
        if any(t in head for t in ids):
            return i
    return None


_NAME_TITLES = {"mr", "mrs", "ms", "miss", "dr", "prof", "professor", "sir", "madam", "hon", "senator", "chairman"}


# =====================================================================
# 7. 裁決：兩組編碼不同的單元，由人決定定稿
# =====================================================================
DECISION_A = "a"            # 採第一組（人工）
DECISION_B = "b"            # 採第二組（模型或另一位編碼者）
DECISION_BOTH = "both"      # 兩組聯集
DECISION_NEITHER = "neither"
DECISION_CUSTOM = "custom"  # 自訂的碼
DECISIONS = [DECISION_A, DECISION_B, DECISION_BOTH, DECISION_NEITHER, DECISION_CUSTOM]
SOURCE_ADJUDICATED = "adjudicated"


def adjudicated_record(cmp, decisions, respondent, adjudicator, label_a="hand", label_b="other",
                       transcript=None):
    """
    依裁決產生一筆定稿紀錄。

    cmp 是 compare_marks 的回傳；decisions 是 {單元編號: {"decision": …,
    "codes": [...], "reason": "..."}}。兩組相同的單元不必裁決，直接採用；
    不同而沒有裁決的單元不編碼，單元編號記在 _meta.undecided。
    每個段落的 review.history 記下兩組原本的碼、決定與理由，由誰裁決。
    """
    segments, undecided = [], []
    counts = {k: 0 for k in DECISIONS}
    counts["same"] = 0
    for row in cmp["frame"]:
        u = row["unit"]
        a, b = set(cmp["a"].get(u, ())), set(cmp["b"].get(u, ()))
        d = (decisions or {}).get(u) or {}
        choice = d.get("decision")
        if a == b:
            codes, choice = a, "same"
        elif choice == DECISION_A:
            codes = a
        elif choice == DECISION_B:
            codes = b
        elif choice == DECISION_BOTH:
            codes = a | b
        elif choice == DECISION_NEITHER:
            codes = set()
        elif choice == DECISION_CUSTOM:
            codes = {c for c in (d.get("codes") or []) if S.split_code(c)[0]}
        else:
            undecided.append(u)
            continue
        counts[choice] += 1
        parsed = []
        for c in sorted(codes):
            dim, pol = S.split_code(c)
            if dim:
                parsed.append(S.make_code(dim, pol))
        if not parsed:
            continue
        segments.append({
            S.SEGMENT_ID: f"S{len(segments) + 1:03d}", S.TITLE: "",
            S.QUOTE: row["text"], S.FULL_TEXT: row["text"], S.CODES_F: parsed,
            S.REVIEW: {S.STATUS: S.STATUS_CONFIRMED, S.SOURCE: SOURCE_ADJUDICATED,
                       S.ORIGINAL_CODES: [],
                       S.HISTORY: [{"by": adjudicator, "unit_id": u, "decision": choice,
                                    label_a: sorted(a), label_b: sorted(b),
                                    "reason": d.get("reason") or ""}]}})
    return {S.RESPONDENT: respondent, S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
            S.TRANSCRIPT: transcript or "", S.SEGMENTS: segments, S.DELETED_SEGMENTS: [],
            S.META: {"source": f"{SOURCE_ADJUDICATED}/{adjudicator or 'adjudicator'}",
                     "endpoint": None, "framework_id": F.active().id,
                     "adjudication": {"units": cmp["units"], "counts": counts,
                                      "undecided": undecided, label_a: label_a, label_b: label_b}}}


def dimension_agreement(cmp):
    """
    忽略極性、只看維度的一致性：一個單元在一個維度上，兩組是否都標了。
    極性常是兩組最常不合的地方，分開看才知道不合在「有沒有」還是「正負」。
    """
    dims = list(F.active().dimensions)
    both = a_only = b_only = neither = 0
    for u in cmp["unit_ids"]:
        A = {S.split_code(x)[0] for x in cmp["a"].get(u, ())}
        B = {S.split_code(x)[0] for x in cmp["b"].get(u, ())}
        for d in dims:
            x, y = d in A, d in B
            both += x and y; a_only += x and not y; b_only += y and not x
            neither += (not x) and (not y)
    n = both + a_only + b_only + neither
    if not n:
        return None
    po = (both + neither) / n
    pa, pb = (both + a_only) / n, (both + b_only) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return {"n": n, "both": both, "a_only": a_only, "b_only": b_only, "neither": neither,
            "observed_agreement": round(po, 3),
            "kappa": round((po - pe) / (1 - pe), 3) if pe < 1 else None}


def comparison_workbook(results, label_a="hand", label_b="other"):
    """
    幾份檔案的比對結果寫成一本 Excel：總表、每碼、每個單元兩組各標了什麼。
    results: [(檔名, cmp)]。回傳位元組。
    """
    import pandas as pd
    summary, per_code, units = [], [], []
    for name, cmp in results:
        pl = cmp["pooled"] or {}
        dim = dimension_agreement(cmp) or {}
        summary.append({"file": name, "units": cmp["units"], "cells": pl.get("n"),
                        "both": pl.get(IRR.BOTH), f"{label_a} only": pl.get(IRR.ONLY_A),
                        f"{label_b} only": pl.get(IRR.ONLY_B),
                        "kappa": pl.get(IRR.KAPPA), "PABAK": pl.get(IRR.PABAK), "AC1": pl.get(IRR.AC1),
                        "precision": cmp["precision"], "recall": cmp["recall"],
                        "dimension kappa": dim.get("kappa"),
                        f"{label_a} not placed": cmp["human_not_placed"],
                        f"{label_b} not placed": cmp["model_not_placed"]})
        for r in cmp["per_code"]:
            per_code.append({"file": name, **r})
        for row in cmp["frame"]:
            u = row["unit"]
            a, b = sorted(cmp["a"].get(u, ())), sorted(cmp["b"].get(u, ()))
            units.append({"file": name, "unit": u, "speaker": row["speaker"],
                          label_a: ", ".join(a), label_b: ", ".join(b),
                          "same": a == b, "text": row["text"]})
    buf = io.BytesIO()
    with pd.ExcelWriter(buf) as w:
        pd.DataFrame(summary).to_excel(w, sheet_name="summary", index=False)
        pd.DataFrame(per_code).to_excel(w, sheet_name="per_code", index=False)
        pd.DataFrame(units).to_excel(w, sheet_name="units", index=False)
    return buf.getvalue()


def side_by_side_zip(parsed, rec, source, respondent, coder, lang=None):
    """同一份逐字稿的兩個螢光筆版本：人工標記的、與載入紀錄的，同一套顏色。"""
    hrec = record_from_marked(parsed, respondent, coder)
    view = dict(rec); view[S.TRANSCRIPT] = parsed["transcript"]
    colours = colour_map([hrec, view], SOURCE_CURRENT)
    buf = io.BytesIO()
    base = _safe_name(respondent)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"{base}_{_safe_name(coder) or 'hand'}.docx", build_docx(hrec, SOURCE_CURRENT, colours, lang))
        z.writestr(f"{base}_{source}.docx", build_docx(view, source, colours, lang))
    return buf.getvalue()
