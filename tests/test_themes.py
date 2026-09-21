"""驗證 tacit_themes.py（英文 schema 版）：彙集、兩階段解析、防幻覺、統計、SVG。"""
import copy
import json
import sys
import xml.etree.ElementTree as ET

import tacit_schema as S
import tacit_i18n as I
import tacit_themes as T

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


def seg(sid, title, quote, codes):
    return {S.SEGMENT_ID: sid, S.TITLE: title, S.QUOTE: quote,
            S.FULL_TEXT: quote + "（完整）",
            S.CODES_F: [S.make_code(d, p) for d, p in codes]}


RECORDS = [
    {S.RESPONDENT: "產A", S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
     S.SEGMENTS: [
         seg("S1", "以專業權威排除外部意見", "我們最懂這個技術", [(S.REFLEXIVITY, "N")]),
         seg("S2", "拒絕依回饋調整", "還是照原計畫走不會改", [(S.RESPONSIVENESS, "N")]),
         seg("S3", "把參與當成告知", "定案之後再跟他們說明", [(S.ENGAGEMENT, "N")]),
     ]},
    {S.RESPONDENT: "產B", S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
     S.SEGMENTS: [
         seg("S1", "技術專家的知識壟斷", "外行人根本不懂", [(S.REFLEXIVITY, "N")]),
         seg("S2", "沉沒成本鎖死路徑", "投資已經下去了改不動", [(S.RESPONSIVENESS, "N")]),
     ]},
    {S.RESPONDENT: "學C", S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
     S.SEGMENTS: [
         seg("S1", "承認知識的邊界", "坦白說我們也不敢說自己都對", [(S.REFLEXIVITY, "P")]),
         seg("S2", "上游納入多元聲音", "一開始就邀請民間團體", [(S.ENGAGEMENT, "P")]),
     ]},
]

print("=" * 70)
print("測試 0：輸出語言必須解析成具體語言（AUTO 在第二階段沒有意義）")
print("=" * 70)
# 要防的失效：介面與逐字稿都是中文，主題名稱卻整批是英文。
# 原因是 AUTO 的指示寫「跟著逐字稿的語言走」，但第二階段的輸入只有
# 第一階段產出的暫定主題，模型手上根本沒有逐字稿，於是自行選了英文。
_zh_items = [{T.GLOBAL_ID: "G1", S.TITLE: "技術鎖定的擔憂",
              S.QUOTE: "這個架構一旦定了就很難改", S.FULL_TEXT: "x"}] * 3
_en_items = [{T.GLOBAL_ID: "G1", S.TITLE: "Concern about lock-in",
              S.QUOTE: "once the architecture is set it is hard to change",
              S.FULL_TEXT: "x"}] * 3


def _lang_line(prompt):
    return next((l for l in prompt.split("\n") if "Write all output" in l), "")


p_zh = T.build_stage1_prompt(_zh_items, S.ANALYSIS_LANG_AUTO)
p_en = T.build_stage1_prompt(_en_items, S.ANALYSIS_LANG_AUTO)
check_true("AUTO + 中文語料 → 明確指定繁體中文",
           "Traditional Chinese" in _lang_line(p_zh), _lang_line(p_zh)[:70])
check_true("AUTO + 英文語料 → 明確指定英文",
           "in English" in _lang_line(p_en), _lang_line(p_en)[:70])
check_true("不再只丟相對指示給模型自行推論",
           "SAME language as the transcript" not in p_zh)

_prov = [{S.THEME_NAME: "技術路徑鎖定", S.THEME_DEFINITION: "受訪者擔心架構定案後難改",
          S.MEMBER_IDS: ["G1"]}]
p2 = T.build_stage2_prompt(_prov, S.ANALYSIS_LANG_AUTO)
check_true("第二階段（看不到逐字稿）也解析得出中文",
           "Traditional Chinese" in _lang_line(p2), _lang_line(p2)[:70])
check_true("明確指定語言時不受語料影響",
           "in English" in _lang_line(T.build_stage1_prompt(_zh_items, "en")))
check_true("指定日文也照辦",
           "Japanese" in _lang_line(T.build_stage1_prompt(_zh_items, "ja")))
check("空語料時 AUTO 仍退回相對指示",
      S.resolve_analysis_lang(S.ANALYSIS_LANG_AUTO, ""), S.ANALYSIS_LANG_AUTO)
check("中文樣本解析為繁中",
      S.resolve_analysis_lang(S.ANALYSIS_LANG_AUTO, "這是中文"), "zh-Hant")
check("英文樣本解析為英文",
      S.resolve_analysis_lang(S.ANALYSIS_LANG_AUTO, "this is english"), "en")
check("已指定的語言不會被樣本改掉",
      S.resolve_analysis_lang("de", "這是中文"), "de")

