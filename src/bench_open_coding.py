"""
bench_open_coding.py — 開放編碼示範（稿件 §3）
==============================================

    python bench_open_coding.py --corpus hearings --model llama3:8b
    python bench_open_coding.py --corpus hearings --provider gemini --model gemini-3.6-flash
    python bench_open_coding.py --corpus demo --model llama3:8b          合成語料

走與 app 相同的路徑（tacit_open.open_code_transcript，每個窗口重建含碼簿的
提示詞）。碼簿依逐字稿順序累積：第二份看得到第一份建立的碼。順序就是
manifest（或檔名）的順序，寫在 summary 裡，因為碼簿取決於順序。

兩種語料
--------
  hearings  美國國會 AI 治理聽證會（demo_data/hearings，公有領域的真實文本）。
            預設只跑稿件用的 24 人子集（manifest 裡 paper_subset = true）；
            --all 跑全部 80 份。這批語料沒有參考編碼，所以只報碼簿本身。
  demo      合成語料（demo_data/en）。有參考編碼，另外報位置吻合與維度對應。

報什麼
------
  codes_initial        跑完時碼簿裡的碼數
  merge_suggestions    近義碼建議的**全部**筆數（similar_pairs，預設門檻，不截斷）
  codes_after_merge    **全部接受**這些建議後的碼數。工具只建議不自動合併；
                       這個數字模擬「研究者照單全收」，不是分析判斷
  （demo 才有）position_recall / position_precision / mapping

額度用完怎麼辦
--------------
雲端免費額度會中途用完。每編完一份就存紀錄與碼簿進度；撞到額度時那一份
整份不算（碼簿還原到編它之前的狀態），換一組 API key 用同一行指令重跑，
從那一份接著編。

輸出：bench_out/open_coding/（demo）或 bench_out/open_coding_hearings/<model>/
"""
import argparse
import copy
import glob
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict

import bench_models as B
import tacit_framework as F
import tacit_irr as IRR
import tacit_llm as LLM
import tacit_open as OP
import tacit_schema as S

STOP_ERRORS = (LLM.RateLimited.__name__, LLM.NotConfigured.__name__,
               LLM.Unavailable.__name__)


def reference_by_resp():
    out = {}
    for p in glob.glob(os.path.join("analyses", "demo_en_*.json")):
        rec = S.migrate_record(json.load(open(p, encoding="utf-8")))
        out[str(rec[S.RESPONDENT])[:3]] = rec
    return out


