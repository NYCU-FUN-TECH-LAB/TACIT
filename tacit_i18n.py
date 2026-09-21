"""
tacit_i18n.py — 介面語言目錄（英文預設，可切換繁體中文）
========================================================
搭配 tacit_schema 使用：schema 定義**內部識別碼**，本模組定義**顯示標籤**。

  程式邏輯只認 tacit_schema 的常數；畫面上與匯出檔裡的每一個字都查這裡。

【設計原則】
  1. 英文為預設語言。這是為了讓工具能被中文以外的研究社群使用。
  2. 查不到的鍵回傳鍵本身，而不是拋錯——少一句翻譯不該讓整個程式掛掉。
     但 missing_keys() 可以列出所有缺漏，CI 或測試會抓到。
  3. 匯出檔（Excel 工作表名、欄位名）也走這套目錄，
     否則外國使用者會拿到英文介面配中文表格。

【用法】
    import tacit_i18n as I
    I.set_lang("en")           # 或 "zh"
    I.t("app.title")           # -> "TACIT"
    I.dim(S.REFLEXIVITY)       # -> "Reflexivity"
    I.code_label("REF-N")      # -> "Reflexivity · Hubris / Over-confident (−)"
"""

import tacit_schema as S

LANGS = ["en", "zh"]
LANG_NAMES = {"en": "English", "zh": "繁體中文"}
DEFAULT_LANG = "en"
_lang = DEFAULT_LANG


def normalize_lang(lang):
    """
    把外部帶進來的語言代碼對到介面語言。

    介面語言只有 en / zh 兩個值，但分析語言是 BCP-47 風格的
    zh-Hant / zh-Hans / ja / …，兩者在存檔、網址參數與舊版狀態裡很容易
    互相走錯位。走錯位時直接退回 DEFAULT_LANG 是最糟的處理：拿到
    "zh-Hant" 的人要的顯然是中文介面，退成英文不會出錯，但也不是他要的，
    而且悄無聲息——沒有任何訊息告訴他為什麼介面變英文了。

    所以先比前綴再退回：zh-Hant / zh-Hans / zh-TW 一律對到 zh。
    """
    if lang in LANGS:
        return lang
    head = str(lang or "").split("-")[0].lower()
    for code in LANGS:
        if code.lower() == head:
            return code
    return DEFAULT_LANG


def set_lang(lang):
    global _lang
    _lang = normalize_lang(lang)
    return _lang


def get_lang():
    return _lang


# =====================================================================
# 維度、極性、屬性、狀態 —— 由 schema 識別碼對應到顯示名稱
# =====================================================================
DIM_LABEL = {
    S.ANTICIPATION:   {"en": "Anticipation",      "zh": "預期"},
    S.REFLEXIVITY:    {"en": "Reflexivity",       "zh": "反思性"},
    S.ENGAGEMENT:     {"en": "Public Engagement", "zh": "參與"},
    S.RESPONSIVENESS: {"en": "Responsiveness",    "zh": "回應性"},
    S.UNASSIGNED:     {"en": "Unassigned",        "zh": "未歸屬"},
}

POLARITY_LABEL = {
    S.ANTICIPATION: {
        "P": {"en": "Long-term / Exploratory (+)", "zh": "長期／探索式 (+)"},
        "N": {"en": "Short / Deterministic (−)",   "zh": "短視／決定論 (−)"}},
    S.REFLEXIVITY: {
        "P": {"en": "Humility (+)",                "zh": "謙遜 (+)"},
        "N": {"en": "Hubris / Over-confident (−)", "zh": "自負／過度自信 (−)"}},
    S.ENGAGEMENT: {
        "P": {"en": "Open / Inclusive (+)",        "zh": "開放／包容 (+)"},
        "N": {"en": "Closed / Exclusive (−)",      "zh": "封閉／排他 (−)"}},
    S.RESPONSIVENESS: {
        "P": {"en": "Adaptive (+)",                "zh": "調適 (+)"},
        "N": {"en": "Obdurate (−)",                "zh": "僵固 (−)"}},
}

DESCRIPTOR_LABEL = {
    "institution_type": {"en": "Institution type", "zh": "機構類型"},
    "role_level":       {"en": "Role level",       "zh": "職位層級"},
    "sector":           {"en": "Sector",           "zh": "產業領域"},
    "experience":       {"en": "Experience",       "zh": "年資區間"},
    S.DESCRIPTOR_BASIS: {"en": "Basis for descriptors", "zh": "屬性判定依據"},
}