# 語言必須由**原始語料**判斷一次，而不是由上一階段的產出判斷。
# 要防的失效：四份全英文訪談稿跑出中文主題。第一階段偶爾失手產出中文後，
# 第二階段拿那些中文暫定主題去判斷語言，於是照著錯誤繼續錯下去。
import json as _json
import re as _re
_en_items = [{T.GLOBAL_ID: f"G{i:04d}", S.RESPONDENT: "P1",
              S.TITLE: "Concern about technological lock-in",
              S.QUOTE: "once the architecture is fixed it is hard to change",
              S.FULL_TEXT: "x"} for i in range(1, 9)]
_calls = []


def _drifting_model(prompt):
    """模擬第一階段失手產出中文，檢查錯誤會不會沿管線延續。"""
    _calls.append(prompt)
    if "PROVISIONAL THEMES" in prompt:
        return _json.dumps({"themes": [{
            "name": "Path lock-in", "definition": "d",
            "aggregate_dimension": "anticipation",
            "merged_from": ["技術路徑鎖定"],
            "frame_relation": "aligned", "polarity_tendency": "N"}]})
    ids = _re.findall(r"^(G\d{4}) \|", prompt, _re.M)
    return _json.dumps({"provisional_themes": [{
        "name": "技術路徑鎖定", "definition": "受訪者擔心架構定案後難以更動",
        "member_ids": ids[:3]}]})


T.induce_themes(_en_items, _drifting_model, chunk_size=4, min_size=2,
                analysis_lang=S.ANALYSIS_LANG_AUTO)
_s2 = [p for p in _calls if "PROVISIONAL THEMES" in p]
check_true("第二階段確實被呼叫到（測試本身有效）", len(_s2) == 1, str(len(_s2)))
_line = next(l for l in _s2[0].split("\n") if "Write all output" in l)
check_true("第一階段誤產中文，第二階段仍指定英文（錯誤不沿管線延續）",
           "in English" in _line, _line.strip()[:70])

print()
print("=" * 70)
print("測試 1：一階概念彙集與全域 ID")
print("=" * 70)
items = T.collect_first_order(RECORDS)
check("一階概念總數", len(items), 7)
check("全域 ID 唯一", len({i[T.GLOBAL_ID] for i in items}), 7)
dup = [i for i in items if i[T.SOURCE_SEGMENT_ID] == "S1"]
check_true("跨案例同名段落 ID 被重新配發",
           len({i[T.GLOBAL_ID] for i in dup}) == 3,
           str([i[T.GLOBAL_ID] for i in dup]))
check("既有編碼帶入", items[0][T.EXISTING_CODES], ["REF-N"])
check_true("欄位皆為 ASCII", all(k.isascii() for k in items[0]))

print()
print("=" * 70)
print("測試 2：提示詞為英文指令，且帶分析語言參數")
print("=" * 70)
p1 = T.build_stage1_prompt(items, analysis_lang="zh-Hant")
check_true("含全部一階 ID", all(i[T.GLOBAL_ID] in p1 for i in items))
check_true("明確要求不預設理論框架", "Do NOT assume any theoretical framework" in p1)
check_true("要求至少兩個一階概念", "AT LEAST TWO first-order concepts" in p1)
check_true("帶入繁中輸出指示", "Traditional Chinese" in p1)
p1_auto = T.build_stage1_prompt(items)
# AUTO 不可以產生「SAME language as the transcript」這種相對指示。
# 語料是中文，就該解析成明確的繁體中文指示，而不是把判斷丟給模型。
check_true("AUTO 依語料解析成明確語言，而非相對指示",
           "Traditional Chinese" in p1_auto and
           "SAME language as the transcript" not in p1_auto)
p1_en = T.build_stage1_prompt(items, analysis_lang="en")
check_true("可指定英文輸出", "Write all output in English" in p1_en)
check_true("指令本身為英文（不含中文）",
           not any("一" <= ch <= "鿿" for ch in T._STAGE1_HEADER))

print()
print("=" * 70)
print("測試 3：stage1 解析與髒資料防禦")
print("=" * 70)
ids = [i[T.GLOBAL_ID] for i in items]
raw1 = json.dumps({"provisional_themes": [
    {"name": "Technical expertise is converted into unchallengeable authority",
     "definition": "d", "member_ids": [ids[0], ids[3], "G9999"],
     "exemplar_id": ids[0]},
    {"name": "too small", "definition": "x", "member_ids": [ids[1]]},
    {"name": "all hallucinated", "definition": "x", "member_ids": ["G8888", "G7777"]},
    {"name": "", "definition": "no name", "member_ids": [ids[1], ids[4]]},
    {"name": "duplicate ids should be deduped", "definition": "y",
     "member_ids": [ids[1], ids[1], ids[4]], "exemplar_id": "G6666"},
]})
prov, dropped = T.parse_stage1(raw1, ids, min_size=2)
print("  留下:", [(p[S.THEME_NAME][:28], p[S.MEMBER_IDS]) for p in prov])
check("有效主題數", len(prov), 2)
check("幻覺 ID 被剔除", prov[0][S.MEMBER_IDS], [ids[0], ids[3]])
check("重複 ID 去重", prov[1][S.MEMBER_IDS], [ids[1], ids[4]])
check("無效 exemplar 改用第一個成員", prov[1]["exemplar_id"], ids[1])
check("過小主題被記錄", len(dropped), 2)
check_true("捨棄理由為英文", dropped[0]["reason"].isascii())

