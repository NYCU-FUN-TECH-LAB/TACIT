"""
驗證 tacit_coding.py：切窗、合併、去重、產出量檢查。

要防的失效（實測）：一份 46,730 字元的訪談逐字稿整份送給 qwen2.5:7b，
回傳 **4 個編碼段落——四個維度剛好各一個**。同一位研究者對一份 21,569
字元的中文稿人工編碼，用螢光筆標出 30 段（反思 11、預期 7、參與 7、
回應 5）。4 段對 30 段，而且畫面上沒有任何跡象顯示這份分析漏掉了大半。

這支測試守住三件事：
  1. 切窗不會切壞引文（引文必須逐字對得回原文，這是工具的核心保證）
  2. 重疊區的重複要被合併掉，但真正的多重編碼不能被誤殺
  3. 那個「每個維度剛好一段」的形狀要被認出來
"""
import sys

import tacit_coding as CH
import tacit_framework as F
import tacit_schema as S

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def eq(label, got, want):
    ok(label, got == want, f"got={got!r} want={want!r}" if got != want else "")


def seg(sid, quote, codes, full=None, title="t"):
    return {S.SEGMENT_ID: sid, S.TITLE: title, S.QUOTE: quote,
            S.FULL_TEXT: full if full is not None else quote,
            S.CODES_F: [S.make_code(d, p) for d, p in codes]}


# 造一份長逐字稿：24 個發言輪次，每輪約 900 字元
TURNS = [f"【受訪者】第{i}輪的發言。" + f"這是第{i}輪的內容，談的是法規遵循與"
         f"跨部門協調的實際做法。" * 18 for i in range(1, 25)]
LONG = "\n".join(TURNS)

print("=" * 70)
print("測試 1：切窗")
print("=" * 70)
print(f"  逐字稿長度 {len(LONG)} 字元，{len(TURNS)} 個發言輪次")
chunks = CH.split_transcript(LONG, window=3000, overlap=300)
ok("長稿被切成多個窗口", len(chunks) > 1, f"{len(chunks)} 個")
ok("每個窗口都不超過窗口上限（單一超長輪次除外）",
   all(len(c) <= 3000 or "\n" not in c for _, c in chunks),
   str([len(c) for _, c in chunks]))
ok("每個窗口都有內容", all(c.strip() for _, c in chunks))

# 引文可回溯是核心保證：任何窗口裡的任何一句，都必須逐字出現在原文裡
_bad = [c[:60] for _, c in chunks if c.split("\n")[0] not in LONG]
ok("窗口內容逐字來自原文（引文才對得回去）", not _bad, str(_bad))

# 每一個發言輪次都必須至少完整出現在某一個窗口裡，否則就是漏讀
_missed = [i for i, tn in enumerate(TURNS)
           if not any(tn in c for _, c in chunks)]
ok("沒有任何發言輪次被漏掉", not _missed, f"漏掉第 {_missed} 輪")

# 重疊：相鄰窗口要有共同內容，橫跨切點的段落才有機會完整被看到一次
_ovl = sum(1 for a, b in zip(chunks, chunks[1:])
           if set(a[1].split("\n")) & set(b[1].split("\n")))
ok("相鄰窗口有重疊", _ovl == len(chunks) - 1, f"{_ovl}/{len(chunks) - 1}")

print()
print("=" * 70)
print("測試 2：短稿不切、空稿不炸")
print("=" * 70)
ok("短稿維持單一窗口", len(CH.split_transcript("很短的一段話", 3000, 300)) == 1)
ok("空字串回空清單", CH.split_transcript("", 3000, 300) == [])
ok("None 不炸", CH.split_transcript(None, 3000, 300) == [])
ok("只有空白也回空清單", CH.split_transcript("   \n\n  \n", 3000, 300) == [])

# 單一發言輪次就超過一個窗口（受訪者一口氣講五分鐘，訪談稿常見）
_mono = "受訪者連續講了很久。" * 800          # 約 8,000 字元、一行
_mc = CH.split_transcript(_mono, 3000, 300)
ok("超長單輪也會被切開", len(_mc) > 1, f"{len(_mc)} 個")
ok("超長單輪切在句末，不切在句子中間",
   all(c.rstrip().endswith(("。", "！", "？")) for _, c in _mc[:-1]),
   str([c[-6:] for _, c in _mc[:-1]]))

print()
print("=" * 70)
print("測試 3：合併與去重")
print("=" * 70)
F.reset()
# 重疊區造成的重複：同一句話、同一個碼，在兩個窗口各出現一次
g1 = [seg("S001", "我們會先開會確認", [(S.REFLEXIVITY, "N")]),
      seg("S002", "定案之後再跟他們說明", [(S.ENGAGEMENT, "N")])]
