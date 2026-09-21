"""
tacit_themes.py — 二階主題歸納與 Gioia 式資料結構
================================================
補上 codes 與 themes 之間缺的那一層。

【方法論定位】
  本模組產出 **Gioia 式資料結構**（Gioia, Corley & Hamilton, 2013）作為分析歷程
  的透明化呈現，但分析策略為**溯因（abductive）**取向的理論驅動分析，而非古典
  紮根理論：聚合維度取自**作用中框架**，屬先驗設定；二階主題則自語料自由
  歸納，事後才對映回聚合維度。

  與古典 Gioia 的差異必須明說：Gioia 的聚合維度是最後浮現的，此處是先給定的。
  因此不得宣稱「採用 Gioia 方法論」，只能說「採 Gioia 式資料結構呈現」。

  歸納不到框架既有維度的主題一律歸入「未歸屬」，不強行塞入框架。
  這批主題是對框架的潛在延伸或挑戰，通常是論文貢獻所在。

  聚合維度不是寫死的：_dimension_block() 從 F.active() 推導。
  內建的 RI 框架只是預設值，不是這個模組的前提。

【語言】
  提示詞以英文撰寫（模型對英文指令遵循度較佳），但輸出語言由 analysis_lang
  決定——研究者可能用英文介面分析中文逐字稿。JSON 鍵一律為 ASCII。
"""

import html
import itertools
import json
import re
import textwrap
import unicodedata
from collections import Counter, defaultdict

import tacit_framework as F
import tacit_schema as S


# 一階概念欄位
GLOBAL_ID = "global_id"
SOURCE_SEGMENT_ID = "source_segment_id"
EXISTING_CODES = "existing_codes"


# =====================================================================
# 1. 一階概念彙集
# =====================================================================
def collect_first_order(records):
    """
    把所有受訪者的編碼段落攤平成一階概念清單，並配發**全域唯一 ID**。
    段落 ID 只在單一受訪者內唯一，跨案例歸納若不重新配發會張冠李戴。
    """
    items = []
    for rec in records:
        resp = rec.get(S.RESPONDENT, "unknown")
        for seg in rec.get(S.SEGMENTS, []):
            items.append({
                GLOBAL_ID: f"G{len(items) + 1:04d}",
                S.RESPONDENT: resp,
                SOURCE_SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                S.TITLE: (seg.get(S.TITLE) or "").strip(),
                S.QUOTE: (seg.get(S.QUOTE) or "").strip(),
                S.FULL_TEXT: (seg.get(S.FULL_TEXT) or "").strip(),
                EXISTING_CODES: S.codes_of(seg),
            })
    return items


