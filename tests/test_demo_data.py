"""
驗證示範資料：引文對得回逐字稿、統計真的跑得出來、設計的分布真的存在。

這一支測試的存在理由，是示範資料的兩個宣稱都很容易在不知不覺中失效：

  1. 「每一段引文都是逐字稿的逐字子字串」——只要有人改了一個字，
     信度模組的抽樣框就會少掉單元，而且介面上不會報錯。
  2. 「樣本數足以讓統計跑得出來」——這正是把示範資料從 6 份擴到 24 份
     的唯一理由。若有人日後刪掉幾份，卡方又會退回「樣本不足」，
     而 README 與論文裡的宣稱就變成假的。

兩件事都不該靠人記得檢查。
"""
import json
import os
import sys

import pandas as pd

import demo_transcripts_en as EN
import tacit_schema as S
import tacit_analysis as A
import tacit_irr as IRR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANALYSES = os.path.join(ROOT, "analyses")

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


print("=" * 70)
print("測試 1：語料規模")
print("=" * 70)
st = EN.stats()
ok("24 位受訪者", st["respondents"] == 24, str(st["respondents"]))
ok("四種機構類型各 6 位",
   set(st["by_institution"].values()) == {6}, str(st["by_institution"]))
ok("段落數足以做主題歸納（>100）", st["segments"] > 100, str(st["segments"]))
ok("四個維度都有足量編碼（各 >30）",
   all(v > 30 for v in st["by_dimension"].values()), str(st["by_dimension"]))

print()
print("=" * 70)
print("測試 2：引文必須是逐字稿的逐字子字串")
print("=" * 70)
# R() 在建檔時已對「回答段落」驗過一次。這裡驗的是更嚴格的一關：
# 引文要對得上**寫進 .docx 再解析回來**的文字。版面、樣式、表格欄位
# 都可能讓解析結果與原始字串不一致，那正是實際會壞掉的地方。
recs = []
for fn in sorted(os.listdir(ANALYSES)) if os.path.isdir(ANALYSES) else []:
    if fn.startswith("demo_en_") and fn.endswith(".json"):
        with open(os.path.join(ANALYSES, fn), "r", encoding="utf-8") as f:
            recs.append(S.migrate_record(json.load(f)))

ok("找得到 24 份參考編碼", len(recs) == 24,
   f"{len(recs)}；若為 0 請先執行 python make_demo_data.py")

if recs:
    bad = []
    for r in recs:
        tr = r.get(S.TRANSCRIPT, "")
        for seg in r.get(S.SEGMENTS, []):
            if seg[S.QUOTE] not in tr:
                bad.append(f"{r[S.RESPONDENT]}/{seg[S.SEGMENT_ID]}")
    ok("每一段引文都在逐字稿裡找得到", not bad, f"{len(bad)} 筆對不上：{bad[:3]}")

    ok("每份紀錄都保存了逐字稿",
       all(r.get(S.TRANSCRIPT) for r in recs),
       "沒有逐字稿的紀錄無法做信度檢定")

    # 磁碟上的示範語料必須跟原始碼一致。
    #
    # 要防的失效：在軟體裡複核示範資料（確認幾個碼、刪掉兩段）會把紀錄寫回
    # analyses/，於是磁碟上的語料悄悄跟 demo_transcripts_en.py 分了家。
    # README 與論文引用的每一個數字都是從這批語料算出來的，語料一漂移，
    # 那些數字就對不上了，而且沒有任何地方會報錯——直到有人自己跑一次。
    # 要恢復：python make_demo_data.py
    on_disk = sum(len(r.get(S.SEGMENTS) or []) for r in recs)
    ok("磁碟上的段落數與原始碼一致",
       on_disk == st["segments"],
       f"disk={on_disk} source={st['segments']}；"
       f"示範語料被改過了。執行 python make_demo_data.py 可還原")
    ok("來源欄標明是參考編碼而非模型輸出",
       all(r.get(S.META, {}).get("source") == "demo/reference-coding"
           for r in recs),
       "這個欄位會進匯出檔，標錯就是誤導讀者")

