"""驗證 tacit_lexicon.py（英文 schema 版）：詞庫遷移、新詞發現、z 分數、編碼規則、稽核。"""
import sys
import copy
import json
import random
import tacit_schema as S
import tacit_lexicon as L
import tacit_framework as F
import os
import tempfile

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


HEADS = ["我們認為", "他提到", "報告指出", "團隊覺得", "後來發現", "主管說明",
         "受訪者強調", "資料顯示", "會議上談到", "當時的想法是", "坦白講",
         "以我的經驗", "公司內部對於", "那個時候"]
TAILS = ["很重要", "有困難", "需要調整", "還在發展", "值得參考", "不容易做",
         "已經開始", "尚待驗證", "有待商榷", "是關鍵", "常常被忽略",
         "其實沒那麼簡單", "後來就停掉了", "算是有進展"]


def sprinkle(term, n, seed=0):
    rnd = random.Random(seed)
    return [f"{rnd.choice(HEADS)}{term}{rnd.choice(TAILS)}" for _ in range(n)]


print("=" * 70)
print("測試 1：詞庫結構已改為 ASCII 鍵，語言資料維持中文")
print("=" * 70)
lex = L.load_lexicon("tacit_lexicon_zh.json")
check("語言標記", lex[L.LANGUAGE], "zh-Hant")
check_true("結構鍵皆為 ASCII",
           all(k.isascii() for k in lex) and
           all(d.isascii() for d in lex[L.CONCEPT_TERMS]))
check_true("維度鍵為 schema 識別碼",
           set(lex[L.CONCEPT_TERMS]) == set(S.DIMENSIONS))
check_true("概念詞內容仍是中文",
           any('一' <= ch <= '鿿'
               for ch in "".join(lex[L.CONCEPT_TERMS][S.REFLEXIVITY]["N"])))
check("強制詞數", len(lex[L.FORCE_TERMS]), 64)
check("句式模板數", len(lex[L.PATTERNS]), 17)
check_true("模板識別碼皆 ASCII 且具語意",
           all(k.isascii() and "_" in k for k in lex[L.PATTERNS]))
spec = lex[L.PATTERNS]["RES_P_causal_adjustment"]
check("模板帶維度", spec[S.DIMENSION], S.RESPONSIVENESS)
check("模板帶極性", spec[S.POLARITY], "P")
check_true("模板說明中英皆有",
           L.pattern_note(spec, "en") and L.pattern_note(spec, "zh"))
check_true("所有模板都有英文說明",
           all(L.pattern_note(s_, "en") for s_ in lex[L.PATTERNS].values()))

print()
print("  -- 舊版中文鍵詞庫仍可載入 --")
old = json.load(open("tacit_seed_lexicon.json", encoding="utf-8"))
mig = L.migrate_lexicon(old, "zh-Hant")
check("舊檔遷移後模板數", len(mig[L.PATTERNS]), 17)
check("遷移冪等", L.migrate_lexicon(json.loads(json.dumps(mig))), mig)
check("空輸入不炸", L.migrate_lexicon(None)[L.FORCE_TERMS], [])
stats = {r["code"]: r["term_count"] for r in L.lexicon_stats(lex)}
check("統計欄位為 ASCII code", sorted(stats) == sorted(S.CODES), True)
check("概念詞總數", sum(stats.values()), 239)

print()
print("=" * 70)
print("測試 2：斷詞——強制詞不可被切開")
print("=" * 70)
seg = L.Segmenter(force_words=lex[L.FORCE_TERMS], backend="ngram")
toks = seg.cut("我們在談負責任創新的時候一定要找利害關係人進來")
print("  ", toks)
check_true("「負責任創新」完整", "負責任創新" in toks)
check_true("「利害關係人」完整", "利害關係人" in toks)
check_true("未被切成「負責」", "負責" not in toks)

print()
print("=" * 70)
print("測試 3：無詞典新詞發現")
print("=" * 70)
corpus = sprinkle("韌性治理框架", 26, seed=1) + \
    ["今天天氣很好我們去散步", "這份文件需要重新整理一次"] * 6
