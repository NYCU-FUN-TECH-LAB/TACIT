"""
tacit_schema.py — 資料結構的單一事實來源（Single Source of Truth）
=================================================================
把「內部識別碼」與「顯示標籤」徹底分開。

【為什麼要做這件事】
  舊格式的紀錄用中文字串同時當三種東西：JSON 鍵名、DataFrame 欄名、畫面文字，
  「受訪者」這個字串身兼資料鍵與 UI 標籤。
  要做多語版就必須拆開，否則一翻譯就會同時破壞存檔相容性與匯出格式。

  本模組定義所有 ASCII 內部識別碼；顯示文字一律交給 tacit_i18n。
  規則很簡單：**程式邏輯只認這裡的常數，畫面上的字一律查 i18n。**

【向後相容】
  舊檔案（v1 巢狀中文鍵、v2 PRO 扁平中文鍵）由 migrate_record() 自動轉換，
  使用者不需要做任何事，也不會遺失資料。轉換是單向的：讀進來就是新格式。
"""

import re

import tacit_framework as F

SCHEMA_VERSION = 3

# =====================================================================
# 1. 維度與極性 —— 由作用中框架推導，不再寫死
# =====================================================================
# 這些字串只是「內建 RI 框架剛好使用的識別碼」，留著是為了讓程式碼與測試
# 讀起來清楚；真正的權威來源是 tacit_framework.active()。
ANTICIPATION = "anticipation"
REFLEXIVITY = "reflexivity"
ENGAGEMENT = "engagement"
RESPONSIVENESS = "responsiveness"
UNASSIGNED = F.UNASSIGNED

POSITIVE, NEGATIVE = "P", "N"

# 舊資料用中文當維度值，讀檔時要能認得（僅適用內建 RI 框架的舊檔）
DIM_FROM_ZH = {"預期": ANTICIPATION, "反思性": REFLEXIVITY,
               "參與": ENGAGEMENT, "回應性": RESPONSIVENESS, "未歸屬": UNASSIGNED}

# 下列名稱改由 __getattr__ 動態解析，切換框架後立即生效：
#   DIMENSIONS, AGG_DIMENSIONS, POLARITIES, DIM_SHORT, SHORT_DIM, CODES
_DYNAMIC = {
    "DIMENSIONS":     lambda fw: fw.dimensions,
    "AGG_DIMENSIONS": lambda fw: fw.agg_dimensions,
    # 無極性的框架回空清單，**不可以**退回 [P, N]。
    #
    # 要防的失效：這裡若寫 `fw.polarity_values or [POSITIVE, NEGATIVE]`，那個
    # or 把「這個框架沒有極性」悄悄變成「這個框架有 P 和 N」，於是 UTAUT 這
    # 種無極性框架在詞庫模組裡會被建出 {dim: {"P": [], "N": []}} 的空殼，
    # lexicon_stats() 也會列出八格根本不存在的統計。空清單才是實話；呼叫端
    # 要嘛先問 has_polarity，要嘛就得處理得了空清單。
    "POLARITIES":     lambda fw: list(fw.polarity_values),
    "DIM_SHORT":      lambda fw: fw.dim_short,
    "SHORT_DIM":      lambda fw: fw.short_dim,
    "CODES":          lambda fw: fw.codes,
    "HAS_POLARITY":   lambda fw: fw.has_polarity,
    # 屬性欄位與維度一樣跟著框架走。UNSPECIFIED 在這裡統一補進每個欄位的
    # 合法值，框架檔不必自己記得寫——漏寫會讓「未標註」變成非法值，
    # 而那是每一份真實資料都會用到的狀態。
    "DESCRIPTOR_FIELDS": lambda fw: {k: list(v) + [UNSPECIFIED]
                                     for k, v in fw.descriptors.items()},
    "DESCRIPTOR_KEYS":   lambda fw: list(fw.descriptors),
}


def __getattr__(name):
    """PEP 562：讓維度相關的模組屬性跟著作用中框架走。"""
    if name in _DYNAMIC:
        return _DYNAMIC[name](F.active())
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def framework():
    return F.active()


def code_of(dimension, polarity=None):
    return F.active().code_of(dimension, polarity)


def split_code(code):
    """回傳 (dimension_id, polarity)；無極性框架時 polarity 為 None。"""
    return F.active().split_code(code)


# =====================================================================
# 2. 記錄欄位（一筆＝一位受訪者）
# =====================================================================
RESPONDENT = "respondent"
DESCRIPTORS = "descriptors"
SEGMENTS = "segments"
DELETED_SEGMENTS = "deleted_segments"
SUMMARY = "summary"
TRANSCRIPT = "transcript"
# 原始逐字稿的檔名。用途不是顯示，而是讓「這份跑過了沒有」可以被判斷——
# 分析中途若 API 配額用盡，換金鑰後應該只跑剩下的，不該把已完成的重跑一遍。
TRANSCRIPT_FILE = "transcript_file"
META = "_meta"

# 段落欄位
SEGMENT_ID = "segment_id"
TITLE = "title"
QUOTE = "quote"
FULL_TEXT = "full_text"
CODES_F = "codes"
DIMENSION = "dimension"
POLARITY = "polarity"
RATIONALE = "rationale"

