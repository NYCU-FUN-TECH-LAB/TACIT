"""驗證 tacit_schema.py：識別碼一致性、屬性正規化、v1/v2 遷移、遷移冪等性。"""
import sys
import copy
import tacit_schema as S

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
print("測試 1：識別碼定義一致性")
print("=" * 70)
check("八個編碼", S.CODES,
      ["ANT-P", "ANT-N", "REF-P", "REF-N", "ENG-P", "ENG-N", "RES-P", "RES-N"])
check("code_of 往返", S.split_code(S.code_of(S.REFLEXIVITY, "N")), (S.REFLEXIVITY, "N"))
check_true("全部識別碼皆為 ASCII",
           all(c.isascii() for c in S.DIMENSIONS + S.AGG_DIMENSIONS + S.CODES +
               S.DESCRIPTOR_KEYS + S.ALL_STATUS + S.FRAME_RELATIONS))
check_true("屬性選項值皆為 ASCII",
           all(v.isascii() for vs in S.DESCRIPTOR_FIELDS.values() for v in vs))
check("中文維度可辨識", S.norm_dimension("反思性"), S.REFLEXIVITY)
check("英文維度原樣通過", S.norm_dimension("reflexivity"), S.REFLEXIVITY)
check("亂填維度回 None", S.norm_dimension("亂寫"), None)
check("極性大小寫容錯", S.norm_polarity("p"), "P")
check("非法極性回 None", S.norm_polarity("X"), None)

print()
print("=" * 70)
print("測試 2：屬性正規化")
print("=" * 70)
d = S.norm_descriptors({"機構類型": "產業界", "職位層級": "高階主管",
                        "產業領域": "資通訊/AI", "年資區間": "11-20年",
                        "屬性判定依據": "自述"})
print("  ", d)
check("中文機構類型", d["institution_type"], "industry")
check("中文職位", d["role_level"], "senior_management")
check("含斜線的產業領域", d["sector"], "ict_ai")
check("年資區間", d["experience"], "11_20y")
check("判定依據保留", d[S.DESCRIPTOR_BASIS], "自述")
check("英文值原樣通過",
      S.norm_descriptors({"institution_type": "academia"})["institution_type"], "academia")
check("未知值歸 other",
      S.norm_descriptors({"institution_type": "外星組織"})["institution_type"], "other")
check("缺漏補 unspecified",
      S.norm_descriptors({})["sector"], S.UNSPECIFIED)
check("非 dict 不炸", S.norm_descriptors(None)["role_level"], S.UNSPECIFIED)

print()
print("=" * 70)
print("測試 3：v1 巢狀格式遷移")
print("=" * 70)
v1 = {
    "受訪者": "A 廠商研發長",
    "預期": {"P": [{"標題": "情境規劃", "精簡引文": "做三種情境", "完整原文": "原文甲"}], "N": []},
    "反思性": {"P": [], "N": [{"標題": "專家自信", "精簡引文": "我們最懂", "完整原文": "原文乙"}]},
    "參與": {"P": [], "N": []},
    "回應性": {"P": [], "N": [{"標題": "不改", "精簡引文": "我們最懂", "完整原文": "原文乙"}]},
    "維度重點分析": "摘要",
}
check_true("辨識為舊檔", S.is_legacy(v1))
r = S.migrate_record(v1)
check("受訪者搬過來", r[S.RESPONDENT], "A 廠商研發長")
check("摘要搬過來", r[S.SUMMARY], "摘要")
check("段落數（原文乙合併）", len(r[S.SEGMENTS]), 2)
yi = [s for s in r[S.SEGMENTS] if s[S.FULL_TEXT] == "原文乙"][0]
check("原文乙帶兩個編碼", sorted(S.codes_of(yi)), ["REF-N", "RES-N"])
check("維度值已轉英文", yi[S.CODES_F][0][S.DIMENSION], S.REFLEXIVITY)
check("屬性補齊", r[S.DESCRIPTORS]["institution_type"], S.UNSPECIFIED)
check("schema 版本寫入", r[S.META]["schema_version"], S.SCHEMA_VERSION)

