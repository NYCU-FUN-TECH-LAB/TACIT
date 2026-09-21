"""
用 Streamlit AppTest 實跑 app.py：八個頁籤 × 兩種介面語言 × 兩種框架。

最關鍵的兩項：
  - 換成無極性框架時，「極性平衡」子頁籤必須消失（那個分析在該框架下沒有意義）
  - 兩種語言下畫面都不得洩漏 ASCII 內部識別碼
"""
import json
import os
import shutil
import sys
import tempfile
from collections import Counter

from streamlit.testing.v1 import AppTest

import tacit_framework as F
import tacit_schema as S
import tacit_i18n as I
import tacit_review as RV
import tacit_llm as LLM

# 測試檔在 tests/，app.py 在專案根目錄。AppTest 把相對路徑解析成
# 「相對於呼叫它的檔案」，所以這裡一定要給絕對路徑。
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "app.py")

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def seg(sid, title, quote, codes, full=None):
    # full_text 預設就用 quote 本身：測試資料不該混入額外語言，
    # 否則「英文介面是否殘留中文」這一項會被自己的測試夾具汙染。
    return {S.SEGMENT_ID: sid, S.TITLE: title, S.QUOTE: quote,
            S.FULL_TEXT: full if full is not None else quote,
            S.CODES_F: [S.make_code(d, p) for d, p in codes]}


def ri_records():
    F.reset()
    return [
        {S.RESPONDENT: "產A",
         S.DESCRIPTORS: S.norm_descriptors({"institution_type": "industry",
                                            "role_level": "senior_management",
                                            "sector": "ict_ai",
                                            "experience": "11_20y"}),
         S.SUMMARY: "測試摘要 A", S.SEGMENTS: [
             seg("S1", "以專業權威排除外部意見", "我們最懂這個技術",
                 [(S.REFLEXIVITY, "N"), (S.RESPONSIVENESS, "N")]),
             seg("S2", "把參與當成告知", "定案之後再跟他們說明", [(S.ENGAGEMENT, "N")]),
             seg("S3", "技術決定論", "這個趨勢一定會走到那裡", [(S.ANTICIPATION, "N")])]},
        {S.RESPONDENT: "學C",
         S.DESCRIPTORS: S.norm_descriptors({"institution_type": "academia",
                                            "role_level": "researcher",
                                            "sector": "ict_ai",
                                            "experience": "over_20y"}),
         S.SUMMARY: "測試摘要 C", S.SEGMENTS: [
             seg("S1", "承認知識邊界", "坦白說我們也不敢說自己都對",
                 [(S.REFLEXIVITY, "P")]),
             seg("S2", "上游納入多元聲音", "一開始就邀請民間團體",
                 [(S.ENGAGEMENT, "P"), (S.ANTICIPATION, "P")])]},
    ]


def run_app(state):
    at = AppTest.from_file(APP, default_timeout=300)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    return at


print("=" * 70)
print("測試 1：空工作區啟動（兩種語言）")
print("=" * 70)
for lang in I.LANGS:
    at = run_app({"ui_lang": lang})
    ok(f"{lang} 啟動無例外", not at.exception,
       str(at.exception[0].value)[:120] if at.exception else "")
    ok(f"{lang} 九個主頁籤", len(at.tabs) >= 9, f"tabs={len(at.tabs)}")
    labels = " ".join(str(x.label) for x in at.tabs)
    ok(f"{lang} 有框架建構頁籤", I.t("tab.framework", lang) in labels)

print()
print("=" * 70)
print("測試 2：有資料時全部頁籤渲染（兩種語言）")
print("=" * 70)
for lang in I.LANGS:
    at = run_app({"ui_lang": lang, "records": ri_records()})
    ok(f"{lang} 無例外", not at.exception,
       str(at.exception[0].value)[:200] if at.exception else "")
    if not at.exception:
        ok(f"{lang} 有資料表", len(at.dataframe) > 5, f"df={len(at.dataframe)}")
        ok(f"{lang} 有指標", len(at.metric) > 5, f"metric={len(at.metric)}")

print()
print("=" * 70)
print("測試 3：介面語言確實切換（用英文語料，才分得清介面文字與研究資料）")
print("=" * 70)
# 用英文內容的紀錄：這樣畫面上出現的任何中文都必然是介面殘留，
# 而不是逐字稿本身。英文介面 + 中文逐字稿是合法組合，不能拿來判定殘留。
en_records = [
    {S.RESPONDENT: "Firm A",
     S.DESCRIPTORS: S.norm_descriptors({"institution_type": "industry",
                                        "role_level": "senior_management"}),
     S.SUMMARY: "Test summary A", S.SEGMENTS: [
         seg("S1", "Expert authority excludes outside voices",
             "We know this technology best",
             [(S.REFLEXIVITY, "N"), (S.RESPONSIVENESS, "N")]),
         seg("S2", "Engagement reduced to notification",
             "We tell them once it is decided", [(S.ENGAGEMENT, "N")])]},
    {S.RESPONDENT: "Univ C",
     S.DESCRIPTORS: S.norm_descriptors({"institution_type": "academia",
                                        "role_level": "researcher"}),
     S.SUMMARY: "Test summary C", S.SEGMENTS: [
         seg("S1", "Acknowledging the limits of knowledge",
             "Honestly we cannot claim we are always right",
             [(S.REFLEXIVITY, "P")])]},
]
texts = {}
for lang in I.LANGS:
    at = run_app({"ui_lang": lang, "records": en_records})
    if at.exception:
        ok(f"{lang} 英文語料無例外", False, str(at.exception[0].value)[:150])
        continue
    texts[lang] = " ".join([str(m.label) for m in at.metric] +
                           [str(c.value) for c in at.caption] +
                           [str(h.value) for h in at.markdown])
if len(texts) == 2:
    leaked = "".join(ch for ch in texts["en"] if "一" <= ch <= "鿿")
    ok("英文介面 + 英文語料 → 畫面完全沒有中文", not leaked, leaked[:60])
    ok("中文介面確實顯示中文", any("一" <= ch <= "鿿" for ch in texts["zh"]))
    ok("兩種語言畫面不同", texts["en"] != texts["zh"])
    ok("英文介面不洩漏內部識別碼",
       "institution_type" not in texts["en"] and "senior_management" not in texts["en"],
       "found raw identifier")
    ok("中文介面也不洩漏內部識別碼",
       "institution_type" not in texts["zh"] and "reflexivity" not in texts["zh"])