DESCRIPTOR_VALUE_LABEL = {
    "industry": {"en": "Industry", "zh": "產業界"},
    "academia": {"en": "Academia", "zh": "學術界"},
    "government": {"en": "Government", "zh": "政府部門"},
    "nonprofit": {"en": "Non-profit", "zh": "非營利組織"},
    "research_institute": {"en": "Research institute", "zh": "研究法人"},
    "senior_management": {"en": "Senior management", "zh": "高階主管"},
    "middle_management": {"en": "Middle management", "zh": "中階管理"},
    "rnd_staff": {"en": "R&D staff", "zh": "研發人員"},
    "researcher": {"en": "Researcher", "zh": "研究者"},
    "policy_maker": {"en": "Policy maker", "zh": "政策制定者"},
    "ict_ai": {"en": "ICT / AI", "zh": "資通訊／AI"},
    "biomedical": {"en": "Biomedical", "zh": "生技醫療"},
    "energy_sustainability": {"en": "Energy / Sustainability", "zh": "能源／永續"},
    "manufacturing": {"en": "Manufacturing", "zh": "製造業"},
    "agritech": {"en": "Agritech", "zh": "農業科技"},
    "finance": {"en": "Finance", "zh": "金融"},
    "under_5y": {"en": "Under 5 years", "zh": "5 年以下"},
    "6_10y": {"en": "6–10 years", "zh": "6–10 年"},
    "11_20y": {"en": "11–20 years", "zh": "11–20 年"},
    "over_20y": {"en": "Over 20 years", "zh": "20 年以上"},
    "other": {"en": "Other", "zh": "其他"},
    S.UNSPECIFIED: {"en": "Unspecified", "zh": "未標註"},
}

STATUS_LABEL = {
    S.STATUS_PENDING:   {"en": "Pending",   "zh": "未審核"},
    S.STATUS_CONFIRMED: {"en": "Confirmed", "zh": "已確認"},
    S.STATUS_MODIFIED:  {"en": "Modified",  "zh": "已修改"},
    S.STATUS_ADDED:     {"en": "Added",     "zh": "人工新增"},
    S.STATUS_DELETED:   {"en": "Deleted",   "zh": "已刪除"},
}

SOURCE_LABEL = {
    S.SOURCE_AI:    {"en": "AI", "zh": "AI"},
    S.SOURCE_HUMAN: {"en": "Human", "zh": "人工"},
}

RELATION_LABEL = {
    S.RELATION_ALIGNED:    {"en": "Aligned",    "zh": "契合"},
    S.RELATION_EXTENDS:    {"en": "Extends",    "zh": "延伸"},
    S.RELATION_CHALLENGES: {"en": "Challenges", "zh": "挑戰"},
}

TENDENCY_LABEL = {
    "P": {"en": "Positive", "zh": "正向"},
    "N": {"en": "Negative", "zh": "負向"},
    S.TENDENCY_MIXED: {"en": "Mixed", "zh": "混合"},
}

SPECIAL_LABEL = {
    S.STRATUM_UNMARKED: {"en": "Uncoded", "zh": "未標記"},
    S.NONE_LABEL:       {"en": "None",    "zh": "無"},
}


def _pick(entry, lang=None):
    if not isinstance(entry, dict):
        return str(entry)
    return entry.get(lang or _lang) or entry.get(DEFAULT_LANG) or ""


def dim(d, lang=None):
    """
    維度標籤優先取自作用中框架——換框架時維度是全新的，
    本模組的 DIM_LABEL 只是內建 RI 框架的備援。
    """
    fw = S.framework()
    if d in fw.agg_dimensions:
        label = fw.label(d, lang or _lang)
        if label and label != d:
            return label
    return _pick(DIM_LABEL.get(d, {"en": str(d), "zh": str(d)}), lang)


def dim_full(d, lang=None):
    """含縮寫的完整維度標籤，如 'Reflexivity (REF)'。"""
    short = S.DIM_SHORT.get(d, "")
    return f"{dim(d, lang)} ({short})" if short else dim(d, lang)