found = L.discover_terms(corpus, min_freq=3, min_pmi=1.0, min_entropy=0.5)
words = [r["term"] for r in found]
print("  前 8 名:", words[:8])
check_true("撈得到植入術語", "韌性治理框架" in words, f"{len(words)} 個候選")
check("跨邊界碎片被濾掉", [w for w in words if w in ("性治", "治理框", "理框架")], [])
check_true("回傳欄位為 ASCII",
           all(k.isascii() for k in found[0]) if found else False)

print()
print("=" * 70)
print("測試 4：特徵詞誘導 z 分數")
print("=" * 70)
code_texts = {c: [] for c in S.CODES}
code_texts["REF-N"] = sprinkle("專業權威", 14, seed=2)
code_texts["ENG-P"] = sprinkle("共同討論", 14, seed=3)
code_texts["ANT-P"] = sprinkle("情境規劃", 14, seed=4)
for c in ("REF-N", "ENG-P", "ANT-P"):
    code_texts[c] += sprinkle("我們公司", 8, seed=5)

ind = L.induce_features(code_texts, lexicon=lex, min_count=3, top_n=10,
                        discover_kwargs={"min_freq": 3, "min_pmi": 1.0,
                                         "min_entropy": 0.5})
for c in ["REF-N", "ENG-P", "ANT-P"]:
    print(f"  {c}: " + ", ".join(f"{r['term']}({r['z']})" for r in ind[c][:3]))
check_true("REF-N 頭號特徵詞", ind["REF-N"] and ind["REF-N"][0]["term"] == "專業權威")
check_true("ENG-P 頭號特徵詞", ind["ENG-P"] and ind["ENG-P"][0]["term"] == "共同討論")
check_true("ANT-P 頭號特徵詞", ind["ANT-P"] and ind["ANT-P"][0]["term"] == "情境規劃")
check_true("z 顯著", ind["REF-N"][0]["z"] > 2.0, f"z={ind['REF-N'][0]['z']}")
shared = [r for r in ind["REF-N"] if r["term"] == "我們公司"]
check_true("共有詞被壓抑",
           (not shared) or shared[0]["z"] < ind["REF-N"][0]["z"] / 2)
allw = {r["term"] for rows in ind.values() for r in rows}
check("無碎片污染", sorted(w for w in allw if w in ("的專", "們公", "司的")), [])

print()
print("=" * 70)
print("測試 5：詞典編碼器規則")
print("=" * 70)
coder = L.DictionaryCoder(lex)
codes, sc, _ = coder.code_text("我們每個月都找利害關係人一起討論產品方向")
check_true("肯定句判 ENG-P", "ENG-P" in codes)

c2, s2, h2 = coder.code_text("我們沒有找利害關係人討論就直接做了")
print(f"  否定句 → {c2}  ENG-P={s2['ENG-P']} ENG-N={s2['ENG-N']}")
check("否定句判 ENG-N", c2, ["ENG-N"])
check_true("重疊詞只計一次",
           "關係人" not in [h["term"] for h in h2 if h["kind"] == "term"])
check_true("正向句式被否定翻轉",
           all(h["effective_polarity"] == "N" for h in h2 if h["kind"] == "pattern"))

c3, s3, _ = coder.code_text("這個規格已經來不及改了")
check_true("負向句式不被二次翻轉", "RES-N" in c3, str(c3))
c4, s4, _ = coder.code_text("因為使用者反映介面太複雜所以我們把整個流程改掉了")
check_true("因果調整句式命中", s4["RES-P"] > 0)
_, s5, _ = coder.code_text("有人說我們最懂這個技術")
_, s6, _ = coder.code_text("我們最懂這個技術")
check_true("傳述句降權", s5["REF-N"] < s6["REF-N"])
ct, st_, _ = coder.code_text("雖然一開始沒有問民眾但是後來我們辦了公聽會蒐集回饋")
check_true("轉折之後立場勝出", st_["ENG-P"] > st_["ENG-N"])
check_true("命中明細欄位為 ASCII", all(k.isascii() for k in h2[0]) if h2 else False)