print()
print("=" * 70)
print("測試 4：切換到無極性框架 → 極性平衡子頁籤必須消失")
print("=" * 70)
# 把框架目錄整個導向暫存區：測試不該在使用者真正的 frameworks/ 裡留下
# 「Smoke Test Framework」這種東西——那會直接出現在側欄的框架下拉選單裡。
# 測試若中途拋錯，finally 也未必救得回來，所以從一開始就別寫進去。
with tempfile.TemporaryDirectory() as d:
    real_dir = F.FRAMEWORK_DIR
    F.FRAMEWORK_DIR = d
    F.ensure_builtin_on_disk()
    np_fw = F.blank("smoke_nopolarity", "Smoke Test Framework",
                    [("alpha", "ALP", "Alpha", "甲"), ("beta", "BET", "Beta", "乙")],
                    has_polarity=False)
    F.save(np_fw, os.path.join(d, "smoke_nopolarity.json"))
    try:
        F.activate_by_id("smoke_nopolarity")
        np_recs = [{S.RESPONDENT: "P1", S.DESCRIPTORS: S.blank_descriptors(),
                    S.SUMMARY: "", S.SEGMENTS: [
                        {S.SEGMENT_ID: "s1", S.TITLE: "t", S.QUOTE: "q",
                         S.FULL_TEXT: "f",
                         S.CODES_F: [S.make_code("alpha"), S.make_code("beta")]},
                        {S.SEGMENT_ID: "s2", S.TITLE: "t2", S.QUOTE: "q2",
                         S.FULL_TEXT: "f2", S.CODES_F: [S.make_code("beta")]}]}]

        at_ri = run_app({"ui_lang": "en", "framework_id": F.DEFAULT_FRAMEWORK_ID,
                         "records": ri_records()})
        n_ri = len(at_ri.tabs)
        at_np = run_app({"ui_lang": "en", "framework_id": "smoke_nopolarity",
                         "records": np_recs})
        ok("無極性框架下無例外", not at_np.exception,
           str(at_np.exception[0].value)[:200] if at_np.exception else "")
        ok("有極性框架的子頁籤較多（多一個極性平衡）",
           len(at_np.tabs) < n_ri, f"{len(at_np.tabs)} < {n_ri}")
        if not at_np.exception:
            blob = " ".join([str(m.label) for m in at_np.metric] +
                            [str(c.value) for c in at_np.caption])
            ok("畫面出現新框架的維度標籤", "Alpha" in blob or "Beta" in blob)
            ok("畫面不再出現 RI 維度",
               "Reflexivity" not in blob and "Anticipation" not in blob)
    finally:
        F.FRAMEWORK_DIR = real_dir
        F.reset()
ok("測試沒有污染真正的 frameworks/ 目錄",
   not os.path.exists(os.path.join(F.FRAMEWORK_DIR, "smoke_nopolarity.json")))

print()
print("=" * 70)
print("測試 5：複核狀態與引文驗證在 UI 上正確累積")
print("=" * 70)
F.reset()
rv_recs = ri_records()
RV.ensure_all(rv_recs)
segs = rv_recs[0][S.SEGMENTS]
RV.confirm(segs[0], reviewer="tester")
RV.update_codes(segs[1], ["REF-P"], reviewer="tester")
RV.delete_segment(rv_recs[0], segs[2][S.SEGMENT_ID], reviewer="tester")
RV.add_segment(rv_recs[0], "研究者補入的一段話", ["ANT-P"], reviewer="tester")
transcripts = {"產A": "\n".join(f"【受訪者】{s[S.FULL_TEXT]}"
                                for s in rv_recs[0][S.SEGMENTS])}
at = run_app({"ui_lang": "en", "records": rv_recs, "transcripts": transcripts})
ok("複核＋逐字稿載入時無例外", not at.exception,
   str(at.exception[0].value)[:200] if at.exception else "")
stats = RV.review_stats(rv_recs)
ok("複核統計正確",
   stats["human_added"] == 1 and stats["deleted"] == 1 and stats["modified"] == 1,
   str({k: stats[k] for k in ("human_added", "deleted", "modified")}))

print()
print("=" * 70)
print("測試 6：舊版中文鍵存檔仍可載入（遷移路徑）")
print("=" * 70)
# 寫進暫存區而不是使用者真正的 analyses/：這一段只需要一個檔案可以讀，
# 不需要 app 去掃描它（紀錄是直接塞進 session_state 的）。
_legacy_dir = tempfile.mkdtemp()
legacy_path = os.path.join(_legacy_dir, "_smoke_legacy.json")
with open(legacy_path, "w", encoding="utf-8") as f:
    json.dump({"受訪者": "舊版F",
               "預期": {"P": [{"標題": "t1", "精簡引文": "q1", "完整原文": "共用原文"}],
                        "N": []},
               "反思性": {"P": [], "N": []},
               "參與": {"P": [{"標題": "t2", "精簡引文": "q2", "完整原文": "共用原文"}],
                        "N": []},
               "回應性": {"P": [], "N": []},
               "維度重點分析": "舊版摘要"}, f, ensure_ascii=False)
try:
    rec = S.migrate_record(json.load(open(legacy_path, encoding="utf-8")))
    at = run_app({"ui_lang": "zh", "records": [rec]})
    ok("舊檔遷移後可渲染", not at.exception,
       str(at.exception[0].value)[:200] if at.exception else "")
    ok("舊檔合併為多重編碼", len(S.codes_of(rec[S.SEGMENTS][0])) == 2,
       str(S.codes_of(rec[S.SEGMENTS][0])))
finally:
    shutil.rmtree(_legacy_dir, ignore_errors=True)

print()
print("=" * 70)
print("測試 8：框架建構頁籤")
print("=" * 70)
F.reset()
at = run_app({"ui_lang": "en"})
blob = " ".join([str(m.label) for m in at.metric] +
                [str(c.value) for c in at.caption] +
                [str(m.value) for m in at.markdown] +
                [str(i.value) for i in at.info])
