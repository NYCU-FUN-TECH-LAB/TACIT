"""
bench_agreement.py — 模型編碼與參考編碼的一致性
===============================================

    python bench_agreement.py bench_out/local_8b/records/llama3_8b/en

先跑 bench_models.py（它會把每篇的編碼存到 bench_out/.../records/），
再用這支把那批編碼放到與參考編碼相同的抽樣框上比較。

抽樣框
------
與介面「信度」頁籤相同：tacit_irr.build_frame 把每份逐字稿切成發言單元，
兩邊的編碼各自以引文比對落到單元上。兩邊用的是**同一份逐字稿文字**，
所以單元切法完全一致，單元編號可以直接對齊。

報什麼
------
  pooled κ、PABAK、Gwet's AC1   所有單元 × 所有碼攤成一張 2×2 表
  precision / recall            以參考編碼為比較基準
  per-code κ                    各碼分開算

參考編碼是與逐字稿一起撰寫的固定比較基準，不是 ground truth。
這裡的數字說明「與該基準的距離」，不是正確率。
"""

import glob
import json
import os
import re
import sys

import tacit_framework as F
import tacit_irr as IRR
import tacit_schema as S


def resp_id(text):
    """'A05 (Chair, ...)' 或 '05_A05_Chair.docx' → 'A05'"""
    # 不能用 \b：檔名是 01_P01_Project-director，底線算字元，\b 對不上
    m = re.search(r"(?<![A-Za-z0-9])([A-Z]\d{2})(?![0-9])", text or "")
    return m.group(1) if m else None


def load_reference():
    out = {}
    for p in sorted(glob.glob(os.path.join("analyses", "demo_en_*.json"))):
        rec = S.migrate_record(json.load(open(p, encoding="utf-8")))
        out[resp_id(rec[S.RESPONDENT]) or resp_id(p)] = rec
    return out


def load_model(folder):
    out = {}
    for p in sorted(glob.glob(os.path.join(folder, "*.json"))):
        rec = S.migrate_record(json.load(open(p, encoding="utf-8")))
        out[resp_id(os.path.basename(p))] = rec
    return out


def coding_by_unit(frame):
    return {u[S.UNIT_ID]: set(u[S.AI_CODES]) for u in frame}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    F.activate_by_id("ri_stilgoe_2013")
    ref = load_reference()
    mod = load_model(argv[0])
    missing = sorted(set(ref) - set(mod))
    if missing:
        print(f"模型缺這些受訪者的編碼：{missing}（缺的單元視為模型未標記）")

    keys = sorted(ref)
    transcripts = {k: ref[k][S.TRANSCRIPT] for k in keys}

    def relabel(recs):
        out = []
        for k in keys:
            if k in recs:
                r = dict(recs[k])
                r[S.RESPONDENT] = k
                out.append(r)
        return out

    ref_frame, ref_diag = IRR.build_frame(relabel(ref), transcripts)
    mod_frame, mod_diag = IRR.build_frame(relabel(mod), transcripts)
    assert [u[S.UNIT_ID] for u in ref_frame] == [u[S.UNIT_ID] for u in mod_frame]

    a, b = coding_by_unit(ref_frame), coding_by_unit(mod_frame)
    units = [u[S.UNIT_ID] for u in ref_frame]
    pooled = IRR.pooled_kappa(a, b, units)
    # 參考編碼為 A、模型為 B：只有 A 標 = 漏標，只有 B 標 = 多標
    tp, fn, fp = pooled[IRR.BOTH], pooled[IRR.ONLY_A], pooled[IRR.ONLY_B]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    unmatched = sum(mod_diag["unmatched_quotes"].values())
    mod_segments = sum(len(r.get(S.SEGMENTS) or []) for r in mod.values())

    result = {
        "model_records": argv[0],
        "units": len(units),
        "reference_unmarked_units": ref_diag["uncoded_units"],
        "model_unmarked_units": mod_diag["uncoded_units"],
        "model_segments": mod_segments,
        "model_quotes_not_located": unmatched,
        "pooled": pooled,
        "precision": None if precision is None else round(precision, 3),
        "recall": None if recall is None else round(recall, 3),
        "exact_set_agreement": IRR.exact_set_agreement(a, b, units),
        "per_code": IRR.per_code_agreement(a, b, units),
    }
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.normpath(argv[0])))), "agreement.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"抽樣框 {len(units)} 單元（參考編碼未標記 {ref_diag['uncoded_units']}，"
          f"模型未標記 {mod_diag['uncoded_units']}）")
    print(f"模型 {mod_segments} 段，其中 {unmatched} 段的引文在逐字稿裡找不到")
    print(f"pooled κ = {pooled[IRR.KAPPA]}  PABAK = {pooled[IRR.PABAK]}  "
          f"AC1 = {pooled[IRR.AC1]}")
    print(f"precision = {result['precision']}  recall = {result['recall']}  "
          f"整組一致 = {result['exact_set_agreement']}")
    for row in result["per_code"]:
        print(f"  {row['code']:6s} κ={row[IRR.KAPPA]}  both={row[IRR.BOTH]} "
              f"ref_only={row[IRR.ONLY_A]} model_only={row[IRR.ONLY_B]}")
    print(f"已寫入 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
