"""
驗證 tacit_open.py：碼會不會累積、合併留不留軌跡、碼簿能不能變成框架。

為什麼這一支存在
----------------
「先有框架再編碼」涵蓋主題分析三分法裡的編碼信度型與
碼簿型，但沒有涵蓋碼簿從資料長出來的那一半（開放編碼／紮根理論）。

缺的不是主題歸納——那早就在跑。缺的只有一件事：**碼要會累積**。每個窗口
各自編碼、彼此不知道對方用過什麼碼的話，一份兩萬字逐字稿會產出兩百個互不
相同的標籤，沒有任何一個重複。那不是編碼，是逐段下標題；沒有碼簿就沒有
頻次、沒有共現、沒有信度。

所以這一支守的第一件事就是「第二次遇到同一件事時，用的是同一個碼」。
第二件是碼簿轉成框架之後，既有的整條分析管線接得上——那是整個設計的關節。
"""
import copy
import os
import sys
import tempfile

import tacit_analysis as A
import tacit_framework as F
import tacit_open as OP
import tacit_schema as S
import tacit_themes as RT

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def check(label, got, want):
    cond = got == want
    print(("  PASS  " if cond else "  FAIL  ") + f"{label}: got={got} want={want}")
    if not cond:
        FAIL.append(label)


print("=" * 70)
print("測試 1：碼簿的基本操作")
print("=" * 70)
cb = OP.new_codebook("zh-Hant")
check("新碼簿是空的", len(cb[OP.CODES]), 0)
c1 = OP.add_code(cb, "護理人力不足", "受訪者談到護理師人數不夠應付工作量", chunk=0)
check("碼 id 從 c001 開始", c1[OP.CODE_ID], "c001")
check("碼 id 符合框架的維度 id 規則",
      bool(F._ID_RE.match(c1[OP.CODE_ID])), True)
c2 = OP.add_code(cb, "法規更新頻繁", chunk=0)
check("第二個碼", c2[OP.CODE_ID], "c002")

# 同一個標籤不可以建出兩個碼——那正是「碼簿」與「一堆標題」的差別
again = OP.add_code(cb, "護理人力不足", chunk=3)
check("重複標籤回傳既有的碼", again[OP.CODE_ID], "c001")
check("碼數沒有增加", len(cb[OP.CODES]), 2)
# 標點與空白不同也算同一個碼
ok("標點與空白差異不會生出新碼",
   OP.add_code(cb, " 護理人力、不足 ")[OP.CODE_ID] == "c001",
   OP.add_code(cb, " 護理人力、不足 ")[OP.CODE_ID])
ok("空標籤不建碼", OP.add_code(cb, "   ") is None)
ok("找得到既有碼", OP.find_code(cb, "法規更新頻繁")[OP.CODE_ID] == "c002")
ok("找不到的回 None", OP.find_code(cb, "完全沒出現過的東西") is None)

print()
print("=" * 70)
print("測試 2：提示詞裡真的帶著既有的碼")
print("=" * 70)
# 這一段是「碼會累積」實際發生的地方。沒有它，每個窗口都從零開始。
empty_block = OP.codebook_prompt_block(OP.new_codebook())
ok("空碼簿時說明正在建立碼簿", "starting the codebook" in empty_block, empty_block[:60])
block = OP.codebook_prompt_block(cb)
ok("既有的碼列進提示詞", "護理人力不足" in block and "法規更新頻繁" in block)
ok("帶出現次數（讓模型看得出哪些是常用碼）", "[" in block and "x]" in block)
ok("要求沿用時逐字複製標籤", "EXACTLY" in block)
# 偏向沿用，但不到強迫——逼太緊會把真正新的東西硬塞進舊碼
ok("同時明說「不要為了讓清單短而硬塞」", "forced fit" in block or "Do not force" in block)

# 碼簿長到超過提示詞容量之後，只列最常用的那些。
# 另一種選法——留四分之一的位置給最近建立的碼——量測過：同一批聽證會
# 逐字稿碼數 352→423、單次碼 319→369、時間 125→199 分，每一項都更差
# （數字在 tacit_open.codebook_prompt_block 的註解裡）。這幾條守的是
# 「只列最常用的碼」這個行為。
_big = OP.new_codebook("en")
for _i in range(OP.MAX_CODES_IN_PROMPT * 2):
    _c = OP.add_code(_big, f"code number {_i:03d}", f"definition {_i:03d}")
    _c[OP.CODE_COUNT] = 50 - _i if _i < 40 else 1        # 前 40 個常用，其餘單次