ok("空工作區時框架頁籤仍渲染", not at.exception,
   str(at.exception[0].value)[:200] if at.exception else "")
ok("顯示現用框架的維度數與編碼數",
   any(str(m.label) == I.t("fw.n_dimensions", "en") for m in at.metric))
ok("宣告了「文獻是知識來源」的原則",
   "Literature is the source of knowledge" in blob)
ok("尚未檢索時提示先做步驟 1", I.t("fw.need_corpus", "en") in blob, blob[:0])
# 這一項是關鍵：fw3 用了 st.stop()，若執行順序寫錯，匯入／匯出會整段消失
ok("未檢索時「匯入／匯出」仍然渲染得出來",
   any(I.t("fw.export_hint", "en") in str(c.value) for c in at.caption),
   "st.stop() 把後續內容吃掉了")
ok("內建框架標示為 builtin 來源",
   any(str(m.value) == I.t("fw.origin_builtin", "en") for m in at.metric))
ok("內建框架沒有 OpenAlex 出處紀錄時不顯示方法段落",
   I.t("fw.methods_para", "en") not in blob)

print()
print("=" * 70)
print("測試 9：選擇性載入（掃描但不自動載入）")
print("=" * 70)
# 這一段刻意**不建立也不刪除任何檔案**：測試不應該在使用者真正的
# analyses/ 裡放東西，也不該去刪那裡的檔案——那是研究資料。
# 改成拿磁碟上實際有什麼，去對照畫面上列出什麼。
F.reset()
# 這兩個名字必須跟 app.py 的 SAVE_DIR / SAVE_DIR_LEGACY 一致。同名會讓
# scan_saved 把同一批紀錄掃兩遍，側欄每一筆都出現兩次——底下這一項
# 順便驗證它們沒有被改成同一個名字。
SAVE_DIRS = ["analyses", "analyses_v1"]
ok("兩個存檔資料夾不同名", len(set(SAVE_DIRS)) == 2,
   "同名的話每筆紀錄都會在側欄列兩遍")
_src_dirs = open(APP, encoding="utf-8").read()
for _d in SAVE_DIRS:
    ok(f"app.py 確實用 {_d}", f'"{_d}"' in _src_dirs)

on_disk = []
for _d in SAVE_DIRS:
    if os.path.isdir(_d):
        on_disk += sorted(f for f in os.listdir(_d) if f.endswith(".json"))

at = run_app({"ui_lang": "en"})
ok("掃描存檔資料夾時不例外", not at.exception,
   str(at.exception[0].value)[:200] if at.exception else "")
ok("啟動時工作區仍為空（掃描不等於載入）",
   len(at.session_state["records"]) == 0,
   str(len(at.session_state["records"])))

picker = [m for m in at.multiselect if m.label == I.t("app.pick_records", "en")]
if not on_disk:
    print("  SKIP  磁碟上沒有既存分析，略過清單內容檢查")
    ok("沒有存檔時不顯示勾選清單，改顯示提示", len(picker) == 0)
else:
    ok("側欄出現訪談稿勾選清單", len(picker) == 1, f"found={len(picker)}")
    if picker:
        opts = list(picker[0].options)
        ok("清單筆數等於磁碟上的檔案數",
           len(opts) == len(on_disk), f"ui={len(opts)} disk={len(on_disk)}")
        ok("預設不是全部勾選就自動載入",
           len(at.session_state["records"]) == 0)
        # AppTest 的 options 回傳的是套用 format_func 之後的顯示字串。
        # 同名受訪者有多份存檔是常態（重跑、換模型、分次訪談），
        # 若標籤只有姓名，畫面上會出現兩三列一模一樣、無法分辨的選項。
        labels = [str(o) for o in opts]
        dup = [l for l, n in Counter(labels).items() if n > 1]
        ok("同名受訪者的多份存檔在畫面上可以分辨", not dup, str(dup[:3]))

print()
print("=" * 70)
print("測試 10：配額中斷後的續跑（已完成的不得重跑）")
print("=" * 70)
# 情境：六份逐字稿跑到第三份時 API 配額用盡。使用者換一把金鑰、
# 重新上傳同樣六份、再按一次開始。已完成的三份必須被略過——
# 它們已經付過錢了，重跑等於再付一次，而且會產生重複紀錄。
F.reset()
S_TF = S.TRANSCRIPT_FILE
done_recs = []
for fn in ("01_A.docx", "02_B.docx", "03_C.docx"):
    r = ri_records()[0]
    r[S.RESPONDENT] = fn[:-5]
    r[S_TF] = fn
    done_recs.append(r)

ok("紀錄保存得住逐字稿檔名", all(r.get(S_TF) for r in done_recs))

# --- 用**真正的** save_record 做往返，不要在測試裡重寫一次存檔邏輯 ---
#
# 要防的失效：在這裡自己寫 `{k: v for k, v in rec.items()
# if not k.startswith("_")}` 來模擬存檔。那等於複製一份存檔邏輯，
# save_record 真的出錯時——每存一次檔就把 _meta 蓋掉一次、模型與端點的
# 來源記錄就此消失——測試照樣會通過。所以走真正的 save_record。
# 測試模擬受測程式的行為，就只是在驗證自己。
_ns = {"os": os, "json": json, "re": __import__("re"),
       "datetime": __import__("datetime").datetime,
       "S": S, "F": F, "SAVE_DIR": tempfile.mkdtemp()}
_app_src = open(APP, encoding="utf-8").read()
exec(_app_src[_app_src.index("def save_record"):
              _app_src.index("def load_records_from_dir")], _ns)
_save = _ns["save_record"]

_rec = ri_records()[0]
_rec[S.META] = {"schema_version": S.SCHEMA_VERSION,
                "framework_id": F.DEFAULT_FRAMEWORK_ID,
                "source": "ollama/llama3.1:8b-instruct-q4_K_M@http://localhost:11434",
                "coded_at": "2026-08-21T10:00:00"}
_fn = _save(_rec)
with open(os.path.join(_ns["SAVE_DIR"], _fn), encoding="utf-8") as _f:
    _on_disk = json.load(_f)