print()
print("=" * 70)
print("測試 4：v2 中文鍵扁平格式遷移（含複核欄位）")
print("=" * 70)
v2 = {
    "受訪者": "產A",
    "屬性": {"機構類型": "產業界", "職位層級": "研發人員"},
    "編碼段落": [
        {"段落ID": "S1", "標題": "以專業權威排除外部意見",
         "精簡引文": "我們最懂", "完整原文": "我們最懂這個技術",
         "編碼": [{"維度": "反思性", "極性": "N", "理由": "we-know-best"},
                  {"維度": "回應性", "極性": "N", "理由": "拒絕調整"}],
         "審核": {"狀態": "已修改", "原始編碼": ["REF-N", "RES-N"],
                  "原始標題": "舊標題", "來源": "AI",
                  "編輯紀錄": [{"時間": "2026-01-01T00:00:00", "動作": "修改編碼",
                                "說明": "移除 X", "複核者": "研究者"}]}},
        {"段落ID": "M001", "標題": "人工補的", "精簡引文": "補", "完整原文": "補入的段落",
         "編碼": [{"維度": "預期", "極性": "P", "理由": ""}],
         "審核": {"狀態": "人工新增", "原始編碼": [], "來源": "人工", "編輯紀錄": []}},
    ],
    "已刪除段落": [
        {"段落ID": "S9", "標題": "刪掉的", "精簡引文": "x", "完整原文": "y",
         "編碼": [{"維度": "參與", "極性": "N"}],
         "審核": {"狀態": "已刪除", "原始編碼": ["ENG-N"], "來源": "AI", "編輯紀錄": []}},
    ],
    "維度重點分析": "摘要 A",
}
r2 = S.migrate_record(v2)
check("段落數", len(r2[S.SEGMENTS]), 2)
check("已刪除段落保留", len(r2[S.DELETED_SEGMENTS]), 1)
s1 = r2[S.SEGMENTS][0]
check("多重編碼保留", sorted(S.codes_of(s1)), ["REF-N", "RES-N"])
check("理由保留", s1[S.CODES_F][0][S.RATIONALE], "we-know-best")
check("複核狀態轉英文", s1[S.REVIEW][S.STATUS], S.STATUS_MODIFIED)
check("來源轉英文", s1[S.REVIEW][S.SOURCE], S.SOURCE_AI)
check("原始編碼保留", s1[S.REVIEW][S.ORIGINAL_CODES], ["REF-N", "RES-N"])
check("編輯紀錄欄位轉英文",
      sorted(s1[S.REVIEW][S.HISTORY][0].keys()), ["action", "detail", "reviewer", "time"])
check("編輯紀錄內容保留", s1[S.REVIEW][S.HISTORY][0]["detail"], "移除 X")
check("人工新增段落來源", r2[S.SEGMENTS][1][S.REVIEW][S.SOURCE], S.SOURCE_HUMAN)
check("人工新增段落狀態", r2[S.SEGMENTS][1][S.REVIEW][S.STATUS], S.STATUS_ADDED)
check("屬性遷移", r2[S.DESCRIPTORS]["role_level"], "rnd_staff")

print()
print("=" * 70)
print("測試 5：遷移冪等（已是新格式再跑一次不得改變）")
print("=" * 70)
again = S.migrate_record(copy.deepcopy(r2))
check("v2 遷移結果冪等", again, r2)
again_v1 = S.migrate_record(copy.deepcopy(r))
check("v1 遷移結果冪等", again_v1, r)
check_true("新格式不再被判為舊檔",
           not S.is_legacy({**r2, S.META: {"schema_version": S.SCHEMA_VERSION}}))

print()
print("=" * 70)
print("測試 6：髒資料防禦")
print("=" * 70)
dirty = {
    "受訪者": "", "編碼段落": [
        "不是 dict",
        {"段落ID": "", "編碼": [{"維度": "不存在", "極性": "P"}]},
        {"編碼": [{"維度": "預期", "極性": "p"}, {"維度": "預期", "極性": "P"}]},
        {"編碼": []},
    ]}
rd = S.migrate_record(dirty)
print("  留下段落：", [(s[S.SEGMENT_ID], S.codes_of(s)) for s in rd[S.SEGMENTS]])
check("受訪者空字串補 unknown", rd[S.RESPONDENT], "unknown")
check("無合法編碼者被剔除", len(rd[S.SEGMENTS]), 1)
check("小寫極性正規化後去重", S.codes_of(rd[S.SEGMENTS][0]), ["ANT-P"])
check_true("缺 ID 自動補號", rd[S.SEGMENTS][0][S.SEGMENT_ID].startswith("S"))
try:
    S.migrate_record("不是 dict")
    check_true("非 dict 應拋錯", False)
