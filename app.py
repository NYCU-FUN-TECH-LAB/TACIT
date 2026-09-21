"""
app.py — TACIT
=================================================================
Theory-driven qualitative coding with pluggable frameworks.

架構分層（由下而上）：
    tacit_framework   理論框架：維度、極性模型、定義、文獻      ← 可插拔
    tacit_schema      資料欄位識別碼與舊檔遷移
    tacit_i18n        顯示標籤（英文預設，可切繁中）
    tacit_analysis    交互分析引擎
    tacit_themes / tacit_lexicon / tacit_irr / tacit_review   各功能模組
    app            只負責介面

本檔案不應出現任何寫死的維度名稱或顯示文字：
維度一律問框架，文字一律查 i18n。

執行： streamlit run app.py
"""

import copy
import io
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime

import docx
import pandas as pd
import streamlit as st

import tacit_llm as LLM
import tacit_framework as F
import tacit_schema as S
import tacit_i18n as I
import tacit_strings  # noqa: F401  匯入即註冊介面文案
import tacit_analysis as A
import tacit_coding as CH
import tacit_open as OP
import tacit_themes as RT
import tacit_lexicon as RL
import tacit_irr as RIRR
import tacit_review as RV
import tacit_openalex as OA

try:
    import plotly.express as px
    import plotly.graph_objects as go
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False

try:
    import streamlit.components.v1 as components
    HAS_COMPONENTS = True
except Exception:
    HAS_COMPONENTS = False


# =====================================================================
# 0. 路徑與相容性
# =====================================================================
# 兩個資料夾不可同名：scan_saved 會分別以 "pro" 與 "legacy" 兩個標籤各掃一次，
# 名稱相同的話每一筆紀錄都會在側欄出現兩遍，而且其中一遍被標成舊格式。
SAVE_DIR_LEGACY = "analyses_v1"           # 早期版本的中文鍵存檔，只讀不寫
SAVE_DIR = "analyses"                     # 目前版本的存檔位置
# OpenAlex 回應快取。放在專案資料夾而非使用者家目錄，
# 是為了讓快取能隨專案一起交付，其他人不需金鑰即可重現檢索。
OA_CACHE_DIR = "openalex_cache"
THEMES_PATH = "themes.json"
IRR_PATH = "irr_session.json"
LEXICON_DIR = "."
for _d in (SAVE_DIR_LEGACY, SAVE_DIR, F.FRAMEWORK_DIR):
    os.makedirs(_d, exist_ok=True)


def _stretch_kwargs():
    """Streamlit 1.43 起 use_container_width 改名為 width="stretch"。"""
    try:
        major, minor = (int(x) for x in st.__version__.split(".")[:2])
        if (major, minor) >= (1, 43):
            return {"width": "stretch"}
    except Exception:
        pass
    return {"use_container_width": True}


WIDE = _stretch_kwargs()


def t(key, **kw):
    return I.t(key, **kw)


# =====================================================================
# 1. 顯示層工具：把 ASCII 識別碼換成當下語言的標籤
# =====================================================================
def label_codes(values):
    return [I.code_label(v) for v in values]


def label_dims(values):
    return [I.dim(v) for v in values]


# DataFrame 欄名 → 顯示標籤。找不到對應就原樣顯示（識別碼本身仍可讀）。
_COL_KEYS = {
    S.RESPONDENT: "common.respondent", S.SEGMENT_ID: "common.segment_id",
    S.DIMENSION: "common.dimension", S.POLARITY: "common.polarity",
    S.TITLE: "common.title", S.QUOTE: "common.quote",
    S.FULL_TEXT: "common.full_text", S.RATIONALE: "common.rationale",
    S.STATUS: "common.status", S.SOURCE: "common.source",
    S.TEXT: "common.text", S.SPEAKER: "common.speaker",
    S.UNIT_ID: "common.segment_id",
    A.CODE: "common.code", A.MULTI_CODED: "cross.tab2",
    "segments": "health.segments", "codes": "health.codes",
    "multi_coded_segments": "health.multi_segments",
    "multi_coded_rate": "health.multi_rate",
    "dimensions_covered": "health.dims_covered",
    "kappa": "stat.kappa", "pabak": "stat.pabak", "ac1": "stat.ac1",
    "observed_agreement": "stat.agreement", "precision": "stat.precision",
    "recall": "stat.recall", "f1": "stat.f1", "jaccard": "stat.jaccard",
    "prevalence_index": "stat.prevalence_index", "bias_index": "stat.bias_index",
    "n": "stat.n",
}


def pretty(df, code_cols=(), dim_cols=()):
    """回傳可直接顯示的 DataFrame：欄名翻譯、識別碼欄位換成標籤。"""
    if df is None or (hasattr(df, "empty") and df.empty):
        return df
    out = df.copy()
    for c in code_cols:
        if c in out.columns:
            out[c] = out[c].map(lambda v: I.code_label(v) if isinstance(v, str) else v)
    for c in dim_cols:
        if c in out.columns:
            out[c] = out[c].map(lambda v: I.dim(v) if isinstance(v, str) else v)
    for c in out.columns:
        if isinstance(c, str) and c in S.DESCRIPTOR_KEYS:
            out[c] = out[c].map(
                lambda v: I.descriptor_value(v) if isinstance(v, str) else v)
    rename = {}
    for c in out.columns:
        if not isinstance(c, str):
            continue
        if c in _COL_KEYS:
            rename[c] = t(_COL_KEYS[c])
        elif c in S.DESCRIPTOR_KEYS or c == S.DESCRIPTOR_BASIS:
            rename[c] = I.descriptor(c)
        elif c in S.CODES:
            rename[c] = c            # 編碼縮寫本身就是通用的，保持原樣較易讀
    return out.rename(columns=rename)


def show_df(df, **kw):
    st.dataframe(df, **WIDE, **kw)


def heatmap(df, title, colorscale="Blues", zmid=None):
    if df is None or df.empty:
        st.info(t("app.no_data"))
        return
    if not HAS_PLOTLY:
        show_df(df)
        return
    fig = px.imshow(df.values, x=[str(c) for c in df.columns],
                    y=[str(i) for i in df.index],
                    color_continuous_scale=colorscale,
                    color_continuous_midpoint=zmid, text_auto=True, aspect="auto")
    fig.update_layout(title=title, height=max(320, 46 * len(df.index) + 140),
                      margin=dict(l=10, r=10, t=60, b=10))
    st.plotly_chart(fig, **WIDE)


# =====================================================================
# 2. 逐字稿讀取與存取
# =====================================================================
def read_docx(file):
    doc = docx.Document(file)
    out = []
    for para in doc.paragraphs:
        if para.text.strip():
            out.append(para.text)
    for table in doc.tables:
        headers = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
        speaker_names = ["講者", "Speaker", "speaker", "發言人"]
        content_names = ["內容", "Content", "content", "逐字稿"]
        is_transcript = any(h in speaker_names + content_names for h in headers)
        if is_transcript:
            si = next((i for i, h in enumerate(headers) if h in speaker_names), None)
            ci = next((i for i, h in enumerate(headers) if h in content_names), None)
            for row in table.rows[1:]:
                cells = [c.text.strip() for c in row.cells]
                if ci is not None and ci < len(cells) and cells[ci]:
                    sp = cells[si] if si is not None and si < len(cells) else ""
                    out.append(f"【{sp}】{cells[ci]}" if sp else cells[ci])
        else:
            for row in table.rows:
                vals = [c.text.strip() for c in row.cells if c.text.strip()]
                if vals:
                    out.append(" | ".join(vals))
    return "\n".join(out)


def fix_newlines_in_strings(s):
    """修復模型輸出 JSON 字串中的 literal 換行。"""
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
    return "".join(out)