g2 = [seg("S001", "我們會先開會確認", [(S.REFLEXIVITY, "N")]),
      seg("S002", "這個趨勢一定會走到那裡", [(S.ANTICIPATION, "N")])]
m = CH.merge_segments([g1, g2])
ok("重複的段落被合併掉", len(m) == 3, f"{len(m)} 段：{[s[S.QUOTE][:8] for s in m]}")
ok("合併後重新編號", [s[S.SEGMENT_ID] for s in m] == ["S001", "S002", "S003"],
   str([s[S.SEGMENT_ID] for s in m]))

# 同一句話被兩個窗口判成**不同維度**。合併成一段並帶兩個碼——留成兩筆
# 引文相同的段落會灌水段落總數，而且共現分析會把「同一段話支持兩個維度」
# 這個事實抹掉。但合併等於製造了一個共現關係，所以必須留下依據。
g3 = [seg("S001", "我們最懂這個技術", [(S.REFLEXIVITY, "N")])]
g4 = [seg("S001", "我們最懂這個技術", [(S.RESPONSIVENESS, "N")])]
m2 = CH.merge_segments([g3, g4])
ok("同句被合併成一段，不留兩筆相同引文", len(m2) == 1, f"{len(m2)} 段")
ok("兩邊的碼都保留下來",
   sorted(S.codes_of(m2[0])) == ["REF-N", "RES-N"], str(S.codes_of(m2[0])))
_h = (m2[0].get(S.REVIEW) or {}).get(S.HISTORY) or []
ok("併碼留下稽核紀錄（共現是分窗的產物，不能靜悄悄產生）",
   any(e.get("action") == CH.MERGE_ACTION and "RES-N" in e.get("detail", "")
       for e in _h), str(_h))
ok("併碼前的原始編碼被記下來",
   (m2[0].get(S.REVIEW) or {}).get(S.ORIGINAL_CODES) == ["REF-N"],
   str((m2[0].get(S.REVIEW) or {}).get(S.ORIGINAL_CODES)))
# 完全相同的重複（同引文同碼）不該留下併碼紀錄——那會讓稽核紀錄充滿雜訊
_same = CH.merge_segments([[seg("S001", "一模一樣", [(S.REFLEXIVITY, "N")])],
                           [seg("S001", "一模一樣", [(S.REFLEXIVITY, "N")])]])
ok("單純的重複不留併碼紀錄",
   not ((_same[0].get(S.REVIEW) or {}).get(S.HISTORY) or []),
   str(_same[0].get(S.REVIEW)))

# 一邊只抓到半句、另一邊抓到整句：留下比較完整的原文
g5 = [seg("S001", "我們會先開會確認鑰匙由誰", [(S.REFLEXIVITY, "N")], full="短的")]
g6 = [seg("S001", "我們會先開會確認鑰匙由誰保管，再辦理後續", [(S.REFLEXIVITY, "N")],
          full="我們會先開會確認鑰匙由誰保管，再辦理後續的手續")]
m3 = CH.merge_segments([g5, g6])
ok("重複時留下比較完整的引文與原文",
   len(m3) == 1 and m3[0][S.QUOTE] == "我們會先開會確認鑰匙由誰保管，再辦理後續"
   and "後續的手續" in m3[0][S.FULL_TEXT],
   f"{len(m3)} 段 / {m3[0][S.QUOTE]}")
# 太短的引文在任何段落裡都找得到，包含關係不代表同一段話
g5s = [seg("S001", "很久", [(S.REFLEXIVITY, "N")])]
g6s = [seg("S001", "我們等了很久才拿到鑰匙", [(S.ANTICIPATION, "N")])]
ok("過短的引文不因被包含而合併",
   len(CH.merge_segments([g5s, g6s])) == 2, str(len(CH.merge_segments([g5s, g6s]))))

# 標點與空白不同不該讓同一句話被算成兩段
g7 = [seg("S001", "我們 會先 開會確認。", [(S.REFLEXIVITY, "N")])]
g8 = [seg("S001", "我們會先開會確認", [(S.REFLEXIVITY, "N")])]
ok("標點與空白差異不影響去重", len(CH.merge_segments([g7, g8])) == 1)
ok("空引文被丟掉（無法回溯的段落沒有用）",
   len(CH.merge_segments([[seg("S001", "", [(S.REFLEXIVITY, "N")])]])) == 0)
ok("空輸入不炸", CH.merge_segments([]) == [] and CH.merge_segments([None]) == [])