def _chunk(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# =====================================================================
# 2. 提示詞
# =====================================================================
_STAGE1_HEADER = """You are an expert in qualitative research methodology, specialising in
Gioia-style data structure analysis.

Below is a batch of FIRST-ORDER CONCEPTS: each line is one coded interview
segment, given as a short title and a verbatim quotation.

Your task is to induce SECOND-ORDER THEMES from them.

=======================================================================
RULES
=======================================================================
1. A second-order theme is a RESEARCHER-LEVEL THEORETICAL CONCEPT, not a
   restatement of informant language.
   Bad:  "Everyone says communication matters"  (merely aggregates concepts)
   Good: "Communication is framed as one-way persuasion, reducing engagement
          to a legitimation device"             (an analytic claim)
2. Theme names must be defensible ANALYTIC PROPOSITIONS, not category labels.
3. Every theme must be constituted by AT LEAST TWO first-order concepts.
   Do not create a theme supported by a single segment.
4. **Do NOT assume any theoretical framework.** Let themes emerge from the
   data's own structure of meaning. Mapping to dimensions happens later.
5. A first-order concept may belong to more than one theme, but be sparing;
   most should belong to exactly one.
6. You need not use every first-order concept. Leaving some unassigned is
   expected — coverage is not the goal.
7. Quotations must be reproduced verbatim; never paraphrase.

{lang_instruction}

=======================================================================
OUTPUT — valid JSON only, no text before or after:
=======================================================================
{{
  "provisional_themes": [
    {{
      "name": "an analytic proposition, roughly 12-25 words",
      "definition": "60-100 words: what pattern of meaning this theme captures, and why these first-order concepts belong together",
      "member_ids": ["G0001", "G0007", "G0012"],
      "exemplar_id": "G0007"
    }}
  ]
}}
"""

_STAGE2_HEADER = """You are an expert in qualitative research methodology. Below are PROVISIONAL
SECOND-ORDER THEMES induced in separate batches from one corpus. Batches may
contain duplicate or highly overlapping themes.

=======================================================================
TASK 1 — CONSOLIDATE
=======================================================================
Merge themes that capture the same or highly overlapping meaning. Keep
dissimilar themes separate. Aim for 8-20 final themes.

=======================================================================
TASK 2 — MAP TO AGGREGATE DIMENSIONS
=======================================================================
Map each final theme to ONE of the following. These are the dimensions of
{framework_name}{framework_citation}:

{dimension_block}

[CRITICAL] Write the identifier exactly as given above, in lower case.

[CRITICAL] Do not force a mapping just to make the framework look complete.
If a theme only marginally touches a dimension, mark it "unassigned" honestly.
Unassigned themes are potential extensions to, or challenges against, the
existing framework and carry high research value; forcing them into the
dimensions destroys the most interesting findings.

[CRITICAL] Equally, do not avoid a dimension. Consider every dimension listed
above for every theme. A dimension receiving no themes at all is a finding
about the data and must not be an artefact of you overlooking it.

Also judge each theme's relation to the framework:
- aligned    : falls squarely within the existing conception of that dimension
- extends    : belongs to that dimension but reveals an under-theorised facet
- challenges : in tension with the dimension's assumptions, or shows the
               framework does not hold in this context

{lang_instruction}

=======================================================================
OUTPUT — valid JSON only, no text before or after:
=======================================================================
{{
  "themes": [
    {{
      "name": "an analytic proposition, roughly 12-25 words",
      "definition": "60-100 words",
      "aggregate_dimension": "{dimension_enum}",
      "dimension_rationale": "under 40 words: why this dimension; if unassigned, what it escapes",
      "frame_relation": "aligned|extends|challenges",
      "polarity_tendency": "P|N|mixed",
      "merged_from": ["provisional theme number", ...]
    }}
  ],
  "unassigned_note": "if there are unassigned themes, 100-150 words on the theoretical gap they jointly point to; otherwise write 'none'"
}}
"""


def build_stage1_prompt(items, analysis_lang=S.DEFAULT_ANALYSIS_LANG):
    lines = []
    for it in items:
        q = it[S.QUOTE] or it[S.FULL_TEXT][:80]
        lines.append(f"{it[GLOBAL_ID]} | {it[S.TITLE]} | \"{q}\"")
    body = "\n".join(lines)
    # 把實際的輸入文字交給語言解析：設為 AUTO 時才有辦法判斷該用哪一種語言。
    header = _STAGE1_HEADER.format(
        lang_instruction=S.analysis_language_instruction(analysis_lang, body))
    return header + "\n=== FIRST-ORDER CONCEPTS ===\n" + body


def _dimension_block(lang="en"):
    """
    第二階段提示詞裡的維度清單，**由作用中的框架產生**。

    要防的失效：這一段若寫死四行負責任創新維度，切換到別的框架之後，
    提示詞照樣叫模型從 anticipation / reflexivity / engagement /
    responsiveness 裡挑一個，模型也照做——然後每一個回傳值都不屬於新框架，
    全部被 norm_dimension 判成 unassigned。結果是換了框架之後，Gioia 圖表
    變成一個大虛線框，而且沒有任何錯誤訊息。

    「維度一律問框架」這條規則，提示詞也算在內。
    """
    fw = F.active()
    # 「未歸屬」也一起排版：它跟其他維度一樣是合法選項，縮排若跟上面幾行
    # 對不齊，讀起來像附註而不像選項，模型也比較容易忽略它。
    entries = [(d, " ".join((fw.definition(d, lang) or fw.label(d, lang)
                             or d).split()))
               for d in fw.dimensions]
    entries.append((S.UNASSIGNED,
                    "THE THEME IS IMPORTANT BUT IS NOT ADEQUATELY COVERED BY "
                    "ANY OF THE DIMENSIONS ABOVE."))
    width = max(len(d) for d, _ in entries)
    pad = " " * (width + 5)
    out = []
    for d, defn in entries:
        # 定義有時很長，硬塞成一行會讓提示詞難讀，模型也更容易看漏後面的維度。
        wrapped = textwrap.wrap(defn, 66) or [""]
        out.append(f"- {d.ljust(width)} : {wrapped[0]}")
        out.extend(f"{pad}{ln}" for ln in wrapped[1:])
    return "\n".join(out)


def _short_citation(fw):
    """引用只取到「作者 (年份)」為止，塞進提示詞用。"""
    m = re.match(r"^(.*?\(\s*\d{4}[a-z]?\s*\))", fw.citation or "")
    return f" — {m.group(1).strip()}" if m else ""


def build_stage2_prompt(provisional, analysis_lang=S.DEFAULT_ANALYSIS_LANG,
                        sample=""):
    lines = []
    for i, t in enumerate(provisional, 1):
        lines.append(f"[{i}] {t[S.THEME_NAME]} ({len(t[S.MEMBER_IDS])} concepts)\n"
                     f"    definition: {t[S.THEME_DEFINITION]}")
    body = "\n".join(lines)
    # 語言依**原始資料**判斷，不依第一階段的產出。
    #
    # 一開始這裡是拿 body（暫定主題）去判斷語言，那有個要命的性質：
    # 第一階段萬一失手產出了另一種語言，第二階段會照著那個錯誤繼續錯下去，
    # 錯誤會自我延續而且看起來很合理。語言是整份語料的屬性，
    # 應該從頭到尾只判斷一次。
    fw = F.active()
    cite = _short_citation(fw)
    header = _STAGE2_HEADER.format(
        lang_instruction=S.analysis_language_instruction(
            analysis_lang, sample or body),
        framework_name=fw.name("en"),
        framework_citation=cite,
        dimension_block=_dimension_block("en"),
        dimension_enum="|".join(S.AGG_DIMENSIONS))
    return header + "\n=== PROVISIONAL THEMES ===\n" + body


# =====================================================================
# 3. 解析與驗證
# =====================================================================
def extract_json(text):
    m = re.search(r"\{.*\}", text or "", re.DOTALL)
    if not m:
        raise ValueError("no JSON object found in response")
    s = m.group(0).replace("\r\n", "\n").replace("\r", "\n")
    out, in_str, esc = [], False, False
    for ch in s:
        if esc:
            out.append(ch); esc = False
        elif ch == "\\" and in_str:
            out.append(ch); esc = True
        elif ch == '"':
            out.append(ch); in_str = not in_str
        elif ch == "\n" and in_str:
            out.append("\\n")
        elif ch == "\t" and in_str:
            out.append("\\t")
        else:
            out.append(ch)
    return json.loads("".join(out))


def parse_stage1(text, valid_ids, min_size=2):
    """解析暫定主題，剔除幻覺 ID 與過小的主題。"""
    data = extract_json(text)
    valid = set(valid_ids)
    out, dropped = [], []
    raw = data.get("provisional_themes") or data.get("暫定主題") or []
    for t in raw:
        if not isinstance(t, dict):
            continue
        name = (t.get(S.THEME_NAME) or t.get("主題名稱") or "").strip()
        if not name:
            continue
        ids = [i for i in (t.get(S.MEMBER_IDS) or t.get("構成ID") or [])
               if i in valid]
        ids = list(dict.fromkeys(ids))
        if len(ids) < min_size:
            dropped.append({S.THEME_NAME: name,
                            "reason": f"only {len(ids)} valid first-order concepts"})
            continue
        rep = t.get("exemplar_id") or t.get("代表引文ID")
        out.append({
            S.THEME_NAME: name,
            S.THEME_DEFINITION: (t.get(S.THEME_DEFINITION)
                                 or t.get("主題定義") or "").strip(),
            S.MEMBER_IDS: ids,
            "exemplar_id": rep if rep in valid else (ids[0] if ids else None),
        })
    return out, dropped


# =====================================================================
# 2b. 輸出格式遵循度探測
# =====================================================================
_PROBE_ITEMS = [
    ("P1", "The team ran a six-month baseline before switching anything on."),
    ("P2", "We are the experts here; the public does not understand the technology."),
    ("P3", "After the residents' meeting we changed the crossing timings."),
    ("P4", "Nobody looked at who would bear the cost if it went wrong."),
    ("P5", "The consultation happened after the design was already signed off."),
    ("P6", "We have no mechanism that would let us stop the rollout."),
]

_PROBE_TEMPLATE = """Map each item below to exactly ONE of these identifiers:

{enum_block}

Rules:
- Write the identifier exactly as listed above, in lower case.
- Choose exactly ONE. Never combine two with a slash, pipe, comma or "and".
- If none fits, write "{unassigned}".

Return valid JSON only, no text before or after:
{{"answers": [{{"id": "P1", "dimension": "<one identifier>"}}, ...]}}

=== ITEMS ===
{items}
"""


def probe_output_contract(generate, dimensions, unassigned=None, items=None):
    """
    模型**照不照得住輸出約定**？回傳 (compliance, detail)。

    為什麼需要這一步：主題歸納的第二階段要模型從一個列舉裡挑一個識別碼。
    實測發現這正是小模型崩掉的地方——不是判斷得不好，是根本沒照格式回答。
    一次真實執行裡，9 個主題有 7 個被判成 unassigned，而模型自己寫的歸屬
    理由明明指名了 anticipation、responsiveness；它寫進 dimension 欄位的
    是複合值或別的東西，守門正確地拒絕猜測，於是整批掉進未歸屬。

    使用者事後只看得到「未歸屬 7 個」，看不出那是資料的性質還是模型的問題。
    這個探測把那件事提前到送出之前，而且花的是幾秒鐘而不是一整輪。

    **這個函式不決定任何事**，只回報數字與模型實際寫了什麼。要不要繼續、
    合不合用，是研究者的判斷——工具負責讓他判斷得出來。

    compliance 是 0–1：回答了幾題、其中幾題給的是列舉裡的單一合法值。
    detail 含 non_conforming（模型實際寫的東西），那是查問題唯一的線索。
    """
    unassigned = unassigned or S.UNASSIGNED
    allowed = list(dimensions) + [unassigned]
    items = items or _PROBE_ITEMS
    enum_block = "\n".join(f"  {d}" for d in allowed)
    prompt = _PROBE_TEMPLATE.format(
        enum_block=enum_block, unassigned=unassigned,
        items="\n".join(f"{i} | {txt}" for i, txt in items))

    detail = {"asked": len(items), "answered": 0, "conforming": 0,
              "non_conforming": [], "valid_json": False, "error": ""}
    try:
        raw = generate(prompt)
    except Exception as e:
        detail["error"] = f"{type(e).__name__}: {e}"
        return 0.0, detail

    try:
        data = extract_json(raw)
    except Exception:
        data = {}
    answers = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(answers, list):
        # 連 JSON 都沒給出來，是最嚴重的一種不合格
        detail["error"] = detail["error"] or "no JSON object with an 'answers' list"
        detail["non_conforming"].append({"id": "-", "wrote": str(raw)[:120]})
        return 0.0, detail
    detail["valid_json"] = True

    seen = set()
    for a in answers:
        if not isinstance(a, dict):
            continue
        aid = str(a.get("id") or "").strip()
        if aid in seen:
            continue
        seen.add(aid)
        detail["answered"] += 1
        wrote = a.get("dimension", a.get("aggregate_dimension"))
        wrote_s = "" if wrote is None else str(wrote)
        # 合格的定義刻意嚴格：必須是列舉裡的單一值。
        # 「大小寫不同」算合格（norm_dimension 本來就容錯），
        # 「複合值」不算——那代表模型沒有做出選擇。
        norm = S.norm_dimension(wrote_s)
        if norm in allowed and norm is not None:
            detail["conforming"] += 1
        else:
            detail["non_conforming"].append({"id": aid or "-",
                                             "wrote": wrote_s[:80]})
    n = detail["answered"] or len(items)
    return (detail["conforming"] / n if n else 0.0), detail


def contract_verdict(compliance, detail, threshold=0.9):
    """
    把探測結果翻成一個可讀的判斷。**不擋任何東西**，只給說法。

    門檻訂 0.9 而不是 1.0：偶爾一題失手是模型的常態抖動，整批不照格式
    才是問題。低於 0.6 幾乎必然做不出可用的主題歸納——實測那次是 0.22。
    """
    if detail.get("error") and not detail.get("valid_json"):
        return "unusable"
    if compliance >= threshold:
        return "ok"
    if compliance >= 0.6:
        return "shaky"
    return "unusable"


def parse_stage2(text, provisional, issues=None):
    """
    解析最終主題，把 merged_from 還原成實際的一階概念 ID。

    issues: 可傳入一個 list，用來收集**沒被認出來的維度字串**。
    模型寫了個認不得的值時，該主題會落到 unassigned；不記下它原本寫了
    什麼，介面上就只看得到「未歸屬 +1」，查不出是模型判斷如此，還是
    格式沒遵守。實測 qwen2.5:7b 會把輸出格式的列舉整串抄回來
    （"engagement|responsiveness"），沒有這份記錄根本查不到。
    """
    data = extract_json(text)
    themes = []
    raw = data.get("themes") or data.get("二階主題") or []
    for k, t in enumerate(raw, 1):
        if not isinstance(t, dict):
            continue
        name = (t.get(S.THEME_NAME) or t.get("主題名稱") or "").strip()
        if not name:
            continue
        if issues is not None:
            _rawdim = t.get(S.AGG_DIMENSION, t.get("聚合維度"))
            if _rawdim is not None and S.norm_dimension(_rawdim) is None:
                issues.append({"theme": name[:60], "wrote": str(_rawdim)[:80]})
        idxs = []
        for item in (t.get(S.MERGED_FROM) or t.get("合併自") or []):
            m = re.search(r"\d+", str(item))
            if m:
                j = int(m.group(0)) - 1
                if 0 <= j < len(provisional):
                    idxs.append(j)
        ids = []
        for j in dict.fromkeys(idxs):
            ids.extend(provisional[j][S.MEMBER_IDS])
        theme = S.migrate_theme({**t, S.THEME_NAME: name,
                                 S.MEMBER_IDS: list(dict.fromkeys(ids)),
                                 S.MERGED_FROM: [provisional[j][S.THEME_NAME]
                                                 for j in dict.fromkeys(idxs)]}, k)
        themes.append(theme)

    order = {d: i for i, d in enumerate(S.AGG_DIMENSIONS)}
    themes.sort(key=lambda t: (order.get(t[S.AGG_DIMENSION], 99), t[S.THEME_ID]))
    for k, t in enumerate(themes, 1):
        t[S.THEME_ID] = f"T{k:02d}"
    note = (data.get("unassigned_note") or data.get("未歸屬綜合說明") or "").strip()
    return themes, note


def induce_themes(items, generate, chunk_size=60, min_size=2, on_progress=None,
                  analysis_lang=S.DEFAULT_ANALYSIS_LANG):
    """
    兩階段主題歸納。

    generate: callable(prompt:str) -> str，把 LLM 呼叫注入進來（便於測試與換模型）
    回傳 (themes, unassigned_note, debug)

    語言由**原始一階概念**決定一次，兩階段共用。不讓第二階段去看第一階段的
    產出來猜語言——否則第一階段一旦失手，錯誤會沿著管線自我延續。
    """
    valid_ids = [it[GLOBAL_ID] for it in items]
    # 取原始一階概念的標題與引文當語言樣本（取前 40 筆已足夠判斷字種）
    lang_sample = " ".join(
        f"{it.get(S.TITLE, '')} {it.get(S.QUOTE, '')}" for it in items[:40])
    provisional, dropped = [], []
    chunks = list(_chunk(items, chunk_size))
    for i, ch in enumerate(chunks, 1):
        if on_progress:
            on_progress("stage1", i - 1, len(chunks) + 1, len(ch))
        prov, drp = parse_stage1(
            generate(build_stage1_prompt(ch, analysis_lang)), valid_ids, min_size)
        provisional.extend(prov)
        dropped.extend(drp)

    if not provisional:
        return [], "", {"provisional_count": 0, "batches": len(chunks),
                        "dropped": dropped, "orphans": []}

    if on_progress:
        on_progress("stage2", len(chunks), len(chunks) + 1, len(provisional))
    dim_issues = []
    themes, note = parse_stage2(
        generate(build_stage2_prompt(provisional, analysis_lang, lang_sample)),
        provisional, issues=dim_issues)

    used = {n for t in themes for n in t[S.MERGED_FROM]}
    orphan = [p[S.THEME_NAME] for p in provisional if p[S.THEME_NAME] not in used]
    empty_dims = [d for d in F.active().dimensions
                  if not any(t[S.AGG_DIMENSION] == d for t in themes)]
    debug = {"provisional_count": len(provisional), "batches": len(chunks),
             "final_count": len(themes), "dropped": dropped, "orphans": orphan,
             # 這兩項是給研究者判斷「少一個維度是發現還是失誤」用的。
             "empty_dimensions": empty_dims,
             "unrecognised_dimensions": dim_issues}
    return themes, note, debug


# =====================================================================
# 3b. 不用模型的主題收斂：依共現把碼分群
# =====================================================================
# 為什麼要有這條路
# ----------------
# 主題歸納是這套工具最依賴模型的一步，而它也是最不需要依賴模型的一步。
# 把一階概念收成二階主題，傳統上靠的是研究者反覆比對；CAQDAS 早就有機械
# 的輔助（NVivo 的 cluster analysis 用詞彙相似度分群）。這裡做的是同一件
# 事的另一種算法：**兩個碼常常出現在同一段話裡，就把它們放在一起**。
#
# 刻意只做到「提出分組」為止。命名與判斷留給研究者，理由不是做不到，而是
# 二階主題的名字就是詮釋本身；讓模型代筆，等於把研究者的工作外包出去，
# 而那正是這套工具在其他地方一直拒絕的事。分群是確定性的，換誰跑都一樣；
# 名字是人給的，記在檔案裡有署名。
#
# 產出的形狀與 induce_themes 相同，所以主題表、跨個案矩陣、覆蓋報表與
# Gioia 匯出全部原封不動能用——跟「碼簿定案成框架」是同一個關節。

CLUSTER_MEMBER_CODES = "member_codes"
CLUSTER_DISTANCE = "merge_distance"


def cooccurrence_distances(counts, totals, codes=None):
    """
    1 − Jaccard，吃 tacit_analysis.cooccurrence() 的回傳值。

    **適用範圍要講清楚。** 這個基底只有在「一段話常被標上不只一個碼」時
    才有資訊。實測一顆 8B 地端模型開放編碼 24 份聽證會逐字稿，936 個段落
    裡只有 79 個帶超過一個碼，352 個碼之間只有 72 對曾經共現——距離矩陣
    幾乎整片都是 1.0，分出來的群沒有任何根據。那種碼簿要用 label_distances。
    分群結果帶著 merge_distance 就是為了讓這件事看得見：接近 1.0 就是
    「這一組是湊出來的」。
    """
    pool = list(codes if codes is not None else totals.index)
    out = {}
    for a, b in itertools.combinations(pool, 2):
        n = float(counts.loc[a, b])
        union = float(totals[a]) + float(totals[b]) - n
        d = 1.0 if union <= 0 else 1.0 - (n / union)
        out[(a, b)] = out[(b, a)] = d
    return out


def label_distances(texts):
    """
    1 − Dice（字元二元組），用碼的標籤與定義算。texts: {code: 文字}。

    開放編碼的碼簿用這個基底。理由與 tacit_open.similar_pairs 選 Dice 的
    理由相同：碼的標籤很短，Jaccard 的分母把兩邊的獨有字元都算進去，短字串
    差一兩個字就掉到門檻以下。
    """
    import tacit_open as OP                      # 只有這條路徑需要，避免循環匯入
    grams = {c: OP._bigrams(t or c) for c, t in texts.items()}
    out = {}
    for a, b in itertools.combinations(list(texts), 2):
        ga, gb = grams[a], grams[b]
        tot = len(ga) + len(gb)
        d = 1.0 if not tot else 1.0 - (2.0 * len(ga & gb) / tot)
        out[(a, b)] = out[(b, a)] = d
    return out


def cluster_codes(dist, codes, k=None, max_distance=0.85, weights=None):
    """
    把碼做凝聚式階層分群（平均連結），不呼叫任何模型。

    dist:         {(碼A, 碼B): 距離}，由 cooccurrence_distances 或
                  label_distances 產生。分群本身不在意距離怎麼來的。
    codes:        要參與分群的碼。
    k:            想要幾群。給了就一路合併到剩 k 群，**不受 max_distance 限制**
                  ——研究者說「給我六組」時要的是六組，但每一群都會帶著
                  merge_distance，看得出這一組是硬湊的還是本來就靠在一起。
    max_distance: k 為 None 時才生效：平均距離超過它就停止合併。
    weights:      {碼: 次數}，只用來決定輸出順序。
    """
    pool = list(codes)
    clusters = [{CLUSTER_MEMBER_CODES: [c], CLUSTER_DISTANCE: 0.0} for c in pool]
    if len(clusters) < 2:
        return clusters

    def linkage(g1, g2):
        """平均連結。單一連結會拉出一條鏈，把本來無關的碼串成一大群。"""
        pairs = [dist[(x, y)] for x in g1[CLUSTER_MEMBER_CODES]
                 for y in g2[CLUSTER_MEMBER_CODES]]
        return sum(pairs) / len(pairs)

    target = max(1, int(k)) if k else None
    while len(clusters) > 1:
        if target is not None and len(clusters) <= target:
            break
        best, bi, bj = None, -1, -1
        for i, j in itertools.combinations(range(len(clusters)), 2):
            d = linkage(clusters[i], clusters[j])
            if best is None or d < best:
                best, bi, bj = d, i, j
        if best is None or (target is None and best > max_distance):
            break
        merged = {
            CLUSTER_MEMBER_CODES: (clusters[bi][CLUSTER_MEMBER_CODES] +
                                   clusters[bj][CLUSTER_MEMBER_CODES]),
            CLUSTER_DISTANCE: round(best, 4),
        }
        clusters = [c for idx, c in enumerate(clusters) if idx not in (bi, bj)]
        clusters.append(merged)

    # weights 常常是 pandas 的 Series（cooccurrence 的回傳值就是），
    # `weights or {}` 對 Series 會去問它的真值然後拋 ValueError。
    w = {} if weights is None else weights

    def weight(g):
        return sum(float(w.get(c, 0)) for c in g[CLUSTER_MEMBER_CODES])

    for g in clusters:
        g[CLUSTER_MEMBER_CODES] = sorted(g[CLUSTER_MEMBER_CODES],
                                         key=lambda c: (-float(w.get(c, 0)), c))
    clusters.sort(key=lambda g: (-weight(g), g[CLUSTER_MEMBER_CODES][0]))
    return clusters


def themes_from_clusters(clusters, items, names=None):
    """
    把分群結果轉成主題結構，形狀與 parse_stage2 的輸出相同。

    names: {群序號(從 1 起): 研究者給的名字}。沒給名字的群，名字留空——
    介面應該要求研究者補上，而不是替他生一個。一個沒有名字的主題在報表上
    看得出來是未完成的；自動生成的名字看起來像完成了。
    """
    names = names or {}
    by_code = defaultdict(list)
    for it in items:
        for c in it.get(EXISTING_CODES) or []:
            by_code[c].append(it[GLOBAL_ID])

    themes = []
    for k, g in enumerate(clusters, 1):
        ids = []
        for c in g[CLUSTER_MEMBER_CODES]:
            ids.extend(by_code.get(c, []))
        ids = list(dict.fromkeys(ids))
        if not ids:
            continue
        themes.append(S.migrate_theme({
            S.THEME_NAME: str(names.get(k, "") or "").strip(),
            S.THEME_DEFINITION: "",
            S.MEMBER_IDS: ids,
            S.MERGED_FROM: list(g[CLUSTER_MEMBER_CODES]),
        }, len(themes) + 1))
    for k, t in enumerate(themes, 1):
        t[S.THEME_ID] = f"T{k:02d}"
    return themes


# =====================================================================
# 4. 主題層統計
# =====================================================================
def index_items(items):
    return {it[GLOBAL_ID]: it for it in items}


def theme_table(themes, items):
    idx = index_items(items)
    rows = []
    for t in themes:
        segs = [idx[i] for i in t[S.MEMBER_IDS] if i in idx]
        speakers = sorted({s[S.RESPONDENT] for s in segs})
        rows.append({
            S.THEME_ID: t[S.THEME_ID],
            S.AGG_DIMENSION: t[S.AGG_DIMENSION],
            S.THEME_NAME: t[S.THEME_NAME],
            S.POLARITY_TENDENCY: t[S.POLARITY_TENDENCY],
            S.FRAME_RELATION: t[S.FRAME_RELATION],
            "concept_count": len(segs),
            "respondent_count": len(speakers),
            "respondents": speakers,
            S.THEME_DEFINITION: t[S.THEME_DEFINITION],
            S.DIM_RATIONALE: t[S.DIM_RATIONALE],
            "exemplar_quote": segs[0][S.QUOTE] if segs else "",
        })
    return rows


def theme_case_matrix(themes, items):
    """主題 × 受訪者。集中在一兩位受訪者身上的主題是薄弱主題。"""
    idx = index_items(items)
    # 依首次出現順序排列；中文姓名照 Unicode 碼位排序沒有意義
    speakers = list(dict.fromkeys(it[S.RESPONDENT] for it in items))
    rows = []
    for t in themes:
        cnt = Counter(idx[i][S.RESPONDENT] for i in t[S.MEMBER_IDS] if i in idx)
        row = {S.THEME_ID: t[S.THEME_ID], S.AGG_DIMENSION: t[S.AGG_DIMENSION],
               S.THEME_NAME: t[S.THEME_NAME]}
        row.update({s: cnt.get(s, 0) for s in speakers})
        row["respondent_count"] = sum(1 for s in speakers if cnt.get(s, 0))
        row["support_rate"] = (round(row["respondent_count"] / len(speakers), 2)
                               if speakers else 0.0)
        rows.append(row)
    return rows, speakers


def theme_by_existing_code(themes, items):
    """主題 × 既有八格編碼，檢查歸納主題與演繹編碼的吻合程度。"""
    idx = index_items(items)
    rows = []
    for t in themes:
        cnt = Counter()
        for i in t[S.MEMBER_IDS]:
            for c in idx.get(i, {}).get(EXISTING_CODES, []):
                cnt[c] += 1
        row = {S.THEME_ID: t[S.THEME_ID], S.AGG_DIMENSION: t[S.AGG_DIMENSION],
               S.THEME_NAME: t[S.THEME_NAME]}
        row.update(dict(cnt))
        rows.append(row)
    return rows


def coverage_report(themes, items):
    idx = index_items(items)
    assigned = {i for t in themes for i in t[S.MEMBER_IDS]}
    total = len(items)
    thin = [t[S.THEME_ID] for t in themes
            if len({idx[i][S.RESPONDENT] for i in t[S.MEMBER_IDS] if i in idx}) < 2]
    by_dim = Counter(t[S.AGG_DIMENSION] for t in themes)
    return {
        "total_concepts": total,
        "assigned_concepts": len(assigned),
        "unassigned_concepts": total - len(assigned),
        "coverage": round(len(assigned) / total, 3) if total else 0.0,
        "theme_count": len(themes),
        "thin_themes": thin,
        "themes_by_dimension": {d: by_dim.get(d, 0) for d in S.AGG_DIMENSIONS},
    }


def unassigned_items(themes, items):
    assigned = {i for t in themes for i in t[S.MEMBER_IDS]}
    return [it for it in items if it[GLOBAL_ID] not in assigned]


# =====================================================================
# 5. Gioia 式資料結構圖（SVG）
# =====================================================================
# 維度配色。
#
# 要防的失效：這裡若是一張寫死四個 RI 維度 id 的對照表、取色時
# `.get(dim, "#555")`。換到 UTAUT 或 ESG，每一個維度都落到那個灰色預設值
# ——Gioia 資料結構圖是靠顏色區分聚合維度的，全灰等於這張圖失去作用。
# 不會當掉，所以也不會有人發現。
#
# 改成依作用中框架的維度順序**算**出顏色，而不是查一張固定長度的表。
#
# 固定調色盤會在維度多的時候壞掉，而且壞得很安靜：內建的 TDF 框架有 14 個
# 領域，一張八色的表會讓第 9 個維度跟第 1 個同色——Gioia 圖正是靠顏色區分
# 聚合維度的，兩個維度同色等於那張圖在說謊。
#
# 依維度在框架裡的位置在色相環上均分，飽和度與明度固定在同一組值，任何
# 維度數量都拿得到彼此可分的顏色，而且同一個框架的同一個維度每次都一樣。
_UNASSIGNED_COLOR = "#8A2F45"     # 未歸屬固定用這個紅，不參與色相環
_HUE_START = 168                  # 從內建 RI 原本的第一個顏色起算，維持觀感
_SAT, _LIGHT = 0.42, 0.36         # 印刷友善：不刺眼、白字放得上去


def _hsl_hex(h, s, light):
    """HSL → #RRGGBB。只在這裡用，不值得為它多一個相依。"""
    import colorsys
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, light, s)
    return "#{:02X}{:02X}{:02X}".format(int(r * 255 + 0.5),
                                        int(g * 255 + 0.5),
                                        int(b * 255 + 0.5))


