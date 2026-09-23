"""
tacit_analysis.py — 交互分析引擎（混合方法）
==========================================
獨立於 app.py 的模組，理由有三：

  1. 測試不必再用 exec 把 Streamlit 檔案挖開才能載入
  2. app 只剩介面，多語轉換的風險大幅降低
  3. 這個引擎本身可被其他研究重用——它不綁定任何特定框架的內容，
     只要資料符合 tacit_schema，任何先驗編碼簿都能套用

四種分析對應 Dedoose 的核心功能，但在三處做得更嚴謹：
  - 交叉表預設輸出**列百分比**（原始次數受組別大小與逐字稿長度污染）
  - 共現另計 **Jaccard**（校正「某碼本來就常出現」造成的假性強關聯）
  - 卡方**主動檢查期望次數**，前提不成立時拒絕提供 p 值

所有回傳欄位皆為 ASCII 識別碼；顯示標籤請在呈現層透過 tacit_i18n 轉換。
"""

import itertools
import math
from collections import Counter, defaultdict

import numpy as np
import pandas as pd

import tacit_schema as S

try:
    from scipy.stats import chi2_contingency
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# --- 長表欄位（ASCII） ----------------------------------------------
CODE = "code"
MULTI_CODED = "multi_coded"
CODES_IN_SEGMENT = "codes_in_segment"

# --- 共現層級 --------------------------------------------------------
LEVEL_SEGMENT = "segment"
LEVEL_CASE = "case"


# =====================================================================
# 1. 長表：所有分析的基底
# =====================================================================
def build_long_df(records):
    """
    一列 = 一個「段落-編碼」配對。
    注意：一段被雙重編碼的引文會佔兩列，因此列數 >= 段落數。
    """
    rows = []
    for rec in records:
        resp = rec.get(S.RESPONDENT, "unknown")
        desc = rec.get(S.DESCRIPTORS) or S.blank_descriptors()
        for seg in rec.get(S.SEGMENTS, []):
            codes = S.codes_of(seg)
            n_codes = len(codes)
            # 一個段落可能被指派兩個「同維度同極性但理由不同」的碼。分析層
            # 以 (段落, 維度, 極性) 為分析單位，所以那仍然只算一列——同一段
            # 話在同一個維度上被算兩次會扭曲共現與 Jaccard。但理由是研究者
            # 的判斷內容，不可以因此被覆蓋掉：兩個理由都留著，用分號串接，
            # 匯出時看得到完整的判斷依據。
            rationale = {}
            for c in seg.get(S.CODES_F) or []:
                d, p = S.norm_dimension(c.get(S.DIMENSION)), S.norm_polarity(c.get(S.POLARITY))
                if d in S.DIMENSIONS and p:
                    key = S.code_of(d, p)
                    txt = (c.get(S.RATIONALE) or "").strip()
                    if not txt:
                        rationale.setdefault(key, "")
                    elif rationale.get(key):
                        if txt not in rationale[key]:
                            rationale[key] += "; " + txt
                    else:
                        rationale[key] = txt
            for code in codes:
                dim, pol = S.split_code(code)
                row = {
                    S.RESPONDENT: resp,
                    S.SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                    S.DIMENSION: dim,
                    S.POLARITY: pol,
                    CODE: code,
                    MULTI_CODED: n_codes > 1,
                    CODES_IN_SEGMENT: n_codes,
                }
                for k in S.DESCRIPTOR_KEYS:
                    row[k] = desc.get(k, S.UNSPECIFIED)
                row[S.TITLE] = seg.get(S.TITLE, "")
                row[S.QUOTE] = seg.get(S.QUOTE, "")
                row[S.FULL_TEXT] = seg.get(S.FULL_TEXT, "")
                row[S.RATIONALE] = rationale.get(code, "")
                rows.append(row)
    cols = ([S.RESPONDENT, S.SEGMENT_ID, S.DIMENSION, S.POLARITY, CODE,
             MULTI_CODED, CODES_IN_SEGMENT] + S.DESCRIPTOR_KEYS +
            [S.TITLE, S.QUOTE, S.FULL_TEXT, S.RATIONALE])
    return pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)


