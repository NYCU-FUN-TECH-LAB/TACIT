"""bench_models_summary.py — 把多輪模型編碼的結果彙整成一張表

    python src/bench_models_summary.py
    python src/bench_models_summary.py --no-recompute      # 只讀既有的 agreement.json

每個 bench_out/<run>/ 資料夾是 bench_models.py 的一輪：bench_results.json
記錄段落數、碼數與分鐘數，records/<model>/en/ 是每篇逐字稿的編碼。
這支腳本先用 bench_agreement.py 把每輪的編碼放到與參考編碼相同的抽樣框上
（重算 agreement.json），再依模型端點分組，印出每一欄的中位數與全距。

不呼叫模型，只讀存下來的紀錄，任何時候跑都得到同一個答案。

分組規則：同一個 endpoint 的各輪放在一起。只有一輪的端點單獨列出。
"""
import argparse
import glob
import json
import os
import statistics
import sys

import bench_agreement as BA

RUNS_ROOT = "bench_out"


def run_dirs():
    out = []
    for d in sorted(glob.glob(os.path.join(RUNS_ROOT, "*"))):
        if os.path.isfile(os.path.join(d, "bench_results.json")):
            out.append(d)
    return out


def read_run(d, recompute=True):
    br = json.load(open(os.path.join(d, "bench_results.json"), encoding="utf-8"))
    res = br["results"][0]
    en = res["coding"]["en"]
    rec_dir = glob.glob(os.path.join(d, "records", "*", "en"))
    if not rec_dir:
        return None
    if recompute:
        BA.main([rec_dir[0]])
    ag = json.load(open(os.path.join(d, "agreement.json"), encoding="utf-8"))
    prov = res.get("provenance") or {}
    return {
        "run": os.path.basename(d),
        "endpoint": res["endpoint"],
        "segments": en["segments"],
        "codes": en["codes"],
        "minutes": en["minutes"],
        "precision": ag["precision"],
        "recall": ag["recall"],
        "kappa": ag["pooled"]["kappa"],
        "pabak": ag["pooled"]["pabak"],
        "ac1": ag["pooled"]["ac1"],
        "units": ag["units"],
        "cells": ag["pooled"]["n"],
        "both": ag["pooled"]["both_coded"],
        "only_ref": ag["pooled"]["only_a"],
        "only_model": ag["pooled"]["only_b"],
        "neither": ag["pooled"]["neither_coded"],
        "model_unmarked_units": ag["model_unmarked_units"],
        "not_located": ag["model_quotes_not_located"],
        "on_excluded": ag.get("model_quotes_on_excluded_units", 0),
        "per_code_kappa": [r["kappa"] for r in ag["per_code"] if r["kappa"] is not None],
        "temperature": prov.get("temperature"),
        "num_ctx": prov.get("num_ctx"),
        "recorded_at": prov.get("recorded_at") or res.get("at"),
    }


def fmt(vals, digits=None):
    """中位數（全距）。一輪就直接給那個數字。"""
    vals = [v for v in vals if v is not None]
    if not vals:
        return "-"

    def f(x):
        if digits is None:
            return f"{x:g}"
        return f"{x:.{digits}f}".lstrip("0") if abs(x) < 1 else f"{x:.{digits}f}"

    if len(vals) == 1:
        return f(vals[0])
    return f"{f(statistics.median(vals))} ({f(min(vals))}–{f(max(vals))})"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-recompute", action="store_true",
                    help="不重算 agreement.json，只讀既有的")
    args = ap.parse_args(argv)

    rows = [r for r in (read_run(d, not args.no_recompute) for d in run_dirs()) if r]
    groups = {}
    for r in rows:
        groups.setdefault(r["endpoint"], []).append(r)

    print()
    print(f"{'Endpoint':34s} {'Runs':>4s} {'Segments':>14s} {'Codes':>14s} "
          f"{'Precision':>14s} {'Recall':>14s} {'κ':>14s} {'Minutes':>18s}")
    for ep, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        print(f"{ep:34s} {len(rs):4d} "
              f"{fmt([r['segments'] for r in rs]):>14s} "
              f"{fmt([r['codes'] for r in rs]):>14s} "
              f"{fmt([r['precision'] for r in rs], 2):>14s} "
              f"{fmt([r['recall'] for r in rs], 2):>14s} "
              f"{fmt([r['kappa'] for r in rs], 2):>14s} "
              f"{fmt([r['minutes'] for r in rs], 1):>18s}")

    print()
    print("每輪的細節（抽樣框單元數、格數、四格計數、PABAK、AC1、各碼 κ 的範圍）")
    for r in rows:
        pk = r["per_code_kappa"]
        print(f"  {r['run']:22s} {r['endpoint']:30s} units={r['units']} cells={r['cells']} "
              f"both={r['both']} ref_only={r['only_ref']} model_only={r['only_model']} "
              f"neither={r['neither']} PABAK={r['pabak']} AC1={r['ac1']} "
              f"per-code κ {min(pk):.2f}–{max(pk):.2f}  "
              f"model_unmarked={r['model_unmarked_units']} not_located={r['not_located']} "
              f"on_excluded={r['on_excluded']} T={r['temperature']} ctx={r['num_ctx']} "
              f"at={r['recorded_at']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