def polarity(d, p, lang=None):
    """極性標籤同理：先問框架，框架沒定義才用內建表。"""
    fw = S.framework()
    if fw.has_polarity and d in fw.dimensions:
        label = fw.polarity_label(d, p, lang or _lang)
        if label and label != p:
            return label
    return _pick((POLARITY_LABEL.get(d) or {}).get(p, {}), lang)


def polarity_generic(p, lang=None):
    """
    不綁維度的極性標籤，例如「屬性 × 極性」交叉表的欄名。

    polarity() 需要維度，因為框架可以為每個維度自訂極性說法
    （負責任創新的「長期／探索式」對「短視／決定論」）。跨維度彙總的
    表沒有單一維度可問，這時要用框架層的通用標籤。
    """
    fw = S.framework()
    if fw.has_polarity:
        label = fw.polarity_label(None, p, lang or _lang)
        if label and label != p:
            return label
    return _pick((POLARITY_LABEL.get(None) or {}).get(p, {}), lang) or str(p)


def code_label(code, lang=None):
    d, p = S.split_code(code)
    if not d:
        return str(code)
    if not p:                      # 無極性框架
        return dim(d, lang)
    return f"{dim(d, lang)} · {polarity(d, p, lang)}"


def _humanise(token):
    """
    沒有翻譯時的退路：report_year → Report year。

    屬性欄位改由框架決定之後，任何人都能宣告自己的欄位，而那些欄位不可能
    事先出現在翻譯表裡。直接把識別碼原樣印出來會讓自訂框架的介面看起來
    像沒做完；humanise 之後至少是可讀的英文。要正式的標籤，在 tacit_strings
    裡補一筆即可。
    """
    s = str(token or "").replace("_", " ").strip()
    return s[:1].upper() + s[1:] if s else str(token)


def descriptor(key, lang=None):
    known = DESCRIPTOR_LABEL.get(key)
    if known:
        return _pick(known, lang)
    return _humanise(key)


def descriptor_value(val, lang=None):
    # 值刻意保持原樣輸出，不做 humanise。欄位名稱是結構（Report year 讀起來
    # 才對），但值往往是研究者自己選定的代碼——y2024 變成 Y2024 只是把它
    # 弄得不像原本寫的東西。看到什麼就是什麼，比較好對照框架檔。
    return _pick(DESCRIPTOR_VALUE_LABEL.get(val, {"en": str(val), "zh": str(val)}),
                 lang)


def status(v, lang=None):
    return _pick(STATUS_LABEL.get(v, {"en": str(v), "zh": str(v)}), lang)


def source(v, lang=None):
    return _pick(SOURCE_LABEL.get(v, {"en": str(v), "zh": str(v)}), lang)


def relation(v, lang=None):
    return _pick(RELATION_LABEL.get(v, {"en": str(v), "zh": str(v)}), lang)


def tendency(v, lang=None):
    return _pick(TENDENCY_LABEL.get(v, {"en": str(v), "zh": str(v)}), lang)


def special(v, lang=None):
    return _pick(SPECIAL_LABEL.get(v, {"en": str(v), "zh": str(v)}), lang)