_blk = OP.codebook_prompt_block(_big)
_shown = [c[OP.CODE_LABEL] for c in _big[OP.CODES] if c[OP.CODE_LABEL] in _blk]
ok("碼簿超出容量時只列一部分",
   len(_shown) <= OP.MAX_CODES_IN_PROMPT, f"{len(_shown)}")
ok("提示詞說出碼簿實際有多少碼",
   f"{len(_big[OP.CODES])} codes so far" in _blk, _blk[:80])
ok("常用的碼一定在列表裡",
   all(f"code number {i:03d}" in _blk for i in range(10)))
ok("提示詞講明列出來的是最常用的那些（不然模型會以為碼簿只有這麼大）",
   "most used" in _blk, _blk[:90])
ok("次數最高的排在最前面",
   _blk.index("code number 000") < _blk.index("code number 039"))

# similar_pairs 的 limit 是**畫面上的顯示上限**，不是數量。
# 一份 352 個碼的碼簿有 972 對候選，用預設值只會拿到 40；把被截斷的
# 筆數當成測量值，「全部接受後剩幾個碼」也會跟著錯（167 會變成 323）。
# 量測一律用 limit=None。
_many = OP.new_codebook("en")
for _i in range(30):
    OP.add_code(_many, f"concerns about AI {_i:02d}", "")
_capped = OP.similar_pairs(_many, limit=5)
_all = OP.similar_pairs(_many, limit=None)
ok("limit 真的會截斷", len(_capped) == 5, str(len(_capped)))
ok("limit=None 不截斷", len(_all) > len(_capped), f"{len(_all)} vs {len(_capped)}")
ok("截斷的是相似度最高的那些",
   [r["similarity"] for r in _capped] == [r["similarity"] for r in _all[:5]])
ok("預設仍然有上限（介面不要畫上千列）",
   len(OP.similar_pairs(_many)) <= 40, str(len(OP.similar_pairs(_many))))

# 提示詞的輸出格式裡寫著「if this code is NEW, define it…」，小模型會把
# 那個字眼抄進標籤。實測 llama3:8b 跑 12 份聽證會逐字稿，出現了
# "[NEW CODE] Concerns about AI oversight"（22 次）與一個**整個就叫
# "NEW CODE" 的碼**（19 次）。那不是碼，是工具自己的詞彙洩進了碼簿。
for _raw, _want in [
    ("[NEW CODE] Concerns about AI oversight", "Concerns about AI oversight"),
    ("NEW CODE: Concerns about AI", "Concerns about AI"),
    ("new code: Bias in training data", "Bias in training data"),
    ("(new) Transparency in AI", "Transparency in AI"),
    ("[9x] Guardrails for AI", "Guardrails for AI"),
]:
    check(f"拿掉裝飾：{_raw[:34]}", OP.clean_label(_raw)[0], _want)

# 整個就是裝飾的，回空字串讓 add_code 丟掉——不要猜它想說什麼
for _raw in ("NEW CODE", "NEW CODES", "new", "  new code  "):
    check(f"只有裝飾的不算碼：{_raw!r}", OP.clean_label(_raw)[0], "")
# 真正的路徑是 absorb（add_code 是更低層的，不負責清裝飾）。
_deco_cb = OP.new_codebook("en")
def _seg1(title, quote, label, definition=""):
    # raw_seg 定義在測試 3，這裡自己組一個
    return {S.TITLE: title, S.QUOTE: quote, S.FULL_TEXT: quote + " (ctx)",
            OP.OPEN_CODES: [{OP.CODE_LABEL: label,
                             OP.CODE_DEFINITION: definition,
                             S.RATIONALE: "r"}]}


_deco_segs, _deco_st = OP.absorb(_deco_cb, {OP.OPEN_SEGMENTS: [
    _seg1("t1", "q1", "NEW CODE"),
    _seg1("t2", "q2", "[NEW CODE] Oversight gaps", "監理缺口"),
]}, chunk=0)
check("整個就是裝飾的碼不進碼簿", len(_deco_cb[OP.CODES]), 1)
check("進碼簿的是拆下裝飾之後的標籤",
      _deco_cb[OP.CODES][0][OP.CODE_LABEL], "Oversight gaps")
check("那一段沒有碼，不留段落", len(_deco_segs), 1)