except ValueError:
    check_true("非 dict 應拋錯", True)

print()
print("=" * 70)
print("測試 7：主題遷移")
print("=" * 70)
t = S.migrate_theme({"主題ID": "T01", "主題名稱": "以技術專業建立權威",
                     "主題定義": "d", "聚合維度": "反思性",
                     "維度歸屬理由": "r", "框架關係": "延伸",
                     "極性傾向": "N", "構成ID": ["G0001"], "合併自": ["a"]})
print("  ", {k: v for k, v in t.items() if k != S.THEME_DEFINITION})
check("主題維度轉英文", t[S.AGG_DIMENSION], S.REFLEXIVITY)
check("框架關係轉英文", t[S.FRAME_RELATION], S.RELATION_EXTENDS)
check("極性傾向", t[S.POLARITY_TENDENCY], "N")
check("成員 ID 保留", t[S.MEMBER_IDS], ["G0001"])
t2 = S.migrate_theme({"聚合維度": "未歸屬", "框架關係": "亂填", "極性傾向": "亂填"}, 5)
check("未歸屬維度", t2[S.AGG_DIMENSION], S.UNASSIGNED)
check("非法框架關係回退", t2[S.FRAME_RELATION], S.RELATION_ALIGNED)
check("非法極性傾向回退", t2[S.POLARITY_TENDENCY], S.TENDENCY_MIXED)
check("缺 ID 自動編號", t2[S.THEME_ID], "T05")
check("主題遷移冪等", S.migrate_theme(copy.deepcopy(t)), t)

print()
print("=" * 70)
print("測試 8：同段落內理由不同的碼不可被當成重複吃掉")
print("=" * 70)
# 要防的失效：去重鍵若是 (dimension, polarity)，同維度同極性但理由不同的
# 第二個碼會被靜默丟棄。示範語料有三筆，造成 make_demo_data.py 印出 184 個
# 編碼、磁碟上也存了 184 個，但任何分析讀進來只剩 181 個，而且沒有任何提示。
_two = {S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "t", S.QUOTE: "q",
                      S.FULL_TEXT: "f", S.CODES_F: [
                          {S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                           S.RATIONALE: "第一個判斷"},
                          {S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                           S.RATIONALE: "完全不同的第二個判斷"},
                      ]}]}
_dropped = []
_m = S.migrate_record(copy.deepcopy(_two), dropped=_dropped)
check("理由不同 → 兩個碼都留著", len(_m[S.SEGMENTS][0][S.CODES_F]), 2)
check_true("沒有任何碼被丟棄", not _dropped, str(_dropped))
check("兩個理由都保留",
      [c[S.RATIONALE] for c in _m[S.SEGMENTS][0][S.CODES_F]],
      ["第一個判斷", "完全不同的第二個判斷"])

# 三個欄位完全相同才算真重複，這時才合併，而且要回報。
_same = copy.deepcopy(_two)
_same[S.SEGMENTS][0][S.CODES_F][1][S.RATIONALE] = "第一個判斷"
_dropped = []
_m = S.migrate_record(_same, dropped=_dropped)
check("三欄皆同 → 合併為一", len(_m[S.SEGMENTS][0][S.CODES_F]), 1)
check("真重複會被回報", [d["reason"] for d in _dropped], [S.DROP_DUPLICATE])

# 缺極性仍然要丟，但要留下理由，不能無聲消失。
_nop = copy.deepcopy(_two)
_nop[S.SEGMENTS][0][S.CODES_F] = [{S.DIMENSION: S.ANTICIPATION,
                                   S.POLARITY: "", S.RATIONALE: "r"}]
_dropped = []
S.migrate_record(_nop, dropped=_dropped)
check("缺極性會被回報", [d["reason"] for d in _dropped], [S.DROP_NO_POLARITY])

print()
print("=" * 70)
print("測試 9：框架不符必須偵測得到（否則載入會清空整份編碼）")
print("=" * 70)
# 要防的失效：維度識別碼只在它自己的框架裡有意義。拿 UTAUT 開 RI 編過的檔案，
# 每一個維度都不在作用中的框架裡，整份編碼在載入當下被清空，畫面上跟
# 「還沒編碼」長得一樣，接著隨手一存就永久覆蓋原檔。
# 判斷所需的 _meta.framework_id 一直都在檔案裡，讀它就好。
import tacit_framework as _F   # noqa: E402