print()
print("=" * 70)
print("測試 4：stage2 合併與維度對映")
print("=" * 70)
prov_full = [
    {S.THEME_NAME: "authority A", S.THEME_DEFINITION: "d",
     S.MEMBER_IDS: [ids[0]], "exemplar_id": ids[0]},
    {S.THEME_NAME: "authority B", S.THEME_DEFINITION: "d",
     S.MEMBER_IDS: [ids[3]], "exemplar_id": ids[3]},
    {S.THEME_NAME: "path lock-in", S.THEME_DEFINITION: "d",
     S.MEMBER_IDS: [ids[1], ids[4]], "exemplar_id": ids[1]},
    {S.THEME_NAME: "escapes the frame", S.THEME_DEFINITION: "d",
     S.MEMBER_IDS: [ids[2]], "exemplar_id": ids[2]},
]
raw2 = json.dumps({"themes": [
    {"name": "Technical expertise is converted into unchallengeable authority",
     "definition": "d", "aggregate_dimension": "reflexivity",
     "dimension_rationale": "we-know-best", "frame_relation": "aligned",
     "polarity_tendency": "N", "merged_from": ["1", "[2]"]},
    {"name": "Sunk cost renders the innovation trajectory irreversible",
     "definition": "d", "aggregate_dimension": "responsiveness",
     "dimension_rationale": "obdurate", "frame_relation": "extends",
     "polarity_tendency": "N", "merged_from": [3]},
    {"name": "Temporal politics inside the organisation compresses deliberation",
     "definition": "d", "aggregate_dimension": "no_such_dimension",
     "dimension_rationale": "escapes", "frame_relation": "garbage",
     "polarity_tendency": "garbage", "merged_from": ["4", "99"]},
], "unassigned_note": "points to a temporal gap"})
themes, note = T.parse_stage2(raw2, prov_full)
for t in themes:
    print(f"  {t[S.THEME_ID]} [{t[S.AGG_DIMENSION]}/{t[S.FRAME_RELATION]}/"
          f"{t[S.POLARITY_TENDENCY]}] ids={t[S.MEMBER_IDS]}")
check("最終主題數", len(themes), 3)
check("合併兩個暫定主題的 ID 聯集",
      sorted(themes[0][S.MEMBER_IDS]), sorted([ids[0], ids[3]]))
unc = [t for t in themes if "Temporal" in t[S.THEME_NAME]][0]
check("非法維度歸入 unassigned", unc[S.AGG_DIMENSION], S.UNASSIGNED)
check("非法極性傾向回退", unc[S.POLARITY_TENDENCY], S.TENDENCY_MIXED)
check("非法框架關係回退", unc[S.FRAME_RELATION], S.RELATION_ALIGNED)
check("超出範圍的索引被忽略", len(unc[S.MEMBER_IDS]), 1)
check("unassigned 排最後", themes[-1][S.AGG_DIMENSION], S.UNASSIGNED)
check("主題 ID 連續", [t[S.THEME_ID] for t in themes], ["T01", "T02", "T03"])
check("未歸屬說明保留", note, "points to a temporal gap")
check_true("主題欄位皆為 ASCII", all(k.isascii() for k in themes[0]))

print()
print("=" * 70)
print("測試 5：端到端 induce_themes（注入假 LLM）")
print("=" * 70)
calls = []


def fake_llm(prompt):
    calls.append(prompt)
    if "PROVISIONAL THEMES" in prompt:
        return "Here you go:\n" + raw2 + "\nDone."
    return ('{"provisional_themes": [{"name": "authority A", '
            '"definition": "with a\nliteral newline", '
            f'"member_ids": ["{ids[0]}", "{ids[3]}"], "exemplar_id": "{ids[0]}"}}]}}')


th, note2, dbg = T.induce_themes(items, fake_llm, chunk_size=4)
print("  debug:", {k: v for k, v in dbg.items() if k != "dropped"})
check("批次數（7 概念 / 每批 4）", dbg["batches"], 2)
check("呼叫次數 = 2 批 + 1 合併", len(calls), 3)
check("端到端主題數", len(th), 3)
check_true("debug 欄位為 ASCII", all(k.isascii() for k in dbg))

print()
print("=" * 70)
print("測試 6：主題層統計")
print("=" * 70)
tt = T.theme_table(themes, items)
print(f"  T01 respondents={tt[0]['respondents']} concepts={tt[0]['concept_count']}")
check("T01 由兩位受訪者支撐", tt[0]["respondent_count"], 2)
check("T01 支持者", tt[0]["respondents"], ["產A", "產B"])

