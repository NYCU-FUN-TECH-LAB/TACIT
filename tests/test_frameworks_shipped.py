"""
把 frameworks/ 裡**每一個**隨工具發行的框架，都推過一次完整分析管線。

為什麼這一支存在
----------------
「可插拔框架」是這個工具的主要賣點，只拿 RI（極性 P/N）與 UTAUT
（**沒有**極性）來測是不夠的。維度換掉會不會壞，那兩個測得到；
但「極性值不叫 P/N」這條路，UTAUT 因為走 has_polarity=False 的分支而整段
跳過，兩個框架都碰不到。

於是下面這些東西活了下來，全部靠讀程式碼才發現：

  tacit_analysis.polarity_balance   前三行用 S.POLARITIES 補欄位，下一行寫
                                    g["P"] + g["N"] → 換 S/A 框架直接 KeyError
  tacit_lexicon._clause_score       否定詞翻轉寫死 "N" if pol=="P" else "P"
  tacit_lexicon.code_text           total.get((dim,"P")) → 換框架後恆為 0，
                                    **靜默回空 codes**，不報任何錯
  tacit_schema._DYNAMIC["POLARITIES"]  `or [P, N]` 讓無極性框架長出假的兩極
  tacit_review.codes_to_objects     無極性框架的 (dim, None) 全被丟掉
  tacit_themes._DIM_COLOR           寫死四個 RI 維度 id，換框架全畫成灰色

而 frameworks/esg_disclosure_probe.json 明明就躺在資料夾裡，極性值正是
S/A——它是唯一能踩到這些地雷的框架，所以必須被測試載入。別的測試裡的
「esg」都是測試自己 inline 建的假框架，連 id 都不一樣。

所以這支測試的規則是：**列舉真實的 frameworks/ 目錄**，不寫死名單。新增
一個框架檔就自動納入測試；沒有人需要記得回來加。
"""
import os
import sys

import tacit_analysis as A
import tacit_framework as F
import tacit_i18n as I
import tacit_irr as IRR
import tacit_lexicon as LX
import tacit_review as RV
import tacit_schema as S
import tacit_themes as RT

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FW_DIR = os.path.join(ROOT, "frameworks")

F.ensure_builtin_on_disk()
SHIPPED = F.list_available(FW_DIR)

print("=" * 70)
print("測試 1：發行的框架清單")
print("=" * 70)
print(f"  {FW_DIR}")
for fid, name, _p in SHIPPED:
    print(f"    - {fid}  ({name})")
ok("frameworks/ 至少有三個框架", len(SHIPPED) >= 3, f"{len(SHIPPED)} 個")

_ids = {fid for fid, _n, _p in SHIPPED}
ok("內建 RI 在清單裡", F.DEFAULT_FRAMEWORK_ID in _ids, str(sorted(_ids)))
# 這兩個是「不像預設框架」的證據，少了任何一個，可插拔的主張就少一條腿
ok("有一個無極性的框架（證明極性模型可以整個關掉）",
   "utaut_venkatesh_2003" in _ids, str(sorted(_ids)))
ok("有一個極性值不是 P/N 的框架（證明兩極的名稱不是寫死的）",
   "esg_disclosure_probe" in _ids, str(sorted(_ids)))


def sample_records(fw, n=2):
    """依框架自己的維度與極性造兩筆紀錄——不假設任何維度 id。"""
    out = []
    for i in range(n):
        segs = []
        for j, d in enumerate(fw.dimensions):
            p = (fw.polarity_values[(i + j) % len(fw.polarity_values)]
                 if fw.has_polarity else None)
            segs.append({
                S.SEGMENT_ID: f"S{j + 1:03d}",
                S.TITLE: f"sub-theme {j + 1}",
                S.QUOTE: f"quote {i}-{j}",
                S.FULL_TEXT: f"full text {i}-{j}",
                S.CODES_F: [S.make_code(d, p, f"rationale {j}")],
            })
        # 一個多重編碼段落：共現分析要有東西可算
        if len(fw.dimensions) >= 2:
            p0 = fw.polarity_values[0] if fw.has_polarity else None
            segs.append({
                S.SEGMENT_ID: f"S{len(fw.dimensions) + 1:03d}",
                S.TITLE: "multi-coded", S.QUOTE: f"quote {i}-multi",
                S.FULL_TEXT: f"full text {i}-multi",
                S.CODES_F: [S.make_code(fw.dimensions[0], p0, "r1"),
                            S.make_code(fw.dimensions[1], p0, "r2")],
            })
        out.append(S.migrate_record({
            S.RESPONDENT: f"case{i + 1}",
            S.DESCRIPTORS: S.blank_descriptors(),
            S.SUMMARY: "summary", S.SEGMENTS: segs}))
    return out