print()
print("=" * 70)
print("測試 4：屬性與受訪者名稱的合併")
print("=" * 70)
# 屬性通常只在稿件開頭的自我介紹裡說一次，只有第一個窗口讀得到；
# 其他窗口照規則會填 unspecified。多數決會讓 unspecified 贏——那就等於
# 切窗把屬性全部弄丟。
d = CH.merge_descriptors([
    {"institution_type": "industry", "role_level": S.UNSPECIFIED,
     S.DESCRIPTOR_BASIS: "他說自己在產業界"},
    {"institution_type": S.UNSPECIFIED, "role_level": S.UNSPECIFIED},
    {"institution_type": S.UNSPECIFIED, "role_level": "senior_management"},
])
ok("第一個非 unspecified 的值勝出（不是多數決）",
   d["institution_type"] == "industry", d["institution_type"])
ok("後面窗口才讀到的屬性也撿得起來",
   d["role_level"] == "senior_management", d["role_level"])
ok("判定依據保留", d[S.DESCRIPTOR_BASIS] == "他說自己在產業界")
ok("全空時補 unspecified",
   CH.merge_descriptors([{}, {}])["sector"] == S.UNSPECIFIED)

ok("受訪者名稱取多數決",
   CH.merge_respondent(["賴經理", "賴經理", "unknown", "受訪者"]) == "賴經理")
ok("全都不可用時回 unknown",
   CH.merge_respondent(["", None, "unknown"]) == "unknown")
ok("只有一個窗口讀到名字時就用它",
   CH.merge_respondent(["unknown", "賴經理", ""]) == "賴經理")

print()
print("=" * 70)
print("測試 5：整段編碼流程（用假模型，不需要真的模型在場）")
print("=" * 70)
calls = []


def fake_code(text, n, total):
    calls.append((n, total, len(text)))
    return S.migrate_record({
        S.RESPONDENT: "賴經理",
        S.DESCRIPTORS: {"institution_type": "industry"} if n == 0 else {},
        S.SUMMARY: f"第 {n} 段的摘要",
        S.SEGMENTS: [seg(f"S{n:03d}", f"第{n}窗口的引文{k}",
                         [(S.REFLEXIVITY, "N")]) for k in range(3)]})


out = CH.code_transcript(LONG, fake_code, window=3000, overlap=300)
ok("每個窗口各呼叫一次模型", len(calls) == len(chunks),
   f"{len(calls)} 次 / {len(chunks)} 窗")
ok("段落數是各窗口的總和（去重後）",
   len(out[S.SEGMENTS]) == 3 * len(chunks), str(len(out[S.SEGMENTS])))
ok("受訪者合併起來", out[S.RESPONDENT] == "賴經理")
ok("只有第一窗讀到的屬性沒有被沖掉",
   out[S.DESCRIPTORS]["institution_type"] == "industry")
ok("provenance 記下窗口參數（換參數就是換一次實驗，必須可重現）",
   out[S.META]["chunking"]["window_chars"] == 3000
   and out[S.META]["chunking"]["overlap_chars"] == 300
   and out[S.META]["chunking"]["n_chunks"] == len(chunks),
   str(out[S.META]["chunking"]))
ok("各窗摘要另外交出去（不直接串起來當總摘要）",
   len(out["_chunk_summaries"]) == len(chunks))

# 一個窗口壞掉不該讓整份稿件作廢——把小失敗放大成大失敗是最貴的錯誤
def flaky(text, n, total):
    if n == 2:
        raise ValueError("模型回了壞 JSON")
    return fake_code(text, n, total)


calls.clear()
out2 = CH.code_transcript(LONG, flaky, window=3000, overlap=300)
ok("單一窗口失敗不中斷整輪", len(out2[S.SEGMENTS]) > 0, str(len(out2[S.SEGMENTS])))
ok("失敗的窗口被記下來（使用者要知道結果不完整）",
   out2[S.META]["chunk_errors"][0]["chunk"] == 2,
   str(out2[S.META].get("chunk_errors")))
ok("成功的窗口數如實記錄",
   out2[S.META]["chunking"]["n_ok"] == len(chunks) - 1)

print()
print("=" * 70)
print("測試 6：產出量檢查（認出「不可能是真的」的形狀）")
print("=" * 70)
DIMS = F.active().dimensions
# 重演實測到的失效：46,730 字元、4 段、四個維度各一段、極性也各一種
_incident = [seg("S001", "q1", [(S.ANTICIPATION, "P")]),
             seg("S002", "q2", [(S.REFLEXIVITY, "P")]),
             seg("S003", "q3", [(S.ENGAGEMENT, "P")]),
             seg("S004", "q4", [(S.RESPONSIVENESS, "N")])]
