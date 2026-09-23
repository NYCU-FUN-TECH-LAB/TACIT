"""
bench_yield.py — 整份一次送 vs 分窗：產出量對照
================================================

    python bench_yield.py --model llama3:8b

稿件 §2.4 的主張是：整份逐字稿塞進一個提示詞不會明顯出錯，而是**產出量
崩掉**——JSON 格式正確，段落卻少得多。這支腳本把那句話變成可重跑的數字。

設計
----
把幾份示範逐字稿接成一份長文件，用同一顆模型、同一份編碼提示詞跑兩種方式：

  single    整份一次送（app 裡關掉分窗時的行為）
  windowed  切成重疊窗口逐段編碼再合併（app 的預設）

**文件長度刻意控制在模型的原生 context 以內。** 否則「一次送」量到的是模型
讀超過訓練長度的文字，那是另一個問題，不是分窗要解決的問題。預設上限
14,000 字元，約 3,500 token，加上約 2,100 token 的提示詞與輸出保留，
仍在 llama3:8b 的 8,192 token 之內。

每種方式跑 --runs 次（預設 3），報中位數與範圍。參考編碼在同幾份逐字稿
上的段落數一併列出，當作「這份文件裡大約有多少可編的東西」的尺度。

輸出：bench_out/yield/yield.json
"""
import argparse
import glob
import json
import os
import statistics
import sys
import time

import bench_models as B
import tacit_coding as CH
import tacit_framework as F
import tacit_llm as LLM
import tacit_schema as S

OUT = os.path.join("bench_out", "yield")


def resp_id(path):
    return os.path.basename(path).split("_")[1]          # 07_A01_... → A01


def build_document(max_chars, prefix):
    files = [p for p in sorted(glob.glob(os.path.join("demo_data", "en", "*.docx")))
             if resp_id(p).startswith(prefix)]
    parts, used, total = [], [], 0
    for p in files:
        text = B.read_docx(p)
        if total + len(text) > max_chars and parts:
            break
        parts.append(text)
        used.append(resp_id(p))
        total += len(text)
    return "\n\n".join(parts), used


def reference_segments(ids):
    n = 0
    for p in glob.glob(os.path.join("analyses", "demo_en_*.json")):
        rec = json.load(open(p, encoding="utf-8"))
        if any(str(rec.get(S.RESPONDENT, "")).startswith(i) for i in ids):
            n += len(rec.get(S.SEGMENTS) or [])
    return n


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="llama3:8b")
    ap.add_argument("--provider", default=LLM.OLLAMA, choices=LLM.PROVIDERS)
    ap.add_argument("--num-ctx", type=int, default=8192)
    ap.add_argument("--max-chars", type=int, default=14000)
    ap.add_argument("--group", default="A", help="用哪一組受訪者（A/G/N/P）")
    ap.add_argument("--runs", type=int, default=3)
    a = ap.parse_args(argv)

    os.makedirs(OUT, exist_ok=True)
    F.activate_by_id("ri_stilgoe_2013")
    fw = F.active()
    doc, ids = build_document(a.max_chars, a.group)
    ep = LLM.Endpoint(provider=a.provider, model=a.model,
                      api_key=os.environ.get("TACIT_API_KEY", ""), num_ctx=a.num_ctx)
    sysmsg = B.build_system_prompt(fw, "en", doc)
    print(f"文件：{', '.join(ids)}，{len(doc):,} 字元；"
          f"提示詞約 {LLM.estimate_tokens(sysmsg):,} token；num_ctx {a.num_ctx}")

    def code_one(text, n, total):
        raw = LLM.complete(ep, f"File: combined.docx\n\nExcerpt {n + 1} of {total}:\n{text}",
                           system=sysmsg, temperature=0.2, json_mode=True)
        js = LLM._extract_first_json(raw)
        if not js:
            raise ValueError("no JSON in response")
        return S.migrate_record(json.loads(js))

    runs = {"single": [], "windowed": []}
    for r in range(a.runs):
        for mode in ("single", "windowed"):
            t0 = time.time()
            try:
                if mode == "single":
                    rec = code_one(doc, 0, 1)
                    n, err = len(rec.get(S.SEGMENTS) or []), None
                else:
                    merged = CH.code_transcript(doc, code_one)
                    errs = (merged[S.META].get("chunk_errors") or [])
                    n, err = len(merged.get(S.SEGMENTS) or []), (errs or None)
            except Exception as e:                             # noqa: BLE001
                n, err = None, f"{type(e).__name__}: {e}"
            took = round(time.time() - t0, 1)
            runs[mode].append({"segments": n, "seconds": took, "error": err})
            print(f"  run {r + 1} {mode:8s} → {n} 段  {took}s"
                  + (f"  ! {str(err)[:120]}" if err else ""), flush=True)

    def summary(rows):
        vals = [x["segments"] for x in rows if x["segments"] is not None]
        return {"median": statistics.median(vals) if vals else None,
                "min": min(vals) if vals else None, "max": max(vals) if vals else None,
                "ok_runs": len(vals)}

    result = {"model": ep.describe(), "num_ctx": a.num_ctx, "respondents": ids,
              "chars": len(doc), "prompt_tokens_est": LLM.estimate_tokens(sysmsg),
              "reference_segments": reference_segments(ids),
              "single": summary(runs["single"]), "windowed": summary(runs["windowed"]),
              "runs": runs}
    with open(os.path.join(OUT, "yield.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"\n參考編碼：{result['reference_segments']} 段")
    print(f"single   中位數 {result['single']['median']}（{result['single']['min']}–{result['single']['max']}）")
    print(f"windowed 中位數 {result['windowed']['median']}（{result['windowed']['min']}–{result['windowed']['max']}）")
    print(f"已寫入 {OUT}/yield.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
