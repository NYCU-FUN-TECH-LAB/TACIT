"""驗證 tacit_review.py（英文 schema 版）：稽核軌跡不可銷毀、狀態機、統計、引文驗證。"""
import sys

import tacit_schema as S
import tacit_i18n as I
import tacit_review as R

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


TRANSCRIPT = ("【受訪者】我們最懂這個技術，外面的人講什麼我們還是照原計畫走。\n"
              "【受訪者】因為使用者反映介面太複雜，所以我們後來把整個流程改掉了。\n"
              "【受訪者】定案之後再跟他們說明就好了。\n"
              "【受訪者】其實我們內部也一直有爭論，我不敢說自己都對。")


def seg(sid, brief, full, codes):
    return {S.SEGMENT_ID: sid, S.TITLE: sid, S.QUOTE: brief, S.FULL_TEXT: full,
            S.CODES_F: [S.make_code(d, p, "AI rationale") for d, p in codes]}


def fresh():
    return [{S.RESPONDENT: "產A", S.DESCRIPTORS: S.blank_descriptors(),
             S.SUMMARY: "", S.SEGMENTS: [
                 seg("S1", "我們最懂這個技術",
                     "我們最懂這個技術，外面的人講什麼我們還是照原計畫走。",
                     [(S.REFLEXIVITY, "N"), (S.RESPONSIVENESS, "N")]),
                 seg("S2", "因為使用者反映介面太複雜",
                     "因為使用者反映介面太複雜，所以我們後來把整個流程改掉了。",
                     [(S.RESPONSIVENESS, "P")]),
                 seg("S3", "定案之後再跟他們說明",
                     "定案之後再跟他們說明就好了。", [(S.ENGAGEMENT, "N")]),
                 seg("S4", "這是模型自己編出來的句子",
                     "這句話根本不在逐字稿裡面。", [(S.ANTICIPATION, "P")]),
             ]}]


print("=" * 70)
print("測試 1：審核欄位初始化與原始編碼快照")
print("=" * 70)
recs = fresh()
R.ensure_all(recs)
s1 = recs[0][S.SEGMENTS][0]
check("初始狀態", s1[S.REVIEW][S.STATUS], S.STATUS_PENDING)
check("原始編碼快照", s1[S.REVIEW][S.ORIGINAL_CODES], ["REF-N", "RES-N"])
check("來源標記", s1[S.REVIEW][S.SOURCE], S.SOURCE_AI)
check("已刪除段落容器建立", recs[0][S.DELETED_SEGMENTS], [])
check_true("審核欄位皆為 ASCII", all(k.isascii() for k in s1[S.REVIEW]))
R.update_codes(s1, ["REF-N"])
R.ensure_review(s1)
check("重複 ensure 不覆寫快照", s1[S.REVIEW][S.ORIGINAL_CODES], ["REF-N", "RES-N"])

print()
print("=" * 70)
print("測試 2：編輯操作與狀態機")
print("=" * 70)
recs = fresh(); R.ensure_all(recs)
segs = recs[0][S.SEGMENTS]

R.confirm(segs[1])
check("確認後狀態", segs[1][S.REVIEW][S.STATUS], S.STATUS_CONFIRMED)
check("確認產生一筆紀錄", len(segs[1][S.REVIEW][S.HISTORY]), 1)

changed, added, removed = R.update_codes(segs[0], ["REF-N"])
print(f"   S1 修改：新增{added} 移除{removed}")
check("回報有變動", changed, True)
check("移除的碼", removed, ["RES-N"])
check("修改後狀態", segs[0][S.REVIEW][S.STATUS], S.STATUS_MODIFIED)
check("目前編碼", R.codes_of(segs[0]), ["REF-N"])
check("原始編碼仍完整保存", segs[0][S.REVIEW][S.ORIGINAL_CODES], ["REF-N", "RES-N"])
check("保留未變動碼的原理由",
      segs[0][S.CODES_F][0][S.RATIONALE], "AI rationale")

check("編碼沒變時回報無變動", R.update_codes(segs[1], ["RES-P"]), (False, [], []))
check("無變動不記為已修改", segs[1][S.REVIEW][S.STATUS], S.STATUS_CONFIRMED)

R.update_text(segs[2], title="下游知會", quote="定案之後再跟他們說明就好了")
check("文字修改後狀態", segs[2][S.REVIEW][S.STATUS], S.STATUS_MODIFIED)
check("標題已更新", segs[2][S.TITLE], "下游知會")
check("原始標題保留", segs[2][S.REVIEW][S.ORIGINAL_TITLE], "S3")
check("重複相同文字不再記錄", R.update_text(segs[2], title="下游知會"), False)