print()
print("=" * 70)
print("測試 6：Cohen's kappa")
print("=" * 70)
check("完全一致", round(L.cohens_kappa([1, 1, 0, 0], [1, 1, 0, 0]), 3), 1.0)
check("等同隨機", round(L.cohens_kappa([1, 1, 0, 0], [1, 0, 1, 0]), 3), 0.0)
check("完全相反", round(L.cohens_kappa([1, 1, 0, 0], [0, 0, 1, 1]), 3), -1.0)
k = L.cohens_kappa([1, 1, 1, 1], [1, 1, 1, 1])
check_true("無變異回 nan", k != k)
check("手算 κ=0.4",
      round(L.cohens_kappa([1, 1, 1, 1, 1, 1, 0, 0, 0, 0],
                           [1, 1, 1, 1, 0, 0, 1, 0, 0, 0]), 3), 0.4)

print()
print("=" * 70)
print("測試 7：對照與稽核（使用新 schema 的紀錄）")
print("=" * 70)


def mkseg(sid, txt, codes):
    return {S.SEGMENT_ID: sid, S.TITLE: sid, S.QUOTE: txt, S.FULL_TEXT: txt,
            S.CODES_F: [S.make_code(d, p) for d, p in codes]}


records = [{
    S.RESPONDENT: "測試甲", S.DESCRIPTORS: S.blank_descriptors(), S.SUMMARY: "",
    S.SEGMENTS: [
        mkseg("S1", "我們每季都找利害關係人一起討論", [(S.ENGAGEMENT, "P")]),
        mkseg("S2", "嗯這個嘛就是那樣子啦你知道的", [(S.REFLEXIVITY, "N")]),
        mkseg("S3", "因為使用者反映所以我們把規格改掉並且決定不做那個功能", []),
    ]}]
per_code, summary, seg_rows = L.compare_coders(records, coder)
print("  摘要:", summary)
check("段落數", summary["segments"], 3)
row = next(r for r in per_code if r["code"] == "ENG-P")
check("ENG-P TP", row["tp"], 1)
check_true("逐碼欄位為 ASCII", all(k.isascii() for k in row))

over, miss = L.audit_llm_coding(seg_rows, miss_threshold=1.0)
print("  疑似過度詮釋:", [(o[S.SEGMENT_ID], o["code"]) for o in over])
print("  疑似漏標:", [(m[S.SEGMENT_ID], m["code"], m["dict_score"]) for m in miss][:3])
check_true("S2 標為過度詮釋",
           any(o[S.SEGMENT_ID] == "S2" and o["code"] == "REF-N" for o in over))
check_true("S3 標為漏標 RES-P",
           any(m[S.SEGMENT_ID] == "S3" and m["code"] == "RES-P" for m in miss))
check_true("S1 未被誤判", not any(o[S.SEGMENT_ID] == "S1" for o in over))

ct_map = L.code_texts_from_records(records)
check("code_texts 以 ASCII code 為鍵", sorted(k for k in ct_map if ct_map[k]),
      ["ENG-P", "REF-N"])

print()
print("=" * 70)
print("測試 8：合併與邊界")
print("=" * 70)
lex2 = copy.deepcopy(lex)
before = len(lex2[L.CONCEPT_TERMS][S.REFLEXIVITY]["N"])
added = L.merge_into_lexicon(lex2, ind, min_z=2.0, max_per_code=5)
print("  新增:", [(a["code"], a["term"], a["z"]) for a in added])
check_true("有詞被合併", len(added) > 0)
check_true("反思性-N 增加",
           len(lex2[L.CONCEPT_TERMS][S.REFLEXIVITY]["N"]) > before)
check_true("合併項欄位為 ASCII", all(k.isascii() for k in added[0]))
check("dry_run 一致",
      len(L.merge_into_lexicon(copy.deepcopy(lex), ind, min_z=2.0,
                               max_per_code=5, dry_run=True)), len(added))
check("不重複加入", len(L.merge_into_lexicon(lex2, ind, min_z=2.0, max_per_code=5)), 0)

check("空語料發現", L.discover_terms([]), [])
check("空語料誘導", L.induce_features({c: [] for c in S.CODES}),
      {c: [] for c in S.CODES})
