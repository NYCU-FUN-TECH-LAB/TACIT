"""驗證 tacit_irr.py（英文 schema 版）：抽樣框含負例、盲測、信度統計手算對答案。"""
import random as _r
import sys
from collections import Counter as _C

import tacit_schema as S
import tacit_irr as I

FAIL = []


def check(label, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{label}: got={got} want={want}")
    if not ok:
        FAIL.append(label)


def check_true(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + f"{label}" + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


TRANSCRIPT = "\n".join([
    "【訪員】可以談談你們怎麼看未來三到五年的技術發展嗎？",
    "【受訪者】嗯。",
    "【受訪者】我們最懂這個技術，外面的人講什麼我們還是照原計畫走不會改。",
    "【受訪者】不過老實說，我們內部也一直有爭論，我不敢說自己都對。",
    "【訪員】那利害關係人的意見呢？",
    "【受訪者】定案之後再跟他們說明就好了，不需要一開始就問。",
    "【受訪者】對啊。",
    "【受訪者】因為使用者反映介面太複雜，所以我們後來把整個流程改掉了。",
])

print("=" * 70)
print("測試 1：逐字稿切分為發言單元")
print("=" * 70)
units = I.split_units(TRANSCRIPT)
for u in units:
    print(f"   [{u[S.SPEAKER]}] {u[S.TEXT][:34]}")
check_true("過短單元被併入", all(len(I.normalize(u[S.TEXT])) >= 15 for u in units))
check_true("單元數合理", 4 <= len(units) <= 7, f"{len(units)} 個")
check_true("講者標記被解析", any(u[S.SPEAKER] == "訪員" for u in units))
check_true("迴歸：訪員提問未被併入受訪者發言",
           not any(u[S.SPEAKER] == "受訪者" and "利害關係人的意見呢" in u[S.TEXT]
                   for u in units))
check_true("迴歸：無單元同時含兩位講者的話",
           not any("技術發展嗎" in u[S.TEXT] and "我們最懂" in u[S.TEXT] for u in units))


def seg(sid, quote, codes):
    return {S.SEGMENT_ID: sid, S.TITLE: sid, S.QUOTE: quote[:12], S.FULL_TEXT: quote,
            S.CODES_F: [S.make_code(d, p) for d, p in codes]}


RECORDS = [{
    S.RESPONDENT: "產A", S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
    S.SEGMENTS: [
        seg("S1", "我們最懂這個技術，外面的人講什麼我們還是照原計畫走不會改。",
            [(S.REFLEXIVITY, "N"), (S.RESPONSIVENESS, "N")]),
        seg("S2", "定案之後再跟他們說明就好了，不需要一開始就問。",
            [(S.ENGAGEMENT, "N")]),
        seg("S3", "因為使用者反映介面太複雜，所以我們後來把整個流程改掉了。",
            [(S.RESPONSIVENESS, "P")]),
    ]}]

print()
print("=" * 70)
print("測試 2：抽樣框必須包含 AI 未標記的單元（recall 的來源）")
print("=" * 70)
frame, diag = I.build_frame(RECORDS, {"產A": TRANSCRIPT})
print("  診斷:", diag)
for f in frame:
    print(f"   {f[S.UNIT_ID]} [{f[S.STRATUM]}] {f[S.TEXT][:24]}")
check_true("抽樣框非空", len(frame) > 0)
check_true("有 AI 標記的單元", diag["ai_coded_units"] >= 3, str(diag["ai_coded_units"]))
check_true("**有未標記的單元**（否則量不到漏標）", diag["uncoded_units"] >= 1,
           str(diag["uncoded_units"]))
check("AI 引文全部對得回逐字稿", diag["unmatched_quotes"], {})
hit = [f for f in frame if "REF-N" in f[S.AI_CODES]]
check_true("多重編碼單元同時帶兩碼",
           bool(hit) and set(hit[0][S.AI_CODES]) == {"REF-N", "RES-N"})
check_true("訪員提問未被標記",
           any(f[S.SPEAKER] == "訪員" and not f[S.AI_CODES] for f in frame))
check_true("欄位皆為 ASCII", all(k.isascii() for k in frame[0]))
check_true("未標記層用識別碼而非顯示文字",
           any(f[S.STRATUM] == S.STRATUM_UNMARKED for f in frame))

print()
print("=" * 70)
print("測試 3：分層抽樣")
print("=" * 70)
big = []
for i in range(400):
    codes = ["REF-N"] if i % 5 == 0 else (["ANT-P"] if i % 7 == 0 else [])
    if i == 3:
        codes = ["ENG-N"]                      # 稀有碼，只有一個
    big.append({S.UNIT_ID: f"U{i:04d}", S.RESPONDENT: f"R{i % 6}", "position": i,
                S.SPEAKER: "受訪者", S.TEXT: f"單元內容{i}" * 3,
                S.AI_CODES: codes,
                S.STRATUM: "+".join(codes) or S.STRATUM_UNMARKED})
samp = I.stratified_sample(big, n=100, seed=7, min_per_code=4, unmarked_share=0.35)
n_un = sum(1 for s in samp if not s[S.AI_CODES])
print(f"  抽出 {len(samp)}，其中未標記 {n_un}")
check("抽樣數", len(samp), 100)
check_true("未標記比例接近設定值", 30 <= n_un <= 40, f"{n_un}")
check_true("稀有碼 ENG-N 有被抽中", any("ENG-N" in s[S.AI_CODES] for s in samp))
check_true("單元不重複", len({s[S.UNIT_ID] for s in samp}) == len(samp))
check("同種子可重現",
      [s[S.UNIT_ID] for s in samp] ==
      [s[S.UNIT_ID] for s in I.stratified_sample(big, n=100, seed=7)], True)
check_true("不同種子結果不同",
           [s[S.UNIT_ID] for s in samp] !=
           [s[S.UNIT_ID] for s in I.stratified_sample(big, n=100, seed=99)])

print()
print("=" * 70)
print("測試 3b：沒有模型時——純人工對人工的抽樣")
print("=" * 70)
# 手邊沒有模型（或不想用模型）的研究者，一樣要能對自己的逐字稿做兩位
# 人工編碼者的信度。這時抽樣框裡沒有任何單元帶 AI 碼，unmarked_share
# 不該再生效——否則要 100 個單元只會拿到 35 個。
plain = [{**u, S.AI_CODES: [], S.STRATUM: S.STRATUM_UNMARKED} for u in big]
hs = I.stratified_sample(plain, n=100, seed=7)
check("全部未標記時仍抽滿", len(hs), 100)
check_true("單元不重複", len({s[S.UNIT_ID] for s in hs}) == len(hs))
check("同種子可重現",
      [s[S.UNIT_ID] for s in hs] ==
      [s[S.UNIT_ID] for s in I.stratified_sample(plain, n=100, seed=7)], True)
check_true("不同種子結果不同",
           [s[S.UNIT_ID] for s in hs] !=
           [s[S.UNIT_ID] for s in I.stratified_sample(plain, n=100, seed=99)])
check("要的比有的多時，全部給出", len(I.stratified_sample(plain[:12], n=100)), 12)
hframe, hdiag = I.build_frame([], {"產A": TRANSCRIPT})      # 沒有任何紀錄
check_true("沒有紀錄也建得出抽樣框", len(hframe) > 0, str(hdiag))
check("沒有紀錄時 AI 標記數為零", hdiag["ai_coded_units"], 0)
check("沒有紀錄時不會有對不回去的引文", hdiag["unmatched_quotes"], {})
hsess = I.create_session(I.stratified_sample(hframe, n=50, seed=1),
                         ["A", "B"], seed=1)
hrows = I.coding_sheet_rows(hsess, "A")
check_true("純人工編碼表也產得出來", len(hrows) == len(hframe), str(len(hrows)))
check_true("純人工編碼表沒有 AI 欄位",
           all(S.AI_CODES not in r for r in hrows))

print()
print("=" * 70)
print("測試 4：雙盲——編碼表不得洩漏 AI 答案")
print("=" * 70)
sess = I.create_session(samp[:20], ["teacher", "me"], seed=7, note="round 1")
rows = I.coding_sheet_rows(sess, "teacher")
cols = set(rows[0])
print("  編碼表欄位:", sorted(cols))
check_true("不含 AI 編碼欄", S.AI_CODES not in cols)
check_true("不含分層資訊", S.STRATUM not in cols)
check_true("含八個碼欄位", all(c in cols for c in S.CODES))
check_true("session 內部保有 AI 編碼", any(u.get(S.AI_CODES) for u in sess[S.UNITS]))
check("工作階段 ID 長度", len(sess[S.SESSION_ID]), 8)

filled = [dict(r) for r in rows]
filled[0]["REF-N"] = "1"; filled[0]["RES-N"] = "V"
filled[1]["ENG-N"] = "✓"; filled[2]["ANT-P"] = "x"
filled[3]["REF-P"] = "0"; filled[4]["ANT-N"] = ""
filled.append({S.UNIT_ID: "U9999", "REF-N": "1"})
valid = {u[S.UNIT_ID] for u in sess[S.UNITS]}
parsed = I.parse_coding_sheet(filled, valid)
check("多種標記都認得", sorted(parsed[rows[0][S.UNIT_ID]]), ["REF-N", "RES-N"])
check("✓ 認得", parsed[rows[1][S.UNIT_ID]], ["ENG-N"])
check("x 認得", parsed[rows[2][S.UNIT_ID]], ["ANT-P"])
check("0 不算標記", parsed[rows[3][S.UNIT_ID]], [])
check("不存在的 ID 被剔除", "U9999" in parsed, False)

print()
print("=" * 70)
print("測試 5：二元一致度（手算對答案）")
print("=" * 70)
# n=10：雙方皆標 3、皆未標 5、僅A 1、僅B 1
a = [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]
b = [1, 1, 1, 0, 1, 0, 0, 0, 0, 0]
r = I.binary_agreement(a, b)
print("  ", r)
check("一致率", r[I.AGREEMENT], 0.8)          # 8/10
check("Cohen's κ", r[I.KAPPA], 0.583)         # (.8-.52)/.48
check("PABAK", r[I.PABAK], 0.6)               # 2*.8-1
check("Gwet's AC1", r[I.AC1], 0.615)          # (.8-.48)/.52
check("雙方皆標", r[I.BOTH], 3)
check("僅A標", r[I.ONLY_A], 1)
check_true("欄位皆為 ASCII", all(k.isascii() for k in r))

print()
print("  -- kappa paradox：一致率高但 κ 低 --")
a2 = [1] + [0] * 99
b2 = [1] + [0] * 99
for i in range(1, 4):
    a2[i] = 1
for i in range(4, 6):
    b2[i] = 1
r2 = I.binary_agreement(a2, b2)
print("  ", {k: r2[k] for k in (I.AGREEMENT, I.KAPPA, I.PABAK, I.AC1,
                                I.PREVALENCE_INDEX)})
check_true("一致率很高", r2[I.AGREEMENT] >= 0.94)
check_true("κ 明顯偏低", r2[I.KAPPA] < 0.4, f"κ={r2[I.KAPPA]}")
check_true("PABAK 高於 κ", r2[I.PABAK] > r2[I.KAPPA])
check_true("AC1 高於 κ", r2[I.AC1] > r2[I.KAPPA])
verdict = I.interpret(r2[I.KAPPA], r2[I.PABAK], r2[I.AC1], r2[I.PREVALENCE_INDEX])
print("  判讀:", verdict)
check("判讀為 paradox", verdict["is_paradox"], True)
check("κ 落在 fair 區間", verdict["band"], I.BAND_FAIR)
check_true("判讀結果不含顯示文字（交給 i18n）",
           all(not isinstance(v, str) or v.isascii() for v in verdict.values()))
normal = I.interpret(0.85, 0.86, 0.87, 0.1)
check("高一致度不判為 paradox", normal["is_paradox"], False)
check("高一致度分級", normal["band"], I.BAND_ALMOST_PERFECT)
check("κ 為 None 時分級", I.kappa_band(None), I.BAND_NA)

print()
print("=" * 70)
print("測試 6：Krippendorff's α — 手算重合矩陣 + Scott's π 交叉驗證")
print("=" * 70)
# 9 個可配對單元；o[1,1]=4 o[2,2]=6 o[3,3]=4 o[4,4]=2 o[1,2]=1 o[2,1]=1
# n_1=5 n_2=7 n_3=4 n_4=2；n=18；Do=2
# Σ_{c≠k} n_c·n_k = 324 − 94 = 230；De = 230/17 = 13.5294；α = 0.8522
A = [1, 2, 3, 3, 2, 1, 4, 1, 2, None, None, None]
B = [1, 2, 3, 3, 2, 2, 4, 1, 2, 5, None, 3]
vals = {}
for i, (x, y) in enumerate(zip(A, B)):
    vs = [v for v in (x, y) if v is not None]
    if len(vs) >= 2:
        vals[i] = vs
check("只計入兩人都編碼的單元", len(vals), 9)
check("手算案例 α = 0.852", I.krippendorff_alpha_nominal(vals), 0.852)
# 三位編碼者：n_1=5 n_0=4 n=9 Do=2 De=40/8=5 → α=0.6
check("三位編碼者手算 α = 0.6",
      I.krippendorff_alpha_nominal({1: [1, 1, 1], 2: [0, 0, 0], 3: [1, 1, 0]}), 0.6)


def scott_check(pairs):
    """獨立實作：α = 1 − ((n−1)/n)·(1−Po)/(1−Pe_scott)，n = 2N。"""
    N = len(pairs)
    po = sum(1 for x, y in pairs if x == y) / N
    allv = [v for p in pairs for v in p]
    n = len(allv)
    pe = sum((c / n) ** 2 for c in _C(allv).values())
    if abs(1 - pe) < 1e-12:
        return None
    return round(1 - ((n - 1) / n) * (1 - po) / (1 - pe), 3)


rng = _r.Random(11)
for trial in range(5):
    pairs = [(rng.choice([0, 1, 2]), rng.choice([0, 1, 2])) for _ in range(40)]
    mine = I.krippendorff_alpha_nominal({i: list(p) for i, p in enumerate(pairs)})
    theirs = scott_check(pairs)
    ok = abs(mine - theirs) < 0.002
    print(f"   trial{trial}: 本實作 α={mine}　獨立公式={theirs}　{'OK' if ok else 'X'}")
    if not ok:
        FAIL.append(f"Scott π trial{trial}")
check_true("五組隨機資料與獨立公式一致",
           not any(str(f).startswith("Scott") for f in FAIL))
check("完全一致 α = 1",
      I.krippendorff_alpha_nominal({1: [1, 1], 2: [0, 0], 3: [1, 1]}), 1.0)
check_true("系統性相反時 α 為負",
           I.krippendorff_alpha_nominal(
               {1: [1, 0], 2: [0, 1], 3: [1, 0], 4: [0, 1]}) < 0)
check("逐碼介面完全一致",
      I.krippendorff_alpha({"t": {"U1": ["REF-N"], "U2": []},
                            "m": {"U1": ["REF-N"], "U2": []}},
                           ["U1", "U2"], "REF-N"), 1.0)

print()
print("=" * 70)
print("測試 7：pooled κ、混淆矩陣、極性、分歧清單")
print("=" * 70)
sess2 = I.create_session([
    {S.UNIT_ID: "U1", S.RESPONDENT: "產A", S.SPEAKER: "", S.TEXT: "我們最懂這個技術",
     S.STRATUM: "REF-N", S.AI_CODES: ["REF-N"]},
    {S.UNIT_ID: "U2", S.RESPONDENT: "產A", S.SPEAKER: "", S.TEXT: "定案後再說明",
     S.STRATUM: "ENG-N", S.AI_CODES: ["ENG-N"]},
    {S.UNIT_ID: "U3", S.RESPONDENT: "產A", S.SPEAKER: "", S.TEXT: "我們找大家一起討論",
     S.STRATUM: S.STRATUM_UNMARKED, S.AI_CODES: []},
    {S.UNIT_ID: "U4", S.RESPONDENT: "產A", S.SPEAKER: "", S.TEXT: "這個嘛就那樣",
     S.STRATUM: S.STRATUM_UNMARKED, S.AI_CODES: []},
], ["teacher", "me"])
uids = [u[S.UNIT_ID] for u in sess2[S.UNITS]]
teacher = {"U1": ["REF-N"], "U2": ["ENG-N"], "U3": ["ENG-P"], "U4": []}
me = {"U1": ["REF-N", "RES-N"], "U2": ["ENG-P"], "U3": ["ENG-P"], "U4": []}

pc = I.per_code_agreement(teacher, me, uids)
refn = next(r for r in pc if r["code"] == "REF-N")
check("REF-N 雙方皆標 1 次", refn[I.BOTH], 1)
check("REF-N 完全一致", refn[I.AGREEMENT], 1.0)

pk = I.pooled_kappa(teacher, me, uids)
print("  pooled:", {k: pk[k] for k in (I.N_OBS, I.AGREEMENT, I.KAPPA, I.PABAK, I.AC1)})
check("pooled 觀察數 = 4 單元 × 8 碼", pk[I.N_OBS], 32)
check("完全一致的單元比例", I.exact_set_agreement(teacher, me, uids), 0.5)

labels, mat = I.dimension_confusion(teacher, me, uids)
check_true("混淆矩陣標籤為識別碼", all(l.isascii() for l in labels))
check("U4 雙方皆判無", mat[S.NONE_LABEL][S.NONE_LABEL], 1)
check("參與 × 參與", mat[S.ENGAGEMENT][S.ENGAGEMENT], 2)

pol = I.polarity_confusion(teacher, me, uids)
eng = next(r for r in pol if r[S.DIMENSION] == S.ENGAGEMENT)
print("  參與極性:", eng)
check("參與：一致 1、相反 1",
      (eng["polarity_agree"], eng["polarity_conflict"]), (1, 1))

dis = I.disagreement_list(sess2, {"teacher": teacher, "me": me}, "teacher", "me")
for d in dis:
    print(f"    {d[S.UNIT_ID]} [{d['disagreement_type']}] "
          f"a={d['codes_a']} b={d['codes_b']}")
check("分歧單元數", len(dis), 2)
check("極性相反排最前", dis[0]["disagreement_type"], I.DISAGREE_POLARITY)
check_true("分歧清單欄位為 ASCII", all(k.isascii() for k in dis[0]))

print()
print("=" * 70)
print("測試 8：AI 的 precision / recall")
print("=" * 70)
rec = I.recall_estimate(sess2, teacher)
engp = next(r for r in rec if r["code"] == "ENG-P")
print("  ENG-P:", engp)
check("ENG-P 抓到漏標", engp["fn_ai_missed"], 1)
check("ENG-P Recall = 0", engp["recall"], 0.0)
refn2 = next(r for r in rec if r["code"] == "REF-N")
check("REF-N 一致", (refn2["tp"], refn2["fp_ai_extra"], refn2["fn_ai_missed"]), (1, 0, 0))
check("REF-N Recall = 1", refn2["recall"], 1.0)

print()
print("=" * 70)
print("測試 8b：人工編碼表要變成可以分析的紀錄")
print("=" * 70)
# 沒有這條路的話，編碼表匯進來只算了信度就停住。交叉表、共現、跨個案
# 矩陣、詞彙探勘這些**本來就不需要模型**的引擎讀不到它，於是「手邊沒有
# 模型的研究者能做什麼」的答案就只有一個係數。
import tacit_analysis as _A                                      # noqa: E402
import tacit_themes as _TH                                       # noqa: E402

sess2[S.HUMAN_CODINGS] = {"teacher": teacher, "me": me}
_recs = I.records_from_codings(sess2, "teacher")
check_true("一位受訪者一筆紀錄", len(_recs) == 1, str(len(_recs)))
check("受訪者名字沿用抽樣框的", _recs[0][S.RESPONDENT], "產A")
_segs = [s for r in _recs for s in r[S.SEGMENTS]]
check("段落數等於這位編碼者標記過的單元數",
      len(_segs), sum(1 for v in teacher.values() if v))
check_true("沒有標記的單元不會變成空段落", all(S.codes_of(s) for s in _segs))
check("段落順序照逐字稿而不是抽樣順序",
      [s[S.SEGMENT_ID] for s in _segs], ["S001", "S002", "S003"])
check_true("引文就是該單元的原文（不替編碼者框一段他沒框的）",
           all(s[S.QUOTE] == s[S.FULL_TEXT] for s in _segs))
check_true("複核狀態記為人工確認",
           all(s[S.REVIEW][S.SOURCE] == S.SOURCE_HUMAN and
               s[S.REVIEW][S.STATUS] == S.STATUS_CONFIRMED for s in _segs))
check("原始編碼留空（沒有模型草稿被覆蓋）",
      sorted({len(s[S.REVIEW][S.ORIGINAL_CODES]) for s in _segs}), [0])
check_true("模型在抽樣框裡標過什麼，不會混進人工紀錄",
           S.codes_of(_segs[2]) == ["ENG-P"],
           str(S.codes_of(_segs[2])))      # U3 模型沒標，人標了 ENG-P
_m = _recs[0][S.META]
check_true("_meta 看得出這批是人工編碼", _m["source"].startswith("human-coding"))
check("_meta 記下是誰編的", _m["coder"], "teacher")
check("_meta 的 endpoint 明確留空，而不是省略", _m["endpoint"], None)
check_true("_meta 帶著工作階段與種子，抽樣可回溯",
           _m["session_id"] == sess2[S.SESSION_ID] and _m["seed"] == sess2[S.SEED])
check_true("通得過 schema 遷移",
           all(S.migrate_record(r).get(S.SEGMENTS) for r in _recs))

# 真正的重點：這些紀錄餵得進不需要模型的分析引擎
_long = _A.build_long_df(_recs)
check("長表列數 = 段落裡的編碼數",
      len(_long), sum(len(S.codes_of(s)) for s in _segs))
_c, _j, _t = _A.cooccurrence(_recs)
check_true("共現算得出來", int(_t.sum()) > 0, str(int(_t.sum())))
check_true("跨個案矩陣畫得出來", _A.case_matrix(_long).shape[0] > 0)
check("一階概念收得出來", len(_TH.collect_first_order(_recs)), len(_segs))

check("沒有任何標記時不產生紀錄",
      I.records_from_codings({S.SESSION_ID: "x", S.UNITS: sess2[S.UNITS],
                              S.HUMAN_CODINGS: {"z": {u: [] for u in uids}}}, "z"), [])
check("不存在的編碼者回空清單", I.records_from_codings(sess2, "nobody"), [])
_with_d = I.records_from_codings(sess2, "teacher",
                                 descriptors={"產A": {"institution_type": "academia"}})
check("研究者填的個案描述子有帶進去",
      _with_d[0][S.DESCRIPTORS].get("institution_type"), "academia")

print()
print("=" * 70)
print("測試 9：邊界情況")
print("=" * 70)
check("空逐字稿切分", I.split_units(""), [])
check("空輸入抽樣框", I.build_frame([], {})[0], [])
check("空抽樣框抽樣", I.stratified_sample([], n=50), [])
check("空一致度不炸", I.binary_agreement([], [])[I.KAPPA], None)
check("無編碼時 α 回 None", I.krippendorff_alpha_nominal({}), None)
check("單一編碼者不計入 α", I.krippendorff_alpha_nominal({1: [1]}), None)
empty = {u: [] for u in uids}
check("雙方全空時 κ 無定義", I.pooled_kappa(empty, empty, uids)[I.KAPPA], None)
check("雙方全空時一致率為 1", I.pooled_kappa(empty, empty, uids)[I.AGREEMENT], 1.0)
check("無單元時完全一致率回 None", I.exact_set_agreement({}, {}, []), None)

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