yr = CH.yield_report("x" * 46730, _incident, DIMS)
print(f"   實測的失效：{yr['n_segments']} 段 / {yr['chars']} 字元 "
      f"= 每萬字元 {yr['per_10k']} 段（人工參考值 {yr['human_reference_per_10k']}）")
ok("認出產出過低", CH.FLAG_LOW_YIELD in yr["flags"], str(yr["flags"]))
ok("認出「每個維度剛好一段」＝照抄範例的簽名",
   CH.FLAG_ONE_PER_DIMENSION in yr["flags"], str(yr["flags"]))

# 人工編碼的密度（30 段 / 21,569 字元）不可以被判成有問題，
# 否則這個警示每次都響，等於沒有警示
_human_dims = ([S.REFLEXIVITY] * 11 + [S.ANTICIPATION] * 7
               + [S.ENGAGEMENT] * 7 + [S.RESPONSIVENESS] * 5)
_human = [seg(f"S{i:03d}", f"q{i}", [(_human_dims[i], "N")])
          for i in range(30)]
yh = CH.yield_report("x" * 21569, _human, DIMS)
print(f"   人工編碼：{yh['n_segments']} 段 / {yh['chars']} 字元 "
      f"= 每萬字元 {yh['per_10k']} 段")
ok("人工編碼的密度不被誤報", not yh["flags"], str(yh["flags"]))

# 短文件不該因為段落少就被警示
ok("短文件不套用密度門檻",
   CH.FLAG_LOW_YIELD not in CH.yield_report("x" * 500, _incident[:1], DIMS)["flags"])
# 剛好四段但集中在同一個維度，不是照抄範例的形狀
_four_same = [seg(f"S{i:03d}", f"q{i}", [(S.REFLEXIVITY, "N")]) for i in range(4)]
ok("四段但集中在同一維度，不算照抄範例",
   CH.FLAG_ONE_PER_DIMENSION not in
   CH.yield_report("x" * 46730, _four_same, DIMS)["flags"])
ok("列出完全沒編到的維度",
   set(CH.yield_report("x" * 46730, _four_same, DIMS)["missing"])
   == {S.ANTICIPATION, S.ENGAGEMENT, S.RESPONSIVENESS})
ok("空結果不炸", CH.yield_report("", [], DIMS)["n_segments"] == 0)
ok("yield_report 不改動輸入（只回報，不修改結果）",
   len(_incident) == 4 and _incident[0][S.SEGMENT_ID] == "S001")

print()
print("=" * 70)
print("測試 7：共現要分得出哪些是分窗合併造成的")
print("=" * 70)
# 要防的失效：一份英文訪談稿 94 段裡，14 個多重編碼段落有 11 個的第二個碼
# 是跨窗合併帶進來的——也就是該份的共現表七成以上不是模型在單一次判斷裡
# 主張的，而是切段這個動作的產物。共現是這套工具的分析輸出之一，
# 「參與·開放 × 回應性·調適」這種結論若照著講出去，講的是切段的產物。
import tacit_analysis as A                                       # noqa: E402

F.reset()
_g1 = [seg("S001", "同一句話", [(S.REFLEXIVITY, "N")]),
       seg("S002", "只有這個窗口看到", [(S.ENGAGEMENT, "P"), (S.RESPONSIVENESS, "P")])]
_g2 = [seg("S001", "同一句話", [(S.RESPONSIVENESS, "N")])]
_merged = CH.merge_segments([_g1, _g2])
_rec = {S.RESPONDENT: "P1", S.SEGMENTS: _merged}

ok("S001 的 RES-N 被標記為跨窗併入",
           A.merged_codes(_merged[0]) == {"RES-N"},
           str(A.merged_codes(_merged[0])))
ok("模型自己給的多重編碼不會被誤標為併碼",
           A.merged_codes(_merged[1]) == set(),
           str(A.merged_codes(_merged[1])))

_cnt, _jac, _tot = A.cooccurrence([_rec])
_cnt2, _jac2, _tot2 = A.cooccurrence([_rec], exclude_merged=True)
ok("預設含併碼共現：REF-N × RES-N 有一次",
           int(_cnt.loc["REF-N", "RES-N"]) == 1,
           str(int(_cnt.loc["REF-N", "RES-N"])))
ok("排除併碼後那一次消失",
           int(_cnt2.loc["REF-N", "RES-N"]) == 0,
           str(int(_cnt2.loc["REF-N", "RES-N"])))
ok("模型自己主張的共現不受影響（ENG-P × RES-P 兩邊都在）",
           int(_cnt.loc["ENG-P", "RES-P"]) == 1
           and int(_cnt2.loc["ENG-P", "RES-P"]) == 1)