# 複核欄位
REVIEW = "review"
STATUS = "status"
ORIGINAL_CODES = "original_codes"
ORIGINAL_TITLE = "original_title"
ORIGINAL_QUOTE = "original_quote"
SOURCE = "source"
HISTORY = "history"

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"
STATUS_MODIFIED = "modified"
STATUS_ADDED = "added"
STATUS_DELETED = "deleted"
ALL_STATUS = [STATUS_PENDING, STATUS_CONFIRMED, STATUS_MODIFIED,
              STATUS_ADDED, STATUS_DELETED]

SOURCE_AI = "ai"
SOURCE_HUMAN = "human"

# =====================================================================
# 3. 受訪者屬性（descriptors）
# =====================================================================
UNSPECIFIED = "unspecified"

# DESCRIPTOR_FIELDS / DESCRIPTOR_KEYS 改由 __getattr__ 向作用中框架取得
# （見上方 _DYNAMIC）。維度與屬性都跟著框架走，程式裡不再有任何一種語料
# 的形狀被寫死。UNSPECIFIED 一律由這裡補上，框架不必自己記得寫。
DESCRIPTOR_BASIS = "descriptor_basis"

# 舊檔的中文屬性值 → 新識別碼
_DESC_VALUE_FROM_ZH = {
    "產業界": "industry", "學術界": "academia", "政府部門": "government",
    "非營利組織": "nonprofit", "研究法人": "research_institute",
    "高階主管": "senior_management", "中階管理": "middle_management",
    "研發人員": "rnd_staff", "研究者": "researcher", "政策制定者": "policy_maker",
    "資通訊/AI": "ict_ai", "生技醫療": "biomedical", "能源/永續": "energy_sustainability",
    "製造業": "manufacturing", "農業科技": "agritech", "金融": "finance",
    "5年以下": "under_5y", "6-10年": "6_10y", "11-20年": "11_20y",
    "20年以上": "over_20y",
    "其他": "other", "未標註": UNSPECIFIED,
}
_DESC_KEY_FROM_ZH = {"機構類型": "institution_type", "職位層級": "role_level",
                     "產業領域": "sector", "年資區間": "experience",
                     "屬性判定依據": DESCRIPTOR_BASIS}

# =====================================================================
# 4. 主題（themes）
# =====================================================================
THEME_ID = "theme_id"
THEME_NAME = "name"
THEME_DEFINITION = "definition"
AGG_DIMENSION = "aggregate_dimension"
DIM_RATIONALE = "dimension_rationale"
FRAME_RELATION = "frame_relation"
POLARITY_TENDENCY = "polarity_tendency"
MEMBER_IDS = "member_ids"
MERGED_FROM = "merged_from"

RELATION_ALIGNED, RELATION_EXTENDS, RELATION_CHALLENGES = "aligned", "extends", "challenges"
FRAME_RELATIONS = [RELATION_ALIGNED, RELATION_EXTENDS, RELATION_CHALLENGES]
TENDENCY_MIXED = "mixed"
POLARITY_TENDENCIES = [POSITIVE, NEGATIVE, TENDENCY_MIXED]

_REL_FROM_ZH = {"契合": RELATION_ALIGNED, "延伸": RELATION_EXTENDS,
                "挑戰": RELATION_CHALLENGES}
_TEND_FROM_ZH = {"混合": TENDENCY_MIXED, "P": POSITIVE, "N": NEGATIVE}

# =====================================================================
# 5. 信度檢定（IRR）
# =====================================================================
UNIT_ID = "unit_id"
SPEAKER = "speaker"
TEXT = "text"
STRATUM = "stratum"
AI_CODES = "ai_codes"
STRATUM_UNMARKED = "__unmarked__"
NONE_LABEL = "__none__"

SESSION_ID = "session_id"
SEED = "seed"
NOTE = "note"
CODERS = "coders"
UNITS = "units"
HUMAN_CODINGS = "human_codings"