check("空字串編碼", coder.code_text("")[0], [])
check("純標點編碼", coder.code_text("，。；！")[0], [])
check("空紀錄對照", L.compare_coders([], coder)[1]["segments"], 0)
v, d = L.build_vocabulary([], lex)
check_true("空語料仍含詞庫既有詞", len(v) > 100, f"{len(v)} 詞")

print()
print("=" * 70)
print("測試 N：虛詞邊界過濾（跨詞邊界碎片不得成為候選詞）")
print("=" * 70)
# 「的模型」「化的」在統計上凝固度高、鄰字也夠分散，光靠 PMI 與熵擋不掉；
# 這類碎片一旦進入詞彙表，就會拿到很高的 z 分數並污染特徵詞誘導的結果。
for frag in ["的模型", "的參與", "化的", "了解決", "很", "都"]:
    check_true(f"判定為碎片：{frag}", L._is_fragment(frag))
for word in ["模型", "利害關係人", "過程", "著手", "回應性", "資料集"]:
    check_true(f"不誤判為碎片：{word}", not L._is_fragment(word))

# 用合成示範語料實測：這批碎片正是在這份語料上被發現的（「的模型」「化的」）。
# 語料要夠長且用詞夠多樣，鄰字熵才有意義——極短或高度重複的語料
# 會讓所有候選詞的熵趨近於零，測不出這一項。
import demo_transcripts_zh as DT

demo_corpus = [DT.text_of(r) for r in DT.all_ids()]
found = {r["term"] for r in L.discover_terms(demo_corpus)}
check_true("示範語料發現足量候選詞", len(found) > 100, f"{len(found)} 詞")
check_true("新詞發現不吐出虛詞碎片",
           not any(L._is_fragment(t) for t in found),
           str(sorted(t for t in found if L._is_fragment(t))[:6]))
check_true("領域詞仍被保留",
           len({"號誌", "路口", "廠商", "說明會", "輪椅"} & found) >= 3,
           str(sorted({"號誌", "路口", "廠商", "說明會", "輪椅"} & found)))

demo_feats = L.induce_features({"industry": demo_corpus[:2],
                                "academia": demo_corpus[2:4],
                                "government": [demo_corpus[4]],
                                "nonprofit": [demo_corpus[5]]})
feat_terms = [r["term"] for rows in demo_feats.values() for r in rows]
check_true("特徵詞誘導結果不含碎片",
           not any(L._is_fragment(t) for t in feat_terms),
           str([t for t in feat_terms if L._is_fragment(t)][:6]))
check_true("特徵詞誘導結果不含功能詞",
           not any(L.is_function_word(t) for t in feat_terms),
           str([t for t in feat_terms if L.is_function_word(t)][:6]))

# 功能詞：不是錯的，只是沒有領域內容——預設濾掉，需要時取得回來
for w in ("沒有", "這個", "其實", "比較", "覺得", "然後", "我們", "如果"):
    check_true(f"認得功能詞：{w}", L.is_function_word(w))
for w in ("風險", "未來", "參與", "責任", "影響", "問題", "揭露", "臨床"):
    check_true(f"不把可能的構念當功能詞：{w}", not L.is_function_word(w))

demo_all = {r["term"] for r in L.discover_terms(demo_corpus)}
demo_with = {r["term"] for r in
             L.discover_terms(demo_corpus, include_function_words=True)}
check_true("預設濾掉功能詞", not any(L.is_function_word(t) for t in demo_all))
check_true("需要時可取回功能詞", len(demo_with) > len(demo_all),
           f"{len(demo_with)} > {len(demo_all)}")

# 斷詞用的詞彙表**必須**含功能詞，否則「這個案子」會被切成「個案子」
vocab_fw, _ = L.build_vocabulary(demo_corpus)
check_true("詞彙表含功能詞（斷詞需要）",
           len({"這個", "那個", "我們"} & vocab_fw) >= 2,
           str(sorted({"這個", "那個", "我們"} & vocab_fw)))

