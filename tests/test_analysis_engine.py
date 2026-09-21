"""
驗證 tacit_analysis.py：長表、交叉表、共現、跨案例矩陣、極性指數，全部手算比對。

（分析引擎是獨立於 app.py 的模組，所以這裡是正常 import，
  不必用 exec 把 Streamlit 檔案挖開。）
"""
import sys

import tacit_schema as S
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


def seg(sid, codes):
    return {S.SEGMENT_ID: sid, S.TITLE: sid, S.QUOTE: f"quote-{sid}",
            S.FULL_TEXT: f"text-{sid}",
            S.CODES_F: [S.make_code(d, p) for d, p in codes]}


def rec(name, desc, segs):
    return {S.RESPONDENT: name, S.DESCRIPTORS: S.norm_descriptors(desc),
            S.SUMMARY: "", S.SEGMENTS: segs}


RECORDS = [
    rec("產A", {"institution_type": "industry", "role_level": "senior_management",
                "sector": "ict_ai", "experience": "11_20y"},
        [seg("a1", [(S.REFLEXIVITY, "N"), (S.RESPONSIVENESS, "N")]),   # 多重
         seg("a2", [(S.ANTICIPATION, "N")]),
         seg("a3", [(S.ENGAGEMENT, "N")]),
         seg("a4", [(S.RESPONSIVENESS, "N")])]),
    rec("產B", {"institution_type": "industry", "role_level": "middle_management",
                "sector": "ict_ai", "experience": "6_10y"},
        [seg("b1", [(S.REFLEXIVITY, "N"), (S.RESPONSIVENESS, "N")]),   # 多重
         seg("b2", [(S.ANTICIPATION, "P")])]),
    rec("學C", {"institution_type": "academia", "role_level": "researcher",
                "sector": "ict_ai", "experience": "over_20y"},
        [seg("c1", [(S.ENGAGEMENT, "P")]),
         seg("c2", [(S.REFLEXIVITY, "P")]),
         seg("c3", [(S.ANTICIPATION, "P")]),
         seg("c4", [(S.RESPONSIVENESS, "P")])]),
    rec("學D", {"institution_type": "academia", "role_level": "researcher",
                "sector": "biomedical", "experience": "11_20y"},
        [seg("d1", [(S.ENGAGEMENT, "P"), (S.REFLEXIVITY, "P")]),        # 多重
         seg("d2", [(S.RESPONSIVENESS, "P")])]),
]

print("=" * 70)
print("測試 1：長表")
print("=" * 70)
long_df = A.build_long_df(RECORDS)
# 產A 5 碼(4段)、產B 3 碼(2段)、學C 4 碼(4段)、學D 3 碼(2段) = 15 碼、12 段
check("長表列數（＝總編碼數）", len(long_df), 15)
check("段落總數", sum(len(r[S.SEGMENTS]) for r in RECORDS), 12)
check("多重編碼列數（3 段 × 2 碼）",
      int(long_df[long_df[A.MULTI_CODED]][S.SEGMENT_ID].count()), 6)
check_true("欄位皆為 ASCII", all(str(c).isascii() for c in long_df.columns))
check_true("維度值為識別碼",
           set(long_df[S.DIMENSION]).issubset(set(S.DIMENSIONS)))
check_true("屬性欄位皆存在",
           all(k in long_df.columns for k in S.DESCRIPTOR_KEYS))

print()
print("=" * 70)
print("測試 2：維度 × 屬性交叉表")
print("=" * 70)
ct, pct = A.crosstab_by_descriptor(long_df, "institution_type")
print(ct.to_string())
# 產業界(A+B)=8 碼：ANT-P 1, ANT-N 1, REF-N 2, ENG-N 1, RES-N 3
check("產業界 REF-N", int(ct.loc["industry", "REF-N"]), 2)
check("產業界 RES-N", int(ct.loc["industry", "RES-N"]), 3)
check("產業界總碼數", int(ct.loc["industry"].sum()), 8)
# 學術界(C+D)=7 碼：ANT-P 1, REF-P 2, ENG-P 2, RES-P 2
check("學術界 ENG-P", int(ct.loc["academia", "ENG-P"]), 2)
check("學術界總碼數", int(ct.loc["academia"].sum()), 7)
check("學術界負向碼數應為 0",
      int(sum(ct.loc["academia", c] for c in ct.columns if c.endswith("-N"))), 0)
check("列百分比每列合計 100", [round(v) for v in pct.sum(axis=1)], [100, 100])
ct_dim, _ = A.crosstab_by_descriptor(long_df, "institution_type",
                                     row_unit=S.DIMENSION)
check_true("可切換為四維度單位",
           set(ct_dim.columns).issubset(set(S.DIMENSIONS)))

