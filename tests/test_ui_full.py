"""
全頁籤實跑：載入 24 份示範分析，把每一個頁籤在兩種語言、兩種框架、
三種供應者下都渲染一遍，並檢查該出現的警告有出現、不該外洩的東西沒外洩。

與 test_ui_smoke 的分工
-----------------------
test_ui_smoke 用小型合成紀錄驗證個別行為（遷移、複核、續跑…）。
這一支用**真正隨附的示範語料**把整個介面跑一次，抓的是只有在真實規模
下才會出現的問題：交叉表夠不夠大、主題頁籤的警告會不會誤觸發、
換供應者時側欄的欄位組合對不對。

這一支不需要網路、不需要金鑰、不需要模型服務。
"""
import json
import os
import sys
import glob

from streamlit.testing.v1 import AppTest

import tacit_framework as F
import tacit_schema as S
import tacit_i18n as I
import tacit_llm as LLM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def demo_records():
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "analyses", "demo_en_*.json"))):
        with open(p, encoding="utf-8") as f:
            out.append(S.migrate_record(json.load(f)))
    return out


def run(state, timeout=420):
    at = AppTest.from_file(APP, default_timeout=timeout)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


def blob(at):
    """畫面上所有看得到的文字，用來檢查警告與洩漏。"""
    parts = []
    for coll in (at.markdown, at.caption, at.warning, at.error, at.info,
                 at.success):
        parts += [str(getattr(x, "value", "")) for x in coll]
    parts += [str(x.label) for x in at.metric]
    return "\n".join(parts)


RECS = demo_records()
print("=" * 70)
print(f"測試 1：載入 {len(RECS)} 份示範分析，九個頁籤全部渲染")
print("=" * 70)
ok("找得到示範分析", len(RECS) == 24, f"{len(RECS)}；請先執行 python make_demo_data.py")

if RECS:
    for lang in I.LANGS:
        F.reset()
        at = run({"ui_lang": lang, "records": RECS})
        ok(f"{lang} 全語料渲染無例外", not at.exception,
           str(at.exception[0].value)[:300] if at.exception else "")
        if not at.exception:
            ok(f"{lang} 九個主頁籤都在", len(at.tabs) >= 9, str(len(at.tabs)))
            ok(f"{lang} 有大量表格（分析真的跑出來了）",
               len(at.dataframe) >= 5, str(len(at.dataframe)))

    print()
    print("=" * 70)
    print("測試 2：英文介面 + 英文語料 → 畫面不得出現中文")
    print("=" * 70)
    F.reset()
    at_en = run({"ui_lang": "en", "records": RECS})
    if not at_en.exception:
        leaked = "".join(ch for ch in blob(at_en) if "一" <= ch <= "鿿")
        ok("英文畫面沒有中文殘留", not leaked, leaked[:60])
        ok("不洩漏內部識別碼",
           "institution_type" not in blob(at_en)
           and "senior_management" not in blob(at_en))

    print()
    print("=" * 70)
    print("測試 3：交叉分析在 24 份語料下真的算得出統計")
    print("=" * 70)
    # 這是把示範語料從 6 份擴到 24 份的唯一理由：6 份時每一項推論統計
    # 都會被前提檢查擋下來，打開這個頁籤只看得到一排「樣本不足」。
    # 預設的列單位是八格編碼（4×8），那是最稀疏的一張表，前提本來就不成立
    # ——守衛必須擋下它。要看到算得出來的檢定，得把列單位換成極性（4×2）。
    # 兩個分支都要驗：只驗一邊，證明不了守衛是在檢查還是一律放行／一律擋下。
    # scipy 是選配。沒裝的時候算不出卡方，介面改說「未安裝 scipy」——
    # 但**不給 p 值**這件事兩種情形都一樣，那才是要驗的行為。
    import tacit_analysis as _A                          # noqa: E402
    if not at_en.exception:
        _txt = blob(at_en)
        if _A.HAS_SCIPY:
            ok("預設（八格編碼）的表被判定為稀疏，不給 p 值",
               "cells have an expected count below 5" in _txt,
               "守衛不能因為語料變大就失效")
        else:
            ok("沒裝 scipy 時，預設的表一樣不給 p 值",
               "p = " not in _txt, "沒有 scipy 也不能憑空生出 p 值")

    F.reset()
    at_pol = run({"ui_lang": "en", "records": RECS, "cx_unit": S.POLARITY})
    ok("列單位換成極性後渲染無例外", not at_pol.exception,
       str(at_pol.exception[0].value)[:200] if at_pol.exception else "")
    if not at_pol.exception:
        txt = blob(at_pol)
        if _A.HAS_SCIPY:
            # 期望次數這個前提成立、p 值給得出來——這是擴到 24 份的理由。
            # 但不再亮綠燈說「可以報告」：181 個單位來自 24 位受訪者，
            # 獨立性不成立，訊息要把兩個前提都講到（細節見測試 6b）。
            ok("屬性 × 極性：期望次數前提成立並給出 p 值",
               "Expected counts meet the assumption" in txt and "p = 0.0182" in txt,
               "6 份語料時這裡只會有「樣本不足」；擴到 24 份就是為了這一行")
            ok("屬性 × 極性：同時指出獨立性不成立",
               "independence does not" in txt, txt[-300:])
        else:
            ok("沒裝 scipy 時，介面說明原因而不是靜靜跳過",
               I.t("cross.chi_no_scipy", "en") in txt or "scipy" in txt.lower(),
               "使用者要知道少了什麼、為什麼沒有數字")