_meta = _on_disk.get(S.META) or {}
ok("存檔後來源端點仍在檔案裡",
   _meta.get("source", "").startswith("ollama/llama3.1"),
   f"{_meta!r}；工具的賣點是稽核軌跡，存一次檔就掉了 provenance 是硬傷")
ok("存檔後編碼時間仍在", _meta.get("coded_at") == "2026-08-21T10:00:00")
ok("存檔會記下最後儲存時間", bool(_meta.get("last_saved")))

# 複核之後再存一次（最常見的操作），provenance 不得消失
_reloaded = S.migrate_record(_on_disk)
_reloaded["_file"] = _fn
_reloaded[S.SEGMENTS][0].setdefault(S.REVIEW, {})[S.STATUS] = S.STATUS_CONFIRMED
_save(_reloaded)
with open(os.path.join(_ns["SAVE_DIR"], _fn), encoding="utf-8") as _f:
    _again = (json.load(_f).get(S.META) or {})
ok("複核後再存一次，來源端點依然在",
   _again.get("source", "").startswith("ollama/llama3.1"),
   f"{_again!r}；這正是會掉資料的路徑")
ok("複核後再存一次，框架 id 依然在",
   _again.get("framework_id") == F.DEFAULT_FRAMEWORK_ID)

round_trip = S.migrate_record(json.loads(json.dumps(
    {k: v for k, v in done_recs[0].items() if not k.startswith("_")})))
ok("檔名經過存檔／載入往返後仍在", round_trip.get(S_TF) == "01_A.docx",
   str(round_trip.get(S_TF)))

at = run_app({"ui_lang": "zh", "records": done_recs})
ok("載入已完成紀錄時無例外", not at.exception,
   str(at.exception[0].value)[:200] if at.exception else "")

uploaded = ["01_A.docx", "02_B.docx", "03_C.docx",
            "04_D.docx", "05_E.docx", "06_F.docx"]
already = {r[S_TF] for r in done_recs}
todo = [f for f in uploaded if f not in already]
ok("只會跑剩下的三份", todo == ["04_D.docx", "05_E.docx", "06_F.docx"], str(todo))
ok("已完成的三份被略過", len(uploaded) - len(todo) == 3,
   str(len(uploaded) - len(todo)))

blob = " ".join([str(x.value) for x in at.info] +
                [str(x.value) for x in at.caption] +
                [str(x.value) for x in at.markdown])
ok("續跑提示文字存在且說明不會重複計費",
   "不會重複計費" in I.t("run.resume_hint", "zh"))
ok("中斷摘要明說已完成的沒有損失",
   "沒有任何損失" in I.t("run.stopped_summary", "zh"))
ok("重跑選項預設關閉且有警告成本",
   "會再花一次 API 配額" in I.t("run.redo_help", "zh"))

print()
print("=" * 70)
print("測試 11：逐字稿不必重新上傳（分析時已隨紀錄保存）")
print("=" * 70)
F.reset()
tr_recs = ri_records()
for r in tr_recs:
    r[S.TRANSCRIPT] = "\n".join(f"【受訪者】{s[S.FULL_TEXT]}"
                                for s in r[S.SEGMENTS])
at = run_app({"ui_lang": "zh", "records": tr_recs})
ok("紀錄自帶逐字稿時無例外", not at.exception,
   str(at.exception[0].value)[:200] if at.exception else "")
blob = " ".join([str(x.value) for x in at.success] +
                [str(x.value) for x in at.warning] +
                [str(x.value) for x in at.info])
ok("信度頁籤顯示「不需要重新上傳」",
   I.t("ir.transcripts_ready", "zh").split("{")[0] in blob or
   "不需要重新上傳" in blob, blob[:150])
ok("沒有要求上傳逐字稿的欄位",
   not any(I.t("ir.upload", "zh") == str(u.label) for u in at.file_uploader),
   str([str(u.label) for u in at.file_uploader]))

# 缺逐字稿時（v1 舊檔）才該出現上傳欄位
mixed = ri_records()
mixed[0][S.TRANSCRIPT] = "【受訪者】" + mixed[0][S.SEGMENTS][0][S.FULL_TEXT]
at2 = run_app({"ui_lang": "zh", "records": mixed})
ok("有缺口時無例外", not at2.exception,
   str(at2.exception[0].value)[:200] if at2.exception else "")
blob2 = " ".join([str(x.value) for x in at2.warning])
ok("缺逐字稿時明確說明缺幾份", "缺漏" in blob2, blob2[:150])
ok("缺逐字稿時才出現上傳欄位",
   any(I.t("ir.upload", "zh") == str(u.label) for u in at2.file_uploader),
   str([str(u.label) for u in at2.file_uploader]))

# 內含的逐字稿優先於上傳的：兩者衝突時必須採用 AI 實際編碼過的那一份
at3 = run_app({"ui_lang": "zh", "records": tr_recs,
               "transcripts": {"產A": "這是使用者後來上傳的不同版本"}})
ok("上傳版本不會覆蓋紀錄內含的逐字稿", not at3.exception,
   str(at3.exception[0].value)[:200] if at3.exception else "")

print()
print("=" * 70)
print("測試 12：模型清單不寫死（寫死的清單一定會過期）")
print("=" * 70)
# 要防的失效：模型清單寫死成 ["gemini-2.5-flash", "gemini-2.5-pro"]，
# 2.5 系列下架後新使用者直接吃 404：
#   "This model is no longer available to new users."
# 正常路徑改成向服務查詢，這裡驗證排序與墊底清單的行為。
_src = open(APP, encoding="utf-8").read()
_key = LLM._gemini_sort_key

pool = ["gemini-2.5-flash", "gemini-3-pro", "gemini-3.7-flash",
        "gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-3.7-pro",
        "gemini-3.8-flash-preview"]
ranked = sorted(pool, key=_key)
ok("預設選最新的正式版 Flash", ranked[0] == "gemini-3.7-flash", ranked[0])
ok("預覽版一律排最後（最快被下架）",
   ranked[-1] == "gemini-3.8-flash-preview", ranked[-1])
ok("同版本 Flash 排在 Pro 之前",
   ranked.index("gemini-3.7-flash") < ranked.index("gemini-3.7-pro"))