print()
print("  -- 卡方（預期會因期望次數不足而被擋下）--")
rep = A.chi_square_report(ct)
print("  ", {k: v for k, v in rep.items() if k != "p_raw"})
# scipy 是選配（C7 列為 recommended，requirements.txt 列在選配區），所以
# 這一段必須兩種安裝情形都成立。沒裝 scipy 時算不出卡方，但**該擋的行為
# 完全一樣**：不提供 p 值。這裡若寫死期待 CHI_SPARSE，只裝必要
# 套件的人跑 run_tests.py 會看到兩個套件失敗——而論文正是叫讀者跑它。
if A.HAS_SCIPY:
    check("判定為期望次數不足", rep["verdict"], A.CHI_SPARSE)
    check("前提不成立", rep["valid"], False)
    check_true("但保留原始 p 供除錯", rep["p_raw"] is not None)
    check_true("有 Cramér's V", rep["cramers_v"] > 0)
else:
    check("沒裝 scipy 時據實說明原因", rep["verdict"], A.CHI_UNAVAILABLE)
    check("並標示結果不可用", rep.get("available"), False)
    print("  （本次執行未安裝 scipy，卡方相關斷言改驗『一樣不給 p 值』）")
# 這一條兩種安裝情形都必須成立，而且是整段真正要保護的東西：
# 沒有前提就沒有 p 值，理由是「前提不成立」還是「算不出來」都一樣。
check_true("不論有沒有 scipy，都不提供 p 值", rep.get("p") is None,
           f"verdict={rep.get('verdict')}")

print()
print("=" * 70)
print("測試 3：共現")
print("=" * 70)
cnt, jac, tot = A.cooccurrence(RECORDS, level=A.LEVEL_SEGMENT)
# REF-N 與 RES-N 同段共現 2 次(a1,b1)；ENG-P 與 REF-P 共現 1 次(d1)
check("REF-N × RES-N 共現", int(cnt.loc["REF-N", "RES-N"]), 2)
check("ENG-P × REF-P 共現", int(cnt.loc["ENG-P", "REF-P"]), 1)
check("對角線為總次數", int(cnt.loc["REF-N", "REF-N"]), 2)
check("RES-N 總次數", int(tot["RES-N"]), 3)
check("矩陣對稱", bool((cnt.values == cnt.values.T).all()), True)
check("Jaccard(REF-N,RES-N) = 2/(2+3-2)", float(jac.loc["REF-N", "RES-N"]), 0.667)
check("無共現者為 0", int(cnt.loc["ANT-P", "ENG-N"]), 0)

pairs = A.cooccurrence_pairs(cnt, tot)
print(pairs.to_string(index=False))
check("共現配對數", len(pairs), 2)
check("最高共現配對",
      (pairs.iloc[0]["code_a"], pairs.iloc[0]["code_b"]), ("REF-N", "RES-N"))
check_true("標示跨維度", bool(pairs.iloc[0]["cross_dimension"]))
check_true("配對欄位為 ASCII", all(str(c).isascii() for c in pairs.columns))

cnt2, _, _ = A.cooccurrence(RECORDS, level=A.LEVEL_CASE)
check("case 層級 REF-N × RES-N", int(cnt2.loc["REF-N", "RES-N"]), 2)
check("case 層級 ENG-P × REF-P", int(cnt2.loc["ENG-P", "REF-P"]), 2)

print()
print("=" * 70)
print("測試 4：跨案例矩陣")
print("=" * 70)
m = A.case_matrix(long_df)
print(m.to_string())
check("產A 列合計", int(m.loc["產A"].sum()), 5)
check("學D ENG-P", int(m.loc["學D", "ENG-P"]), 1)
mp = A.case_matrix(long_df, normalize=True)
check("標準化後列合計 100", round(float(mp.loc["產A"].sum())), 100)

print()
print("=" * 70)
print("測試 5：極性平衡")
print("=" * 70)
per_dim, overall = A.polarity_balance(long_df)
o = overall.set_index(S.RESPONDENT)
print(overall.to_string(index=False))
# 產A: P0 N5 → −1 ; 學C: P4 N0 → +1 ; 產B: P1 N2 → (1−2)/3 = −0.333
check("產A 整體極性指數", float(o.loc["產A", "polarity_index"]), -1.0)
check("學C 整體極性指數", float(o.loc["學C", "polarity_index"]), 1.0)
check("產B 整體極性指數", float(o.loc["產B", "polarity_index"]), -0.333)
check("產A 編碼總數", int(o.loc["產A", "total_codes"]), 5)
pdx = per_dim.set_index([S.RESPONDENT, S.DIMENSION])
check("產A 回應性 N 數（a1+a4）",
      int(pdx.loc[("產A", S.RESPONSIVENESS), "N"]), 2)
check("產A 回應性極性指數",
      float(pdx.loc[("產A", S.RESPONSIVENESS), "polarity_index"]), -1.0)