print()
print("=" * 70)
print("測試 P：詞庫與框架不符必須明說（不得靜默清空）")
print("=" * 70)
# 要防的失效：切換到自建框架後載入 RI 詞庫，migrate_lexicon 用
# S.norm_dimension() 正規化維度名稱，而它只認得作用中框架的維度，
# 於是 239 個概念詞與 17 個模板被逐一丟棄。不報錯，只是詞典編碼器
# 一個碼都標不出來——畫面顯示 κ=0.0、編碼 89/0，看起來像功能壞了。
F.reset()
real = L.load_lexicon("tacit_lexicon_zh.json")
check("詞庫有宣告自己屬於哪個框架",
      L.lexicon_framework(real), F.DEFAULT_FRAMEWORK_ID)
check("框架相符時不報警", L.framework_mismatch(real), None)
n_terms = sum(len(real[L.CONCEPT_TERMS][d][p])
              for d in S.DIMENSIONS for p in S.POLARITIES)
check_true("相符時詞條完整載入", n_terms > 200, str(n_terms))
check_true("相符時句式模板完整載入", len(real[L.PATTERNS]) >= 15,
           str(len(real[L.PATTERNS])))

with tempfile.TemporaryDirectory() as d:
    real_dir = F.FRAMEWORK_DIR
    F.FRAMEWORK_DIR = d
    F.ensure_builtin_on_disk()
    other = F.blank("other_theory", "Other Theory",
                    [("alpha", "ALP", "Alpha", "甲"), ("beta", "BET", "Beta", "乙")])
    F.set_active(other)
    try:
        lex2 = L.load_lexicon("tacit_lexicon_zh.json")
        mm = L.framework_mismatch(lex2)
        check_true("框架不符時一定要報出來", mm is not None)
        check("報告裡指出詞庫屬於哪個框架",
              mm["lexicon_framework"], F.DEFAULT_FRAMEWORK_ID)
        check("報告裡指出目前是哪個框架", mm["active_framework"], "other_theory")
        check("報告裡說明詞條剩幾個（0 才是問題所在）",
              mm["terms_after_load"], 0)
        check("報告裡說明模板剩幾個", mm["patterns_after_load"], 0)
        # 這才是使用者會看到的後果
        coder = L.DictionaryCoder(lex2)
        codes, _, _ = coder.code_text("我們有做情境規劃，也找了利害關係人一起討論。")
        check("不符時詞典編碼器確實標不出東西（所以更要事先警告）", codes, [])
    finally:
        F.FRAMEWORK_DIR = real_dir
        F.reset()

print()
print("  -- 存檔不得以空詞庫覆蓋既有內容（這是資料損毀，不是使用者失誤）--")
check("詞庫大小＝概念詞＋模板", L.lexicon_size(real), 256)
check("空詞庫大小為 0", L.lexicon_size(L.blank_lexicon()), 0)
check("None 不炸", L.lexicon_size(None), 0)
with tempfile.TemporaryDirectory() as d:
    p = os.path.join(d, "lex.json")
    L.save_lexicon(real, p)
    check("正常詞庫可存檔", L.lexicon_size(L.load_lexicon(p)), 256)
    try:
        L.save_lexicon(L.blank_lexicon(), p)
        check_true("空詞庫覆蓋非空檔案必須被擋下", False)
    except L.LexiconWriteRefused as e:
        check_true("空詞庫覆蓋非空檔案必須被擋下", True, str(e)[:50])
    check("被擋下後檔案完好無損", L.lexicon_size(L.load_lexicon(p)), 256)
    p2 = os.path.join(d, "brand_new.json")
    L.save_lexicon(L.blank_lexicon(), p2)
    check_true("全新檔案存空詞庫是允許的（沒有東西會被蓋掉）",
               os.path.exists(p2))
    L.save_lexicon(L.blank_lexicon(), p, allow_empty=True)
    check("明確指定 allow_empty 時才放行", L.lexicon_size(L.load_lexicon(p)), 0)

check_true("重置後回到相符狀態",
           L.framework_mismatch(L.load_lexicon("tacit_lexicon_zh.json")) is None)
check_true("新建的空詞庫會標記目前框架",
           L.lexicon_framework(L.blank_lexicon()) == F.active().id)