# =====================================================================
# 一般介面字串
# =====================================================================
STRINGS = {
    # --- 應用程式層級 ---
    "app.title": {"en": "TACIT", "zh": "TACIT"},
    "app.subtitle": {
        "en": "Theory-anchored qualitative coding with interpretive "
              "transparency · pluggable coding frameworks",
        "zh": "理論錨定的質性編碼，詮釋權留在研究者手上 · 可插拔編碼框架"},
    "app.language": {"en": "Language", "zh": "語言"},
    "app.settings": {"en": "Settings", "zh": "系統設定"},
    "app.api_key": {"en": "Gemini API key", "zh": "Gemini API Key"},
    "app.api_hint": {"en": "Free tier has a daily limit. Upgrade at aistudio.google.com",
                     "zh": "免費方案每日次數有限。付費升級：aistudio.google.com"},
    "app.model": {"en": "Model", "zh": "模型"},
    "app.load_data": {"en": "Load existing data", "zh": "載入既有資料"},
    "app.load_pro": {"en": "Load saved analyses", "zh": "載入 PRO 紀錄"},
    "app.load_legacy": {"en": "Import legacy files", "zh": "併入舊版紀錄"},
    "app.clear": {"en": "Clear workspace", "zh": "清空工作區"},
    "app.respondents_loaded": {"en": "Respondents loaded", "zh": "目前分析中的受訪者"},
    "app.no_data": {
        "en": "No data in the workspace. Run an analysis, or load saved records "
              "from the sidebar.",
        "zh": "工作區沒有資料。請先執行分析，或用左側按鈕載入既有紀錄。"},
    "app.migrated": {"en": "Legacy files were converted to the current format.",
                     "zh": "偵測到舊版檔案，已自動轉換為目前格式。"},

    # --- 頁籤 ---
    "tab.run": {"en": "Run analysis", "zh": "執行新分析"},
    "tab.data": {"en": "Data & descriptors", "zh": "資料與屬性"},
    "tab.review": {"en": "Code review", "zh": "編碼複核"},
    "tab.cross": {"en": "Cross-analysis", "zh": "交互分析"},
    "tab.themes": {"en": "Theme structure", "zh": "主題結構"},
    "tab.lexicon": {"en": "Lexicon induction", "zh": "詞庫誘導"},
    "tab.irr": {"en": "Reliability", "zh": "信度檢定"},
    "tab.export": {"en": "Export", "zh": "匯出"},
    "tab.framework": {"en": "Framework builder", "zh": "框架建構"},
    "common.citation": {"en": "Citation", "zh": "文獻"},
    "common.year": {"en": "Year", "zh": "年份"},
    "common.cited_by": {"en": "Cited by", "zh": "被引次數"},
    "common.abstract": {"en": "Abstract", "zh": "摘要"},
    "common.name": {"en": "Name", "zh": "名稱"},
    "common.role": {"en": "Role", "zh": "角色"},

    # --- 通用 ---
    "common.respondent": {"en": "Respondent", "zh": "受訪者"},
    "common.segment": {"en": "Segment", "zh": "段落"},
    "common.segment_id": {"en": "Segment ID", "zh": "段落ID"},
    "common.title": {"en": "Title", "zh": "標題"},
    "common.quote": {"en": "Quote", "zh": "精簡引文"},
    "common.full_text": {"en": "Full text", "zh": "完整原文"},
    "common.code": {"en": "Code", "zh": "編碼"},
    "common.codes": {"en": "Codes", "zh": "編碼"},
    "common.dimension": {"en": "Dimension", "zh": "維度"},
    "common.polarity": {"en": "Polarity", "zh": "極性"},
    "common.rationale": {"en": "Rationale", "zh": "理由"},
    "common.summary": {"en": "Summary", "zh": "維度重點分析"},
    "common.count": {"en": "Count", "zh": "次數"},
    "common.percent": {"en": "Percent", "zh": "百分比"},
    "common.total": {"en": "Total", "zh": "總計"},
    "common.status": {"en": "Status", "zh": "狀態"},
    "common.source": {"en": "Source", "zh": "來源"},
    "common.download": {"en": "Download", "zh": "下載"},
    "common.save": {"en": "Save", "zh": "儲存"},
    "common.none": {"en": "None", "zh": "無"},
    "common.all": {"en": "All", "zh": "全部"},
    "common.speaker": {"en": "Speaker", "zh": "講者"},
    "common.text": {"en": "Text", "zh": "文字"},
    "common.reviewer": {"en": "Reviewer", "zh": "複核者"},
    "common.time": {"en": "Time", "zh": "時間"},
    "common.action": {"en": "Action", "zh": "動作"},
    "common.detail": {"en": "Detail", "zh": "說明"},
    "common.notes": {"en": "Notes", "zh": "備註"},

    # --- 匯出：Excel 工作表名（需 ≤31 字元，Excel 限制）---
    "sheet.long_table": {"en": "Coded segments (long)", "zh": "編碼長表"},
    "sheet.data_health": {"en": "Data health check", "zh": "資料健檢"},
    "sheet.descriptors": {"en": "Respondent descriptors", "zh": "受訪者屬性"},
    "sheet.crosstab": {"en": "Crosstab", "zh": "交叉表"},
    "sheet.cooc_count": {"en": "Co-occurrence (count)", "zh": "共現矩陣_次數"},
    "sheet.cooc_jaccard": {"en": "Co-occurrence (Jaccard)", "zh": "共現矩陣_Jaccard"},
    "sheet.cooc_pairs": {"en": "Co-occurrence pairs", "zh": "共現配對清單"},
    "sheet.case_count": {"en": "Case matrix (count)", "zh": "跨案例矩陣_次數"},
    "sheet.case_pct": {"en": "Case matrix (percent)", "zh": "跨案例矩陣_百分比"},
    "sheet.polarity_dim": {"en": "Polarity by dimension", "zh": "極性平衡_維度別"},
    "sheet.polarity_overall": {"en": "Polarity overall", "zh": "極性平衡_整體"},
    "sheet.code_ref": {"en": "Code reference", "zh": "編碼對照表"},
    "sheet.themes": {"en": "Second-order themes", "zh": "二階主題表"},
    "sheet.theme_case": {"en": "Theme x respondent", "zh": "主題×受訪者"},
    "sheet.theme_code": {"en": "Theme x code", "zh": "主題×既有編碼"},
    "sheet.first_order": {"en": "First-order concepts", "zh": "一階概念對照"},
    "sheet.unassigned_segs": {"en": "Segments outside themes", "zh": "未納入主題的段落"},
    "sheet.coverage": {"en": "Coverage check", "zh": "覆蓋健檢"},
    "sheet.agreement": {"en": "Agreement by code", "zh": "逐碼一致度"},
    "sheet.overview": {"en": "Overview", "zh": "摘要"},
    "sheet.confusion": {"en": "Dimension confusion", "zh": "維度混淆矩陣"},
    "sheet.polarity_agree": {"en": "Polarity agreement", "zh": "極性一致度"},
    "sheet.disagreements": {"en": "Disagreements", "zh": "分歧清單"},
    "sheet.ai_reliability": {"en": "AI reliability", "zh": "AI信度"},
    "sheet.coding_sheet": {"en": "Coding sheet", "zh": "編碼表"},
    "sheet.code_definitions": {"en": "Code definitions", "zh": "編碼定義"},
    "sheet.review_summary": {"en": "Review summary", "zh": "複核摘要"},
    "sheet.code_changes": {"en": "Changes by code", "zh": "逐碼變動"},
    "sheet.changed_segments": {"en": "Changed segments", "zh": "變動段落對照"},
    "sheet.audit_trail": {"en": "Audit trail", "zh": "稽核軌跡"},
    "sheet.quote_summary": {"en": "Quote verification", "zh": "引文驗證摘要"},
    "sheet.quote_issues": {"en": "Quote mismatches", "zh": "引文不符清單"},
    "sheet.lexicon": {"en": "Lexicon (full)", "zh": "詞庫全表"},
    "sheet.lexicon_stats": {"en": "Lexicon statistics", "zh": "詞庫統計"},
    "sheet.induced_terms": {"en": "Induced feature terms", "zh": "誘導特徵詞"},
    "sheet.over_coded": {"en": "Possible over-coding", "zh": "疑似過度詮釋"},
    "sheet.under_coded": {"en": "Possible under-coding", "zh": "疑似漏標"},

    # --- 統計量欄位名 ---
    "stat.kappa": {"en": "Cohen's kappa", "zh": "Cohen's κ"},
    "stat.pabak": {"en": "PABAK", "zh": "PABAK"},
    "stat.ac1": {"en": "Gwet's AC1", "zh": "Gwet's AC1"},
    "stat.alpha": {"en": "Krippendorff's alpha", "zh": "Krippendorff's α"},
    "stat.agreement": {"en": "Observed agreement", "zh": "觀察一致率"},
    "stat.prevalence_index": {"en": "Prevalence index", "zh": "盛行率指數"},
    "stat.bias_index": {"en": "Bias index", "zh": "偏誤指數"},
    "stat.precision": {"en": "Precision", "zh": "Precision"},
    "stat.recall": {"en": "Recall", "zh": "Recall"},
    "stat.f1": {"en": "F1", "zh": "F1"},
    "stat.jaccard": {"en": "Jaccard", "zh": "Jaccard"},
    "stat.polarity_index": {"en": "Polarity index", "zh": "極性指數"},
    "stat.cramers_v": {"en": "Cramer's V", "zh": "Cramér's V"},
    "stat.n": {"en": "N", "zh": "N"},
}


