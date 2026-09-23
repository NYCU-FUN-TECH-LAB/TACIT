"""
tacit_framework.py — 可插拔的理論編碼框架
========================================
把「維度」從程式常數變成**資料**。這是整套工具能被 RI 以外的研究社群使用的
前提，也是最底層的一塊：tacit_schema 的維度與編碼都由這裡的作用中框架推導。

【為什麼要這樣做】
  四個 RI 維度若寫死在程式裡，工具的適用範圍就等於一個理論。
  框架外部化之後，任何採用先驗編碼簿的主題分析都能使用——
  演繹式框架分析、模板分析、理論驅動的內容分析都在射程內。

【極性不是普世的】
  Foley 的正負極性是 RI 特有的擴充。別的理論可能沒有極性。
  因此框架自行宣告 polarity.enabled：
      有極性 → 編碼為 ANT-P / ANT-N（八格）
      無極性 → 編碼為 ANT / REF / ENG / RES（四格）
  無極性時，極性平衡分析應由呼叫端自行停用（has_polarity 可判斷）。

【文獻出處】
  每個維度可掛 literature 清單，記錄該定義依據哪幾篇文獻，以及是人工挑選
  還是經 OpenAlex 檢索。框架建構的可追溯性本身就是方法論貢獻——
  「工程師憑印象挑的」與「系統性檢索、被引量排序、納入排除有紀錄」
  在方法論上是兩回事。
"""

import json
import os
import re

FRAMEWORK_DIR = "frameworks"
# 下列函式一律在呼叫當下才解析目錄（directory=None → FRAMEWORK_DIR），
# 而不是把它綁進預設參數。預設參數在 def 當下就求值，一旦綁死，
# 測試就無法把框架目錄導向暫存區，只能去污染使用者真正的 frameworks/。
DEFAULT_FRAMEWORK_ID = "ri_stilgoe_2013"

# --- 框架檔欄位（ASCII） --------------------------------------------
FRAMEWORK_ID = "framework_id"
NAME = "name"
CITATION = "citation"
DESCRIPTION = "description"
VERSION = "version"
POLARITY = "polarity"
POLARITY_ENABLED = "enabled"
POLARITY_VALUES = "values"
POLARITY_LABELS = "labels"
POLARITY_CITATION = "citation"
DIMENSIONS = "dimensions"
PROVENANCE = "provenance"

# --- 維度欄位 --------------------------------------------------------
DESCRIPTORS = "descriptors"
CORPUS = "corpus"

# 語料的語彙。編碼提示詞要用這幾個詞稱呼它正在讀的東西。
#
# 為什麼這也得由框架決定：提示詞若寫死「thematic analysis of an interview
# transcript」，並要模型從「自我介紹、職稱、年資」裡抽屬性。換成永續報告書
# 之後，維度與屬性都正確跟著框架走了，模型卻仍被指示去報告書裡找自我介紹
# ——維度可插拔，但語料的種類不可插拔，等於「任何演繹式架構都適用」這句話
# 只成立了一半。
#
# 預設是訪談，所以沒宣告的框架行為完全不變。
DEFAULT_CORPUS = {
    "document": {"en": "interview transcript", "zh": "訪談逐字稿"},
    "case": {"en": "respondent", "zh": "受訪者"},
    "descriptor_source": {
        "en": "self-introduction, job title, organisation, stated years of experience",
        "zh": "自我介紹、職稱、所屬機構、自述年資"},
}

# 案例層屬性的預設集合。
#
# 為什麼要有預設值而不是強制每個框架都寫：這四個欄位是訪談研究的
# 預設形狀，沒有宣告 descriptors 的紀錄都照它存。沒有宣告 descriptors
# 的框架（含使用者手上所有既有的檔案）必須維持完全相同的行為，否則等於把人家做到
# 一半的研究弄壞。宣告了就用它自己的。
#
# 這一組是訪談研究的形狀。分析永續報告、政策文件、專利說明書的框架，
# 應該宣告自己的——那正是這次把它移進框架的理由。
DEFAULT_DESCRIPTORS = {
    "institution_type": ["industry", "academia", "government", "nonprofit",
                         "research_institute", "other"],
    "role_level": ["senior_management", "middle_management", "rnd_staff",
                   "researcher", "policy_maker", "other"],
    "sector": ["ict_ai", "biomedical", "energy_sustainability", "manufacturing",
               "agritech", "finance", "other"],
    "experience": ["under_5y", "6_10y", "11_20y", "over_20y"],
}

DIM_ID = "id"
DIM_SHORT = "short"
DIM_LABEL = "label"
DIM_DEFINITION = "definition"
DIM_INDICATORS = "indicators"
# 排除條件：這個維度**不**涵蓋什麼。
#
# 為什麼需要它，而不是只把定義寫清楚一點：指標是正面例子，正面例子永遠
# 界定不出邊界。實測撞到的事情是——engagement 的指標只寫了 upstream
# participation / two-way dialogue / co-creation / including non-expert
# voices，模型於是自己補了邊界，把「我們用 design thinking 想使用者要
# 什麼」「就是 target user，我們的目標客群」，甚至英文稿裡的
# "Project Overview"、"MRI Based Imaging" 全判成 engagement 的正向證據。
# 一份 20,856 字元的訪談稿裡，人工標 7 段參與，軟體標了 33 段。
#
# 這件事會直接打穿框架模組存在的理由。這套工具的主張是「編碼依附於一個
# 有文獻出處的框架」——但如果構念的操作型邊界是模型當場想出來的，那個
# 主張就是假的：編碼依附的其實是模型的想像，文獻出處只是掛在旁邊。
# 所以排除條件跟指標一樣是框架的一部分，一樣可以（也應該）掛文獻。
DIM_EXCLUSIONS = "exclusions"
DIM_LITERATURE = "literature"