mat, speakers = T.theme_case_matrix(themes, items)
check("受訪者依出現順序", speakers, ["產A", "產B", "學C"])
check("T01 在產A 計 1", mat[0]["產A"], 1)
check("T01 支持率", mat[0]["support_rate"], 0.67)

cov = T.coverage_report(themes, items)
print("  覆蓋:", cov)
check("一階概念總數", cov["total_concepts"], 7)
check("已納入", cov["assigned_concepts"], 5)
check("覆蓋率", cov["coverage"], 0.714)
check_true("薄弱主題被標出", len(cov["thin_themes"]) >= 1, str(cov["thin_themes"]))
check("unassigned 維度計 1", cov["themes_by_dimension"][S.UNASSIGNED], 1)
check("未納入主題的概念數", len(T.unassigned_items(themes, items)), 2)

xt = T.theme_by_existing_code(themes, items)
check("T01 對應 REF-N", xt[0].get("REF-N", 0), 2)

print()
print("=" * 70)
print("測試 7：Gioia SVG（標籤由呼叫端注入，可任意語言）")
print("=" * 70)
for lang in I.LANGS:
    I.set_lang(lang)
    svg = T.render_data_structure_svg(
        themes, items,
        dim_label=lambda d: I.dim(d),
        relation_label=lambda r: I.relation(r),
        column_titles=("1st-Order Concepts", "2nd-Order Themes",
                       "Aggregate Dimensions"))
    root = ET.fromstring(svg)
    texts = [e.text for e in root.iter() if e.tag.endswith("text") and e.text]
    check_true(f"{lang} SVG 為合法 XML", root is not None)
    check_true(f"{lang} 含三欄標題",
               all(any(h in t for t in texts)
                   for h in ["1st-Order", "2nd-Order", "Aggregate"]))
    check_true(f"{lang} 聚合維度用該語言",
               any(I.dim(S.REFLEXIVITY, lang) in t for t in texts),
               I.dim(S.REFLEXIVITY, lang))
    check_true(f"{lang} 未歸屬有出現",
               any(I.dim(S.UNASSIGNED, lang) in t for t in texts))
    check_true(f"{lang} 高度隨主題數成長", int(root.get("height")) > 200)
I.set_lang("en")
svg_default = T.render_data_structure_svg(themes, items)
check_true("未注入標籤時退回識別碼且不炸",
           ET.fromstring(svg_default) is not None)
open("_preview_data_structure.svg", "w", encoding="utf-8").write(
    T.render_data_structure_svg(themes, items,
                                dim_label=lambda d: I.dim(d, "en"),
                                relation_label=lambda r: I.relation(r, "en")))
print("  已輸出預覽圖 _preview_data_structure.svg")

print()
print("=" * 70)
print("測試 8：邊界情況")
print("=" * 70)
check("空紀錄彙集", T.collect_first_order([]), [])
check_true("無主題時 SVG 合法",
           ET.fromstring(T.render_data_structure_svg([], [])) is not None)
check("空主題覆蓋率", T.coverage_report([], items)["coverage"], 0.0)
try:
    T.extract_json("no json at all")
    check_true("無 JSON 應拋錯", False)
except ValueError:
    check_true("無 JSON 應拋錯", True)
empty_th, _n, empty_dbg = T.induce_themes(
    items, lambda p: '{"provisional_themes": []}', chunk_size=10)
check("全數無效時回空主題", empty_th, [])
check("空主題時仍記錄批次", empty_dbg["batches"], 1)
long_theme = [S.migrate_theme({S.THEME_NAME: "n" * 60, S.AGG_DIMENSION: S.ANTICIPATION,
                               S.MEMBER_IDS: [i[T.GLOBAL_ID] for i in items]})]
check_true("超長主題名不炸圖",
           ET.fromstring(T.render_data_structure_svg(long_theme, items)) is not None)
check_true("舊中文鍵主題仍可解析（經 migrate_theme）",
           S.migrate_theme({"主題名稱": "x", "聚合維度": "反思性"})[S.AGG_DIMENSION]
           == S.REFLEXIVITY)

print()
print("=" * 70)
print("測試 N：維度名稱的變體寫法（Gioia 圖表少一個維度的真正原因）")
print("=" * 70)
# 要防的失效：Gioia 圖表永遠只長出三個維度，responsiveness 完全不見。
# 原因不是模型沒判斷出來，而是它寫的是 "Responsiveness"——首字大寫。
# 精確比對認不得，靜靜落到 unassigned，畫面上看起來就像資料裡沒有這個維度。
# 這種錯不會報錯，而且結論看起來完全合理，研究者會直接寫進論文。
import tacit_framework as _F
_F.reset()
for _v in ["Responsiveness", "responsiveness ", "RESPONSIVENESS",
           "Responsiveness" + chr(10), "Responsiveness (capacity to change)",
           "RES", "res"]:
    check(f"變體寫法仍歸到 responsiveness：{_v!r}",
          S.norm_dimension(_v), S.RESPONSIVENESS)
