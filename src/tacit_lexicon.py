"""
tacit_lexicon.py — 詞庫誘導與稽核引擎（多語架構）
================================================
設計立場：詞庫不當分類器。拿關鍵詞當主要編碼機制等於退回 bag-of-words 典範，
中文上一定輸。所以本模組讓詞庫做三件它真正擅長的事：

  ① 反向誘導  — 從已編碼語料統計出各碼的特徵詞，而非憑空手寫
  ② 稽核工具  — 反過來檢查 LLM 有沒有過度詮釋或漏標（recall 估計）
  ③ 對照基準  — 詞典式編碼當 baseline，與 LLM 編碼算一致度

【語言架構】
  詞庫是**語言相關的資源**：中文詞庫不能拿去分析英文逐字稿。
  因此詞庫檔本身帶 "language" 欄位，結構鍵一律為 ASCII 識別碼，
  而詞條內容（概念詞、正規表示式）則是該語言的語言學資料，保持原文。

  結構（ASCII）      → 程式邏輯讀得懂，可跨語言重用
  詞條內容（該語言） → 語言學資料，不翻譯

【零相依即可執行】
  無詞典新詞發現（n-gram 凝固度＋左右鄰字熵）不需要斷詞器，
  反而能「發現」領域新詞而非受限於既有詞典。裝了 CKIP 會自動改用。

主要參考：
  Monroe, Colaresi & Quinn (2008) Fightin' Words — log-odds with Dirichlet prior
"""

import json
import math
import os
import re
from collections import Counter, defaultdict

import tacit_schema as S
import tacit_framework as F

# --- 選配的斷詞後端 -------------------------------------------------
try:
    from ckip_transformers.nlp import CkipWordSegmenter  # noqa
    HAS_CKIP_TRANSFORMERS = True
except Exception:
    HAS_CKIP_TRANSFORMERS = False
try:
    from ckiptagger import WS, construct_dictionary       # noqa
    HAS_CKIPTAGGER = True
except Exception:
    HAS_CKIPTAGGER = False


CJK = r'一-鿿㐀-䶿'
_NON_CJK = re.compile(f'[^{CJK}]+')
_CLAUSE_SPLIT = re.compile(r'[，。！？；：、\n,.!?;:]')

DEFAULT_LEXICON_PATH = "tacit_lexicon_zh.json"

# --- 詞庫結構鍵（ASCII） --------------------------------------------
LANGUAGE = "language"
# 詞庫綁定的框架。詞庫的概念詞是按**維度**分層的，因此它不只跟語言有關，
# 也跟框架有關：一份為負責任創新四維度寫的詞庫，套到別的框架上毫無意義。
FRAMEWORK_ID = "framework_id"
FORCE_TERMS = "force_terms"
CONCEPT_TERMS = "concept_terms"
NEGATORS = "negators"
PIVOTS = "pivots"
INTENSIFIERS = "intensifiers"
REPORTED_SPEECH = "reported_speech"
PATTERNS = "patterns"
PATTERN_REGEX = "regex"
PATTERN_NOTE = "note"
LAYER_KEYS = [FORCE_TERMS, NEGATORS, PIVOTS, INTENSIFIERS, REPORTED_SPEECH]

# 舊版中文結構鍵 → 新識別碼
_LEGACY_KEYS = {
    "強制詞": FORCE_TERMS, "概念詞": CONCEPT_TERMS, "否定詞": NEGATORS,
    "轉折詞": PIVOTS, "程度詞": INTENSIFIERS, "傳述標記": REPORTED_SPEECH,
    "句式模板": PATTERNS,
}


# 舊版把維度、極性與說明全編在中文名稱裡。這裡給每個模板一個有意義的
# ASCII 識別碼，並補上英文說明——工具要能給非中文使用者讀懂。
_PATTERN_ID_MAP = {
    "預期_P_條件未來": "ANT_P_conditional_future",
    "預期_P_時間跨度": "ANT_P_long_horizon",
    "預期_P_不確定性承認": "ANT_P_uncertainty_acknowledged",
    "預期_N_決定論": "ANT_N_determinism",
    "預期_N_延後思考": "ANT_N_deferral",
    "反思性_P_認知讓步": "REF_P_epistemic_concession",
    "反思性_P_自我質疑": "REF_P_self_questioning",
    "反思性_N_專業權威": "REF_N_expert_authority",
    "反思性_N_風險否認": "REF_N_risk_denial",
    "參與_P_主動納入": "ENG_P_active_inclusion",
    "參與_P_雙向": "ENG_P_two_way_dialogue",
    "參與_N_下游知會": "ENG_N_downstream_notification",
    "參與_N_能力否定": "ENG_N_deficit_model",
    "回應性_P_因果調整": "RES_P_causal_adjustment",
    "回應性_P_停止決策": "RES_P_halt_decision",
    "回應性_N_不可改": "RES_N_immutable_path",
    "回應性_N_法規為敵": "RES_N_regulation_as_obstacle",
}

_PATTERN_NOTE_EN = {
    "ANT_P_conditional_future": "Conditional clause plus modality; signals exploration of multiple futures.",
    "ANT_P_long_horizon": "An explicit multi-year time horizon.",
    "ANT_P_uncertainty_acknowledged": "Explicit admission that outcomes cannot be predicted.",
    "ANT_N_determinism": "Single deterministic forecast; technological determinism.",
    "ANT_N_deferral": "Postponing foresight until the technology has already stabilised.",
    "REF_P_epistemic_concession": "First-person epistemic humility.",
    "REF_P_self_questioning": "Second-order reflection on the speaker's own assumptions.",
    "REF_N_expert_authority": "We-know-best framing that excludes outside voices.",
    "REF_N_risk_denial": "Denial of risk or uncertainty; techno-optimism.",
    "ENG_P_active_inclusion": "Actively inviting external actors into the process.",
    "ENG_P_two_way_dialogue": "Two-way exchange rather than one-way communication.",
    "ENG_N_downstream_notification": "Engagement reduced to notification after decisions are fixed.",
    "ENG_N_deficit_model": "Deficit-model framing of the public as incapable of understanding.",
    "RES_P_causal_adjustment": "Full causal chain from external signal to substantive change; the strongest evidence of responsiveness.",
    "RES_P_halt_decision": "Capacity to stop or withdraw an innovation trajectory.",
    "RES_N_immutable_path": "Rigid structure; the trajectory cannot be changed.",
    "RES_N_regulation_as_obstacle": "Regulation framed as an obstacle rather than as material for co-governance.",
}