_mp = A.merge_provenance([_rec])
ok("provenance 表算得出併碼佔比",
           int(_mp.iloc[0]["multi_coded"]) == 2
           and int(_mp.iloc[0]["multi_from_merge"]) == 1
           and abs(float(_mp.iloc[0]["merged_share"]) - 0.5) < 1e-9,
           _mp.to_dict("records")[0].__str__())
_clean = {S.RESPONDENT: "P2", S.SEGMENTS: [
    seg("S001", "q", [(S.REFLEXIVITY, "N"), (S.ENGAGEMENT, "N")])]}
ok("沒有併碼時佔比為 0",
           float(A.merge_provenance([_clean]).iloc[0]["merged_share"]) == 0.0)
ok("空紀錄不炸", A.merge_provenance([]).empty)

print()
print("=" * 70)
print("測試 8：窗口的字元範圍與重疊區")
print("=" * 70)
# 合併只能在相鄰窗口的重疊區裡做，所以每個窗口要知道自己在原文的哪裡、
# 跟前一個窗口共有哪一段。
plan = CH.plan_windows(LONG, window=3000, overlap=300)
ok("plan 與 split_transcript 的窗口一致",
   [(p["unit_start"], p["text"]) for p in plan] == CH.split_transcript(LONG, 3000, 300))
ok("字元範圍逐字對得回原文",
   all(LONG[p["char_start"]:p["char_end"]] == p["text"] for p in plan))
ok("第一個窗口沒有重疊區", plan[0]["overlap_text"] == "")
ok("重疊區是前一窗口的結尾、也是本窗口的開頭",
   all(a["text"].endswith(b["overlap_text"]) and b["text"].startswith(b["overlap_text"])
       and b["overlap_text"] for a, b in zip(plan, plan[1:])))
ok("重疊區至少有 overlap 那麼長",
   all(len(b["overlap_text"]) >= 300 for b in plan[1:]),
   str([len(b["overlap_text"]) for b in plan[1:]]))
_blank = "第一段。\n\n\n第二段在空行之後。"
_pu = CH.split_units_with_offsets(_blank)
ok("空行不算單位，但位置仍然對得上",
   [u for _, u in _pu] == ["第一段。", "第二段在空行之後。"]
   and all(_blank[o:o + len(u)] == u for o, u in _pu), str(_pu))
_long_line = "受訪者連續講了很久。" * 800
_lu = CH.split_units_with_offsets(_long_line)
ok("超長單行切開後每段的位置仍對得回原文",
   len(_lu) > 1 and all(_long_line[o:o + len(u)] == u for o, u in _lu))
ok("短稿的單一窗口也有字元範圍",
   CH.plan_windows("很短的一段話", 3000, 300)[0]["char_end"] == 6)

print()
print("=" * 70)
print("測試 9：只在相鄰窗口的重疊區裡合併——相隔很遠的同一句話是兩段")
print("=" * 70)
# 要防的失效：同一句「We never asked the residents.」在第 2 輪與第 35 輪各說
# 一次，兩處的脈絡不同、判斷也不同（ENG-N 對 REF-P）。只看引文包含、不看
# 位置的合併會把第 35 輪那一段整個併進第 2 輪，稿件裡從此沒有第二段。
F.reset()
_w0 = [seg("S001", "That is a good question. We never asked the residents.",
           [(S.ENGAGEMENT, "N")]),
       seg("S002", "The overlap sentence that both windows can see, verbatim.",
           [(S.ANTICIPATION, "P")]),
       seg("S003", "It took a long time before anyone noticed the problem.",
           [(S.REFLEXIVITY, "N")])]
_w1 = [seg("S001", "The overlap sentence that both windows can see, verbatim.",
           [(S.RESPONSIVENESS, "P")]),
       seg("S002", "a long time", [(S.ANTICIPATION, "N")]),
       seg("S003", "A sentence in the middle of window one, not in any overlap.",
           [(S.REFLEXIVITY, "P")])]
_w2 = [seg("S001", "A sentence in the middle of window one, not in any overlap.",
           [(S.ENGAGEMENT, "P")])]
_w3 = [seg("S001", "We never asked the residents.", [(S.REFLEXIVITY, "P")])]
_overlaps = ["",
             "The overlap sentence that both windows can see, verbatim.",
             "some other shared text",
             "nothing shared here"]
_m = CH.merge_segments([_w0, _w1, _w2, _w3], overlaps=_overlaps)
_quotes = [s[S.QUOTE] for s in _m]
ok("重疊區裡同一句話的兩份判斷合併成一段",
   _quotes.count("The overlap sentence that both windows can see, verbatim.") == 1)