check("顯示標籤也認得（Public Engagement）",
      S.norm_dimension("Public Engagement"), S.ENGAGEMENT)
check("中文標籤也認得", S.norm_dimension("回應性"), S.RESPONSIVENESS)
check("Unassigned 大寫也認得", S.norm_dimension("Unassigned"), S.UNASSIGNED)
check("補充說明不影響判讀",
      S.norm_dimension("responsiveness — the capacity to stop"),
      S.RESPONSIVENESS)

# 但不做模糊猜測：猜錯維度比留在 unassigned 更糟，
# 因為前者會產生一個看不出是錯的結論。
for _v in ["response", "responsivity", "banana", "", None, 42]:
    check_true(f"認不出來就回 None，不亂猜：{_v!r}",
               S.norm_dimension(_v) is None)

# 實測 qwen2.5:7b 會把輸出格式裡的列舉整串抄回來，等於**沒有選**。
# 替它挑第一個，就是把工具的猜測偽裝成研究者的判斷，而且挑錯了看不出來。
# 一律回 None，讓它落到未歸屬並被計數，研究者才查得到。
for _v in ["engagement|responsiveness", "anticipation|engagement",
           "engagement|anticipation",
           "anticipation|reflexivity|engagement|responsiveness|unassigned",
           "engagement, responsiveness"]:
    check_true(f"同時給多個維度＝沒有選，不替它挑：{_v!r}",
               S.norm_dimension(_v) is None)

# 沒認出來的值必須被記錄下來，否則介面上只看得到「未歸屬 +1」，
# 查不出是模型的判斷還是它沒遵守格式。
_iss = []
T.parse_stage2(json.dumps({"themes": [
    {"name": "Z", "definition": "d",
     "aggregate_dimension": "engagement|responsiveness",
     "merged_from": ["1"]}]}),
    [{S.THEME_NAME: "p", S.THEME_DEFINITION: "d",
      S.MEMBER_IDS: [items[0][T.GLOBAL_ID]]}], issues=_iss)
check("認不出來的維度值有被記錄", len(_iss), 1)
check("記錄裡留著模型原本寫了什麼",
      _iss[0]["wrote"], "engagement|responsiveness")

# 端到端：模型全部用大寫開頭回答，四個維度都必須活下來。
_prov = [{S.THEME_NAME: f"p{i}", S.THEME_DEFINITION: "d",
          S.MEMBER_IDS: [items[i][T.GLOBAL_ID]]} for i in range(4)]
_resp = json.dumps({"themes": [
    {"name": "A", "definition": "d", "aggregate_dimension": "Anticipation",
     "merged_from": ["1"]},
    {"name": "B", "definition": "d", "aggregate_dimension": "Reflexivity",
     "merged_from": ["2"]},
    {"name": "C", "definition": "d", "aggregate_dimension": "Engagement",
     "merged_from": ["3"]},
    {"name": "D", "definition": "d", "aggregate_dimension": "Responsiveness",
     "merged_from": ["4"]}]})
_th, _ = T.parse_stage2(_resp, _prov)
check("四個維度全部保留（不是三個）",
      sorted({t[S.AGG_DIMENSION] for t in _th}),
      sorted([S.ANTICIPATION, S.REFLEXIVITY, S.ENGAGEMENT, S.RESPONSIVENESS]))
check_true("沒有任何一個被誤判為未歸屬",
           all(t[S.AGG_DIMENSION] != S.UNASSIGNED for t in _th))
_cov = T.coverage_report(_th, items)
check_true("覆蓋報告裡四個維度都非零",
           all(_cov["themes_by_dimension"][d] > 0
               for d in _F.active().dimensions),
           str(_cov["themes_by_dimension"]))
# 圖表的維度標籤由 app.py 注入 dim_label。長標籤會折行，但**只能折在空白處**。
#
# 要防的失效：_wrap 若是 text[i:i+per_line]、純按字元數硬切，匯出的圖會長成
# "Requires a plan f" / "or inconvenient f" / "indings (A05 (Cha"——每個換行都
# 切在字母中間。這一段要逐行驗：把所有 <text> 節點接回來再比對的話，
# "Public Engag" + "ement" 也算通過。逐行驗，硬切會當場失敗。
_svg = T.render_data_structure_svg(_th, items, dim_label=lambda d: I.dim(d))
_lines = [(e.text or "").strip() for e in ET.fromstring(_svg).iter()
          if e.tag.endswith("text")]
_lines = [x for x in _lines if x]
_joined = "".join(_lines)
for _d in ["Anticipation", "Reflexivity", "Responsiveness"]:
    check_true(f"Gioia 圖表畫得出「{_d}」欄", _d in _joined)
# 這一個標籤有空白，折行時必須折在空白處，兩個字都要完整出現在某一行裡
check_true("「Public Engagement」折在空白處，不是切在字母中間",
           any(x == "Public" for x in _lines) and
           any(x == "Engagement" for x in _lines),
           str([x for x in _lines if "Enga" in x or "Publi" in x]))