def t(key, lang=None, **fmt):
    """
    取得介面字串。查不到就回傳 key 本身——寧可畫面上出現一個鍵名，
    也不要因為少一句翻譯就讓程式崩潰。
    """
    entry = STRINGS.get(key)
    text = _pick(entry, lang) if entry else key
    if fmt:
        try:
            return text.format(**fmt)
        except (KeyError, IndexError, ValueError):
            return text
    return text


# =====================================================================
# 完整性檢查
# =====================================================================
def missing_keys(lang):
    """回傳該語言缺少翻譯的鍵，供測試把關。"""
    out = []
    for k, v in STRINGS.items():
        if not (v.get(lang) or "").strip():
            out.append(k)
    for name, table in (("DIM_LABEL", DIM_LABEL), ("STATUS_LABEL", STATUS_LABEL),
                        ("DESCRIPTOR_LABEL", DESCRIPTOR_LABEL),
                        ("DESCRIPTOR_VALUE_LABEL", DESCRIPTOR_VALUE_LABEL),
                        ("RELATION_LABEL", RELATION_LABEL),
                        ("TENDENCY_LABEL", TENDENCY_LABEL),
                        ("SOURCE_LABEL", SOURCE_LABEL),
                        ("SPECIAL_LABEL", SPECIAL_LABEL)):
        for k, v in table.items():
            if not (v.get(lang) or "").strip():
                out.append(f"{name}[{k}]")
    for d, pols in POLARITY_LABEL.items():
        for p, v in pols.items():
            if not (v.get(lang) or "").strip():
                out.append(f"POLARITY_LABEL[{d}][{p}]")
    return out