# --- 文獻條目 --------------------------------------------------------
LIT_CITATION = "citation"
LIT_OPENALEX_ID = "openalex_id"
LIT_DOI = "doi"
LIT_YEAR = "year"
LIT_CITED_BY = "cited_by_count"
LIT_ROLE = "role"
LIT_INCLUDED = "included"
LIT_NOTE = "note"

ROLE_GROUNDING = "grounding"     # 建立該維度定義的核心文獻
ROLE_SUPPORTING = "supporting"   # 補充或應用
ROLE_EXCLUDED = "excluded"       # 檢索到但研究者判定不納入（要記錄理由）

# --- 來源 ------------------------------------------------------------
PROV_BUILTIN = "builtin"
PROV_MANUAL = "manual"
PROV_OPENALEX_DRAFT = "openalex_draft"
PROV_OPENALEX_APPROVED = "openalex_approved"
# 由開放編碼從語料歸納出來的碼簿轉成的框架（tacit_open.codebook_to_framework）。
# 這個值必須跟 manual 分開：一個從文獻讀出來的框架與一個從資料跑出來的框架，
# 在方法論上是完全不同的東西，三個月後沒有人能從維度名稱分辨。稽核軌跡要
# 自己說得出來。
PROV_INDUCED = "induced"

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{1,39}$")

# 屬性「值」的規則比識別碼寬鬆：它是列舉標記，不是模組名稱。
# 單一字元（"a"）、以數字開頭（"2024"）都該收，_ID_RE 的「至少兩字元、
# 必須字母開頭」在這裡只會擋掉合理的寫法。仍然限制在 ASCII 小寫與底線，
# 因為這些值會進 JSON 鍵、CSV 欄位與檔名。
_VALUE_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,39}$")
_SHORT_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")

UNASSIGNED = "unassigned"
UNASSIGNED_SHORT = "UNC"


class FrameworkError(ValueError):
    """框架檔不合法。訊息為英文識別性描述，顯示文字由介面層處理。"""