# =====================================================================
# 6. 正規化工具
# =====================================================================
def norm_dimension(v):
    """
    把任意來源寫的維度名稱收斂成識別碼；認不出來就回 None。

    為什麼不能只做精確比對
    ----------------------
    要防的失效：主題歸納的 Gioia 圖表永遠只長出三個維度，第四個
    （responsiveness）完全消失。原因不是模型沒判斷出那個維度，而是它寫的是
    "Responsiveness"——首字大寫。精確比對認不得，於是靜靜地落到 unassigned，
    畫面上看起來就像「資料裡沒有這個維度」。

    這種錯最惡劣的地方在於它不會報錯，而且結論看起來完全合理：研究者會以為
    受訪者真的沒談到回應性，然後把這個「發現」寫進論文。

    地端模型比雲端模型更常這樣寫。既然大小寫、前後空白、把標籤而不是識別碼
    填進來都不改變作者的意思，就該一律接受。不接受的只有真正認不出來的值,
    那時回 None，由呼叫端標成 unassigned——那才是誠實的「未歸屬」。

    接受的形式：識別碼、短代碼（ANT/RES…）、任一語言的顯示標籤、
    以及舊檔的中文值；一律忽略大小寫與前後空白。
    """
    if v is None:
        return None
    if not isinstance(v, str):
        v = str(v)
    raw = v.strip()
    if not raw:
        return None
    if raw in DIM_FROM_ZH:                       # 舊檔的中文值，精確比對優先
        return DIM_FROM_ZH[raw]

    fw = F.active()
    valid = fw.agg_dimensions
    if raw in valid:                             # 最常見的情形，先走捷徑
        return raw

    key = raw.casefold()
    lookup = {}
    for d in valid:
        lookup[d.casefold()] = d
        short = fw.dim_short.get(d)
        if short:
            lookup[short.casefold()] = d
        for lang in ("en", "zh"):
            if d == UNASSIGNED:
                lookup[F.UNASSIGNED_LABEL.get(lang, "").casefold()] = d
            else:
                lab = fw.label(d, lang)
                if lab:
                    lookup[lab.casefold()] = d
    lookup.pop("", None)
    if key in lookup:
        return lookup[key]

    # 帶了雜訊的寫法：切開之後看看能認出幾個維度。
    #
    # 只認出一個 → 就是它。例如 "responsiveness (capacity to change)"。
    #
    # 認出兩個以上 → 回 None。實測發現 qwen2.5:7b 會把輸出格式裡的列舉
    # 原樣抄回來，寫成 "engagement|responsiveness"——它根本沒有選。
    # 這種時候替它挑第一個，等於把工具的猜測偽裝成研究者的判斷，而且
    # 挑錯了也看不出來。落到 unassigned 至少會出現在「未歸屬」計數裡，
    # 研究者看得到、查得到。這是本工具一貫的取捨：寧可不給答案，
    # 也不給一個看不出是錯的答案。
    parts = [p.strip() for p in re.split(r"[(（)）\-—/|:：,，、]", key)]
    found = {lookup[p] for p in parts if p in lookup}
    return found.pop() if len(found) == 1 else None


def norm_polarity(v):
    """無極性框架一律回 None——極性在那種框架下沒有意義。"""
    fw = F.active()
    if not fw.has_polarity:
        return None
    v = str(v or "").strip().upper()
    return v if v in fw.polarity_values else None


def descriptor_fields():
    """
    作用中框架的屬性欄位 {欄位: [合法值…]}，含 UNSPECIFIED。

    模組**內部**一律走這個函式，不要用裸名稱 DESCRIPTOR_FIELDS：PEP 562 的
    __getattr__ 只攔得到從模組外部來的存取，同一個檔案裡的裸名稱會直接
    NameError。維度那幾個常數沒有這個問題，是因為模組內剛好沒有人用。
    """
    return {k: list(v) + [UNSPECIFIED] for k, v in F.active().descriptors.items()}


def descriptor_keys():
    return list(F.active().descriptors)


def blank_descriptors():
    d = {k: UNSPECIFIED for k in descriptor_keys()}
    d[DESCRIPTOR_BASIS] = ""
    return d


def norm_descriptors(raw):
    """把任意來源（AI 輸出、舊檔、人工編輯）的屬性收斂為合法識別碼。"""
    out = blank_descriptors()
    if not isinstance(raw, dict):
        return out
    conv = {}
    for k, v in raw.items():
        key = _DESC_KEY_FROM_ZH.get(k, k)
        conv[key] = v
    for key, allowed in descriptor_fields().items():
        v = conv.get(key)
        v = _DESC_VALUE_FROM_ZH.get(v, v)
        if v in allowed:
            out[key] = v
        elif v in (None, "", UNSPECIFIED):
            out[key] = UNSPECIFIED
        else:
            out[key] = "other"
    out[DESCRIPTOR_BASIS] = str(conv.get(DESCRIPTOR_BASIS, "") or "").strip()
    return out


def make_code(dimension, polarity=None, rationale=""):
    if not F.active().has_polarity:
        polarity = None
    return {DIMENSION: dimension, POLARITY: polarity, RATIONALE: rationale or ""}


def codes_of(segment):
    """
    段落目前的編碼字串集合（排序後）。有極性→['REF-N']；無極性→['REF']。

    **這是集合，不是清單。** 一個段落若被指派兩個同維度同極性但理由不同的
    碼，這裡只會回傳一個字串——分析層以 (段落, 維度, 極性) 為單位，同一段
    話在同一個維度上被計兩次會扭曲共現與 Jaccard。

    因此「紀錄裡的編碼數」與「分析用的編碼數」可以不相等，示範語料就是
    184 對 181。兩個都對，但它們回答的是不同的問題，任何一份報告都必須
    講明用的是哪一個。紀錄那一側不再去重（見 _migrate_codes），研究者寫下的
    每一個判斷都留著。
    """
    fw = F.active()
    out = set()
    for c in segment.get(CODES_F) or []:
        d = norm_dimension(c.get(DIMENSION))
        if d is None or d not in fw.dimensions:
            continue
        if fw.has_polarity:
            p = norm_polarity(c.get(POLARITY))
            if p:
                out.add(fw.code_of(d, p))
        else:
            out.add(fw.code_of(d))
    return sorted(out)


# =====================================================================
# 7. 舊檔遷移
# =====================================================================
_LEGACY_SEG = {"段落ID": SEGMENT_ID, "標題": TITLE, "精簡引文": QUOTE,
               "完整原文": FULL_TEXT}
_LEGACY_REVIEW = {"狀態": STATUS, "原始編碼": ORIGINAL_CODES,
                  "原始標題": ORIGINAL_TITLE, "原始精簡引文": ORIGINAL_QUOTE,
                  "來源": SOURCE, "編輯紀錄": HISTORY}