# =====================================================================
# 2. 維度 × 屬性交叉表
# =====================================================================
def crosstab_by_descriptor(long_df, descriptor_key, row_unit=CODE, normalize="row",
                           case_level=False):
    """
    回傳 (次數表, 百分比表)。
    normalize="row" → 各屬性組別內部的編碼分布，已消除組別大小差異，組間才可比較。

    case_level=True → **每位受訪者只佔一列**，歸到他最常出現的那一類；
    最常出現的不只一類就歸 "mixed"。表的總數等於受訪者人數。

    為什麼需要這個開關：卡方檢定假設觀察彼此獨立，而編碼單元**巢套在受訪者
    底下**——24 位受訪者貢獻 181 個單元，平均一人 7.5 個。同一個人講了七段
    同樣的話，在段落層級的表裡就是七個獨立觀察，它們當然不獨立。
    chi_square_report 只查期望次數，查不到這件事；期望次數夠大反而讓一張
    前提不成立的表看起來可以做檢定。

    **為什麼不是「每位受訪者在每一欄只計一次」。** 那種做法（對 (受訪者, 類別)
    去重）看起來合理，但一個正負兩極都講過的人會被算兩次：示範語料的 24 位
    受訪者會得到 N = 48，四組全部 6/6，χ² = 0、p = 1.00，期望次數守衛還會
    放行。同一個人同時坐在兩欄裡，那張表比段落層級的更不獨立，只是看起來
    很乾淨。N 大於受訪者人數，就是這種錯的指紋。

    一人一列之後，同一份語料是 N = 24、12 格期望次數全部小於 5，守衛扣住
    p 值。描述上的樣態還在（六位學界受訪者全部偏正向），只是 24 個人撐不起
    推論檢定——這才是這份語料誠實的答案。
    """
    if long_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    if case_level:
        def _modal(g):
            vc = g.value_counts()
            if len(vc) == 1 or vc.iloc[0] > vc.iloc[1]:
                return vc.index[0]
            return CASE_MIXED

        long_df = (long_df.groupby(S.RESPONDENT, sort=False)
                   .agg(**{descriptor_key: (descriptor_key, "first"),
                           row_unit: (row_unit, _modal)})
                   .reset_index())
    # 欄的排列順序依單位而定。極性本來漏在這裡：row_unit=polarity 時會拿
    # 維度清單去 reindex，結果每一欄都對不上，交叉表整個變空。
    # 而機構類型 × 極性正好是這類語料裡唯一一張期望次數夠大、卡方前提
    # 站得住的表——漏掉它等於把唯一算得出來的檢定藏起來。
    order = {CODE: S.CODES, S.DIMENSION: S.DIMENSIONS,
             S.POLARITY: S.POLARITIES}.get(row_unit, S.DIMENSIONS)
    ct = pd.crosstab(long_df[descriptor_key], long_df[row_unit])
    cols = [c for c in order if c in ct.columns]
    if CASE_MIXED in ct.columns:
        cols.append(CASE_MIXED)
    ct = ct.reindex(columns=cols)
    if normalize == "row":
        denom = ct.sum(axis=1).replace(0, np.nan)
        pct = (ct.div(denom, axis=0) * 100).round(1).fillna(0)
    else:
        denom = ct.sum(axis=0).replace(0, np.nan)
        pct = (ct.div(denom, axis=1) * 100).round(1).fillna(0)
    return ct, pct


# 受訪者層級的表裡，最常出現的類別不只一個的受訪者
CASE_MIXED = "mixed"

CHI_OK = "assumptions_met"
CHI_SPARSE = "expected_counts_too_small"
CHI_UNAVAILABLE = "scipy_not_installed"
CHI_TOO_SMALL = "table_too_small"


def chi_square_report(ct):
    """
    卡方檢定 + 期望次數健檢。

    質性研究樣本小，多數情況期望次數不足。此時本函式明確回傳
    verdict=CHI_SPARSE 且 valid=False——與其給一個看起來像結論的 p 值，
    不如讓呼叫端知道它不能用。另需注意：同一位受訪者貢獻多筆編碼
    會違反觀察值獨立假設，這一點呼叫端應在介面上標明。
    """
    if not HAS_SCIPY:
        return {"available": False, "verdict": CHI_UNAVAILABLE}
    if ct.empty or ct.shape[0] < 2 or ct.shape[1] < 2:
        return {"available": False, "verdict": CHI_TOO_SMALL}
    ct_clean = ct.loc[ct.sum(axis=1) > 0, ct.sum(axis=0) > 0]
    if ct_clean.shape[0] < 2 or ct_clean.shape[1] < 2:
        return {"available": False, "verdict": CHI_TOO_SMALL}

    chi2, p, dof, expected = chi2_contingency(ct_clean.values)
    exp = np.asarray(expected)
    small = int((exp < 5).sum())
    frac_small = small / exp.size
    n = int(ct_clean.values.sum())
    k = min(ct_clean.shape) - 1
    cramers_v = float(np.sqrt(chi2 / (n * k))) if n > 0 and k > 0 else float("nan")
    valid = frac_small <= 0.2 and exp.min() >= 1
    return {
        "available": True, "valid": valid,
        "verdict": CHI_OK if valid else CHI_SPARSE,
        "chi2": round(float(chi2), 3),
        "p": float(p) if valid else None,
        "p_raw": float(p),
        "dof": int(dof), "cramers_v": round(cramers_v, 3), "n": n,
        "cells_below_5": small, "cells_total": int(exp.size),
        "min_expected": round(float(exp.min()), 2),
    }