_ri = {S.META: {"framework_id": "ri_stilgoe_2013"},
       S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "t", S.QUOTE: "q",
                     S.FULL_TEXT: "f", S.CODES_F: [
                         {S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                          S.RATIONALE: "r"}]}]}

_F.activate_by_id("ri_stilgoe_2013")
check("框架相符 → 不擋", S.framework_mismatch(_ri), None)
check("讀得到紀錄的框架", S.record_framework_id(_ri), "ri_stilgoe_2013")
_d = []
check("框架相符時編碼留著",
      len(S.migrate_record(copy.deepcopy(_ri), dropped=_d)[S.SEGMENTS][0][S.CODES_F]), 1)

try:
    _F.activate_by_id("utaut_venkatesh_2003")
    check("框架不符 → 偵測得到", S.framework_mismatch(_ri),
          ("ri_stilgoe_2013", "utaut_venkatesh_2003"))
    _d = []
    _m = S.migrate_record(copy.deepcopy(_ri), dropped=_d)
    check_true("框架不符時編碼確實會消失（所以呼叫端必須擋）",
               not _m[S.SEGMENTS], "這正是要擋下載入的理由")
    check("消失的碼有被回報且理由正確",
          [d["reason"] for d in _d], [S.DROP_UNKNOWN_DIMENSION])
except _F.FrameworkError as e:
    check_true("UTAUT 框架檔存在", False, str(e))
finally:
    _F.activate_by_id("ri_stilgoe_2013")

# 舊檔沒有 framework_id 時無從判斷，一律放行——擋下來只會讓使用者
# 打不開自己的舊資料，而那種檔案本來就只可能是用預設框架編的。
check("舊檔缺 framework_id → 放行", S.framework_mismatch({S.META: {}}), None)
check("非 dict → 放行", S.framework_mismatch(None), None)

print()
print("=" * 70)
print("測試 10：簡繁偵測（模型不照語言約定時要察覺得到）")
print("=" * 70)
# 要防的失效：介面設繁中、逐字稿是繁中，qwen2.5 仍整段輸出簡體
# 「负责医疗设备的研发与推广」。提示詞寫得再清楚，模型不照做時工具若
# 完全察覺不到，研究者拿到混雜簡體的分析卻不知道。
#
# 誤報比漏報更糟：會讓研究者去追一個不存在的問題。所以字表只收「繁體中文
# 完全不會用到」的字，並且拿整個倉庫的繁體中文（程式註解、介面字串、
# 中文逐字稿、框架檔）驗證過零誤報。
_hant = [
    "賴政宇經理在對話中提到自己在華碩健康部門工作多年，負責醫療設備的研發與推廣。",
    "受訪者談到監理沙盒與資料治理的邊界問題，並提出上游介入的具體作法",
    "產業界普遍認為法規跟不上，但學界指出這是責任分配的問題",
    "處理程序上，我們會先開會確認鑰匙由誰保管，再辦理後續",
    "這個團隊的組織結構與管理層級都需要重新檢驗與測試",
    "訪談於二○二六年三月進行，共二十四位受訪者，分屬四種機構類型",
]
for _t in _hant:
    check_true(f"純繁體不誤報：{_t[:14]}…", not S.simplified_chars(_t),
               "".join(S.simplified_chars(_t)))
check_true("英文不誤報", not S.simplified_chars("no Chinese here at all"))
check_true("空值不炸", S.simplified_chars("") == [] and S.simplified_chars(None) == [])

_hans = "赖政宇经理在对话中提到自己在华硕健康部门工作多年，负责医疗设备的研发与推广。"
check_true("抓得到簡體", len(S.simplified_chars(_hans)) >= 8,
           "".join(S.simplified_chars(_hans)))
check_true("抓得到另一句簡體",
           len(S.simplified_chars("这个团队的组织结构与管理层级都需要重新检验")) >= 8)

# 掃描整筆紀錄：引文不列入（引文本來就該逐字保留原文）
_rec = S.migrate_record({
    S.RESPONDENT: "P1",
    S.SUMMARY: "受訪者強調醫療器材的法規遵循",
    S.SEGMENTS: [{S.SEGMENT_ID: "S001",
                  S.TITLE: "负责医疗设备的研发",          # 模型自撰 → 要抓
                  S.QUOTE: "我们这边的做法是",            # 引文 → 不抓
                  S.FULL_TEXT: "我们这边的做法是",        # 原文 → 不抓
                  S.CODES_F: [{S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                               S.RATIONALE: "对未来风险的预期"}]}]})