_STATUS_FROM_ZH = {"未審核": STATUS_PENDING, "已確認": STATUS_CONFIRMED,
                   "已修改": STATUS_MODIFIED, "人工新增": STATUS_ADDED,
                   "已刪除": STATUS_DELETED}


# 編碼在遷移時被丟棄的三種理由。呼叫端可據此決定要擋下、警告，還是忽略。
DROP_UNKNOWN_DIMENSION = "unknown_dimension"
DROP_NO_POLARITY = "no_polarity"
DROP_DUPLICATE = "duplicate"
DROP_MALFORMED = "malformed"
DROP_ABSENCE_RATIONALE = "absence_as_evidence"

# 以「這段話沒有表現出 X」為理由的編碼。
#
# 要防的失效：模型對一段純粹在描述開發流程的話產生了 REF-N，理由寫
# 「未表現出對自身假設或知識邊界的反省，僅強調遵循既定流程」。沉默不是
# 證據——這是憑空生出一筆資料，而且它會直接進到交叉表、共現矩陣與極性
# 指數裡，讓「這個人比較自負」變成一個有數字支撐的結論。
#
# 提示詞裡已經明文禁止，但提示詞是請求不是保證；模型不照做是常態，而這
# 一種不照做特別危險，因為產出看起來完全正常。所以在資料層再擋一次。
#
# 只比對**理由**，不碰引文與原文。
#
# 【規則不能寫得太寬】
# 把「缺乏」「absence of」「there is no」也算進去的話，示範語料會掉
# 14 個編碼、12 個段落整段消失。看被擋掉的內容才發現規則混淆了兩件完全
# 不同的事：
#
#   (a) **編碼者**說：這段話沒有表現出 X。          → 憑空生資料，要擋
#   (b) **受訪者**說：我們沒有這樣的機制。          → 這就是證據，要留
#
# 「The absence of a review mechanism is stated plainly, including the
# respondent's own inaction」是 (b)：受訪者親口說了沒有覆核機制，那正是
# 回應性負向最紮實的證據。擋掉它等於把真正的發現丟掉。
#
# 分界線是**誰的缺席**：(a) 講的是文本有沒有展現出什麼，用的是展示類詞彙
# （show / demonstrate / evidence / 表現出 / 顯示 / 看不出）；(b) 講的是
# 受訪者描述的世界裡缺了什麼東西（no trigger、缺乏覆核機制）。所以只比對
# 展示類詞彙，不比對「沒有某個東西」。
_ABSENCE_PATTERNS = [
    # 英文：談的是「文本沒有展現出」
    r"\b(?:does|did|do)\s*n[o']t\s+(?:show|demonstrate|exhibit|display"
    r"|reflect|indicate|reveal|evidence|mention|articulate)\b",
    r"\bfail(?:s|ed|ing)?\s+to\s+(?:show|demonstrate|exhibit|display|reflect"
    r"|indicate|reveal|evidence|mention|acknowledge|articulate)\b",
    r"\bno\s+(?:evidence|indication|sign|mention|trace)\s+of\b",
    r"\bnot\s+(?:shown|demonstrated|evidenced|evident|articulated)\b",
    r"\bnothing\s+(?:here|in\s+this\s+(?:passage|excerpt|segment|quote))\b",
    r"\bthe\s+(?:passage|excerpt|segment|quote|speaker)\s+(?:does\s*n[o']t|"
    r"never)\s+(?:show|demonstrate|exhibit|reflect|indicate)\b",
    # 中文（繁簡都要，模型兩種都會吐）：一樣只抓展示類詞彙
    r"未(?:表現出|表现出|展現|展现|顯示|显示|呈現|呈现|體現|体现)",
    r"沒有(?:表現|展現|顯示|呈現|體現)",
    r"没有(?:表现|展现|显示|呈现|体现)",
    r"並未(?:表現|展現|顯示|呈現|體現)|并未(?:表现|展现|显示|呈现|体现)",
    r"看不出|無法看出|无法看出|不足以顯示|不足以显示|未見(?:任何)?(?:證據|跡象)",
    r"(?:本段|這段|该段|此段)[^，。；]{0,12}(?:沒有|没有|未)",
]
_ABSENCE_RE = re.compile("|".join(_ABSENCE_PATTERNS), re.IGNORECASE)


def is_absence_rationale(text):
    """
    理由是不是在說「**這段話**沒有表現出 X」。

    是的話那不是證據，是缺席——要擋。但「受訪者說他們沒有覆核機制」不算，
    那是受訪者描述的世界裡缺了東西，是真正的負向證據。
    """
    return bool(_ABSENCE_RE.search(str(text or "")))