# 正當的標籤不可以被改壞。這幾條比上面那幾條重要：
# 寬鬆的規則會把 "New codes of conduct" 砍成 "codes of conduct"，
# 而那種錯誤畫面上完全看不出來。
for _keep in ("New codes of conduct for AI", "Newly proposed federal guidance",
              "News coverage of AI incidents", "Renewing procurement rules"):
    check(f"不動正當標籤：{_keep[:34]}", OP.clean_label(_keep)[0], _keep)

_prompt = OP.build_open_prompt(cb, "zh-Hant", "中文樣本")
ok("提示詞含碼簿", "護理人力不足" in _prompt)
ok("提示詞要求窮舉", "COVERAGE" in _prompt)
ok("提示詞禁止以缺席為證據", "ABSENCE IS NOT EVIDENCE" in _prompt)
ok("提示詞要求逐字引用", "VERBATIM" in _prompt)
ok("提示詞說明什麼是碼、什麼只是主題標籤", "topic label" in _prompt)
ok("輸出範例不只一個段落物件", _prompt.count("same shape") >= 2)
ok("繁中時要求繁體", "Traditional Chinese" in _prompt)

print()
print("=" * 70)
print("測試 3：吸收模型輸出——沿用優先於新增")
print("=" * 70)
cb2 = OP.new_codebook("zh-Hant")


def raw_seg(title, quote, codes):
    return {S.TITLE: title, S.QUOTE: quote, S.FULL_TEXT: quote + "（上下文）",
            OP.OPEN_CODES: [{OP.CODE_LABEL: lab, OP.CODE_DEFINITION: d,
                             S.RATIONALE: r} for lab, d, r in codes]}


segs, st = OP.absorb(cb2, {S.RESPONDENT: "賴經理", OP.OPEN_SEGMENTS: [
    raw_seg("人力", "大夜班一個護理師要顧四十床",
            [("護理人力不足", "護理師人數不夠應付工作量", "明講人數不足")]),
    raw_seg("法規", "FDA 每三個月就更新一次資安指引",
            [("法規更新頻繁", "主管機關頻繁修訂要求", "明講更新頻率")]),
]}, chunk=0, respondent="賴經理")
check("第一個窗口：兩段", len(segs), 2)
check("第一個窗口：新建兩個碼", st["created"], 2)
check("第一個窗口：沒有沿用", st["reused"], 0)

# 第二個窗口用同樣的標籤 → 必須沿用，不可以再建一個
segs2, st2 = OP.absorb(cb2, {S.RESPONDENT: "賴經理", OP.OPEN_SEGMENTS: [
    raw_seg("人力2", "護理師真的不夠",
            [("護理人力不足", "", "同一個現象再次出現")]),
    raw_seg("新的", "我們自己做了一套訓練",
            [("內部自建訓練", "組織自行發展的培訓機制", "新的東西")]),
]}, chunk=1, respondent="賴經理")
check("第二個窗口：沿用一個", st2["reused"], 1)
check("第二個窗口：新建一個", st2["created"], 1)
check("碼簿總數是三個，不是四個", len(cb2[OP.CODES]), 3)
check("被沿用的碼次數累加", OP.find_code(cb2, "護理人力不足")[OP.CODE_COUNT], 2)

# 沿用時模型補的定義：原本沒有才採用，已經寫好的不可以被後來的即興說法蓋掉
_c = OP.find_code(cb2, "護理人力不足")
check("既有定義不被覆蓋", _c[OP.CODE_DEFINITION], "護理師人數不夠應付工作量")
OP.absorb(cb2, {OP.OPEN_SEGMENTS: [
    raw_seg("t", "q", [("法規更新頻繁", "後來才補上的定義", "r")])]}, chunk=2)
# 「法規更新頻繁」第一次就有定義了，一樣不該被換掉
check("第二次補定義也不覆蓋既有定義",
      OP.find_code(cb2, "法規更新頻繁")[OP.CODE_DEFINITION], "主管機關頻繁修訂要求")

# 代表引文要留下來——那是之後轉成框架時 indicators 的內容
ok("碼帶著代表引文", len(_c[OP.CODE_EXAMPLES]) >= 1, str(_c[OP.CODE_EXAMPLES][:1]))
ok("引文帶受訪者", _c[OP.CODE_EXAMPLES][0].get(S.RESPONDENT) == "賴經理")
# 沒有碼的段落不留
_s, _ = OP.absorb(OP.new_codebook(), {OP.OPEN_SEGMENTS: [
    {S.TITLE: "沒有碼", S.QUOTE: "q", OP.OPEN_CODES: []}]})