# =====================================================================
# 1. Framework 物件
# =====================================================================
class Framework:
    """
    一個理論編碼框架。所有維度相關的推導都經過這裡，
    程式其他部分不應該再出現任何寫死的維度名稱。
    """

    def __init__(self, data):
        self.data = data
        self._dims = list(data.get(DIMENSIONS) or [])
        self._by_id = {d[DIM_ID]: d for d in self._dims}

    # --- 基本屬性 ---
    @property
    def id(self):
        return self.data.get(FRAMEWORK_ID, "")

    @property
    def version(self):
        return self.data.get(VERSION, "1.0")

    @property
    def provenance(self):
        return self.data.get(PROVENANCE, PROV_MANUAL)

    def name(self, lang="en"):
        return _pick(self.data.get(NAME), lang, self.id)

    def description(self, lang="en"):
        return _pick(self.data.get(DESCRIPTION), lang, "")

    @property
    def citation(self):
        return self.data.get(CITATION, "")

    # --- 極性 ---
    @property
    def has_polarity(self):
        return bool((self.data.get(POLARITY) or {}).get(POLARITY_ENABLED))

    @property
    def polarity_values(self):
        if not self.has_polarity:
            return []
        return list((self.data.get(POLARITY) or {}).get(POLARITY_VALUES) or ["P", "N"])

    @property
    def polarity_citation(self):
        return (self.data.get(POLARITY) or {}).get(POLARITY_CITATION, "")

    def polarity_label(self, dim_id, value, lang="en"):
        """優先取維度自訂的極性標籤，否則用框架層的通用標籤。"""
        d = self._by_id.get(dim_id) or {}
        per_dim = (d.get(POLARITY_LABELS) or {}).get(value)
        if per_dim:
            return _pick(per_dim, lang, value)
        generic = ((self.data.get(POLARITY) or {}).get(POLARITY_LABELS) or {}).get(value)
        return _pick(generic, lang, value)

    # --- 維度 ---
    def corpus_term(self, key, lang="en"):
        """
        語料語彙：document（在讀什麼）、case（一筆紀錄是誰）、
        descriptor_source（屬性該從哪裡抽）。未宣告則沿用訪談的說法。
        """
        raw = self.data.get(CORPUS)
        block = (raw or {}).get(key) if isinstance(raw, dict) else None
        if not isinstance(block, dict) or not block.get(lang, block.get("en")):
            block = DEFAULT_CORPUS.get(key, {})
        return _pick(block, lang) or DEFAULT_CORPUS.get(key, {}).get("en", key)

    @property
    def descriptors(self):
        """
        案例層屬性：{欄位: [合法值…]}。框架沒宣告就用訪談研究的預設集合。

        維度講的是「這段話在說什麼」，屬性講的是「這個案例是誰／是什麼」。
        兩者都該由框架決定：分析訪談時是機構類型與年資，分析永續報告時
        可能是產業別、報告年度、是否經第三方確信。屬性若寫死在 schema
        裡，「任何演繹式架構都適用」這句話只對維度成立，換一種語料
        就會在屬性這一層卡住。
        """
        raw = self.data.get(DESCRIPTORS)
        # 只有「作者根本沒宣告」才退回預設。宣告了卻被過濾到空，不可以默默
        # 給他訪談欄位——那會讓一份寫壞的框架看起來像正常運作，而使用者要到
        # 分析做到一半才發現欄位不對。這種情形交給 validate() 在載入時就報錯。
        if not isinstance(raw, dict) or not raw:
            return {k: list(v) for k, v in DEFAULT_DESCRIPTORS.items()}
        out = {}
        for key, vals in raw.items():
            if not _ID_RE.match(str(key)):
                continue
            clean = [str(v) for v in (vals or []) if _VALUE_RE.match(str(v))]
            if clean:
                out[str(key)] = clean
        return out

    @property
    def dimensions(self):
        return [d[DIM_ID] for d in self._dims]

    @property
    def agg_dimensions(self):
        """聚合維度含「未歸屬」，供主題對映使用。"""
        return self.dimensions + [UNASSIGNED]

    @property
    def dim_short(self):
        m = {d[DIM_ID]: d[DIM_SHORT] for d in self._dims}
        m[UNASSIGNED] = UNASSIGNED_SHORT
        return m

    @property
    def short_dim(self):
        return {v: k for k, v in self.dim_short.items()}

    def label(self, dim_id, lang="en"):
        d = self._by_id.get(dim_id)
        if d is None:
            return UNASSIGNED_LABEL.get(lang, dim_id) if dim_id == UNASSIGNED else dim_id
        return _pick(d.get(DIM_LABEL), lang, dim_id)

    def definition(self, dim_id, lang="en"):
        d = self._by_id.get(dim_id) or {}
        return _pick(d.get(DIM_DEFINITION), lang, "")

    def indicators(self, dim_id, polarity=None, lang=None):
        """
        取得該維度的指標描述。

        結構是三層的：極性 → 語言 → 清單，例如
            {"P": {"en": [...], "zh": [...]}, "N": {...}}
        無極性的框架則少一層極性，改用固定鍵 "all"。

        指定 lang 就直接拿到該語言的清單（找不到時退回英文）；
        不指定則原樣回傳雙語 dict，由呼叫端自己挑。

        【容易寫錯的地方一】最後一行若寫 `list(ind.get(polarity) or [])`，
        對雙語 dict 做 list() 得到的是它的**鍵**——畫面上因此列出
        「en」「zh」兩個空項目，而不是指標內容。凡是可能拿到 dict 的地方，
        都不能用 list() 當成「轉成清單」的萬用手段。

        【容易寫錯的地方二】無極性框架若只認 "all" 這個鍵：手寫一個無極性
        框架時，最自然的寫法是直接 `"indicators": {"en": [...], "zh": [...]}`
        ——少一層極性，就少寫一層。內建的 UTAUT 框架正是這樣寫的，於是它
        那 16 條指標**進不了提示詞**：ind.get("all") 回 None，
        模型只拿到維度名與定義，指標全部落空，而畫面與輸出都看不出異狀。
        現在兩種寫法都認。
        """
        d = self._by_id.get(dim_id) or {}
        ind = d.get(DIM_INDICATORS) or {}
        if not self.has_polarity:
            if isinstance(ind, list):
                block = ind
            elif "all" in ind:
                block = ind["all"]
            elif any(k in ind for k in ("en", "zh")):
                block = ind          # 直接就是語言 → 清單
            else:
                block = None
        elif polarity is None:
            block = {p: ind.get(p) or {} for p in self.polarity_values}
            return {p: _pick_lang(v, lang) for p, v in block.items()} \
                if lang else block
        else:
            block = ind.get(polarity)
        return _pick_lang(block, lang) if lang else _as_indicator_block(block)

    def exclusions(self, dim_id, lang=None):
        """
        取得該維度的排除條件（這個維度**不**涵蓋什麼）。

        結構比指標淺一層：語言 → 清單，沒有極性。排除條件講的是構念的邊界，
        邊界對正負兩極是同一條——「內部替使用者著想」不算 engagement，
        既不算正向的 engagement 也不算負向的 engagement。

        沒設定就回空清單：舊的框架檔沒有這個欄位，不能因此炸掉。
        """
        d = self._by_id.get(dim_id) or {}
        block = d.get(DIM_EXCLUSIONS)
        return _pick_lang(block, lang) if lang else _as_indicator_block(block)

    def has_exclusions(self):
        """有沒有任何一個維度寫了排除條件——用來提醒使用者這一層是空的。"""
        return any(self.exclusions(d, "en") or self.exclusions(d, "zh")
                   for d in self.dimensions)

    def literature(self, dim_id=None, role=None, included_only=True):
        out = []
        dims = [dim_id] if dim_id else self.dimensions
        for did in dims:
            for lit in (self._by_id.get(did, {}).get(DIM_LITERATURE) or []):
                if included_only and lit.get(LIT_INCLUDED) is False:
                    continue
                if role and lit.get(LIT_ROLE) != role:
                    continue
                out.append({**lit, DIM_ID: did})
        return out

    # --- 編碼 ---
    @property
    def codes(self):
        """有極性 → ANT-P/ANT-N…；無極性 → ANT/REF/…"""
        short = self.dim_short
        if not self.has_polarity:
            return [short[d] for d in self.dimensions]
        return [f"{short[d]}-{p}" for d in self.dimensions for p in self.polarity_values]

    def code_of(self, dim_id, polarity=None):
        short = self.dim_short.get(dim_id, dim_id)
        if not self.has_polarity:
            return short
        return f"{short}-{polarity}"

    def split_code(self, code):
        """回傳 (dimension_id, polarity)。無極性框架時 polarity 為 None。"""
        code = str(code)
        if not self.has_polarity:
            return self.short_dim.get(code), None
        short, _, pol = code.partition("-")
        return self.short_dim.get(short), (pol or None)

    def code_label(self, code, lang="en"):
        dim_id, pol = self.split_code(code)
        if dim_id is None:
            return code
        base = self.label(dim_id, lang)
        if not self.has_polarity or not pol:
            return base
        return f"{base} · {self.polarity_label(dim_id, pol, lang)}"

    def to_dict(self):
        return json.loads(json.dumps(self.data, ensure_ascii=False))


UNASSIGNED_LABEL = {"en": "Unassigned", "zh": "未歸屬"}


def _pick(entry, lang, fallback=""):
    if isinstance(entry, dict):
        return entry.get(lang) or entry.get("en") or fallback
    return str(entry) if entry else fallback