print()
print("=" * 70)
print("測試 3：統計真的跑得出來（擴充語料的唯一理由）")
print("=" * 70)
if recs and A.HAS_SCIPY:
    df = A.build_long_df(recs)
    ok("長表非空", not df.empty, f"{len(df)} 列")

    # 機構類型 × 極性：這一張表是「6 份不夠、24 份才夠」的具體證據。
    #
    # 走 crosstab_by_descriptor 而不是自己 pd.crosstab：測試要走使用者
    # 實際會走的那條路。在這裡自己算的話，就算極性根本不在介面的
    # 「列單位」選項裡——README 引用的數字在軟體上做不出來——測試也會過。
    ct, _ = A.crosstab_by_descriptor(df, "institution_type",
                                     row_unit=S.POLARITY, normalize=None)
    ok("極性交叉表算得出來（介面的列單位選項之一）",
       ct.shape == (4, 2), str(ct.shape))
    rep = A.chi_square_report(ct)
    ok("機構類型 × 極性：卡方假設成立",
       rep.get("verdict") == A.CHI_OK,
       f"verdict={rep.get('verdict')} min_expected={rep.get('min_expected')}")
    ok("機構類型 × 極性：沒有任何一格期望次數 < 5",
       rep.get("cells_below_5") == 0, str(rep.get("cells_below_5")))
    ok("機構類型 × 極性：真的印得出 p 值",
       rep.get("p") is not None, str(rep.get("p")))
    ok("刻意設計的關聯確實存在（p < .05）",
       rep.get("p") is not None and rep["p"] < 0.05,
       f"p={rep.get('p')}；示範資料若無關聯，交叉分析頁籤就什麼也示範不到")

    # 維度 × 機構類型：假設同樣成立，但結果不顯著。
    # 這一項是刻意保留的：工具在假設成立時也要能誠實地報告「沒有關聯」，
    # 而不是只在顯著時才有畫面。
    ct2, _ = A.crosstab_by_descriptor(df, "institution_type",
                                      row_unit=S.DIMENSION, normalize=None)
    rep2 = A.chi_square_report(ct2)
    ok("維度 × 機構類型：卡方假設也成立",
       rep2.get("verdict") == A.CHI_OK, str(rep2.get("verdict")))

    # 八格編碼的交叉表仍然稀疏——這是**對的**行為，守衛必須還在。
    ct3, _ = A.crosstab_by_descriptor(df, "institution_type",
                                      row_unit=A.CODE, normalize=None)
    rep3 = A.chi_square_report(ct3)
    ok("八格編碼交叉表仍被判定為稀疏（守衛沒有被樣本數沖掉）",
       rep3.get("verdict") == A.CHI_SPARSE,
       f"verdict={rep3.get('verdict')}；擴充語料不該讓假設檢查失效")
    ok("稀疏時不提供 p 值", rep3.get("p") is None, str(rep3.get("p")))
elif recs:
    print("  SKIP  scipy 未安裝，跳過卡方相關檢查")

print()
print("=" * 70)
print("測試 4：共現分析有東西可算")
print("=" * 70)
if recs:
    ok("有多重編碼的段落",
       st["multi_coded"] > 0, f"{st['multi_coded']} 段")
    rate = st["multi_coded"] / st["segments"]
    ok("多重編碼率落在合理區間（10%–35%）", 0.10 <= rate <= 0.35,
       f"{rate:.0%}；過高表示切分方式有問題，過低則共現矩陣太稀疏")
    counts, jac, totals = A.cooccurrence(recs, level=A.LEVEL_SEGMENT)
    pairs = A.cooccurrence_pairs(counts, totals)
    ok("共現配對非空", not pairs.empty, f"{len(pairs)} 組")
    if not pairs.empty:
        ok("存在跨維度共現",
           bool(pairs["cross_dimension"].any()),
           "只有同維度共現的話，共現分析看不出任何理論上有意思的東西")

print()
print("=" * 70)
print("測試 5：信度抽樣框含未標記單元（recall 才有意義）")
print("=" * 70)
if recs:
    tr = {r[S.RESPONDENT]: r[S.TRANSCRIPT] for r in recs}
    frame, diag = IRR.build_frame(recs, tr)
    ok("抽樣框單元數足夠（>200）", diag["total_units"] > 200,
       str(diag["total_units"]))
    ok("抽樣框含未標記單元", diag["uncoded_units"] > 0,
       f"{diag['uncoded_units']}；沒有未標記單元的話 recall 恆等於 1，數字沒有意義")
    ok("每一段參考引文都對得回抽樣框的單元",
       not diag["unmatched_quotes"], str(diag["unmatched_quotes"]))
    samp = IRR.stratified_sample(frame, 60, seed=7)
    if isinstance(samp, tuple):
        samp = samp[0]
    ok("分層抽樣抽得出 60 個單元", len(samp) == 60, str(len(samp)))
    ok("樣本同時含已標記與未標記單元",
       0 < sum(1 for u in samp if u[S.AI_CODES]) < len(samp))

print()
print("=" * 70)
print("測試 6：合成資料聲明必須隨檔案流通")
print("=" * 70)
for sub, name, needle in (("en", "00_ABOUT_THIS_DATA.txt", "FICTIONAL"),
                          ("zh", "00_關於這批資料.txt", "虛構")):
    p = os.path.join(ROOT, "demo_data", sub, name)
    exists = os.path.isfile(p)
    ok(f"demo_data/{sub}/ 有資料聲明", exists)
    if exists:
        with open(p, encoding="utf-8") as f:
            txt = f.read()
        ok(f"demo_data/{sub}/ 聲明有講清楚是虛構的", needle in txt)

n_docx = len([f for f in os.listdir(os.path.join(ROOT, "demo_data", "en"))
              if f.endswith(".docx") and not f.startswith("~$")]) \
    if os.path.isdir(os.path.join(ROOT, "demo_data", "en")) else 0
ok("英文示範資料有 24 份 .docx", n_docx == 24, str(n_docx))

print()
print("=" * 70)
print("結果：全部通過 ✅" if not FAIL else f"結果：{len(FAIL)} 項失敗 ❌")
for f in FAIL:
    print(f"  - {f}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