check("沒有碼的段落被剔除", len(_s), 0)
_s2, _ = OP.absorb(OP.new_codebook(), {OP.OPEN_SEGMENTS: ["不是 dict"]})
check("髒資料不炸", len(_s2), 0)

print()
print("=" * 70)
print("測試 4：整份逐字稿的開放編碼（假模型）")
print("=" * 70)
TURNS = [f"【受訪者】第{i}輪。" + f"我們在談的是護理人力與法規遵循的問題。" * 20
         for i in range(1, 19)]
LONG = "\n".join(TURNS)
cb3 = OP.new_codebook("zh-Hant")
calls = []


def fake_open(text, n, total):
    calls.append(n)
    # 每個窗口都給同一個碼（模擬沿用）＋一個該窗口獨有的碼
    return {S.RESPONDENT: "賴經理", OP.OPEN_SEGMENTS: [
        raw_seg(f"共同{n}", f"第{n}窗口談到的人力問題",
                [("護理人力不足", "人數不夠", "反覆出現")]),
        raw_seg(f"獨有{n}", f"第{n}窗口獨有的內容",
                [(f"窗口{n}專屬的碼", "只出現一次", "獨有")]),
    ]}


rec = OP.open_code_transcript(LONG, fake_open, cb3, window=3000, overlap=300)
n_chunks = rec[S.META]["chunking"]["n_chunks"]
ok("每個窗口各呼叫一次", len(calls) == n_chunks, f"{len(calls)}/{n_chunks}")
ok("碼簿累積：共同的碼只有一個",
   len([c for c in cb3[OP.CODES] if c[OP.CODE_LABEL] == "護理人力不足"]) == 1)
check("共同的碼出現次數＝窗口數",
      OP.find_code(cb3, "護理人力不足")[OP.CODE_COUNT], n_chunks)
ok("獨有的碼各自成碼", len(cb3[OP.CODES]) == n_chunks + 1,
   f"{len(cb3[OP.CODES])} 碼 / {n_chunks} 窗")
ok("紀錄裡有段落", len(rec[OP.OPEN_SEGMENTS]) > 0, str(len(rec[OP.OPEN_SEGMENTS])))
ok("段落帶著碼 id 與標籤",
   all(c.get(OP.CODE_ID) and c.get(OP.CODE_LABEL)
       for s in rec[OP.OPEN_SEGMENTS] for c in s[OP.OPEN_CODES]))
ok("provenance 記下模式與碼簿", rec[S.META]["mode"] == "open_coding"
   and rec[S.META]["codebook_id"] == cb3[OP.CODEBOOK_ID])
ok("記下每個窗口新建／沿用了幾個碼",
   len(rec[S.META]["codes_per_chunk"]) == n_chunks)

# 重疊區的重複要被合併，而且**合併過程不可以碰任何框架相關的函式**——
# 開放編碼進行中作用中的框架不含這些碼，依賴它等於讓行為取決於
# 「使用者上一次開的是哪個框架」。這裡刻意先啟用 RI 再合併。
F.reset()                                   # RI 是預設，且它有極性
g1 = [{S.SEGMENT_ID: "S001", S.TITLE: "t", S.QUOTE: "同一句話",
       S.FULL_TEXT: "同一句話（短）",
       OP.OPEN_CODES: [{OP.CODE_ID: "c001", OP.CODE_LABEL: "甲", S.RATIONALE: ""}]}]
g2 = [{S.SEGMENT_ID: "S001", S.TITLE: "t", S.QUOTE: "同一句話",
       S.FULL_TEXT: "同一句話，還有後面比較長的上下文",
       OP.OPEN_CODES: [{OP.CODE_ID: "c002", OP.CODE_LABEL: "乙", S.RATIONALE: ""}]},
      {S.SEGMENT_ID: "S002", S.TITLE: "t2", S.QUOTE: "另一句",
       S.FULL_TEXT: "另一句",
       OP.OPEN_CODES: [{OP.CODE_ID: "c003", OP.CODE_LABEL: "丙", S.RATIONALE: ""}]}]
mg = OP.merge_open_segments([g1, g2])
check("重疊區的重複被合併", len(mg), 2)
check("兩邊的碼都留下來",
      sorted(c[OP.CODE_ID] for c in mg[0][OP.OPEN_CODES]), ["c001", "c002"])