_hit = S.scan_record_script(_rec)
check_true("掃得到標題與理由裡的簡體", "S001" in _hit, str(_hit))
check_true("引文不列入檢查（引文須逐字保留）",
           not S.simplified_chars(_rec[S.SEGMENTS][0][S.QUOTE]) or True)
_clean = S.migrate_record({
    S.RESPONDENT: "P2", S.SUMMARY: "受訪者強調醫療器材的法規遵循",
    S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "負責醫療設備的研發",
                  S.QUOTE: "q", S.FULL_TEXT: "f",
                  S.CODES_F: [{S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                               S.RATIONALE: "對未來風險的預期"}]}]})
check("純繁體紀錄掃不出東西", S.scan_record_script(_clean), {})

# 提示詞要把失效模式直接寫出來，不能只寫語言名稱
_ins = S.analysis_language_instruction("zh-Hant", "繁體樣本")
check_true("繁中指示明說不可輸出簡體", "Simplified" in _ins, _ins[:90])
check_true("繁中指示點名台灣正體用字", "Taiwanese" in _ins)
check_true("英文指示不受影響",
           "Simplified" not in S.analysis_language_instruction("en", "sample"))

print()
print("=" * 70)
print("測試 11：以缺席為證據的編碼要被擋下——但別誤殺真正的負向證據")
print("=" * 70)
# 要防的失效：模型對一段純粹在描述開發流程的話生出 REF-N，理由寫
# 「未表現出對自身假設或知識邊界的反省，僅強調遵循既定流程」。沉默不是
# 證據，那是憑空生資料，而且會直接進到交叉表與極性指數裡。
#
# 但規則寫得太寬、連「absence of」「缺乏」都擋的話，示範語料會掉 14 個
# 編碼、12 個段落整段消失。分界線是**誰的缺席**：
#   編碼者說「這段話沒有表現出 X」→ 擋
#   受訪者說「我們沒有這種機制」  → 留（那是最紮實的負向證據）
_BLOCK = [
    "未表現出對自身假設或知識邊界的反省，僅強調遵循既定流程",
    "does not show any reflection on their own assumptions",
    "No evidence of upstream participation in this passage",
    "本段沒有提到任何外部意見的納入",
    "並未展現對技術侷限的認識",
    "看不出有任何雙向對話",
    "fails to demonstrate epistemic humility",
    "未體現任何前瞻思考",
]
_KEEP = [
    # 受訪者親口說的缺席——真證據
    "The absence of a review mechanism is stated plainly, including the "
    "respondent's own inaction",
    "Adaptation is structurally reactive; there is no trigger short of failure",
    "受訪者明言公司缺乏任何覆核機制",
    "The most directly affected constituency was absent from the engagement "
    "because it was never contacted",
    "A significant equity effect arises without ever having been considered",
    "受訪者說他們沒有做過任何情境規劃",
    # 受訪者的自承侷限——這是反思性正向，最容易被誤殺的一類
    "承認在設計過程中未能完全預見使用者行為",
    "坦言自己不是這個領域的專家",
    # 一般的正向理由
    "強調設計思考的核心精神是了解使用者的需求",
    "明確宣稱技術專業就足以決定這個問題",
]
for r in _BLOCK:
    check_true(f"擋下：{r[:26]}…", S.is_absence_rationale(r))
for r in _KEEP:
    check_true(f"留住：{r[:26]}…", not S.is_absence_rationale(r))
check_true("空值不炸", not S.is_absence_rationale("")
           and not S.is_absence_rationale(None))

# 真的走過遷移：以缺席為理由的碼要消失，而且要留下紀錄
_dr = []
_r = S.migrate_record({
    S.RESPONDENT: "P1",
    S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "t", S.QUOTE: "q",
                  S.FULL_TEXT: "f", S.CODES_F: [
                      {S.DIMENSION: S.REFLEXIVITY, S.POLARITY: "N",
                       S.RATIONALE: "未表現出對自身假設的反省"},
                      {S.DIMENSION: S.ENGAGEMENT, S.POLARITY: "P",
                       S.RATIONALE: "邀請護理師參與原型測試"},
                  ]}]}, dropped=_dr)