print()
print("=" * 70)
print("測試 4：主題頁籤——維度掛零時必須示警")
print("=" * 70)
# 要防的失效：Gioia 圖表只畫得出有主題的維度，所以少一個維度時圖看起來
# 完全正常，研究者會讀成「資料裡沒有這個面向」。這一項確保介面會講出來。
F.reset()
_dims = F.active().dimensions
three_of_four = [
    S.migrate_theme({S.THEME_NAME: f"theme {i}", S.AGG_DIMENSION: d,
                     S.MEMBER_IDS: []}, i + 1)
    for i, d in enumerate(_dims[:-1])          # 故意漏掉最後一個維度
]
at_gap = run({"ui_lang": "en", "records": RECS[:6], "themes": three_of_four})
ok("缺維度時渲染無例外", not at_gap.exception,
   str(at_gap.exception[0].value)[:200] if at_gap.exception else "")
if not at_gap.exception:
    txt = blob(at_gap)
    missing_label = I.dim(_dims[-1], "en")
    ok(f"畫面明講「{missing_label}」沒有拿到主題",
       "No theme was assigned to" in txt and missing_label in txt,
       "少一個維度卻不出聲，正是這個 bug 藏了兩個版本的原因")
    ok("措辭說清楚這是待查證的問題而非結論",
       "not a finding" in txt or "a question" in txt)

all_four = [
    S.migrate_theme({S.THEME_NAME: f"theme {i}", S.AGG_DIMENSION: d,
                     S.MEMBER_IDS: []}, i + 1)
    for i, d in enumerate(_dims)
]
at_full = run({"ui_lang": "en", "records": RECS[:6], "themes": all_four})
if not at_full.exception:
    ok("四個維度都有主題時不誤觸發警告",
       "No theme was assigned to" not in blob(at_full))

print()
print("=" * 70)
print("測試 5：供應者切換後側欄的欄位組合")
print("=" * 70)
CASES = [
    ("gemini", None, ["app.api_key"], ["llm.base_url", "llm.num_ctx"]),
    ("ollama", "http://localhost:11434", ["llm.base_url", "llm.num_ctx"],
     ["app.api_key"]),
    ("openai_compat", "http://localhost:1234/v1",
     ["llm.base_url", "llm.num_ctx"], ["app.api_key"]),
    ("openai_compat", "https://openrouter.ai/api/v1",
     ["llm.base_url", "llm.remote_key"], []),
]
for prov, url, must, must_not in CASES:
    st_state = {"ui_lang": "en", "llm_provider": prov}
    if url:
        st_state["llm_base_url"] = url
    F.reset()
    at_p = run(st_state)
    tag = f"{prov}{' @remote' if url and 'openrouter' in url else ''}"
    ok(f"{tag} 渲染無例外", not at_p.exception,
       str(at_p.exception[0].value)[:200] if at_p.exception else "")
    if at_p.exception:
        continue
    labels = ([str(x.label) for x in at_p.text_input]
              + [str(x.label) for x in at_p.number_input])
    for key in must:
        ok(f"{tag} 側欄有「{I.t(key, 'en')}」", I.t(key, "en") in labels,
           str(labels))
    for key in must_not:
        ok(f"{tag} 側欄沒有「{I.t(key, 'en')}」", I.t(key, "en") not in labels)