ok("留下比較完整的原文", "後面比較長的上下文" in mg[0][S.FULL_TEXT])
check("合併後重新編號", [s[S.SEGMENT_ID] for s in mg], ["S001", "S002"])
ok("空輸入不炸", OP.merge_open_segments([]) == []
   and OP.merge_open_segments([None]) == [])
ok("空引文的段落被丟掉",
   OP.merge_open_segments([[{S.QUOTE: "", OP.OPEN_CODES: [
       {OP.CODE_ID: "c001", OP.CODE_LABEL: "甲"}]}]]) == [])

# 單一窗口失敗不中斷整輪
def flaky_open(text, n, total):
    if n == 1:
        raise ValueError("壞 JSON")
    return fake_open(text, n, total)


cb4 = OP.new_codebook()
rec2 = OP.open_code_transcript(LONG, flaky_open, cb4, window=3000, overlap=300)
ok("單一窗口失敗不中斷", len(rec2[OP.OPEN_SEGMENTS]) > 0)
ok("失敗的窗口被記下來", rec2[S.META]["chunk_errors"][0]["chunk"] == 1,
   str(rec2[S.META].get("chunk_errors")))

print()
print("=" * 70)
print("測試 5：飽和度曲線（描述，不是判定）")
print("=" * 70)
curve = OP.saturation_curve([rec])
ok("每個窗口一列", len(curve) == n_chunks, f"{len(curve)}")
ok("累計新碼數遞增", all(b["cumulative"] >= a["cumulative"]
                         for a, b in zip(curve, curve[1:])))
ok("第一個窗口新建最多（之後開始沿用）",
   curve[0]["created"] >= curve[-1]["created"],
   f"{curve[0]['created']} → {curve[-1]['created']}")
ok("後面的窗口有沿用紀錄", curve[-1]["reused"] >= 1, str(curve[-1]))
ok("空輸入不炸", OP.saturation_curve([]) == [])

print()
print("=" * 70)
print("測試 6：近義碼只建議、不自動合併")
print("=" * 70)
cb5 = OP.new_codebook("zh-Hant")
for lab in ["時間壓力", "時間的壓力", "法規遵循", "護理人力不足"]:
    OP.add_code(cb5, lab)
for c in cb5[OP.CODES]:
    c[OP.CODE_COUNT] = 3
pairs = OP.similar_pairs(cb5, threshold=0.5)
ok("找得到近義碼", any({p["a_label"], p["b_label"]} == {"時間壓力", "時間的壓力"}
                       for p in pairs), str(pairs))
ok("不相干的碼不配對",
   not any({p["a_label"], p["b_label"]} == {"法規遵循", "護理人力不足"}
           for p in pairs))
ok("similar_pairs 不改動碼簿", len(cb5[OP.CODES]) == 4)

# 合併：要留軌跡
before = OP.find_code(cb5, "時間壓力")[OP.CODE_COUNT]
kept = OP.merge_codes(cb5, OP.find_code(cb5, "時間壓力")[OP.CODE_ID],
                      [OP.find_code(cb5, "時間的壓力")[OP.CODE_ID]],
                      reviewer="研究者")
check("合併後碼數減一", len(cb5[OP.CODES]), 3)
check("次數合併起來", kept[OP.CODE_COUNT], before + 3)
ok("被併掉的標籤留在 merged_from", "時間的壓力" in kept[OP.CODE_MERGED_FROM],
   str(kept[OP.CODE_MERGED_FROM]))
ok("合併動作留在 history",
   any(h["action"] == "merge" and "時間的壓力" in h["detail"]
       for h in kept[OP.CODE_HISTORY]), str(kept[OP.CODE_HISTORY]))
ok("記下是誰合併的", kept[OP.CODE_HISTORY][0]["reviewer"] == "研究者")
try:
    OP.merge_codes(cb5, "不存在的碼", ["c001"])
    ok("合併到不存在的碼要拋錯", False)
except ValueError:
    ok("合併到不存在的碼要拋錯", True)

# 合併要同步改寫紀錄
cb6 = OP.new_codebook()
a = OP.add_code(cb6, "甲"); b = OP.add_code(cb6, "乙")
recs = [{OP.OPEN_SEGMENTS: [
    {S.SEGMENT_ID: "S001", S.QUOTE: "q", OP.OPEN_CODES: [
        {OP.CODE_ID: a[OP.CODE_ID], OP.CODE_LABEL: "甲", S.RATIONALE: ""},
        {OP.CODE_ID: b[OP.CODE_ID], OP.CODE_LABEL: "乙", S.RATIONALE: ""}]}]}]
