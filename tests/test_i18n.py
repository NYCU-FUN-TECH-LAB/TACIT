"""驗證 tacit_i18n.py：英文預設、兩語言皆無缺漏、每個 schema 識別碼都有標籤、Excel 名稱合法。"""
import sys
import tacit_schema as S
import tacit_i18n as I

FAIL = []


def check(label, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{label}: got={got!r} want={want!r}")
    if not ok:
        FAIL.append(label)


def check_true(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + f"{label}" + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


print("=" * 70)
print("測試 1：預設語言為英文")
print("=" * 70)
I.set_lang("en")
check("預設語言", I.get_lang(), "en")
check("維度標籤", I.dim(S.REFLEXIVITY), "Reflexivity")
check("頁籤標籤", I.t("tab.review"), "Code review")
check("非法語言碼回退英文", I.set_lang("fr"), "en")
# 分析語言用 BCP-47 風格的代碼（zh-Hant / zh-Hans），介面語言只有 en / zh。
# 兩者在存檔與舊狀態裡很容易走錯位；走錯位時退回英文不會出錯，但拿到
# "zh-Hant" 的人要的顯然是中文介面，而且那個退回是悄無聲息的。
check("zh-Hant 對到 zh 而不是退回英文", I.set_lang("zh-Hant"), "zh")
check("zh-Hans 也對到 zh", I.set_lang("zh-Hans"), "zh")
check("zh-TW 也對到 zh", I.set_lang("zh-TW"), "zh")
check("沒有前綴可比的仍然回退英文", I.set_lang("klingon"), "en")
check("None 不會炸", I.set_lang(None), "en")
I.set_lang("en")

print()
print("=" * 70)
print("測試 2：切換繁中")
print("=" * 70)
I.set_lang("zh")
check("維度標籤", I.dim(S.REFLEXIVITY), "反思性")
check("頁籤標籤", I.t("tab.review"), "編碼複核")
check("屬性值標籤", I.descriptor_value("ict_ai"), "資通訊／AI")
check("狀態標籤", I.status(S.STATUS_MODIFIED), "已修改")
check("框架關係", I.relation(S.RELATION_CHALLENGES), "挑戰")
check("lang 參數可覆寫全域設定", I.dim(S.REFLEXIVITY, lang="en"), "Reflexivity")
I.set_lang("en")

print()
print("=" * 70)
print("測試 3：兩種語言都不得有缺漏")
print("=" * 70)
for lang in I.LANGS:
    miss = I.missing_keys(lang)
    check(f"{lang} 缺漏鍵數", len(miss), 0)
    if miss:
        print("      缺：", miss[:12])
print("  覆蓋率：", I.coverage_report())

print()
print("=" * 70)
print("測試 4：每個 schema 識別碼都要有標籤（避免畫面出現識別碼）")
print("=" * 70)
for lang in I.LANGS:
    bad = []
    for d in S.AGG_DIMENSIONS:
        if I.dim(d, lang) == d:
            bad.append(f"dim:{d}")
    for d in S.DIMENSIONS:
        for p in S.POLARITIES:
            if not I.polarity(d, p, lang):
                bad.append(f"pol:{d}-{p}")
    for k in S.DESCRIPTOR_KEYS + [S.DESCRIPTOR_BASIS]:
        if I.descriptor(k, lang) == k:
            bad.append(f"desc:{k}")
    for vs in S.DESCRIPTOR_FIELDS.values():
        for v in vs:
            if I.descriptor_value(v, lang) == v:
                bad.append(f"descval:{v}")
    for st in S.ALL_STATUS:
        if I.status(st, lang) == st:
            bad.append(f"status:{st}")
    for r in S.FRAME_RELATIONS:
        if I.relation(r, lang) == r:
            bad.append(f"rel:{r}")
    for tend in S.POLARITY_TENDENCIES:
        if I.tendency(tend, lang) == tend:
            bad.append(f"tend:{tend}")
    for sp in (S.STRATUM_UNMARKED, S.NONE_LABEL):
        if I.special(sp, lang) == sp:
            bad.append(f"special:{sp}")
    check(f"{lang} 未翻譯的識別碼", bad, [])

print()
print("=" * 70)
print("測試 5：八個編碼的完整標籤")
print("=" * 70)
for lang in I.LANGS:
    labels = [I.code_label(c, lang) for c in S.CODES]
    check_true(f"{lang} 八個編碼都有標籤",
               all(l and "-" not in l.split("·")[0] for l in labels))
    check_true(f"{lang} 標籤互不重複", len(set(labels)) == 8)
print("  en 範例：", I.code_label("REF-N", "en"))
print("  zh 範例：", I.code_label("REF-N", "zh"))
check("未知編碼原樣回傳", I.code_label("XXX-P"), "XXX-P")
check("dim_full 含縮寫", I.dim_full(S.ENGAGEMENT, "en"), "Public Engagement (ENG)")

print()
print("=" * 70)
print("測試 6：Excel 工作表名稱限制（≤31 字元、不得含 : \\ / ? * [ ]）")
print("=" * 70)
bad_chars = set(':\\/?*[]')
for lang in I.LANGS:
    problems = []
    names = []
    for k in I.STRINGS:
        if not k.startswith("sheet."):
            continue
        n = I.t(k, lang)
        names.append(n)
        if len(n) > 31:
            problems.append(f"{k} 過長({len(n)})")
        if set(n) & bad_chars:
            problems.append(f"{k} 含非法字元")
    check(f"{lang} 工作表名稱問題", problems, [])
    dup = [n for n in set(names) if names.count(n) > 1]
    check(f"{lang} 工作表名稱不重複", dup, [])
print(f"  共 {sum(1 for k in I.STRINGS if k.startswith('sheet.'))} 個工作表名稱")

print()
print("=" * 70)
print("測試 7：容錯行為")
print("=" * 70)
check("查不到的鍵回傳鍵本身", I.t("nope.not.here"), "nope.not.here")
check("格式化參數", I.t("common.total", x=1), "Total")
check("未知維度不炸", I.dim("bogus"), "bogus")
check("未知屬性值不炸", I.descriptor_value("bogus"), "bogus")
I.set_lang("zh")
check("切換後仍容錯", I.t("nope"), "nope")
I.set_lang("en")

print()
print("=" * 70)
print("測試 8：與 tacit_schema 的耦合正確")
print("=" * 70)
check_true("STRINGS 的鍵皆為 ASCII 點分命名",
           all(k.isascii() and " " not in k for k in I.STRINGS))
check_true("英文標籤不含中文",
           not any(any('一' <= ch <= '鿿' for ch in I.t(k, "en"))
                   for k in I.STRINGS))
zh_only = [k for k in I.STRINGS
           if I.t(k, "zh") == I.t(k, "en") and not any(
               x in k for x in ("stat.", "app.title", "sheet."))]
print(f"  中英相同的鍵（多為專有名詞，正常）：{len(zh_only)} 個 -> {zh_only[:5]}")

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