# =====================================================================
# 3. 編碼共現
# =====================================================================
MERGE_ACTION = "merged_across_excerpts"


def merged_codes(seg):
    """
    這個段落裡有哪些碼是**跨窗合併**帶進來的。

    長逐字稿分窗編碼時，同一句話可能在兩個窗口各被判一次；合併成一段之後
    它就帶著兩個碼，於是在段落層級構成一次共現。但那個共現不是模型在任何
    一次判斷裡主張的，而是分窗這個動作的產物。

    實測的量體不小：一份英文訪談稿 94 段裡，14 個多重編碼段落有 11 個是
    這樣來的——也就是說該份的共現表七成以上是合併造成的。這件事必須看得
    見，否則「參與·開放 × 回應性·調適」這種結論會被當成資料講出去。
    """
    out = set()
    for e in ((seg.get(S.REVIEW) or {}).get(S.HISTORY) or []):
        if e.get("action") != MERGE_ACTION:
            continue
        for part in str(e.get("detail") or "").split(":")[-1].split(","):
            part = part.strip()
            if part in S.CODES:
                out.add(part)
    return out


def cooccurrence(records, level=LEVEL_SEGMENT, exclude_merged=False):
    """
    level=segment → 同一段引文同時被標記兩碼（嚴格共現，Dedoose 式）
    level=case    → 同一受訪者同時出現兩碼（寬鬆關聯，樣本小時使用）
    回傳 (共現次數矩陣, Jaccard 矩陣, 各碼總次數)

    exclude_merged=True 時，跨窗合併帶進來的碼不計入共現——只保留模型在
    單一次判斷裡就同時給出的那些。兩個數字並陳，差距本身就是一個訊息：
    差很多就代表該份的共現大半是分窗的產物。
    """
    counts = pd.DataFrame(0, index=S.CODES, columns=S.CODES, dtype=int)
    totals = pd.Series(0, index=S.CODES, dtype=int)

    def seg_codes(seg):
        cs = set(S.codes_of(seg))
        return cs - merged_codes(seg) if exclude_merged else cs

    def code_sets():
        if level == LEVEL_SEGMENT:
            for rec in records:
                for seg in rec.get(S.SEGMENTS, []):
                    yield seg_codes(seg)
        else:
            for rec in records:
                s = set()
                for seg in rec.get(S.SEGMENTS, []):
                    s |= seg_codes(seg)
                yield s

    for cs in (s for s in code_sets() if s):
        for c in cs:
            if c in totals.index:
                totals[c] += 1
        for a, b in itertools.combinations(sorted(cs), 2):
            if a in counts.index and b in counts.columns:
                counts.loc[a, b] += 1
                counts.loc[b, a] += 1
    for c in S.CODES:
        counts.loc[c, c] = int(totals[c])

    jac = pd.DataFrame(0.0, index=S.CODES, columns=S.CODES)
    for a, b in itertools.combinations(S.CODES, 2):
        union = totals[a] + totals[b] - counts.loc[a, b]
        v = round(counts.loc[a, b] / union, 3) if union > 0 else 0.0
        jac.loc[a, b] = jac.loc[b, a] = v
    for c in S.CODES:
        jac.loc[c, c] = 1.0 if totals[c] > 0 else 0.0
    return counts, jac, totals