ok("舊版本排在新版本之後",
   ranked.index("gemini-3.6-flash") < ranked.index("gemini-2.5-flash"))
ok("lite 版不會被選為預設", "lite" not in ranked[0])
ok("沒有版本號也不炸", isinstance(_key("gemini-flash"), tuple))

# 地端模型的清單完全因人而異，更不可能寫死。這裡驗證排序把
# 「照著提示詞回傳 JSON 的機率高」的那些排在前面。
_local = sorted(["nomic-embed-text", "llama3.1:8b", "qwen2.5:7b-instruct",
                 "mistral:7b-instruct"], key=LLM._local_sort_key)
ok("嵌入模型排最後（不能拿來生成）", _local[-1] == "nomic-embed-text", str(_local))
ok("指令微調版排在 base 之前",
   _local.index("mistral:7b-instruct") < _local.index("llama3.1:8b"), str(_local))

# 寫死的模型清單不只可能出現在側欄，任何一個頁籤都可能有。
# 這一項掃全檔：app.py 裡任何地方都不該出現寫死的模型名稱——
# 墊底清單住在 tacit_llm，不是介面的事。
_hard = [ln.strip() for ln in _src.splitlines() if '"gemini-' in ln]
ok("app.py 沒有任何寫死的模型名稱", not _hard, str(_hard[:2]))

_pickers = [ln for ln in _src.splitlines() if 'selectbox(t("app.model")' in ln]
ok("每個模型選單都有兩個以上", len(_pickers) >= 2, str(len(_pickers)))
ok("每個模型選單都吃同一份 models 清單",
   all(", models," in ln or ", models)" in ln for ln in _pickers),
   str([ln.strip()[:70] for ln in _pickers
        if ", models," not in ln and ", models)" not in ln]))

ok("墊底清單不含已下架的 2.5 系列",
   not any("2.5" in m for m in LLM.FALLBACK_MODELS[LLM.GEMINI]),
   "墊底清單本身就過期的話，這個修法等於沒修")

print()
print("=" * 70)
print("測試 12b：供應者抽象層")
print("=" * 70)
# SoftwareX 的通用性要求裡，最實質的一項是「不綁單一雲端供應者」。
# 這一組驗證介面確實走抽象層，而不是某處還藏著直接呼叫 SDK 的路徑。
ok("app.py 不直接匯入 Gemini SDK",
   "google.generativeai" not in _src,
   "介面若還直接碰 SDK，地端使用者就會在某個頁籤上撞牆")
ok("app.py 不直接呼叫 genai", "genai." not in _src)
ok("三個供應者都在", set(LLM.PROVIDERS) == {"gemini", "ollama", "openai_compat"},
   str(LLM.PROVIDERS))
ok("地端供應者不需要金鑰",
   not LLM.Endpoint(LLM.OLLAMA, "m").needs_key)
ok("指向 localhost 的相容端點不需要金鑰",
   not LLM.Endpoint(LLM.OPENAI_COMPAT, "m",
                    base_url="http://localhost:1234/v1").needs_key)
ok("指向雲端的相容端點需要金鑰",
   LLM.Endpoint(LLM.OPENAI_COMPAT, "m",
                base_url="https://openrouter.ai/api/v1").needs_key,
   "把資料送到別人機器上卻不提示金鑰與倫理，是最糟的預設值")
ok("稽核字串記得下完整端點，不只模型名",
   "@" in LLM.Endpoint(LLM.OLLAMA, "llama3.1:8b").describe(),
   LLM.Endpoint(LLM.OLLAMA, "llama3.1:8b").describe())

# context 溢位守衛。這是地端最危險的失效模式：伺服器無聲截斷輸入，
# 卻照樣回傳格式完整的 JSON——結果看起來完全正常。
_tiny = LLM.Endpoint(LLM.OLLAMA, "m", num_ctx=4096, max_tokens=2048)
try:
    LLM.check_context(_tiny, "字" * 30000)
    ok("提示詞放不下時擋下不送", False, "沒擋，會被無聲截斷")
except LLM.ContextOverflow:
    ok("提示詞放不下時擋下不送", True)
try:
    LLM.check_context(_tiny, "short")
    ok("放得下時不誤擋", True)
except LLM.ContextOverflow as e:
    ok("放得下時不誤擋", False, str(e))
ok("雲端不套用地端的 context 檢查",
   LLM.check_context(LLM.Endpoint(LLM.GEMINI, "m", api_key="k"),
                     "字" * 30000) is None)

# JSON 擷取：地端模型常在 JSON 前後加話，貪婪正規式會把結語一起吃進來。
ok("擷取得出圍欄裡的 JSON",
   LLM._extract_first_json('sure:\n```json\n{"a":1}\n```\nhope that helps')
   == '{"a":1}')
ok("結語不會被吃進來",
   LLM._extract_first_json('{"a":{"b":2}} and that is all {stray')
   == '{"a":{"b":2}}')
ok("字串裡的大括號不會誤判",
   LLM._extract_first_json('{"q":"a } b"}') == '{"q":"a } b"}')
ok("沒有 JSON 就回空字串", LLM._extract_first_json("no json here") == "")

# Gemini SDK 有新舊兩套，API 完全不同。兩套都要支援：只裝了舊套件的
# 既有使用者不該因為升級而壞掉，新使用者也不該被引導去裝一個已經停止
# 維護的套件。沒裝任何一套時，程式仍必須能啟動（地端使用者的常態）。
ok("SDK 常數兩套都定義了",
   {LLM.GENAI_NEW, LLM.GENAI_OLD} == {"google-genai", "google-generativeai"})
ok("偵測結果只會是三種狀態之一",
   LLM.GEMINI_SDK in (None, LLM.GENAI_NEW, LLM.GENAI_OLD), str(LLM.GEMINI_SDK))
ok("HAS_GEMINI 與偵測結果一致",
   LLM.HAS_GEMINI == (LLM.GEMINI_SDK is not None))
_avail, _note = LLM.gemini_sdk_note()
ok("SDK 狀態說明與可用性一致", _avail == LLM.HAS_GEMINI)
if LLM.GEMINI_SDK == LLM.GENAI_OLD:
    ok("用舊 SDK 時會提示改裝新的", "google-genai" in _note, _note[:60])