# =====================================================================
# 2. 驗證
# =====================================================================
def validate(data):
    """回傳問題清單（英文識別性描述）；空清單代表通過。"""
    problems = []
    if not isinstance(data, dict):
        return ["framework must be a JSON object"]

    fid = data.get(FRAMEWORK_ID, "")
    if not _ID_RE.match(str(fid)):
        problems.append(f"invalid framework_id: {fid!r} (need ^[a-z][a-z0-9_]{{1,39}}$)")
    if not data.get(NAME):
        problems.append("missing name")

    pol = data.get(POLARITY) or {}
    if pol.get(POLARITY_ENABLED):
        vals = pol.get(POLARITY_VALUES) or []
        if len(vals) < 2:
            problems.append("polarity enabled but fewer than 2 values")
        if any(not re.match(r"^[A-Za-z0-9]{1,4}$", str(v)) for v in vals):
            problems.append("polarity values must be short alphanumeric tokens")

    # 屬性欄位：宣告了就必須是可用的。沒宣告完全沒問題（沿用訪談預設），
    # 但宣告了卻沒有任何一個欄位存活下來，代表框架檔寫壞了——那要在載入時
    # 就講出來，而不是讓它安靜地退回訪談欄位，等使用者分析到一半才發現。
    desc = data.get(DESCRIPTORS)
    if desc is not None and not isinstance(desc, dict):
        problems.append("descriptors must be a JSON object")
    elif isinstance(desc, dict) and desc:
        kept = 0
        for key, vals in desc.items():
            if not _ID_RE.match(str(key)):
                problems.append(f"invalid descriptor field name: {key!r} "
                                f"(need ^[a-z][a-z0-9_]{{1,39}}$)")
                continue
            bad = [v for v in (vals or []) if not _VALUE_RE.match(str(v))]
            if bad:
                problems.append(f"descriptor {key!r} has invalid values: "
                                f"{bad[:3]} (need ^[a-z0-9][a-z0-9_]{{0,39}}$)")
            if [v for v in (vals or []) if _VALUE_RE.match(str(v))]:
                kept += 1
            else:
                problems.append(f"descriptor {key!r} has no usable values")
        if not kept:
            problems.append("descriptors declared but no usable field survived; "
                            "remove the key to fall back to the interview defaults")

    dims = data.get(DIMENSIONS) or []
    if not dims:
        problems.append("no dimensions defined")
    seen_id, seen_short = set(), set()
    for i, d in enumerate(dims):
        if not isinstance(d, dict):
            problems.append(f"dimension[{i}] is not an object")
            continue
        did, short = d.get(DIM_ID, ""), d.get(DIM_SHORT, "")
        if not _ID_RE.match(str(did)):
            problems.append(f"dimension[{i}] invalid id: {did!r}")
        if not _SHORT_RE.match(str(short)):
            problems.append(f"dimension[{i}] invalid short code: {short!r} "
                            "(need 2-6 uppercase alphanumerics)")
        if did in seen_id:
            problems.append(f"duplicate dimension id: {did!r}")
        if short in seen_short:
            problems.append(f"duplicate short code: {short!r}")
        if short == UNASSIGNED_SHORT:
            problems.append(f"short code {UNASSIGNED_SHORT!r} is reserved")
        if did == UNASSIGNED:
            problems.append(f"dimension id {UNASSIGNED!r} is reserved")
        seen_id.add(did); seen_short.add(short)
        if not d.get(DIM_LABEL):
            problems.append(f"dimension {did!r} missing label")
    return problems


def load_dict(data):
    problems = validate(data)
    if problems:
        raise FrameworkError("; ".join(problems))
    return Framework(data)


def load_file(path):
    with open(path, "r", encoding="utf-8") as f:
        return load_dict(json.load(f))


def save(fw, path=None):
    path = path or os.path.join(FRAMEWORK_DIR, f"{fw.id}.json")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(fw.to_dict(), f, ensure_ascii=False, indent=2)
    return path


def _as_indicator_block(block):
    """保持原樣傳出：dict 維持 dict，list 複製一份，None 變空清單。"""
    if isinstance(block, dict):
        return {k: list(v) if isinstance(v, list) else v
                for k, v in block.items()}
    return list(block or [])


def _pick_lang(block, lang):
    """從雙語 dict 取出指定語言的清單；已經是清單就原樣回傳。"""
    if isinstance(block, dict):
        return list(block.get(lang) or block.get("en") or [])
    return list(block or [])


def list_available(directory=None):
    """列出可用框架 [(id, 顯示名稱, 路徑)]，壞檔會被略過而不是讓程式掛掉。"""
    directory = directory or FRAMEWORK_DIR
    out = []
    if os.path.isdir(directory):
        for fn in sorted(os.listdir(directory)):
            if not fn.endswith(".json"):
                continue
            path = os.path.join(directory, fn)
            try:
                fw = load_file(path)
                out.append((fw.id, fw.name("en"), path))
            except Exception:
                continue
    return out


# =====================================================================
# 3. 作用中框架
# =====================================================================
_active = None


def set_active(fw):
    global _active
    _active = fw
    return _active


def active():
    """取得作用中框架；尚未設定時載入內建的 RI 框架。"""
    global _active
    if _active is None:
        _active = builtin_ri()
    return _active


def reset():
    global _active
    _active = None


def activate_by_id(framework_id, directory=None):
    directory = directory or FRAMEWORK_DIR
    if framework_id == DEFAULT_FRAMEWORK_ID:
        return set_active(builtin_ri())
    for fid, _name, path in list_available(directory):
        if fid == framework_id:
            return set_active(load_file(path))
    raise FrameworkError(f"framework not found: {framework_id}")