def _migrate_codes(raw, dropped=None, segment_id=""):
    """
    段落編碼的遷移。**丟掉任何一個碼都必須留下紀錄。**

    要防的失效一（去重過度）：去重鍵若是 (dimension, polarity)，同一個
    段落裡若有兩個「同維度同極性但理由不同」的碼，第二個會被靜默吃掉。
    示範語料就有三筆，造成 make_demo_data.py 印出 184 個編碼、磁碟上也存了
    184 個，但任何分析讀進來只剩 181 個——而且沒有任何地方說過這件事。
    理由是編碼的內容，不是註解；兩個理由不同的碼是兩個判斷，不是重複。
    真正的重複（三個欄位都一樣）才合併。

    要防的失效二（換框架全滅）：`d not in F.active().dimensions` 這個條件會把
    「用別的框架編過的碼」整批丟掉。用 UTAUT 開啟 RI 編過的檔案，148 段的
    編碼在載入當下全部消失，介面一聲不吭，接著隨手一存就永久覆蓋原檔。
    這裡改成照樣回報；擋下載入的責任在呼叫端（見 framework_mismatch）。

    dropped 傳入一個 list 時，每一筆被丟棄的碼都會附上理由 append 進去。
    不傳則行為與過去相同，只是不再過度去重。
    """
    out, seen = [], set()

    def _note(reason, code):
        if dropped is not None:
            dropped.append({"segment_id": segment_id, "reason": reason,
                            "dimension": code.get(DIMENSION, code.get("維度")),
                            "polarity": code.get(POLARITY, code.get("極性")),
                            "rationale": code.get(RATIONALE, code.get("理由", ""))})

    for c in raw or []:
        if not isinstance(c, dict):
            if dropped is not None:
                dropped.append({"segment_id": segment_id,
                                "reason": DROP_MALFORMED, "dimension": None,
                                "polarity": None, "rationale": str(c)[:80]})
            continue
        d = norm_dimension(c.get(DIMENSION, c.get("維度")))
        p = norm_polarity(c.get(POLARITY, c.get("極性")))
        r = c.get(RATIONALE, c.get("理由", "")) or ""
        fw = F.active()
        if d not in fw.dimensions:
            _note(DROP_UNKNOWN_DIMENSION, c)
            continue
        # 只有「有極性的框架」才要求極性。
        #
        # 要防的失效：這裡若無條件寫 `if not p: drop`：norm_polarity() 對
        # 無極性框架**一律回 None**（那是對的，極性在那種框架下沒有意義），
        # 於是任何一筆在無極性框架下遷移的紀錄，**每一個碼都會被丟掉**，
        # 整份分析變成空的。
        #
        # 這種錯不容易看見：紀錄若是直接塞進 session_state、沒經過遷移，
        # 無極性框架就不會走到 migrate_record。這跟極性值寫死 "P"/"N"
        # 是同一種病——無極性那條路要有測試走過。
        if fw.has_polarity and not p:
            _note(DROP_NO_POLARITY, c)
            continue
        # 以缺席為證據的碼一律丟棄並回報。丟掉是對的：留下來它會混進交叉表
        # 與極性指數，而使用者沒有辦法從最終的數字裡看出哪些是這樣來的。
        if is_absence_rationale(r):
            _note(DROP_ABSENCE_RATIONALE, c)
            continue
        # 去重鍵含理由：理由不同就是不同的判斷。
        key = (d, p, r.strip())
        if key in seen:
            _note(DROP_DUPLICATE, c)
            continue
        seen.add(key)
        out.append(make_code(d, p, r))
    return out


def _migrate_segment(raw, index, dropped=None):
    seg = {}
    for zh, en in _LEGACY_SEG.items():
        seg[en] = raw.get(en, raw.get(zh, ""))
    seg[SEGMENT_ID] = seg.get(SEGMENT_ID) or f"S{index:03d}"
    seg[CODES_F] = _migrate_codes(raw.get(CODES_F, raw.get("編碼")),
                                  dropped=dropped,
                                  segment_id=seg[SEGMENT_ID])

    rv = raw.get(REVIEW, raw.get("審核"))
    if isinstance(rv, dict):
        new_rv = {}
        for zh, en in _LEGACY_REVIEW.items():
            new_rv[en] = rv.get(en, rv.get(zh))
        new_rv[STATUS] = _STATUS_FROM_ZH.get(new_rv.get(STATUS), new_rv.get(STATUS)) \
            or STATUS_PENDING
        new_rv[SOURCE] = {"AI": SOURCE_AI, "人工": SOURCE_HUMAN}.get(
            new_rv.get(SOURCE), new_rv.get(SOURCE) or SOURCE_AI)
        new_rv[ORIGINAL_CODES] = list(new_rv.get(ORIGINAL_CODES) or [])
        new_rv[ORIGINAL_TITLE] = new_rv.get(ORIGINAL_TITLE) or ""
        new_rv[ORIGINAL_QUOTE] = new_rv.get(ORIGINAL_QUOTE) or ""
        hist = []
        for e in (new_rv.get(HISTORY) or []):
            if isinstance(e, dict):
                hist.append({
                    "time": e.get("time", e.get("時間", "")),
                    "action": e.get("action", e.get("動作", "")),
                    "detail": e.get("detail", e.get("說明", "")),
                    "reviewer": e.get("reviewer", e.get("複核者", "")),
                })
        new_rv[HISTORY] = hist
        seg[REVIEW] = new_rv
    return seg


def _is_legacy_v1(raw):
    """v1 格式：頂層直接掛四個中文維度名，底下是 {'P': [...], 'N': [...]}"""
    return any(k in raw for k in DIM_FROM_ZH) and \
        SEGMENTS not in raw and "編碼段落" not in raw