_ov_seg = next(s for s in _m if s[S.QUOTE].startswith("The overlap sentence"))
ok("合併時兩邊的碼都保留",
   sorted(S.codes_of(_ov_seg)) == ["ANT-P", "RES-P"], str(S.codes_of(_ov_seg)))
ok("相隔三十輪的同一句話仍是兩段（第 35 輪那一段還在）",
   "We never asked the residents." in _quotes, str(_quotes))
ok("第 2 輪那一段沒有被併入別的碼",
   sorted(S.codes_of(next(s for s in _m if s[S.QUOTE].startswith("That is a good"))))
   == ["ENG-N"])
ok("過短的引文（a long time）不併進包含它的段落",
   "a long time" in _quotes, str(_quotes))
ok("同一句話出現在相鄰窗口、但不在重疊區裡：不合併",
   _quotes.count("A sentence in the middle of window one, not in any overlap.") == 2)
ok("段落總數正確（8 段輸入，只有重疊區那一對合併）", len(_m) == 7, str(len(_m)))
# 沒有 overlaps 時退回「相鄰窗口、引文包含」的規則；不相鄰照樣不合併
_m2 = CH.merge_segments([_w0, [], [], _w3])
ok("沒有位置資訊時，不相鄰的窗口也不合併",
   [s[S.QUOTE] for s in _m2].count("We never asked the residents.") == 1
   and len(_m2) == 4, str(len(_m2)))
# 同一窗口內模型把同一段回了兩次：合併
ok("同一窗口內完全相同的重複合併成一段",
   len(CH.dedupe_segments([seg("S001", "Dup sentence here.", [(S.ANTICIPATION, "P")])] * 3)) == 1)
ok("失敗窗口（空清單）不打斷相鄰關係的計算",
   len(CH.merge_segments([_w0, [], _w0])) == 6)

print()
print("=" * 70)
print("測試 10：整批的錯誤直接拋出，窗口的錯誤記清楚位置")
print("=" * 70)
# 要防的失效：視窗不夠的拒絕、配額用完、服務沒開，都被逐窗吞成
# 「窗口失敗」，畫面上只剩「Failed after 3 attempts」，原因與解法都不見了。
import tacit_llm as LLM                                          # noqa: E402

for _exc in (LLM.ContextOverflow("prompt is about 7874 tokens but only 5120 remain"),
             LLM.RateLimited("HTTP 429 rate limited"),
             LLM.NotConfigured("Cannot reach http://localhost:11434"),
             LLM.Timeout("no answer within 900 seconds"),
             LLM.Unavailable("tried 4 times")):
    def _fatal(text, n, total, _e=_exc):
        if n == 1:
            raise _e
        return fake_code(text, n, total)
    try:
        CH.code_transcript(LONG, _fatal, window=3000, overlap=300)
        ok(f"{type(_exc).__name__} 直接拋出", False)
    except type(_exc) as e:
        ok(f"{type(_exc).__name__} 直接拋出（型別不變）", True)
        ok(f"{type(_exc).__name__} 的訊息說出是哪個窗口",
           "window 2 of" in str(e) and "characters" in str(e), str(e)[:100])
        ok(f"{type(_exc).__name__} 的原始訊息保留", str(_exc) in str(e))
    except Exception as e:                                       # noqa: BLE001
        ok(f"{type(_exc).__name__} 直接拋出", False, f"變成了 {type(e).__name__}")

_err = out2[S.META]["chunk_errors"][0]
ok("窗口錯誤記下字元範圍",
   _err.get("start_char") is not None and _err.get("end_char", 0) > _err.get("start_char", 0)
   and _err.get("chars", 0) > 0, str(_err))
ok("窗口錯誤帶原因", "壞 JSON" in _err["error"])
eq("失敗的窗口數寫進 _meta.incomplete_windows", out2[S.META].get("incomplete_windows"), 1)
eq("chunking.n_failed 一致", out2[S.META]["chunking"]["n_failed"], 1)
ok("完整的紀錄沒有 incomplete_windows", "incomplete_windows" not in out[S.META])
_wins = out2[S.META]["chunking"]["windows"]
ok("每個窗口一筆診斷", len(_wins) == len(chunks), str(len(_wins)))
ok("失敗的窗口標成 failed",
   [w["status"] for w in _wins if w["chunk"] == 2] == ["failed"])
ok("成功的窗口記段落數與密度",
   all(w["segments"] == 3 and w.get("per_10k", 0) > 0
       for w in _wins if w["status"] == "ok"))
ok("合併規則寫進 provenance",
   out2[S.META]["chunking"].get("merge_rule") == "adjacent_overlap")