# =====================================================================
# 4. 內建：Stilgoe et al. (2013) 四維度 + Foley 極性
# =====================================================================
def _dim(did, short, en, zh, def_en, def_zh, pos_en, pos_zh, neg_en, neg_zh,
         pol_en_p, pol_zh_p, pol_en_n, pol_zh_n, literature):
    return {
        DIM_ID: did, DIM_SHORT: short,
        DIM_LABEL: {"en": en, "zh": zh},
        DIM_DEFINITION: {"en": def_en, "zh": def_zh},
        POLARITY_LABELS: {
            "P": {"en": pol_en_p, "zh": pol_zh_p},
            "N": {"en": pol_en_n, "zh": pol_zh_n}},
        DIM_INDICATORS: {"P": {"en": pos_en, "zh": pos_zh},
                         "N": {"en": neg_en, "zh": neg_zh}},
        # 排除條件按維度 id 從 _EXCLUSIONS 帶進來，不佔 _dim 的位置參數：
        # 這支函式已經有十五個位置參數，再加兩個只會讓四個呼叫點更難讀。
        DIM_EXCLUSIONS: {k: list(v) for k, v in
                         (_EXCLUSIONS.get(did) or {"en": [], "zh": []}).items()},
        DIM_LITERATURE: literature,
    }


def _lit(citation, role=ROLE_GROUNDING, year=None, note="", doi=None):
    """
    一筆文獻依據。

    citation 一律寫成完整的 APA 形式，並盡可能附上 DOI——讀者要能自己
    去把那篇調出來讀。像「Collingridge dilemma — 早期設計的控制問題」
    這種寫法不算引文：它指的是一個概念，不是一份可查證的來源。
    """
    return {LIT_CITATION: citation, LIT_ROLE: role, LIT_YEAR: year,
            LIT_INCLUDED: True, LIT_NOTE: note,
            LIT_OPENALEX_ID: None, LIT_DOI: doi, LIT_CITED_BY: None}


# 反覆被四個維度共同引用的核心文獻，集中定義避免手抄出錯。
_STILGOE_2013 = ("Stilgoe, J., Owen, R., & Macnaghten, P. (2013). Developing a "
                 "framework for responsible innovation. Research Policy, 42(9), "
                 "1568-1580.")
_STILGOE_DOI = "10.1016/j.respol.2013.05.008"
_OWEN_2012 = ("Owen, R., Macnaghten, P., & Stilgoe, J. (2012). Responsible "
              "research and innovation: From science in society to science for "
              "society, with society. Science and Public Policy, 39(6), 751-760.")
_OWEN_DOI = "10.1093/scipol/scs093"
_VONSCHOMBERG_2013 = ("von Schomberg, R. (2013). A vision of responsible research "
                      "and innovation. In R. Owen, J. Bessant, & M. Heintz (Eds.), "
                      "Responsible Innovation (pp. 51-74). Wiley.")
_VONSCHOMBERG_DOI = "10.1002/9781118551424.ch3"


# 內建框架的排除條件。
#
# 這一組是**依實測的誤判寫出來的**：拿一份人工編碼過的訪談稿（30 段）與
# 模型輸出逐段比對，位置命中 73%、維度也判對只有 37%，而錯的方向高度一致
# ——什麼都往 engagement 倒。每一條排除條件對應一種真的發生過的誤判。
#
# 它們是**草案，不是定論**。構念的操作型邊界屬於研究者的判斷，不屬於工具，
# 更不屬於我；框架編輯器裡可以逐條改。放在這裡的意義是：邊界必須是寫下來、
# 看得到、可以引用來源的東西，而不是模型每跑一次自己想一次。
_EXCLUSIONS = {
    "anticipation": {
        "en": [
            "Ordinary business forecasting — market projections, product "
            "roadmaps, KPI targets — is NOT anticipation unless the speaker "
            "engages with uncertainty or with alternative futures. Anticipation "
            "is not prediction (Guston, 2014).",
            "Stating that a regulation or trend already exists is NOT "
            "anticipation. Reasoning about its future effects is.",
            "Describing what the organisation plans to build next is NOT "
            "anticipation unless plausible futures or their consequences are "
            "actually explored.",
        ],
        "zh": [
            "一般的商業預測——市場推估、產品藍圖、KPI 目標——不算預期，"
            "除非說話者處理了不確定性或探討了其他可能的未來。預期不等於預測"
            "（Guston, 2014）。",
            "陳述某個法規或趨勢已經存在，不算預期；推論它未來的效應才算。",
            "描述組織接下來要做什麼產品，不算預期，除非真的探討了多重可能的"
            "未來或其後果。",
        ]},
    "reflexivity": {
        "en": [
            "The ABSENCE of self-examination in a passage is NOT evidence of "
            "hubris. Never code a negative polarity on the grounds that the "
            "speaker 'does not show' reflection — negative polarity requires an "
            "affirmative claim in the text (e.g. an explicit assertion that "
            "technical expertise settles the question).",
            "Following an established process, standard or regulation is NOT "
            "reflexivity. Stilgoe et al. (2013) distinguish reflexivity from "
            "compliance: examining the assumptions BEHIND the process is "
            "reflexivity; describing the process is not.",
            "Describing what the organisation does well, or its capabilities, "
            "is NOT reflexivity.",
            "Considering what users need is NOT reflexivity unless the speaker "
            "turns the scrutiny on their own assumptions or knowledge limits.",
        ],
        "zh": [
            "一段話裡「沒有出現」自我檢視，不構成自負的證據。絕不可以因為"
            "說話者「未表現出」反省就給負向編碼——負向極性必須有文本上的"
            "正面主張（例如明確宣稱技術專業就能決定這個問題）。",
            "遵循既有的流程、標準或法規不算反思性。Stilgoe 等人（2013）把"
            "反思性與合規區分開來：檢視流程背後的假設才是反思，描述流程不是。",
            "描述組織做得好的地方或自身能力，不算反思性。",
            "思考使用者需要什麼不算反思性，除非說話者把檢視轉向自己的假設"
            "或知識邊界。",
        ]},
    "engagement": {
        "en": [
            "Merely MENTIONING users, customers, patients, nurses, partners or "
            "government as the subject of a decision is NOT engagement. "
            "Engagement requires interaction in which those actors actually "
            "shape the innovation.",
            "User-centred design reasoning carried out INTERNALLY — design "
            "thinking, defining the target user, inferring what users need — is "
            "NOT engagement. It is the deficit model the concept was formulated "
            "against (Wynne, 1992).",
            "Describing a project, a product, a partnership or an "
            "organisational structure is NOT engagement, however many actors it "
            "names.",
            "Commercial relationships — selling to a hospital, working through "
            "a distributor, winning a government contract — are NOT engagement "
            "unless the counterpart shapes the direction of the innovation.",
            "Communication AFTER the decision is fixed is downstream "
            "notification: code it negative, never positive.",
        ],
        "zh": [
            "只是「提到」使用者、客戶、病患、護理師、合作夥伴或政府，不算參與。"
            "參與要求那些行動者實際參與了塑造這項創新的過程。",
            "在組織**內部**進行的使用者中心設計推理——design thinking、"
            "定義目標客群、推想使用者要什麼——不算參與。那正是這個概念當初"
            "要對抗的 deficit model（Wynne, 1992）。",
            "描述一個計畫、一項產品、一段合作關係或組織架構，不算參與，"
            "無論裡面點名了多少行動者。",
            "商業關係——賣給醫院、透過經銷商、拿到政府標案——不算參與，"
            "除非對方影響了這項創新的走向。",
            "決定拍板之後才進行的溝通屬於下游告知：編負向，不可編正向。",
        ]},
    "responsiveness": {
        "en": [
            "Routine product iteration, bug fixing or scheduled upgrades are "
            "NOT responsiveness. Responsiveness requires a change of direction "
            "in response to an external signal (Stilgoe et al., 2013).",
            "Meeting a regulatory requirement is NOT responsiveness unless the "
            "trajectory of the innovation actually changed as a result.",
            "Stating an intention to respond in future is NOT responsiveness; "
            "a change that actually occurred is.",
        ],
        "zh": [
            "例行的產品迭代、修 bug 或排定的版本更新，不算回應性。回應性要求"
            "因外部訊號而改變方向（Stilgoe et al., 2013）。",
            "滿足法規要求不算回應性，除非創新的走向真的因此改變。",
            "宣稱未來會回應不算回應性；真的發生過的改變才算。",
        ]},
}