def _from_v1(raw):
    """v1 巢狀 → 扁平。以完整原文去重合併，還原多重編碼。"""
    segments, index = [], {}
    for zh_dim, dim in DIM_FROM_ZH.items():
        if dim == UNASSIGNED:
            continue
        block = raw.get(zh_dim)
        if not isinstance(block, dict):
            continue
        for pol in F.active().polarity_values:
            for q in (block.get(pol) or []):
                if not isinstance(q, dict):
                    continue
                full = (q.get("完整原文") or q.get("精簡引文") or "").strip()
                key = full or f"__{len(segments)}"
                if key not in index:
                    index[key] = {
                        SEGMENT_ID: f"S{len(segments) + 1:03d}",
                        TITLE: q.get("標題", ""),
                        QUOTE: q.get("精簡引文", ""),
                        FULL_TEXT: full,
                        CODES_F: [],
                    }
                    segments.append(index[key])
                index[key][CODES_F].append(make_code(dim, pol, "migrated from v1"))
    return segments


def migrate_record(raw, dropped=None):
    """
    任何版本的單筆紀錄 → 目前的 schema。這是唯一的入口，
    所有讀檔路徑都必須經過它，否則新舊格式會在記憶體裡混在一起。

    dropped 傳入一個 list 時，遷移過程中被丟棄的每一個編碼都會附上理由
    append 進去。呼叫端該拿它做什麼，取決於理由：unknown_dimension 通常
    代表框架選錯了（見 framework_mismatch），該擋下來而不是照樣載入。
    """
    if not isinstance(raw, dict):
        raise ValueError("record must be a dict")

    if _is_legacy_v1(raw):
        segments = _from_v1(raw)
    else:
        src = raw.get(SEGMENTS, raw.get("編碼段落")) or []
        segments = [_migrate_segment(s, i + 1, dropped=dropped)
                    for i, s in enumerate(src) if isinstance(s, dict)]
        segments = [s for s in segments if s[CODES_F] or
                    (s.get(REVIEW, {}).get(SOURCE) == SOURCE_HUMAN)]

    deleted_src = raw.get(DELETED_SEGMENTS, raw.get("已刪除段落")) or []
    deleted = [_migrate_segment(s, i + 1, dropped=dropped)
               for i, s in enumerate(deleted_src) if isinstance(s, dict)]

    rec = {
        RESPONDENT: raw.get(RESPONDENT, raw.get("受訪者", "unknown")) or "unknown",
        DESCRIPTORS: norm_descriptors(raw.get(DESCRIPTORS, raw.get("屬性"))),
        SEGMENTS: segments,
        DELETED_SEGMENTS: deleted,
        SUMMARY: raw.get(SUMMARY, raw.get("維度重點分析", "")) or "",
        META: raw.get(META) or {"schema_version": SCHEMA_VERSION},
    }
    if raw.get(TRANSCRIPT) or raw.get("逐字稿"):
        rec[TRANSCRIPT] = raw.get(TRANSCRIPT) or raw.get("逐字稿")
    if raw.get(TRANSCRIPT_FILE) or raw.get("逐字稿檔名"):
        rec[TRANSCRIPT_FILE] = raw.get(TRANSCRIPT_FILE) or raw.get("逐字稿檔名")
    rec[META]["schema_version"] = SCHEMA_VERSION
    for k in ("_source", "_file", "_來源", "_檔名"):
        if raw.get(k):
            rec[{"_來源": "_source", "_檔名": "_file"}.get(k, k)] = raw[k]
    return rec


def migrate_theme(raw, index=1):
    t = dict(raw or {})
    dim = norm_dimension(t.get(AGG_DIMENSION, t.get("聚合維度")))
    rel = t.get(FRAME_RELATION, t.get("框架關係"))
    tend = t.get(POLARITY_TENDENCY, t.get("極性傾向"))
    return {
        THEME_ID: t.get(THEME_ID, t.get("主題ID")) or f"T{index:02d}",
        THEME_NAME: t.get(THEME_NAME, t.get("主題名稱", "")),
        THEME_DEFINITION: t.get(THEME_DEFINITION, t.get("主題定義", "")),
        AGG_DIMENSION: dim if dim in F.active().agg_dimensions else UNASSIGNED,
        DIM_RATIONALE: t.get(DIM_RATIONALE, t.get("維度歸屬理由", "")),
        FRAME_RELATION: _REL_FROM_ZH.get(rel, rel if rel in FRAME_RELATIONS
                                         else RELATION_ALIGNED),
        POLARITY_TENDENCY: _TEND_FROM_ZH.get(tend, tend if tend in POLARITY_TENDENCIES
                                             else TENDENCY_MIXED),
        MEMBER_IDS: list(t.get(MEMBER_IDS, t.get("構成ID")) or []),
        MERGED_FROM: list(t.get(MERGED_FROM, t.get("合併自")) or []),
    }


def record_framework_id(raw):
    """紀錄是用哪個框架編出來的。舊檔沒有這個欄位時回 None。"""
    if not isinstance(raw, dict):
        return None
    fid = (raw.get(META) or {}).get(F.FRAMEWORK_ID)
    return str(fid) if fid else None