def dim_color(dim_id):
    """維度對應的顏色。未歸屬固定；其餘依框架宣告的順序在色相環上均分。"""
    if dim_id == S.UNASSIGNED:
        return _UNASSIGNED_COLOR
    dims = list(F.active().dimensions)
    if dim_id not in dims:
        return "#555"
    n = max(1, len(dims))
    return _hsl_hex(_HUE_START + 360.0 * dims.index(dim_id) / n, _SAT, _LIGHT)

DEFAULT_COLUMN_TITLES = ("1st-Order Concepts", "2nd-Order Themes",
                         "Aggregate Dimensions")


# 斷行用的切分：空白、單一個 CJK 字、或一整串非空白的西文。
# CJK 每個字都是合法斷點（中文本來就不用空白斷詞）；西文只在空白處斷。
_CJK = r"ᄀ-ᇿ⺀-〿぀-鿿가-힯豈-﫿︰-﹏＀-￯"
_TOKENS = re.compile(f"[\\s]+|[{_CJK}]|[^\\s{_CJK}]+")


def _display_width(s):
    """CJK 字形在同一字級下約為西文的兩倍寬，排版寬度要照這個算。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
               for c in s)


def _wrap(text, per_line):
    """
    折行。**不可以在單字中間切開。**

    要防的失效：`text[i:i + per_line]` 這種純粹按字元數的硬切，會讓
    匯出的 Gioia 資料結構圖長這樣——

        "Requires a plan f" / "or inconvenient f" / "indings (A05 (Cha" /
        "ir, university re" / "search ethics com" / "mittee))"

    每一個換行都切在字母中間。圖是要放進論文的，讀者會直接看到
    "com/mittee"。測試也要逐行驗：把所有 <text> 節點接回來再比對的話，
    "Public Engag" + "ement" 也算通過。

    per_line 的單位是「西文字元寬」，CJK 字算兩格（見 _display_width）。
    真的塞不下的單一長詞（例如網址）才硬切——那是合理的，不是這裡的問題。
    """
    text = (text or "").strip()
    if not text:
        return [""]
    per_line = max(1, int(per_line))

    lines, cur, cur_w = [], "", 0
    for tok in _TOKENS.findall(text):
        if tok.isspace():
            # 行首不留空白；行中的空白照常累積
            if cur:
                cur, cur_w = cur + " ", cur_w + 1
            continue
        w = _display_width(tok)
        if cur_w + w > per_line and cur.strip():
            lines.append(cur.rstrip())
            cur, cur_w = "", 0
        while w > per_line:
            # 單一 token 比整行還長（長網址、無空白的長字），只好硬切
            take = per_line - cur_w
            if take <= 0:
                lines.append(cur.rstrip()); cur, cur_w = "", 0; take = per_line
            cut = 0
            acc = 0
            for ch in tok:
                cw = _display_width(ch)
                if acc + cw > take:
                    break
                acc += cw; cut += 1
            cut = max(1, cut)
            cur += tok[:cut]
            lines.append(cur.rstrip())
            tok = tok[cut:]
            w = _display_width(tok)
            cur, cur_w = "", 0
        if tok:
            cur += tok
            cur_w += w
    if cur.strip():
        lines.append(cur.rstrip())
    return lines or [""]


# ---- 資料結構圖的字級 ---------------------------------------------------
#
# 這張圖宣稱「可直接放進論文」，所以字級要用印出來的尺寸去定，不是看螢幕。
# 畫布寬 960 單位，放成期刊單欄全寬 6.27 吋，1 單位 = 6.27 × 72 / 960 = 0.470 pt。
# Elsevier 要求圖內文字至少 7 pt，也就是至少 14.9 單位。
#
# 字級若是 9 / 10.5 / 11 / 12 / 13，換算只有 4.2–6.1 pt，整張圖沒有一個字過關。
# 等比放大畫布不會改善——比例不變，縮回版面寬度後還是一樣小。要改的是
# 「字級對畫布寬度」的比例，代價是圖變高。
SVG_WIDTH = 960
SVG_PT_PER_UNIT = 6.27 * 72 / SVG_WIDTH
SVG_MIN_FONT = 15            # 7.05 pt
FS_CONCEPT = 16              # 一階概念
FS_THEME = 17                # 二階主題
FS_DIM = 18                  # 聚合維度
FS_HEADER = 19               # 欄標題
FS_BADGE = 15                # 與框架關係的小標
# 西文平均字寬：一般字重約 0.55 em，粗體約 0.62 em。CJK 在 _display_width
# 裡算兩格，等於 1.1–1.24 em，略保守，中文不會溢出框外。
_EM_REGULAR = 0.55
_EM_BOLD = 0.62


def _chars_per_line(box_width, font_size, pad, bold=False):
    em = _EM_BOLD if bold else _EM_REGULAR
    return max(6, int((box_width - 2 * pad) / (font_size * em)))


def render_data_structure_svg(themes, items, max_first_order_per_theme=5,
                              show_speaker=True, dim_label=None,
                              relation_label=None, column_titles=None,
                              more_label="…and {n} more"):
    """
    三欄式 Gioia 資料結構圖。純 SVG，無外部相依，可直接放進論文。

    顯示文字由呼叫端注入（dim_label / relation_label / column_titles），
    這樣同一份程式可以產出任何語言的圖，而不必把 i18n 綁進繪圖邏輯。

    字級規則見上方常數：放成 6.27 吋寬時任何文字都不小於 7 pt。
    """
    dim_label = dim_label or (lambda d: d)
    relation_label = relation_label or (lambda r: r)
    column_titles = column_titles or DEFAULT_COLUMN_TITLES

    if not themes:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60">'
                f'<text x="10" y="35" font-size="{SVG_MIN_FONT}">No themes to display'
                f'</text></svg>')

    idx = index_items(items)
    X1, W1 = 20, 300
    X2, W2 = 370, 330
    X3, W3 = 750, 190
    PAD, GAP = 10, 10
    LH1 = round(FS_CONCEPT * 1.3)        # 一階概念行高
    LH2 = round(FS_THEME * 1.3)          # 二階主題行高
    LH3 = round(FS_DIM * 1.3)            # 聚合維度行高
    BADGE_H = round(FS_BADGE * 1.4)
    HEADER_Y, RULE_Y, TOP = 34, 48, 64

    wrap1 = _chars_per_line(W1, FS_CONCEPT, PAD)
    wrap2 = _chars_per_line(W2, FS_THEME, PAD, bold=True)
    wrap3 = _chars_per_line(W3, FS_DIM, PAD, bold=True)

    layout, y = [], TOP
    for t in themes:
        segs = [idx[i] for i in t[S.MEMBER_IDS] if i in idx]
        shown = segs[:max_first_order_per_theme]
        extra = len(segs) - len(shown)

        boxes, yy = [], y
        for s in shown:
            label = s[S.TITLE] or s[S.QUOTE][:40]
            if show_speaker:
                label = f"{label} ({s[S.RESPONDENT]})"
            lines = _wrap(label, wrap1)
            h = len(lines) * LH1 + PAD * 2
            boxes.append({"y": yy, "h": h, "lines": lines})
            yy += h + GAP
        if extra > 0:
            lines = [more_label.format(n=extra)]
            h = LH1 + PAD * 2
            boxes.append({"y": yy, "h": h, "lines": lines, "muted": True})
            yy += h + GAP

        has_badge = t[S.FRAME_RELATION] != S.RELATION_ALIGNED
        tlines = _wrap(f"{t[S.THEME_ID]}  {t[S.THEME_NAME]}", wrap2)
        th = len(tlines) * LH2 + PAD * 2 + (BADGE_H if has_badge else 0)
        th = max(th, 48)
        group_h = max(yy - y - GAP, th)
        layout.append({"theme": t, "boxes": boxes, "top": y, "badge": has_badge,
                       "group_h": group_h, "tlines": tlines, "th": th})
        y += group_h + 28

    total_h = int(y + 24)

    groups, cur = [], None
    for L in layout:
        d = L["theme"][S.AGG_DIMENSION]
        if cur and cur["dim"] == d:
            cur["items"].append(L)
        else:
            cur = {"dim": d, "items": [L]}
            groups.append(cur)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{total_h}" '
           f'viewBox="0 0 {SVG_WIDTH} {total_h}" '
           f'font-family="Noto Sans TC, Microsoft JhengHei, Arial, sans-serif">',
           '<rect width="100%" height="100%" fill="#ffffff"/>']
    # 第三欄只有 190 寬，放大後的欄標題比欄還寬；改成靠右對齊畫布右緣，
    # 向左延伸進第二欄右側的空白，而不是超出畫布被裁掉。
    for x, anchor, label in [(X1, "start", column_titles[0]),
                             (X2, "start", column_titles[1]),
                             (SVG_WIDTH - 20, "end", column_titles[2])]:
        out.append(f'<text x="{x}" y="{HEADER_Y}" font-size="{FS_HEADER}" '
                   f'font-weight="700" text-anchor="{anchor}" fill="#333">'
                   f'{html.escape(str(label))}</text>')
    out.append(f'<line x1="20" y1="{RULE_Y}" x2="{SVG_WIDTH - 20}" y2="{RULE_Y}" '
               f'stroke="#ccc" stroke-width="1"/>')

    # 基線放在行高內偏下的位置，字母下伸部不會壓到框線
    def baseline(top, lh, k, fs):
        return round(top + PAD + lh * k + (lh + fs * 0.72) / 2, 1)

    for L in layout:
        t = L["theme"]
        color = dim_color(t[S.AGG_DIMENSION])
        tcy = L["top"] + L["group_h"] / 2
        ty = tcy - L["th"] / 2

        for b in L["boxes"]:
            fill = "#fbfbfb" if b.get("muted") else "#f7f7f9"
            style = ' stroke-dasharray="3 3"' if b.get("muted") else ""
            out.append(f'<rect x="{X1}" y="{b["y"]}" width="{W1}" height="{b["h"]}" '
                       f'rx="4" fill="{fill}" stroke="#bbb"{style}/>')
            for k, ln in enumerate(b["lines"]):
                out.append(f'<text x="{X1 + PAD}" y="{baseline(b["y"], LH1, k, FS_CONCEPT)}" '
                           f'font-size="{FS_CONCEPT}" fill="#333">{html.escape(ln)}</text>')
            cy = b["y"] + b["h"] / 2
            out.append(f'<path d="M{X1 + W1} {cy} C{X1 + W1 + 25} {cy}, {X2 - 25} {tcy}, '
                       f'{X2} {tcy}" fill="none" stroke="{color}" stroke-width="1.2" '
                       f'opacity="0.5"/>')

        out.append(f'<rect x="{X2}" y="{ty}" width="{W2}" height="{L["th"]}" rx="5" '
                   f'fill="#ffffff" stroke="{color}" stroke-width="1.8"/>')
        for k, ln in enumerate(L["tlines"]):
            out.append(f'<text x="{X2 + PAD}" y="{baseline(ty, LH2, k, FS_THEME)}" '
                       f'font-size="{FS_THEME}" font-weight="600" fill="#222">'
                       f'{html.escape(ln)}</text>')
        if L["badge"]:
            # 放在主題文字下方而不是右上角：字放大之後，角落的小標會壓到標題
            by = ty + PAD + len(L["tlines"]) * LH2 + FS_BADGE
            out.append(f'<text x="{X2 + W2 - PAD}" y="{round(by, 1)}" '
                       f'font-size="{FS_BADGE}" font-style="italic" '
                       f'text-anchor="end" fill="{color}">'
                       f'{html.escape(str(relation_label(t[S.FRAME_RELATION])))}</text>')

    for g in groups:
        color = dim_color(g["dim"])
        top = min(L["top"] + L["group_h"] / 2 - L["th"] / 2 for L in g["items"])
        bot = max(L["top"] + L["group_h"] / 2 + L["th"] / 2 for L in g["items"])
        lines = _wrap(str(dim_label(g["dim"])), wrap3)
        h = max(bot - top, len(lines) * LH3 + PAD * 2, 48)
        cy = (top + bot) / 2
        top = cy - h / 2
        dash = ' stroke-dasharray="5 4"' if g["dim"] == S.UNASSIGNED else ""
        out.append(f'<rect x="{X3}" y="{top}" width="{W3}" height="{h}" rx="6" '
                   f'fill="{color}" fill-opacity="0.08" stroke="{color}" '
                   f'stroke-width="1.8"{dash}/>')
        for L in g["items"]:
            ty = L["top"] + L["group_h"] / 2
            out.append(f'<path d="M{X2 + W2} {ty} C{X2 + W2 + 22} {ty}, {X3 - 22} {cy}, '
                       f'{X3} {cy}" fill="none" stroke="{color}" stroke-width="1.4" '
                       f'opacity="0.6"/>')
        first = cy - (len(lines) * LH3) / 2
        for k, ln in enumerate(lines):
            out.append(f'<text x="{X3 + W3 / 2}" '
                       f'y="{round(first + LH3 * k + (LH3 + FS_DIM * 0.72) / 2, 1)}" '
                       f'font-size="{FS_DIM}" font-weight="700" text-anchor="middle" '
                       f'fill="{color}">{html.escape(ln)}</text>')

    out.append("</svg>")
    return "\n".join(out)