# =====================================================================
# 0. 詞庫存取與遷移
# =====================================================================
def blank_lexicon(language="zh-Hant", framework_id=None):
    return {
        LANGUAGE: language,
        FRAMEWORK_ID: framework_id or F.active().id,
        FORCE_TERMS: [],
        CONCEPT_TERMS: {d: {p: [] for p in S.POLARITIES} for d in S.DIMENSIONS},
        NEGATORS: [], PIVOTS: [], INTENSIFIERS: [], REPORTED_SPEECH: [],
        PATTERNS: {},
    }


def migrate_lexicon(raw, language="zh-Hant"):
    """舊版中文鍵詞庫 → 新結構。冪等：已是新格式再跑一次不會改變。"""
    lex = blank_lexicon(raw.get(LANGUAGE, language) if isinstance(raw, dict) else language,
                        (raw or {}).get(FRAMEWORK_ID) if isinstance(raw, dict) else None)
    if not isinstance(raw, dict):
        return lex
    src = {}
    for k, v in raw.items():
        src[_LEGACY_KEYS.get(k, k)] = v

    for k in LAYER_KEYS:
        lex[k] = [w for w in (src.get(k) or []) if isinstance(w, str) and w]

    concepts = src.get(CONCEPT_TERMS) or {}
    for dim_key, block in concepts.items():
        dim = S.norm_dimension(dim_key)
        if dim not in S.DIMENSIONS or not isinstance(block, dict):
            continue
        for pol in S.POLARITIES:
            lex[CONCEPT_TERMS][dim][pol] = [
                w for w in (block.get(pol) or []) if isinstance(w, str) and w]

    for name, spec in (src.get(PATTERNS) or {}).items():
        if not isinstance(spec, dict):
            continue
        dim = S.norm_dimension(spec.get(S.DIMENSION))
        pol = S.norm_polarity(spec.get(S.POLARITY))
        if dim is None or pol is None:
            # 舊版把維度與極性編在名稱裡：「預期_P_條件未來」
            parts = str(name).split("_")
            if len(parts) >= 2:
                dim = dim or S.norm_dimension(parts[0])
                pol = pol or S.norm_polarity(parts[1])
        rx = spec.get(PATTERN_REGEX, spec.get("regex", ""))
        if dim not in S.DIMENSIONS or pol not in S.POLARITIES or not rx:
            continue
        try:
            re.compile(rx)
        except re.error:
            continue
        # 已經是合法 ASCII 識別碼就原樣沿用，否則遷移不會冪等
        pid = (spec.get("id") or _PATTERN_ID_MAP.get(name)
               or (str(name) if re.fullmatch(r"[A-Za-z0-9_]+", str(name))
                   else _slug(name, dim, pol, lex[PATTERNS])))
        lex[PATTERNS][pid] = {
            S.DIMENSION: dim, S.POLARITY: pol, PATTERN_REGEX: rx,
            PATTERN_NOTE: _norm_note(spec.get(PATTERN_NOTE, spec.get("說明", "")),
                                     lex[LANGUAGE], pid),
        }
    return lex


def _norm_note(note, language, pid):
    """
    句式模板的說明存成 {en, zh} 雙語。說明會顯示在介面上，
    只有單一語言的話，切換介面語言時就會露出另一種語言的字。
    """
    if isinstance(note, dict):
        out = {"en": note.get("en", ""), "zh": note.get("zh", "")}
    else:
        text = str(note or "")
        lang_key = "zh" if str(language).startswith("zh") else "en"
        out = {"en": "", "zh": ""}
        out[lang_key] = text
    if not out["en"]:
        out["en"] = _PATTERN_NOTE_EN.get(pid, "")
    return out


def pattern_note(spec, lang="en"):
    note = spec.get(PATTERN_NOTE)
    if isinstance(note, dict):
        return note.get(lang) or note.get("en") or note.get("zh") or ""
    return str(note or "")


def _slug(name, dim, pol, existing):
    base = f"{S.DIM_SHORT[dim]}_{pol}"
    tail = re.sub(r'[^0-9A-Za-z]+', '', str(name).split("_")[-1]) or "rule"
    pid = f"{base}_{tail}" if tail.isascii() and tail else base
    n = 1
    while pid in existing:
        n += 1
        pid = f"{base}_{n}"
    return pid