def framework_mismatch(raw):
    """
    這筆紀錄跟目前作用中的框架對不對得上？

    對得上（或無從判斷）回 None；對不上回 (紀錄的框架, 目前的框架)。

    為什麼一定要有這個檢查：編碼的維度識別碼只在**它自己的框架**裡有意義。
    拿 UTAUT 去開 RI 編過的檔案，每一個維度都不在作用中的框架裡，於是整份
    編碼在載入當下就被清空——畫面上看起來就只是「這份還沒編碼」，接著隨手
    一存，磁碟上的原始資料就被空的版本覆蓋，無法復原。

    判斷所需的資訊本來就在檔案裡（_meta.framework_id 從 v1.0 起就會寫），
    讀它就好。

    舊檔沒有 framework_id，無從判斷，一律回 None 放行——這種檔案本來就
    只可能是用預設框架編的，而且擋下來只會讓使用者打不開自己的舊資料。
    """
    fid = record_framework_id(raw)
    if not fid:
        return None
    active = F.active().id
    return None if fid == active else (fid, active)


def is_legacy(raw):
    """是否為需要遷移的舊檔（用於提示使用者）。"""
    if not isinstance(raw, dict):
        return False
    if _is_legacy_v1(raw):
        return True
    return "編碼段落" in raw or "受訪者" in raw or \
        (raw.get(META) or {}).get("schema_version", 0) < SCHEMA_VERSION


# =====================================================================
# 8. 語言設定
# =====================================================================
# 介面語言與分析輸出語言是兩件獨立的事：
#   介面語言   = 研究者看到的按鈕與標籤（tacit_i18n 負責）
#   分析語言   = 逐字稿的語言，也就是模型要用哪種語言寫標題、引文與理由
# 一位台灣研究者可能用英文介面分析中文逐字稿；反之亦然。
# 兩者綁在一起會讓這套工具無法給其他語系的研究社群使用。
ANALYSIS_LANG_AUTO = "auto"
ANALYSIS_LANGS = {
    ANALYSIS_LANG_AUTO: "Match the transcript",
    "zh-Hant": "Traditional Chinese (繁體中文)",
    "zh-Hans": "Simplified Chinese (简体中文)",
    "en": "English",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "de": "German (Deutsch)",
    "fr": "French (Français)",
    "es": "Spanish (Español)",
}
DEFAULT_ANALYSIS_LANG = ANALYSIS_LANG_AUTO


_CJK_RANGE = r'一-鿿㐀-䶿'