def coverage_report():
    return {lang: {"total": len(STRINGS), "missing": len(missing_keys(lang))}
            for lang in LANGS}


# =====================================================================
# 方法章節句子 —— 由 tacit_review.methods_facts() 的數字組成
# =====================================================================
def methods_sentence(facts, lang=None):
    """
    依實際複核數據產生可直接貼進論文方法章節的句子。
    數字由 tacit_review 計算，措辭在這裡組——引擎不該內建任何一種語言的敘述。
    """
    lang = lang or _lang
    if not facts or not facts.get("has_data"):
        return ("（尚未開始複核）" if lang == "zh" else "(review not yet started)")

    n = facts["ai_segments"]
    rate = (facts["review_rate"] or 0) * 100
    conf, mod, dele = facts["confirmed"], facts["modified"], facts["deleted"]
    conf_r = (facts["confirm_rate"] or 0) * 100
    mod_r = (facts["modify_rate"] or 0) * 100
    del_r = (facts["delete_rate"] or 0) * 100
    added = facts["human_added"]

    if lang == "zh":
        add_clause = (f"另由研究者補入模型漏標之段落 {added} 段。" if added else "")
        return (f"模型初編碼共產生 {n} 個編碼段落，研究者逐段複核 "
                f"{facts['reviewed']} 段（複核率 {rate:.1f}%），其中 "
                f"{conf} 段確認無誤（{conf_r:.1f}%）、"
                f"{mod} 段經修改（{mod_r:.1f}%）、"
                f"{dele} 段判定不成立而刪除（{del_r:.1f}%）；"
                f"{add_clause}進入後續分析的編碼皆經研究者確認。")

    was = lambda k: "was" if k == 1 else "were"
    segw = lambda k: "segment" if k == 1 else "segments"
    add_clause = (f"A further {added} {segw(added)} missed by the model "
                  f"{was(added)} added by the researcher. " if added else "")
    return (f"The model's first pass produced {n} coded {segw(n)}. The researcher "
            f"reviewed {facts['reviewed']} of them ({rate:.1f}%): {conf} "
            f"{was(conf)} confirmed unchanged ({conf_r:.1f}%), {mod} {was(mod)} "
            f"modified ({mod_r:.1f}%), and {dele} {was(dele)} rejected "
            f"({del_r:.1f}%). {add_clause}Every code entering the analysis was "
            f"verified by the researcher.")


# =====================================================================
# 字串註冊 —— 讓應用層把自己的文案併進來
# =====================================================================
def register(extra):
    """
    合併額外的字串目錄（例如 tacit_strings）。
    核心字彙（維度、統計量、匯出表名）留在本模組；
    介面文案量大且只有 app 用得到，分開維護比較清楚。
    重複的鍵會被後註冊者覆寫，並在 DUPLICATES 留下紀錄供測試檢查。
    """
    for k, v in (extra or {}).items():
        if k in STRINGS and STRINGS[k] != v:
            DUPLICATES.append(k)
        STRINGS[k] = v
    return len(STRINGS)


DUPLICATES = []