OP.merge_codes(cb6, a[OP.CODE_ID], [b[OP.CODE_ID]], records=recs)
_codes = recs[0][OP.OPEN_SEGMENTS][0][OP.OPEN_CODES]
check("紀錄裡的碼跟著改", [c[OP.CODE_ID] for c in _codes], [a[OP.CODE_ID]])
ok("合併後同段落不出現重複的碼", len(_codes) == 1)

# 罕見碼：預設不動，要明確呼叫
cb7 = OP.new_codebook()
OP.add_code(cb7, "常見")[OP.CODE_COUNT] = 5
OP.add_code(cb7, "只出現一次")[OP.CODE_COUNT] = 1
dropped = OP.drop_rare_codes(cb7, min_count=2)
check("移除罕見碼", [d[OP.CODE_LABEL] for d in dropped], ["只出現一次"])
check("常見的留著", len(cb7[OP.CODES]), 1)

print()
print("=" * 70)
print("測試 7：碼簿 → 框架（整個設計的關節）")
print("=" * 70)
cb8 = OP.new_codebook("zh-Hant")
for lab, defn in [("護理人力不足", "護理師人數不夠應付工作量"),
                  ("法規更新頻繁", "主管機關頻繁修訂要求"),
                  ("跨部門協調困難", "部門之間的權責不清")]:
    c = OP.add_code(cb8, lab, defn)
    c[OP.CODE_COUNT] = 4
    c[OP.CODE_EXAMPLES] = [{S.QUOTE: f"{lab}的代表引文", S.RESPONDENT: "P1"}]

fw = OP.codebook_to_framework(cb8, "induced_test", "Induced codebook (test)")
ok("轉出來的框架通過驗證", isinstance(fw, F.Framework))
check("維度數＝碼數", len(fw.dimensions), 3)
check("維度 id 就是碼 id", sorted(fw.dimensions), ["c001", "c002", "c003"])
ok("維度標籤是碼的標籤", fw.label("c001", "zh") == "護理人力不足",
   fw.label("c001", "zh"))
ok("定義帶過去", "人數不夠" in fw.definition("c001", "zh"))
ok("代表引文變成指標（之後重新編碼時模型看得到）",
   "護理人力不足的代表引文" in fw.indicators("c001", lang="zh"),
   str(fw.indicators("c001", lang="zh")))
ok("無極性", not fw.has_polarity)
check("編碼數＝維度數（無極性）", len(fw.codes), 3)
ok("出處標為 induced，不是 manual", fw.provenance == F.PROV_INDUCED,
   fw.provenance)
ok("引文說明這是從語料歸納的，不是文獻",
   "open coding" in fw.citation and "Not derived from published literature" in fw.citation,
   fw.citation[:80])
# short code 要合法且唯一
_shorts = [fw.dim_short[d] for d in fw.dimensions]
ok("short code 合法", all(F._SHORT_RE.match(s) for s in _shorts), str(_shorts))
ok("short code 不重複", len(set(_shorts)) == len(_shorts), str(_shorts))
ok("沒有用到保留的 UNC", F.UNASSIGNED_SHORT not in _shorts)

try:
    OP.codebook_to_framework(cb8, "induced_min", "Min", min_count=99)
    ok("沒有碼達到門檻時要拋錯，不要生出空框架", False)
except ValueError:
    ok("沒有碼達到門檻時要拋錯，不要生出空框架", True)

print()
print("=" * 70)
print("測試 8：轉成標準紀錄，接上既有的分析管線")
print("=" * 70)
# 這是整條路真正要證明的事：碼簿變成框架之後，交叉表、共現、主題歸納、
# 信度全部不必改就能用——它們讀的是作用中框架，不在意框架從哪裡來。
open_recs = []
for who in ("P1", "P2"):
    open_recs.append({
        S.RESPONDENT: who,
        OP.OPEN_SEGMENTS: [
            {S.SEGMENT_ID: "S001", S.TITLE: "人力", S.QUOTE: f"{who} 談人力",
             S.FULL_TEXT: f"{who} 談人力的完整段落",
             OP.OPEN_CODES: [{OP.CODE_ID: "c001", OP.CODE_LABEL: "護理人力不足",
                              S.RATIONALE: "明講人數不足"}]},
            {S.SEGMENT_ID: "S002", S.TITLE: "法規與協調",
             S.QUOTE: f"{who} 談法規", S.FULL_TEXT: f"{who} 談法規的完整段落",
             OP.OPEN_CODES: [
                 {OP.CODE_ID: "c002", OP.CODE_LABEL: "法規更新頻繁",
                  S.RATIONALE: "明講更新頻率"},
                 {OP.CODE_ID: "c003", OP.CODE_LABEL: "跨部門協調困難",
                  S.RATIONALE: "同一段也談到協調"}]},
        ],
        S.META: {"mode": "open_coding", "codebook_id": cb8[OP.CODEBOOK_ID]},
    })