def detect_script(text, threshold=0.15):
    """
    判斷這段文字主要是中文還是英文。回傳 "zh" / "en" / "unknown"。

    看的是漢字佔「漢字＋拉丁字母」的比例。門檻刻意訂低（15%）：
    中文語料常夾雜英文術語與機構名，只要出現一定比例的漢字就該判為中文；
    反過來，純英文語料不會有漢字，不會誤判。
    """
    text = text or ""
    cjk = len(re.findall(f"[{_CJK_RANGE}]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if cjk + latin == 0:
        return "unknown"
    return "zh" if cjk / (cjk + latin) >= threshold else "en"


_SCRIPT_TO_LANG = {"zh": "zh-Hant", "en": "en"}


def resolve_analysis_lang(lang, sample_text=""):
    """
    把 AUTO 解析成具體的語言代碼。

    「跟著逐字稿的語言走」這個指示，只在模型看得到逐字稿時才有意義。
    主題歸納的第二階段輸入的是第一階段產出的暫定主題，模型手上根本沒有
    逐字稿，於是它自行決定用英文——中文訪談跑出一整排英文主題名稱就是這樣來的。

    能自己判斷的事情不要丟給模型推論：這裡直接看輸入文字的字種，
    給出明確的語言名稱。判斷不出來時才退回原本的相對指示。
    """
    if lang != ANALYSIS_LANG_AUTO and lang in ANALYSIS_LANGS:
        return lang
    return _SCRIPT_TO_LANG.get(detect_script(sample_text), ANALYSIS_LANG_AUTO)


def analysis_language_instruction(lang, sample_text=""):
    """
    產生要放進提示詞的語言指示。

    給了 sample_text 就會把 AUTO 解析成具體語言，指示因此變成絕對而非相對；
    這對於「模型看不到原始逐字稿」的階段（例如主題歸納）是必要的。
    """
    lang = resolve_analysis_lang(lang, sample_text)
    if lang == ANALYSIS_LANG_AUTO or lang not in ANALYSIS_LANGS:
        return ("Write all output in the SAME language as the source material "
                "you are given. Quotations must always be copied verbatim in "
                "the original language.")
    extra = ""
    if lang == "zh-Hant":
        # 中國訓練的模型（qwen 系列最明顯）即使被要求繁體，仍會整段輸出簡體。
        # 這是實測撞到的：介面設繁中、逐字稿是繁中，產出仍是「负责医疗设备的
        # 研发与推广」。把失效模式直接寫進指示，比只寫語言名稱有效得多。
        extra = (" Use Taiwanese Traditional Chinese orthography throughout. "
                 "Do NOT output Simplified Chinese characters under any "
                 "circumstances — not 简, 会, 医, 发, 员, 长, 华, 负, 责, 与, "
                 "产, 业, 术, 达, 过, 关, 应, 该, 时, 间. If you are about to "
                 "write a Simplified form, write the Traditional form instead.")
    return (f"Write all output in {ANALYSIS_LANGS[lang]}.{extra} "
            "Quotations must always be copied verbatim in the original language "
            "of the transcript, even if that differs from the output language.")


# ---------------------------------------------------------------------
# 簡繁偵測
#
# 為什麼要有這個：提示詞寫了「Traditional Chinese (繁體中文)」，模型照樣
# 回簡體——這跟維度值寫成 "engagement|responsiveness" 是同一種病：模型不照
# 約定，而工具沒有辦法察覺，於是研究者拿到一份混雜簡體的分析卻不知道。
#
# **只偵測，不自動轉換。** 簡轉繁不是一對一（发 → 發／髮），自動改寫等於
# 工具替研究者竄改模型的輸出，而保留模型原始判斷正是這套工具的核心主張。
# 報出來，讓研究者決定要換模型還是自己處理。
#
# 這份清單刻意只收「繁體中文完全不會用到」的高頻簡化字，寧可漏報也不誤報。
# ---------------------------------------------------------------------
SIMPLIFIED_ONLY = set(
    # 每一個都必須是「繁體中文完全不會寫成這樣」的字。兩岸通用的字
    # （政、分、量、值、道、件、例、硬）一律不收——誤報會讓研究者去追一個
    # 不存在的問題，比漏報更浪費時間。
    "简会医发员长华负责与产业术达过关应该时"      # 高頻虛詞與常用字
    "间们个为这来说话语读书还没经济认识实现场"
    "传统门问题动规则专务确别导师际组织结构层级"
    "质标营养销价观点击键盘网络软电脑机视频艺设"
    "计类学习惯证据检验测购买卖农渔矿银铁钢铜铝"
    "东单双条线带缴税财赤亏损亚欧丽龙凤鸟鱼虾贝"
    "龟鲸鲨鲤鳞图书馆亲爱贫穷丰满乐团队伍险恶"
    "举办处开闭锁钥灯烛烟酒药疗养护卫"
    "厂矿场馆园艺术馆剧场戏剧团体"
)


def simplified_chars(text):
    """
    找出文字裡的簡體專用字。回傳排序後的清單，空的代表沒偵測到。

    保守：只認繁體中文完全不會出現的字，寧可漏報也不誤報。誤報會讓
    研究者去追一個不存在的問題，比漏報更浪費時間。
    """
    if not text:
        return []
    return sorted({c for c in str(text) if c in SIMPLIFIED_ONLY})


def scan_record_script(rec):
    """
    掃一筆紀錄裡**模型自己寫的**欄位有沒有簡體。

    引文與逐字稿不掃：那些本來就該逐字保留原文，原文若是簡體，
    照抄簡體是正確行為，不是缺陷。掃的是標題、理由、摘要——
    也就是模型自己產出的文字。
    """
    hits = {}
    for seg in rec.get(SEGMENTS) or []:
        for field in (TITLE, ):
            found = simplified_chars(seg.get(field))
            if found:
                hits.setdefault(seg.get(SEGMENT_ID, "?"), set()).update(found)
        for c in seg.get(CODES_F) or []:
            found = simplified_chars(c.get(RATIONALE))
            if found:
                hits.setdefault(seg.get(SEGMENT_ID, "?"), set()).update(found)
    found = simplified_chars(rec.get(SUMMARY))
    if found:
        hits.setdefault("summary", set()).update(found)
    # 屬性判定依據也是模型自己寫的。漏掉這一欄是實測才發現的：一份繁中
    # 分析的判定依據寫著「未在访谈中明确提及」，畫面上一片乾淨。
    found = simplified_chars((rec.get(DESCRIPTORS) or {}).get(DESCRIPTOR_BASIS))
    if found:
        hits.setdefault(DESCRIPTOR_BASIS, set()).update(found)
    return {k: sorted(v) for k, v in hits.items()}


def degenerate_titles(rec, labels=None):
    """
    找出退化成維度名的標題。

    要防的失效：英文那份跑出 "Reflexivity - N"、"Engagement"、"Anticipation - P"
    當標題。標題的用途是給下游主題聚斂用的**次主題**標籤——填成維度名，
    這一欄就作廢了，主題分析只會把框架的四個維度再跑出來一次，看起來像
    分析結果，其實是同義反覆。

    labels 傳入額外的顯示名稱（各語言的維度標籤）；不傳則只比對維度 id
    與編碼識別碼。回傳 {segment_id: title}。
    """
    # 模組層級的 CODES 是靠 __getattr__ 從作用中框架取的，那個機制只在
    # 從模組外面存取時才會觸發；模組**內部**寫裸名 CODES 會直接 NameError。
    fw = F.active()
    bad = {d.lower() for d in fw.dimensions}
    bad |= {c.lower() for c in fw.codes}
    bad |= {str(x).lower() for x in (labels or [])}
    out = {}
    for seg in rec.get(SEGMENTS) or []:
        t = str(seg.get(TITLE) or "").strip()
        if not t:
            continue
        # 去掉尾巴的極性標記。三種寫法都出現過：
        #   "Reflexivity - N"、"Engagement (P)"、"參與 N"
        # 括號版要先處理，否則 [PN]$ 對不上結尾的 ")"。
        core = re.sub(r"[\s\-–—_:：]*[(（\[][\s]*[PN][\s]*[)）\]]\s*$", "", t,
                      flags=re.IGNORECASE)
        core = re.sub(r"[\s\-–—_:：]*[PN]$", "", core, flags=re.IGNORECASE)
        core = core.strip(" -–—_:：()（）[]").lower()
        if core in bad or t.lower() in bad:
            out[seg.get(SEGMENT_ID, "?")] = t
    return out


# 詞庫是語言相關的資源：中文詞庫不能拿去分析英文逐字稿
LEXICON_LANGUAGE = "language"
