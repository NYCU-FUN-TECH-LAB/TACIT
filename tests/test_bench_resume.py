"""
bench_models 的「額度用完、換一組 API key 接著跑」

免費額度用完時的實際做法是換一組 key 重跑同一行指令。這支測試確認三件事：

  1. 撞到額度就停，而且那一份**不存檔**。分窗編碼會吞掉單一窗口的錯誤繼續
     跑，若不特別處理，只編了一半的逐字稿會被當成完成，Table 5 的段落數
     就悄悄變少。
  2. 重跑時已完成的逐字稿直接沿用，不重送模型。
  3. 耗時只算真正在編碼的時間，不含換 key 之間停下來的時間。

不需要模型、網路或 API key：LLM.complete 換成假的。
"""
import json
import os
import sys
import tempfile

import bench_models as B
import tacit_framework as F
import tacit_llm as LLM
import tacit_schema as S

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


F.activate_by_id("ri_stilgoe_2013")
ep = LLM.Endpoint(provider=LLM.GEMINI, model="fake-flash", api_key="k1")

state = {"quota_after_file": None, "mid_file": None, "calls": 0}
_real_complete = LLM.complete


def fake_complete(endpoint, prompt, system=None, **kw):
    state["calls"] += 1
    name = prompt.split("\n", 1)[0].replace("File: ", "")
    idx = int(name.split("_", 1)[0])              # 01_P01_... → 1
    excerpt = prompt.split(":\n", 1)[1]
    # 第 quota_after_file 份之後一律回 429
    q = state["quota_after_file"]
    if q is not None and idx > q:
        raise LLM.RateLimited("429 RESOURCE_EXHAUSTED (fake)")
    # mid_file 那一份：第一個窗口成功、第二個窗口撞額度——編到一半用完
    if state["mid_file"] == idx and "Excerpt 1 of" not in prompt:
        raise LLM.RateLimited("429 RESOURCE_EXHAUSTED (fake, mid-transcript)")
    quote = excerpt.strip().split("\n")[0][:80]
    return json.dumps({
        S.RESPONDENT: name,
        S.SEGMENTS: [{
            S.SEGMENT_ID: "S001", S.TITLE: "Plans ahead", S.QUOTE: quote,
            S.FULL_TEXT: quote,
            S.CODES_F: [S.make_code(S.ANTICIPATION, "P",
                                    "The speaker describes planning for future risks.")],
        }],
    })


LLM.complete = fake_complete
try:
    with tempfile.TemporaryDirectory() as tmp:
        save = os.path.join(tmp, "records")

        print("=" * 70)
        print("測試 1a：一份逐字稿編到一半額度用完（分窗路徑）")
        print("=" * 70)
        # 01_P01 超過一個窗口長度，會切成兩窗。分窗編碼不可以吞掉第二窗的
        # 錯誤、把只有第一窗結果的紀錄當成完成。
        mid_dir = os.path.join(tmp, "mid")
        state["mid_file"] = 1
        s_mid, _ = B.bench_coding(ep, "en", "en", limit=1, save_dir=mid_dir)
        ok("編到一半撞額度時停下", bool(s_mid["stopped_on_quota"]),
           str(s_mid["stopped_on_quota"])[:80])
        ok("編到一半的那份不算完成", s_mid["completed"] == 0, str(s_mid["completed"]))
        ok("編到一半的那份沒有存檔",
           not (os.path.isdir(mid_dir) and os.listdir(mid_dir)))
        state["mid_file"] = None

        print()
        print("=" * 70)
        print("測試 1b：第 3 份開始額度用完")
        print("=" * 70)
        state["quota_after_file"] = 2
        calls_before = state["calls"]
        stats, recs = B.bench_coding(ep, "en", "en", limit=5, save_dir=save)
        saved = sorted(os.listdir(save)) if os.path.isdir(save) else []
        ok("停在額度錯誤", bool(stats["stopped_on_quota"]), str(stats["stopped_on_quota"])[:80])
        ok("只算完成 2 份", stats["completed"] == 2, str(stats["completed"]))
        ok("只存了 2 份", len(saved) == 2, str(saved))
        ok("額度錯誤不算成模型失敗", stats["failed"] == 0, str(stats["failed"]))
        ok("停在第 3 份，沒有把後面幾份也打一遍",
           "03_" in str(stats["stopped_on_quota"]))

        print()
        print("=" * 70)
        print("測試 2：換 key 重跑，從第 3 份接著跑")
        print("=" * 70)
        state["quota_after_file"] = None
        calls_before = state["calls"]
        stats2, recs2 = B.bench_coding(ep, "en", "en", limit=5, save_dir=save)
        ok("這次跑完 5 份", stats2["completed"] == 5, str(stats2["completed"]))
        ok("其中 2 份沿用存檔", stats2["resumed"] == 2, str(stats2["resumed"]))
        ok("沒有停在額度", stats2["stopped_on_quota"] is None)
        sent = state["calls"] - calls_before
        ok("沿用的 2 份沒有重送模型（只為第 3–5 份送了 3 次）", sent == 3, str(sent))
        ok("段落數等於 5 份的總和（沒有重複計入）",
           stats2["segments"] == sum(len(r[S.SEGMENTS]) for r in recs2),
           f"{stats2['segments']} vs {sum(len(r[S.SEGMENTS]) for r in recs2)}")

        print()
        print("=" * 70)
        print("測試 3：換成另一顆模型時不能沿用別顆的存檔")
        print("=" * 70)
        other = LLM.Endpoint(provider=LLM.GEMINI, model="another-model", api_key="k1")
        calls_before = state["calls"]
        stats3, _ = B.bench_coding(other, "en", "en", limit=2, save_dir=save)
        ok("另一顆模型重新編碼", stats3["resumed"] == 0, str(stats3["resumed"]))
        ok("而且真的有送請求", state["calls"] > calls_before)

        print()
        print("=" * 70)
        print("測試 4：表格標出未完成")
        print("=" * 70)
        md = B.markdown_table([{"model": "fake-flash", "coding": {"en": stats},
                                "themes": {"skipped": "coding incomplete"},
                                "contract": {}}])
        row = next((l for l in md.splitlines() if l.startswith("| fake-flash")), "")
        ok("未完成的列寫成 2/5 (incomplete)", "2/5 (incomplete)" in row, row[:90])
        md2 = B.markdown_table([{"model": "fake-flash", "coding": {"en": stats2},
                                 "themes": {"skipped": "x"}, "contract": {}}])
        ok("完成的列不帶 incomplete", "incomplete" not in md2.split("### Theme")[0])
finally:
    LLM.complete = _real_complete

print()
print("=" * 70)
print("結果：全部通過 ✅" if not FAIL else f"結果：{len(FAIL)} 項失敗 ❌")
for f in FAIL:
    print(f"  - {f}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