# 回了零個段落的窗口不是錯誤，但要數出來
def _sparse(text, n, total):
    r = fake_code(text, n, total)
    if n == 0:
        r[S.SEGMENTS] = []
    return r
_o3 = CH.code_transcript(LONG, _sparse, window=3000, overlap=300)
eq("零段落的窗口數出來", _o3[S.META]["chunking"]["n_no_segments"], 1)
ok("零段落的窗口不算失敗", "incomplete_windows" not in _o3[S.META])

print()
print("=" * 70)
print("測試 11：受訪者識別碼不從模型輸出來")
print("=" * 70)
# 要防的失效：模型讀不到名字時把提示詞的佔位字樣照抄回來——兩份不同文件都
# 叫「the respondent, as named in the interview transcript」，紀錄、逐字稿與
# 抽樣框都用這個字串當鍵，第二份把第一份蓋掉。
for _ph in ("the respondent, as named in the interview transcript",
            "the person speaking, as named in the document",
            "未指定", "Respondent", "unknown", "N/A", "受訪者"):
    ok(f"佔位字樣不算名字：{_ph[:30]}", CH.is_placeholder_name(_ph))
ok("真正的名字不會被誤判", not CH.is_placeholder_name("Patsy Calton"))
eq("全是佔位字樣時回 unknown",
   CH.merge_respondent(["the respondent, as named in the interview transcript", "未指定"]),
   "unknown")
eq("檔名主幹當識別碼",
   CH.respondent_from_filename("some/dir/LY_2024 (final).docx"), "LY_2024 (final)")
eq("沒有檔名時回 unknown", CH.respondent_from_filename(""), "unknown")
_o4 = CH.code_transcript(LONG, fake_code, window=3000, overlap=300,
                         respondent="D2_hansard")
eq("呼叫端給的識別碼優先於模型讀到的名字", _o4[S.RESPONDENT], "D2_hansard")
eq("識別碼的來源記進 _meta", _o4[S.META].get("respondent_source"), "caller")

print()
print("=" * 70)
print("測試 12：產出量診斷寫得進紀錄")
print("=" * 70)
eq("低產出量門檻是每萬字元 3.0 段", CH.LOW_YIELD_PER_10K, 3.0)
_rec = {S.RESPONDENT: "P", S.SEGMENTS: [seg("S001", "這句話在原文裡", [(S.REFLEXIVITY, "N")]),
                                         seg("S002", "這句話不在原文裡", [(S.REFLEXIVITY, "N")])]}
_yr = CH.attach_yield(_rec, "x" * 3000 + "這句話在原文裡", DIMS,
                      dropped=[{"reason": S.DROP_UNKNOWN_DIMENSION},
                               {"reason": S.DROP_UNKNOWN_DIMENSION},
                               {"reason": S.DROP_DUPLICATE}])
ok("_meta.yield 寫入", _rec[S.META]["yield"] is _yr or _rec[S.META]["yield"] == _yr)
eq("低產出量的狀態寫進 _meta.low_yield", _rec[S.META]["low_yield"], False)
eq("被丟棄的碼逐筆寫入", len(_rec[S.META]["dropped"]), 3)
eq("被丟棄的碼依原因計數",
   _rec[S.META]["drop_summary"], {S.DROP_UNKNOWN_DIMENSION: 2, S.DROP_DUPLICATE: 1})
eq("引文對不回原文的段落數出來", _yr["n_unmatched_quotes"], 1)
eq("報告寫出門檻", _yr["low_yield_threshold_per_10k"], 3.0)
_low = {S.RESPONDENT: "P", S.SEGMENTS: [seg("S001", "q", [(S.REFLEXIVITY, "N")])]}
CH.attach_yield(_low, "x" * 40000, DIMS)
eq("真的低產出時 low_yield 為 True", _low[S.META]["low_yield"], True)
eq("沒有丟棄時計數是空的", _low[S.META]["drop_summary"], {})

print()
print("=" * 70)
print("測試 13：讀 .docx——依文件順序、表格每列一次、追蹤修訂的新增字算進去")
print("=" * 70)
# 要防的失效：表格全部被搬到文件最後；合併的儲存格照格線重複好幾次
# （20 頁報告讀成 626,315 字元，其中「2023 Sustainability Report」出現 245 次）；
# 表頭是 Speaker | Text 的逐字稿表格整個被丟掉；追蹤修訂裡新增的字不見。
import os                                                        # noqa: E402
import tempfile                                                  # noqa: E402
import docx                                                      # noqa: E402
from docx.oxml import OxmlElement                                # noqa: E402
from docx.oxml.ns import qn                                      # noqa: E402

