"""
驗證 tacit_framework.py：框架驗證、有／無極性兩種模型、切換框架後整條管線仍正確。

最關鍵的一組測試是「換一個完全不同的理論框架，交互分析仍算得出正確數字」——
那才是 SoftwareX 所要求的 reuse potential 的實證。
"""
import re
import json
import os
import sys
import tempfile

import tacit_framework as F
import tacit_schema as S
import tacit_i18n as I
import tacit_analysis as A

FAIL = []


def check(label, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{label}: got={got} want={want}")
    if not ok:
        FAIL.append(label)


def check_true(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + f"{label}" + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


print("=" * 70)
print("測試 1：內建 RI 框架")
print("=" * 70)
F.reset()
fw = F.builtin_ri()
check("框架 ID", fw.id, F.DEFAULT_FRAMEWORK_ID)
check("維度數", len(fw.dimensions), 4)
check("有極性", fw.has_polarity, True)
check("編碼數（4 維 × 2 極性）", len(fw.codes), 8)
check("編碼內容", fw.codes[:2], ["ANT-P", "ANT-N"])
check("英文標籤", fw.label("reflexivity", "en"), "Reflexivity")
check("中文標籤", fw.label("reflexivity", "zh"), "反思性")
check("極性標籤", fw.polarity_label("reflexivity", "N", "en"),
      "Hubris / Over-confident (−)")
check("編碼完整標籤", fw.code_label("REF-N", "en"),
      "Reflexivity · Hubris / Over-confident (−)")
check("code_of / split_code 往返", fw.split_code(fw.code_of("engagement", "P")),
      ("engagement", "P"))
check_true("每個維度都有定義", all(fw.definition(d, "en") for d in fw.dimensions))
check_true("每個維度都有文獻", all(fw.literature(d) for d in fw.dimensions))
check("agg_dimensions 含 unassigned", fw.agg_dimensions[-1], F.UNASSIGNED)
check_true("指標分正負",
           set(fw.indicators("anticipation")) == {"P", "N"})

# 要防的失效：對雙語 dict 做 list()，拿到的是鍵 ["en","zh"]，
# 介面上每個極性底下只列出兩個空項目「en」「zh」而不是指標內容。
ind_p = fw.indicators("anticipation", "P")
check_true("指標回傳雙語 dict 而非它的鍵", isinstance(ind_p, dict) and
   set(ind_p) >= {"en", "zh"}, str(ind_p)[:80])
check_true("指標內容不是語言代碼", "en" not in ind_p.get("en", []), str(ind_p.get("en"))[:60])
check_true("指定語言直接拿到清單",
   isinstance(fw.indicators("anticipation", "P", lang="zh"), list))
check_true("中文指標拿得到中文", any("情境" in x for x in
                            fw.indicators("anticipation", "P", lang="zh")),
   str(fw.indicators("anticipation", "P", lang="zh")))
check_true("英文指標拿得到英文", any("scenario" in x for x in
                            fw.indicators("anticipation", "P", lang="en")))
check_true("未知語言退回英文",
   fw.indicators("anticipation", "P", lang="fr") ==
   fw.indicators("anticipation", "P", lang="en"))
check_true("polarity=None 加 lang 逐極性給清單",
   all(isinstance(v, list) for v in
       fw.indicators("anticipation", lang="zh").values()))
check_true("每個極性都有指標，沒有空的",
   all(fw.indicators(d, p, lang="en") and fw.indicators(d, p, lang="zh")
       for d in fw.dimensions for p in fw.polarity_values))
check_true("未知維度不炸", fw.indicators("no_such_dim", "P", lang="zh") == [])

# 文獻依據的密度與可查證性。讀者會問「你憑幾篇文獻定義這個維度」，
# 每格兩三筆、又沒有 DOI 的話，這個問題沒辦法回答。
for d in fw.dimensions:
    lits = fw.literature(d)
    grounding = [x for x in lits if x[F.LIT_ROLE] == F.ROLE_GROUNDING]
    check_true(f"{d} 至少 5 筆文獻", len(lits) >= 5, str(len(lits)))
    check_true(f"{d} 至少 3 筆為 grounding", len(grounding) >= 3, str(len(grounding)))
    check_true(f"{d} 多數文獻可用 DOI 查證",
       sum(1 for x in lits if x.get(F.LIT_DOI)) >= len(lits) - 2,
       f"{sum(1 for x in lits if x.get(F.LIT_DOI))}/{len(lits)}")
    check_true(f"{d} 每筆都寫明納入理由",
       all(x.get(F.LIT_NOTE) for x in lits),
       str([x[F.LIT_CITATION][:30] for x in lits if not x.get(F.LIT_NOTE)]))
    for x in lits:
        c = x[F.LIT_CITATION]
        check_true(f"{d}: 引文含年份 — {c[:28]}", bool(re.search(r"\(\d{4}[a-z]?\)", c)), c[:70])
        check_true(f"{d}: 引文不是概念名稱 — {c[:28]}",
                   "—" not in c and " - " not in c, c[:70])
        check_true(f"{d}: 引文夠完整 — {c[:28]}", len(c) > 45, f"{len(c)} 字")
check_true("DOI 不含網址前綴",
   all(not str(x.get(F.LIT_DOI) or "").startswith("http")
       for x in fw.literature()), "應存純 DOI")

print()
print("=" * 70)
print("測試 2：驗證器擋得住壞框架")
print("=" * 70)
cases = [
    ("缺 framework_id", {F.NAME: {"en": "x"}, F.DIMENSIONS: [
        {F.DIM_ID: "a", F.DIM_SHORT: "AA", F.DIM_LABEL: {"en": "A"}}]}),
    ("大寫 id", {F.FRAMEWORK_ID: "BadId", F.NAME: {"en": "x"}, F.DIMENSIONS: [
        {F.DIM_ID: "a", F.DIM_SHORT: "AA", F.DIM_LABEL: {"en": "A"}}]}),
    ("沒有維度", {F.FRAMEWORK_ID: "ok_id", F.NAME: {"en": "x"}, F.DIMENSIONS: []}),
    ("維度 short 太長", {F.FRAMEWORK_ID: "ok_id", F.NAME: {"en": "x"}, F.DIMENSIONS: [
        {F.DIM_ID: "a", F.DIM_SHORT: "TOOLONGX", F.DIM_LABEL: {"en": "A"}}]}),
    ("重複 short", {F.FRAMEWORK_ID: "ok_id", F.NAME: {"en": "x"}, F.DIMENSIONS: [
        {F.DIM_ID: "a", F.DIM_SHORT: "AA", F.DIM_LABEL: {"en": "A"}},
        {F.DIM_ID: "b", F.DIM_SHORT: "AA", F.DIM_LABEL: {"en": "B"}}]}),
    ("使用保留字 UNC", {F.FRAMEWORK_ID: "ok_id", F.NAME: {"en": "x"}, F.DIMENSIONS: [
        {F.DIM_ID: "a", F.DIM_SHORT: "UNC", F.DIM_LABEL: {"en": "A"}}]}),
    ("維度缺 label", {F.FRAMEWORK_ID: "ok_id", F.NAME: {"en": "x"}, F.DIMENSIONS: [
        {F.DIM_ID: "a", F.DIM_SHORT: "AA"}]}),
]
for label, data in cases:
    problems = F.validate(data)
    check_true(f"擋下：{label}", len(problems) > 0, problems[0] if problems else "")
    try:
        F.load_dict(data)
        check_true(f"load_dict 應拋錯：{label}", False)
    except F.FrameworkError:
        pass
check("合法框架通過驗證", F.validate(fw.to_dict()), [])

print()
print("=" * 70)
print("測試 3：無極性框架（例如純歸納式主題分析）")
print("=" * 70)
np_fw = F.blank("thematic_inductive", "Inductive Thematic Analysis",
                [("meaning_making", "MMK", "Meaning making", "意義建構"),
                 ("power_relations", "PWR", "Power relations", "權力關係"),
                 ("temporality", "TMP", "Temporality", "時間性")],
                has_polarity=False, name_zh="歸納式主題分析")
check("無極性", np_fw.has_polarity, False)
check("編碼即維度縮寫", np_fw.codes, ["MMK", "PWR", "TMP"])
check("code_of 不加極性", np_fw.code_of("temporality"), "TMP")
check("split_code 極性為 None", np_fw.split_code("TMP"), ("temporality", None))
check("code_label 不含極性", np_fw.code_label("PWR", "en"), "Power relations")
check("polarity_values 為空", np_fw.polarity_values, [])

print()
print("=" * 70)
print("測試 4：切換框架後 tacit_schema 立即反映（PEP 562 動態解析）")
print("=" * 70)
F.set_active(np_fw)
check("S.DIMENSIONS 換掉了", S.DIMENSIONS,
      ["meaning_making", "power_relations", "temporality"])
check("S.CODES 換掉了", S.CODES, ["MMK", "PWR", "TMP"])
check("S.HAS_POLARITY", S.HAS_POLARITY, False)
check("無極性時 norm_polarity 一律 None", S.norm_polarity("P"), None)
check("norm_dimension 認得新維度", S.norm_dimension("temporality"), "temporality")
check("norm_dimension 不認得舊維度", S.norm_dimension("anticipation"), None)
check("make_code 不塞極性",
      S.make_code("temporality", "P")[S.POLARITY], None)
seg_np = {S.SEGMENT_ID: "X1", S.CODES_F: [S.make_code("temporality")]}
check("codes_of 產出無極性碼", S.codes_of(seg_np), ["TMP"])
check("i18n 維度標籤跟著換", I.dim("power_relations", "en"), "Power relations")
check("i18n 中文標籤跟著換", I.dim("meaning_making", "zh"), "意義建構")
check("i18n code_label 無極性", I.code_label("TMP", "en"), "Temporality")

print()
print("=" * 70)
print("測試 5：換框架後交互分析仍算得出正確數字")
print("=" * 70)


def seg(sid, dims):
    return {S.SEGMENT_ID: sid, S.TITLE: sid, S.QUOTE: f"q{sid}",
            S.FULL_TEXT: f"t{sid}",
            S.CODES_F: [S.make_code(d) for d in dims]}


recs = [
    {S.RESPONDENT: "P1", S.DESCRIPTORS: S.norm_descriptors(
        {"institution_type": "academia"}), S.SUMMARY: "",
     S.SEGMENTS: [seg("s1", ["meaning_making", "temporality"]),   # 多重
                  seg("s2", ["power_relations"])]},
    {S.RESPONDENT: "P2", S.DESCRIPTORS: S.norm_descriptors(
        {"institution_type": "industry"}), S.SUMMARY: "",
     S.SEGMENTS: [seg("s1", ["temporality"]),
                  seg("s2", ["meaning_making", "temporality"])]},  # 多重
]
long_df = A.build_long_df(recs)
print("  長表欄位:", list(long_df.columns)[:6], "…")
# P1: 3 碼(2段)、P2: 3 碼(2段) = 6 碼、4 段
check("長表列數", len(long_df), 6)
check("維度值為新框架的識別碼",
      sorted(set(long_df[S.DIMENSION])),
      ["meaning_making", "power_relations", "temporality"])
check_true("無極性時 polarity 欄為 None",
           long_df[S.POLARITY].isna().all() or
           set(long_df[S.POLARITY].dropna()) == set())

m = A.case_matrix(long_df)
print(m.to_string())
check("跨案例矩陣欄位＝三個新碼", list(m.columns), ["MMK", "PWR", "TMP"])
check("P2 TMP 計 2", int(m.loc["P2", "TMP"]), 2)
check("P1 列合計 3", int(m.loc["P1"].sum()), 3)

cnt, jac, tot = A.cooccurrence(recs, level=A.LEVEL_SEGMENT)
# MMK 與 TMP 同段共現 2 次（P1-s1, P2-s2）
check("共現矩陣為 3×3", cnt.shape, (3, 3))
check("MMK × TMP 共現 2 次", int(cnt.loc["MMK", "TMP"]), 2)
check("TMP 總次數 3", int(tot["TMP"]), 3)

ct, pct = A.crosstab_by_descriptor(long_df, "institution_type")
check("交叉表欄位為新碼", sorted(ct.columns), ["MMK", "PWR", "TMP"])
check("學術界總碼數", int(ct.loc["academia"].sum()), 3)

cov = {r[S.RESPONDENT]: r for r in A.coverage_report(recs)}
check("P1 涵蓋維度數（s1 兩個 + s2 一個）", cov["P1"]["dimensions_covered"], 3)
check("P1 多重編碼段落", cov["P1"]["multi_coded_segments"], 1)

print()
print("=" * 70)
print("測試 6：存檔／載入往返，以及 activate_by_id")
print("=" * 70)
with tempfile.TemporaryDirectory() as d:
    path = F.save(np_fw, os.path.join(d, "thematic_inductive.json"))
    reloaded = F.load_file(path)
    check("往返後 ID 相同", reloaded.id, np_fw.id)
    check("往返後編碼相同", reloaded.codes, np_fw.codes)
    check("往返後資料完全相同", reloaded.to_dict(), np_fw.to_dict())
    avail = F.list_available(d)
    check("列出可用框架", [a[0] for a in avail], ["thematic_inductive"])
    with open(os.path.join(d, "broken.json"), "w", encoding="utf-8") as fh:
        fh.write("{ not valid json")
    check("壞檔被略過而非讓程式掛掉",
          [a[0] for a in F.list_available(d)], ["thematic_inductive"])
    F.activate_by_id("thematic_inductive", d)
    check("依 ID 啟用", F.active().id, "thematic_inductive")
    try:
        F.activate_by_id("nope", d)
        check_true("不存在的框架應拋錯", False)
    except F.FrameworkError:
        check_true("不存在的框架應拋錯", True)

print()
print("=" * 70)
print("測試 7：切回 RI 框架，舊資料與舊行為完全復原")
print("=" * 70)
F.reset()
check("預設回到內建 RI", F.active().id, F.DEFAULT_FRAMEWORK_ID)
check("S.CODES 復原", S.CODES,
      ["ANT-P", "ANT-N", "REF-P", "REF-N", "ENG-P", "ENG-N", "RES-P", "RES-N"])
check("norm_polarity 復原", S.norm_polarity("p"), "P")
legacy = {"受訪者": "舊檔", "反思性": {"P": [], "N": [
    {"標題": "t", "精簡引文": "q", "完整原文": "f"}]}}
rec = S.migrate_record(legacy)
check("舊檔遷移仍正常", S.codes_of(rec[S.SEGMENTS][0]), ["REF-N"])
check("i18n 標籤復原", I.dim(S.REFLEXIVITY, "zh"), "反思性")

print()
print("=" * 70)
print("測試 8：內建框架可寫成檔案供使用者複製修改")
print("=" * 70)
with tempfile.TemporaryDirectory() as d:
    path = F.ensure_builtin_on_disk(d)
    check_true("檔案已產生", os.path.exists(path))
    data = json.load(open(path, encoding="utf-8"))
    check("檔案可再載入", F.load_dict(data).id, F.DEFAULT_FRAMEWORK_ID)
    check_true("結構鍵皆為 ASCII", all(k.isascii() for k in data))
    check_true("維度識別碼皆為 ASCII",
               all(x[F.DIM_ID].isascii() and x[F.DIM_SHORT].isascii()
                   for x in data[F.DIMENSIONS]))
    check_true("標籤含中英雙語",
               all(set(x[F.DIM_LABEL]) >= {"en", "zh"} for x in data[F.DIMENSIONS]))
    check("重複呼叫不覆寫", F.ensure_builtin_on_disk(d), path)

print()
print("=" * 70)
print("測試 X：案例層屬性也由框架決定")
print("=" * 70)
# 為什麼要有這一段：屬性欄位（institution_type / role_level / experience）
# 若寫死在 tacit_schema 裡，就全部是訪談研究的形狀，「任何演繹式架構
# 都適用」這句話只對維度成立——換一種語料（永續報告、政策文件、專利說明書）
# 就會在屬性這一層卡住，而使用者得改程式才能繼續。
import tacit_schema as _S                                      # noqa: E402

_F_ = F  # 可讀性

# 沒宣告 descriptors 的框架必須維持預設的訪談欄位，一個字都不能變——
# 使用者手上所有既有的分析紀錄都是照那個形狀存的。
_F_.activate_by_id("ri_stilgoe_2013")
check("未宣告時沿用訪談預設", _S.descriptor_keys(),
      ["institution_type", "role_level", "sector", "experience"])
check_true("預設值裡含 UNSPECIFIED",
           _S.UNSPECIFIED in _S.descriptor_fields()["institution_type"])
check("舊紀錄照樣正規化得出來",
      _S.norm_descriptors({"institution_type": "academia",
                           "role_level": "researcher"})["institution_type"],
      "academia")

_esg = _F_.load_dict({
    "framework_id": "esg_probe", "name": {"en": "ESG probe"},
    "dimensions": [
        {"id": "governance", "short": "GOV", "label": {"en": "Governance"}},
        {"id": "emissions", "short": "EMI", "label": {"en": "Emissions"}}],
    "descriptors": {
        "industry": ["finance", "manufacturing", "utilities"],
        "report_year": ["y2023", "y2024"],
        "assurance": ["none", "limited", "reasonable"]},
})
_F_.set_active(_esg)
check("宣告了就用自己的欄位", _S.descriptor_keys(),
      ["industry", "report_year", "assurance"])
check_true("訪談欄位完全不殘留",
           not any(k in _S.descriptor_keys()
                   for k in ("institution_type", "role_level", "experience")))
check("自訂欄位的合法值收得進來",
      _S.norm_descriptors({"industry": "finance", "assurance": "limited",
                           "report_year": "y2024"})["assurance"], "limited")
check("非法值仍收斂為 other",
      _S.norm_descriptors({"industry": "banana"})["industry"], "other")
check_true("空白紀錄用的是新欄位",
           set(_S.blank_descriptors()) ==
           {"industry", "report_year", "assurance", _S.DESCRIPTOR_BASIS})

# 切回去要立刻恢復，跟維度一樣——殘留會讓下一個分析悄悄用錯欄位
_F_.activate_by_id("ri_stilgoe_2013")
check("切回原框架後欄位立刻恢復", _S.descriptor_keys()[0], "institution_type")

# 值的規則要比識別碼寬鬆：單一字元、以數字開頭都是合理的列舉標記
check_true("單字元的值收得進來",
           not any("invalid values" in p for p in _F_.validate({
               "framework_id": "v_ok", "name": {"en": "v"},
               "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}],
               "descriptors": {"grade": ["a", "b", "c"]}})),
           str(_F_.validate({
               "framework_id": "v_ok", "name": {"en": "v"},
               "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}],
               "descriptors": {"grade": ["a", "b", "c"]}})))
check_true("以數字開頭的值也收",
           not _F_.validate({
               "framework_id": "v_ok2", "name": {"en": "v"},
               "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}],
               "descriptors": {"year": ["2023", "2024"]}}))

# 寫壞的宣告必須在載入時就報錯，**不可以安靜地退回訪談預設**。
# 那正是這個專案一路抓到的那種無聲替換：框架看起來正常運作，
# 使用者要到分析做到一半才發現欄位根本不是自己宣告的那些。
_probs = _F_.validate({
    "framework_id": "bad_desc", "name": {"en": "bad"},
    "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}],
    "descriptors": {"Bad Key!": ["x"], "empty": []},
})
check_true("非法欄位名會被 validate 抓到",
           any("invalid descriptor field name" in p for p in _probs), str(_probs))
check_true("欄位沒有可用值會被抓到",
           any("no usable values" in p for p in _probs), str(_probs))
check_true("全部不可用時明確報錯，而不是退回預設",
           any("no usable field survived" in p for p in _probs), str(_probs))
check_true("錯誤訊息告訴作者怎麼修",
           any("remove the key" in p for p in _probs), str(_probs))
check_true("descriptors 不是物件也會被抓到",
           any("must be a JSON object" in p for p in _F_.validate({
               "framework_id": "d_bad", "name": {"en": "d"},
               "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}],
               "descriptors": ["not", "an", "object"]})))
check_true("完全不宣告 descriptors 不算問題",
           not _F_.validate({
               "framework_id": "no_desc", "name": {"en": "n"},
               "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}]}))

_blank = _F_.load_dict({
    "framework_id": "no_desc", "name": {"en": "n"},
    "dimensions": [{"id": "d1", "short": "D1", "label": {"en": "D1"}}],
})
_F_.set_active(_blank)
check_true("沒宣告時退回訪談預設",
           "institution_type" in _S.descriptor_keys())
_F_.activate_by_id("ri_stilgoe_2013")

# 介面標籤：自訂欄位不可能事先出現在翻譯表裡，退路要可讀
import tacit_i18n as _I                                        # noqa: E402
check("未知欄位名 humanise 成可讀英文", _I.descriptor("report_year", "en"),
      "Report year")
check("已知欄位仍用正式翻譯", _I.descriptor("institution_type", "zh"), "機構類型")
check("屬性值保持原樣，不做 humanise", _I.descriptor_value("y2024", "en"), "y2024")

print()
print("=" * 70)
print("測試 X：排除條件（構念邊界必須寫在框架裡，不能由模型當場決定）")
print("=" * 70)
# 要防的失效：engagement 的指標只寫了 upstream participation / two-way
# dialogue / co-creation / including non-expert voices——全是正面例子，
# 而正面例子界定不出邊界。模型於是自己補：把「我們用 design thinking 想
# 使用者要什麼」「就是 target user，我們的目標客群」，以及英文稿裡的
# "Project Overview"、"MRI Based Imaging" 全判成 engagement 的正向證據。
# 一份 20,856 字元的訪談稿人工標 7 段參與，軟體標了 33 段。
#
# 這會直接打穿框架模組存在的理由：如果構念的操作型邊界是模型想出來的，
# 「編碼依附於一個有文獻出處的框架」這個主張就是假的。
_fw = F.builtin_ri()
check_true("內建框架有排除條件", _fw.has_exclusions())
for _d in _fw.dimensions:
    check_true(f"{_d} 有英文排除條件", len(_fw.exclusions(_d, "en")) >= 3,
               str(len(_fw.exclusions(_d, "en"))))
    check_true(f"{_d} 中英文條數一致",
               len(_fw.exclusions(_d, "en")) == len(_fw.exclusions(_d, "zh")),
               f'en={len(_fw.exclusions(_d, "en"))} zh={len(_fw.exclusions(_d, "zh"))}')

# 每一條真的對應到一種發生過的誤判
_eng = " ".join(_fw.exclusions("engagement", "en")).lower()
check_true("參與：排除「只是提到使用者」", "mention" in _eng)
check_true("參與：排除內部的使用者中心設計推理",
           "internally" in _eng or "design thinking" in _eng)
check_true("參與：排除單純的商業關係", "commercial" in _eng)
_ref = " ".join(_fw.exclusions("reflexivity", "en")).lower()
check_true("反思：明說缺席不是自負的證據", "absence" in _ref)
check_true("反思：排除「遵循既有流程」", "compliance" in _ref or "process" in _ref)
_ant = " ".join(_fw.exclusions("anticipation", "en")).lower()
check_true("預期：排除一般商業預測", "forecast" in _ant)
_res = " ".join(_fw.exclusions("responsiveness", "en")).lower()
check_true("回應：排除例行迭代", "iteration" in _res or "routine" in _res)

# 沒寫排除條件的框架不能因此炸掉——舊框架檔都沒有這個欄位
_blank = F.blank("excl_test", "Exclusion Test",
                 [("alpha", "ALP", "Alpha", "甲"), ("beta", "BET", "Beta", "乙")])
check("空白框架的排除條件是空清單", _blank.exclusions("alpha", "en"), [])
check_true("空白框架 has_exclusions 為假", not _blank.has_exclusions())
check("不存在的維度回空清單", _blank.exclusions("不存在", "en"), [])


print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