check("圖表畫出四個聚合維度框（不是三個）",
      _svg.count('fill-opacity="0.08"'), 4)

# 逐行掃描整張圖：任何一行的結尾若把一個西文單字切成兩半，就是硬切。
# 判準是「這一行結尾是字母，且下一行開頭也是字母，而兩者原本相連」——
# 直接檢查每一行是不是完整的字詞序列比較單純。
_bad = [x for x in _lines
        if _re.search(r"[A-Za-z]$", x) and len(x) > 3 and
        not _re.search(r"(^|\s)[A-Za-z][A-Za-z'’\-\.]*$", x)]
check_true("整張圖沒有任何一行把單字切開", not _bad, str(_bad[:4]))

# 印刷字級。這張圖宣稱可以直接放進論文，放成 6.27 吋寬時任何字都不能小於
# 7 pt。最小的字若是 9 單位，印出來只有 4.2 pt——而螢幕上看起來完全正常，
# 不量就不會知道。
_sizes = [float(x) for x in _re.findall(r'font-size="([\d.]+)"', _svg)]
_min_pt = min(_sizes) * T.SVG_PT_PER_UNIT
check_true("資料結構圖最小字級放成單欄全寬時 ≥ 7 pt", _min_pt >= 7.0,
           f"最小 {min(_sizes)} 單位 = {_min_pt:.2f} pt")
check_true("畫布寬度仍是字級規則假設的 960",
           ET.fromstring(_svg).get("width") == str(T.SVG_WIDTH) == "960")

# _wrap 本身的直接驗證，含中英混排與超長無空白字串
_w = T._wrap("Requires a plan for inconvenient findings (A05 (Chair))", 17)
check_true("英文只折在空白處",
           all(" " not in ln or ln == ln.strip() for ln in _w) and
           all(not ln.startswith(" ") for ln in _w), str(_w))
check_true("每一行都在寬度內", all(T._display_width(ln) <= 17 for ln in _w), str(_w))
check_true("折回去等於原文（只差空白）",
           "".join(_w).replace(" ", "") ==
           "Requires a plan for inconvenient findings (A05 (Chair))".replace(" ", ""),
           str(_w))
# 中文沒有空白，每個字都是合法斷點；且 CJK 一個字算兩格寬
_wz = T._wrap("受訪者談到監理沙盒與資料治理的邊界問題", 12)
check_true("中文每行不超過寬度（CJK 算兩格）",
           all(T._display_width(ln) <= 12 for ln in _wz), str(_wz))
check_true("中文折行不掉字",
           "".join(_wz) == "受訪者談到監理沙盒與資料治理的邊界問題", str(_wz))
# 真的塞不下的單一長詞才可以硬切（網址是合理的例外）
_wu = T._wrap("https://doi.org/10.1016/j.softx.2026.102702", 17)
check_true("超長無空白字串仍會被切開（合理例外）", len(_wu) > 1, str(_wu))
check_true("硬切也不掉字",
           "".join(_wu) == "https://doi.org/10.1016/j.softx.2026.102702", str(_wu))
check_true("空字串不炸掉", T._wrap("", 12) == [""])

print()
print("=" * 70)
print("測試 N+1：第二階段提示詞必須跟著作用中的框架走")
print("=" * 70)
# 要防的失效：這段提示詞若寫死四個負責任創新維度，換成別的框架之後，
# 提示詞照樣叫模型挑 anticipation/reflexivity/...，模型也照做，
# 然後每個回傳值都不屬於新框架，全部被判成 unassigned——
# Gioia 圖表變成一個大虛線框，而且沒有任何錯誤訊息。
_prompt_ri = T.build_stage2_prompt(_prov, "en", "sample")
for _d in _F.active().dimensions:
    check_true(f"RI 框架下提示詞列出 {_d}", f"- {_d}" in _prompt_ri)

import os as _os
import tempfile as _tf
with _tf.TemporaryDirectory() as _d:
    _real = _F.FRAMEWORK_DIR
    _F.FRAMEWORK_DIR = _d
    _F.ensure_builtin_on_disk()
    _alt = _F.blank("theme_prompt_probe", "Probe Framework",
                    [("alpha", "ALP", "Alpha", "甲"), ("beta", "BET", "Beta", "乙")],
                    has_polarity=False)
    _F.save(_alt, _os.path.join(_d, "theme_prompt_probe.json"))
    try:
        _F.activate_by_id("theme_prompt_probe")
        _p2 = T.build_stage2_prompt(_prov, "en", "sample")
        check_true("換框架後提示詞列出新框架的維度",
                   "- alpha" in _p2 and "- beta" in _p2)
        check_true("換框架後提示詞不再出現 RI 的維度",
                   "anticipation" not in _p2 and "reflexivity" not in _p2
                   and "responsiveness" not in _p2,
                   "提示詞若還在講別的框架，模型會照著答，然後全部落到未歸屬")
        check_true("輸出格式的列舉也跟著換",
                   '"alpha|beta|unassigned"' in _p2)
        # 模型照著新提示詞作答，維度必須留得住
        _r2 = json.dumps({"themes": [
            {"name": "X", "definition": "d", "aggregate_dimension": "Alpha",
             "merged_from": ["1"]},
            {"name": "Y", "definition": "d", "aggregate_dimension": "beta",
             "merged_from": ["2"]}]})
        _t2, _ = T.parse_stage2(_r2, _prov)
        check("換框架後維度不會全部掉進未歸屬",
              sorted(t[S.AGG_DIMENSION] for t in _t2), ["alpha", "beta"])
    finally:
        _F.FRAMEWORK_DIR = _real
        _F.reset()