with tempfile.TemporaryDirectory() as _d:
    _doc = docx.Document()
    _doc.sections[0].header.paragraphs[0].text = "HEADERMARK confidential"
    _doc.sections[0].footer.paragraphs[0].text = "FOOTERMARK page"
    _doc.add_paragraph("P1 before the table.")
    _tb = _doc.add_table(rows=2, cols=3)
    _tb.cell(0, 0).merge(_tb.cell(0, 2)).text = "MERGED scope 1 emissions fell 12 percent."
    _tb.cell(1, 0).text, _tb.cell(1, 1).text, _tb.cell(1, 2).text = "a", "b", "c"
    _doc.add_paragraph("P2 after the table.")
    _sp = _doc.add_table(rows=3, cols=2)
    _sp.cell(0, 0).text, _sp.cell(0, 1).text = "Speaker", "Text"
    _sp.cell(1, 0).text, _sp.cell(1, 1).text = "LUCID", "I grew up in Bethany."
    _sp.cell(2, 0).text, _sp.cell(2, 1).text = "ROSS-NAZZAL", "When was that?"
    _para = _doc.add_paragraph("P3 base text ")
    _ins = OxmlElement("w:ins")
    _ins.set(qn("w:id"), "901"); _ins.set(qn("w:author"), "A"); _ins.set(qn("w:date"), "2026-01-01T00:00:00Z")
    _r = OxmlElement("w:r"); _t = OxmlElement("w:t"); _t.text = "INSERTED within two weeks "
    _t.set(qn("xml:space"), "preserve"); _r.append(_t); _ins.append(_r); _para._p.append(_ins)
    _del = OxmlElement("w:del")
    _del.set(qn("w:id"), "902"); _del.set(qn("w:author"), "A"); _del.set(qn("w:date"), "2026-01-01T00:00:00Z")
    _r2 = OxmlElement("w:r"); _dt = OxmlElement("w:delText"); _dt.text = "DELETED after six months "
    _dt.set(qn("xml:space"), "preserve"); _r2.append(_dt); _del.append(_r2); _para._p.append(_del)
    _r3 = OxmlElement("w:r"); _t3 = OxmlElement("w:t"); _t3.text = "and published."; _r3.append(_t3); _para._p.append(_r3)
    _nest_host = _doc.add_table(rows=1, cols=1)
    _nest_host.cell(0, 0).text = "OUTER cell"
    _inner = _nest_host.cell(0, 0).add_table(rows=1, cols=2)
    _inner.cell(0, 0).text, _inner.cell(0, 1).text = "INNER left", "INNER right"
    _doc.add_paragraph("")
    _path = os.path.join(_d, "features.docx")
    _doc.save(_path)

    _text = CH.read_docx_text(_path)
    _lines = _text.split("\n")
    ok("段落與表格依文件順序",
       _lines.index("P1 before the table.") < _lines.index("MERGED scope 1 emissions fell 12 percent.")
       < _lines.index("P2 after the table."), str(_lines[:4]))
    eq("合併的儲存格只出現一次", _text.count("MERGED"), 1)
    ok("表格列以 tab 接起來", "a\tb\tc" in _lines, str(_lines))
    ok("Speaker | Text 表格變成講者標記",
       "【LUCID】I grew up in Bethany." in _lines and "【ROSS-NAZZAL】When was that?" in _lines,
       str(_lines))
    ok("表頭列本身不輸出", not any(l.startswith("Speaker") for l in _lines))
    ok("頁首不讀", "HEADERMARK" not in _text)
    ok("頁尾不讀", "FOOTERMARK" not in _text)
    ok("追蹤修訂新增的字算進去", "P3 base text INSERTED within two weeks and published." in _lines,
       str([l for l in _lines if l.startswith("P3")]))
    ok("追蹤修訂刪掉的字不算", "DELETED" not in _text)
    ok("巢狀表格的列也讀到", "INNER left\tINNER right" in _lines, str(_lines))
    ok("空段落不輸出", "" not in _lines)
    with open(_path, "rb") as _fh:
        eq("已開啟的檔案物件也讀得到", CH.read_docx_text(_fh), _text)
    _bad = os.path.join(_d, "fake.docx")
    with open(_bad, "w", encoding="utf-8") as _fh:
        _fh.write("this is not a zip")
    try:
        CH.read_docx_text(_bad)
        ok("不是 .docx 的檔案要拋 ValueError", False)
    except ValueError as e:
        ok("不是 .docx 的檔案要拋 ValueError（呼叫端接得住、訊息帶檔名）",
           "fake.docx" in str(e), str(e)[:100])
    import bench_models as B                                     # noqa: E402
    eq("基準腳本用同一個讀法", B.read_docx(_path), _text)

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
