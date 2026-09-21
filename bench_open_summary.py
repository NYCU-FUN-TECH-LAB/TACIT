"""bench_open_summary.py — 把 bench_open_coding 的多輪結果彙整成一張表

    python bench_open_summary.py

為什麼需要它
------------
開放編碼跑一輪得到的碼數**不是一個穩定的量**。同一顆模型、同一批逐字稿、
同一個順序、同一個溫度，兩輪可以差 1.6 倍（實測 flash-lite 在 12 份聽證會
逐字稿上跑出 143 與 89 個碼）。單獨報一輪的數字，報的是那一次採樣，不是
模型或工具的性質。

所以稿件報的是**多輪的中位數與全距**，這支腳本就是產生那個數字的地方。
近義建議的筆數與「全部接受後的碼數」在這裡從存下來的碼簿重算，
用的是 similar_pairs(limit=None)——預設的 40 是畫面上的顯示上限，不是數量。

不呼叫模型，只讀存下來的碼簿與紀錄，任何時候跑都得到同一個答案。

資料夾命名：<模型>_<逐字稿份數>_run<N>。同一個（模型，份數）的各輪會被
放在同一組彙整。
"""
import argparse
import copy
import glob
import json
import os
import statistics
import sys

import tacit_framework as F
import tacit_open as OP

HEARINGS = os.path.join("bench_out", "open_coding_hearings")

# 不是量測的資料夾。彙整只該包含同一份程式跑出來的輪次：把別的東西放進
# 同一組算中位數，會把程式之間的差異混進同一份程式的採樣變異裡。
EXCLUDE = {
    "fake-smoke": "測試用的假模型輸出，不是量測",
}


def accept_all_merges(cb0):
    """模擬研究者把每一筆近義建議都接受。回傳 (建議筆數, 合併後的碼數)。"""
    pairs = OP.similar_pairs(cb0, limit=None)
    cb = copy.deepcopy(cb0)
    gone = set()
    for p in pairs:
        if p["a"] in gone or p["b"] in gone:
            continue
        keep, drop = ((p["a"], p["b"]) if p["a_count"] >= p["b_count"]
                      else (p["b"], p["a"]))
        OP.merge_codes(cb, keep, [drop], reviewer="summary: accept all")
        gone.add(drop)
    return len(pairs), OP.codebook_stats(cb)["codes"]


def read_run(d):
    """讀一輪的結果。merge 相關的數字一律重算，不信 summary.json 裡的。"""
    base = os.path.join(HEARINGS, d)
    sm_path = os.path.join(base, "summary.json")
    cb_path = os.path.join(base, "codebook_initial.json")
    if not (os.path.isfile(sm_path) and os.path.isfile(cb_path)):
        return None
    sm = json.load(open(sm_path, encoding="utf-8"))
    cb0 = OP.load_codebook(cb_path)
    n_pairs, after = accept_all_merges(cb0)
    codes = len(cb0[OP.CODES])
    # 集中度：用得最多的兩個碼佔了全部標記的幾成。
    #
    # 單次碼佔比只抓得到「碼簿爆開」這一種失敗。同一顆 llama3:8b 在 24 份
    # 逐字稿上跑出 352 個碼、九成只出現一次；在其中 12 份上卻有輪次只跑出
    # 11 個碼、只有 1 個單次碼——看起來漂亮，其實是塌縮："Defining the Topic"
    # 與 "Sharing Relevant Experience" 兩個泛用標籤吃掉三分之二的標記，碼簿對
    # 內容什麼都沒說。兩個指標要一起看。
    counts = sorted((c[OP.CODE_COUNT] for c in cb0[OP.CODES]), reverse=True)
    top2 = sum(counts[:2]) / max(sum(counts), 1)
    return {
        "top2_share": top2,
        "dir": d,
        "model": sm["model"],
        "transcripts": sm["transcripts"],
        "windows": sm["windows"],
        "windows_ok": sm["windows_ok"],
        "segments": sm["open_segments"],
        "codes": codes,
        "singletons": sm["singletons_initial"],
        "applications": sm["applications_initial"],
        "minutes": sm["coding_minutes"],
        "suggestions": n_pairs,
        "after_merge": after,
    }