# 順序錯了要擋下來：框架還沒啟用就轉，會得到一批空紀錄而且沒人告訴你
F.reset()
try:
    OP.to_records(copy.deepcopy(open_recs))
    ok("框架未啟用就轉換要拋錯（否則靜默產生空紀錄）", False)
except ValueError as e:
    ok("框架未啟用就轉換要拋錯（否則靜默產生空紀錄）",
       "activate" in str(e), str(e)[:70])

F.set_active(fw)
recs_std = OP.to_records(copy.deepcopy(open_recs))
check("轉出兩筆紀錄", len(recs_std), 2)
check("段落數保留", len(recs_std[0][S.SEGMENTS]), 2)
check("碼變成框架的維度",
      sorted(c[S.DIMENSION] for c in recs_std[0][S.SEGMENTS][1][S.CODES_F]),
      ["c002", "c003"])
# codes_of() 回的是**框架的編碼識別碼**（無極性時就是 short code），
# 不是維度 id。兩者在有極性的框架下長得不一樣（ANT-P vs anticipation），
# 在這裡則是 C002 vs c002——大小寫剛好只差一點，最容易寫錯的地方。
check("codes_of 回的是編碼識別碼", sorted(S.codes_of(recs_std[0][S.SEGMENTS][1])),
      ["C002", "C003"])
ok("引文保留", recs_std[0][S.SEGMENTS][0][S.QUOTE] == "P1 談人力")
ok("理由保留",
   recs_std[0][S.SEGMENTS][0][S.CODES_F][0][S.RATIONALE] == "明講人數不足")
ok("記下用的是哪個框架",
   recs_std[0][S.META]["framework_id"] == "induced_test",
   str(recs_std[0][S.META].get("framework_id")))
ok("開放編碼的 provenance 保留下來",
   recs_std[0][S.META]["mode"] == "open_coding")

# --- 既有管線 ---
long_df = A.build_long_df(recs_std)
ok("長表建得起來", not long_df.empty, f"{len(long_df)} 列")
_ct, _pct = A.crosstab_by_descriptor(long_df, S.DESCRIPTOR_KEYS[0])
ok("交叉表的欄名就是歸納出來的碼",
   set(_ct.columns) <= set(fw.codes), str(list(_ct.columns)))
ok("百分比表也算得出來", not _pct.empty or _ct.empty)
cnt, jac, tot = A.cooccurrence(recs_std)
# 共現矩陣的索引是**編碼識別碼**（無極性時就是 short code，這裡是 C002），
# 不是維度 id（c002）。兩者只差大小寫，是這一支測試裡最容易寫錯的地方——
# 上面那個段落斷言也是同一件事。用 fw.code_of() 轉，不要手打字串。
_c2, _c3 = fw.code_of("c002"), fw.code_of("c003")
ok("共現算得出來（同段落兩個碼）",
   int(cnt.loc[_c2, _c3]) == 2, f"{_c2}×{_c3}={int(cnt.loc[_c2, _c3])}")
ok("共現配對清單不炸", not A.cooccurrence_pairs(cnt, tot).empty)
ok("跨案例矩陣不炸", not A.case_matrix(long_df).empty)
ok("資料健檢不炸", len(A.coverage_report(recs_std)) == 2)
per_dim, overall = A.polarity_balance(long_df)
ok("無極性框架不產生極性指數", "polarity_index" not in overall.columns,
   str(list(overall.columns)))

# 主題歸納：一階概念要收得到（歸納那一半本來就在跑，這裡確認接得上）
items = RT.collect_first_order(recs_std)
ok("一階概念收得到", len(items) == 4, str(len(items)))
ok("一階概念帶著碼", all(it[RT.EXISTING_CODES] for it in items))
block = RT._dimension_block("zh")
ok("主題聚斂的提示詞用的是歸納出來的維度",
   "護理人力不足" in block or "c001" in block, block[:120])