# 指向本機時要說「資料不會離開這台電腦」；指向雲端時要提醒倫理審查。
F.reset()
at_local = run({"ui_lang": "en", "llm_provider": "ollama",
                "llm_base_url": "http://localhost:11434"})
if not at_local.exception:
    ok("本機端點顯示隱私提示",
       any("not sent over the network" in str(s.value) for s in at_local.success))
F.reset()
at_remote = run({"ui_lang": "en", "llm_provider": "openai_compat",
                 "llm_base_url": "https://openrouter.ai/api/v1"})
if not at_remote.exception:
    ok("雲端端點顯示倫理提醒",
       any("ethics approval" in str(w.value) for w in at_remote.warning),
       "把人類受試者資料送到別人機器上卻不提醒，是最糟的預設值")

print()
print("=" * 70)
print("測試 6：換成無極性框架後，全語料仍然跑得動")
print("=" * 70)
F.reset()
at_u = run({"ui_lang": "en", "framework_id": "utaut_venkatesh_2003",
            "records": RECS})
ok("UTAUT + 24 份語料渲染無例外", not at_u.exception,
   str(at_u.exception[0].value)[:300] if at_u.exception else "")
if not at_u.exception:
    txt = blob(at_u)
    ok("畫面出現 UTAUT 的維度",
       "Performance expectancy" in txt or "Effort expectancy" in txt)
    ok("畫面不再出現 RI 的維度",
       "Reflexivity" not in txt and "Anticipation" not in txt)
    ok("極性子頁籤消失（該分析在無極性框架下沒有意義）",
       len(at_u.tabs) < len(at_en.tabs) if not at_en.exception else True)

print()
print("=" * 70)
print("測試 7：框架不符的存檔，介面必須擋下來而不是載入空紀錄")
print("=" * 70)
# 要防的失效：切到 UTAUT 再開 RI 編過的存檔，編碼若在遷移當下就全被丟掉，
# 畫面上跟「這份還沒編碼」一模一樣；使用者接著隨手一存，磁碟上的原檔就被
# 清空的版本覆蓋，無法復原。
#
# 這一段**不碰磁碟**：scan_saved() 在 _saved_index 已存在時直接回傳快取，
# 所以注入一份索引就能走完整條載入路徑。測試不該去動使用者的存檔資料夾，
# 尤其是這種驗證「資料會不會被毀掉」的測試。


def _fake_index(mismatch):
    """兩筆索引項，模擬 scan_saved() 的輸出。"""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "analyses",
                                           "demo_en_*.json")))[:2]:
        with open(p, encoding="utf-8") as f:
            raw = json.load(f)
        dropped = []
        rec = S.migrate_record(raw, dropped=dropped)
        fn = os.path.basename(p)
        rec["_source"], rec["_file"] = "pro", fn
        rec["_fw_mismatch"], rec["_dropped"] = mismatch, dropped
        out.append({"key": f"pro/{fn}", "tag": "pro", "legacy": False,
                    "respondent": str(rec.get(S.RESPONDENT) or fn),
                    "segments": len(rec.get(S.SEGMENTS) or []),
                    "fw_mismatch": mismatch, "dropped": dropped,
                    "record": rec})
    return out


def _ss(at, key, default=None):
    """AppTest 的 session_state 沒有 .get()。"""
    try:
        return at.session_state[key]
    except (KeyError, AttributeError):
        return default