def fmt_range(vals):
    """中位數（全距）。一輪就直接給那個數字。"""
    if not vals:
        return "-"
    if len(vals) == 1:
        return f"{vals[0]:g}"
    return f"{statistics.median(vals):g} ({min(vals):g}–{max(vals):g})"


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*", default=None,
                    help="只看這幾個輸出資料夾")
    ap.add_argument("--everything", action="store_true",
                    help="連 EXCLUDE 裡的也列出來（不同程式版本、測試產物）")
    a = ap.parse_args(argv)

    F.activate_by_id("ri_stilgoe_2013")
    dirs = sorted(os.path.basename(p) for p in glob.glob(os.path.join(HEARINGS, "*"))
                  if os.path.isdir(p))
    if a.only:
        dirs = [d for d in dirs if d in a.only]
    elif not a.everything:
        skipped = [(d, EXCLUDE[d]) for d in dirs if d in EXCLUDE]
        dirs = [d for d in dirs if d not in EXCLUDE]
        if skipped:
            print("不列入彙整（--everything 可以看全部）：")
            for d, why in skipped:
                print(f"  {d:<38} {why}")
            print()

    runs = [r for r in (read_run(d) for d in dirs) if r]
    if not runs:
        print("bench_out/open_coding_hearings/ 下面沒有跑完的結果")
        return 1

    print("=" * 108)
    print("每一輪")
    print("=" * 108)
    hdr = (f"{'輸出資料夾':<38} {'份':>3} {'窗口':>8} {'段落':>5} {'碼':>5} "
           f"{'單次':>5} {'單次%':>6} {'前2碼%':>7} {'碼/段':>6} {'建議':>5} {'合併後':>6} {'分鐘':>6}")
    print(hdr)
    print("-" * 108)
    for r in runs:
        print(f"{r['dir']:<38} {r['transcripts']:>3} "
              f"{r['windows_ok']:>4}/{r['windows']:<3} {r['segments']:>5} "
              f"{r['codes']:>5} {r['singletons']:>5} "
              f"{r['singletons'] / max(r['codes'], 1):>5.0%} "
              f"{r['top2_share']:>6.0%} "
              f"{r['applications'] / max(r['segments'], 1):>6.2f} "
              f"{r['suggestions']:>5} {r['after_merge']:>6} {r['minutes']:>6.1f}")

    # 依 (模型, 份數) 分組，同一組的多輪報中位數與全距
    groups = {}
    for r in runs:
        groups.setdefault((r["model"], r["transcripts"]), []).append(r)
    print()
    print("=" * 108)
    print("同一個模型與語料的多輪：中位數（全距）")
    print("=" * 108)
    for (model, n), rs in sorted(groups.items(), key=lambda kv: (-kv[0][1], kv[0][0])):
        print(f"\n{model}  —  {n} 份逐字稿，{len(rs)} 輪")
        for label, key, pct in [
            ("段落數", "segments", False),
            ("碼數", "codes", False),
            ("只出現一次", "singletons", False),
            ("近義建議筆數", "suggestions", False),
            ("全部接受後的碼數", "after_merge", False),
            ("分鐘", "minutes", False),
        ]:
            print(f"  {label:<14} {fmt_range([r[key] for r in rs])}")
        share = [r["singletons"] / max(r["codes"], 1) for r in rs]
        print(f"  {'單次碼佔比':<13} "
              f"{statistics.median(share):.0%} "
              f"({min(share):.0%}–{max(share):.0%})" if len(share) > 1
              else f"  {'單次碼佔比':<13} {share[0]:.0%}")
        t2 = [r["top2_share"] for r in rs]
        print(f"  {'前兩個碼佔標記':<11} " + (f"{statistics.median(t2):.0%} ({min(t2):.0%}–{max(t2):.0%})"
                                          if len(t2) > 1 else f"{t2[0]:.0%}"))
        if len(rs) > 1:
            lo, hi = min(r["codes"] for r in rs), max(r["codes"] for r in rs)
            print(f"  → 碼數的輪間差異：{hi / max(lo, 1):.2f} 倍"
                  f"（同一模型、同一語料、同一順序）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