print()
print("=" * 70)
print("測試 3：刪除不得銷毀資料")
print("=" * 70)
check("刪除成功",
      R.delete_segment(recs[0], "S4", reason="quote not in transcript"), True)
check("有效段落剩 3", len(recs[0][S.SEGMENTS]), 3)
check("已刪除區保留 1", len(recs[0][S.DELETED_SEGMENTS]), 1)
d = recs[0][S.DELETED_SEGMENTS][0]
check("被刪段落狀態", d[S.REVIEW][S.STATUS], S.STATUS_DELETED)
check("被刪段落仍保有原始編碼", d[S.REVIEW][S.ORIGINAL_CODES], ["ANT-P"])
check_true("刪除理由入軌跡",
           any("quote not in" in e[R.LOG_DETAIL] for e in d[S.REVIEW][S.HISTORY]))
check("刪除不存在的 ID 回 False", R.delete_segment(recs[0], "XXX"), False)

R.restore_segment(recs[0], "S4")
check("還原後有效段落回到 4", len(recs[0][S.SEGMENTS]), 4)
check("已刪除區清空", len(recs[0][S.DELETED_SEGMENTS]), 0)
R.delete_segment(recs[0], "S4", reason="deleted again")

print()
print("=" * 70)
print("測試 4：人工新增段落")
print("=" * 70)
new = R.add_segment(recs[0], "其實我們內部也一直有爭論，我不敢說自己都對。",
                    ["REF-P"], title="承認知識邊界", reason="model missed it")
print(f"   新增 {new[S.SEGMENT_ID]}：{R.codes_of(new)}")
check_true("新段落 ID 前綴 M", new[S.SEGMENT_ID].startswith("M"))
check("新段落狀態", new[S.REVIEW][S.STATUS], S.STATUS_ADDED)
check("新段落來源", new[S.REVIEW][S.SOURCE], S.SOURCE_HUMAN)
check("人工新增者 AI 原始編碼為空", new[S.REVIEW][S.ORIGINAL_CODES], [])
check("編碼正確", R.codes_of(new), ["REF-P"])
new2 = R.add_segment(recs[0], "另一段", ["ANT-P"])
check_true("ID 不重複", new2[S.SEGMENT_ID] != new[S.SEGMENT_ID])
check("非法碼被過濾", R.add_segment(recs[0], "x", ["NOPE"])[S.CODES_F], [])

print()
print("=" * 70)
print("測試 5：複核統計（手算對答案）")
print("=" * 70)
# AI 段落 4：S1 已修改、S2 已確認、S3 已修改、S4 已刪除；人工新增 3
st = R.review_stats(recs)
for k, v in st.items():
    print(f"   {k}: {v}")
check("AI 產出段落數", st["ai_segments"], 4)
check("已複核", st["reviewed"], 4)
check("複核率", st["review_rate"], 1.0)
check("確認未改", st["confirmed"], 1)
check("經修改", st["modified"], 2)
check("修改率 2/4", st["modify_rate"], 0.5)
check("經刪除", st["deleted"], 1)
check("刪除率 1/4", st["delete_rate"], 0.25)
check("人工新增段落", st["human_added"], 3)
check("目前有效段落數（3 AI + 3 人工）", st["active_segments"], 6)
check("未複核", st["pending"], 0)
check_true("統計欄位皆為 ASCII", all(k.isascii() for k in st))

print()
print("  -- 逐碼變動 --")
cl = {r["code"]: r for r in R.code_level_changes(recs)}
print("   RES-N:", {k: v for k, v in cl["RES-N"].items() if k != "code"})
check("RES-N AI 原始標記", cl["RES-N"]["ai_original"], 1)
check("RES-N 被移除", cl["RES-N"]["removed_by_researcher"], 1)
check("RES-N 移除率", cl["RES-N"]["removal_rate"], 1.0)
check("REF-P 被研究者新增", cl["REF-P"]["added_by_researcher"], 1)
check("ANT-P 刪除的不算、人工新增的算", cl["ANT-P"]["kept_after_review"], 1)