def load_lexicon(path=DEFAULT_LEXICON_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return migrate_lexicon(json.load(f))


def lexicon_framework(lex):
    """詞庫宣告自己屬於哪個框架。舊檔沒有這個欄位，視為內建的 RI 框架。"""
    return (lex or {}).get(FRAMEWORK_ID) or F.DEFAULT_FRAMEWORK_ID


def framework_mismatch(lex, framework=None):
    """
    檢查詞庫與作用中框架是否相符，不符就回傳說明用的資料。

    【為什麼一定要檢查】
    migrate_lexicon 會用 S.norm_dimension() 把舊維度名稱正規化，而
    norm_dimension 只認得**作用中框架**的維度。所以切換到別的框架之後載入
    這份 RI 詞庫，239 個概念詞與 17 個句式模板會被逐一丟棄，得到一份結構
    完整但內容全空的詞庫——不會報錯，只會讓詞典編碼器一個碼都標不出來，
    畫面上顯示 κ = 0.0、編碼 89 / 0，看起來像功能壞掉。

    靜默地把資料丟掉是最糟的失敗方式：使用者沒有任何線索可以查。
    """
    fw = framework or F.active()
    want = lexicon_framework(lex)
    if want == fw.id:
        return None
    n_terms = sum(len(lex[CONCEPT_TERMS][d][p])
                  for d in fw.dimensions for p in S.POLARITIES
                  if d in lex.get(CONCEPT_TERMS, {}))
    return {"lexicon_framework": want, "active_framework": fw.id,
            "terms_after_load": n_terms,
            "patterns_after_load": len(lex.get(PATTERNS) or {})}


class LexiconWriteRefused(RuntimeError):
    """拒絕以空詞庫覆蓋既有的非空詞庫。"""


def lexicon_size(lex):
    """
    概念詞 + 句式模板的總數，用來判斷一份詞庫是不是空的。

    數的是**這份詞庫自己**的鍵，不是作用中框架的極性值。這支函式的用途是
    「存檔前擋下用空詞庫蓋掉有內容的詞庫」，而那個判斷不可以受當下開著哪
    個框架影響——若寫 `for p in S.POLARITIES`，切到極性值不同的框架時
    會把一份滿的詞庫數成空的，然後放行覆蓋。
    """
    ct = (lex or {}).get(CONCEPT_TERMS) or {}
    n = 0
    for v in ct.values():
        if isinstance(v, dict):
            n += sum(len(x) for x in v.values() if isinstance(x, list))
        elif isinstance(v, list):
            n += len(v)
    return n + len((lex or {}).get(PATTERNS) or {})


def save_lexicon(lex, path=DEFAULT_LEXICON_PATH, allow_empty=False):
    """
    存檔前擋下「用空詞庫蓋掉有內容的詞庫」。

    這不是防呆，是防資料損毀。空詞庫會在幾種情況下產生——檔名對不上、
    框架切換後維度認不得——而使用者在介面上完全看不出詞庫已經空了；
    接著任何一次合併或重新載入都會把空的存回去，239 個詞就永久消失。
    寫入是不可逆的，所以這一關寧可誤擋也不能誤放。
    """
    if not allow_empty and lexicon_size(lex) == 0 and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                existing = migrate_lexicon(json.load(f))
        except Exception:
            existing = None
        if existing is not None and lexicon_size(existing) > 0:
            raise LexiconWriteRefused(
                f"refusing to overwrite {path}: the lexicon in memory is empty "
                f"but the file on disk holds {lexicon_size(existing)} entries")
    payload = {k: v for k, v in lex.items() if not k.startswith("_")}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path


def lexicon_stats(lex):
    return [{S.DIMENSION: d, S.POLARITY: p, "code": S.code_of(d, p),
             "term_count": len(lex[CONCEPT_TERMS][d][p])}
            for d in S.DIMENSIONS for p in S.POLARITIES]


def lexicon_language(lex):
    return (lex or {}).get(LANGUAGE, "zh-Hant")


# =====================================================================
# 1. 文本預處理
# =====================================================================
def segment_text(seg):
    return (seg.get(S.FULL_TEXT) or seg.get(S.QUOTE) or "").strip()


def clean_cjk(text):
    return _NON_CJK.sub("　", text or "")


def iter_clauses(text):
    for c in _CLAUSE_SPLIT.split(text or ""):
        c = c.strip()
        if c:
            yield c


# =====================================================================
# 2. 無詞典新詞發現（凝固度 + 左右鄰字熵）
# =====================================================================
# 虛詞邊界過濾。
# PMI 與鄰字熵擋得掉鬆散組合，卻擋不掉「虛詞 + 內容詞」這種跨詞邊界片段：
# 「的模型」「的參與」「化的」在統計上凝固度很高、左右鄰字也夠分散，
# 因此能一路通過並取得很高的 z 分數，污染特徵詞誘導的結果。
# 唯一可靠的判準是語言學的：某些虛詞在詞內不可能出現於首字或末字。
# 兩份清單刻意取保守交集——寧可漏掉幾個碎片，也不要誤殺真詞
# （例如「過程」「著手」，故 過、著 不列入首字禁用）。
_NO_LEAD = set("的了嗎呢吧啦喔耶哦嘛之麼")
# 末字禁用：語助詞、副詞、介詞、以及代名詞與指示詞。
# 「說你」「把這」這類碎片就是動詞黏上了下一句的開頭代名詞。
_NO_TAIL = set("的很最都也就還卻並而把被是我你妳他她它這那其每各某另從對跟向給")

# 功能詞清單。
#
# 為什麼需要它：PMI 與鄰字熵測的是「這幾個字是否常黏在一起、且前後文夠分散」，
# 而功能詞的搭配完全符合這個條件——「沒有」「這個」「其實」在任何中文語料裡
# 都又高頻又自由，統計上跟真正的領域術語無從分辨。結果就是新詞清單被
# 「比較、自己、知道、我們、已經、什麼」淹沒，真正的「臨床、揭露、高齡」被埋掉。
#
# 收錄原則：只收在**任何理論框架下**都不可能是分析對象的詞——
# 代名詞、指示詞、連接詞、程度副詞、時貌詞、泛稱量詞。
# 刻意不收「未來、風險、責任、參與、影響、問題」這類詞：
# 它們在某些框架下正是核心構念（例如負責任創新的「預期」就談未來與風險）。
# 框架是可插拔的，這份清單就不能預設任何特定理論。
_FUNCTION_WORDS = set("""
我們 你們 他們 她們 它們 咱們 自己 大家 別人 人家 對方
這個 那個 這些 那些 這樣 那樣 這種 那種 這邊 那邊 這裡 那裡 哪裡 哪些 哪個
什麼 怎麼 怎樣 為何 多少 幾個 是否
沒有 有些 有的 有一 有點 有時 沒什麼
就是 但是 可是 還是 或是 於是 而是 不是 只是 也是 都是 就會 就要 才會 才能
其實 然後 所以 因為 由於 雖然 不過 而且 並且 或者 甚至 反正 反而 倒是
如果 假如 要是 除非 否則 不然 結果 總之 因此 於是乎
比如 例如 譬如 比方 之類 什麼的 等等
至於 關於 除了 之外 之後 之前 之間 以及 還有 另外 其他 其中 以外 以後 以來
比較 非常 特別 相當 十分 稍微 有點 一點 一些 很多 許多 大量 少數 部分
真的 確實 當然 一定 必須 應該 可能 或許 大概 也許 差不多 幾乎 幾乎沒有
覺得 知道 認為 以為 想說 曉得 記得 發現 看到 聽到 講到 談到 提到 說到
已經 開始 繼續 一直 常常 偶爾 現在 目前 以前 後來 最後 剛剛 等一下 馬上
裡面 外面 上面 下面 前面 後面 旁邊 中間 當中
一個 兩個 三個 一下 一樣 一起 一邊 一次 每次 這次 上次 下次
時候 情況 狀況 東西 事情 地方 方面 部份 樣子 感覺
可以 不能 不會 不要 不用 需要 想要 願意 敢說
這麼 那麼 多麼 越來越 更加 尤其
""".split())


_EN_STOPWORDS = set("""
a an the this that these those it its they them their he she his her we us our you your i me my
is are was were be been being am do does did doing have has had having will would can could
shall should may might must not no nor
and or but so because if then than as of in on at to for from with by about into over under
between through during before after above below up down out off again further once here there
when where why how all any both each few more most other some such only own same too very just
one two three thing things way ways lot lots kind sort bit
what who whom which whose
i'm it's that's don't doesn't didn't isn't aren't wasn't weren't can't won't
like know think mean say said says get got go going went really actually basically
""".split())


# 不可出現在英文術語內部的詞：連接詞、關係詞、代名詞。
_EN_NO_INSIDE = set("""
because and or but so if then that which who what when where why how
it its they them their he she his her we us our you your i me my
is are was were be been am do does did have has had will would can could not no
""".split())


def detect_script(text, threshold=0.15):
    """
    判斷這段文字主要是中文還是英文。

    看的是 CJK 字元佔「有意義字元」的比例。門檻刻意訂得低（15%）：
    中文逐字稿常夾雜英文術語與機構名，只要出現一定比例的漢字就該走中文路徑；
    反過來，純英文語料裡不會有漢字，不會誤判。
    """
    text = text or ""
    cjk = len(re.findall(f"[{CJK}]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk + latin == 0:
        return "unknown"
    return "zh" if cjk / (cjk + latin) >= threshold else "en"


def is_function_word(term):
    """
    是否為功能詞（代名詞、連接詞、程度副詞等），不具領域內容。

    不代表「錯誤」——某一群受訪者確實比較常說「沒有」是一項可報告的發現。
    但它不是術語，不該出現在「新詞發現」的結果裡。
    """
    return term in _FUNCTION_WORDS or term.lower() in _EN_STOPWORDS


def _is_fragment(term):
    """判定候選詞是否為跨詞邊界的碎片，而非完整的詞。"""
    if not term:
        return False
    if term[0] in _NO_LEAD or term[-1] in _NO_TAIL:
        return True
    # 功能詞黏上內容字，例如「那個誤」「這個技」——功能詞本身是完整的，
    # 但把它跟後面的字黏成一個「詞」一定是切錯了邊界。
    for w in _FUNCTION_WORDS:
        if len(term) > len(w) and (term.startswith(w) or term.endswith(w)):
            return True
    return False


def _entropy(counter):
    total = sum(counter.values())
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log(c / total) for c in counter.values() if c > 0)


def _discover_en(texts, max_n=4, min_freq=3, min_pmi=1.5, max_candidates=800,
                 include_function_words=False):
    """
    英文的術語發現：單詞 + 詞的 n-gram 搭配（PMI 過濾）。

    回傳欄位與中文路徑一致，UI 與下游不必分兩套處理。
    英文有空白當詞界，所以不需要鄰字熵那一關——邊界不是問題，
    問題只在於「這幾個詞是不是一個固定搭配」，那由 PMI 判斷。
    """
    # 以句子為單位切開再組 n-gram：跨句的相鄰詞不是搭配，只是排版的巧合。
    # 少了這一步會抽出「demands it」「privacy anticipatory」這種橫跨句號的組合。
    sents = []
    for t in texts:
        for s in re.split(r"[.!?;:\n]+", (t or "").lower()):
            toks = re.findall(r"[a-z][a-z'-]*", s)
            if toks:
                sents.append(toks)
    tok_docs = sents
    uni = Counter(w for d in tok_docs for w in d)
    total = sum(uni.values()) or 1
    results, seen = [], set()

    def keep(term):
        if term in seen or len(term) < 2:
            return False
        if not include_function_words and is_function_word(term):
            return False
        return True

    for w, f in uni.items():
        if f >= min_freq and keep(w):
            seen.add(w)
            results.append({"term": w, "freq": f, "cohesion": 0.0,
                            "left_entropy": 0.0, "right_entropy": 0.0,
                            "score": round(math.log(f + 1), 3)})

    for n in range(2, max_n + 1):
        grams = Counter()
        for d in tok_docs:
            for i in range(len(d) - n + 1):
                grams[tuple(d[i:i + n])] += 1
        for g, f in grams.items():
            if f < min_freq:
                continue
            # 首尾若是虛詞，這一組就是切錯了邊界，不是一個術語：
            # 「because responsible」是把連接詞黏上了後面的形容詞，
            # 「demands it」是把動詞黏上了下一句的代名詞。
            if not include_function_words and (is_function_word(g[0])
                                               or is_function_word(g[-1])):
                continue
            # 連接詞與代名詞不會出現在術語**內部**——出現就代表跨了子句。
            # 介系詞（of/in/for）刻意不列入：「theory of change」「duty of care」
            # 這類術語內部本來就有介系詞。
            if not include_function_words and any(w in _EN_NO_INSIDE for w in g):
                continue
            p_joint = f / total
            p_ind = 1.0
            for w in g:
                p_ind *= uni[w] / total
            if p_ind <= 0:
                continue
            pmi = math.log(p_joint / p_ind, 2) / (n - 1)
            if pmi < min_pmi:
                continue
            term = " ".join(g)
            if not keep(term):
                continue
            seen.add(term)
            results.append({"term": term, "freq": f, "cohesion": round(pmi, 3),
                            "left_entropy": 0.0, "right_entropy": 0.0,
                            "score": round(pmi * math.log(f + 1), 3)})

    results.sort(key=lambda r: -r["score"])
    return results[:max_candidates]


def discover_terms(texts, max_n=6, min_freq=3, min_pmi=1.5, min_entropy=0.8,
                   max_candidates=800, include_function_words=False):
    """
    從語料中發現領域術語，不需要任何斷詞器或既有詞典。
    凝固度（PMI）過濾鬆散組合；左右鄰字熵過濾不完整片段。兩者都要通過。
    回傳依分數排序的 [{term, freq, cohesion, left_entropy, right_entropy, score}]
    """
    texts = [t for t in texts if t]
    # 英文語料走另一條路：字元 n-gram 對有空白的語言毫無意義
    #（"resp"、"onsi" 這種東西不是詞），要抽的是**詞**的 n-gram 搭配。
    if texts and detect_script("\n".join(texts)) == "en":
        return _discover_en(texts, max_n=min(max_n, 4), min_freq=min_freq,
                            min_pmi=min_pmi, max_candidates=max_candidates,
                            include_function_words=include_function_words)

    blob = "　".join(clean_cjk(t) for t in texts)
    if not blob.strip():
        return []

    grams = [Counter() for _ in range(max_n + 1)]
    left_ctx, right_ctx = defaultdict(Counter), defaultdict(Counter)
    L = len(blob)
    for n in range(1, max_n + 1):
        cnt = grams[n]
        for i in range(L - n + 1):
            s = blob[i:i + n]
            if "　" in s:
                continue
            cnt[s] += 1
            if n >= 2:
                left_ctx[s][blob[i - 1] if i > 0 else "<S>"] += 1
                right_ctx[s][blob[i + n] if i + n < L else "<E>"] += 1

    total_uni = sum(grams[1].values()) or 1
    results = []
    for n in range(2, max_n + 1):
        for s, freq in grams[n].items():
            if freq < min_freq:
                continue
            if _is_fragment(s):
                continue
            if not include_function_words and is_function_word(s):
                continue
            p_s = freq / total_uni
            splits_ok = all(grams[len(s[:k])][s[:k]] and grams[len(s[k:])][s[k:]]
                            for k in range(1, n))
            if not splits_ok:
                continue
            pmi = min(
                math.log(p_s / ((grams[len(s[:k])][s[:k]] / total_uni) *
                                (grams[len(s[k:])][s[k:]] / total_uni)))
                for k in range(1, n))
            if pmi < min_pmi:
                continue
            hl, hr = _entropy(left_ctx[s]), _entropy(right_ctx[s])
            if min(hl, hr) < min_entropy:
                continue
            results.append({
                "term": s, "freq": freq,
                "cohesion": round(pmi, 3),
                "left_entropy": round(hl, 3), "right_entropy": round(hr, 3),
                "score": round(pmi + min(hl, hr) + math.log(freq), 3),
            })
    results.sort(key=lambda r: -r["score"])
    return results[:max_candidates]


# =====================================================================
# 3. 斷詞
# =====================================================================
class Segmenter:
    """
    統一斷詞介面。強制詞在任何後端都會被保護不切開——
    「負責任創新」被切成「負責/任/創新」是整條分析管線最致命的錯誤來源。
    """

    def __init__(self, force_words=None, backend="auto"):
        self.force_words = sorted({w for w in (force_words or []) if len(w) >= 2},
                                  key=len, reverse=True)
        self.backend = self._pick(backend)
        self._ws = None

    def _pick(self, backend):
        if backend != "auto":
            return backend
        if HAS_CKIP_TRANSFORMERS:
            return "ckip-transformers"
        if HAS_CKIPTAGGER:
            return "ckiptagger"
        return "ngram"

    def backend_for(self, text):
        """
        依**這一段文字的語言**決定後端，而不是全域固定一種。

        中文與英文的斷詞是兩個不同的問題：中文沒有詞界，需要 CKIP 這類
        帶語言知識的模型；英文有空白，用空白切就已經接近正確，反而不該
        送進中文模型。同一份研究裡兩種語料並存是常態（中文訪談 + 英文文獻），
        所以路由必須逐段判斷。
        """
        if detect_script(text) == "en":
            return "whitespace"
        return self.backend

    def _lazy(self):
        if self._ws is not None:
            return
        if self.backend == "ckip-transformers":
            self._ws = CkipWordSegmenter(model="bert-base")
        elif self.backend == "ckiptagger":
            self._ws = WS("./data")

    def cut(self, text):
        text = (text or "").strip()
        if not text:
            return []
        use = self.backend_for(text)
        if use == "whitespace":
            return self._english(text)
        if use == "ngram":
            return self._max_match(text)
        try:
            self._lazy()
            if self.backend == "ckip-transformers":
                out = self._ws([text])[0]
            else:
                d = construct_dictionary({w: 1 for w in self.force_words})
                out = self._ws([text], coerce_dictionary=d)[0]
            return self._remerge(out)
        except Exception:
            self.backend = "ngram"
            return self._max_match(text)

    def _remerge(self, tokens):
        if not self.force_words:
            return tokens
        out, i = [], 0
        while i < len(tokens):
            matched = False
            for w in self.force_words:
                acc, j = "", i
                while j < len(tokens) and len(acc) < len(w):
                    acc += tokens[j]; j += 1
                    if acc == w:
                        out.append(w); i = j; matched = True; break
                if matched:
                    break
            if not matched:
                out.append(tokens[i]); i += 1
        return out

    def _english(self, text):
        """
        英文：空白／標點切詞，再把強制片語合回去。

        英文不能走 _max_match——那個函式只認 CJK 字元，其餘一律跳過，
        丟英文進去會得到幾乎空的結果（只剩強制詞本身）。

        一律轉小寫，讓 "Stakeholder" 與 "stakeholder" 併為同一個詞；
        質性語料的大小寫多半只是句首位置造成的，不帶意義。
        """
        # 先把換行與連續空白壓成單一空格：逐字稿裡「responsible\ninnovation」
        # 換行只是排版，不該讓強制片語比對失敗。
        low = re.sub(r"\s+", " ", text.lower())
        # 強制片語內部的空白換成不可見字元，讓它在切詞時被當成一個 token，
        # 切完再換回來。比用佔位符再查表簡單，也不會有標記外洩的風險。
        for p in sorted((w.lower() for w in self.force_words if " " in w),
                        key=len, reverse=True):
            low = low.replace(p, p.replace(" ", "\x01"))
        out = []
        for w in re.findall(r"[a-z0-9\x01][a-z0-9'\x01-]*", low):
            w = w.replace("\x01", " ").strip("-' ")
            if w:
                out.append(w)
        return out

    def _max_match(self, text):
        tokens, i, L = [], 0, len(text)
        while i < L:
            hit = None
            for w in self.force_words:
                if text.startswith(w, i):
                    hit = w; break
            if hit:
                tokens.append(hit); i += len(hit); continue
            ch = text[i]
            if not re.match(f"[{CJK}]", ch):
                i += 1; continue
            # 詞彙表沒收錄時，只吐出**單字**，不要盲抓兩個字。
            #
            # 「沒對到就抓下兩個字當一個詞」的做法會憑掃描位置
            # 硬切出跨詞邊界的碎片：「…的方法是…」若詞彙表只有「方法」，
            # 掃到「的」對不到，就抓成「的方」，接著再抓成「法是」。
            # 這類碎片全是假詞，卻照樣進入特徵詞誘導並拿到很高的 z 分數。
            #
            # 單字之後會被 len>=2 的條件濾掉，等於「詞彙表沒有的就不宣稱認得」。
            # 代價是低頻的真詞會被漏掉——但低頻詞本來就不是可靠的特徵詞。
            tokens.append(ch)
            i += 1
        return tokens


# =====================================================================
# 4. 特徵詞誘導（Monroe et al. 2008）
# =====================================================================
def _tokenize_all(texts, segmenter, vocab_filter=None):
    out = []
    for t in texts:
        toks = [w for w in segmenter.cut(t) if len(w) >= 2]
        if vocab_filter:
            toks = [w for w in toks if w in vocab_filter]
        out.append(toks)
    return out


def build_vocabulary(texts, lexicon=None, **discover_kwargs):
    """
    分析用詞彙表 = 詞庫既有詞 ∪ 語料中發現的新詞。
    這一步不能省：沒有詞彙表約束時，後備斷詞器會吐出「的專」「期情」這類
    跨詞邊界碎片，它們照樣能拿到很高的 z 分數，直接污染誘導結果。
    """
    vocab = set()
    if lexicon:
        vocab |= {w for w in lexicon.get(FORCE_TERMS, []) if len(w) >= 2}
        # 用 .get() 逐層取，不直接索引。詞庫與作用中框架不一定相符——
        # 拿 RI 的中文詞庫、開著 ESG 框架時，S.DIMENSIONS 裡的鍵在詞庫裡
        # 根本不存在，直接索引就是 KeyError。詞庫對不上框架是該回報的狀況
        # （lexicon_mismatch 負責），不是該讓斷詞器崩掉的狀況。
        _ct = lexicon.get(CONCEPT_TERMS) or {}
        for _block in _ct.values():
            if isinstance(_block, dict):
                for _terms in _block.values():
                    if isinstance(_terms, list):
                        vocab |= {w for w in _terms
                                  if isinstance(w, str) and len(w) >= 2}

    # 關鍵區分：**斷詞需要功能詞，報告不需要。**
    #
    # 詞彙表是給斷詞器用的。若「這個」不在詞彙表裡，斷詞器掃到「這個案子」
    # 就對不到任何詞，只好一個字一個字吐，或者把「個案子」誤當成一個詞。
    # 所以詞彙表必須收功能詞——它們是句子的一部分，要被正確地消耗掉。
    #
    # 但「新詞發現」與「特徵詞」是要給人看的分析結果，功能詞在那裡只是雜訊。
    # 因此：discovered（回報用）不含功能詞，vocab（斷詞用）含。
    discovered = discover_terms(texts, **discover_kwargs)
    vocab |= {r["term"] for r in discovered}
    vocab |= {w for w in _FUNCTION_WORDS if len(w) >= 2}
    return vocab, discovered


def induce_features(code_texts, segmenter=None, vocab=None, lexicon=None,
                    auto_vocab=True, min_count=3, top_n=30, prior_strength=None,
                    discover_kwargs=None, include_function_words=False):
    """
    code_texts: {code: [text, ...]}
    回傳 {code: [{term, z, log_odds, count_in, count_out, doc_freq}]}

    z 分數（Monroe et al. 2008）以整體語料為 Dirichlet 先驗，比較「本碼」與
    「其他所有碼」的對數勝算比。它會自動壓抑各碼共有的通用詞，
    也不會像純 TF-IDF 那樣被只出現一兩次的罕詞誤導。
    """
    all_texts = [t for ts in code_texts.values() for t in ts]
    if vocab is None and auto_vocab:
        vocab, _ = build_vocabulary(all_texts, lexicon, **(discover_kwargs or {}))
    if segmenter is None:
        force = sorted(vocab, key=len, reverse=True) if vocab else None
        segmenter = Segmenter(force_words=force)

    tok_by_code = {c: _tokenize_all(ts, segmenter, vocab) for c, ts in code_texts.items()}

    background = Counter()
    counts_by_code, docfreq_by_code = {}, {}
    for c, docs in tok_by_code.items():
        cnt, df = Counter(), Counter()
        for toks in docs:
            cnt.update(toks)
            df.update(set(toks))
        counts_by_code[c], docfreq_by_code[c] = cnt, df
        background.update(cnt)

    background = Counter({w: n for w, n in background.items() if n >= min_count})
    if not background:
        return {c: [] for c in code_texts}

    a0 = prior_strength or sum(background.values())
    bg_total = sum(background.values())
    alpha = {w: a0 * (n / bg_total) for w, n in background.items()}
    alpha_sum = sum(alpha.values())

    results = {}
    for c in code_texts:
        yi = counts_by_code[c]
        yj = Counter()
        for other, cnt in counts_by_code.items():
            if other != c:
                yj.update(cnt)
        ni = sum(yi[w] for w in background)
        nj = sum(yj[w] for w in background)
        rows = []
        for w, a_w in alpha.items():
            y_i, y_j = yi.get(w, 0), yj.get(w, 0)
            if y_i + y_j < min_count:
                continue
            num_i, den_i = y_i + a_w, ni + alpha_sum - y_i - a_w
            num_j, den_j = y_j + a_w, nj + alpha_sum - y_j - a_w
            if min(num_i, den_i, num_j, den_j) <= 0:
                continue
            delta = math.log(num_i / den_i) - math.log(num_j / den_j)
            var = 1.0 / num_i + 1.0 / num_j
            rows.append({
                "term": w,
                "z": round(delta / math.sqrt(var), 3) if var > 0 else 0.0,
                "log_odds": round(delta, 3),
                "count_in": y_i, "count_out": y_j,
                "doc_freq": docfreq_by_code[c].get(w, 0),
            })
        rows.sort(key=lambda r: -r["z"])
        # 功能詞在這裡不是「錯的」——某一組確實比較常說「沒有」是可報告的發現。
        # 但它不是術語，放在特徵詞清單裡只會擠掉真正有內容的詞。
        # 預設濾掉，需要時可用 include_function_words=True 取回。
        if not include_function_words:
            rows = [r for r in rows if not is_function_word(r["term"])]
        results[c] = rows[:top_n]
    return results


def code_texts_from_records(records):
    """{code: [segment text]}，供 induce_features 使用。"""
    out = {c: [] for c in S.CODES}
    for rec in records:
        for seg in rec.get(S.SEGMENTS, []):
            txt = segment_text(seg)
            if not txt:
                continue
            for code in S.codes_of(seg):
                out.setdefault(code, []).append(txt)
    return out


def merge_into_lexicon(lex, induced, min_z=2.0, max_per_code=15, dry_run=False):
    """把誘導出的特徵詞補進概念詞層。回傳實際新增的清單。"""
    added = []
    for code, rows in induced.items():
        dim, pol = S.split_code(code)
        if dim not in S.DIMENSIONS or pol not in S.POLARITIES:
            continue
        # 詞庫可能缺這個維度或這一極（例如詞庫是別的框架寫的、或是新加的
        # 維度）。缺就補一個空清單，而不是 KeyError——這裡是「把誘導結果
        # 寫回詞庫」，新維度沒有既有詞條本來就是正常狀態。
        pool = lex.setdefault(CONCEPT_TERMS, {}) \
                  .setdefault(dim, {}).setdefault(pol, [])
        existing = set(pool)
        for row in rows[:max_per_code]:
            w = row["term"]
            if row["z"] < min_z or w in existing:
                continue
            added.append({"code": code, S.DIMENSION: dim, S.POLARITY: pol,
                          "term": w, "z": row["z"]})
            if not dry_run:
                pool.append(w)
            existing.add(w)
    return added


# =====================================================================
# 5. 詞典式基準編碼器
# =====================================================================
class DictionaryCoder:
    """
    純詞典＋規則的編碼器，刻意做成透明可稽核的樣子。
    它的作用不是取代 LLM，是當對照組——展示詞典法在中文上會在哪裡失敗。
    """

    def __init__(self, lexicon, neg_window=6, pattern_weight=2.0,
                 quote_penalty=0.4, threshold=1.0):
        self.lex = lexicon
        self.neg_window = neg_window
        self.pattern_weight = pattern_weight
        self.quote_penalty = quote_penalty
        self.threshold = threshold
        self.neg = [w for w in lexicon.get(NEGATORS, []) if w]
        self.deg = [w for w in lexicon.get(INTENSIFIERS, []) if w]
        self.quote = [w for w in lexicon.get(REPORTED_SPEECH, []) if w]
        self.pivot = [w for w in lexicon.get(PIVOTS, []) if w]
        self.patterns = {}
        for pid, spec in (lexicon.get(PATTERNS) or {}).items():
            try:
                self.patterns[pid] = (re.compile(spec[PATTERN_REGEX]),
                                      spec[S.DIMENSION], spec[S.POLARITY],
                                      spec.get(PATTERN_NOTE, ""))
            except (re.error, KeyError):
                continue

    @staticmethod
    def _find_all(hay, needle):
        i, out = hay.find(needle), []
        while i >= 0:
            out.append(i)
            i = hay.find(needle, i + 1)
        return out

    def _pivot_weight(self, clause, pos):
        """「雖然…但是…」中，轉折之後才是受訪者的真實立場。"""
        if not self.pivot:
            return 1.0
        idxs = [i for p in self.pivot for i in self._find_all(clause, p)]
        if not idxs:
            return 1.0
        return 1.5 if pos > min(idxs) else 0.7

    def _flip(self, pol):
        """
        否定詞把極性翻到另一極。

        要防的失效：這裡若直接寫 `"N" if pol == "P" else "P"`：內建 RI 框架
        的極性剛好叫 P/N，所以看不出問題；但 esg_disclosure_probe.json 用的
        是 S/A，於是「不」「沒有」這些否定詞會把 S 翻成 P——一個這個框架裡
        根本不存在的極性值。接著 code_text() 找不到任何 (dim, S)／(dim, A)
        的分數，**靜默回傳空的 codes**，不報任何錯。

        這正是本檔 §244 自己寫下的那句話：靜默地把資料丟掉是最糟的失敗方式。

        兩極以外的情況不翻轉：三極以上的框架沒有「另一極」這個概念，硬翻
        等於替研究者發明一個它沒宣告的對立關係。
        """
        pols = list(S.POLARITIES)
        if len(pols) != 2 or pol not in pols:
            return pol
        return pols[1] if pol == pols[0] else pols[0]

    def _clause_score(self, clause):
        scores = defaultdict(float)
        hits = []
        is_quote = any(q in clause for q in self.quote)
        base = self.quote_penalty if is_quote else 1.0

        spans = []
        for dim in S.DIMENSIONS:
            for pol in S.POLARITIES:
                for term in self.lex[CONCEPT_TERMS][dim][pol]:
                    if not term:
                        continue
                    for pos in self._find_all(clause, term):
                        spans.append({"start": pos, "end": pos + len(term),
                                      "term": term, "dim": dim, "pol": pol})

        # 最長匹配去重：「關係人」在「利害關係人」內部，不去重會雙倍計分
        spans.sort(key=lambda s: (-(s["end"] - s["start"]), s["start"]))
        kept = []
        for s in spans:
            if any(k["start"] <= s["start"] and s["end"] <= k["end"] for k in kept):
                continue
            kept.append(s)

        for s in kept:
            pos, dim, pol, term = s["start"], s["dim"], s["pol"], s["term"]
            window = clause[max(0, pos - self.neg_window):pos]
            negated = any(n in window for n in self.neg)
            boosted = any(d in window for d in self.deg)
            w = base * (1.5 if boosted else 1.0) * self._pivot_weight(clause, pos)
            eff = self._flip(pol) if negated else pol
            scores[(dim, eff)] += w
            hits.append({"kind": "term", "term": term, S.DIMENSION: dim,
                         "source_polarity": pol, "effective_polarity": eff,
                         "negated": negated, "reported": is_quote,
                         "weight": round(w, 2)})

        for pid, (rx, dim, pol, _note) in self.patterns.items():
            m = rx.search(clause)
            if not m:
                continue
            window = clause[max(0, m.start() - self.neg_window):m.start()]
            # 只有第一極（框架宣告的正向）的句式會被否定翻轉；
            # 負向句式的 regex 本身多半就含否定詞，再翻一次會翻回去
            _pols = list(S.POLARITIES)
            negated = (bool(_pols) and pol == _pols[0]
                       and any(n in window for n in self.neg))
            eff = self._flip(pol) if negated else pol
            w = base * self.pattern_weight * self._pivot_weight(clause, m.start())
            scores[(dim, eff)] += w
            hits.append({"kind": "pattern", "term": pid, S.DIMENSION: dim,
                         "source_polarity": pol, "effective_polarity": eff,
                         "negated": negated, "reported": is_quote,
                         "weight": round(w, 2)})
        return scores, hits

    def code_text(self, text):
        """回傳 (codes, scores, hits)。"""
        total = defaultdict(float)
        all_hits = []
        for clause in iter_clauses(text):
            s, h = self._clause_score(clause)
            for k, v in s.items():
                total[k] += v
            all_hits.extend(h)
        # 每個維度取得分最高的那一極。極性名稱由框架決定——寫死 "P"/"N"
        # 會讓極性值不同的框架（ESG 用 S/A）兩個 .get() 都拿到 0.0，
        # abs(p-n) < 1e-9 恆成立，於是這支編碼器**永遠回空清單而不報錯**。
        codes = []
        pols = list(S.POLARITIES)
        for dim in S.DIMENSIONS:
            if not pols:                       # 無極性框架：只判維度在不在
                v = total.get((dim, None), 0.0) or total.get(dim, 0.0)
                if v >= self.threshold:
                    codes.append(S.code_of(dim))
                continue
            vals = sorted(((total.get((dim, p), 0.0), p) for p in pols),
                          reverse=True)
            top_v, top_p = vals[0]
            second_v = vals[1][0] if len(vals) > 1 else 0.0
            # 平手不編碼：兩極分數一樣時沒有理由挑任何一邊
            if top_v < self.threshold or abs(top_v - second_v) < 1e-9:
                continue
            codes.append(S.code_of(dim, top_p))
        scores = {S.code_of(d, p): round(total.get((d, p), 0.0), 2)
                  for d in S.DIMENSIONS for p in S.POLARITIES}
        return codes, scores, all_hits


# =====================================================================
# 6. 一致度與稽核
# =====================================================================
def cohens_kappa(a, b):
    """兩組二元標記的 Cohen's κ。無變異時回傳 nan（κ 在此無定義）。"""
    if len(a) != len(b) or not a:
        return float("nan")
    n = len(a)
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1, pb1 = sum(a) / n, sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if abs(1 - pe) < 1e-12:
        return float("nan")
    return (po - pe) / (1 - pe)


def compare_coders(records, coder):
    """LLM 編碼 vs 詞典編碼，逐碼計算 κ 與 precision/recall/F1。"""
    seg_rows = []
    for rec in records:
        for seg in rec.get(S.SEGMENTS, []):
            txt = segment_text(seg)
            if not txt:
                continue
            llm = set(S.codes_of(seg))
            dic, scores, _ = coder.code_text(txt)
            seg_rows.append({S.RESPONDENT: rec.get(S.RESPONDENT, "unknown"),
                             S.SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                             "text": txt, "llm_codes": llm,
                             "dict_codes": set(dic), "scores": scores})
    per_code = []
    for c in S.CODES:
        a = [1 if c in r["llm_codes"] else 0 for r in seg_rows]
        b = [1 if c in r["dict_codes"] else 0 for r in seg_rows]
        tp = sum(1 for x, y in zip(a, b) if x and y)
        fp = sum(1 for x, y in zip(a, b) if not x and y)
        fn = sum(1 for x, y in zip(a, b) if x and not y)
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec_ = tp / (tp + fn) if tp + fn else float("nan")
        f1 = (2 * prec * rec_ / (prec + rec_)
              if prec == prec and rec_ == rec_ and (prec + rec_) > 0 else float("nan"))
        k = cohens_kappa(a, b)
        per_code.append({
            "code": c, "llm_count": sum(a), "dict_count": sum(b),
            "tp": tp, "dict_extra": fp, "dict_missed": fn,
            "precision": None if prec != prec else round(prec, 3),
            "recall": None if rec_ != rec_ else round(rec_, 3),
            "f1": None if f1 != f1 else round(f1, 3),
            "kappa": None if k != k else round(k, 3),
        })
    oa = [1 if c in r["llm_codes"] else 0 for r in seg_rows for c in S.CODES]
    ob = [1 if c in r["dict_codes"] else 0 for r in seg_rows for c in S.CODES]
    k_all = cohens_kappa(oa, ob)
    summary = {"segments": len(seg_rows),
               "overall_kappa": None if k_all != k_all else round(k_all, 3),
               "llm_total": sum(oa), "dict_total": sum(ob)}
    return per_code, summary, seg_rows


def audit_llm_coding(seg_rows, miss_threshold=2.0):
    """
    疑似過度詮釋 — LLM 標了某碼，但該段沒有任何該碼的詞彙或句式證據
    疑似漏標     — 詞典證據很強，LLM 卻沒標（recall 的估計材料）
    """
    over, miss = [], []
    for r in seg_rows:
        for c in r["llm_codes"]:
            if r["scores"].get(c, 0) == 0:
                over.append({S.RESPONDENT: r[S.RESPONDENT],
                             S.SEGMENT_ID: r[S.SEGMENT_ID], "code": c,
                             "dict_score": 0.0, "text": r["text"][:120]})
        for c in S.CODES:
            if c not in r["llm_codes"] and r["scores"].get(c, 0) >= miss_threshold:
                miss.append({S.RESPONDENT: r[S.RESPONDENT],
                             S.SEGMENT_ID: r[S.SEGMENT_ID], "code": c,
                             "dict_score": r["scores"][c], "text": r["text"][:120]})
    over.sort(key=lambda x: (x[S.RESPONDENT], x[S.SEGMENT_ID]))
    miss.sort(key=lambda x: -x["dict_score"])
    return over, miss