def corpus_files(corpus, use_all, limit, per_sector=None):
    """回傳 [(respondent_id, path, descriptors 或 None)]，順序即編碼順序。"""
    if corpus == "demo":
        files = sorted(glob.glob(os.path.join("demo_data", "en", "*.docx")))
        out = [(os.path.basename(p).split("_")[1], p, None) for p in files]
    else:
        man = json.load(open(os.path.join("demo_data", "hearings", "manifest.json"),
                             encoding="utf-8"))
        rows = [r for r in man["respondents"] if use_all or r.get("paper_subset")]
        if per_sector:
            # 雲端免費額度跑不完 24 份時用：每個部門取子集裡的前 N 位（manifest 順序），
            # 所以 12 人子集一定是 24 人子集的一部分，兩顆模型可以在同一批人上比較。
            seen, kept = Counter(), []
            for r in rows:
                s = r["descriptors"]["institution_type"]
                if seen[s] < per_sector:
                    kept.append(r); seen[s] += 1
            rows = kept
        out = [(r["respondent_id"], os.path.join("demo_data", "hearings", "en", r["file"]),
                r["descriptors"]) for r in rows]
    return out[:limit] if limit else out


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--corpus", default="demo", choices=["demo", "hearings"])
    ap.add_argument("--all", action="store_true", help="hearings：跑全部 80 份而不是 24 人子集")
    ap.add_argument("--model", default="llama3:8b")
    ap.add_argument("--provider", default=LLM.OLLAMA, choices=LLM.PROVIDERS)
    ap.add_argument("--api-key", default=os.environ.get("TACIT_API_KEY", ""))
    ap.add_argument("--num-ctx", type=int, default=LLM.DEFAULT_NUM_CTX)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--per-sector", type=int, default=None,
                    help="hearings：每個部門只取子集裡的前 N 位（3 → 12 人）")
    ap.add_argument("--analyse-only", action="store_true",
                    help="不呼叫模型，從上次存下的紀錄與碼簿重算合併與對應")
    ap.add_argument("--tag", default="",
                    help="輸出資料夾加上的後綴。同一顆模型要跑第二輪對照時用，"
                         "免得蓋掉上一輪的紀錄（續跑也是看這個資料夾）")
    a = ap.parse_args(argv)

    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", a.model)
    if a.tag:
        safe += "_" + re.sub(r"[^A-Za-z0-9._-]+", "_", a.tag)
    out_dir = (os.path.join("bench_out", "open_coding") if a.corpus == "demo"
               else os.path.join("bench_out", "open_coding_hearings", safe))
    rec_dir = os.path.join(out_dir, "records")
    os.makedirs(rec_dir, exist_ok=True)
    progress_path = os.path.join(out_dir, "codebook_progress.json")
    initial_path = os.path.join(out_dir, "codebook_initial.json")

    # 批次腳本要比介面更有耐心：一次尖峰讓整批停下來，代價是人要回來重下指令。
    LLM.set_retry_delays(5, 15, 40, 90)
    F.activate_by_id("ri_stilgoe_2013")      # 開放編碼不讀它；只是讓 schema 有個作用中框架
    ep = LLM.Endpoint(provider=a.provider, model=a.model, api_key=a.api_key,
                      num_ctx=a.num_ctx)
    files = corpus_files(a.corpus, a.all, a.limit, a.per_sector)
    cb = OP.new_codebook(language="en")
    open_records, seconds, failed, stopped = [], 0.0, [], None

    if a.analyse_only:
        cb = OP.load_codebook(initial_path)
        prev = json.load(open(os.path.join(out_dir, "summary.json"), encoding="utf-8"))
        seconds = prev["coding_minutes"] * 60
        failed = prev.get("failed") or []
        for rid, _, _ in files:
            with open(os.path.join(rec_dir, rid + ".json"), encoding="utf-8") as f:
                open_records.append(json.load(f))
        todo = []
    else:
        # 接續：已編完的逐字稿沿用存檔，碼簿從進度檔載回
        done = {}
        if os.path.isfile(progress_path):
            for rid, _, _ in files:
                p = os.path.join(rec_dir, rid + ".json")
                if os.path.isfile(p):
                    done[rid] = json.load(open(p, encoding="utf-8"))
                else:
                    break                      # 順序有意義：只沿用開頭連續完成的那一段
            if done:
                cb = OP.load_codebook(progress_path)
                print(f"（沿用已完成的 {len(done)} 份與它們累積的碼簿 {len(cb[OP.CODES])} 碼）")
        for rid, _, _ in files:
            if rid in done:
                open_records.append(done[rid])
                seconds += float((done[rid].get("_bench") or {}).get("seconds") or 0)
        todo = [f for f in files if f[0] not in done]
        print(f"{a.corpus}：{len(files)} 份，待編 {len(todo)} 份，端點 {ep.describe()}")

    for rid, path, desc in todo:
        transcript = B.read_docx(path)
        snapshot = copy.deepcopy(cb)

        def code_open(text, n, total, _name=os.path.basename(path), _tr=transcript):
            sysmsg = OP.build_open_prompt(cb, "en", _tr, corpus_term="interview transcript")
            out = LLM.complete(ep, f"File: {_name}\n\nExcerpt {n + 1} of {total}:\n{text}",
                               system=sysmsg, temperature=0.2, json_mode=True)
            js = LLM._extract_first_json(out)
            if not js:
                raise ValueError("no JSON in response")
            return LLM.loads_lenient(js.replace("\r\n", "\n").replace("\r", "\n"))

        t0 = time.time()
        rec = OP.open_code_transcript(transcript, code_open, cb)
        took = time.time() - t0
        errs = rec[S.META].get("chunk_errors") or []
        quota = [e for e in errs if e["error"].startswith(STOP_ERRORS)]
        if quota:
            # 服務端的問題不是模型行為：這一份只編了一部分，不能算完成；
            # 它已經寫進碼簿的碼也要退回去，否則下一輪接續時碼簿是髒的。
            cb.clear(); cb.update(snapshot)
            err = quota[0]["error"]
            stopped = f"{rid}: {err[:200]}"
            # 額度與滿載要分開講。混在一起的代價是使用者白換一組金鑰——
            # 滿載時換金鑰完全沒有用，該做的是等或換模型。
            if err.startswith(LLM.Unavailable.__name__):
                what = (f"服務端暫時無法回應（滿載），停在 {rid}。"
                        f"\n    這**不是**你的額度用完，換一組 API key 沒有用。"
                        f"\n    等幾分鐘後用同一行指令重跑，或改用別的模型"
                        f"（例如 --model gemini-3.7-flash）。")
            else:
                what = (f"額度用完或缺少設定，停在 {rid}。"
                        f"\n    換一組**不同專案**的 API key 後用同一行指令重跑。")
            print(f"\n  ■ {what}\n    已完成 {len(open_records)} 份已存檔，重跑會從這一份接著編。"
                  f"\n    {stopped}", file=sys.stderr)
            break
        seconds += took
        rec[S.RESPONDENT] = rid
        rec[S.TRANSCRIPT] = transcript
        if desc:
            rec[S.DESCRIPTORS] = {**S.blank_descriptors(), **desc}
        rec["_bench"] = {"seconds": round(took, 1), "chars": len(transcript)}
        if errs:
            failed.append({"respondent": rid, "errors": errs})
        open_records.append(rec)
        with open(os.path.join(rec_dir, rid + ".json"), "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        OP.save_codebook(cb, progress_path)
        ch = rec[S.META]["chunking"]
        print(f"  ✓ {rid}  {len(transcript):>6,} 字元  {ch['n_ok']}/{ch['n_chunks']} 窗  "
              f"{len(rec[OP.OPEN_SEGMENTS]):>3} 段  碼簿 {len(cb[OP.CODES]):>3} 碼  {took:.0f}s"
              + (f"  ! {len(errs)} 窗口失敗" if errs else ""), flush=True)

    if stopped:
        return 3
    if not a.analyse_only:
        OP.save_codebook(cb, initial_path)
    stats_initial = OP.codebook_stats(cb)
    n_windows = sum((r[S.META].get("chunking") or {}).get("n_chunks", 0) for r in open_records)
    n_windows_ok = sum((r[S.META].get("chunking") or {}).get("n_ok", 0) for r in open_records)

    # ---- 近義碼：全部接受建議 ----
    pairs = OP.similar_pairs(cb, limit=None)   # 量測不能用顯示上限
    merged_away = set()
    for p in pairs:
        if p["a"] in merged_away or p["b"] in merged_away:
            continue
        keep, drop = ((p["a"], p["b"]) if p["a_count"] >= p["b_count"] else (p["b"], p["a"]))
        OP.merge_codes(cb, keep, [drop], records=open_records, reviewer="bench: accept all")
        merged_away.add(drop)
    OP.save_codebook(cb, os.path.join(out_dir, "codebook_merged.json"))
    stats_merged = OP.codebook_stats(cb)

    summary = {
        "corpus": a.corpus, "model": ep.describe(),
        "provenance": ep.provenance(temperature=0.2),
        "order": [rid for rid, _, _ in files],
        "transcripts": len(open_records),
        "chars": sum(len(r.get(S.TRANSCRIPT) or "") for r in open_records),
        "windows": n_windows, "windows_ok": n_windows_ok,
        "transcripts_with_chunk_errors": len(failed),
        "coding_minutes": round(seconds / 60, 1),
        "open_segments": sum(len(r[OP.OPEN_SEGMENTS]) for r in open_records),
        "codes_initial": stats_initial["codes"],
        "applications_initial": stats_initial["applications"],
        "singletons_initial": stats_initial["singletons"],
        "merge_suggestions": len(pairs),
        "codes_after_merge": stats_merged["codes"],
        "saturation": OP.saturation_curve(open_records),
        "top_codes": [{"label": c[OP.CODE_LABEL], "count": c[OP.CODE_COUNT]}
                      for c in sorted(cb[OP.CODES], key=lambda c: -c[OP.CODE_COUNT])[:25]],
        "failed": failed,
    }

    if a.corpus == "demo":
        summary.update(map_to_reference(open_records, cb))

    with open(os.path.join(out_dir, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    show = {k: v for k, v in summary.items()
            if k not in ("codes", "failed", "saturation", "order", "top_codes", "provenance")}
    print("\n" + json.dumps(show, ensure_ascii=False, indent=2))
    print("最常用的碼：" + "; ".join(f"{c['label'][:40]} ({c['count']})"
                                for c in summary["top_codes"][:10]))
    print(f"已寫入 {out_dir}/summary.json")
    return 0


def map_to_reference(open_records, cb):
    """合成語料專用：位置吻合與維度對應（在參考編碼的發言單元上）。"""
    ref = reference_by_resp()
    unit_ref, unit_open = {}, defaultdict(set)
    for rec in open_records:
        rid = rec[S.RESPONDENT]
        rrec = ref.get(rid) or {}
        # 單元要用參考編碼存的逐字稿來切，抽樣框才會與 bench_agreement、
        # 介面「信度」頁籤與稿件的 299 個單元是同一個。
        units = IRR.split_units(rrec.get(S.TRANSCRIPT) or rec[S.TRANSCRIPT])
        norm_units = [IRR.normalize(u[S.TEXT]) for u in units]
        ref_ex = [(IRR.normalize(sg.get(S.FULL_TEXT) or sg.get(S.QUOTE) or ""),
                   {S.split_code(c)[0] for c in S.codes_of(sg)})
                  for sg in (rrec.get(S.SEGMENTS) or [])]
        for k, un in enumerate(norm_units):
            dims = set()
            for ex, ds in ref_ex:
                if IRR._overlaps(un, ex):
                    dims |= ds
            unit_ref[(rid, k)] = dims
        for seg in rec[OP.OPEN_SEGMENTS]:
            ex = IRR.normalize(seg.get(S.FULL_TEXT) or seg.get(S.QUOTE) or "")
            hit = [k for k, un in enumerate(norm_units) if IRR._overlaps(un, ex)]
            for c in seg.get(OP.OPEN_CODES) or []:
                for k in hit:
                    unit_open[(rid, k)].add(c[OP.CODE_ID])

    ref_marked = {u for u, d in unit_ref.items() if d}
    open_marked = {u for u, c in unit_open.items() if c}
    both = ref_marked & open_marked
    per_code_units = defaultdict(set)
    for u, cs in unit_open.items():
        for c in cs:
            per_code_units[c].add(u)
    mapping, detail = Counter(), []
    for code in cb[OP.CODES]:
        cid = code[OP.CODE_ID]
        units = per_code_units.get(cid, set())
        kind, dim = "unlocated", None
        if units:
            dims = Counter(d for u in units for d in unit_ref[u])
            if not sum(1 for u in units if unit_ref[u]):
                kind = "outside"
            else:
                dim, top = dims.most_common(1)[0]
                kind = "mapped" if top / len(units) > 0.5 else "mixed"
                dim = dim if kind == "mapped" else None
        mapping[kind] += 1
        detail.append({"code_id": cid, "label": code[OP.CODE_LABEL],
                       "count": code[OP.CODE_COUNT], "units": len(units),
                       "kind": kind, "dimension": dim})
    return {
        "frame_units": len(unit_ref),
        "reference_marked_units": len(ref_marked),
        "open_marked_units": len(open_marked),
        "position_recall": round(len(both) / len(ref_marked), 3) if ref_marked else None,
        "position_precision": round(len(both) / len(open_marked), 3) if open_marked else None,
        "mapping": dict(mapping),
        "mapped_by_dimension": dict(Counter(d["dimension"] for d in detail
                                            if d["kind"] == "mapped")),
        "codes": detail,
    }


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