def builtin_ri():
    """內建的預設框架。這是示範，也是本工具原始的研究用途。"""
    return load_dict({
        FRAMEWORK_ID: DEFAULT_FRAMEWORK_ID,
        VERSION: "1.0",
        PROVENANCE: PROV_BUILTIN,
        NAME: {"en": "Responsible Innovation (AIRR)",
               "zh": "負責任創新（AIRR 四維度）"},
        CITATION: ("Stilgoe, J., Owen, R., & Macnaghten, P. (2013). Developing a "
                   "framework for responsible innovation. Research Policy, 42(9), "
                   "1568-1580."),
        DESCRIPTION: {
            "en": "The four-dimension framework for Responsible Innovation "
                  "(Anticipation, Reflexivity, Engagement, Responsiveness), "
                  "extended with Foley's positive/negative polarity model.",
            "zh": "負責任創新四維度框架（預期、反思性、參與、回應性），"
                  "並以 Foley 的正負極性模型擴充。"},
        POLARITY: {
            POLARITY_ENABLED: True,
            POLARITY_VALUES: ["P", "N"],
            POLARITY_LABELS: {"P": {"en": "Positive", "zh": "正向"},
                              "N": {"en": "Negative", "zh": "負向"}},
            POLARITY_CITATION: "Foley's positive/negative polarity model",
        },
        DIMENSIONS: [
            _dim("anticipation", "ANT", "Anticipation", "預期",
                 "Systematic foresight: exploring plausible futures, handling "
                 "uncertainty, and keeping design options open before the "
                 "technology stabilises.",
                 "系統性的前瞻：探索多重可能的未來、處理不確定性，"
                 "並在技術定型之前保留設計彈性。",
                 ["scenario planning", "upstream intervention",
                  "acknowledging uncertainty", "avoiding lock-in"],
                 ["情境規劃", "上游介入", "承認不確定性", "迴避技術鎖定"],
                 ["single deterministic forecast", "deferring foresight",
                  "reducing anticipation to KPI tracking"],
                 ["單一確定性預測", "延後前瞻", "把預期降格為 KPI 追蹤"],
                 "Long-term / Exploratory (+)", "長期／探索式 (+)",
                 "Short / Deterministic (−)", "短視／決定論 (−)",
                 [_lit(_STILGOE_2013, year=2013, doi=_STILGOE_DOI,
                       note="Defines anticipation as systematic thinking about "
                            "plausible futures, and distinguishes it from "
                            "prediction."),
                  _lit("Barben, D., Fisher, E., Selin, C., & Guston, D. H. (2008). "
                       "Anticipatory governance of nanotechnology: Foresight, "
                       "engagement, and integration. In E. J. Hackett et al. (Eds.), "
                       "The Handbook of Science and Technology Studies (3rd ed., "
                       "pp. 979-1000). MIT Press.", year=2008,
                       note="The foresight/engagement/integration formulation that "
                            "anticipation in RI is built on."),
                  _lit("Guston, D. H. (2014). Understanding 'anticipatory "
                       "governance'. Social Studies of Science, 44(2), 218-242.",
                       year=2014, doi="10.1177/0306312713508669",
                       note="Anticipation as building societal capacity, not as "
                            "forecasting accuracy."),
                  _lit("Collingridge, D. (1980). The Social Control of Technology. "
                       "Pinter.", ROLE_SUPPORTING, 1980,
                       note="The control dilemma: early intervention lacks "
                            "knowledge, late intervention lacks leverage."),
                  _lit("Genus, A., & Stirling, A. (2018). Collingridge and the "
                       "dilemma of control: Towards responsible and accountable "
                       "innovation. Research Policy, 47(1), 61-69.",
                       ROLE_SUPPORTING, 2018, doi="10.1016/j.respol.2017.09.012",
                       note="Re-reads the dilemma as a governance problem rather "
                            "than an information problem."),
                  _lit("Muiderman, K., Gupta, A., Vervoort, J., & Biermann, F. "
                       "(2020). Four approaches to anticipatory climate governance. "
                       "WIREs Climate Change, 11(6), e673.",
                       ROLE_SUPPORTING, 2020, doi="10.1002/wcc.673",
                       note="Shows that 'anticipation' covers several distinct "
                            "conceptions of the future; useful for coding "
                            "borderline segments."),
                  _lit(_VONSCHOMBERG_2013, ROLE_SUPPORTING, 2013,
                       doi=_VONSCHOMBERG_DOI,
                       note="Normative anchoring of anticipation in societal "
                            "desirability.")]),
            _dim("reflexivity", "REF", "Reflexivity", "反思性",
                 "Scrutiny of one's own values, assumptions and knowledge limits; "
                 "epistemic humility rather than the assumption that technical "
                 "expertise settles ethical questions.",
                 "檢視自身的價值、假設與知識邊界；展現認識論謙遜，"
                 "而非把技術專業當成倫理判斷的答案。",
                 ["questioning own assumptions", "epistemic humility",
                  "acknowledging limits", "second-order reflection"],
                 ["質疑自身假設", "認知謙遜", "承認侷限", "二階反思"],
                 ["techno-optimism", "we-know-best framing",
                  "reflexivity reduced to compliance"],
                 ["技術樂觀主義", "we-know-best 框架", "反思淪為合規程序"],
                 "Humility (+)", "謙遜 (+)",
                 "Hubris / Over-confident (−)", "自負／過度自信 (−)",
                 [_lit(_STILGOE_2013, year=2013, doi=_STILGOE_DOI,
                       note="Defines reflexivity as holding a mirror to one's own "
                            "activities, commitments and assumptions."),
                  _lit(_OWEN_2012, year=2012, doi=_OWEN_DOI,
                       note="Locates reflexivity within the wider RRI programme "
                            "and its institutional demands."),
                  _lit("Wynne, B. (1992). Misunderstood misunderstanding: Social "
                       "identities and public uptake of science. Public "
                       "Understanding of Science, 1(3), 281-304.", year=1992,
                       doi="10.1088/0963-6625/1/3/004",
                       note="The classic argument that expert framings carry "
                            "unexamined assumptions; the root of institutional "
                            "reflexivity."),
                  _lit("Fisher, E., Mahajan, R. L., & Mitcham, C. (2006). "
                       "Midstream modulation of technology: Governance from "
                       "within. Bulletin of Science, Technology & Society, 26(6), "
                       "485-496.", ROLE_SUPPORTING, 2006,
                       doi="10.1177/0270467606295402",
                       note="Reflexivity as something enacted inside the lab, not "
                            "imposed from outside."),
                  _lit("Schuurbiers, D. (2011). What happens in the lab: Applying "
                       "midstream modulation to enhance critical reflection in the "
                       "laboratory. Science and Engineering Ethics, 17(4), "
                       "769-788.", ROLE_SUPPORTING, 2011,
                       doi="10.1007/s11948-011-9317-8",
                       note="Empirical evidence of what reflexive talk actually "
                            "looks like in researcher interviews."),
                  _lit("Burget, M., Bardone, E., & Pedaste, M. (2017). Definitions "
                       "and conceptual dimensions of responsible research and "
                       "innovation: A literature review. Science and Engineering "
                       "Ethics, 23(1), 1-19.", ROLE_SUPPORTING, 2017,
                       doi="10.1007/s11948-016-9782-1",
                       note="Confirms reflexivity as one of four recurring "
                            "dimensions across the RRI literature.")]),
            _dim("engagement", "ENG", "Public Engagement", "參與",
                 "Relations with external actors: upstream, two-way and "
                 "consequential participation, as against one-way communication "
                 "or consultation after decisions are already fixed.",
                 "與外部行動者的關係：上游、雙向且能實質影響決策的參與，"
                 "而非單向傳播或決策定案後才進行的諮詢。",
                 ["upstream participation", "two-way dialogue", "co-creation",
                  "including non-expert voices"],
                 ["上游參與", "雙向對話", "共創", "納入非專家聲音"],
                 ["participation washing", "deficit-model communication",
                  "downstream notification"],
                 ["參與清洗", "缺乏模型式傳播", "下游知會"],
                 "Open / Inclusive (+)", "開放／包容 (+)",
                 "Closed / Exclusive (−)", "封閉／排他 (−)",
                 [_lit(_STILGOE_2013, year=2013, doi=_STILGOE_DOI,
                       note="Defines inclusion as opening up visions and purposes "
                            "to broader deliberation, not just consultation."),
                  _lit("Wilsdon, J., & Willis, R. (2004). See-through Science: Why "
                       "Public Engagement Needs to Move Upstream. Demos.",
                       year=2004,
                       note="The upstream-engagement argument that the positive "
                            "pole of this dimension rests on."),
                  _lit("Stirling, A. (2008). 'Opening up' and 'closing down': "
                       "Power, participation, and pluralism in the social "
                       "appraisal of technology. Science, Technology, & Human "
                       "Values, 33(2), 262-294.", year=2008,
                       doi="10.1177/0162243907311265",
                       note="The opening-up / closing-down distinction; the "
                            "sharpest test for separating genuine inclusion from "
                            "participation washing."),
                  _lit("Irwin, A. (2006). The politics of talk: Coming to terms "
                       "with the 'new' scientific governance. Social Studies of "
                       "Science, 36(2), 299-320.", ROLE_SUPPORTING, 2006,
                       doi="10.1177/0306312706053350",
                       note="Warns that participation can become ritual; the "
                            "empirical basis for the negative pole."),
                  _lit("Wynne, B. (2006). Public engagement as a means of "
                       "restoring public trust in science: Hitting the notes but "
                       "missing the music? Community Genetics, 9(3), 211-220.",
                       ROLE_SUPPORTING, 2006, doi="10.1159/000092659",
                       note="The deficit-model critique that the negative "
                            "indicators are drawn from."),
                  _lit(_OWEN_2012, ROLE_SUPPORTING, 2012, doi=_OWEN_DOI,
                       note="Positions inclusion within institutional research "
                            "funding practice.")]),
            _dim("responsiveness", "RES", "Responsiveness", "回應性",
                 "Capacity to change the innovation trajectory in response to "
                 "external signals — including the capacity to stop — rather than "
                 "treating the trajectory as fixed.",
                 "依外部訊號實質改變創新軌跡的能力（包含終止的能力），"
                 "而非把軌跡視為既定。",
                 ["substantive modification after feedback", "iterative learning",
                  "institutionalised mechanisms", "capacity to halt"],
                 ["依回饋實質修改", "迭代學習", "機制制度化", "有能力喊停"],
                 ["refusal to change course", "sunk-cost lock-in",
                  "regulation framed as obstacle"],
                 ["拒絕改變路徑", "沉沒成本鎖定", "視法規為障礙"],
                 "Adaptive (+)", "調適 (+)",
                 "Obdurate (−)", "僵固 (−)",
                 [_lit(_STILGOE_2013, year=2013, doi=_STILGOE_DOI,
                       note="Defines responsiveness as the capacity to change "
                            "shape or direction in response to stakeholder and "
                            "public values and changing circumstances."),
                  _lit(_VONSCHOMBERG_2013, year=2013, doi=_VONSCHOMBERG_DOI,
                       note="Mutual responsiveness between societal actors and "
                            "innovators; the source of the term in RRI."),
                  _lit("Pellizzoni, L. (2004). Responsibility and environmental "
                       "governance. Environmental Politics, 13(3), 541-565.",
                       year=2004, doi="10.1080/0964401042000229034",
                       note="Separates responsiveness from care, liability and "
                            "accountability — the distinction that keeps this "
                            "dimension from collapsing into compliance talk."),
                  _lit("Collingridge, D. (1980). The Social Control of Technology. "
                       "Pinter.", ROLE_SUPPORTING, 1980,
                       note="Corrigibility: keeping decisions reversible is what "
                            "makes later responsiveness possible at all."),
                  _lit("Genus, A., & Stirling, A. (2018). Collingridge and the "
                       "dilemma of control: Towards responsible and accountable "
                       "innovation. Research Policy, 47(1), 61-69.",
                       ROLE_SUPPORTING, 2018, doi="10.1016/j.respol.2017.09.012",
                       note="Lock-in and path dependence; the conceptual basis "
                            "for the negative indicators."),
                  _lit("Blok, V., & Lemmens, P. (2015). The emerging concept of "
                       "responsible innovation: Three reasons why it is "
                       "questionable. In B.-J. Koops et al. (Eds.), Responsible "
                       "Innovation 2 (pp. 19-35). Springer.",
                       ROLE_SUPPORTING, 2015, doi="10.1007/978-3-319-17308-5_2",
                       note="Argues that commercial actors face structural limits "
                            "on responsiveness; read this before interpreting "
                            "industry respondents as simply obdurate.")]),
        ],
    })