print()
print("=" * 70)
print("測試 12：輸出約定探測（送出前幾秒鐘就抓得到的失效）")
print("=" * 70)
# 要防的失效：一次真實執行跑出 9 個主題，7 個掉進未歸屬，四個維度掛零三個
# ——而模型自己寫的歸屬理由明明指名了 anticipation 與 responsiveness。
# 它不是判斷得不好，是把複合值寫進了只能填一個識別碼的欄位。
# 探測要在送出前抓到這件事，而且要說得出模型實際寫了什麼。
import tacit_framework as _FW                                  # noqa: E402
_FW.activate_by_id("ri_stilgoe_2013")
_DIMS = _FW.active().dimensions


def _ids_from(prompt):
    return [l.split(" | ")[0]
            for l in prompt.split("=== ITEMS ===")[1].strip().split("\n")]


def _answer_with(value_for):
    def _fn(prompt):
        ids = _ids_from(prompt)
        return json.dumps({"answers": [{"id": i, "dimension": value_for(k)}
                                       for k, i in enumerate(ids)]})
    return _fn


_c, _d = T.probe_output_contract(_answer_with(lambda k: _DIMS[k % 4]), _DIMS)
check("完全照做 → 遵循度 1.0", round(_c, 2), 1.0)
check("完全照做 → verdict ok", T.contract_verdict(_c, _d), "ok")
check_true("完全照做 → 沒有不合格項", not _d["non_conforming"], str(_d["non_conforming"]))

# 大小寫不同算合格：norm_dimension 本來就容錯，這裡不該重複懲罰
_c, _d = T.probe_output_contract(_answer_with(lambda k: _DIMS[k % 4].upper()), _DIMS)
check("全大寫仍算合格", round(_c, 2), 1.0)

# **這一條是整段的重點**：複合值代表模型沒有做出選擇，必須算不合格
_c, _d = T.probe_output_contract(
    _answer_with(lambda k: "engagement|responsiveness"), _DIMS)
check("複合值 → 遵循度 0", round(_c, 2), 0.0)
check("複合值 → verdict unusable", T.contract_verdict(_c, _d), "unusable")
check_true("複合值 → 記下模型實際寫了什麼",
           any(x["wrote"] == "engagement|responsiveness"
               for x in _d["non_conforming"]), str(_d["non_conforming"][:2]))

_c, _d = T.probe_output_contract(
    _answer_with(lambda k: _DIMS[k % 4] if k < 4 else "anticipation, reflexivity"),
    _DIMS)
check_true("一半複合值 → 落在中間帶", 0.5 < _c < 0.8, f"{_c:.2f}")
check("一半複合值 → verdict shaky", T.contract_verdict(_c, _d), "shaky")

# 連 JSON 都不給，是最嚴重的一種
_c, _d = T.probe_output_contract(lambda p: "Sure! P1 is about anticipation…", _DIMS)
check("回散文 → 遵循度 0", round(_c, 2), 0.0)
check_true("回散文 → 標記為沒有合法 JSON", not _d["valid_json"])
check_true("回散文 → 仍記下模型寫了什麼",
           bool(_d["non_conforming"]), str(_d["non_conforming"][:1]))


def _boom(prompt):
    raise RuntimeError("connection refused")


_c, _d = T.probe_output_contract(_boom, _DIMS)
check("連線失敗 → 遵循度 0", round(_c, 2), 0.0)
check_true("連線失敗 → 錯誤訊息留著", "connection refused" in _d["error"], _d["error"])
check_true("連線失敗不會拋出去（探測不該讓介面崩掉）", True)

# unassigned 是合法答案：模型說「都不適用」是一種正當的判斷，不是不合格
_c, _d = T.probe_output_contract(_answer_with(lambda k: S.UNASSIGNED), _DIMS)
check("全部回未歸屬仍算遵循格式", round(_c, 2), 1.0)