for fid, fname, path in SHIPPED:
    print()
    print("=" * 70)
    print(f"測試：{fid} —— {fname}")
    print("=" * 70)
    F.reset()
    try:
        fw = F.activate_by_id(fid, FW_DIR)
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 載入", False, f"{type(e).__name__}: {e}")
        continue
    ok(f"[{fid}] 載入並啟用", True,
       f"{len(fw.dimensions)} 維度 / 極性 {fw.polarity_values or '無'}")

    # schema 的動態屬性要跟著框架走，而且**不可以**替無極性框架生出假的兩極
    ok(f"[{fid}] S.DIMENSIONS 跟著框架", list(S.DIMENSIONS) == list(fw.dimensions))
    ok(f"[{fid}] S.POLARITIES 跟著框架（無極性就是空清單，不是 P/N）",
       list(S.POLARITIES) == list(fw.polarity_values),
       f"{list(S.POLARITIES)} vs {list(fw.polarity_values)}")
    ok(f"[{fid}] 編碼數 = 維度 × 極性",
       len(S.CODES) == len(fw.dimensions) * max(1, len(fw.polarity_values)),
       f"{len(S.CODES)} 個：{list(S.CODES)[:4]}…")
    if fw.has_polarity:
        ok(f"[{fid}] 編碼識別碼用的是框架宣告的極性值",
           all(S.split_code(c)[1] in fw.polarity_values for c in S.CODES),
           str(list(S.CODES)[:4]))

    recs = sample_records(fw)
    long_df = A.build_long_df(recs)
    ok(f"[{fid}] 長表建得起來", not long_df.empty, f"{len(long_df)} 列")

    # --- 這裡就是 KeyError 發生過的地方 ---
    try:
        per_dim, overall = A.polarity_balance(long_df)
        ok(f"[{fid}] 極性平衡不炸", True,
           f"{len(per_dim)} 列 / 欄位 {list(overall.columns)}")
        if fw.has_polarity and len(fw.polarity_values) == 2:
            ok(f"[{fid}] 兩極框架算得出極性指數",
               "polarity_index" in overall.columns, str(list(overall.columns)))
            ok(f"[{fid}] 極性欄位用框架的值命名",
               all(p in overall.columns for p in fw.polarity_values),
               str(list(overall.columns)))
            ok(f"[{fid}] 極性指數在 [-1, 1] 之間",
               all(-1.0 <= v <= 1.0 for v in overall["polarity_index"].dropna()),
               str(overall["polarity_index"].tolist()))
        else:
            # 無極性框架不該生出一個假的指數——那會讓使用者以為有這個分析
            ok(f"[{fid}] 無極性框架不產生極性指數",
               "polarity_index" not in overall.columns,
               str(list(overall.columns)))
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 極性平衡不炸", False, f"{type(e).__name__}: {e}")

    for label, fn in [("交叉表", lambda: A.crosstab_by_descriptor(
                           long_df, S.DESCRIPTOR_KEYS[0])),
                      ("共現", lambda: A.cooccurrence(recs)),
                      ("排除併碼的共現", lambda: A.cooccurrence(
                           recs, exclude_merged=True)),
                      ("併碼來源表", lambda: A.merge_provenance(recs)),
                      ("跨案例矩陣", lambda: A.case_matrix(long_df)),
                      ("資料健檢", lambda: A.coverage_report(recs))]:
        try:
            fn()
            ok(f"[{fid}] {label}不炸", True)
        except Exception as e:                               # noqa: BLE001
            ok(f"[{fid}] {label}不炸", False, f"{type(e).__name__}: {e}")

    # 共現配對清單（需要 cooccurrence 的輸出）
    try:
        _c, _j, _t = A.cooccurrence(recs)
        A.cooccurrence_pairs(_c, _t)
        ok(f"[{fid}] 共現配對清單不炸", True)
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 共現配對清單不炸", False, f"{type(e).__name__}: {e}")

    # --- 複核：無極性框架的 (dim, None) 不可以被整批丟掉 ---
    try:
        codes = S.codes_of(recs[0][S.SEGMENTS][0])
        objs = RV.codes_to_objects(codes)
        ok(f"[{fid}] 複核物件轉換不丟碼",
           len(objs) == len(codes), f"{len(objs)}/{len(codes)}")
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 複核物件轉換不丟碼", False, f"{type(e).__name__}: {e}")

    # --- 詞庫：不可以靜默回空 ---
    try:
        blank = LX.blank_lexicon()
        ct = blank[LX.CONCEPT_TERMS]
        ok(f"[{fid}] 空白詞庫的維度與框架一致",
           set(ct) == set(fw.dimensions), str(sorted(ct)))
        if fw.has_polarity:
            ok(f"[{fid}] 空白詞庫的極性鍵與框架一致",
               all(set(v) == set(fw.polarity_values) for v in ct.values()),
               str([sorted(v) for v in list(ct.values())[:1]]))
        else:
            ok(f"[{fid}] 無極性框架的詞庫不長出假的 P/N",
               all(not set(v) & {"P", "N"} for v in ct.values()),
               str([sorted(v) for v in list(ct.values())[:1]]))
        LX.lexicon_stats(blank)
        ok(f"[{fid}] 詞庫統計不炸", True)
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 詞庫路徑不炸", False, f"{type(e).__name__}: {e}")

    # --- 提示詞：整份要由框架推導，而且不得殘留別的框架的字 ---
    #
    # 注意：import app 會執行 app.py 的模組層級程式，而那裡面有一段
    # activate_by_id(session_state.framework_id)——在 bare mode 下讀不到
    # session_state，於是它 reset() 成內建 RI。**作用中框架會被換掉。**
    # 不切回來的話，ESG 的顏色、標籤、主題提示詞三項會全失敗，
    # 而失敗的原因不在被測的程式，在這一行 import。
    # 所以 import 之後、往下測之前，要把框架切回來。
    try:
        import app as APP
        F.activate_by_id(fid, FW_DIR)
        p = APP.build_system_prompt(fw, "en", "a short sample")
        ok(f"[{fid}] 提示詞產得出來", len(p) > 500, f"{len(p)} 字元")
        for d in fw.dimensions:
            if f"[id: {d}]" not in p:
                ok(f"[{fid}] 提示詞列出所有維度", False, f"缺 {d}")
                break
        else:
            ok(f"[{fid}] 提示詞列出所有維度", True)
        if fid != F.DEFAULT_FRAMEWORK_ID:
            # 換了框架，提示詞裡不該再出現 RI 的維度 id
            leaked = [d for d in ("anticipation", "reflexivity",
                                  "engagement", "responsiveness")
                      if f"[id: {d}]" in p]
            ok(f"[{fid}] 提示詞沒有殘留 RI 的維度", not leaked, str(leaked))
        if fw.has_polarity:
            ok(f"[{fid}] 提示詞用框架自己的極性值",
               f'one of {"|".join(fw.polarity_values)}' in p,
               "|".join(fw.polarity_values))
        else:
            ok(f"[{fid}] 無極性框架的提示詞不要求極性",
               '"polarity"' not in p)
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 提示詞產得出來", False, f"{type(e).__name__}: {e}")

    # --- 主題：Gioia 圖的配色不可以整片同色 ---
    try:
        colors = {RT.dim_color(d) for d in fw.dimensions}
        ok(f"[{fid}] 每個維度拿到不同顏色（Gioia 圖靠顏色分維度）",
           len(colors) == len(fw.dimensions), str(sorted(colors)))
        ok(f"[{fid}] 沒有維度落到灰色預設值", "#555" not in colors)
        block = RT._dimension_block("en")
        for d in fw.dimensions:
            if d not in block:
                ok(f"[{fid}] 主題聚斂提示詞列出所有維度", False, f"缺 {d}")
                break
        else:
            ok(f"[{fid}] 主題聚斂提示詞列出所有維度", True)
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 主題路徑不炸", False, f"{type(e).__name__}: {e}")

    # --- 信度：抽樣框不該假設任何維度 ---
    try:
        _tr = {r[S.RESPONDENT]: ("這是一段足夠長的逐字稿內容，用來讓抽樣框切得出"
                                 "分析單元，長度必須超過最小門檻才會被保留下來。")
               for r in recs}
        frame = IRR.build_frame(recs, _tr)
        ok(f"[{fid}] 信度抽樣框建得起來", len(frame) > 0, f"{len(frame)} 個單元")
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 信度抽樣框建得起來", False, f"{type(e).__name__}: {e}")

    # --- 介面標籤：不可以把內部識別碼漏到畫面上 ---
    try:
        for d in fw.dimensions:
            lab = I.dim(d, "en")
            if lab == d and fw.label(d, "en") != d:
                ok(f"[{fid}] 維度標籤取得到", False, f"{d} 回傳了識別碼")
                break
        else:
            ok(f"[{fid}] 維度標籤取得到", True)
        for c in S.CODES:
            I.code_label(c)
        ok(f"[{fid}] 每個編碼都有可顯示的標籤", True)
    except Exception as e:                                   # noqa: BLE001
        ok(f"[{fid}] 介面標籤不炸", False, f"{type(e).__name__}: {e}")

    # --- 排除條件：構念邊界要寫在框架裡，不能留給模型自己想 ---
    ok(f"[{fid}] 有宣告排除條件", fw.has_exclusions(),
       "沒有排除條件的框架，構念邊界是模型當場決定的")

F.reset()
print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