def cooccurrence_pairs(counts, totals, top_n=15):
    """把共現矩陣攤平成可讀的配對清單，依共現次數排序。"""
    rows = []
    for a, b in itertools.combinations(S.CODES, 2):
        n = int(counts.loc[a, b])
        if n == 0:
            continue
        union = totals[a] + totals[b] - n
        rows.append({
            "code_a": a, "code_b": b, "cooccurrence": n,
            "count_a": int(totals[a]), "count_b": int(totals[b]),
            "jaccard": round(n / union, 3) if union > 0 else 0.0,
            "cross_dimension": S.split_code(a)[0] != S.split_code(b)[0],
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df = (df.sort_values(["cooccurrence", "jaccard"], ascending=False)
                .head(top_n).reset_index(drop=True))
    return df


def merge_provenance(records):
    """
    多重編碼裡有多少是跨窗合併造成的。回傳每位受訪者一列。

    這張表是共現分析該不該照用的判斷依據：merged_share 高就代表該份的
    共現主要是分窗的產物，不是模型的判斷。
    """
    rows = []
    for rec in records:
        segs = rec.get(S.SEGMENTS) or []
        multi = [s for s in segs if len(set(S.codes_of(s))) > 1]
        from_merge = [s for s in multi if merged_codes(s)]
        rows.append({
            S.RESPONDENT: rec.get(S.RESPONDENT, ""),
            "segments": len(segs),
            "multi_coded": len(multi),
            "multi_from_merge": len(from_merge),
            "merged_share": round(len(from_merge) / len(multi), 3) if multi else 0.0,
        })
    return pd.DataFrame(rows)


# =====================================================================
# 4. 跨案例矩陣
# =====================================================================
def case_matrix(long_df, normalize=False):
    """列＝受訪者，欄＝八格編碼。normalize=True 轉為該受訪者內部百分比。"""
    if long_df.empty:
        return pd.DataFrame()
    m = pd.crosstab(long_df[S.RESPONDENT], long_df[CODE])
    m = m.reindex(columns=S.CODES, fill_value=0)
    if normalize:
        denom = m.sum(axis=1).replace(0, np.nan)
        m = (m.div(denom, axis=0) * 100).round(1).fillna(0)
    return m


# =====================================================================
# 5. 極性平衡
# =====================================================================
def polarity_balance(long_df):
    """
    極性指數 = (第一極 − 第二極) / 總數，值域 [−1, +1]。
    已對編碼總量標準化，因此不受逐字稿長度影響，可跨案例比較。
    但某維度編碼總數過少（<3）時極不穩定，解讀時須對照 total 欄。

    【兩極的名稱由框架決定，不是 P 和 N】

    要防的失效：上面三行用 S.POLARITIES 補欄位，下一行卻寫
    `g["P"] + g["N"]`。內建 RI 框架的極性剛好叫 P/N，所以看不出問題；但
    frameworks/ 裡躺著的 esg_disclosure_probe.json 用的是 S/A（有憑據／
    僅為宣稱），載入它再打開這個分析就是 KeyError。

    這個 bug 能活下來是因為測試裡的第二個框架是 UTAUT，而 UTAUT **沒有**
    極性模型——它走 has_polarity=False 的分支，整段根本不執行。換句話說，
    「證明可插拔」的那個例子剛好跳過了唯一會壞的那條路。

    另外這個指數本身有前提：它假設極性恰好兩極、而且兩極有方向性（誰減誰
    才有意義）。超過兩極就不算，回傳的欄位裡只保留各極的次數與 total。
    """
    if long_df.empty:
        return pd.DataFrame(), pd.DataFrame()
    pols = list(S.POLARITIES)
    g = long_df.groupby([S.RESPONDENT, S.DIMENSION])[S.POLARITY] \
               .value_counts().unstack(fill_value=0)
    for p in pols:
        if p not in g.columns:
            g[p] = 0
    g = g.reset_index()
    overall = long_df.groupby(S.RESPONDENT)[S.POLARITY] \
                     .value_counts().unstack(fill_value=0)
    for p in pols:
        if p not in overall.columns:
            overall[p] = 0

    if not pols:
        # 無極性框架：呼叫端本來就該先問 has_polarity，但真的走到這裡
        # 也不能炸。給出次數為 0 的空結構，而不是一個假的指數。
        g["total"] = 0
        overall["total_codes"] = 0
        return g, overall.reset_index()

    g["total"] = g[pols].sum(axis=1)
    overall["total_codes"] = overall[pols].sum(axis=1)
    if len(pols) == 2:
        hi, lo = pols[0], pols[1]        # 框架宣告的順序＝正向在前
        g["pn_ratio"] = np.where(g[lo] > 0, (g[hi] / g[lo]).round(2), np.nan)
        g["polarity_index"] = np.where(
            g["total"] > 0, ((g[hi] - g[lo]) / g["total"]).round(3), np.nan)
        overall["polarity_index"] = (
            (overall[hi] - overall[lo]) / overall["total_codes"].replace(0, np.nan)
        ).round(3)
    return g, overall.reset_index()


# =====================================================================
# 6. 資料健檢
# =====================================================================
def coverage_report(records):
    """每位受訪者的段落數、編碼數、多重編碼比例、屬性完整度。"""
    rows = []
    for rec in records:
        segs = rec.get(S.SEGMENTS, [])
        n_codes = sum(len(S.codes_of(s)) for s in segs)
        multi = sum(1 for s in segs if len(S.codes_of(s)) > 1)
        desc = rec.get(S.DESCRIPTORS) or {}
        filled = sum(1 for k in S.DESCRIPTOR_KEYS
                     if desc.get(k, S.UNSPECIFIED) != S.UNSPECIFIED)
        dims_hit = {S.split_code(c)[0] for s in segs for c in S.codes_of(s)}
        rows.append({
            S.RESPONDENT: rec.get(S.RESPONDENT, "unknown"),
            "segments": len(segs),
            "codes": n_codes,
            "multi_coded_segments": multi,
            "multi_coded_rate": round(multi / len(segs), 3) if segs else None,
            "dimensions_covered": len(dims_hit),
            "descriptors_filled": filled,
            "descriptors_total": len(S.DESCRIPTOR_KEYS),
        })
    return rows