elif LLM.GEMINI_SDK == LLM.GENAI_NEW:
    ok("用新 SDK 時不多嘴", _note == "", _note[:60])
else:
    ok("沒裝 SDK 時說明講清楚地端不需要它", "local providers" in _note, _note[:80])
ok("沒有金鑰時 Gemini 也回得出墊底清單而不是炸掉",
   isinstance(LLM.list_models(LLM.GEMINI, "", "")[0], list))

# 環境變數路徑：批次執行與可重現腳本靠這個，不能悄悄壞掉。
_env_before = {k: os.environ.get(k) for k in
               ("TACIT_PROVIDER", "TACIT_MODEL", "TACIT_BASE_URL")}
os.environ["TACIT_PROVIDER"] = "ollama"
os.environ["TACIT_MODEL"] = "llama3.1:8b"
_ep = LLM.from_env()
ok("讀得到環境變數設定", _ep is not None and _ep.model == "llama3.1:8b")
os.environ["TACIT_PROVIDER"] = "nonsense"
ok("無效的供應者回 None 而非炸掉", LLM.from_env() is None)
for k, v in _env_before.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v

print()
print("=" * 70)
print("測試 7：i18n 完整性")
print("=" * 70)
import tacit_strings  # noqa
ok("無重複鍵", not I.DUPLICATES, str(I.DUPLICATES[:5]))
for lang in I.LANGS:
    ok(f"{lang} 無缺漏翻譯", not I.missing_keys(lang),
       str(I.missing_keys(lang)[:5]))
ok("英文字串不含中文",
   not any(any("一" <= ch <= "鿿" for ch in I.t(k, "en"))
           for k in I.STRINGS))

print()
print("=" * 70)
print("測試 8：側欄狀態值不合法時，app 不可以起不來")
print("=" * 70)
# 要防的失效：Streamlit 1.63.0 在真實瀏覽器裡把供應者選單的**顯示標籤**
# （"Google Gemini (cloud)"）存進 session_state["llm_provider"]，接著
# `LLM.PROVIDERS.index(...)` 直接 ValueError，整個 app 開不起來。
# AppTest 繞過前端所以重現不出那個「存進標籤」的動作，但可以直接注入——
# 這裡驗的是「不論 session_state 裡是什麼，側欄都要活著」。
import tacit_llm as _LLM                                     # noqa: E402
_cases = [
    ("gemini", "識別碼"),
    ("Google Gemini (cloud)", "英文顯示標籤（使用者實際撞到的值）"),
    (I.t("llm.provider.ollama", "zh"), "中文顯示標籤"),
    ("not-a-provider", "垃圾值"),
    ("", "空字串"),
]
for injected, why in _cases:
    F.reset()
    _at = AppTest.from_file(APP, default_timeout=300)
    _at.session_state["ui_lang"] = "en"
    _at.session_state["records"] = []
    _at.session_state["llm_provider"] = injected
    _at.run()
    ok(f"注入 {why} → app 起得來",
       not _at.exception,
       str(_at.exception[0].value)[:80] if _at.exception else "")
    if not _at.exception:
        ok(f"注入 {why} → 狀態被正規化成識別碼",
           _at.session_state["llm_provider"] in _LLM.PROVIDERS,
           repr(_at.session_state["llm_provider"]))
# 而且標籤要對得回正確的供應者，不是一律退回預設
F.reset()
_at = AppTest.from_file(APP, default_timeout=300)
_at.session_state["ui_lang"] = "en"; _at.session_state["records"] = []
_at.session_state["llm_provider"] = I.t("llm.provider.ollama", "en")
_at.run()
ok("Ollama 的標籤對回 ollama，不是退回 gemini",
   not _at.exception and _at.session_state["llm_provider"] == _LLM.OLLAMA,
   repr(_at.session_state["llm_provider"]) if not _at.exception else "exception")

print()
print("=" * 70)
print("測試 13：開放編碼的兩個頁籤（模式切換與碼簿）")
print("=" * 70)
# 開放編碼多了一個頁籤與一個模式切換。這裡守的是最基本但最容易壞的事：
# 兩種模式都起得來、碼簿空的時候不炸、碼簿有東西的時候畫得出來。
import tacit_open as _OP                                        # noqa: E402

F.reset()
# ui_lang 只有 I.LANGS 的兩個值（en / zh）。分析語言才是 zh-Hant 那一組，
# 兩者是刻意分開的：介面英文、逐字稿中文是常見組合。
_at = run_app({"ui_lang": "zh", "records": [], "coding_mode": "framework"})
ok("框架模式起得來", not _at.exception,
   str(_at.exception[0].value)[:120] if _at.exception else "")
ok("有碼簿頁籤", any("碼簿" in str(x.label) for x in _at.tabs),
   str([str(x.label) for x in _at.tabs][:12]))

_at = run_app({"ui_lang": "zh", "records": [], "coding_mode": "open"})
ok("開放編碼模式起得來", not _at.exception,
   str(_at.exception[0].value)[:200] if _at.exception else "")
if not _at.exception:
    _txt = " ".join(str(m.value) for m in _at.markdown) + \
           " ".join(str(c.value) for c in _at.caption) + \
           " ".join(str(i.value) for i in _at.info)
    ok("空碼簿時說明碼簿是怎麼來的",
       "碼簿" in _txt, _txt[:100])
    ok("開放編碼模式有自己的開始按鈕",
       any("開放編碼" in str(b.label) for b in _at.button),
       str([str(b.label) for b in _at.button][:10]))

# 碼簿有內容時，碼簿頁籤要畫得出表、統計與定案區塊
_cb = _OP.new_codebook("zh-Hant")
for _lab, _n in [("護理人力不足", 5), ("法規更新頻繁", 3), ("只出現一次的碼", 1)]:
    _c = _OP.add_code(_cb, _lab, f"{_lab}的定義")
    _c[_OP.CODE_COUNT] = _n
    _c[_OP.CODE_EXAMPLES] = [{S.QUOTE: f"{_lab}的引文", S.RESPONDENT: "P1"}]
_at = run_app({"ui_lang": "zh", "records": [], "coding_mode": "open",
               "codebook": _cb, "open_records": []})