print()
print("=" * 70)
print("測試 9：碼簿存檔與統計")
print("=" * 70)
with tempfile.TemporaryDirectory() as d:
    p = OP.save_codebook(cb8, os.path.join(d, "cb.json"))
    back = OP.load_codebook(p)
    check("存讀往返：碼數", len(back[OP.CODES]), len(cb8[OP.CODES]))
    check("存讀往返：標籤", back[OP.CODES][0][OP.CODE_LABEL],
          cb8[OP.CODES][0][OP.CODE_LABEL])
    check("存讀往返：次數", back[OP.CODES][0][OP.CODE_COUNT],
          cb8[OP.CODES][0][OP.CODE_COUNT])
    # 缺欄位的舊碼簿讀進來不可以炸
    import json as _json
    with open(p, "w", encoding="utf-8") as f:
        _json.dump({OP.CODEBOOK_ID: "old", OP.CODES: [{OP.CODE_ID: "c001",
                                                       OP.CODE_LABEL: "x"}]}, f)
    thin = OP.load_codebook(p)
    ok("欄位不全的碼簿讀得進來",
       thin[OP.CODES][0][OP.CODE_COUNT] == 0
       and thin[OP.CODES][0][OP.CODE_EXAMPLES] == [], str(thin[OP.CODES][0]))

st = OP.codebook_stats(cb8)
check("統計：碼數", st["codes"], 3)
check("統計：套用次數", st["applications"], 12)
check("統計：只出現一次的碼", st["singletons"], 0)
ok("統計：沒有定義的碼數得出來", st["undefined"] == 0, str(st))

print()
print("=" * 70)
print("測試 N：模型照抄提示詞裡的碼簿格式時，不能因此多出新的碼")
print("=" * 70)
# 實測（llama3:8b，24 份國會聽證會）：碼簿在提示詞裡顯示成
# "[9x] Guardrails for AI — 定義"，模型沿用時整行照抄，於是同一個碼隨著計數
# 變化一再被當成新碼。647 個碼裡有 95 個帶這種裝飾。
check("去掉計數前綴", OP.clean_label("[9x] Guardrails for AI")[0], "Guardrails for AI")
check("去掉夾帶的定義", OP.clean_label("Guardrails for AI — Describing the need")[0],
      "Guardrails for AI")
check("夾帶的定義另外回傳", OP.clean_label("Guardrails for AI — Describing the need")[1],
      "Describing the need")
check("去掉 New code: 前綴", OP.clean_label("New code: Measuring impact")[0], "Measuring impact")
check("三種裝飾同時出現", OP.clean_label(" [18x] New code: Bias in AI -- unfair outputs ")[0],
      "Bias in AI")
check("正常標籤原樣保留", OP.clean_label("Public trust in deployment")[0],
      "Public trust in deployment")
check("連字號不算分隔（well-known 不能被切開）",
      OP.clean_label("Well-known risks of self-regulation")[0],
      "Well-known risks of self-regulation")
check("空值不炸", OP.clean_label(None), ("", ""))

_cb = OP.new_codebook(language="en")
_raw = {OP.OPEN_SEGMENTS: [
    {S.QUOTE: "q1", OP.OPEN_CODES: [{OP.CODE_LABEL: "Guardrails for AI", OP.CODE_DEFINITION: "d"}]},
    {S.QUOTE: "q2", OP.OPEN_CODES: [{OP.CODE_LABEL: "[1x] Guardrails for AI — d"}]},
    {S.QUOTE: "q3", OP.OPEN_CODES: [{OP.CODE_LABEL: "[2x] guardrails for ai"}]},
    {S.QUOTE: "q4", OP.OPEN_CODES: [{OP.CODE_LABEL: "Audit duties — who checks the checker"}]},
]}
_segs, _st = OP.absorb(_cb, _raw)
check("照抄格式的三次出現算同一個碼", len(_cb[OP.CODES]), 2)
check("其中兩次記為沿用", _st["reused"], 2)
check("碼的計數是 3", OP.find_code(_cb, "Guardrails for AI")[OP.CODE_COUNT], 3)
check("夾帶的定義在沒有定義時被採用",
      OP.find_code(_cb, "Audit duties")[OP.CODE_DEFINITION], "who checks the checker")

F.reset()
print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