check_true("維度欄為識別碼",
           set(per_dim[S.DIMENSION]).issubset(set(S.DIMENSIONS)))

print()
print("=" * 70)
print("測試 6：資料健檢")
print("=" * 70)
cov = {r[S.RESPONDENT]: r for r in A.coverage_report(RECORDS)}
print("  產A:", cov["產A"])
check("產A 段落數", cov["產A"]["segments"], 4)
check("產A 編碼數", cov["產A"]["codes"], 5)
check("產A 多重編碼段落", cov["產A"]["multi_coded_segments"], 1)
check("產A 多重編碼比例", cov["產A"]["multi_coded_rate"], 0.25)
check("產A 涵蓋維度數", cov["產A"]["dimensions_covered"], 4)
check("產A 屬性完整度", (cov["產A"]["descriptors_filled"],
                        cov["產A"]["descriptors_total"]), (4, 4))
check_true("健檢欄位為 ASCII", all(k.isascii() for k in cov["產A"]))

print()
print("=" * 70)
print("測試 7：邊界情況")
print("=" * 70)
empty = A.build_long_df([])
check("空資料長表為空", empty.empty, True)
check_true("空長表仍有欄位定義", len(empty.columns) > 5)
check("空長表 case_matrix", A.case_matrix(empty).empty, True)
check("空長表交叉表", A.crosstab_by_descriptor(empty, "sector")[0].empty, True)
check("空長表極性", A.polarity_balance(empty)[0].empty, True)
c0, j0, t0 = A.cooccurrence([], level=A.LEVEL_SEGMENT)
check("空資料共現全零", int(c0.values.sum()), 0)
check("空資料共現配對", len(A.cooccurrence_pairs(c0, t0)), 0)
check("空資料健檢", A.coverage_report([]), [])
_tiny = A.chi_square_report(A.crosstab_by_descriptor(
    A.build_long_df(RECORDS[:1]), "institution_type")[0])
check("2x2 以下不做卡方",
      _tiny["verdict"],
      A.CHI_TOO_SMALL if A.HAS_SCIPY else A.CHI_UNAVAILABLE)
check_true("2x2 以下一律沒有 p 值", _tiny.get("p") is None)
no_code = [rec("空人", {}, [{S.SEGMENT_ID: "x", S.CODES_F: []}])]
check("無編碼段落不產生列", len(A.build_long_df(no_code)), 0)
check("無編碼者健檢仍有列", len(A.coverage_report(no_code)), 1)


print()
print("=" * 70)
print("測試 N：極性可以當交叉表的列單位")
print("=" * 70)
# 要防的失效：crosstab_by_descriptor 的欄位排序只認 code 與 dimension，
# row_unit=polarity 時會拿維度清單去 reindex，每一欄都對不上，表整個變空。
# 而「屬性 × 極性」正好是這類語料裡唯一一張期望次數夠大、卡方前提站得住
# 的表——欄數最少，格子最滿。漏掉它等於把唯一算得出來的檢定藏起來。
_recs = [
    {S.RESPONDENT: f"R{i}",
     S.DESCRIPTORS: S.norm_descriptors(
         {"institution_type": "industry" if i % 2 else "academia"}),
     S.SEGMENTS: [
         {S.SEGMENT_ID: f"s{j}", S.TITLE: "t", S.QUOTE: "q", S.FULL_TEXT: "f",
          S.CODES_F: [S.make_code(S.ANTICIPATION, "P" if (i + j) % 2 else "N")]}
         for j in range(6)]}
    for i in range(8)]
_df = A.build_long_df(_recs)
_ct, _pct = A.crosstab_by_descriptor(_df, "institution_type",
                                     row_unit=S.POLARITY, normalize="row")
check_true("極性交叉表不是空的", not _ct.empty, str(_ct.shape))
check("極性交叉表是 2 欄", _ct.shape[1], 2)
check("欄名就是極性值", sorted(_ct.columns), sorted(S.POLARITIES))
check("總數守恆", int(_ct.values.sum()), len(_df))
check_true("百分比表同樣算得出來", not _pct.empty)
# 三種列單位都要能算，且不互相污染
for _u, _w in ((A.CODE, len(S.CODES)), (S.DIMENSION, 1), (S.POLARITY, 2)):
    _c, _ = A.crosstab_by_descriptor(_df, "institution_type", row_unit=_u,
                                     normalize=None)
    check_true(f"列單位 {_u} 算得出非空的表", not _c.empty, str(_c.shape))
    check_true(f"列單位 {_u} 的總數守恆", int(_c.values.sum()) == len(_df))