ok("碼簿有內容時不炸", not _at.exception,
   str(_at.exception[0].value)[:200] if _at.exception else "")
if not _at.exception:
    _all = " ".join(str(m.value) for m in _at.markdown) + \
           " ".join(str(c.value) for c in _at.caption) + \
           " ".join(str(w.value) for w in _at.warning)
    ok("碼簿頁籤顯示碼的內容", "護理人力不足" in _all or
       any("護理人力不足" in str(d.value.to_dict()) for d in _at.dataframe),
       _all[:120])
    ok("只出現一次的碼有被指出來（但不自動移除）",
       "只出現一次" in _all, _all[:200])
    ok("有定案成框架的入口",
       any("框架" in str(b.label) for b in _at.button),
       str([str(b.label) for b in _at.button][:10]))
    # 這條線是方法論的：碼還在長的時候，頻次都是暫時的
    ok("說明定案之後分析才成立",
       "共現" in _all or "信度" in _all, _all[:200])

# 側邊欄的兩個語言選單若直接 .index() session_state 的值，舊存檔、舊版本
# 的狀態、或把分析語言的代碼放進介面語言，都會讓側邊欄第一個元件就 ValueError，
# 整個畫面全白。這兩條守的是「不認得的代碼要退得漂亮」，不是「代碼要正確」。
_at = run_app({"ui_lang": "zh-Hant", "records": []})
ok("不認得的介面語言代碼不會讓 app 起不來", not _at.exception,
   str(_at.exception[0].value)[:120] if _at.exception else "")
ok("zh-Hant 退回中文介面（前綴比對），不是退回英文",
   any("碼簿" in str(x.label) for x in _at.tabs),
   str([str(x.label) for x in _at.tabs][:12]))
_at = run_app({"ui_lang": "en", "records": [], "analysis_lang": "klingon"})
ok("不認得的分析語言代碼不會讓 app 起不來", not _at.exception,
   str(_at.exception[0].value)[:120] if _at.exception else "")
F.reset()

print()
print("=" * 70)
print("測試 14：沒有模型、也沒有任何分析時的人工信度")
print("=" * 70)
# 一位手邊沒有 Ollama、也不想把逐字稿送上雲端的研究者打開
# 軟體時，工作區是空的、也沒有模型。每一個頁籤都只顯示「尚無資料」的話，
# 這位研究者什麼都做不了。這一段守的是：信度頁籤在這個情況下仍然做得完整件事——
# 上傳逐字稿 → 切單元 → 抽盲樣 → 產編碼表 → 回收 → 算係數。
import tacit_irr as _IR                                          # noqa: E402

F.reset()
_tr = {"P01": "\n".join([
    "訪員：你們在導入之前做了什麼評估？",
    "受訪者：我們先盤點了現有流程，也找了幾個部門一起討論可能的風險。",
    "訪員：那使用者的意見呢？",
    "受訪者：老實說一開始沒有問，是上線之後被反映介面太複雜才回頭改的。",
    "訪員：現在回頭看有什麼不同的做法？",
    "受訪者：會更早把第一線的人拉進來，而不是等到定案之後才說明。"])}
_frame, _diag = _IR.build_frame([], _tr)          # 沒有紀錄、沒有模型編碼
ok("沒有紀錄也建得出抽樣框", len(_frame) > 0, str(_diag))
ok("抽樣框裡沒有模型編碼", _diag["ai_coded_units"] == 0, str(_diag))

_samp = _IR.stratified_sample(_frame, n=100, seed=1)
ok("全部未標記時抽樣不會被未標記配額砍掉",
   len(_samp) == len(_frame), f"{len(_samp)}/{len(_frame)}")
_sess = _IR.create_session(_samp, ["coder_a", "coder_b"], seed=1)
_uids = [u[S.UNIT_ID] for u in _sess[S.UNITS]]
_a = {u: (["ANT-P"] if i % 2 else ["ENG-N"]) for i, u in enumerate(_uids)}
_b = {u: (["ANT-P"] if i % 3 else ["ENG-N"]) for i, u in enumerate(_uids)}
_sess[S.HUMAN_CODINGS] = {"coder_a": _a, "coder_b": _b}

_state = {"ui_lang": "en", "records": [], "irr_frame": _frame,
          "irr_diag": _diag, "irr_human_only": True, "irr_session": _sess}
_at = run_app(_state)
ok("空工作區＋純人工信度不例外", not _at.exception,
   str(_at.exception[0].value)[:200] if _at.exception else "")
if not _at.exception:
    _cap = " ".join(str(c.value) for c in _at.caption)
    _err = " ".join(str(e.value) for e in _at.error)
    _lab = " ".join(str(m.label) for m in _at.metric)
    ok("說明這是沒有模型編碼的抽樣框",
       I.t("ir.human_only_frame", "en")[:30] in _cap, _cap[:160])
    ok("不再誤報「抽樣框裡沒有未標記單元」",
       I.t("ir.no_uncoded", "en")[:30] not in _err, _err[:160])
    ok("仍然算得出 κ 與 PABAK",
       I.t("stat.kappa", "en") in _lab and I.t("stat.pabak", "en") in _lab,
       _lab[:200])
    ok("不顯示模型的 precision / recall（沒有對象可比）",
       I.t("ir.ai_pr", "en") not in
       " ".join(str(m.value) for m in _at.markdown),
       "")
    ok("信度報表的編碼者選單不含 AI",
       all("AI" not in (s.options or [])
           for s in _at.selectbox if s.label == I.t("ir.coder_a", "en")),
       str([s.options for s in _at.selectbox
            if s.label == I.t("ir.coder_a", "en")]))

# 同一份狀態換成「有紀錄、有模型編碼」時，precision / recall 必須回來——
# 上面那幾條不能是把功能關掉關出來的。
_recs = ri_records()
_at2 = run_app({"ui_lang": "en", "records": _recs,
                "irr_frame": _frame, "irr_diag": _diag,
                "irr_human_only": False, "irr_session": _sess})
ok("一般模式下 precision / recall 仍在", not _at2.exception and
   I.t("ir.ai_pr", "en") in " ".join(str(m.value) for m in _at2.markdown),
   str(_at2.exception[0].value)[:160] if _at2.exception else "")