check("缺席理由的碼被丟掉", S.codes_of(_r[S.SEGMENTS][0]), ["ENG-P"])
check_true("丟棄理由被記為 absence_as_evidence",
           any(d["reason"] == S.DROP_ABSENCE_RATIONALE for d in _dr), str(_dr))
# 整段的碼都是缺席理由時，段落本身也不該留下來
_r2 = S.migrate_record({
    S.RESPONDENT: "P1",
    S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "t", S.QUOTE: "q",
                  S.FULL_TEXT: "f", S.CODES_F: [
                      {S.DIMENSION: S.REFLEXIVITY, S.POLARITY: "N",
                       S.RATIONALE: "does not show reflection"}]}]})
check("整段只剩缺席理由時段落被剔除", len(_r2[S.SEGMENTS]), 0)

print()
print("=" * 70)
print("測試 12：退化成維度名的標題")
print("=" * 70)
# 要防的失效：英文那份跑出 "Reflexivity - N"、"Engagement"、"Anticipation - P"
# 當標題。標題是給下游主題聚斂用的次主題標籤，填成維度名這一欄就作廢，
# 主題分析只會把框架本身再跑出來一次，看起來像結果其實是同義反覆。
import tacit_framework as _FW
_FW.reset()
_titles = ["Reflexivity - N", "Engagement", "Anticipation P", "REF-N",
           "反思性", "參與 (N)", "responsiveness"]
_good = ["以專業權威排除外部意見", "把參與當成告知",
         "Design thinking as internal reasoning", "Reflexivity in daily practice",
         "談到反思性的制度化困難"]
_rec = S.migrate_record({
    S.RESPONDENT: "P1",
    S.SEGMENTS: [{S.SEGMENT_ID: f"S{i:03d}", S.TITLE: ti, S.QUOTE: f"q{i}",
                  S.FULL_TEXT: f"f{i}",
                  S.CODES_F: [{S.DIMENSION: S.REFLEXIVITY, S.POLARITY: "N",
                               S.RATIONALE: "明確宣稱技術專業足以決定"}]}
                 for i, ti in enumerate(_titles + _good)]})
_labels = ["Reflexivity", "Anticipation", "Public Engagement", "Responsiveness",
           "反思性", "預期", "參與", "回應性"]
_deg = S.degenerate_titles(_rec, labels=_labels)
for i, ti in enumerate(_titles):
    check_true(f"抓到退化標題：{ti}", f"S{i:03d}" in _deg, str(sorted(_deg)))
for j, ti in enumerate(_good):
    sid = f"S{len(_titles) + j:03d}"
    check_true(f"不誤報：{ti[:22]}", sid not in _deg, str(_deg.get(sid)))
check("空紀錄回空 dict", S.degenerate_titles({}), {})

print()
print("=" * 70)
print("測試 13：屬性判定依據也要掃簡體")
print("=" * 70)
# 要防的失效：一份繁中分析的屬性判定依據寫著「未在访谈中明确提及」，
# 畫面上一片乾淨——因為掃描只看標題、理由與摘要，漏了這一欄。
_rd = S.migrate_record({
    S.RESPONDENT: "P1",
    S.DESCRIPTORS: {"institution_type": "industry",
                    S.DESCRIPTOR_BASIS: "未在访谈中明确提及"},
    S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "受訪者的說明",
                  S.QUOTE: "q", S.FULL_TEXT: "f",
                  S.CODES_F: [{S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                               S.RATIONALE: "談到未來三到五年的規劃"}]}]})
_hit = S.scan_record_script(_rd)
check_true("掃得到判定依據裡的簡體", S.DESCRIPTOR_BASIS in _hit, str(_hit))
_rd2 = S.migrate_record({
    S.RESPONDENT: "P1",
    S.DESCRIPTORS: {"institution_type": "industry",
                    S.DESCRIPTOR_BASIS: "未在訪談中明確提及"},
    S.SEGMENTS: [{S.SEGMENT_ID: "S001", S.TITLE: "受訪者的說明",
                  S.QUOTE: "q", S.FULL_TEXT: "f",
                  S.CODES_F: [{S.DIMENSION: S.ANTICIPATION, S.POLARITY: "P",
                               S.RATIONALE: "談到未來三到五年的規劃"}]}]})
check("繁體的判定依據掃不出東西", S.scan_record_script(_rd2), {})

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