def ensure_builtin_on_disk(directory=None):
    """把內建框架寫成檔案，讓使用者看得到範例格式、也能複製後修改。"""
    directory = directory or FRAMEWORK_DIR
    path = os.path.join(directory, f"{DEFAULT_FRAMEWORK_ID}.json")
    if not os.path.exists(path):
        save(builtin_ri(), path)
    return path


# =====================================================================
# 5. 建立空白框架（供使用者自建）
# =====================================================================
def blank(framework_id, name_en, dimensions, has_polarity=True, name_zh=None,
          citation="", provenance=PROV_MANUAL):
    """
    dimensions: [(id, SHORT, label_en, label_zh)]
    產出的框架已通過驗證，可直接存檔後在介面上編輯定義與文獻。
    """
    dims = []
    for did, short, en, zh in dimensions:
        dims.append({
            DIM_ID: did, DIM_SHORT: short,
            DIM_LABEL: {"en": en, "zh": zh or en},
            DIM_DEFINITION: {"en": "", "zh": ""},
            DIM_INDICATORS: ({"P": {"en": [], "zh": []}, "N": {"en": [], "zh": []}}
                             if has_polarity else {"all": {"en": [], "zh": []}}),
            DIM_EXCLUSIONS: {"en": [], "zh": []},
            DIM_LITERATURE: [],
        })
    data = {
        FRAMEWORK_ID: framework_id, VERSION: "1.0", PROVENANCE: provenance,
        NAME: {"en": name_en, "zh": name_zh or name_en},
        CITATION: citation, DESCRIPTION: {"en": "", "zh": ""},
        POLARITY: {POLARITY_ENABLED: bool(has_polarity),
                   POLARITY_VALUES: ["P", "N"] if has_polarity else [],
                   POLARITY_LABELS: {"P": {"en": "Positive", "zh": "正向"},
                                     "N": {"en": "Negative", "zh": "負向"}},
                   POLARITY_CITATION: ""},
        DIMENSIONS: dims,
    }
    return load_dict(data)