print()
print("=" * 70)
print("測試 N：受訪者層級的交叉表（卡方的獨立性假設）")
print("=" * 70)
# 卡方假設觀察彼此獨立，而編碼單元巢套在受訪者底下。期望次數守衛查不到
# 這件事——期望次數夠大反而讓一張前提不成立的表看起來可以做檢定。
_ld = A.build_long_df(RECORDS)
_seg, _ = A.crosstab_by_descriptor(_ld, "institution_type", row_unit=S.POLARITY)
_case, _ = A.crosstab_by_descriptor(_ld, "institution_type", row_unit=S.POLARITY,
                                    case_level=True)
check_true("段落層級的 n 等於長表列數", int(_seg.values.sum()) == len(_ld),
           f"{int(_seg.values.sum())} vs {len(_ld)}")
# 這一條是整段最重要的不變量：表的總數必須等於受訪者人數。
# 「每位受訪者在每一欄只計一次」那種寫法會讓正負兩極都講過的人被算兩次，
# 24 位受訪者得到 N = 48、四組全部 6/6、p = 1.00，守衛還會放行——而其他
# 每一條斷言它都通得過，只有「總數是不是人數」擋得住它。
_n_resp = _ld[S.RESPONDENT].nunique()
for _u in (S.POLARITY, S.DIMENSION, A.CODE):
    _c, _ = A.crosstab_by_descriptor(_ld, "institution_type", row_unit=_u,
                                     case_level=True)
    check(f"受訪者層級（{_u}）的總數 = 受訪者人數",
          int(_c.values.sum()), _n_resp)
check_true("每一列的人數 = 該組的受訪者人數",
           all(int(_case.loc[r].sum()) ==
               _ld[_ld["institution_type"] == r][S.RESPONDENT].nunique()
               for r in _case.index), _case.to_dict())

# 正負兩極各半的受訪者要歸到 mixed，不是兩邊各算一次
_both = [{S.RESPONDENT: "兩極各半", S.DESCRIPTORS: {**S.blank_descriptors(),
                                                 "institution_type": "industry"},
          S.SUMMARY: "", S.SEGMENTS: [
              {S.SEGMENT_ID: "S1", S.TITLE: "", S.QUOTE: "a", S.FULL_TEXT: "a",
               S.CODES_F: [S.make_code(S.ENGAGEMENT, "P")]},
              {S.SEGMENT_ID: "S2", S.TITLE: "", S.QUOTE: "b", S.FULL_TEXT: "b",
               S.CODES_F: [S.make_code(S.ENGAGEMENT, "N")]}]}]
_cb, _ = A.crosstab_by_descriptor(A.build_long_df(_both), "institution_type",
                                  row_unit=S.POLARITY, case_level=True)
check("兩極各半的人只算一次", int(_cb.values.sum()), 1)
check("而且歸在 mixed", list(_cb.columns), [A.CASE_MIXED])

# 明顯偏一邊的人歸到那一邊
_lean = [{**_both[0], S.RESPONDENT: "偏正向", S.SEGMENTS: _both[0][S.SEGMENTS] + [
    {S.SEGMENT_ID: "S3", S.TITLE: "", S.QUOTE: "c", S.FULL_TEXT: "c",
     S.CODES_F: [S.make_code(S.ANTICIPATION, "P")]}]}]
_cl, _ = A.crosstab_by_descriptor(A.build_long_df(_lean), "institution_type",
                                  row_unit=S.POLARITY, case_level=True)
check("偏正向的人歸在 P", list(_cl.columns), ["P"])
check_true("mixed 欄排在最後（不混進框架的碼裡）",
           list(A.crosstab_by_descriptor(
               A.build_long_df(_both + _lean), "institution_type",
               row_unit=S.POLARITY, case_level=True)[0].columns)[-1] == A.CASE_MIXED)
check("空長表也吃得下 case_level",
      A.crosstab_by_descriptor(empty, "sector", case_level=True)[0].empty, True)

# 同一位受訪者重複講同一件事，段落層級會放大，受訪者層級不會
_dup = [dict(RECORDS[0]) for _ in range(1)]
_dup[0] = {**RECORDS[0],
           S.SEGMENTS: RECORDS[0][S.SEGMENTS] + RECORDS[0][S.SEGMENTS]}
_ld2 = A.build_long_df(_dup + RECORDS[1:])
_seg2, _ = A.crosstab_by_descriptor(_ld2, "institution_type", row_unit=S.POLARITY)
_case2, _ = A.crosstab_by_descriptor(_ld2, "institution_type", row_unit=S.POLARITY,
                                     case_level=True)
check_true("把一位受訪者的段落複製一份，段落層級的表會變",
           not _seg2.equals(_seg), f"{_seg2.values.sum()} vs {_seg.values.sum()}")
check_true("**但受訪者層級的表不變**——這正是它存在的理由",
           _case2.equals(_case), f"{_case2.to_dict()} vs {_case.to_dict()}")

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