def save_record(rec):
    """
    寫回磁碟。**既有的 _meta 要合併，不能整份蓋掉。**

    要防的失效：這裡若直接把 _meta 賦成新的兩個鍵，每存一次檔，
    _meta 裡其他東西就消失一次：研究者在「編碼複核」頁籤改了一個碼，
    按下儲存，那份紀錄「是哪個模型、哪個端點跑出來的」就永久不見了
    ——而複核正是最需要留下軌跡的動作。

    第二個坑：payload 會濾掉所有底線開頭的鍵，所以掛在 rec["_source"] 上
    的端點描述根本沒被寫進檔案過。provenance 一律走 _meta，因為 _meta
    是唯一會被寫出去、也會被讀回來的那一個。
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = re.sub(r'[\\/:*?"<>|]', "_", str(rec.get(S.RESPONDENT, "unknown")))[:40]
    fn = rec.get("_file") or f"{safe}_{ts}.json"
    payload = {k: v for k, v in rec.items() if not k.startswith("_")}
    meta = dict(rec.get(S.META) or {})          # 保留讀進來時就有的欄位
    meta["schema_version"] = S.SCHEMA_VERSION
    meta.setdefault("framework_id", F.active().id)
    meta["last_saved"] = datetime.now().isoformat(timespec="seconds")

    # 第三個坑（#36）：隨軟體附的參考編碼同時是「示範資料」與「論文 Table 6
    # 的資料來源」。從 analyses/ 載入 demo 紀錄後在複核頁籤改一個碼並儲存，
    # 若直接覆寫原檔，參考標準就悄悄變了：只改一個碼，卡方就從
    # 10.04/.018 變成 10.454/.0151，任何引用這批語料的數字都對不上。
    # 參考編碼一律唯讀：修改另存新檔，並在 _meta 記下它是從哪一份分出來的。
    if rec.get("_reference"):
        orig = fn
        stem = re.sub(r"\.json$", "", orig)
        fn = f"{stem}_reviewed_{ts}.json"
        meta["derived_from"] = orig
        meta["reference_source"] = meta.get("source")
        meta["source"] = f"reviewed-copy/{orig}"
        rec["_reference"] = False
        try:
            st.session_state["_fork_note"] = (orig, fn)
            st.session_state.pop("_saved_index", None)   # 新檔要出現在清單裡
        except Exception:                                # noqa: BLE001 — bare mode
            pass
    payload[S.META] = meta
    with open(os.path.join(SAVE_DIR, fn), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    # 記憶體內的紀錄也要拿到更新後的 _meta：否則分出新檔之後再存一次，
    # 舊的 source 會把 derived_from 蓋掉，新檔下次載入又被當成參考編碼。
    rec[S.META] = meta
    rec["_file"] = fn
    return fn


def load_records_from_dir(path, tag):
    """
    讀取並自動遷移。任何版本的舊檔都會被轉成目前的 schema。

    每一筆都會附上兩個底線欄位供上層判斷：

      _fw_mismatch  (紀錄的框架, 目前的框架)；對得上或無從判斷時為 None
      _dropped      遷移過程中被丟棄的編碼，每筆附理由

    這兩項存在的理由：維度識別碼只在它自己的框架裡有意義。拿 UTAUT 開
    RI 編過的檔案，整份編碼會在載入當下被清空，畫面上跟「還沒編碼」
    長得一模一樣——接著隨手一存就永久覆蓋原檔。判斷所需的資訊本來就
    在 _meta.framework_id 裡，讀它就好。
    """
    out, migrated = [], 0
    if not os.path.isdir(path):
        return out, migrated
    for fn in sorted(os.listdir(path)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(path, fn), "r", encoding="utf-8") as f:
                raw = json.load(f)
            was_legacy = S.is_legacy(raw)
            dropped = []
            mismatch = S.framework_mismatch(raw)
            rec = S.migrate_record(raw, dropped=dropped)
            rec["_source"], rec["_file"] = tag, fn
            rec["_fw_mismatch"], rec["_dropped"] = mismatch, dropped
            # 隨軟體附的參考編碼：save_record 看到這個標記就另存新檔（#36）
            _m = rec.get(S.META) or {}
            rec["_reference"] = (str(_m.get("source") or "").startswith("demo/")
                                 and not _m.get("derived_from"))
            out.append(rec)
            migrated += 1 if was_legacy else 0
        except Exception as e:
            st.warning(f"{fn}: {e}")
    return out, migrated


def available_models(provider, api_key, base_url):
    """
    向所選供應者查詢目前可用的模型。

    寫死的模型清單一定會過期：Gemini 2.5 Flash 就在 2026 年被下架，
    舊使用者還能用、新使用者直接吃 404。地端服務更是每個人裝的模型
    都不一樣，根本無從寫死。所以正常路徑一律**跟服務要清單**，
    tacit_llm.FALLBACK_MODELS 只是查不到時的墊底。

    回傳 (清單, 提示文字)。結果快取在 session 裡，避免每次重繪都打一次
    ——地端服務查一次要幾百毫秒，Streamlit 一個 widget 動作就重跑整個腳本。
    """
    ck = (provider, api_key[-8:] if api_key else "", base_url)
    cache = st.session_state.get("_models_cache")
    if cache and cache.get("key") == ck:
        return cache["models"], cache["note"]
    names, note = LLM.list_models(provider, api_key, base_url)
    st.session_state._models_cache = {"key": ck, "models": names, "note": note}
    return names, note


def scan_saved():
    """
    掃描兩個存檔資料夾，列出可載入的分析，但**不**把它們放進工作區。

    載入是選擇性的：其他頁籤的每一項分析都以工作區內容為範圍，
    一次全部載入會讓交叉表與共現矩陣大到難以閱讀，也讓研究者無法
    針對特定幾位受訪者做比較。掃描結果快取在 session 裡，
    按「重新掃描」才會重讀磁碟。
    """
    cached = st.session_state.get("_saved_index")
    if cached is not None:
        return cached
    index = []
    for path, tag in ((SAVE_DIR, "pro"), (SAVE_DIR_LEGACY, "legacy")):
        recs, _ = load_records_from_dir(path, tag)
        for r in recs:
            fn = r.get("_file", "")
            index.append({
                "key": f"{tag}/{fn}",
                "tag": tag,
                "legacy": tag == "legacy",
                "respondent": str(r.get(S.RESPONDENT) or fn or "?"),
                "segments": len(r.get(S.SEGMENTS) or []),
                "fw_mismatch": r.get("_fw_mismatch"),
                "dropped": r.get("_dropped") or [],
                "record": r,
            })
    st.session_state._saved_index = index
    return index


def available_transcripts(recs):
    """
    目前拿得到的逐字稿：{受訪者: 全文}。

    來源有兩個，優先序不能顛倒：
      1. **紀錄裡本來就存著的**——分析當下一併保存的原文。這一份才是 AI
         實際據以編碼的文本，引文比對與單元切分都必須以它為準。
      2. 使用者補上傳的——只用來填補第一項的缺口。v1 舊檔沒有保存逐字稿，
         那些紀錄只能靠補上傳。

    若讓上傳的覆蓋內含的，使用者上傳到不同版本（改過錯字、換過段落）時，
    引文會比對不到，信度抽樣框會莫名其妙少掉一堆單元，而且很難查。
    """
    uploaded = dict(st.session_state.get("transcripts") or {})
    out = {}
    for r in recs or []:
        who = r.get(S.RESPONDENT)
        if not who:
            continue
        if r.get(S.TRANSCRIPT):
            out[who] = r[S.TRANSCRIPT]
        elif uploaded.get(who):
            out[who] = uploaded[who]
    for who, tr in uploaded.items():   # 不在工作區裡的也留著，不主動丟棄
        out.setdefault(who, tr)
    return out


def missing_transcripts(recs):
    """哪些受訪者還缺逐字稿——只有這些才需要請使用者補上傳。"""
    have = available_transcripts(recs)
    return [r.get(S.RESPONDENT) for r in (recs or [])
            if r.get(S.RESPONDENT) and not have.get(r.get(S.RESPONDENT))]


def analysed_transcript_files():
    """
    已經分析過的逐字稿檔名集合。

    同時看工作區與磁碟：即使中途關掉程式重開，工作區是空的，
    磁碟上的存檔仍然算數——那些是已經付過 API 費用的成果。
    """
    done = set()
    for r in st.session_state.get("records", []):
        if r.get(S.TRANSCRIPT_FILE):
            done.add(r[S.TRANSCRIPT_FILE])
    for x in scan_saved():
        v = x["record"].get(S.TRANSCRIPT_FILE)
        if v:
            done.add(v)
    return done


# =====================================================================
# 3. 由框架動態生成系統提示詞
# =====================================================================
def build_system_prompt(fw, analysis_lang, sample=""):
    """
    提示詞完全由作用中框架推導——換框架就換提示詞，不必改程式。
    指令用英文（模型遵循度較好），輸出語言另由 analysis_lang 指定。

    【sample 是必要的，不是選配】
    設為「跟著逐字稿」時，必須把**該份逐字稿的內容**交給語言解析，
    才知道要指定哪一種語言。這支函式若在讀檔之前只被呼叫一次、
    整批共用，模型只拿到「跟著逐字稿走」這種相對指示，於是自己挑一種
    ——四份全英文的訪談稿會因此跑出中文主題。"""
    # 語料語彙由框架提供，預設是訪談。維度、屬性、語料種類三者都跟著
    # 框架走，提示詞裡才不會殘留「去找自我介紹與年資」這種只對訪談
    # 成立的指示。
    DOC = fw.corpus_term("document", "en")
    # 冠詞跟著詞首的母音走："a interview transcript" 會讓整段提示詞
    # 看起來像沒校對過，而模型對提示詞品質是敏感的。
    A_DOC = ("an " if DOC[:1].lower() in "aeiou" else "a ") + DOC
    CASE = fw.corpus_term("case", "en")
    SRC = fw.corpus_term("descriptor_source", "en")
    lines = [
        "You are an expert qualitative researcher performing rigorous, "
        f"theory-driven thematic analysis of {A_DOC}.",
        "",
        f"THEORETICAL FRAMEWORK: {fw.name('en')}",
    ]
    if fw.citation:
        lines.append(f"Source: {fw.citation}")
    if fw.description("en"):
        lines.append(fw.description("en"))
    lines += ["", S.analysis_language_instruction(analysis_lang, sample), "",
              "=" * 68,
              "1. DIMENSIONS",
              "=" * 68]

    for d in fw.dimensions:
        lines.append("")
        lines.append(f"## {fw.label(d, 'en')}   [id: {d}]")
        if fw.definition(d, "en"):
            lines.append(fw.definition(d, "en"))
        if fw.has_polarity:
            for p in fw.polarity_values:
                lines.append(f"  polarity {p} = {fw.polarity_label(d, p, 'en')}")
                for x in fw.indicators(d, p, lang="en"):
                    lines.append(f"    - {x}")
        else:
            for x in fw.indicators(d, lang="en"):
                lines.append(f"    - {x}")
        # 排除條件必須跟指標放在一起。指標是正面例子，而正面例子界定不出
        # 邊界——邊界沒寫，模型就自己補。實測的後果是 engagement 吃掉了
        # 一半的編碼：「我們用 design thinking 想使用者要什麼」被當成參與
        # 的正向證據，而那正是這個概念當初要對抗的東西。
        excl = fw.exclusions(d, lang="en")
        if excl:
            lines.append("  DOES NOT INCLUDE — do not code these as "
                         f"{fw.label(d, 'en')}:")
            for x in excl:
                lines.append(f"    ✗ {x}")
        lit = fw.literature(d, role=F.ROLE_GROUNDING)
        if lit:
            lines.append("  grounded in: " +
                         "; ".join(x[F.LIT_CITATION] for x in lit[:4]))

    pol_note = ""
    if fw.has_polarity:
        pol_note = (f'\n      "{S.POLARITY}": "one of '
                    f'{"|".join(fw.polarity_values)}",')
    dim_list = "|".join(fw.dimensions)
    desc_fields = ",\n    ".join(
        f'"{k}": "one of {"|".join(v)}"' for k, v in S.DESCRIPTOR_FIELDS.items())

    lines += ["", "=" * 68,
              "2. SEGMENT-BASED MULTI-CODING RULES",
              "=" * 68,
              "1. Output a FLAT LIST of coded segments. Do not group by dimension.",
              "2. A segment is a contiguous verbatim excerpt expressing one "
              "coherent idea, typically 1-4 sentences.",
              # 要防的失效：這一條若只寫「Under-code rather than over-code」：
              # 本意是限制**單一段落**上的多重編碼，但模型會讀成全域指示，
              # 整份兩萬字的稿件只回四段。所以把適用範圍寫死在句子裡。
              "3. Assign MULTIPLE codes to THE SAME segment only when that one "
              "excerpt genuinely evidences more than one dimension. This rule "
              "limits co-occurrence within a segment; it is NOT a reason to "
              "return fewer segments.",
              # 窮舉是這個任務的重點，而模型的預設行為是「挑幾個代表性的」。
              # 沒有這一條，模型會回傳一份精選集而不是一份編碼。
              f"4. COVERAGE: work through the {DOC} from beginning to end and "
              "code EVERY passage that evidences a dimension. This is "
              "exhaustive coding, not a selection of highlights. A typical "
              "excerpt of this length yields many segments, not one per "
              "dimension. Do not stop early.",
              f"5. If a dimension is genuinely absent from the {DOC}, produce "
              "no segment for it. Never fabricate evidence. Absence must come "
              "from the text, not from stopping early.",
              # 實測撞到的失效：模型產生一個 REF-N，理由寫「未表現出對自身
              # 假設或知識邊界的反省，僅強調遵循既定流程」。沉默不是證據；
              # 那是憑空生出一筆資料。第 4 條要求窮舉，如果沒有這一條當
              # 對重，窮舉的壓力會直接變成捏造的壓力。
              # 這一條要區分兩件很容易混淆的事，所以寫得比別條長：
              # 受訪者說「我們沒有覆核機制」是實打實的負向證據；編碼者說
              # 「這段話沒有表現出反思」則是憑空生資料。兩者不分開的話，
              # 連示範語料裡 14 個紮實的負向編碼都會被誤殺。
              "6. ABSENCE IS NOT EVIDENCE — but be careful which absence. "
              "A negative polarity requires the passage to AFFIRMATIVELY "
              "express the negative stance. Two cases that look alike:",
              "   ✓ VALID: the speaker states that something is missing in "
              "their world — \"we have no review mechanism\", \"nobody asked "
              "the residents\", \"there is no trigger to stop\". They told you "
              "this; it is evidence, and it is often the strongest evidence "
              "for a negative code.",
              "   ✗ INVALID: YOU observe that the passage does not display "
              "the dimension — \"does not show reflection on assumptions\", "
              '"no evidence of engagement here", "未表現出對自身假設的反省". '
              "Silence in the text is not a finding. If that is the only "
              "thing you can say about a passage, leave the passage UNCODED "
              "and move on.",
              # 實測撞到的失效：標題被填成 "Reflexivity - N"、"Engagement"。
              # 標題的用途是給下游主題聚斂用的次主題標籤，填成維度名等於
              # 這一欄作廢，主題分析只會把四個維度再跑出來一次。
              f"7. TITLE: a substantive sub-theme label describing WHAT the "
              f"passage says, in the words of this {DOC}. Never use the "
              "dimension name, the code, or a polarity marker as the title. "
              '"Reflexivity", "Engagement - N", "Anticipation P" are all '
              "invalid titles.",
              f"8. Every quote and full_text must be copied VERBATIM from the "
              f"{DOC}. Never rewrite, summarise, translate or clean up the "
              "wording. quote must be a substring of full_text.",
              f"9. DESCRIPTORS: fill in only from information explicitly stated in "
              f"the {DOC} ({SRC}). If a field is not stated, output "
              f'"{S.UNSPECIFIED}". NEVER infer a descriptor from tone or topic.',
              "10. JSON: escape all quotes inside strings; never emit literal "
              "newline characters inside JSON string values.",
              "", "=" * 68,
              "3. OUTPUT FORMAT — valid JSON only, no text before or after:",
              "=" * 68,
              "{",
              f'  "{S.RESPONDENT}": "the {CASE}, as named in the {DOC}",',
              f'  "{S.DESCRIPTORS}": {{',
              f"    {desc_fields},",
              f'    "{S.DESCRIPTOR_BASIS}": "which sentence you based these on; '
              f'if none, say the {DOC} does not state it"',
              "  },",
              # 範例裡刻意放**多個**段落物件並加上「...」與 as many as 的
              # 註記。只寫一個物件的話，模型就照抄一個物件的形狀：實測回來
              # 的是「四個維度各一段」，那不是分析結果，是照著範例填空。
              f'  "{S.SEGMENTS}": [',
              "    {",
              f'      "{S.TITLE}": "a concise sub-theme label",',
              f'      "{S.QUOTE}": "the most representative 1-2 sentences, verbatim",',
              f'      "{S.FULL_TEXT}": "the fuller passage giving context, verbatim",',
              f'      "{S.CODES_F}": [',
              "        {",
              f'          "{S.DIMENSION}": "one of {dim_list}",{pol_note}',
              f'          "{S.RATIONALE}": "under 20 words: why this code applies"',
              "        }",
              "      ]",
              "    },",
              "    { second coded segment, same shape },",
              "    { third coded segment, same shape }",
              "  ],",
              f'  "{S.SUMMARY}": "150-200 words of analytic commentary: which '
              f"dimensions this {CASE} most strongly exhibits, which are weak "
              "or absent, and what any multi-coded segments reveal about the "
              'structure of the account."',
              "}",
              "",
              # 範例只能寫有限個物件，而模型會把範例的長度當成目標長度。
              # 這一句把「範例三個」與「實際要幾個」明確分開。
              f"The three segment objects above show the SHAPE only. Return as "
              f"many segment objects as the {DOC} actually warrants — commonly "
              "far more than three. The list ends when you reach the end of the "
              f"{DOC}, not when you have covered each dimension once."]
    return "\n".join(lines)


# =====================================================================
# 4. 主程式：狀態與側欄
# =====================================================================
st.set_page_config(page_title="TACIT", layout="wide")

if "records" not in st.session_state:
    st.session_state.records = []
if "ui_lang" not in st.session_state:
    st.session_state.ui_lang = I.DEFAULT_LANG
if "analysis_lang" not in st.session_state:
    st.session_state.analysis_lang = S.DEFAULT_ANALYSIS_LANG
if "framework_id" not in st.session_state:
    st.session_state.framework_id = F.DEFAULT_FRAMEWORK_ID

# 正規化要在 set_lang 之前、而且要寫回 session_state：側邊欄的選單之後會拿
# 這個值去 .index()，模組層的語言與 session_state 的值必須是同一個。只改其中
# 一邊，會得到「介面是中文但選單顯示 English」這種更難查的狀態。
st.session_state.ui_lang = I.normalize_lang(st.session_state.ui_lang)
I.set_lang(st.session_state.ui_lang)
F.ensure_builtin_on_disk()
try:
    F.activate_by_id(st.session_state.framework_id)
except F.FrameworkError:
    F.reset()
    st.session_state.framework_id = F.DEFAULT_FRAMEWORK_ID

FW = F.active()

# 編碼模式。選單在側邊欄（框架選單的上面），但標題這一行比側邊欄先畫，
# 所以這裡先從 session_state 讀；widget 的值在指令稿重跑之前就已經更新了。
MODE_FRAMEWORK, MODE_OPEN = "framework", "open"
# 碼簿定案成框架之後要切回框架模式，但 widget 建立之後不能再改它的值，
# 所以定案當下只留一個記號，下一輪在 widget 建立之前套用。
if "_pending_mode" in st.session_state:
    st.session_state.coding_mode = st.session_state.pop("_pending_mode")
if st.session_state.get("coding_mode") not in (MODE_FRAMEWORK, MODE_OPEN):
    st.session_state.coding_mode = MODE_FRAMEWORK
IS_OPEN = st.session_state.coding_mode == MODE_OPEN

st.title(t("app.title"))
if IS_OPEN:
    # 開放編碼時不套用任何框架。這裡若照樣印著「Responsible Innovation ·
    # Stilgoe et al. (2013)」，任何人看了都會以為自己正在用那個框架編碼。
    st.caption(t("app.header_open"))
else:
    st.caption(f"{FW.name()} · {FW.citation}" if FW.citation else FW.name())

with st.sidebar:
    st.header(t("app.settings"))

    # --- 語言：介面與分析輸出是兩件獨立的事 ---
    #
    # 這兩個選單不能直接對 session_state 的值做 .index()：那個值是可以
    # 從舊的存檔、舊版本的狀態、或別的地方帶進來的。帶進來一個不在清單裡
    # 的代碼（例如把分析語言的 "zh-Hant" 放進介面語言），ValueError 會在
    # 側邊欄第一個元件就炸掉，整個 app 起不來、畫面全白，而錯誤訊息只說
    # 「'zh-Hant' is not in list」，看不出是哪個選單。框架選單早就先驗證
    # 才 .index()，這兩個是漏掉的。
    #
    # 介面語言在上面 I.normalize_lang 已經正規化過（要在 set_lang 之前做，
    # 不然介面會變英文）；這裡只剩分析語言那一份清單。
    def _lang_fallback(value, options):
        if value in options:
            return value
        head = str(value or "").split("-")[0].lower()
        for o in options:
            if o.lower() == head or o.lower().split("-")[0] == head:
                return o
        return options[0]

    lang = st.selectbox(t("side.ui_lang"), I.LANGS,
                        index=I.LANGS.index(st.session_state.ui_lang),
                        format_func=lambda c: I.LANG_NAMES[c], key="sel_ui_lang")
    if lang != st.session_state.ui_lang:
        st.session_state.ui_lang = lang
        st.rerun()

    alangs = list(S.ANALYSIS_LANGS)
    st.session_state.analysis_lang = _lang_fallback(
        st.session_state.analysis_lang, alangs)
    st.session_state.analysis_lang = st.selectbox(
        t("side.analysis_lang"), alangs,
        index=alangs.index(st.session_state.analysis_lang),
        format_func=lambda c: S.ANALYSIS_LANGS[c],
        help=t("side.analysis_lang_help"), key="sel_analysis_lang")

    st.divider()

    # --- 編碼模式 ---
    # 這個選單若放在「執行新分析」頁籤裡，側邊欄仍然顯示著框架與它的
    # 碼數。選了開放編碼的人一眼望去看到的仍然是一個框架，分不清現在到底是
    # 哪一種。模式決定「碼從哪裡來」，它管的範圍比框架大，所以放在框架上面。
    st.radio(
        t("run.mode"), [MODE_FRAMEWORK, MODE_OPEN],
        format_func=lambda v: (t("run.mode_framework") if v == MODE_FRAMEWORK
                               else t("run.mode_open")),
        help=t("side.mode_help"), key="coding_mode")

    # --- 框架 ---
    avail = F.list_available()
    ids = [a[0] for a in avail] or [F.DEFAULT_FRAMEWORK_ID]
    names = {a[0]: a[1] for a in avail}
    cur = st.session_state.framework_id if st.session_state.framework_id in ids else ids[0]
    # `names` 用預設引數綁進來，不要用閉包。app.py 是一支從頭跑到尾的指令稿，
    # 底下還有好幾個地方會把 `names` 指到別的東西；顯示函式事後被呼叫時查的是
    # 「當下」的值，於是框架選單會顯示成識別碼，甚至直接 AttributeError。
    if IS_OPEN:
        # 不畫框架選單。留著它等於在畫面上同時擺兩個互相矛盾的訊息。
        _cbk = st.session_state.get("codebook")
        _ncb = len(_cbk[OP.CODES]) if _cbk else 0
        st.caption(t("side.open_active", n=_ncb))
    else:
        chosen = st.selectbox(
            t("side.framework"), ids, index=ids.index(cur),
            format_func=lambda i, _n=names: (_n.get(i, i) +
                                             (f" {t('side.framework_builtin')}"
                                              if i == F.DEFAULT_FRAMEWORK_ID else "")),
            help=t("side.framework_help"), key="sel_framework")
        if chosen != st.session_state.framework_id:
            st.session_state.framework_id = chosen
            st.rerun()

        st.caption(f"{len(FW.dimensions)} × "
                   f"{len(FW.polarity_values) if FW.has_polarity else 1} = "
                   f"{len(FW.codes)} {t('common.codes').lower()}")
        if not FW.has_polarity:
            st.info(t("side.no_polarity_note"))

    st.divider()

    # -----------------------------------------------------------------
    # 語言模型供應者
    #
    # 供應者選在最上面而不是模型選單旁邊，是因為它會改變下面每一個欄位
    # 的意義：雲端要金鑰不要位址，地端要位址不要金鑰。先問供應者，
    # 才不會同時攤開兩組互相矛盾的欄位。
    # -----------------------------------------------------------------
    _env_ep = LLM.from_env()
    _prov_default = _env_ep.provider if _env_ep else LLM.GEMINI

    def _provider_label(p):
        return t(f"llm.provider.{p}")

    def _provider_from_state(raw):
        """
        把 session_state 裡的值正規化成合法的供應者識別碼。

        要防的失效：Streamlit 1.63.0 在真實瀏覽器裡把**顯示標籤**
        （"Google Gemini (cloud)"）存進了這個 widget 的 session_state，
        接著 `LLM.PROVIDERS.index(...)` 直接 ValueError，整個 app 起不來。
        AppTest 重現不出來——它繞過前端——所以測試全綠而使用者一開就炸。

        側欄其他選單本來就不會這樣寫：語言選單的 widget key 跟狀態 key 分開，
        框架選單先驗證 `cur in ids` 才 `.index()`。只有這一個是拿使用者控制的
        狀態值直接去 `.index()`，那是定時炸彈，跟 Streamlit 哪一版無關。

        接受三種輸入：識別碼、任何介面語言下的顯示標籤、以及垃圾。
        垃圾一律退回預設值，絕不拋錯——側欄壞掉等於整個工具壞掉。
        """
        if raw in LLM.PROVIDERS:
            return raw
        if isinstance(raw, str):
            for p in LLM.PROVIDERS:
                for lang in I.LANGS:
                    if raw.strip() == I.t(f"llm.provider.{p}", lang).strip():
                        return p
        return _prov_default

    _prov_cur = _provider_from_state(st.session_state.get("llm_provider"))
    provider = st.selectbox(
        t("llm.provider"), LLM.PROVIDERS,
        index=LLM.PROVIDERS.index(_prov_cur),
        format_func=_provider_label,
        help=t("llm.provider_help"), key="llm_provider")
    # 不論 widget 回傳什麼，往下走的一律是識別碼
    provider = _provider_from_state(provider)

    if provider == LLM.GEMINI:
        api_key = st.text_input(t("app.api_key"), type="password",
                                value=(_env_ep.api_key if _env_ep else ""))
        st.caption(t("app.api_hint"))
        base_url = ""
    else:
        base_url = st.text_input(
            t("llm.base_url"),
            value=st.session_state.get("llm_base_url")
                  or (_env_ep.base_url if _env_ep else LLM.DEFAULT_BASE_URL[provider]),
            help=t("llm.base_url_help"), key="llm_base_url")
        # 非本機位址（雲端的 OpenAI 相容服務）才問金鑰。指向 localhost
        # 還跟使用者要金鑰，只會讓人以為自己漏設了什麼。
        if LLM._is_loopback(base_url):
            api_key = ""
            st.success(t("llm.local_privacy"))
        else:
            api_key = st.text_input(t("llm.remote_key"), type="password")
            st.warning(t("llm.remote_warning"))

    # Gemini 選了卻沒裝 SDK：模型清單查不到，欄位退化成手打。
    # 只在欄位**下方**放一行小字說明的話，使用者看到的是「居然要自己打模型
    # 名稱」，不會把它跟一個沒裝的套件連起來。缺套件是可以行動的事，
    # 提示就該放在撞到它的地方、講清楚要做什麼。
    # 只印一行 `pip install google-genai` 是不夠的：它
    # 叫使用者自己去裝。**但這個程式是雙擊啟動器打開的，畫面上沒有任何
    # 地方可以打指令。** 對一個不寫程式的研究者來說，那行字等於死路。
    #
    # 不把 SDK 放進必裝清單的理由仍然成立（只用地端模型的人不該被迫裝
    # 雲端 SDK，那群人正是倫理限制最嚴的一群），所以解法不是改成必裝，
    # 而是**把安裝這個動作搬進介面**：按一個鈕，裝在同一個虛擬環境裡。
    if provider == LLM.GEMINI and not LLM.HAS_GEMINI:
        st.warning(t("llm.gemini_sdk_missing"))
        if st.session_state.get("_gemini_install_done"):
            st.info(t("llm.gemini_sdk_restart"))
        elif st.button(t("llm.gemini_sdk_install"), key="btn_gemini_sdk"):
            with st.spinner(t("llm.gemini_sdk_installing")):
                okay, log = LLM.install_gemini_sdk()
            st.session_state["_gemini_install_done"] = okay
            if okay:
                st.success(t("llm.gemini_sdk_restart"))
            else:
                # 失敗時才顯示指令——到了這一步，使用者已經需要找人幫忙，
                # 給得出可以貼給對方的東西比藏起來有用。
                st.error(t("llm.gemini_sdk_failed"))
                st.code(f"{sys.executable} -m pip install google-genai",
                        language="bash")
                with st.expander(t("llm.gemini_sdk_log")):
                    st.code(log[-3000:] or "(no output)")

    models, model_note = available_models(provider, api_key, base_url)
    if models:
        _prev = st.session_state.get("_llm_model")
        _idx = models.index(_prev) if _prev in models else 0
        model_name = st.selectbox(t("app.model"), models, index=_idx,
                                  key="_llm_model")
    else:
        model_name = st.text_input(t("app.model"),
                                   value=st.session_state.get("_llm_model", ""),
                                   key="_llm_model",
                                   placeholder=t("llm.model_placeholder"))
    if model_note:
        st.caption(model_note)

    num_ctx = LLM.DEFAULT_NUM_CTX
    if provider in LLM.LOCAL_PROVIDERS:
        # context window 給使用者調，且預設值遠高於伺服器的預設值。
        # Ollama 出廠是 4096——一份逐字稿放不下，超出的部分會被無聲
        # 截斷，而模型照樣回傳格式完整的 JSON。這是地端最危險的失效
        # 模式：結果看起來正常，實際上有一半資料從沒被讀過。
        num_ctx = st.number_input(t("llm.num_ctx"), 2048, 1048576,
                                  int(st.session_state.get("llm_num_ctx",
                                                           LLM.DEFAULT_NUM_CTX)),
                                  2048, help=t("llm.num_ctx_help"),
                                  key="llm_num_ctx")
        # 視窗預算要看得見。使用者調了 num_ctx 卻不知道有多少真的落到
        # 逐字稿上，就只能靠撞牆時的錯誤訊息去反推——而那個訊息出現的
        # 時候，他已經選好模型、上傳好檔案、按下開始了。
        _res = LLM.default_max_tokens(provider, int(num_ctx))
        _room = int(num_ctx) - _res
        st.caption(t("llm.budget", ctx=f"{int(num_ctx):,}", out=f"{_res:,}",
                     room=f"{_room:,}", chars=f"{int(_room * 3.5):,}"))
        if st.button(t("llm.test"), **WIDE):
            ok, note = LLM.probe(LLM.Endpoint(provider, model_name, api_key,
                                              base_url, num_ctx=int(num_ctx)))
            (st.success if ok else st.error)(note or ("OK" if ok else "-"))

    def endpoint(model=None, max_tokens=None):
        """目前側欄設定所描述的端點。model 可覆寫（主題歸納會挑別的）。"""
        return LLM.Endpoint(provider=provider, model=model or model_name,
                            api_key=api_key, base_url=base_url,
                            num_ctx=int(num_ctx), max_tokens=max_tokens)

    # OpenAlex 金鑰放在這裡而不是框架建構頁籤裡：兩把金鑰都是憑證，
    # 集中在同一處，使用者只需要記住「金鑰都貼在側欄」這一件事。
    st.text_input(t("fw.api_key"), type="password", key="oa_key",
                  value=os.environ.get("OPENALEX_API_KEY", ""),
                  help=t("fw.api_key_help"))
    if os.environ.get("OPENALEX_API_KEY"):
        st.caption(t("fw.key_from_env"))
    else:
        st.caption(t("fw.key_persist_hint"))

    st.divider()
    st.subheader(t("app.load_data"))
    st.caption(t("app.pick_hint"))

    _fork = st.session_state.pop("_fork_note", None)
    if _fork:
        st.info(t("app.reference_forked", orig=_fork[0], new=_fork[1]))
    index = scan_saved()
    if not index:
        st.caption(t("app.no_saved"))
    else:
        pro_names = {x["respondent"] for x in index if x["tag"] == "pro"}
        keys = [x["key"] for x in index]
        # 同一位受訪者常有多份存檔（重跑、換模型、分次訪談），光看姓名會出現
        # 兩三列一模一樣、無法分辨的選項。撞名時補上檔名——鍵值本來就以
        # 檔名為準，只是標籤要讓人看得出差別。
        name_counts = Counter(x["respondent"] for x in index)
        labels = {}
        for x in index:
            bits = [f"{x['respondent']} ({x['segments']})"]
            if name_counts[x["respondent"]] > 1:
                bits.append(os.path.splitext(x["key"].split("/", 1)[-1])[0])
            if x["tag"] == "legacy":
                bits.append(t("app.legacy_mark"))
                if x["respondent"] in pro_names:
                    bits.append(t("app.dup_mark"))
            if x["fw_mismatch"]:
                bits.append(t("app.fw_mark", fw=x["fw_mismatch"][0]))
            labels[x["key"]] = " · ".join(bits)

        # 框架對不上的先講清楚，而且不要預選。載入它們等於把編碼清空。
        blocked = [x for x in index if x["fw_mismatch"]]
        if blocked:
            st.error(t("app.fw_mismatch_list",
                       n=len(blocked), active=F.active().id,
                       others=", ".join(sorted({x["fw_mismatch"][0]
                                                for x in blocked}))))

        # 舊格式且已有新版者，預設不勾——但仍列出來，讓使用者自己決定。
        fresh = [x["key"] for x in index
                 if not x["fw_mismatch"]
                 and not (x["tag"] == "legacy" and x["respondent"] in pro_names)]
        if "sel_records" not in st.session_state:
            st.session_state.sel_records = fresh

        b1, b2, b3 = st.columns(3)
        if b1.button(t("app.select_all"), **WIDE):
            st.session_state.sel_records = keys
            st.rerun()
        if b2.button(t("app.select_none"), **WIDE):
            st.session_state.sel_records = []
            st.rerun()
        if b3.button(t("app.refresh_list"), **WIDE):
            st.session_state.pop("_saved_index", None)
            st.rerun()

        sel = st.multiselect(t("app.pick_records"), keys,
                             format_func=lambda k: labels.get(k, k),
                             key="sel_records")

        if st.button(t("app.load_selected"), type="primary", **WIDE):
            by_key = {x["key"]: x for x in index}
            bad = [k for k in sel if by_key.get(k, {}).get("fw_mismatch")]
            if not sel:
                st.warning(t("app.nothing_selected"))
            elif bad:
                # 硬擋。照樣載入的話，編碼早在遷移時就被清空了——
                # 使用者看到的是一份「沒有編碼」的紀錄，存檔即永久覆蓋。
                x = by_key[bad[0]]
                st.error(t("app.fw_blocked", n=len(bad),
                           theirs=x["fw_mismatch"][0],
                           active=x["fw_mismatch"][1]))
            else:
                # 深拷貝：複核與屬性編輯會改動紀錄，不可回頭汙染掃描快取。
                st.session_state.records = [
                    copy.deepcopy(by_key[k]["record"]) for k in sel if k in by_key]
                if any(by_key[k]["legacy"] for k in sel if k in by_key):
                    st.info(t("app.migrated"))
                lost = [d for k in sel for d in (by_key[k].get("dropped") or [])]
                if lost:
                    st.warning(t("app.codes_dropped", n=len(lost)))
                    show_df(pd.DataFrame(lost), hide_index=True)
                st.success(t("app.loaded_n", n=len(st.session_state.records),
                             total=len(index)))

    if st.button(t("app.clear"), **WIDE):
        st.session_state.records = []

    st.divider()
    st.metric(t("app.respondents_loaded"), len(st.session_state.records))
    if not HAS_PLOTLY:
        st.warning(t("side.plotly_missing"))
    if not A.HAS_SCIPY:
        st.info(t("side.scipy_missing"))


TAB_KEYS = ["tab.run", "tab.codebook", "tab.data", "tab.review", "tab.cross",
            "tab.themes", "tab.lexicon", "tab.irr", "tab.export", "tab.framework"]
(tab_run, tab_codebook, tab_data, tab_review, tab_cross, tab_themes, tab_lex,
 tab_irr, tab_export, tab_fw) = st.tabs([t(k) for k in TAB_KEYS])

# 開放編碼的碼簿放在 session_state，跟 records 同層級。它會跨多份逐字稿
# 累積——那正是「碼簿」與「一堆標題」的分界線，所以不能每份重建一次。
if "codebook" not in st.session_state:
    st.session_state.codebook = None
if "open_records" not in st.session_state:
    st.session_state.open_records = []


# =====================================================================
# 5. 執行新分析
# =====================================================================
with tab_run:
    # -----------------------------------------------------------------
    # 兩種編碼模式
    #
    # 這兩種不是難易之分，是主題分析裡兩條不同的路：
    #   框架驅動 = 先有碼簿再編碼（碼簿型 TA、編碼信度型 TA）
    #   開放編碼 = 碼簿從資料長出來（開放編碼／紮根理論的前半）
    # 兩條路最後在同一個地方會合：開放編碼產生的碼簿可以存成框架，
    # 接著就能拿它重新編碼、算信度、做共現——也就是走回第一條路。
    # -----------------------------------------------------------------
    # 模式在側邊欄選（框架選單的上面）。這裡只說明目前是哪一種。
    mode = st.session_state.coding_mode
    st.markdown(f"**{t('run.mode')}: "
                f"{t('run.mode_framework') if mode == MODE_FRAMEWORK else t('run.mode_open')}**")
    st.caption(t("run.mode_framework_help") if mode == MODE_FRAMEWORK
               else t("run.mode_open_help"))

    st.caption(t("run.transcript_hint"))
    files = st.file_uploader(t("run.upload"), type=["docx"],
                             accept_multiple_files=True)
    delay = st.slider(t("run.delay"), 0, 30, 10, help=t("run.delay_help"))

    if mode == MODE_FRAMEWORK:
        with st.expander(f"{t('side.framework')}: {FW.name()}"):
            for d in FW.dimensions:
                st.markdown(f"**{I.dim(d)}** (`{FW.dim_short[d]}`)")
                if FW.definition(d, I.get_lang()):
                    st.caption(FW.definition(d, I.get_lang()))
            if FW.has_polarity and FW.polarity_citation:
                st.caption(FW.polarity_citation)
    else:
        _cb = st.session_state.codebook
        _n = len(_cb[OP.CODES]) if _cb else 0
        with st.expander(t("run.open_codebook_state", n=_n), expanded=not _cb):
            if not _cb:
                st.caption(t("run.open_codebook_empty"))
            else:
                st.caption(t("run.open_codebook_continues",
                             n=_n, cb=_cb[OP.CODEBOOK_ID]))
            # 從零開始是一個需要明講的決定：碼簿一清掉，之前幾份逐字稿
            # 建立的碼就不再被沿用，後面編出來的碼會跟前面對不上。
            if _cb and st.button(t("run.open_codebook_reset"), key="btn_cb_reset"):
                st.session_state.codebook = None
                st.session_state.open_records = []
                st.rerun()

    # 已分析過的逐字稿，預設跳過。
    # API 配額中途用盡是常態，換一把金鑰再按一次「開始分析」時，
    # 不應該把前面已經跑完、已經付過錢的檔案重跑一遍。
    already = analysed_transcript_files()
    if files:
        pending = [f for f in files if f.name not in already]
        skipping = [f for f in files if f.name in already]
        if skipping:
            st.info(t("run.will_skip", n=len(skipping), m=len(pending)))
            with st.expander(t("run.skip_list", n=len(skipping))):
                for f in skipping:
                    st.caption(f"• {f.name}")
    redo = st.checkbox(t("run.redo"), value=False, help=t("run.redo_help"))

    # -----------------------------------------------------------------
    # 分段編碼
    #
    # 要防的失效：一份 46,730 字元的訪談稿整份送進去，回來 4 個段落——
    # 四個維度剛好各一個。同一批人工編碼的稿件（21,569 字元）標出 30 段。
    # 要求模型一次窮舉一份兩萬字文件裡的所有證據，召回率會塌；這不是
    # 換一顆模型能解決的，是任務形狀的問題。切成窗口之後每次只要求它
    # 掃過三千字，模型做得到。
    #
    # 做成可關的選項而不是寫死：短文件切了只是徒增合併誤差，而且窗口
    # 大小會改變結果，必須是使用者知道且記錄得下來的一個實驗參數。
    # -----------------------------------------------------------------
    with st.expander(t("run.chunk_title"), expanded=False):
        st.caption(t("run.chunk_help"))
        use_chunks = st.checkbox(t("run.chunk_on"), value=True,
                                 key="chk_chunk", help=t("run.chunk_on_help"))
        win = st.slider(t("run.chunk_window"), 1000, 8000,
                        CH.DEFAULT_WINDOW_CHARS, step=500, key="sl_window",
                        help=t("run.chunk_window_help"),
                        disabled=not use_chunks)
        ov = st.slider(t("run.chunk_overlap"), 0, 1000,
                       CH.DEFAULT_OVERLAP_CHARS, step=100, key="sl_overlap",
                       help=t("run.chunk_overlap_help"), disabled=not use_chunks)
        if files:
            _n = [len(CH.split_transcript(read_docx(f), win, ov))
                  for f in files] if use_chunks else [1] * len(files)
            st.caption(t("run.chunk_est", calls=sum(_n), files=len(files)))

    # -----------------------------------------------------------------
    # 批次前的單筆試跑
    #
    # 為什麼要有這一步：整批送出去之後才發現提示詞或模型不對，代價是
    # 整輪的時間（地端 8B 模型跑二十幾份逐字稿是數十分鐘起跳），雲端則
    # 是真的花掉的錢。更要緊的是，研究者在看到模型**實際**怎麼切段、
    # 怎麼寫理由之前，沒有辦法判斷這個框架與這個模型合不合用。
    #
    # 這一步刻意不寫進任何紀錄：它是校準，不是資料。傳統內容分析裡
    # 對應的是編碼員訓練——先在少量材料上對齊理解，再開始正式編碼。
    # -----------------------------------------------------------------
    with st.expander(t("run.dry_title"), expanded=False):
        st.caption(t("run.dry_help"))
        sample = st.text_area(t("run.dry_input"), height=160, key="dry_text",
                              placeholder=t("run.dry_placeholder"))
        c_dry, c_note = st.columns([1, 3])
        if c_dry.button(t("run.dry_go"), key="btn_dry"):
            if not model_name:
                st.error(t("run.need_model"))
            elif provider == LLM.GEMINI and not api_key:
                st.error(t("run.need_key"))
            elif not (sample or "").strip():
                st.warning(t("run.dry_need_text"))
            else:
                ep_dry = endpoint()
                try:
                    # 試跑要用**當前模式的**提示詞。拿框架驅動的提示詞去校準
                    # 開放編碼，校準的是另一件事——那比不校準更糟，因為它會
                    # 給人「已經檢查過了」的錯覺。
                    if mode == MODE_OPEN:
                        # 用一份丟棄式的碼簿：試跑不該污染正在累積的那一份，
                        # 它是校準不是資料（跟框架模式的理由完全相同）。
                        _cb_dry = OP.new_codebook(st.session_state.analysis_lang)
                        sys_dry = OP.build_open_prompt(
                            _cb_dry, st.session_state.analysis_lang, sample,
                            corpus_term=FW.corpus_term("document", "en"))
                    else:
                        sys_dry = build_system_prompt(
                            FW, st.session_state.analysis_lang, sample)
                    with st.spinner(t("run.dry_running")):
                        raw = LLM.complete(
                            ep_dry, f"Transcript:\n{sample}",
                            system=sys_dry, temperature=0.2, json_mode=True)
                    js = LLM._extract_first_json(raw)
                    if not js:
                        raise ValueError(t("run.no_json"))
                    parsed = LLM.loads_lenient(fix_newlines_in_strings(js))
                    if mode == MODE_OPEN:
                        _segs, _ = OP.absorb(_cb_dry, parsed)
                        segs = [{S.TITLE: s.get(S.TITLE), S.QUOTE: s.get(S.QUOTE),
                                 "_labels": [c[OP.CODE_LABEL]
                                             for c in s[OP.OPEN_CODES]],
                                 "_why": [c.get(S.RATIONALE, "")
                                          for c in s[OP.OPEN_CODES]]}
                                for s in _segs]
                    else:
                        rec_dry = S.migrate_record(parsed)
                        segs = [{S.TITLE: s.get(S.TITLE), S.QUOTE: s.get(S.QUOTE),
                                 "_labels": [I.code_label(c)
                                             for c in S.codes_of(s)],
                                 "_why": [c.get(S.RATIONALE, "")
                                          for c in (s.get(S.CODES_F) or [])]}
                                for s in (rec_dry.get(S.SEGMENTS) or [])]
                    st.session_state.dry_result = {
                        "endpoint": ep_dry.describe(),
                        "segments": segs,
                        "raw": raw,
                    }
                except LLM.ContextOverflow as e:
                    st.session_state.dry_result = {"error": str(e)}
                except Exception as e:
                    st.session_state.dry_result = {"error": f"{type(e).__name__}: {e}"}

        res = st.session_state.get("dry_result")
        if res:
            if res.get("error"):
                st.error(res["error"])
            else:
                segs = res["segments"]
                st.caption(f"`{res['endpoint']}`")
                if not segs:
                    # 空結果不是「這段話沒有內容」，是一個要判斷的訊號。
                    st.warning(t("run.dry_empty"))
                else:
                    st.success(t("run.dry_n", n=len(segs)))
                    # 兩種模式的段落在這裡已經被正規化成同一個形狀
                    # （標題／引文／標籤／理由），所以渲染只有一份。
                    for s in segs:
                        labels = s.get("_labels") or []
                        st.markdown(f"**{s.get(S.TITLE) or '—'}** — "
                                    + (" / ".join(labels) if labels
                                       else t("run.dry_nocode")))
                        if s.get(S.QUOTE):
                            st.caption(f"「{s[S.QUOTE]}」")
                        for why in s.get("_why") or []:
                            if why:
                                st.caption(f"· {why}")
                with st.expander(t("run.dry_raw")):
                    st.code(res["raw"][:4000], language="json")
            c_note.caption(t("run.dry_not_saved"))

    # 框架驅動的批次。開放編碼走下面另一段——兩條路的產出格式不同
    # （一邊是 (維度, 極性)，一邊是還沒有框架的自由碼），硬塞進同一個
    # 迴圈只會讓兩邊都長出一堆 if。
    if mode == MODE_FRAMEWORK and st.button(t("run.start"), type="primary",
                                            key="btn_run"):
        todo = list(files or []) if redo else [f for f in (files or [])
                                               if f.name not in already]
        if not model_name:
            st.error(t("run.need_model"))
        elif provider == LLM.GEMINI and not api_key:
            st.error(t("run.need_key"))
        elif not files:
            st.warning(t("run.need_file"))
        elif not todo:
            st.success(t("run.all_done"))
        else:
            ep = endpoint()
            prog = st.progress(0.0)
            n_ok, n_fail, stopped = 0, 0, False
            for i, file in enumerate(todo):
                st.subheader(file.name)
                status = st.empty()
                raw = None
                for attempt in range(3):
                    try:
                        status.info(t("run.coding", a=attempt + 1))
                        transcript = read_docx(file)
                        if not transcript.strip():
                            raise ValueError(t("run.empty_doc"))
                        # 提示詞的語言指示要依**這一份**的內容決定，
                        # 中文稿產中文、英文稿產英文，所以每份重建一次。
                        sysmsg = build_system_prompt(
                            FW, st.session_state.analysis_lang, transcript)

                        # 編碼期間被丟掉的碼要收起來給使用者看。以缺席為證據
                        # 的碼（「未表現出對自身假設的反省」）在這裡被擋掉，
                        # 而擋掉這件事本身是研究者需要知道的資訊——它說的是
                        # 這顆模型在這份稿件上的失效率。
                        run_drops = []

                        def code_chunk(text, n, total, _f=file, _s=sysmsg,
                                       _st=status, _dr=run_drops):
                            _st.info(t("run.coding_chunk", i=n + 1, n=total))
                            out = LLM.complete(
                                ep, f"File: {_f.name}\n\n"
                                    f"Excerpt {n + 1} of {total}:\n{text}",
                                system=_s, temperature=0.2, json_mode=True)
                            j = LLM._extract_first_json(out)
                            if not j:
                                raise ValueError(t("run.no_json"))
                            j = j.replace("\r\n", "\n").replace("\r", "\n")
                            return S.migrate_record(
                                LLM.loads_lenient(fix_newlines_in_strings(j)),
                                dropped=_dr)

                        if use_chunks and len(transcript) > win:
                            merged = CH.code_transcript(transcript, code_chunk,
                                                        window=win, overlap=ov)
                            chunk_meta = merged.pop(S.META, {})
                            parts = merged.pop("_chunk_summaries", [])
                            if not merged[S.SEGMENTS]:
                                raise ValueError(t("run.no_json"))
                            # 各窗口的摘要是「這三千字裡有什麼」，不是這個人
                            # 的整體樣貌。串起來會是一份重複而破碎的東西，
                            # 所以另外跑一次綜述——輸入是各窗口的摘要，不是
                            # 整份逐字稿，成本很低。失敗就退回串接，不讓摘要
                            # 這種次要欄位害整份分析作廢。
                            try:
                                merged[S.SUMMARY] = LLM.complete(
                                    ep, t("run.synth_prompt",
                                          text="\n\n".join(parts)),
                                    system=sysmsg.split("=" * 68)[0],
                                    temperature=0.2)[:4000].strip()
                            except Exception:               # noqa: BLE001
                                merged[S.SUMMARY] = "\n\n".join(parts)
                            rec = S.migrate_record(merged)
                            rec.setdefault(S.META, {}).update(chunk_meta)
                            raw = f"(chunked: {chunk_meta.get('chunking')})"
                        else:
                            rec = code_chunk(transcript, 0, 1)
                            raw = "(single pass)"
                        rec[S.TRANSCRIPT] = transcript
                        rec[S.TRANSCRIPT_FILE] = file.name
                        # 稽核軌跡要記下**完整**的端點描述，不能只記模型名。
                        # 同一個 "llama3.1:8b" 在不同人的機器上是不同的量化
                        # 版本，只寫模型名的紀錄無法重現。
                        #
                        # 寫進 _meta 而不是 rec["_source"]：save_record 會濾掉
                        # 所有底線開頭的鍵，掛在 _source 上等於沒存。
                        rec.setdefault(S.META, {}).update({
                            "source": ep.describe(),
                            # 完整版：量化等級、digest、num_ctx、temperature、
                            # 分窗參數——換一個就是換一次實驗的每一樣東西
                            "endpoint": ep.provenance(
                                temperature=0.2,
                                window_chars=win if use_chunks else None,
                                overlap_chars=ov if use_chunks else None),
                            "framework_id": FW.id,
                            "coded_at": datetime.now().isoformat(timespec="seconds"),
                        })
                        save_record(rec)
                        # 存檔後立刻讓側欄的掃描快取失效，
                        # 否則新跑完的這一份不會出現在可載入清單裡。
                        st.session_state.pop("_saved_index", None)
                        st.session_state.records.append(rec)
                        n_ok += 1
                        n_seg = len(rec[S.SEGMENTS])
                        n_multi = sum(1 for s in rec[S.SEGMENTS]
                                      if len(S.codes_of(s)) > 1)
                        status.success(t("run.done", n=n_seg, m=n_multi))
                        # 產出量檢查。工具不知道正確答案是幾段——那是研究者
                        # 的判斷——但認得出幾種「不可能是真的」的形狀。沒有
                        # 這一層的話，使用者拿到 4 段，畫面上沒有任何
                        # 跡象顯示這份分析漏掉了大半份稿件。
                        yr = CH.yield_report(transcript, rec[S.SEGMENTS],
                                             FW.dimensions)
                        if yr["flags"]:
                            st.warning(t("run.yield_low", n=yr["n_segments"],
                                         chars=yr["chars"], d=yr["per_10k"],
                                         ref=yr["human_reference_per_10k"]))
                            if CH.FLAG_ONE_PER_DIMENSION in yr["flags"]:
                                st.error(t("run.yield_template"))
                            if yr["missing"]:
                                st.caption(t("run.yield_missing", dims=", ".join(
                                    I.dim(d) for d in yr["missing"])))
                        rec.setdefault(S.META, {})["yield"] = yr
                        # 以缺席為證據而被擋下的碼。數量大代表這顆模型在這
                        # 份稿件上經常憑「沒有出現 X」生碼——那是換模型或
                        # 收緊框架排除條件的訊號，不是可以忽略的雜訊。
                        _absent = [d for d in run_drops
                                   if d.get("reason") == S.DROP_ABSENCE_RATIONALE]
                        if _absent:
                            st.warning(t("run.absence_dropped", n=len(_absent)))
                            with st.expander(t("run.absence_detail")):
                                show_df(pd.DataFrame(_absent), hide_index=True)
                        rec[S.META]["dropped"] = run_drops
                        if delay:
                            time.sleep(delay)
                        break
                    except LLM.RateLimited:
                        # 配額用盡就整批停下。繼續跑下去只會讓每一份都失敗，
                        # 畫面被錯誤訊息淹沒，也看不出到底做到哪裡。
                        status.error(t("run.quota"))
                        stopped = True
                        break
                    except (LLM.ContextOverflow, LLM.NotConfigured) as e:
                        # 這兩種錯誤重試一百次也一樣：context 不夠就是不夠，
                        # 服務沒開就是沒開。直接停下並把解法講清楚。
                        status.error(str(e))
                        stopped = True
                        break
                    except Exception as e:
                        if attempt < 2:
                            status.warning(f"{t('run.retry')} ({e})")
                            time.sleep(5)
                        else:
                            n_fail += 1
                            status.error(t("run.failed", name=file.name))
                            with st.expander(t("run.raw_output")):
                                st.code((raw or "-")[:4000])
                prog.progress((i + 1) / len(todo))
                if stopped:
                    break

            remaining = len(todo) - n_ok - n_fail
            if stopped:
                st.warning(t("run.stopped_summary", ok=n_ok, left=remaining))
                st.info(t("run.resume_hint"))
            elif n_ok:
                st.success(t("run.batch_done", ok=n_ok, fail=n_fail))

    # -----------------------------------------------------------------
    # 開放編碼的批次
    #
    # 與上面最大的差別：**碼簿跨檔案累積**。每跑完一份逐字稿，碼簿就長大
    # 一點，下一份會帶著它去編碼——沒有這一點，一份兩萬字的稿件會產出兩百
    # 個互不相同的標籤，那不是編碼，是逐段下標題。
    #
    # 檔案的順序因此是有意義的（先跑的那幾份決定了碼簿的骨架），所以介面
    # 上要說出目前碼簿有幾個碼、是接續哪一份，不能讓它靜悄悄地累積。
    # -----------------------------------------------------------------
    if mode == MODE_OPEN and st.button(t("run.open_start"), type="primary",
                                       key="btn_open_run"):
        if not model_name:
            st.error(t("run.need_model"))
        elif provider == LLM.GEMINI and not api_key:
            st.error(t("run.need_key"))
        elif not files:
            st.warning(t("run.need_file"))
        else:
            ep = endpoint()
            cb = st.session_state.codebook or OP.new_codebook(
                st.session_state.analysis_lang)
            st.session_state.codebook = cb
            prog = st.progress(0.0)
            n_ok = n_fail = 0
            for i, file in enumerate(files):
                st.subheader(file.name)
                status = st.empty()
                try:
                    transcript = read_docx(file)
                    if not transcript.strip():
                        raise ValueError(t("run.empty_doc"))

                    def code_open(text, n, total, _f=file, _st=status, _cb=cb,
                                  _tr=transcript):
                        _st.info(t("run.coding_chunk", i=n + 1, n=total))
                        # 提示詞每個窗口重建一次——**因為碼簿變了**。這跟
                        # 框架驅動那邊不同：那邊整份共用一份提示詞就夠，
                        # 這邊每編一段碼簿就長大，下一段必須看得到。
                        sysmsg = OP.build_open_prompt(
                            _cb, st.session_state.analysis_lang, _tr,
                            corpus_term=FW.corpus_term("document", "en"))
                        out = LLM.complete(
                            ep, f"File: {_f.name}\n\n"
                                f"Excerpt {n + 1} of {total}:\n{text}",
                            system=sysmsg, temperature=0.2, json_mode=True)
                        j = LLM._extract_first_json(out)
                        if not j:
                            raise ValueError(t("run.no_json"))
                        j = j.replace("\r\n", "\n").replace("\r", "\n")
                        return LLM.loads_lenient(fix_newlines_in_strings(j))

                    rec = OP.open_code_transcript(
                        transcript, code_open, cb,
                        window=win if use_chunks else 10 ** 9, overlap=ov)
                    rec[S.TRANSCRIPT] = transcript
                    rec[S.TRANSCRIPT_FILE] = file.name
                    rec[S.META]["source"] = ep.describe()
                    rec[S.META]["endpoint"] = ep.provenance(
                        temperature=0.2,
                        window_chars=win if use_chunks else None,
                        overlap_chars=ov if use_chunks else None)
                    rec[S.META]["coded_at"] = datetime.now().isoformat(
                        timespec="seconds")
                    st.session_state.open_records.append(rec)
                    n_ok += 1

                    _st = [s for s in (rec[S.META].get("codes_per_chunk") or [])]
                    status.success(t(
                        "run.open_done",
                        seg=len(rec[OP.OPEN_SEGMENTS]),
                        new=sum(s.get("created", 0) for s in _st),
                        reused=sum(s.get("reused", 0) for s in _st),
                        total=len(cb[OP.CODES])))
                    if rec[S.META].get("chunk_errors"):
                        st.warning(t("run.open_chunk_errors",
                                     n=len(rec[S.META]["chunk_errors"])))
                    if delay:
                        time.sleep(delay)
                except LLM.RateLimited:
                    status.error(t("run.quota"))
                    break
                except (LLM.ContextOverflow, LLM.NotConfigured) as e:
                    status.error(str(e))
                    break
                except Exception as e:                       # noqa: BLE001
                    n_fail += 1
                    status.error(f"{t('run.failed', name=file.name)}: "
                                 f"{type(e).__name__}: {e}")
                prog.progress((i + 1) / len(files))
            if n_ok:
                st.success(t("run.open_batch_done", ok=n_ok, fail=n_fail,
                             codes=len(cb[OP.CODES])))
                st.info(t("run.open_next_step"))

    if st.session_state.records:
        st.divider()
        st.markdown(f"### {t('run.workspace')}")
        show_df(pretty(pd.DataFrame(A.coverage_report(st.session_state.records))),
                hide_index=True)


# =====================================================================
# 5b. 碼簿（開放編碼）
#
# 這個頁籤是開放編碼與後續分析之間的關口。碼簿在這裡定案——定案之前所有
# 頻次都是暫時的，談不上信度與共現；定案之後轉成框架，整條既有管線才接
# 得上。介面要把這個先後講清楚，不能讓使用者在碼還在長的時候就去看交叉表。
# =====================================================================
with tab_codebook:
    cb = st.session_state.codebook
    if not cb or not cb[OP.CODES]:
        st.info(t("cb.empty"))
        st.caption(t("cb.empty_hint"))
    else:
        stats = OP.codebook_stats(cb)
        m = st.columns(4)
        m[0].metric(t("cb.n_codes"), stats["codes"])
        m[1].metric(t("cb.n_applications"), stats["applications"])
        m[2].metric(t("cb.n_singletons"), stats["singletons"])
        m[3].metric(t("cb.n_undefined"), stats["undefined"])
        st.caption(t("cb.provenance", cb=cb[OP.CODEBOOK_ID],
                     created=cb.get(OP.CREATED, "—"),
                     docs=len(st.session_state.open_records)))

        # --- 飽和度 ---
        curve = OP.saturation_curve(st.session_state.open_records)
        if len(curve) >= 3:
            st.markdown(f"#### {t('cb.saturation')}")
            st.caption(t("cb.saturation_help"))
            show_df(pd.DataFrame(curve).rename(columns={
                "n": t("cb.chunk_n"), "created": t("cb.created"),
                "reused": t("cb.reused"), "cumulative": t("cb.cumulative")}),
                hide_index=True)

        # --- 碼簿本體 ---
        st.divider()
        st.markdown(f"#### {t('cb.codes')}")
        cb_df = pd.DataFrame([{
            t("cb.col_id"): c[OP.CODE_ID],
            t("cb.col_label"): c[OP.CODE_LABEL],
            t("cb.col_count"): c[OP.CODE_COUNT],
            t("cb.col_definition"): c[OP.CODE_DEFINITION],
            t("cb.col_example"): (c[OP.CODE_EXAMPLES][0][S.QUOTE]
                                  if c[OP.CODE_EXAMPLES] else ""),
            t("cb.col_merged"): "; ".join(c.get(OP.CODE_MERGED_FROM) or []),
        } for c in sorted(cb[OP.CODES], key=lambda x: -x[OP.CODE_COUNT])])
        edited_cb = st.data_editor(
            cb_df, hide_index=True, **WIDE, key="cb_editor",
            column_config={
                t("cb.col_id"): st.column_config.TextColumn(disabled=True),
                t("cb.col_count"): st.column_config.NumberColumn(disabled=True),
                t("cb.col_example"): st.column_config.TextColumn(
                    disabled=True, width="large"),
                t("cb.col_merged"): st.column_config.TextColumn(disabled=True),
                t("cb.col_definition"): st.column_config.TextColumn(
                    width="large"),
            })
        if st.button(t("cb.save_edits"), key="btn_cb_save"):
            _by_id = {c[OP.CODE_ID]: c for c in cb[OP.CODES]}
            _n = 0
            for _, row in edited_cb.iterrows():
                c = _by_id.get(row[t("cb.col_id")])
                if not c:
                    continue
                for fld, col in ((OP.CODE_LABEL, t("cb.col_label")),
                                 (OP.CODE_DEFINITION, t("cb.col_definition"))):
                    v = str(row[col] or "").strip()
                    if v != c[fld]:
                        c[fld] = v
                        _n += 1
            st.success(t("cb.saved", n=_n))

        # --- 近義碼 ---
        st.divider()
        st.markdown(f"#### {t('cb.similar')}")
        st.caption(t("cb.similar_help"))
        thr = st.slider(t("cb.similar_threshold"), 0.3, 0.9, 0.5, step=0.05,
                        key="cb_thr")
        # 先拿全部筆數，再決定要顯示幾筆。**上限不能悄悄套用**：一份 352 個碼
        # 的碼簿有 972 對候選，只畫 40 筆卻不說，研究者會以為候選就是 40 筆
        # ——量測腳本也一樣：要用 limit=None，否則報出去的是顯示上限。
        all_pairs = OP.similar_pairs(cb, threshold=thr, limit=None)
        SHOW = 40
        pairs = all_pairs[:SHOW]
        if not pairs:
            st.caption(t("cb.similar_none"))
        elif len(all_pairs) > len(pairs):
            st.info(t("cb.similar_truncated", shown=len(pairs),
                      total=len(all_pairs)))
        else:
            st.caption(t("cb.similar_count", n=len(all_pairs)))
        for p in pairs:
            c1, c2, c3 = st.columns([4, 4, 2])
            c1.markdown(f"**{p['a_label']}** ({p['a_count']}×)")
            c2.markdown(f"**{p['b_label']}** ({p['b_count']}×)")
            c3.caption(f"{p['similarity']:.2f}")
            b1, b2 = c3.columns(2)
            # 合併方向要讓研究者選：留哪一個標籤是分析判斷，不是次數決定的。
            if b1.button("←", key=f"mg_a_{p['a']}_{p['b']}",
                         help=t("cb.merge_into", label=p["a_label"])):
                OP.merge_codes(cb, p["a"], [p["b"]],
                               records=st.session_state.open_records,
                               reviewer=t("cb.researcher"))
                st.rerun()
            if b2.button("→", key=f"mg_b_{p['a']}_{p['b']}",
                         help=t("cb.merge_into", label=p["b_label"])):
                OP.merge_codes(cb, p["b"], [p["a"]],
                               records=st.session_state.open_records,
                               reviewer=t("cb.researcher"))
                st.rerun()

        # --- 罕見碼 ---
        if stats["singletons"]:
            st.divider()
            st.markdown(f"#### {t('cb.rare')}")
            st.warning(t("cb.rare_warning", n=stats["singletons"]))
            if st.button(t("cb.rare_drop"), key="btn_cb_rare"):
                gone = OP.drop_rare_codes(
                    cb, min_count=2, records=st.session_state.open_records)
                st.success(t("cb.rare_dropped", n=len(gone)))
                st.rerun()

        # --- 定案：轉成框架 ---
        st.divider()
        st.markdown(f"#### {t('cb.to_framework')}")
        st.caption(t("cb.to_framework_help"))
        f1, f2 = st.columns(2)
        new_id = f1.text_input(t("cb.fw_id"),
                               value=f"induced_{datetime.now():%Y%m%d}",
                               key="cb_fw_id")
        new_name = f2.text_input(t("cb.fw_name"), value=t("cb.fw_name_default"),
                                 key="cb_fw_name")
        min_count = st.number_input(t("cb.fw_min_count"), 1, 20, 1,
                                    help=t("cb.fw_min_count_help"),
                                    key="cb_fw_min")
        if st.button(t("cb.fw_build"), type="primary", key="btn_cb_fw"):
            try:
                new_fw = OP.codebook_to_framework(
                    cb, new_id, new_name, min_count=int(min_count))
                path = F.save(new_fw)
                # 轉檔之後把紀錄也帶過去：碼簿定案的意義就是「從現在起，
                # 這些碼是一個框架」，紀錄留在開放格式等於定案沒有生效。
                F.set_active(new_fw)
                st.session_state.framework_id = new_fw.id
                converted = OP.to_records(st.session_state.open_records)
                for r in converted:
                    save_record(r)
                st.session_state.records = converted
                st.session_state.pop("_saved_index", None)
                OP.save_codebook(cb, os.path.join(
                    SAVE_DIR, f"codebook_{cb[OP.CODEBOOK_ID]}.json"))
                st.success(t("cb.fw_built", n=len(new_fw.dimensions),
                             path=os.path.basename(path),
                             recs=len(converted)))
                st.info(t("cb.fw_built_next"))
                # 碼簿定案的那一刻，這批資料就從「開放編碼」變成「有框架的
                # 編碼」了。側邊欄要跟著切回框架模式並顯示這個新框架，否則
                # 畫面會說「沒有套用框架」而分析頁籤卻在用它。widget 已經
                # 建立，這一輪改不了它的值，留個記號下一輪套用。
                st.session_state["_pending_mode"] = MODE_FRAMEWORK
            except Exception as e:                           # noqa: BLE001
                st.error(f"{type(e).__name__}: {e}")


# =====================================================================
# 6. 資料與屬性
# =====================================================================
with tab_data:
    recs = st.session_state.records
    if not recs:
        st.info(t("app.no_data"))
    else:
        st.markdown(f"### {t('data.descriptor_editor')}")
        st.caption(t("data.descriptor_hint"))

        desc_df = pd.DataFrame([
            {S.RESPONDENT: r.get(S.RESPONDENT, ""),
             **{k: I.descriptor_value(r.get(S.DESCRIPTORS, {}).get(k, S.UNSPECIFIED))
                for k in S.DESCRIPTOR_KEYS},
             "basis": r.get(S.DESCRIPTORS, {}).get(S.DESCRIPTOR_BASIS, "")}
            for r in recs])
        col_cfg = {
            # 受訪者名稱本來是唯讀的，理由是它被當成跨模組的連結鍵（逐字稿、
            # 信度抽樣框、主題的一階概念都靠它對回來）。但那個理由保護的是
            # 程式，不是使用者：模型從逐字稿抓出來的名稱經常有誤，而**去識別
            # 化**（把真名換成 TW-I-F-006）正是處理真實訪談資料時的必要動作。
            # 現在開放編輯，改名時同步更新所有依賴它的地方（見下方存檔處）。
            S.RESPONDENT: st.column_config.TextColumn(t("common.respondent"),
                                                      required=True),
            "basis": st.column_config.TextColumn(t("data.ai_basis"), disabled=True,
                                                 width="large"),
        }
        for k, opts in S.DESCRIPTOR_FIELDS.items():
            col_cfg[k] = st.column_config.SelectboxColumn(
                I.descriptor(k), options=[I.descriptor_value(o) for o in opts],
                required=True)
        edited = st.data_editor(desc_df, column_config=col_cfg, hide_index=True,
                                **WIDE, key="desc_editor")

        if st.button(t("data.save_descriptors"), type="primary", key="btn_desc"):
            renamed, clashes = [], []
            _existing = [r.get(S.RESPONDENT, "") for r in recs]
            for i, r in enumerate(recs):
                if i >= len(edited):
                    continue
                d = r.setdefault(S.DESCRIPTORS, S.blank_descriptors())
                for k, opts in S.DESCRIPTOR_FIELDS.items():
                    shown = edited.iloc[i][k]
                    match = next((o for o in opts
                                  if I.descriptor_value(o) == shown), None)
                    if match:
                        d[k] = match
                # --- 改名：要連著所有以名稱為鍵的地方一起改 ---
                old = r.get(S.RESPONDENT, "")
                new = str(edited.iloc[i][S.RESPONDENT] or "").strip()
                if new and new != old:
                    # 撞名會讓兩筆紀錄在交叉分析裡被合併成一個人，而且靜悄悄。
                    if new in _existing[:i] + _existing[i + 1:]:
                        clashes.append((old, new))
                    else:
                        r[S.RESPONDENT] = new
                        _existing[i] = new
                        # 逐字稿快取是用名稱當鍵的，不跟著改就會變成「缺逐字稿」
                        _tr = st.session_state.get("transcripts") or {}
                        if old in _tr:
                            _tr[new] = _tr.pop(old)
                            st.session_state.transcripts = _tr
                        renamed.append((old, new))
                save_record(r)
            if clashes:
                st.error(t("data.rename_clash",
                           pairs="；".join(f"{a} → {b}" for a, b in clashes)))
            if renamed:
                # 已經建好的信度抽樣框與主題是另外存的，裡面還是舊名字。
                # 這件事必須說出來，否則使用者會在信度頁籤看到對不上的資料
                # 卻找不到原因。
                st.warning(t("data.renamed",
                             n=len(renamed),
                             pairs="；".join(f"{a} → {b}" for a, b in renamed)))
            st.success(t("data.saved"))

        st.divider()
        st.markdown(f"### {t('data.health')}")
        show_df(pretty(pd.DataFrame(A.coverage_report(recs))), hide_index=True)

        # 簡繁檢查。分析語言設繁中、模型卻回簡體，是實測撞到的失效——
        # 中國訓練的模型（qwen 系列最明顯）即使被明確要求繁體仍會輸出簡體。
        # 這跟維度值寫成複合值是同一種病：模型不照約定，而工具沒有察覺，
        # 於是研究者拿到一份混雜簡體的分析卻不知道。
        # **只回報，不自動轉換**：簡轉繁不是一對一（发 → 發／髮），
        # 自動改寫等於工具替研究者竄改模型的輸出。
        # 退化標題：模型把維度名填進標題欄。那一欄的用途是給主題聚斂用的
        # 次主題標籤，填成維度名之後主題分析只會把框架本身再跑出來一次。
        _deg = {}
        for r in recs:
            d = S.degenerate_titles(r, labels=[I.dim(x, lang)
                                               for x in FW.dimensions]
                                   + [I.dim(x, "en") for x in FW.dimensions])
            if d:
                _deg[r.get(S.RESPONDENT, "?")] = d
        if _deg:
            st.warning(t("data.degenerate_titles",
                         n=sum(len(v) for v in _deg.values())))
            show_df(pd.DataFrame(
                [{"respondent": who, "segment": sid, "title": ti}
                 for who, segs in _deg.items() for sid, ti in segs.items()]),
                hide_index=True)

        # 共現有多少是分窗合併造成的。實測一份英文稿 14 個多重編碼段落裡
        # 有 11 個是這樣來的——共現表若照用，講出去的會是分窗的產物。
        _mp = A.merge_provenance(recs)
        if not _mp.empty and _mp["multi_from_merge"].sum() > 0:
            st.info(t("data.merge_provenance",
                      n=int(_mp["multi_from_merge"].sum()),
                      m=int(_mp["multi_coded"].sum())))
            show_df(pretty(_mp), hide_index=True)

        if st.session_state.analysis_lang == "zh-Hant":
            _script = {}
            for r in recs:
                h = S.scan_record_script(r)
                if h:
                    _script[r.get(S.RESPONDENT, "?")] = h
            if _script:
                _chars = sorted({c for v in _script.values()
                                 for cs in v.values() for c in cs})
                st.warning(t("data.simplified_found",
                             n=len(_script), chars="".join(_chars[:30])))
                show_df(pd.DataFrame(
                    [{"respondent": who, "where": seg, "chars": "".join(cs)}
                     for who, segs in _script.items()
                     for seg, cs in segs.items()]), hide_index=True)

        st.divider()
        st.markdown(f"### {t('data.per_case')}")
        names = [f"{i + 1}. {r.get(S.RESPONDENT, '')}" for i, r in enumerate(recs)]
        pick = st.selectbox(t("data.select_case"), names)
        rec = recs[names.index(pick)]

        d = rec.get(S.DESCRIPTORS, {})
        st.caption(" | ".join(f"**{I.descriptor(k)}**: "
                              f"{I.descriptor_value(d.get(k, S.UNSPECIFIED))}"
                              for k in S.DESCRIPTOR_KEYS))
        if rec.get(S.SUMMARY):
            st.success(rec[S.SUMMARY])

        segs = rec.get(S.SEGMENTS, [])
        cols = st.columns(max(len(FW.dimensions), 1))
        for i, dim in enumerate(FW.dimensions):
            if FW.has_polarity:
                parts = []
                for p in FW.polarity_values:
                    code = FW.code_of(dim, p)
                    parts.append(f"{p}:{sum(1 for s in segs if code in S.codes_of(s))}")
                cols[i].metric(I.dim(dim), "  ".join(parts))
            else:
                code = FW.code_of(dim)
                cols[i].metric(I.dim(dim),
                               sum(1 for s in segs if code in S.codes_of(s)))

        multi = [s for s in segs if len(S.codes_of(s)) > 1]
        if multi:
            st.caption(t("data.multi_note", n=len(multi)))

        for seg in segs:
            codes = S.codes_of(seg)
            tags = " ".join(f"`{c}`" for c in codes)
            star = " *" if len(codes) > 1 else ""
            with st.expander(f"{tags}{star}  {seg.get(S.TITLE, '')}"):
                for c in seg.get(S.CODES_F, []):
                    dim = S.norm_dimension(c.get(S.DIMENSION))
                    if dim is None:
                        continue
                    code = FW.code_of(dim, S.norm_polarity(c.get(S.POLARITY)))
                    st.markdown(f"- **{I.code_label(code)}** — "
                                f"{c.get(S.RATIONALE, '')}")
                st.markdown(f"> {seg.get(S.QUOTE, '')}")
                st.caption(seg.get(S.FULL_TEXT, ""))


# =====================================================================
# 7. 編碼複核
# =====================================================================
with tab_review:
    recs = st.session_state.records
    if not recs:
        st.info(t("app.no_data"))
    else:
        RV.ensure_all(recs)
        with st.expander(t("rv.why")):
            st.markdown(t("rv.why_body"))
        reviewer = st.text_input(t("rv.reviewer"), "researcher", key="rv_who")
        rv1, rv2, rv3, rv4 = st.tabs([t("rv.tab1"), t("rv.tab2"),
                                      t("rv.tab3"), t("rv.tab4")])

        # ---- 逐段複核
        with rv1:
            c1, c2, c3 = st.columns([2, 2, 1])
            names = [r.get(S.RESPONDENT, "") for r in recs]
            who = c1.selectbox(t("common.respondent"), names, key="rv_case")
            rec = recs[names.index(who)]
            pending_only = c2.checkbox(t("rv.pending_only"), True, key="rv_pending")
            cf = c3.selectbox(t("rv.filter_code"), [t("common.all")] + S.CODES,
                              key="rv_cf")

            pool = rec.get(S.SEGMENTS, [])
            if pending_only:
                pool = [s for s in pool
                        if s[S.REVIEW][S.STATUS] == S.STATUS_PENDING]
            if cf != t("common.all"):
                pool = [s for s in pool if cf in S.codes_of(s)]

            total = len(rec.get(S.SEGMENTS, []))
            done = sum(1 for s in rec.get(S.SEGMENTS, [])
                       if s[S.REVIEW][S.STATUS] != S.STATUS_PENDING)
            st.progress(done / total if total else 0.0,
                        text=t("rv.progress", who=who, done=done, total=total))

            if not pool:
                st.success(t("rv.nothing"))
            else:
                per = 5
                npages = max(1, (len(pool) + per - 1) // per)
                pg = st.number_input(f"{t('ir.page')} / {npages}", 1, npages, 1,
                                     key="rv_pg")
                tr = available_transcripts(recs).get(who, "")
                for s in pool[(pg - 1) * per: pg * per]:
                    sid = s.get(S.SEGMENT_ID, "")
                    with st.container(border=True):
                        st.markdown(
                            f"**`{sid}`  {I.status(s[S.REVIEW][S.STATUS])}**  "
                            f"{t('rv.ai_original')}: "
                            f"`{'/'.join(s[S.REVIEW][S.ORIGINAL_CODES]) or '-'}`")
                        if tr:
                            v = RV.verify_quote(s, tr)
                            if v["full_text_ok"] is False:
                                st.error(t("rv.quote_bad_full"))
                            elif v["quote_ok"] is False:
                                st.warning(t("rv.quote_bad_brief"))
                            else:
                                st.caption(t("rv.quote_ok"))
                        title = st.text_input(t("common.title"), s.get(S.TITLE, ""),
                                              key=f"rv_t_{who}_{sid}")
                        quote = st.text_area(t("common.quote"), s.get(S.QUOTE, ""),
                                             height=68, key=f"rv_q_{who}_{sid}")
                        with st.expander(t("common.full_text")):
                            full = st.text_area(
                                t("common.full_text"), s.get(S.FULL_TEXT, ""),
                                height=120, key=f"rv_f_{who}_{sid}",
                                label_visibility="collapsed")
                        picked = st.multiselect(
                            t("common.codes"), S.CODES, default=S.codes_of(s),
                            key=f"rv_c_{who}_{sid}",
                            format_func=lambda c: f"{c}  {I.code_label(c)}")
                        if s.get(S.CODES_F):
                            st.caption(t("rv.ai_rationale") + ": " + "; ".join(
                                f"{c.get(S.RATIONALE, '')}" for c in s[S.CODES_F]
                                if c.get(S.RATIONALE)))
                        b1, b2, b3 = st.columns([1, 1, 2])
                        if b1.button(t("rv.confirm"), key=f"rv_ok_{who}_{sid}",
                                     **WIDE):
                            RV.update_text(s, title=title, quote=quote,
                                           full_text=full, reviewer=reviewer)
                            RV.update_codes(s, picked, reviewer=reviewer)
                            save_record(rec)
                            st.rerun()
                        if b2.button(t("rv.delete"), key=f"rv_del_{who}_{sid}",
                                     **WIDE):
                            RV.delete_segment(rec, sid, reviewer=reviewer)
                            save_record(rec)
                            st.rerun()
                        b3.caption(t("rv.confirm_help"))

            if rec.get(S.DELETED_SEGMENTS):
                with st.expander(t("rv.deleted_box",
                                   n=len(rec[S.DELETED_SEGMENTS]))):
                    for s in list(rec[S.DELETED_SEGMENTS]):
                        cc1, cc2 = st.columns([4, 1])
                        cc1.caption(f"`{s.get(S.SEGMENT_ID)}`  "
                                    f"{'/'.join(s[S.REVIEW][S.ORIGINAL_CODES]) or '-'}"
                                    f"  {s.get(S.QUOTE, '')[:40]}")
                        if cc2.button(t("rv.restore"),
                                      key=f"rv_res_{who}_{s.get(S.SEGMENT_ID)}"):
                            RV.restore_segment(rec, s.get(S.SEGMENT_ID),
                                               reviewer=reviewer)
                            save_record(rec)
                            st.rerun()

        # ---- 人工新增
        with rv2:
            st.caption(t("rv.add_hint"))
            names2 = [r.get(S.RESPONDENT, "") for r in recs]
            who2 = st.selectbox(t("rv.add_to"), names2, key="rv_add_case")
            rec2 = recs[names2.index(who2)]
            new_title = st.text_input(t("common.title"), key="rv_add_t")
            new_text = st.text_area(t("rv.add_text"), height=130, key="rv_add_f")
            new_codes = st.multiselect(t("common.codes"), S.CODES, key="rv_add_c",
                                       format_func=lambda c: f"{c}  {I.code_label(c)}")
            new_reason = st.text_input(t("rv.add_reason"), "model missed it",
                                       key="rv_add_r")
            tr2 = available_transcripts(recs).get(who2, "")
            if new_text and tr2:
                if RV.normalize(new_text) in RV.normalize(tr2):
                    st.success(t("rv.in_transcript"))
                else:
                    st.warning(t("rv.not_in_transcript"))
            if st.button(t("rv.add_go"), type="primary", key="rv_add_go"):
                if not new_text or not new_codes:
                    st.error(t("rv.add_need"))
                else:
                    s = RV.add_segment(rec2, new_text, new_codes, title=new_title,
                                       reviewer=reviewer, reason=new_reason)
                    save_record(rec2)
                    st.success(f"{s[S.SEGMENT_ID]}: {'/'.join(S.codes_of(s))}")

        # ---- 引文驗證
        with rv3:
            # 逐字稿以紀錄內含的為準，不必等使用者到信度頁籤上傳。
            tmap = available_transcripts(recs)
            if not tmap:
                st.info(t("rv.no_transcripts"))
            else:
                summ, rows = RV.verify_all_quotes(recs, tmap)
                m1, m2, m3 = st.columns(3)
                m1.metric(t("common.segment"), summ["checked"])
                m2.metric(t("rv.quote_rate"),
                          f"{(summ['full_text_rate'] or 0) * 100:.1f}%")
                m3.metric(t("rv.needs_check"), summ["needs_review"])
                if rows:
                    show_df(pretty(pd.DataFrame(rows)), hide_index=True)
                else:
                    st.success(t("rv.all_verbatim"))

        # ---- 複核報表
        with rv4:
            stt = RV.review_stats(recs)
            m = st.columns(5)
            m[0].metric(t("rv.stat_ai"), stt["ai_segments"])
            m[1].metric(t("rv.stat_rate"), f"{(stt['review_rate'] or 0) * 100:.0f}%")
            m[2].metric(t("rv.stat_modified"), f"{(stt['modify_rate'] or 0) * 100:.0f}%")
            m[3].metric(t("rv.stat_deleted"), f"{(stt['delete_rate'] or 0) * 100:.0f}%")
            m[4].metric(t("rv.stat_added"), stt["human_added"])
            if stt["pending"]:
                st.warning(t("rv.pending_warn", n=stt["pending"]))
            else:
                st.success(t("rv.all_done"))

            st.markdown(f"##### {t('rv.methods_sentence')}")
            facts = RV.methods_facts(recs)
            st.code(I.methods_sentence(facts, "zh"), language=None)
            st.code(I.methods_sentence(facts, "en"), language=None)

            st.markdown(f"##### {t('rv.code_changes')}")
            cdf = pd.DataFrame(RV.code_level_changes(recs))
            show_df(pretty(cdf, code_cols=["code"]), hide_index=True)
            st.caption(t("rv.removal_note"))

            st.markdown(f"##### {t('rv.changed')}")
            ch = RV.changed_segments(recs)
            show_df(pretty(pd.DataFrame(ch)) if ch else pd.DataFrame(),
                    hide_index=True)

            st.markdown(f"##### {t('rv.trail')}")
            trail = RV.audit_trail(recs)
            show_df(pretty(pd.DataFrame(trail)) if trail else pd.DataFrame(),
                    hide_index=True)

            rbuf = io.BytesIO()
            with pd.ExcelWriter(rbuf, engine="openpyxl") as xw:
                pd.DataFrame([stt]).to_excel(xw, sheet_name=t("sheet.review_summary"),
                                             index=False)
                cdf.to_excel(xw, sheet_name=t("sheet.code_changes"), index=False)
                (pd.DataFrame(ch) if ch else pd.DataFrame({"-": []})).to_excel(
                    xw, sheet_name=t("sheet.changed_segments"), index=False)
                (pd.DataFrame(trail) if trail else pd.DataFrame({"-": []})).to_excel(
                    xw, sheet_name=t("sheet.audit_trail"), index=False)
            rbuf.seek(0)
            st.download_button(f"{t('common.download')} — {t('rv.tab4')}", rbuf,
                               file_name=f"review_{datetime.now():%Y%m%d}.xlsx",
                               **WIDE, type="primary")


# =====================================================================
# 8. 交互分析
# =====================================================================
with tab_cross:
    recs = st.session_state.records
    long_df = A.build_long_df(recs)
    if long_df.empty:
        st.info(t("app.no_data"))
    else:
        st.caption(t("cross.basis", r=long_df[S.RESPONDENT].nunique(),
                     s=long_df[S.SEGMENT_ID].nunique(), c=len(long_df)))

        # 無極性框架時不顯示極性平衡——那個分析在此沒有意義
        sub_keys = ["cross.tab1", "cross.tab2", "cross.tab3"]
        if FW.has_polarity:
            sub_keys.append("cross.tab4")
        subs = st.tabs([t(k) for k in sub_keys])

        # ---- 交叉表
        with subs[0]:
            c1, c2, c3 = st.columns(3)
            dkey = c1.selectbox(t("cross.group_by"), S.DESCRIPTOR_KEYS,
                                format_func=I.descriptor, key="cx_dkey")
            # 極性也要能當列單位。屬性 × 極性通常是這幾張表裡唯一一張
            # 期望次數夠大、卡方前提站得住的——欄數最少，格子自然最滿。
            # 少了這個選項，使用者在八格編碼的表上只會一直看到「前提不成立」，
            # 而工具其實算得出來的那一個檢定，介面上根本到不了。
            unit_opts = [A.CODE] + ([S.DIMENSION, S.POLARITY]
                                    if FW.has_polarity else [])
            _unit_names = {A.CODE: "common.code", S.DIMENSION: "common.dimension",
                           S.POLARITY: "common.polarity"}
            unit = c2.selectbox(t("cross.unit"), unit_opts,
                                format_func=lambda u: t(_unit_names[u]),
                                help=t("cross.unit_help"), key="cx_unit")
            # 選項值用穩定識別碼，顯示交給 format_func。
            # 若拿翻譯後的字串當選項值，widget 狀態會以該語言的字串存進
            # session_state；使用者一切換介面語言，殘留值就不在新的選項清單裡了。
            show_pct = c3.selectbox(
                t("cross.show"), ["pct", "count"],
                format_func=lambda v: (t("cross.row_pct") if v == "pct"
                                       else t("cross.raw_count")),
                key="cx_show") == "pct"
            drop_un = st.checkbox(t("cross.drop_unspecified"), True, key="cx_drop")
            # 卡方假設觀察獨立，而編碼單元巢套在受訪者底下。這個開關至少
            # 拿掉「同一個人講了七次就算七個觀察」那一層。
            case_lvl = st.checkbox(t("cross.case_level"), False, key="cx_case",
                                   help=t("cross.case_level_help"))

            use = long_df[long_df[dkey] != S.UNSPECIFIED] if drop_un else long_df
            if use.empty:
                st.warning(t("cross.no_data_after_filter"))
            else:
                ct, pct = A.crosstab_by_descriptor(use, dkey, row_unit=unit,
                                                   case_level=case_lvl)
                if case_lvl:
                    st.caption(t("cross.case_level_note",
                                 n=int(ct.values.sum())))
                shown = pct if show_pct else ct
                disp = shown.copy()
                disp.index = [I.descriptor_value(i) for i in disp.index]
                _col_label = {A.CODE: I.code_label, S.DIMENSION: I.dim,
                              S.POLARITY: I.polarity_generic}[unit]
                # 受訪者層級的表多一欄 "mixed"：最常出現的類別不只一個的受訪者。
                # 它不是框架裡的碼，不能丟給 code_label 去查。
                disp.columns = [t("cross.case_mixed") if c == A.CASE_MIXED
                                else _col_label(c) for c in disp.columns]
                heatmap(disp, f"{I.descriptor(dkey)} × {t('cross.unit')}")
                show_df(disp)
                st.caption(t("cross.pct_note"))

                with st.expander(t("cross.chi_title")):
                    rep = A.chi_square_report(ct)
                    if rep["verdict"] == A.CHI_UNAVAILABLE:
                        st.info(t("cross.chi_no_scipy"))
                    elif rep["verdict"] == A.CHI_TOO_SMALL:
                        st.info(t("cross.chi_too_small"))
                    else:
                        k1, k2, k3, k4 = st.columns(4)
                        k1.metric("χ²", rep["chi2"])
                        k2.metric("df", rep["dof"])
                        k3.metric(t("stat.cramers_v"), rep["cramers_v"])
                        k4.metric(t("stat.n"), rep["n"])
                        # 卡方有兩個前提，守衛要對兩個都有交代。
                        #
                        # 期望次數一過關就亮綠燈說「p may be reported」、
                        # 正下方的灰字卻說觀察不獨立——那是同一個畫面上一邊
                        # 說可以報、一邊說不該當推論。獨立性其實查得出來：
                        # 表的總數大於受訪者人數，就是有人被算了不只一次。
                        n_resp = int(use[S.RESPONDENT].nunique())
                        nested = (not case_lvl) and rep["n"] > n_resp
                        if not rep["valid"]:
                            st.warning(t("cross.chi_sparse",
                                         small=rep["cells_below_5"],
                                         total=rep["cells_total"]))
                        elif nested:
                            st.info(t("cross.chi_nested", p=f"{rep['p']:.4f}",
                                      n=rep["n"], k=n_resp))
                        else:
                            st.success(f"p = {rep['p']:.4f}  {t('cross.chi_ok')}")
                        if case_lvl:
                            st.caption(t("cross.chi_case_note", k=n_resp))
                        elif not (rep["valid"] and nested):
                            # 藍色提示已經講過獨立性的那一種情況，不再重複一次
                            st.caption(t("cross.chi_independence"))

        # ---- 共現
        with subs[1]:
            lv = st.radio(t("cross.cooc_level"),
                          [A.LEVEL_SEGMENT, A.LEVEL_CASE], horizontal=True,
                          format_func=lambda v: (t("cross.level_segment")
                                                 if v == A.LEVEL_SEGMENT
                                                 else t("cross.level_case")),
                          help=t("cross.level_help"), key="cx_lv")
            # 分窗編碼會製造共現：同一句話在兩個窗口各被判一次，合併之後
            # 就帶著兩個碼。那個共現不是模型在任何一次判斷裡主張的。
            # 兩個數字並陳，差距本身就是要看的東西。
            _mp = A.merge_provenance(recs)
            _has_merge = (not _mp.empty) and _mp["multi_from_merge"].sum() > 0
            excl_merged = False
            if _has_merge:
                excl_merged = st.checkbox(
                    t("cross.exclude_merged"), value=False, key="cx_exmg",
                    help=t("cross.exclude_merged_help"))
                st.caption(t("cross.merge_note",
                             n=int(_mp["multi_from_merge"].sum()),
                             m=int(_mp["multi_coded"].sum())))
            cnt, jac, tot = A.cooccurrence(recs, level=lv,
                                           exclude_merged=excl_merged)
            metric = st.radio(t("cross.matrix_value"), ["count", "jaccard"],
                              format_func=lambda v: (t("common.count")
                                                     if v == "count"
                                                     else t("stat.jaccard")),
                              horizontal=True, key="cx_metric")
            mat = cnt if metric == "count" else jac
            disp = mat.copy()
            disp.index = [I.code_label(c) for c in disp.index]
            disp.columns = list(mat.columns)
            if metric == "count":
                st.caption(t("cross.diag_note"))
            heatmap(disp, t("cross.tab2"), colorscale="Reds")

            pairs = A.cooccurrence_pairs(cnt, tot, top_n=20)
            st.markdown(f"#### {t('cross.top_pairs')}")
            if pairs.empty:
                st.warning(t("cross.no_cooc"))
            else:
                show_df(pretty(pairs, code_cols=["code_a", "code_b"]),
                        hide_index=True)
                st.caption(t("cross.jaccard_note"))
            n_multi = sum(1 for r in recs for s in r.get(S.SEGMENTS, [])
                          if len(S.codes_of(s)) > 1)
            n_seg = sum(len(r.get(S.SEGMENTS, [])) for r in recs)
            st.info(t("cross.multi_stat", m=n_multi, n=n_seg))

        # ---- 跨案例
        with subs[2]:
            norm = st.checkbox(t("cross.normalize_case"), True,
                               help=t("cross.normalize_help"), key="cx_norm")
            m = A.case_matrix(long_df, normalize=norm)
            heatmap(m, t("cross.tab3"))
            show_df(m)
            st.caption(t("cross.case_note"))

        # ---- 極性平衡（僅有極性的框架）
        if FW.has_polarity:
            with subs[3]:
                per_dim, overall = A.polarity_balance(long_df)
                st.markdown(f"#### {t('cross.polarity_overall')}")
                if HAS_PLOTLY and not overall.empty:
                    o = overall.sort_values("polarity_index")
                    fig = px.bar(o, x="polarity_index", y=S.RESPONDENT,
                                 orientation="h", color="polarity_index",
                                 color_continuous_scale="RdBu", range_color=[-1, 1],
                                 text="polarity_index")
                    fig.update_layout(height=max(300, 40 * len(o) + 120),
                                      margin=dict(l=10, r=10, t=40, b=10))
                    st.plotly_chart(fig, **WIDE)
                show_df(pretty(overall), hide_index=True)

                st.markdown(f"#### {t('cross.polarity_by_dim')}")
                pivot = per_dim.pivot(index=S.RESPONDENT, columns=S.DIMENSION,
                                      values="polarity_index")
                pivot = pivot.reindex(columns=[d for d in FW.dimensions
                                               if d in pivot.columns])
                pivot.columns = [I.dim(c) for c in pivot.columns]
                heatmap(pivot.round(2).fillna(0), t("cross.polarity_by_dim"),
                        colorscale="RdBu", zmid=0)

                if HAS_PLOTLY and not per_dim.empty:
                    st.markdown(f"#### {t('cross.radar')}")
                    people = sorted(per_dim[S.RESPONDENT].unique())
                    sel = st.multiselect(t("cross.radar_select"), people,
                                         default=people[:4], key="cx_radar")
                    if sel:
                        fig = go.Figure()
                        axis = [I.dim(d) for d in FW.dimensions]
                        for name in sel:
                            sub = per_dim[per_dim[S.RESPONDENT] == name] \
                                .set_index(S.DIMENSION)
                            vals = [float(sub["polarity_index"].get(d, 0) or 0)
                                    for d in FW.dimensions]
                            fig.add_trace(go.Scatterpolar(
                                r=vals + [vals[0]], theta=axis + [axis[0]],
                                fill="toself", name=str(name), opacity=0.5))
                        fig.update_layout(
                            polar=dict(radialaxis=dict(range=[-1, 1], visible=True)),
                            height=520, margin=dict(t=40, b=20))
                        st.plotly_chart(fig, **WIDE)
                        # 極性雷達圖的圓心是 −1 而不是 0，這一點必須寫在圖旁邊。
                        # 讀者對雷達圖的預設是「圓心＝零＝沒有」，於是會把
                        # 縮到中心的軸讀成「很少談這個維度」——實際上是
                        # 「談的時候幾乎都是負向的」。兩者都是有意義的發現，
                        # 但完全不同，而且在圖上長得一模一樣。
                        st.caption(t("cross.radar_centre_note"))

                show_df(pretty(per_dim, dim_cols=[S.DIMENSION]), hide_index=True)
                st.caption(t("cross.polarity_note"))


# =====================================================================
# 9. 主題結構
# =====================================================================
with tab_themes:
    recs = st.session_state.records
    items = RT.collect_first_order(recs)
    with st.expander(t("th.disclaimer")):
        st.markdown(t("th.disclaimer_body"))

    c0, c1, c2 = st.columns(3)
    c0.metric(t("common.respondent"), len({i[S.RESPONDENT] for i in items}))
    c1.metric(t("common.segment"), len(items))
    c2.metric(t("th.tab2"), len(st.session_state.get("themes") or []))

    th1, th2, th3, th4 = st.tabs([t("th.tab1"), t("th.tab2"),
                                  t("th.tab3"), t("th.tab4")])

    with th1:
        if 0 < len(items) < 30:
            st.warning(t("th.too_few", n=len(items)))

        # -------------------------------------------------------------
        # 不用模型的那條路。
        #
        # 主題歸納是這套工具最依賴模型的一步，而它也是最不需要依賴模型的
        # 一步。把碼收成群，CAQDAS 早有機械的做法（NVivo 的 cluster
        # analysis 用詞彙相似度）；這裡提供兩種基底，一種看共現、一種看
        # 標籤文字。**刻意只做到提出分組為止**：二階主題的名字就是詮釋
        # 本身，讓模型代筆等於把研究者的工作外包出去。
        # -------------------------------------------------------------
        with st.expander(t("th.nomodel")):
            st.markdown(t("th.nomodel_body"))
            used = [c for c in S.CODES
                    if any(c in (i.get(RT.EXISTING_CODES) or []) for i in items)]
            if len(used) < 2:
                st.info(t("th.nomodel_need"))
            else:
                nb1, nb2 = st.columns([2, 1])
                basis = nb1.radio(
                    t("th.nomodel_basis"), ["cooccurrence", "labels"],
                    horizontal=True, key="th_basis",
                    format_func=lambda v: (t("th.basis_cooc") if v == "cooccurrence"
                                           else t("th.basis_labels")),
                    help=t("th.nomodel_basis_help"))
                n_groups = nb2.number_input(t("th.nomodel_k"), 2,
                                            max(2, len(used)),
                                            min(8, max(2, len(used) // 2)),
                                            key="th_k")
                if st.button(t("th.nomodel_go"), key="btn_cluster"):
                    cnt, _jac, tot = A.cooccurrence(recs)
                    if basis == "cooccurrence":
                        dist = RT.cooccurrence_distances(cnt, tot, used)
                    else:
                        dist = RT.label_distances(
                            {c: f"{I.code_label(c)} {FW.definition(S.split_code(c)[0], I.get_lang())}"
                             for c in used})
                    st.session_state.code_clusters = RT.cluster_codes(
                        dist, used, k=int(n_groups), weights=tot)
                    st.session_state.cluster_basis = basis

                groups = st.session_state.get("code_clusters") or []
                if groups:
                    cnt, _jac, tot = A.cooccurrence(recs)
                    if st.session_state.get("cluster_basis") == "cooccurrence" \
                            and all(g[RT.CLUSTER_DISTANCE] > 0.95
                                    for g in groups if len(g[RT.CLUSTER_MEMBER_CODES]) > 1):
                        st.warning(t("th.cluster_no_basis"))
                    show_df(pd.DataFrame([
                        {"group": k,
                         t("th.cluster_distance"): g[RT.CLUSTER_DISTANCE],
                         t("common.codes"): ", ".join(
                             f"{I.code_label(c)} ({int(tot.get(c, 0))})"
                             for c in g[RT.CLUSTER_MEMBER_CODES])}
                        for k, g in enumerate(groups, 1)]), hide_index=True)
                    st.caption(t("th.cluster_distance_note"))
                    st.markdown(f"###### {t('th.name_groups')}")
                    st.caption(t("th.name_groups_note"))
                    names = {}
                    for k, g in enumerate(groups, 1):
                        names[k] = st.text_input(
                            f"{k}. " + ", ".join(
                                I.code_label(c)
                                for c in g[RT.CLUSTER_MEMBER_CODES][:4]),
                            key=f"clname_{k}")
                    if st.button(t("th.nomodel_build"), type="primary",
                                 key="btn_cluster_themes"):
                        unnamed = [k for k, v in names.items() if not v.strip()]
                        built = RT.themes_from_clusters(groups, items, names)
                        st.session_state.themes = built
                        st.session_state.theme_note = ""
                        st.session_state.theme_debug = None
                        with open(THEMES_PATH, "w", encoding="utf-8") as f:
                            json.dump({"themes": built, "unassigned_note": "",
                                       "framework_id": FW.id,
                                       "generated": datetime.now().isoformat(),
                                       # 沒有模型參與，來源記的是演算法本身
                                       "source": ("cluster/" +
                                                  str(st.session_state.get(
                                                      "cluster_basis"))),
                                       "endpoint": None,
                                       # 誰命名的要留下來：分群是機械的，
                                       # 名字是詮釋，兩者的責任歸屬不同。
                                       "named_by": st.session_state.get(
                                           "rv_who") or "",
                                       "diagnostics": {
                                           "method": "agglomerative-average",
                                           "basis": st.session_state.get(
                                               "cluster_basis"),
                                           "k": len(groups),
                                           "merge_distances": [
                                               g[RT.CLUSTER_DISTANCE]
                                               for g in groups]}},
                                      f, ensure_ascii=False, indent=2)
                        st.success(t("th.nomodel_built", n=len(built)))
                        if unnamed:
                            st.warning(t("th.nomodel_unnamed", n=len(unnamed)))

        cc1, cc2, cc3 = st.columns(3)
        chunk = cc1.number_input(t("th.chunk"), 20, 200, 60, 10, key="th_chunk")
        min_sz = cc2.number_input(t("th.min_size"), 1, 5, 2,
                                  help=t("th.min_size_help"), key="th_min")
        # 用側欄同一份清單（向服務查詢而來）。主題歸納預設挑推理能力較強
        # 的那一顆：這一步是把幾百個一階概念抽象成二階主題，比逐句編碼更難。
        # 雲端看 "pro"，地端看參數量——70b 之於 8b 的差距，在這一步遠比在
        # 逐句編碼上明顯。
        if models:
            _big = next((i for i, m in enumerate(models)
                         if "pro" in m.lower()
                         or re.search(r"\b(70|72|123|405)b\b", m.lower())), 0)
            tmodel = cc3.selectbox(t("app.model"), models, index=_big,
                                   key="th_model")
        else:
            tmodel = cc3.text_input(t("app.model"), value=model_name,
                                    key="th_model")

        # -------------------------------------------------------------
        # 送出前先探測模型照不照得住輸出約定。
        #
        # 要防的失效：一次歸納跑出 9 個主題，7 個掉進未歸屬，四個維度掛零三個
        # ——而模型自己寫的歸屬理由明明指名了 anticipation 與 responsiveness。
        # 它不是判斷得不好，是沒照格式回答。使用者事後只看得到「未歸屬 7 個」，
        # 分不出那是資料的性質還是模型的問題，而那一輪已經花掉了。
        #
        # 探測幾秒鐘就跑完，抓的正是這個失效。**但它不擋任何東西**：合不合用
        # 是研究者的判斷，工具只負責讓他判斷得出來。寫死的模型白名單也一定
        # 會過期——這一點程式裡別處已經吃過虧。
        # -------------------------------------------------------------
        _probe_key = f"{endpoint(model=tmodel).describe()}|{FW.id}"
        _probed = (st.session_state.get("th_probe") or {})
        _hit = _probed.get(_probe_key)
        if _hit and _hit["verdict"] != "ok":
            st.warning(t("th.contract_bad", pct=f"{_hit['compliance']:.0%}",
                         n=_hit["detail"]["conforming"],
                         total=_hit["detail"]["answered"] or _hit["detail"]["asked"]))
            _wrote = _hit["detail"]["non_conforming"]
            if _wrote:
                show_df(pd.DataFrame(_wrote), hide_index=True)
            st.caption(t("th.contract_advice"))

        _go = st.button(t("th.run"), type="primary", key="btn_themes")
        _anyway = False
        if _hit and _hit["verdict"] != "ok":
            _anyway = st.button(t("th.contract_anyway"), key="btn_themes_anyway")

        if _go or _anyway:
            if not tmodel:
                st.error(t("run.need_model"))
            elif provider == LLM.GEMINI and not api_key:
                st.error(t("run.need_key"))
            elif not items:
                st.warning(t("app.no_data"))
            else:
                # 這個「模型＋框架」還沒探測過就先探一次。過關直接往下跑；
                # 不過關則停在這裡重繪，把警告與「仍要執行」顯示出來。
                # 使用者按了「仍要執行」（_anyway）時跳過探測，那是他的決定。
                if not _anyway and (_hit is None or _hit["key"] != _probe_key):
                    with st.spinner(t("th.contract_probing")):
                        try:
                            _c, _d = RT.probe_output_contract(
                                LLM.make_callable(endpoint(model=tmodel),
                                                  temperature=0.0),
                                FW.dimensions)
                            _v = RT.contract_verdict(_c, _d)
                        except Exception as e:
                            _c, _d, _v = 0.0, {
                                "asked": 0, "answered": 0, "conforming": 0,
                                "non_conforming": [], "valid_json": False,
                                "error": f"{type(e).__name__}: {e}"}, "unusable"
                    _probed[_probe_key] = {"key": _probe_key, "compliance": _c,
                                           "verdict": _v, "detail": _d}
                    st.session_state.th_probe = _probed
                    _hit = _probed[_probe_key]
                    if _v != "ok":
                        st.rerun()
                tcall = LLM.make_callable(endpoint(model=tmodel),
                                          temperature=0.4)
                bar, status = st.progress(0.0), st.empty()

                def _prog(stage, done, total, n):
                    status.info(f"{stage}  {done + 1}/{total}  (n={n})")
                    bar.progress(min(done / max(total, 1), 1.0))

                try:
                    themes, note, dbg = RT.induce_themes(
                        items, tcall,
                        chunk_size=int(chunk), min_size=int(min_sz),
                        on_progress=_prog,
                        analysis_lang=st.session_state.analysis_lang)
                    bar.progress(1.0)
                    st.session_state.themes = themes
                    st.session_state.theme_note = note
                    st.session_state.theme_debug = dbg
                    # 診斷要跟結果一起存下來。
                    #
                    # 要防的失效：一次歸納跑出 9 個主題，其中 7 個是 unassigned，
                    # 四個維度有三個掛零。要判斷那是「資料真的沒談到」還是
                    # 「模型沒照格式回答」，唯一的線索是 dbg 裡的
                    # unrecognised_dimensions——它記著模型原本到底寫了什麼。
                    # 但那份東西只在畫面上出現一次就沒了，隔週把 themes.json
                    # 載回來，已經無從判斷。跟編碼那邊的 provenance 是同一種病：
                    # 能解釋結果的證據，被丟在產生它的那一次執行裡。
                    with open(THEMES_PATH, "w", encoding="utf-8") as f:
                        json.dump({"themes": themes, "unassigned_note": note,
                                   "framework_id": FW.id,
                                   "generated": datetime.now().isoformat(),
                                   "source": endpoint(model=tmodel).describe(),
                                   "endpoint": endpoint(model=tmodel).provenance(
                                       temperature=0.4),
                                   "diagnostics": dbg,
                                   # 遵循度跟結果一起存：論文要報「模型在
                                   # N 個主題中有 M 個回傳了不合格的維度值」
                                   # 時，這個數字必須查得到出處。
                                   "output_contract": _hit},
                                  f, ensure_ascii=False, indent=2)
                    status.success(f"{len(themes)}")
                except Exception as e:
                    status.error(str(e))

        cl1, cl2 = st.columns(2)
        if cl1.button(t("th.load"), key="btn_load_themes"):
            try:
                with open(THEMES_PATH, "r", encoding="utf-8") as f:
                    d = json.load(f)
                st.session_state.themes = [S.migrate_theme(x, i + 1) for i, x
                                           in enumerate(d.get("themes", []))]
                st.session_state.theme_note = d.get("unassigned_note", "")
                # 載回來的診斷要一併還原，否則「為什麼這麼多 unassigned」
                # 這個問題在重新載入之後就再也答不出來了。
                if d.get("diagnostics"):
                    st.session_state.theme_debug = d["diagnostics"]
                if d.get("source"):
                    st.caption(f"`{d['source']}`  ·  {d.get('generated', '')}")
                st.success(str(len(st.session_state.themes)))
            except Exception as e:
                st.warning(str(e))
        if cl2.button(t("th.clear"), key="btn_clear_themes"):
            st.session_state.pop("themes", None)
            st.session_state.pop("theme_note", None)

        dbg = st.session_state.get("theme_debug")
        if dbg:
            with st.expander(t("th.debug")):
                st.json({k: v for k, v in dbg.items() if k != "dropped"})
                if dbg.get("dropped"):
                    show_df(pd.DataFrame(dbg["dropped"]), hide_index=True)
                if dbg.get("orphans"):
                    st.warning(t("th.orphans") + "\n\n- " +
                               "\n- ".join(dbg["orphans"]))
                # 模型寫了認不得的維度值。不列出來的話，介面上只看得到
                # 「未歸屬 +1」，查不出是模型的判斷還是它沒遵守格式。
                if dbg.get("unrecognised_dimensions"):
                    st.error(t("th.bad_dims",
                               n=len(dbg["unrecognised_dimensions"])))
                    show_df(pd.DataFrame(dbg["unrecognised_dimensions"]),
                            hide_index=True)

    themes = st.session_state.get("themes") or []

    with th2:
        if not themes:
            st.info(t("app.no_data"))
        else:
            cov = RT.coverage_report(themes, items)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric(t("th.tab2"), cov["theme_count"])
            m2.metric(t("th.coverage"), f"{cov['coverage'] * 100:.0f}%")
            m3.metric(t("th.unassigned_count"),
                      cov["themes_by_dimension"].get(S.UNASSIGNED, 0))
            m4.metric(t("th.thin"), len(cov["thin_themes"]))
            st.caption(t("th.coverage_note"))
            if cov["thin_themes"]:
                st.warning(t("th.thin_warn", ids=", ".join(cov["thin_themes"])))

            # 有維度一個主題都沒拿到，一定要講出來。
            #
            # 這是本工具最容易產生錯誤結論的地方：Gioia 圖表只畫得出有主題的
            # 維度，所以少一個維度時，圖看起來完全正常——研究者會直接讀成
            # 「受訪者沒有談到這個面向」，然後把這個「發現」寫進論文。
            # 它也可能只是模型漏看了。兩者的差別必須由研究者來判斷，
            # 前提是他知道有這件事。
            empty = [d for d in FW.dimensions
                     if not cov["themes_by_dimension"].get(d)]
            if empty:
                st.warning(t("th.empty_dims",
                             dims=", ".join(I.dim(d) for d in empty)))

            tdf = pd.DataFrame(RT.theme_table(themes, items))
            dims = st.multiselect(t("th.filter_dim"), FW.agg_dimensions,
                                  default=FW.agg_dimensions, format_func=I.dim,
                                  key="th_dimfilter")
            show_df(pretty(tdf[tdf[S.AGG_DIMENSION].isin(dims)],
                           dim_cols=[S.AGG_DIMENSION]), hide_index=True)

            note = st.session_state.get("theme_note")
            if note and note.lower() not in ("none", "無"):
                st.markdown(f"##### {t('th.unassigned_note')}")
                st.success(note)

            st.divider()
            st.markdown(f"##### {t('th.support')}")
            mat, speakers = RT.theme_case_matrix(themes, items)
            mdf = pd.DataFrame(mat)
            show_df(pretty(mdf, dim_cols=[S.AGG_DIMENSION]), hide_index=True)
            st.caption(t("th.support_note"))
            if HAS_PLOTLY and speakers:
                hm = mdf.set_index(S.THEME_ID)[speakers]
                heatmap(hm, t("th.support"), colorscale="Greens")

            st.divider()
            st.markdown(f"##### {t('th.by_code')}")
            xdf = pd.DataFrame(RT.theme_by_existing_code(themes, items)).fillna(0)
            show_df(pretty(xdf, dim_cols=[S.AGG_DIMENSION]), hide_index=True)
            st.caption(t("th.by_code_note"))

            un = RT.unassigned_items(themes, items)
            with st.expander(t("th.outside", n=len(un))):
                if un:
                    show_df(pretty(pd.DataFrame(un)[
                        [RT.GLOBAL_ID, S.RESPONDENT, S.TITLE, S.QUOTE]]),
                        hide_index=True)

    with th3:
        if not themes:
            st.info(t("app.no_data"))
        else:
            cf1, cf2 = st.columns(2)
            maxfo = cf1.slider(t("th.max_fo"), 2, 12, 5, key="th_maxfo")
            show_sp = cf2.checkbox(t("th.show_speaker"), True, key="th_sp")
            svg = RT.render_data_structure_svg(
                themes, items, max_first_order_per_theme=int(maxfo),
                show_speaker=show_sp,
                dim_label=lambda d: I.dim(d),
                relation_label=lambda r: I.relation(r))
            if HAS_COMPONENTS:
                h = int(re.search(r'height="(\d+)"', svg).group(1)) + 30
                components.html(f'<div style="background:#fff">{svg}</div>',
                                height=min(h, 2400), scrolling=True)
            st.download_button(t("th.download_svg"), svg.encode("utf-8"),
                               file_name=f"data_structure_{datetime.now():%Y%m%d}.svg",
                               mime="image/svg+xml", **WIDE)
            st.caption(t("th.svg_note"))

    with th4:
        if not themes:
            st.info(t("app.no_data"))
        else:
            tbuf = io.BytesIO()
            with pd.ExcelWriter(tbuf, engine="openpyxl") as xw:
                pd.DataFrame(RT.theme_table(themes, items)).to_excel(
                    xw, sheet_name=t("sheet.themes"), index=False)
                pd.DataFrame(RT.theme_case_matrix(themes, items)[0]).to_excel(
                    xw, sheet_name=t("sheet.theme_case"), index=False)
                pd.DataFrame(RT.theme_by_existing_code(themes, items)).fillna(0) \
                    .to_excel(xw, sheet_name=t("sheet.theme_code"), index=False)
                idx = RT.index_items(items)
                fo = [{S.THEME_ID: th[S.THEME_ID],
                       S.AGG_DIMENSION: th[S.AGG_DIMENSION],
                       S.THEME_NAME: th[S.THEME_NAME], RT.GLOBAL_ID: gid,
                       S.RESPONDENT: idx[gid][S.RESPONDENT],
                       S.TITLE: idx[gid][S.TITLE], S.QUOTE: idx[gid][S.QUOTE],
                       S.FULL_TEXT: idx[gid][S.FULL_TEXT],
                       "codes": "/".join(idx[gid][RT.EXISTING_CODES])}
                      for th in themes for gid in th[S.MEMBER_IDS] if gid in idx]
                pd.DataFrame(fo).to_excel(xw, sheet_name=t("sheet.first_order"),
                                          index=False)
                pd.DataFrame(RT.unassigned_items(themes, items)).to_excel(
                    xw, sheet_name=t("sheet.unassigned_segs"), index=False)
                c = RT.coverage_report(themes, items)
                pd.DataFrame([{k: (v if not isinstance(v, (list, dict)) else str(v))
                               for k, v in c.items()}]).to_excel(
                    xw, sheet_name=t("sheet.coverage"), index=False)
            tbuf.seek(0)
            st.download_button(f"{t('common.download')} — {t('tab.themes')}", tbuf,
                               file_name=f"themes_{datetime.now():%Y%m%d}.xlsx",
                               **WIDE, type="primary")
            st.caption(t("th.export_note"))


# =====================================================================
# 10. 詞庫誘導
# =====================================================================
def lexicon_path():
    """
    詞庫是「框架 × 語言」相依的資源，檔名必須帶兩者。

    但**內建 RI 框架的中文詞庫沿用原本的檔名** `tacit_lexicon_zh.json`：
    它是隨程式一起發布的資產，改名等於讓既有專案全部找不到自己的詞庫。

    漏掉這個對應的後果比「檔案找不到」嚴重得多：程式改建一份
    空詞庫，接著任何一次「合併特徵詞」或「重新載入」都會把那份空的存回
    磁碟，於是 239 個概念詞與 17 個句式模板悄悄消失，詞典稽核整頁歸零。
    """
    lang = st.session_state.analysis_lang
    if lang == S.ANALYSIS_LANG_AUTO:
        lang = "zh-Hant"
    if FW.id == F.DEFAULT_FRAMEWORK_ID and str(lang).startswith("zh"):
        legacy = os.path.join(LEXICON_DIR, RL.DEFAULT_LEXICON_PATH)
        if os.path.exists(legacy):
            return legacy
    return os.path.join(LEXICON_DIR, f"lexicon_{FW.id}_{lang}.json")


with tab_lex:
    st.caption(t("lx.stance"))
    lex_path = lexicon_path()
    if "lexicon_path" not in st.session_state or \
            st.session_state.lexicon_path != lex_path:
        st.session_state.lexicon_path = lex_path
        try:
            st.session_state.lexicon = RL.load_lexicon(lex_path)
        except Exception:
            st.session_state.lexicon = RL.blank_lexicon(
                st.session_state.analysis_lang
                if st.session_state.analysis_lang != S.ANALYSIS_LANG_AUTO
                else "zh-Hant")
            st.info(t("lx.not_found", path=os.path.basename(lex_path)))
    lex = st.session_state.lexicon

    # 詞庫的概念詞是按維度分層的，換了框架就對不上。不符時 migrate_lexicon
    # 會把認不得的維度整批丟掉，得到一份結構完整但內容全空的詞庫——
    # 不報錯，只是詞典編碼器一個碼都標不出來。這裡把它攤在檯面上。
    _mm = RL.framework_mismatch(lex)
    if _mm:
        st.error(t("lx.framework_mismatch",
                   lex_fw=_mm["lexicon_framework"], cur=_mm["active_framework"]))
        st.caption(t("lx.framework_mismatch_how"))

    stats = {r["code"]: r["term_count"] for r in RL.lexicon_stats(lex)}
    cols = st.columns(min(len(S.CODES), 8) or 1)
    for i, c in enumerate(S.CODES[:8]):
        cols[i].metric(c, stats.get(c, 0))

    # 斷詞後端決定了這整個頁籤的品質上限。後備演算法只靠統計，
    # 沒有語言知識，切錯是必然的——使用者必須知道自己在看什麼等級的結果。
    _backend = RL.Segmenter().backend
    if _backend == "ngram":
        st.warning(t("lx.backend_fallback"))
        with st.expander(t("lx.backend_how")):
            st.markdown(t("lx.backend_install"))
    else:
        st.caption(t("lx.backend_ok", name=_backend))

    lx1, lx2, lx3, lx4 = st.tabs([t("lx.tab1"), t("lx.tab2"),
                                  t("lx.tab3"), t("lx.tab4")])

    with lx1:
        st.caption(t("lx.discover_note"))
        c1, c2, c3, c4 = st.columns(4)
        min_freq = c1.number_input(t("lx.min_freq"), 2, 50, 3, key="lx_freq")
        min_pmi = c2.number_input(t("lx.min_pmi"), 0.0, 10.0, 1.5, 0.1, key="lx_pmi")
        min_ent = c3.number_input(t("lx.min_entropy"), 0.0, 3.0, 0.8, 0.1, key="lx_ent")
        max_n = c4.number_input(t("lx.max_n"), 2, 8, 6, key="lx_n")

        if st.button(t("lx.run_discover"), type="primary", key="btn_discover"):
            texts = [RL.segment_text(s) for r in st.session_state.records
                     for s in r.get(S.SEGMENTS, [])]
            texts = [x for x in texts if x]
            if not texts:
                st.warning(t("app.no_data"))
            else:
                with st.spinner(str(len(texts))):
                    st.session_state.discovered = RL.discover_terms(
                        texts, max_n=int(max_n), min_freq=int(min_freq),
                        min_pmi=float(min_pmi), min_entropy=float(min_ent))

        disc = st.session_state.get("discovered")
        if disc:
            show_df(pd.DataFrame(disc), hide_index=True)
            picks = st.multiselect(t("lx.pick_force"), [r["term"] for r in disc],
                                   key="lx_picks")
            if st.button(t("lx.add_force"), key="btn_force"):
                for w in picks:
                    if w not in lex[RL.FORCE_TERMS]:
                        lex[RL.FORCE_TERMS].append(w)
                RL.save_lexicon(lex, lex_path)
                st.success(str(len(lex[RL.FORCE_TERMS])))
        elif disc == []:
            st.info(t("lx.no_terms"))

    with lx2:
        st.caption(t("lx.induce_note"))
        c1, c2, c3 = st.columns(3)
        min_count = c1.number_input(t("lx.min_count"), 2, 50, 3, key="lx_mc")
        top_n = c2.number_input(t("lx.top_n"), 5, 100, 25, key="lx_tn")
        min_z = c3.number_input(t("lx.merge_z"), 0.0, 10.0, 2.0, 0.1, key="lx_z")

        if st.button(t("lx.run_induce"), type="primary", key="btn_induce"):
            ct = RL.code_texts_from_records(st.session_state.records)
            if sum(len(v) for v in ct.values()) == 0:
                st.warning(t("app.no_data"))
            else:
                with st.spinner("…"):
                    st.session_state.induced = RL.induce_features(
                        ct, lexicon=lex, min_count=int(min_count), top_n=int(top_n),
                        discover_kwargs={"min_freq": 3, "min_pmi": 1.0,
                                         "min_entropy": 0.5})
                    st.session_state.induce_counts = {c: len(v)
                                                      for c, v in ct.items()}

        ind = st.session_state.get("induced")
        if ind:
            counts = st.session_state.get("induce_counts", {})
            sel = st.selectbox(t("lx.select_code"),
                               [c for c in S.CODES],
                               format_func=lambda c: f"{c}  {I.code_label(c)}  "
                                                     f"(n={counts.get(c, 0)})",
                               key="lx_sel")
            rows = ind.get(sel, [])
            if rows:
                show_df(pd.DataFrame(rows), hide_index=True)
                if HAS_PLOTLY:
                    top = pd.DataFrame(rows).head(15).sort_values("z")
                    fig = px.bar(top, x="z", y="term", orientation="h",
                                 color="z", color_continuous_scale="Teal")
                    fig.update_layout(height=max(280, 26 * len(top) + 120),
                                      margin=dict(l=10, r=10, t=30, b=10),
                                      title=I.code_label(sel))
                    st.plotly_chart(fig, **WIDE)
            st.divider()
            preview = RL.merge_into_lexicon(lex, ind, min_z=float(min_z),
                                            max_per_code=15, dry_run=True)
            st.markdown(f"**{t('lx.merge_preview', n=len(preview))}**")
            if preview:
                show_df(pretty(pd.DataFrame(preview), code_cols=["code"]),
                        hide_index=True)
                st.warning(t("lx.merge_warn"))
                if st.button(t("lx.merge_go"), key="btn_merge"):
                    added = RL.merge_into_lexicon(lex, ind, min_z=float(min_z),
                                                  max_per_code=15)
                    RL.save_lexicon(lex, lex_path)
                    st.success(str(len(added)))
                    st.rerun()

    with lx3:
        st.caption(t("lx.compare_note"))
        c1, c2, c3 = st.columns(3)
        thr = c1.number_input(t("lx.threshold"), 0.5, 10.0, 1.0, 0.5, key="lx_thr")
        neg_win = c2.number_input(t("lx.neg_window"), 2, 20, 6, key="lx_neg")
        miss_thr = c3.number_input(t("lx.miss_threshold"), 0.5, 10.0, 2.0, 0.5,
                                   key="lx_miss")
        if st.button(t("lx.run_compare"), type="primary", key="btn_compare"):
            if not st.session_state.records:
                st.warning(t("app.no_data"))
            else:
                coder = RL.DictionaryCoder(lex, neg_window=int(neg_win),
                                           threshold=float(thr))
                with st.spinner("…"):
                    pc, sm, sr = RL.compare_coders(st.session_state.records, coder)
                    over, miss = RL.audit_llm_coding(sr, miss_threshold=float(miss_thr))
                st.session_state.cmp = (pc, sm, over, miss)

        if "cmp" in st.session_state:
            pc, sm, over, miss = st.session_state.cmp
            m1, m2, m3 = st.columns(3)
            m1.metric(t("common.segment"), sm["segments"])
            m2.metric(t("lx.overall_kappa"), sm["overall_kappa"])
            m3.metric(t("common.codes"), f"{sm['llm_total']} / {sm['dict_total']}")
            st.markdown(f"##### {t('lx.per_code')}")
            show_df(pretty(pd.DataFrame(pc), code_cols=["code"]), hide_index=True)
            st.caption(t("lx.per_code_note"))
            a1, a2 = st.tabs([t("lx.over", n=len(over)), t("lx.under", n=len(miss))])
            with a1:
                st.caption(t("lx.over_note"))
                show_df(pretty(pd.DataFrame(over), code_cols=["code"])
                        if over else pd.DataFrame(), hide_index=True)
            with a2:
                st.caption(t("lx.under_note"))
                show_df(pretty(pd.DataFrame(miss), code_cols=["code"])
                        if miss else pd.DataFrame(), hide_index=True)

    with lx4:
        st.caption(f"`{os.path.basename(lex_path)}`  ·  "
                   f"{RL.lexicon_language(lex)}")
        if st.button(t("lx.reload"), key="btn_reload_lex"):
            try:
                st.session_state.lexicon = RL.load_lexicon(lex_path)
                st.rerun()
            except Exception as e:
                st.warning(str(e))
        show_df(pretty(pd.DataFrame(RL.lexicon_stats(lex)),
                       dim_cols=[S.DIMENSION]), hide_index=True)
        layer = st.selectbox(t("lx.layer"),
                             [RL.CONCEPT_TERMS, RL.FORCE_TERMS, RL.NEGATORS,
                              RL.PIVOTS, RL.INTENSIFIERS, RL.REPORTED_SPEECH,
                              RL.PATTERNS], key="lx_layer")
        if layer == RL.CONCEPT_TERMS:
            rows = [{S.DIMENSION: d, S.POLARITY: p, "term": w}
                    for d in FW.dimensions
                    for p in (FW.polarity_values or ["-"])
                    for w in lex[RL.CONCEPT_TERMS].get(d, {}).get(p, [])]
            show_df(pretty(pd.DataFrame(rows), dim_cols=[S.DIMENSION]),
                    hide_index=True)
        elif layer == RL.PATTERNS:
            rows = [{"id": k, S.DIMENSION: v[S.DIMENSION],
                     S.POLARITY: v.get(S.POLARITY), "regex": v[RL.PATTERN_REGEX],
                     "note": RL.pattern_note(v, I.get_lang())}
                    for k, v in lex[RL.PATTERNS].items()]
            show_df(pretty(pd.DataFrame(rows), dim_cols=[S.DIMENSION]),
                    hide_index=True)
            st.caption(t("lx.pattern_note"))
        else:
            show_df(pd.DataFrame({layer: lex.get(layer, [])}), hide_index=True)
        st.download_button(f"{t('common.download')} JSON",
                           json.dumps(lex, ensure_ascii=False, indent=2)
                           .encode("utf-8"),
                           file_name=os.path.basename(lex_path),
                           mime="application/json", **WIDE)


# =====================================================================
# 11. 信度檢定
# =====================================================================
with tab_irr:
    recs = st.session_state.records
    with st.expander(t("ir.trap1")):
        st.markdown(t("ir.trap1_body"))
    with st.expander(t("ir.trap2")):
        st.markdown(t("ir.trap2_body"))

    ir1, ir2, ir3, ir4 = st.tabs([t("ir.tab1"), t("ir.tab2"),
                                  t("ir.tab3"), t("ir.tab4")])

    # ---- 抽樣框
    with ir1:
        # 兩位人類編碼者之間的一致性完全不需要模型，也不需要先有分析結果。
        # 這個頁籤若要求先載入紀錄，等於逼一個只想做傳統雙人編碼信度的
        # 研究者先用模型編一遍——那跟這套工具的立場互相矛盾。
        src = st.radio(
            t("ir.source"), ["records", "files"], horizontal=True,
            index=0 if recs else 1,
            format_func=lambda v: (t("ir.source_records") if v == "records"
                                   else t("ir.source_files")),
            help=t("ir.source_help"), key="irr_src")
        human_only = src == "files"
        # 這三個名字一定要跟側邊欄的區域變數分開。app.py 是一支從頭跑到尾的
        # 指令稿，所有名字都在同一個模組命名空間裡：側邊欄的框架選單用
        # `format_func=lambda i: names.get(i, i)`，那個 lambda 事後才被呼叫，
        # 查的是「當下」的 names。這裡如果叫 names，框架選單的顯示函式就會
        # 拿到一個 list 然後 AttributeError。
        have, missing, resp_names = {}, [], []
        if human_only:
            own = {}
            for f in (st.file_uploader(t("ir.upload_own"), type=["docx"],
                                       accept_multiple_files=True,
                                       key="irr_own") or []):
                try:
                    own[os.path.splitext(f.name)[0][:40]] = read_docx(f)
                except Exception as e:                        # noqa: BLE001
                    st.warning(f"{f.name}: {e}")
            have = own
            if own:
                st.success(t("ir.human_only_ready", n=len(own)))
        elif not recs:
            st.info(t("app.no_data"))
        else:
            # 逐字稿在分析當下就跟著紀錄一起存下來了，正常情況不需要重新上傳。
            # 只有 v1 舊檔（當年沒保存原文）才會有缺口，這時才請使用者補。
            have = available_transcripts(recs)
            missing = missing_transcripts(recs)
            resp_names = [r.get(S.RESPONDENT, "") for r in recs]

            if not missing:
                st.success(t("ir.transcripts_ready", n=len(recs)))
            else:
                st.warning(t("ir.transcripts_missing",
                             n=len(missing), have=len(recs) - len(missing)))
                st.caption(t("ir.upload_note"))
                irr_files = st.file_uploader(t("ir.upload"), type=["docx"],
                                             accept_multiple_files=True,
                                             key="irr_up")
                if irr_files:
                    st.markdown(f"##### {t('ir.map_file')}")
                    mapping = {}
                    for f in irr_files:
                        stem = os.path.splitext(f.name)[0]
                        guess = next((n for n in missing if n and n in stem),
                                     None) or next(
                            (n for n in resp_names if n and n in stem), None)
                        idx0 = (resp_names.index(guess)
                                if guess in resp_names else 0)
                        mapping[f.name] = st.selectbox(f.name, resp_names,
                                                       index=idx0,
                                                       key=f"map_{f.name}")
                    if st.button(t("ir.attach"), key="btn_attach"):
                        tmap = dict(st.session_state.get("transcripts") or {})
                        for f in irr_files:
                            try:
                                tmap[mapping[f.name]] = read_docx(f)
                            except Exception as e:
                                st.warning(f"{f.name}: {e}")
                        st.session_state.transcripts = tmap
                        st.rerun()

        c1, c2 = st.columns(2)
        mn = c1.number_input(t("ir.unit_min"), 5, 60, 15, key="irr_min")
        mx = c2.number_input(t("ir.unit_max"), 100, 1000, 400, 50, key="irr_max")

        if st.button(t("ir.build"), type="primary", key="btn_frame",
                     disabled=not have):
            if not human_only:
                # 逐字稿同時供編碼複核頁籤的引文驗證使用。純人工模式不寫回去：
                # 那些檔案跟載入的紀錄沒有關係，蓋掉會讓複核頁籤對錯文本。
                st.session_state.transcripts = dict(have)
            frame, diag = RIRR.build_frame([] if human_only else recs, have,
                                           min_len=int(mn), max_len=int(mx))
            st.session_state.irr_frame = frame
            st.session_state.irr_diag = diag
            st.session_state.irr_human_only = human_only
            if missing and not human_only:
                st.info(t("ir.built_partial", n=len(missing)))

        diag = st.session_state.get("irr_diag")
        if diag:
            m1, m2, m3 = st.columns(3)
            m1.metric(t("ir.total_units"), diag["total_units"])
            m2.metric(t("ir.coded_units"), diag["ai_coded_units"])
            m3.metric(t("ir.uncoded_units"), diag["uncoded_units"])
            if st.session_state.get("irr_human_only"):
                st.caption(t("ir.human_only_frame"))
            elif diag["uncoded_units"] == 0:
                st.error(t("ir.no_uncoded"))
            if diag.get("unmatched_quotes"):
                st.warning(t("ir.unmatched") + "\n\n" +
                           json.dumps(diag["unmatched_quotes"], ensure_ascii=False))
            frame = st.session_state.get("irr_frame") or []
            show_df(pretty(pd.DataFrame(
                [{k: v for k, v in f.items() if k != S.AI_CODES}
                 for f in frame]).head(200)), hide_index=True)

    # ---- 抽樣與盲測
    with ir2:
        frame = st.session_state.get("irr_frame") or []
        if not frame:
            st.info(t("app.no_data"))
        else:
            # 抽樣框裡沒有任何模型標記時，分層就無從談起——這兩個參數是用來
            # 平衡各個碼與未標記單元的，全部未標記時設定它們只會誤導。
            plain = bool(st.session_state.get("irr_human_only"))
            c1, c2, c3, c4 = st.columns(4)
            n_samp = c1.number_input(t("ir.n_sample"), 20, 500, 100, 10, key="irr_n")
            seed = c2.number_input(t("ir.seed"), 0, 9999, 42,
                                   help=t("ir.seed_help"), key="irr_seed")
            min_pc = c3.number_input(t("ir.min_per_code"), 0, 20, 4, key="irr_mpc",
                                     disabled=plain)
            un_share = c4.slider(t("ir.unmarked_share"), 0.0, 0.7, 0.35, 0.05,
                                 key="irr_us", disabled=plain)
            if plain:
                st.caption(t("ir.human_only_sample"))
            coders_raw = st.text_input(t("ir.coders"), "coder_a, coder_b",
                                       key="irr_coders")
            note = st.text_input(t("common.notes"), "", key="irr_note")

            if st.button(t("ir.create"), type="primary", key="btn_sample"):
                coders = [c.strip() for c in coders_raw.split(",") if c.strip()]
                if len(coders) < 2:
                    st.error(t("ir.need_two"))
                else:
                    samp = RIRR.stratified_sample(
                        frame, n=int(n_samp), seed=int(seed),
                        min_per_code=int(min_pc), unmarked_share=float(un_share))
                    sess = RIRR.create_session(samp, coders, seed=int(seed),
                                               note=note)
                    st.session_state.irr_session = sess
                    with open(IRR_PATH, "w", encoding="utf-8") as f:
                        json.dump(sess, f, ensure_ascii=False, indent=2)
                    st.success(sess[S.SESSION_ID])

            if st.button(t("ir.load_session"), key="btn_load_irr"):
                try:
                    with open(IRR_PATH, "r", encoding="utf-8") as f:
                        st.session_state.irr_session = json.load(f)
                    st.success(st.session_state.irr_session[S.SESSION_ID])
                except Exception as e:
                    st.warning(str(e))

            sess = st.session_state.get("irr_session")
            if sess:
                strat = Counter(u[S.STRATUM] for u in sess[S.UNITS])
                st.markdown(f"##### {t('ir.strata')}")
                show_df(pd.DataFrame(
                    [{"stratum": (I.special(k) if k == S.STRATUM_UNMARKED else k),
                      "n": v} for k, v in sorted(strat.items(),
                                                 key=lambda x: -x[1])]),
                    hide_index=True)

                st.markdown(f"##### {t('ir.sheets')}")
                st.caption(t("ir.sheet_note"))
                cols = st.columns(len(sess[S.CODERS]))
                for i, coder in enumerate(sess[S.CODERS]):
                    rows = RIRR.coding_sheet_rows(sess, coder)
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
                        pd.DataFrame(rows).to_excel(
                            xw, sheet_name=t("sheet.coding_sheet"), index=False)
                        pd.DataFrame([{"code": c, "meaning": I.code_label(c)}
                                      for c in S.CODES]).to_excel(
                            xw, sheet_name=t("sheet.code_definitions"), index=False)
                    buf.seek(0)
                    cols[i].download_button(
                        f"{t('common.download')} — {coder}", buf,
                        file_name=f"irr_{sess[S.SESSION_ID]}_{coder}.xlsx",
                        **WIDE, key=f"dl_{coder}")

    # ---- 回收
    with ir3:
        sess = st.session_state.get("irr_session")
        if not sess:
            st.info(t("app.no_data"))
        else:
            valid = {u[S.UNIT_ID] for u in sess[S.UNITS]}
            for coder in sess[S.CODERS]:
                with st.container(border=True):
                    done = len(sess[S.HUMAN_CODINGS].get(coder) or {})
                    st.markdown(f"**{coder}** — " +
                                t("ir.received", done=done, total=len(valid)))
                    up = st.file_uploader(t("ir.upload_sheet", who=coder),
                                          type=["xlsx", "csv"], key=f"irr_in_{coder}")
                    if up is not None and st.button(t("ir.import", who=coder),
                                                    key=f"btn_in_{coder}"):
                        try:
                            df = (pd.read_csv(up) if up.name.endswith(".csv")
                                  else pd.read_excel(up, sheet_name=0))
                            parsed = RIRR.parse_coding_sheet(
                                df.fillna("").to_dict("records"), valid)
                            sess[S.HUMAN_CODINGS][coder] = parsed
                            with open(IRR_PATH, "w", encoding="utf-8") as f:
                                json.dump(sess, f, ensure_ascii=False, indent=2)
                            st.success(t("ir.imported", n=len(parsed),
                                         m=sum(1 for v in parsed.values() if v)))
                        except Exception as e:
                            st.error(str(e))

            st.divider()
            st.markdown(f"##### {t('ir.code_here')}")
            who = st.selectbox(t("ir.as_coder"), sess[S.CODERS], key="irr_who")
            npages = max(1, (len(sess[S.UNITS]) + 9) // 10)
            page = st.number_input(t("ir.page"), 1, npages, 1, key="irr_pg")
            cur = sess[S.HUMAN_CODINGS].setdefault(who, {})
            for u in sess[S.UNITS][(page - 1) * 10: page * 10]:
                with st.container(border=True):
                    st.markdown(f"`{u[S.UNIT_ID]}`  {u[S.TEXT]}")
                    cur[u[S.UNIT_ID]] = st.multiselect(
                        t("common.codes"), S.CODES,
                        default=cur.get(u[S.UNIT_ID], []),
                        key=f"code_{who}_{u[S.UNIT_ID]}",
                        format_func=lambda c: f"{c}  {I.code_label(c)}",
                        label_visibility="collapsed")
            if st.button(t("ir.save_page"), key="btn_save_manual"):
                with open(IRR_PATH, "w", encoding="utf-8") as f:
                    json.dump(sess, f, ensure_ascii=False, indent=2)
                st.success("ok")

            # ---- 人工編碼 → 分析紀錄
            # 沒有這條路的話，編碼表收回來只算了信度就停住，交叉表、共現、
            # 跨個案矩陣、詞彙探勘這些不需要模型的引擎讀不到它。
            st.divider()
            st.markdown(f"##### {t('ir.to_records')}")
            st.caption(t("ir.to_records_note"))
            filled = [c for c in sess[S.CODERS]
                      if any((sess[S.HUMAN_CODINGS].get(c) or {}).values())]
            if not filled:
                st.info(t("ir.to_records_need"))
            else:
                rc1, rc2 = st.columns([2, 1])
                src_coder = rc1.selectbox(t("ir.to_records_who"), filled,
                                          key="irr_rec_who")
                replace = rc2.checkbox(t("ir.to_records_replace"), value=False,
                                       key="irr_rec_replace",
                                       help=t("ir.to_records_replace_help"))
                if st.button(t("ir.to_records_go"), type="primary",
                             key="btn_to_records"):
                    new_recs = RIRR.records_from_codings(sess, src_coder)
                    if not new_recs:
                        st.warning(t("ir.to_records_empty"))
                    else:
                        cur_recs = [] if replace else list(st.session_state.records)
                        taken = {r.get(S.RESPONDENT) for r in cur_recs}
                        added = [r for r in new_recs
                                 if r[S.RESPONDENT] not in taken]
                        st.session_state.records = cur_recs + added
                        st.success(t("ir.to_records_done",
                                     n=len(added),
                                     m=sum(len(r[S.SEGMENTS]) for r in added),
                                     who=src_coder))
                        if len(added) < len(new_recs):
                            st.caption(t("ir.to_records_skipped",
                                         n=len(new_recs) - len(added)))

    # ---- 報表
    with ir4:
        sess = st.session_state.get("irr_session")
        if not sess:
            st.info(t("app.no_data"))
        else:
            codings = {k: v for k, v in sess[S.HUMAN_CODINGS].items() if v}
            ai_coding = {u[S.UNIT_ID]: u.get(S.AI_CODES, []) for u in sess[S.UNITS]}
            pool = dict(codings)
            all_coders = list(codings)
            # 純人工模式的單元一個模型碼都沒有，把 AI 列進來只會得到一份
            # 「完全一致」的假報表（雙方都是空的）。
            if not st.session_state.get("irr_human_only"):
                pool["AI"] = ai_coding
                all_coders = all_coders + ["AI"]

            if not codings:
                st.info(t("ir.no_codings"))
            else:
                c1, c2 = st.columns(2)
                na = c1.selectbox(t("ir.coder_a"), all_coders, 0, key="irr_a")
                nb = c2.selectbox(t("ir.coder_b"), all_coders,
                                  min(1, len(all_coders) - 1), key="irr_b")
                if na == nb:
                    st.warning(t("ir.pick_two"))
                else:
                    ca, cb = pool[na], pool[nb]
                    uids = [u[S.UNIT_ID] for u in sess[S.UNITS]
                            if u[S.UNIT_ID] in ca and u[S.UNIT_ID] in cb]
                    if not uids:
                        st.warning(t("ir.no_common"))
                    else:
                        st.caption(t("ir.common_units", n=len(uids)))
                        pk = RIRR.pooled_kappa(ca, cb, uids)
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric(t("stat.agreement"), pk[RIRR.AGREEMENT])
                        m2.metric(t("stat.kappa"), pk[RIRR.KAPPA])
                        m3.metric(t("stat.pabak"), pk[RIRR.PABAK])
                        m4.metric(t("stat.ac1"), pk[RIRR.AC1])
                        v = RIRR.interpret(pk[RIRR.KAPPA], pk[RIRR.PABAK],
                                           pk[RIRR.AC1], pk[RIRR.PREVALENCE_INDEX])
                        if v["is_paradox"]:
                            st.warning(t("ir.paradox", pabak=pk[RIRR.PABAK],
                                         ac1=pk[RIRR.AC1]))
                        else:
                            st.success(t("ir.consistent", pabak=pk[RIRR.PABAK],
                                         ac1=pk[RIRR.AC1]))
                        st.metric(t("ir.exact"),
                                  RIRR.exact_set_agreement(ca, cb, uids))

                        st.markdown(f"##### {t('lx.per_code')}")
                        pcdf = pd.DataFrame(RIRR.per_code_agreement(ca, cb, uids))
                        pcdf[t("stat.alpha")] = [
                            RIRR.krippendorff_alpha({na: ca, nb: cb}, uids, c)
                            for c in S.CODES]
                        show_df(pretty(pcdf, code_cols=["code"]), hide_index=True)
                        st.caption(t("ir.sparse_code_note"))
                        if HAS_PLOTLY:
                            kk = pcdf.dropna(subset=[RIRR.KAPPA])
                            if not kk.empty:
                                long = kk.melt(id_vars="code",
                                               value_vars=[RIRR.KAPPA, RIRR.PABAK,
                                                           RIRR.AC1],
                                               var_name="coef", value_name="v")
                                fig = px.bar(long, x="code", y="v", color="coef",
                                             barmode="group", range_y=[-1, 1])
                                fig.add_hline(y=0.6, line_dash="dot")
                                fig.update_layout(height=380,
                                                  margin=dict(l=10, r=10, t=40, b=10))
                                st.plotly_chart(fig, **WIDE)

                        st.markdown(f"##### {t('ir.confusion')}")
                        labels, mat = RIRR.dimension_confusion(ca, cb, uids)
                        disp = [I.dim(l) if l != S.NONE_LABEL else I.special(l)
                                for l in labels]
                        cm = pd.DataFrame([[mat[r][c] for c in labels]
                                           for r in labels],
                                          index=[f"{na}: {d}" for d in disp],
                                          columns=[f"{nb}: {d}" for d in disp])
                        show_df(cm)

                        if FW.has_polarity:
                            st.markdown(f"##### {t('ir.polarity_agree')}")
                            show_df(pretty(pd.DataFrame(
                                RIRR.polarity_confusion(ca, cb, uids)),
                                dim_cols=[S.DIMENSION]), hide_index=True)
                            st.caption(t("ir.polarity_note"))

                        st.markdown(f"##### {t('ir.disagreements')}")
                        dis = RIRR.disagreement_list(sess, pool, na, nb)
                        show_df(pd.DataFrame(dis) if dis else pd.DataFrame(),
                                hide_index=True)

                        # 純人工模式的抽樣框裡沒有模型編碼，precision / recall
                        # 沒有對象可以算
                        if na != "AI" and nb != "AI" \
                                and not st.session_state.get("irr_human_only"):
                            st.divider()
                            st.markdown(f"##### {t('ir.ai_pr')}")
                            ref = st.selectbox(t("ir.ai_pr_ref"), [na, nb],
                                               key="irr_ref")
                            show_df(pretty(pd.DataFrame(
                                RIRR.recall_estimate(sess, pool[ref])),
                                code_cols=["code"]), hide_index=True)
                            st.caption(t("ir.ai_pr_note"))

                        ibuf = io.BytesIO()
                        with pd.ExcelWriter(ibuf, engine="openpyxl") as xw:
                            pd.DataFrame([{S.SESSION_ID: sess[S.SESSION_ID],
                                           S.SEED: sess[S.SEED],
                                           "coder_a": na, "coder_b": nb,
                                           "common_units": len(uids), **pk}]) \
                                .to_excel(xw, sheet_name=t("sheet.overview"),
                                          index=False)
                            pcdf.to_excel(xw, sheet_name=t("sheet.agreement"),
                                          index=False)
                            cm.to_excel(xw, sheet_name=t("sheet.confusion"))
                            (pd.DataFrame(dis) if dis
                             else pd.DataFrame({"-": []})).to_excel(
                                xw, sheet_name=t("sheet.disagreements"), index=False)
                            pd.DataFrame(RIRR.recall_estimate(sess, ca)).to_excel(
                                xw, sheet_name=t("sheet.ai_reliability"), index=False)
                        ibuf.seek(0)
                        st.download_button(t("ir.download_report"), ibuf,
                                           file_name=f"irr_{sess[S.SESSION_ID]}.xlsx",
                                           **WIDE, type="primary")


# =====================================================================
# 12. 匯出
# =====================================================================
def build_excel(records):
    long_df = A.build_long_df(records)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        pretty(long_df, code_cols=[A.CODE], dim_cols=[S.DIMENSION]).to_excel(
            xw, sheet_name=t("sheet.long_table"), index=False)
        pretty(pd.DataFrame(A.coverage_report(records))).to_excel(
            xw, sheet_name=t("sheet.data_health"), index=False)
        rows = []
        for r in records:
            d = r.get(S.DESCRIPTORS, {})
            rows.append({t("common.respondent"): r.get(S.RESPONDENT, ""),
                         **{I.descriptor(k): I.descriptor_value(d.get(k, S.UNSPECIFIED))
                            for k in S.DESCRIPTOR_KEYS},
                         I.descriptor(S.DESCRIPTOR_BASIS): d.get(S.DESCRIPTOR_BASIS, ""),
                         t("common.summary"): r.get(S.SUMMARY, "")})
        pd.DataFrame(rows).to_excel(xw, sheet_name=t("sheet.descriptors"),
                                    index=False)
        if not long_df.empty:
            for k in S.DESCRIPTOR_KEYS:
                ct, pct = A.crosstab_by_descriptor(long_df, k)
                if ct.empty:
                    continue
                sheet = f"{t('sheet.crosstab')} {I.descriptor(k)}"[:31]
                ct.to_excel(xw, sheet_name=sheet, startrow=1)
                pct.to_excel(xw, sheet_name=sheet, startrow=ct.shape[0] + 5)
            cnt, jac, tot = A.cooccurrence(records)
            cnt.to_excel(xw, sheet_name=t("sheet.cooc_count"))
            jac.to_excel(xw, sheet_name=t("sheet.cooc_jaccard"))
            pairs = A.cooccurrence_pairs(cnt, tot, top_n=100)
            if not pairs.empty:
                pairs.to_excel(xw, sheet_name=t("sheet.cooc_pairs"), index=False)
            A.case_matrix(long_df).to_excel(xw, sheet_name=t("sheet.case_count"))
            A.case_matrix(long_df, True).to_excel(xw, sheet_name=t("sheet.case_pct"))
            if FW.has_polarity:
                per_dim, overall = A.polarity_balance(long_df)
                pretty(per_dim, dim_cols=[S.DIMENSION]).to_excel(
                    xw, sheet_name=t("sheet.polarity_dim"), index=False)
                pretty(overall).to_excel(xw, sheet_name=t("sheet.polarity_overall"),
                                         index=False)
        pd.DataFrame([{"code": c, "meaning": I.code_label(c)}
                      for c in S.CODES]).to_excel(
            xw, sheet_name=t("sheet.code_ref"), index=False)
    buf.seek(0)
    return buf


def build_word(records):
    long_df = A.build_long_df(records)
    doc = docx.Document()
    doc.add_heading(t("export.report_title"), 0)
    doc.add_paragraph(f"{t('side.framework')}: {FW.name()} — {FW.citation}")
    doc.add_paragraph(f"{t('export.generated')}: {datetime.now():%Y-%m-%d %H:%M}   "
                      f"{t('export.sample')}: {len(records)}")

    doc.add_heading(t("export.section_cross"), level=1)
    if long_df.empty:
        doc.add_paragraph(t("export.no_codes"))
    else:
        doc.add_heading(t("cross.tab3"), level=2)
        m = A.case_matrix(long_df)
        tb = doc.add_table(rows=1, cols=len(m.columns) + 1)
        tb.style = "Light Grid Accent 1"
        hdr = tb.rows[0].cells
        hdr[0].text = t("common.respondent")
        for j, c in enumerate(m.columns):
            hdr[j + 1].text = str(c)
        for idx, row in m.iterrows():
            cells = tb.add_row().cells
            cells[0].text = str(idx)
            for j, c in enumerate(m.columns):
                cells[j + 1].text = str(row[c])

        doc.add_heading(t("cross.tab2"), level=2)
        cnt, jac, tot = A.cooccurrence(records)
        pairs = A.cooccurrence_pairs(cnt, tot, top_n=20)
        if pairs.empty:
            doc.add_paragraph(t("cross.no_cooc"))
        else:
            for _, r in pairs.iterrows():
                doc.add_paragraph(
                    f"{I.code_label(r['code_a'])} × {I.code_label(r['code_b'])}: "
                    f"{r['cooccurrence']} ({t('stat.jaccard')} {r['jaccard']})",
                    style="List Bullet")

    doc.add_page_break()
    doc.add_heading(t("export.section_cases"), level=1)
    for rec in records:
        doc.add_heading(rec.get(S.RESPONDENT, ""), level=2)
        d = rec.get(S.DESCRIPTORS, {})
        doc.add_paragraph("  ".join(
            f"{I.descriptor(k)}={I.descriptor_value(d.get(k, S.UNSPECIFIED))}"
            for k in S.DESCRIPTOR_KEYS))
        if rec.get(S.SUMMARY):
            doc.add_paragraph(rec[S.SUMMARY])
        for seg in rec.get(S.SEGMENTS, []):
            codes = S.codes_of(seg)
            p = doc.add_paragraph()
            p.add_run(seg.get(S.TITLE, "")).bold = True
            if len(codes) > 1:
                p.add_run(f"  [{t('export.multi_mark')}]").bold = True
            doc.add_paragraph("  ".join(I.code_label(c) for c in codes),
                              style="List Bullet")
            doc.add_paragraph(f"“{seg.get(S.QUOTE, '')}”",
                              style="List Bullet 2")
        doc.add_page_break()

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


with tab_export:
    recs = st.session_state.records
    if not recs:
        st.info(t("app.no_data"))
    else:
        st.markdown(f"### {t('export.title')}")
        st.caption(t("export.hint"))
        c1, c2 = st.columns(2)
        with c1:
            st.download_button(t("export.excel"), build_excel(recs),
                               file_name=f"analysis_{datetime.now():%Y%m%d}.xlsx",
                               **WIDE, type="primary")
        with c2:
            st.download_button(t("export.word"), build_word(recs),
                               file_name=f"report_{datetime.now():%Y%m%d}.docx",
                               **WIDE)
        st.divider()
        payload = [{k: v for k, v in r.items() if not k.startswith("_")}
                   for r in recs]
        st.download_button(
            t("export.json"),
            json.dumps({"framework_id": FW.id, "schema_version": S.SCHEMA_VERSION,
                        "records": payload}, ensure_ascii=False,
                       indent=2).encode("utf-8"),
            file_name=f"records_{datetime.now():%Y%m%d}.json",
            mime="application/json", **WIDE)


# =====================================================================
# 13. 框架建構：OpenAlex 檢索 → 草擬 → 人工核可
# =====================================================================
def _origin_label(prov):
    return {F.PROV_BUILTIN: t("fw.origin_builtin"),
            F.PROV_MANUAL: t("fw.origin_manual"),
            F.PROV_OPENALEX_DRAFT: t("fw.origin_draft"),
            F.PROV_OPENALEX_APPROVED: t("fw.origin_approved"),
            F.PROV_INDUCED: t("fw.origin_induced")}.get(prov, prov)


def _oa_client():
    """快取放在專案資料夾裡，才能跟著專案一起流通給其他研究者重現。"""
    return OA.Client(api_key=st.session_state.get("oa_key", ""),
                     cache_dir=OA_CACHE_DIR)


with tab_fw:
    lang = I.get_lang()
    st.info(t("fw.principle"))
    fw1, fw2, fw3, fw4 = st.tabs([t("fw.tab1"), t("fw.tab2"),
                                  t("fw.tab3"), t("fw.tab4")])

    # ----------------------------------------------------------------
    # 現用框架
    # ----------------------------------------------------------------
    with fw1:
        st.markdown(f"### {FW.name(lang)}")
        if FW.description(lang):
            st.caption(FW.description(lang))
        m = st.columns(4)
        m[0].metric(t("fw.n_dimensions"), len(FW.dimensions))
        m[1].metric(t("fw.n_codes"), len(FW.codes))
        m[2].metric(t("fw.polarity_model"),
                    t("fw.polarity_on") if FW.has_polarity else t("fw.polarity_off"))
        m[3].metric(t("fw.origin"), _origin_label(FW.provenance))
        if FW.citation:
            st.caption(FW.citation)
        # 沒有排除條件的框架，其構念邊界是模型當場想出來的——這件事會
        # 直接打穿「編碼依附於一個有文獻出處的框架」這個主張，所以要講。
        if not FW.has_exclusions():
            st.warning(t("fw.exclusions_missing"))

        st.divider()
        st.markdown(f"#### {t('fw.definitions')}")
        for d in FW.dimensions:
            with st.expander(f"{I.dim(d, lang)}  ·  `{FW.dim_short[d]}`"):
                if FW.definition(d, lang):
                    st.write(FW.definition(d, lang))
                if FW.has_polarity:
                    for p in FW.polarity_values:
                        items = FW.indicators(d, p, lang=lang)
                        st.markdown(f"**{FW.polarity_label(d, p, lang)}**")
                        for x in items:
                            st.markdown(f"- {x}")
                else:
                    items = FW.indicators(d, lang=lang)
                    if items:
                        st.markdown(f"**{t('fw.indicators_for')}**")
                        for x in items:
                            st.markdown(f"- {x}")
                # 排除條件跟指標同等重要：指標說「什麼算」，排除條件說
                # 「什麼不算」。沒寫的話模型會自己補，而它補出來的邊界
                # 不會出現在任何文件裡——框架的文獻追蹤就變成一句空話。
                excl = FW.exclusions(d, lang=lang)
                st.markdown(f"**{t('fw.exclusions')}**")
                if excl:
                    for x in excl:
                        st.markdown(f"- ✗ {x}")
                else:
                    st.caption(t("fw.no_exclusions"))
                lits = FW.literature(d)
                if lits:
                    st.markdown(f"**{t('fw.grounding')}**")
                    for l in lits:
                        mark = "★" if l.get(F.LIT_ROLE) == F.ROLE_GROUNDING else "·"
                        st.caption(f"{mark} {l.get(F.LIT_CITATION, '')}")

        st.divider()
        bib = OA.bibliography(FW)
        st.markdown(f"#### {t('fw.bibliography')}")
        if not bib:
            st.info(t("fw.no_bibliography"))
        else:
            show_df(pd.DataFrame([{
                t("common.citation"): b["citation"],
                t("common.role"): b["role"],
                t("common.dimension"): ", ".join(I.dim(x, lang)
                                                 for x in b["dimensions"]),
                "DOI": b["doi"] or "",
            } for b in bib]), hide_index=True)

        prov = OA.provenance_of(FW)
        if prov:
            st.divider()
            st.markdown(f"#### {t('fw.methods_para')}")
            st.caption(t("fw.methods_hint"))
            st.text_area("", OA.methods_sentence(OA.methods_facts(FW), lang),
                         height=170, key="fw_methods_para",
                         label_visibility="collapsed")
            with st.expander(t("fw.provenance")):
                st.json({k: v for k, v in prov.items() if k != OA.PD_WORKS})
                st.caption(f"{t('fw.retrieved_works')}: "
                           f"{len(prov.get(OA.PD_WORKS) or [])}")

    # ----------------------------------------------------------------
    # 步驟 1：檢索
    # ----------------------------------------------------------------
    with fw2:
        # 金鑰的輸入欄在側欄，這裡只回報目前的額度狀態。
        client = _oa_client()
        if not client.api_key:
            st.caption(t("fw.key_in_sidebar"))
        (st.success if client.has_key else st.warning)(client.budget_note(lang))

        theory = st.text_input(t("fw.theory"), key="oa_theory",
                               placeholder=t("fw.theory_ph"),
                               help=t("fw.theory_help"))

        st.caption(t("fw.topics_hint"))
        if st.button(t("fw.find_topics"), key="btn_oa_topics"):
            if not theory.strip():
                st.warning(t("fw.need_theory"))
            else:
                try:
                    st.session_state.oa_topics = OA.suggest_topics(client, theory)
                except OA.QuotaError as e:
                    st.error(f"{t('fw.quota_hit')}: {e}")
                except OA.OpenAlexError as e:
                    st.error(str(e))

        topic_id = None
        topics = st.session_state.get("oa_topics") or []
        if topics:
            opts = [None] + [x["id"] for x in topics]
            topic_names = {x["id"]: f"{x['name']} · {x['works_count']:,} works "
                                    f"({x['field']})" for x in topics}
            topic_id = st.selectbox(
                t("fw.theory"), opts, key="oa_topic",
                format_func=lambda i, _n=topic_names: (
                    t("fw.topic_none") if i is None else _n.get(i, i)))

        c = st.columns(4)
        n_sem = c[0].number_input(t("fw.n_seminal"), 5, 50, 20, key="oa_n_sem")
        n_rec = c[1].number_input(t("fw.n_recent"), 0, 50, 15, key="oa_n_rec")
        yrs = c[2].number_input(t("fw.recent_years"), 2, 15, 6, key="oa_years")
        req_ab = c[3].checkbox(t("fw.require_abstract"), value=False,
                               key="oa_req_ab",
                               help=t("fw.require_abstract_help"))

        if st.button(t("fw.retrieve"), type="primary", key="btn_oa_go"):
            if not theory.strip():
                st.warning(t("fw.need_theory"))
            else:
                try:
                    with st.spinner(t("fw.retrieving")):
                        works, log = OA.retrieve_corpus(
                            client, theory, n_seminal=int(n_sem),
                            n_recent=int(n_rec), recent_years=int(yrs),
                            topic_id=topic_id, require_abstract=req_ab)
                    st.session_state.oa_works = works
                    st.session_state.oa_log = log
                    st.session_state.oa_draft = None
                except OA.QuotaError as e:
                    st.error(f"{t('fw.quota_hit')}: {e}")
                except OA.OpenAlexError as e:
                    st.error(str(e))

        works = st.session_state.get("oa_works") or []
        if works:
            log = st.session_state.get("oa_log") or {}
            st.success(t("fw.retrieved", n=len(works),
                         a=sum(1 for w in works if w["has_abstract"])))
            # 檢索式寫錯時，回來的會是「全文某處剛好提到、但被引數很高」的
            # 論文——放射性碳定年、鋰電池綜述那一類。這個比例就是在抓這件事。
            rel = log.get("relevance")
            if rel is not None:
                if log.get("relevance_warning"):
                    st.error(t("fw.relevance_bad", pct=int(rel * 100)))
                elif rel < 0.85:
                    st.warning(t("fw.relevance_mid", pct=int(rel * 100)))
                else:
                    st.caption(t("fw.relevance_ok", pct=int(rel * 100)))
            if log.get("fallback_query"):
                st.info(t("fw.query_widened", n=log.get("phrase_hits", 0)))
            st.caption(t("fw.cache_note"))
            show_df(pd.DataFrame([{
                "#": f"W{i}",
                t("common.year"): w["year"],
                t("common.citation"): OA.apa_citation(w),
                t("common.cited_by"): w["cited_by_count"],
                t("common.abstract"): "✓" if w["has_abstract"] else "",
            } for i, w in enumerate(works, 1)]), hide_index=True)
            with st.expander(t("fw.retrieval_log")):
                st.json(log)
        elif st.session_state.get("oa_log"):
            st.warning(t("fw.no_results"))

    # ----------------------------------------------------------------
    # 步驟 2：草擬與核可
    # ----------------------------------------------------------------

    # ----------------------------------------------------------------
    # 匯入／匯出
    # ----------------------------------------------------------------
    with fw4:
        st.caption(t("fw.export_hint"))
        st.download_button(
            t("fw.export_active"),
            json.dumps(FW.data, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"{FW.id}.json", mime="application/json", **WIDE)

        st.divider()
        up = st.file_uploader(t("fw.import"), type=["json"], key="fw_upload")
        if up is not None:
            try:
                data = json.loads(up.read().decode("utf-8"))
                imported = F.load_dict(data)
                F.save(imported, os.path.join(F.FRAMEWORK_DIR,
                                              f"{imported.id}.json"))
                st.success(t("fw.import_ok", id=imported.id))
            except (F.FrameworkError, ValueError, json.JSONDecodeError) as e:
                st.error(t("fw.import_bad", e=e))

        st.divider()
        st.markdown(f"#### {t('fw.installed')}")
        show_df(pd.DataFrame([{
            t("fw.new_id"): fid,
            t("common.name"): name,
            t("common.source"): path,
        } for fid, name, path in F.list_available()]), hide_index=True)

    # 【注意】這一段刻意排在 fw4 之後才執行。
    # st.stop() 會中止整支腳本，凡是尚未渲染的內容都會消失；若 fw3 寫在前面，
    # 使用者一進來（還沒檢索任何文獻）就會連「匯入／匯出」都看不到。
    # 子頁籤的顯示順序由 st.tabs() 決定，與 with 區塊的執行順序無關，
    # 因此把 fw3 挪到最後執行，畫面順序不受影響。
    with fw3:
      works = st.session_state.get("oa_works") or []
      if not works:
        st.info(t("fw.need_corpus"))
      else:
        st.markdown(f"### {t('fw.draft_from', n=len(works))}")
        pol_opts = [None, True, False]
        pol_names = {None: t("fw.polarity_auto"), True: t("fw.polarity_yes"),
                     False: t("fw.polarity_no")}
        pol = st.radio(t("fw.polarity_choice"), pol_opts, horizontal=True,
                       format_func=lambda v: pol_names[v], key="oa_pol",
                       help=t("fw.polarity_choice_help"))
        extra = st.text_area(t("fw.extra"), key="oa_extra",
                             placeholder=t("fw.extra_ph"), height=80)

        if st.button(t("fw.draft"), type="primary", key="btn_oa_draft"):
            if not model_name:
                st.error(t("run.need_model"))
            elif provider == LLM.GEMINI and not api_key:
                st.error(t("run.need_key"))
            else:
                index = OA.evidence_index(works)
                dep = endpoint()
                try:
                    with st.spinner(t("fw.drafting")):
                        draft, report = OA.draft_framework(
                            st.session_state.get("oa_theory", ""), index,
                            LLM.make_callable(dep, temperature=0.2),
                            has_polarity=pol, extra=extra,
                            model_name=dep.describe())
                    st.session_state.oa_draft = draft
                    st.session_state.oa_report = report
                    st.session_state.oa_decisions = OA.blank_decisions(draft)
                except OA.DraftError as e:
                    st.session_state.oa_draft = None
                    st.error(t("fw.draft_failed", e=e))
                except Exception as e:
                    st.session_state.oa_draft = None
                    st.error(t("fw.draft_failed", e=e))

        draft = st.session_state.get("oa_draft")
        if not draft:
            st.stop()

        report = st.session_state.get("oa_report") or {}
        st.success(t("fw.draft_ok", n=report.get("n_dimensions", 0)))
        if report.get("errors"):
            st.error(t("fw.guard_blocked"))
            for e in report["errors"]:
                st.caption(f"• {e}")
        if report.get("dropped"):
            with st.expander(t("fw.dropped")):
                for d in report["dropped"]:
                    st.caption(f"• {d.get('label', d.get('index'))} — {d['reason']}")
        if report.get("warnings"):
            with st.expander(t("fw.warnings")):
                for w in report["warnings"]:
                    st.caption(f"• {w}")

        st.divider()
        st.markdown(f"### {t('fw.approve_title')}")
        st.caption(t("fw.approve_hint"))

        decisions = st.session_state.setdefault("oa_decisions",
                                                OA.blank_decisions(draft))
        dec_opts = [None, OA.DECISION_APPROVE, OA.DECISION_EDIT, OA.DECISION_REJECT]
        dec_names = {None: t("fw.dec_pending"),
                     OA.DECISION_APPROVE: t("fw.dec_approve"),
                     OA.DECISION_EDIT: t("fw.dec_edit"),
                     OA.DECISION_REJECT: t("fw.dec_reject")}

        for row in OA.review_rows(draft, lang):
            did = row["dimension_id"]
            cur = decisions.setdefault(did, {"decision": None, "note": ""})
            mark = {None: "○", OA.DECISION_APPROVE: "✔",
                    OA.DECISION_EDIT: "✎",
                    OA.DECISION_REJECT: "✘"}[cur.get("decision")]
            with st.expander(f"{mark}  {row['label']}  ·  `{row['short']}`  "
                             f"·  {row['n_grounding']}★ + {row['n_supporting']}",
                             expanded=cur.get("decision") is None):
                st.write(row["definition"] or "—")
                st.markdown(f"**{t('fw.grounding')}**")
                for cite in row["grounding_citations"]:
                    st.caption(f"★ {cite}")
                if row["grounding_note"]:
                    st.caption(f"_{t('fw.grounding_note')}: {row['grounding_note']}_")

                choice = st.radio(
                    t("fw.decision"), dec_opts, horizontal=True,
                    index=dec_opts.index(cur.get("decision")),
                    format_func=lambda v: dec_names[v], key=f"dec_{did}")
                cur["decision"] = choice

                if choice == OA.DECISION_EDIT:
                    dim = next(x for x in draft[F.DIMENSIONS] if x[F.DIM_ID] == did)
                    e1, e2 = st.columns(2)
                    cur["label_en"] = e1.text_input(
                        t("fw.dim_label_en"), dim[F.DIM_LABEL].get("en", ""),
                        key=f"le_{did}")
                    cur["label_zh"] = e2.text_input(
                        t("fw.dim_label_zh"), dim[F.DIM_LABEL].get("zh", ""),
                        key=f"lz_{did}")
                    cur["definition_en"] = st.text_area(
                        t("fw.dim_def_en"), dim[F.DIM_DEFINITION].get("en", ""),
                        key=f"de_{did}", height=90)
                    cur["definition_zh"] = st.text_area(
                        t("fw.dim_def_zh"), dim[F.DIM_DEFINITION].get("zh", ""),
                        key=f"dz_{did}", height=90)
                if choice is not None:
                    cur["note"] = st.text_input(
                        t("fw.dim_note_reject") if choice == OA.DECISION_REJECT
                        else t("fw.dim_note"), cur.get("note", ""),
                        key=f"nt_{did}")

        vals = [v.get("decision") for v in decisions.values()]
        st.caption(t("fw.summary_counts",
                     a=vals.count(OA.DECISION_APPROVE),
                     e=vals.count(OA.DECISION_EDIT),
                     r=vals.count(OA.DECISION_REJECT),
                     p=vals.count(None)))

        st.divider()
        s1, s2 = st.columns(2)
        reviewer = s1.text_input(t("fw.reviewer"), key="oa_reviewer",
                                 help=t("fw.reviewer_help"))
        new_id = s2.text_input(t("fw.new_id"), draft[F.FRAMEWORK_ID],
                               key="oa_new_id", help=t("fw.new_id_help"))
        note = st.text_input(t("fw.approval_note"), key="oa_appr_note")

        target = os.path.join(F.FRAMEWORK_DIR, f"{OA._slug(new_id)}.json")
        if os.path.exists(target):
            st.warning(t("fw.overwrite_warn"))

        if st.button(t("fw.save"), type="primary", key="btn_oa_save"):
            if not reviewer.strip():
                st.error(t("fw.need_reviewer"))
            elif not any(v in (OA.DECISION_APPROVE, OA.DECISION_EDIT)
                         for v in vals):
                st.error(t("fw.need_decision"))
            else:
                try:
                    newfw = OA.apply_decisions(draft, decisions, reviewer.strip(),
                                               framework_id=new_id, note=note)
                    F.save(newfw, os.path.join(F.FRAMEWORK_DIR,
                                               f"{newfw.id}.json"))
                    st.success(t("fw.saved", id=newfw.id))
                    st.session_state.oa_draft = None
                except OA.DraftError as e:
                    st.error(str(e))