print()
print("=" * 70)
print("測試 6b：卡方守衛要對兩個前提都有交代")
print("=" * 70)
# 期望次數一過關就亮綠燈說「p may be reported」、正下方的灰字卻說觀察
# 不獨立——那是同一個畫面上一邊說可以報、一邊說不該當推論。
# 獨立性查得出來：表的總數大於受訪者人數。
F.reset()
if RECS:
    def _chi_view(case):
        return run({"ui_lang": "en", "records": RECS,
                    "cx_unit": S.POLARITY, "cx_case": case})

    _seg = _chi_view(False)
    ok("段落層級渲染無例外", not _seg.exception,
       str(_seg.exception[0].value)[:200] if _seg.exception else "")
    if not _seg.exception:
        _ok = [str(x.value) for x in _seg.success if "p = " in str(x.value)]
        _info = [str(x.value) for x in _seg.info if "p = " in str(x.value)]
        ok("段落層級不再亮綠燈說 p 可以報告", not _ok, str(_ok)[:120])
        ok("段落層級照樣給出 p 值", bool(_info) and "0.0182" in _info[0],
           str(_info)[:120])
        ok("並且說出有幾個單位、來自幾位受訪者",
           bool(_info) and "181" in _info[0] and "24 respondents" in _info[0],
           str(_info)[:200])
        ok("並且指向一人一列的那個開關",
           bool(_info) and "One row per respondent" in _info[0])

    _case = _chi_view(True)
    ok("受訪者層級渲染無例外", not _case.exception,
       str(_case.exception[0].value)[:200] if _case.exception else "")
    if not _case.exception:
        _warn = " ".join(str(x.value) for x in _case.warning)
        _cap = " ".join(str(x.value) for x in _case.caption)
        ok("受訪者層級的 p 值被扣住", "no p-value is reported" in _warn, _warn[:160])
        ok("受訪者層級不再說「一位受訪者貢獻多筆編碼」（那已經不成立）",
           "one respondent contributes several codes" not in _cap)
        ok("改說每人只算一次、觀察獨立",
           "counted once" in _cap and "24 respondents" in _cap, _cap[-200:])
        ok("表上有 N = 24",
           any(str(m.value) == "24" for m in _case.metric),
           str([str(m.value) for m in _case.metric][-6:]))

F.reset()
_MM = ("ri_stilgoe_2013", "utaut_venkatesh_2003")
F.activate_by_id("utaut_venkatesh_2003")
_bad_index = _fake_index(_MM)
F.activate_by_id("ri_stilgoe_2013")
_good_index = _fake_index(None)
_keys = [x["key"] for x in _bad_index]
F.reset()

at_b = run({"ui_lang": "en", "framework_id": "utaut_venkatesh_2003",
            "records": [], "_saved_index": _bad_index})
ok("UTAUT 下掃描 RI 存檔不炸掉", not at_b.exception,
   str(at_b.exception[0].value)[:300] if at_b.exception else "")
if not at_b.exception:
    txt = blob(at_b)
    ok("有明講框架對不上", "coded under a different framework" in txt)
    ok("有點名紀錄當初的框架", "ri_stilgoe_2013" in txt)
    ok("預設不勾選對不上的存檔", not (_ss(at_b, "sel_records") or []),
       str(_ss(at_b, "sel_records")))

# 使用者硬是勾選並按下載入 → 必須擋，且工作區維持空的
at_c = run({"ui_lang": "en", "framework_id": "utaut_venkatesh_2003",
            "records": [], "_saved_index": _bad_index,
            "sel_records": _keys})
if not at_c.exception:
    btns = [b for b in at_c.button if "Load selected" in str(b.label)]
    if btns:
        at_c = btns[0].click().run()
        ok("按下載入後不炸掉", not at_c.exception,
           str(at_c.exception[0].value)[:300] if at_c.exception else "")
        ok("載入被擋下，工作區仍為空", not (_ss(at_c, "records") or []),
           f"records={len(_ss(at_c, 'records') or [])}")
        ok("有說明為什麼擋", "Not loaded" in blob(at_c))
    else:
        ok("找得到載入按鈕", False)
else:
    ok("硬選後執行不炸掉", False, str(at_c.exception[0].value)[:300])

# 框架相符時要照常載入——擋的是不符，不是全部
at_d = run({"ui_lang": "en", "framework_id": "ri_stilgoe_2013",
            "records": [], "_saved_index": _good_index,
            "sel_records": _keys})
if not at_d.exception:
    btns = [b for b in at_d.button if "Load selected" in str(b.label)]
    if btns:
        at_d = btns[0].click().run()
        ok("框架相符時同一批檔案載得進來",
           len(_ss(at_d, "records") or []) == len(_keys),
           f"records={len(_ss(at_d, 'records') or [])}")
        ok("載入後編碼沒有消失",
           sum(len(s[S.CODES_F]) for r in (_ss(at_d, "records") or [])
               for s in r[S.SEGMENTS]) > 0)
    else:
        ok("框架相符時找得到載入按鈕", False)
else:
    ok("框架相符時執行不炸掉", False, str(at_d.exception[0].value)[:300])
F.reset()

print()
print("=" * 70)
print("結果：全部通過 ✅" if not FAIL else f"結果：{len(FAIL)} 項失敗 ❌")
for f in FAIL:
    print(f"  - {f}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