F.reset()

print()
print("=" * 70)
print("測試 15：選單的顯示函式不得依賴「之後才被改掉」的變數")
print("=" * 70)
# app.py 是一支從頭跑到尾的指令稿，所有名字共用一個模組命名空間。
# `format_func=lambda i: names.get(i, i)` 這種寫法查的是**呼叫當下**的
# `names`——而 `names` 在後面的頁籤裡被重新指成 list 過。畫面上不一定看得出來
# （Streamlit 在畫的當下就呼叫過一次），但任何事後再問一次顯示值的人
# ——測試工具、以及 Streamlit 自己在回填 widget 狀態的時候——都會拿到
# AttributeError，或是看到選單顯示成內部識別碼。
# 這一條把每個選單的顯示函式在整支指令稿跑完之後再呼叫一次。


def format_funcs_survive(at, label):
    from streamlit.testing.v1.element_tree import TESTING_KEY
    try:
        ss = at.session_state
        reg = ss[TESTING_KEY] if TESTING_KEY in ss else {}
    except Exception:                                            # noqa: BLE001
        reg = {}
    broken = []
    for w in list(at.selectbox) + list(at.radio) + list(at.multiselect):
        fn = reg.get(w.id)
        if fn is None:
            continue
        for opt_val in ([w.value] if not isinstance(w.value, list) else w.value):
            try:
                fn(opt_val)
            except Exception as e:                               # noqa: BLE001
                broken.append(f"{w.label!r}: {type(e).__name__}: {e}")
    ok(f"{label}：所有顯示函式在指令稿跑完後仍可呼叫",
       not broken, "; ".join(broken[:3]))
    return broken


F.reset()
for _fw in ("ri_stilgoe_2013", "utaut_venkatesh_2003"):
    _at = run_app({"ui_lang": "en", "framework_id": _fw,
                   "records": ri_records()})
    if not _at.exception:
        format_funcs_survive(_at, _fw)
    else:
        ok(f"{_fw} 渲染無例外", False, str(_at.exception[0].value)[:160])

# 空工作區時側邊欄仍然要顯示框架名稱，而不是退回顯示識別碼
_at = run_app({"ui_lang": "en", "framework_id": "utaut_venkatesh_2003",
               "records": []})
if not _at.exception:
    format_funcs_survive(_at, "空工作區")
    _fwbox = [s for s in _at.selectbox
              if s.label == I.t("side.framework", "en")]
    ok("找得到框架選單", bool(_fwbox))
    if _fwbox:
        ok("框架選單顯示的是名稱不是識別碼",
           all("_" not in o for o in _fwbox[0].options),
           str(_fwbox[0].options))
        ok("選單指得到現用框架（不會 ValueError）",
           _fwbox[0].index is not None, str(_fwbox[0].value))
F.reset()

print()
print("=" * 70)
print("測試 16：開放編碼時畫面上不該還擺著一個框架")
print("=" * 70)
# 要防的混淆：模式選單若藏在「執行新分析」頁籤裡，而側邊欄永遠顯示框架選單、
# 標題下方永遠印著框架的文獻。選了開放編碼的人一眼望去看到的仍然是
# 「Responsible Innovation · Stilgoe et al. (2013)」，分不清現在到底是哪一種。
# 模式決定碼從哪裡來，所以它放在側邊欄、框架選單的上面；選了開放編碼，
# 框架選單與文獻就收起來。
F.reset()


def _mode_view(mode, **extra):
    _a = run_app({"ui_lang": "en", "records": [], "coding_mode": mode, **extra})
    return _a


_fwv = _mode_view("framework")
ok("框架模式起得來", not _fwv.exception,
   str(_fwv.exception[0].value)[:160] if _fwv.exception else "")
if not _fwv.exception:
    ok("模式選單在側邊欄",
       I.t("run.mode", "en") in [r.label for r in _fwv.sidebar.radio],
       str([r.label for r in _fwv.sidebar.radio]))
    ok("框架模式：側邊欄有框架選單",
       I.t("side.framework", "en") in [x.label for x in _fwv.sidebar.selectbox])
    ok("框架模式：標題下方是框架與它的文獻",
       "Stilgoe" in str(_fwv.caption[0].value), str(_fwv.caption[0].value)[:80])
    ok("主畫面不再另外畫一個模式選單（兩個選單會互相打架）",
       I.t("run.mode", "en") not in [r.label for r in _fwv.radio
                                     if r not in list(_fwv.sidebar.radio)])

_opv = _mode_view("open")
ok("開放編碼模式起得來", not _opv.exception,
   str(_opv.exception[0].value)[:160] if _opv.exception else "")
if not _opv.exception:
    ok("開放編碼：側邊欄**沒有**框架選單",
       I.t("side.framework", "en") not in [x.label for x in _opv.sidebar.selectbox],
       str([x.label for x in _opv.sidebar.selectbox]))
    ok("開放編碼：標題下方不出現框架的文獻",
       "Stilgoe" not in str(_opv.caption[0].value), str(_opv.caption[0].value)[:80])
    ok("開放編碼：標題下方明說沒有套用框架",
       I.t("app.header_open", "en") == str(_opv.caption[0].value))
    _side = " ".join(str(c.value) for c in _opv.sidebar.caption)
    ok("開放編碼：側邊欄說明碼從哪裡來、碼簿現在多大",
       "No framework is applied" in _side and "0 code" in _side, _side[:140])
    ok("開放編碼：側邊欄不再印「4 × 2 = 8 codes」",
       "\u00d7" not in _side, _side[:140])

# 不認得的模式值要退回框架模式，不能讓側邊欄第一個 radio 就 ValueError
_bad = _mode_view("reflexive")
ok("不認得的模式值不會讓 app 起不來", not _bad.exception,
   str(_bad.exception[0].value)[:160] if _bad.exception else "")

# 碼簿定案之後留下的記號，下一輪要把模式切回框架
_pend = _mode_view("open", _pending_mode="framework")
ok("定案後的下一輪自動切回框架模式",
   not _pend.exception and _pend.session_state["coding_mode"] == "framework",
   str(_pend.session_state["coding_mode"]) if not _pend.exception else "exception")
F.reset()

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