print()
print("=" * 70)
print("測試 6：逐字引文驗證")
print("=" * 70)
recs2 = fresh(); R.ensure_all(recs2)
v_ok = R.verify_quote(recs2[0][S.SEGMENTS][0], TRANSCRIPT)
v_bad = R.verify_quote(recs2[0][S.SEGMENTS][3], TRANSCRIPT)
print("   S1:", v_ok)
print("   S4:", v_bad)
check("真實引文通過", (v_ok["quote_ok"], v_ok["full_text_ok"]), (True, True))
check("幻覺引文被抓出", (v_bad["quote_ok"], v_bad["full_text_ok"]), (False, False))
check("無逐字稿標為不可驗證",
      R.verify_quote(recs2[0][S.SEGMENTS][0], "")["checkable"], False)

summary, rows = R.verify_all_quotes(recs2, {"產A": TRANSCRIPT})
print("   摘要:", summary)
check("可驗證段落數", summary["checked"], 4)
check("完整原文相符 3/4", summary["full_text_verbatim"], 3)
check("相符率", summary["full_text_rate"], 0.75)
check("需人工檢查 1 筆", summary["needs_review"], 1)
check("抓到的是 S4", rows[0][S.SEGMENT_ID], "S4")
check("問題型態為識別碼", rows[0]["issue"], R.QUOTE_ISSUE_FULL)
check("標點差異不影響比對",
      R.verify_quote({S.QUOTE: "我們最懂這個技術外面的人講什麼",
                      S.FULL_TEXT: "我們最懂這個技術"}, TRANSCRIPT)["quote_ok"], True)

print()
print("=" * 70)
print("測試 7：稽核軌跡與前後對照")
print("=" * 70)
trail = R.audit_trail(recs)
dist = {a: sum(1 for t in trail if t[R.LOG_ACTION] == a)
        for a in {t[R.LOG_ACTION] for t in trail}}
print(f"   共 {len(trail)} 筆，動作分布：{dist}")
check_true("軌跡非空", len(trail) >= 6)
check_true("依時間排序",
           all(trail[i][R.LOG_TIME] <= trail[i + 1][R.LOG_TIME]
               for i in range(len(trail) - 1)))
check_true("含新增動作", any(t[R.LOG_ACTION] == R.ACTION_ADD for t in trail))
check_true("含刪除動作", any(t[R.LOG_ACTION] == R.ACTION_DELETE for t in trail))
check_true("動作皆為識別碼", all(t[R.LOG_ACTION] in R.ALL_ACTIONS for t in trail))
check_true("軌跡欄位為 ASCII", all(k.isascii() for k in trail[0]))

ch = R.changed_segments(recs)
print("   變動段落:", [(c[S.SEGMENT_ID], c[S.STATUS], c["removed"], c["added"])
                       for c in ch])
ids = {c[S.SEGMENT_ID] for c in ch}
check_true("S1 列入變動", "S1" in ids)
check_true("S2（確認未改）不列入", "S2" not in ids)
check_true("S4（已刪除）列入", "S4" in ids)

print()
print("=" * 70)
print("測試 8：方法章節句子（引擎給數字，i18n 組句）")
print("=" * 70)
facts = R.methods_facts(recs)
check_true("facts 不含顯示文字",
           all(not isinstance(v, str) or v.isascii() for v in facts.values()))
zh = I.methods_sentence(facts, "zh")
en = I.methods_sentence(facts, "en")
print("  ZH:", zh)
print("  EN:", en[:110], "…")
check_true("中文句含複核率", "複核率 100.0%" in zh)
check_true("中文句含修改率", "50.0%" in zh)
check_true("英文句含 verified", "verified by the researcher" in en)
check_true("英文句主謂一致（單數用 was）", " 1 was rejected" in en, en[-160:])
check("未複核時給明確訊息",
      I.methods_sentence(R.methods_facts([{S.RESPONDENT: "x", S.SEGMENTS: []}]), "zh"),
      "（尚未開始複核）")

print()
print("=" * 70)
print("測試 9：邊界情況")
print("=" * 70)
check("空紀錄統計", R.review_stats([])["ai_segments"], 0)
check("空紀錄軌跡", R.audit_trail([]), [])
check("空紀錄引文驗證", R.verify_all_quotes([], {})[0]["checked"], 0)
e = {S.RESPONDENT: "空", S.SEGMENTS: []}
R.ensure_all([e])
check("無段落仍建立刪除區", e[S.DELETED_SEGMENTS], [])
bad = {S.SEGMENT_ID: "B1", S.CODES_F: [{S.DIMENSION: "nope", S.POLARITY: "P"}]}
R.ensure_review(bad)
check("非法維度不進原始快照", bad[S.REVIEW][S.ORIGINAL_CODES], [])
R.update_codes(bad, ["REF-N", "garbage"])
check("非法碼被過濾", R.codes_of(bad), ["REF-N"])

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