print()
print("=" * 70)
print("測試 O：語言偵測與斷詞後端路由")
print("=" * 70)
EN_TEXT = """We involve stakeholder groups early in the design process because
responsible innovation demands it. The stakeholder engagement was not a
consultation exercise; we changed the risk assessment after the community
raised concerns about privacy. Anticipatory governance means thinking about
plausible futures before the technology is locked in."""
ZH_TEXT = "我們認為負責任創新很重要，這個案子的方法是先做風險評估，再談技術落地。"

check("純英文判為 en", L.detect_script(EN_TEXT), "en")
check("純中文判為 zh", L.detect_script(ZH_TEXT), "zh")
check("中文夾雜英文術語仍判為 zh",
      L.detect_script("我們談 responsible innovation，也就是負責任創新的概念。"), "zh")
check("英文夾雜少量中文仍判為 en",
      L.detect_script(EN_TEXT + " (台灣)"), "en")
check("空字串不炸", L.detect_script(""), "unknown")
check("純數字符號不炸", L.detect_script("123 !!! ---"), "unknown")

seg_mix = L.Segmenter(force_words=["responsible innovation",
                                   "stakeholder engagement", "負責任創新"])
check("英文段落路由到空白斷詞", seg_mix.backend_for(EN_TEXT), "whitespace")
check_true("中文段落不走空白斷詞", seg_mix.backend_for(ZH_TEXT) != "whitespace")

en_toks = seg_mix.cut(EN_TEXT)
check_true("英文確實切得出詞", len(en_toks) > 20, str(len(en_toks)))
check_true("英文強制片語有合併",
           "responsible innovation" in en_toks and
           "stakeholder engagement" in en_toks, str(en_toks[:12]))
check_true("跨行的強制片語也合得起來",
           "responsible innovation" in L.Segmenter(
               force_words=["responsible innovation"]).cut(
               "of responsible\ninnovation here"))
check_true("英文斷詞沒有控制字元外洩",
           not any("\x00" in w or "\x01" in w for w in en_toks))
check_true("英文一律轉小寫",
           all(w == w.lower() for w in en_toks), str(en_toks[:8]))

# 同一個 Segmenter 物件要能同時處理兩種語言——中英語料並存是常態
check_true("同一物件處理中文仍正常",
           "負責任創新" in seg_mix.cut(ZH_TEXT), str(seg_mix.cut(ZH_TEXT)[:6]))

en_terms = [r["term"] for r in L.discover_terms([EN_TEXT] * 5)]
check_true("英文語料抽得出術語", len(en_terms) > 5, str(len(en_terms)))
check_true("英文術語不含虛詞",
           not any(L.is_function_word(t) for t in en_terms),
           str([t for t in en_terms if L.is_function_word(t)][:5]))
check_true("英文術語不含跨子句組合（首尾為虛詞）",
           not any(t.split()[0] in L._EN_STOPWORDS or
                   t.split()[-1] in L._EN_STOPWORDS for t in en_terms))
check_true("英文術語不含連接詞在內部",
           not any(w in L._EN_NO_INSIDE for t in en_terms for w in t.split()),
           str([t for t in en_terms
                if any(w in L._EN_NO_INSIDE for w in t.split())][:4]))
check_true("抽得到真正的多詞術語",
           any(" " in t for t in en_terms), str(en_terms[:8]))
check_true("英文停用詞認得出來", L.is_function_word("the") and
           L.is_function_word("BECAUSE") and not L.is_function_word("privacy"))

# 後備斷詞器：詞彙表沒收錄時只吐單字，不得盲抓兩個字
seg = L.Segmenter(force_words=["方法", "案子"], backend="ngram")
toks = seg.cut("這個案子的方法是這樣")
check_true("後備斷詞不吐出跨邊界的雙字碎片",
           not any(len(x) == 2 and x not in ("方法", "案子") for x in toks),
           str(toks))
check_true("詞彙表裡的詞仍被正確切出",
           "方法" in toks and "案子" in toks, str(toks))
check_true("四個組別都誘導出特徵詞",
           all(len(rows) > 0 for rows in demo_feats.values()),
           str({k: len(v) for k, v in demo_feats.items()}))

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