# 探測必須跟著作用中的框架走，不能寫死 RI 的四個維度
_FW.activate_by_id("utaut_venkatesh_2003")
_UD = _FW.active().dimensions
_c_ri, _ = T.probe_output_contract(_answer_with(lambda k: _DIMS[k % 4]), _UD)
_c_ut, _ = T.probe_output_contract(_answer_with(lambda k: _UD[k % len(_UD)]), _UD)
check("用 UTAUT 探測時，RI 的維度值算不合格", round(_c_ri, 2), 0.0)
check("用 UTAUT 探測時，UTAUT 的維度值算合格", round(_c_ut, 2), 1.0)
_FW.activate_by_id("ri_stilgoe_2013")

# 門檻的行為
check("0.9 以上算 ok", T.contract_verdict(0.95, {"valid_json": True}), "ok")
check("0.6–0.9 算 shaky", T.contract_verdict(0.7, {"valid_json": True}), "shaky")
check("0.6 以下算 unusable", T.contract_verdict(0.3, {"valid_json": True}), "unusable")

print()
print("=" * 70)
print("測試 N：不用模型的主題收斂——依相似度把碼分群")
print("=" * 70)
# 主題歸納是這套工具最依賴模型的一步，但把一階概念收成群不必然要模型。
# 這一段守三件事：分群是確定性的、距離誠實反映根據有多薄、名字不會被
# 自動生出來（二階主題的名字就是詮釋本身，工具不該代筆）。
import tacit_analysis as _A                                      # noqa: E402

_counts, _jac, _totals = _A.cooccurrence(RECORDS)
_codes = [c for c in S.CODES if _totals[c] > 0]
_d = T.cooccurrence_distances(_counts, _totals, _codes)
check_true("距離對稱", all(_d[(a, b)] == _d[(b, a)]
                        for a, b in zip(_codes, _codes[1:])))
check_true("距離落在 0 到 1 之間", all(0.0 <= v <= 1.0 for v in _d.values()))

_g1 = T.cluster_codes(_d, _codes, k=3, weights=_totals)
check("要三群就給三群", len(_g1), 3)
check("每個碼都只出現在一群裡",
      sorted(c for g in _g1 for c in g[T.CLUSTER_MEMBER_CODES]), sorted(_codes))
check_true("同樣的輸入給同樣的輸出（分群是確定性的）",
           [g[T.CLUSTER_MEMBER_CODES] for g in _g1] ==
           [g[T.CLUSTER_MEMBER_CODES]
            for g in T.cluster_codes(_d, _codes, k=3, weights=_totals)])
check_true("每一群都帶著合併距離",
           all(T.CLUSTER_DISTANCE in g for g in _g1))
check_true("硬湊出來的群距離接近 1（看得出根據很薄）",
           max(g[T.CLUSTER_DISTANCE] for g in _g1) > 0.5,
           str([g[T.CLUSTER_DISTANCE] for g in _g1]))
check("碼數少於兩個時原樣回傳",
      len(T.cluster_codes(_d, _codes[:1])), 1)

# 開放編碼的碼簿幾乎不共現（一段話通常只有一個碼），那種碼簿要用標籤相似度
_texts = {"a": "Impact of AI on job loss", "b": "Job loss due to AI",
          "c": "Importance of transparency", "d": "Transparency",
          "e": "Semiconductor export controls"}
_dl = T.label_distances(_texts)
check_true("意思相近的標籤距離較近",
           _dl[("c", "d")] < _dl[("c", "e")],
           f"{_dl[('c', 'd')]:.3f} vs {_dl[('c', 'e')]:.3f}")
check_true("完全不相干的標籤距離很遠（但不會剛好是 1——短標籤總會共用幾個二元組）",
           _dl[("a", "e")] > 0.8, f"{_dl[('a', 'e')]:.3f}")
_g2 = T.cluster_codes(_dl, list(_texts), k=3)
_pair = [g for g in _g2 if "c" in g[T.CLUSTER_MEMBER_CODES]][0]
check_true("兩個談透明的碼被放在一起",
           "d" in _pair[T.CLUSTER_MEMBER_CODES],
           str([g[T.CLUSTER_MEMBER_CODES] for g in _g2]))

_items = T.collect_first_order(RECORDS)
_th = T.themes_from_clusters(_g1, _items, names={1: "把參與當成事後告知"})
check_true("產出的主題結構跟模型那條路一樣",
           all(set(t) == set(T.parse_stage2('{"themes":[{"name":"x","merged_from":[]}]}',
                                            [])[0][0]) for t in _th),
           str(sorted(_th[0])))
check_true("主題的成員是一階概念的全域 ID",
           all(i.startswith("G") for t in _th for i in t[S.MEMBER_IDS]))
check("沒給名字的主題名字留空（不自動生成）",
      sum(1 for t in _th if not t[S.THEME_NAME]), len(_th) - 1)
check_true("主題 ID 連號", [t[S.THEME_ID] for t in _th] ==
           [f"T{i:02d}" for i in range(1, len(_th) + 1)])
check_true("這些主題吃得進既有的主題表", len(T.theme_table(_th, _items)) == len(_th))
check_true("這些主題畫得出 Gioia 圖",
           T.render_data_structure_svg(_th, _items).startswith("<svg"))

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
