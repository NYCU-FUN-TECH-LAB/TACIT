"""
驗證 tacit_openalex.py：檢索客戶端、摘要還原、幻覺防護、人工核可、出處紀錄。

完全不碰網路。假的 HTTP 層覆寫 Client._fetch，因此參數組裝、快取、
額度計算都會被實際執行到，只有最後那一步網路呼叫被換掉。

最關鍵的一組是「幻覺防護」：模型引用一篇沒有被檢索到的文獻時，
系統必須拒絕，而不是照單全收。編碼框架是整份研究的效度根基，
在這裡放行等於讓整條分析管線建立在杜撰的文獻上。
"""
import json
import sys
import tempfile
import urllib.error

import tacit_framework as F
import tacit_openalex as OA

FAIL = []


def check(label, got, want):
    ok = got == want
    print(("  PASS  " if ok else "  FAIL  ") + f"{label}: got={got!r} want={want!r}")
    if not ok:
        FAIL.append(label)


def check_true(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


# =====================================================================
# 假的 OpenAlex 回應
# =====================================================================
def inv(text):
    """把一段文字轉成 OpenAlex 的倒排索引格式。"""
    d = {}
    for i, w in enumerate(text.split()):
        d.setdefault(w, []).append(i)
    return d


def work(wid, title, year, authors, venue, cites, abstract, doi=None,
         vol=None, issue=None, fp=None, lp=None):
    return {
        "id": f"https://openalex.org/{wid}",
        "display_name": title,
        "publication_year": year,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "type": "article",
        "cited_by_count": cites,
        "authorships": [{"author": {"display_name": a}} for a in authors],
        "primary_location": {"source": {"display_name": venue}},
        "biblio": {"volume": vol, "issue": issue, "first_page": fp, "last_page": lp},
        "open_access": {"is_oa": True, "oa_url": f"https://example.org/{wid}.pdf"},
        "abstract_inverted_index": inv(abstract) if abstract else None,
    }


SEMINAL = [
    work("W1", "Developing a framework for responsible innovation", 2013,
         ["Jack Stilgoe", "Richard Owen", "Phil Macnaghten"], "Research Policy",
         4200, "This paper describes four integrated dimensions of responsible "
         "innovation: anticipation, reflexivity, inclusion and responsiveness. "
         "It argues that governance of emerging technology must move upstream.",
         doi="10.1016/j.respol.2013.05.008", vol="42", issue="9",
         fp="1568", lp="1580"),
    work("W2", "Responsible research and innovation: from science in society", 2012,
         ["Rene von Schomberg"], "Science and Public Policy", 1900,
         "A normative account of responsible research and innovation grounded in "
         "the anticipation of societal impacts and in deliberative inclusion of "
         "stakeholders throughout the innovation process."),
    work("W3", "Anticipatory governance of nanotechnology", 2010,
         ["David Guston"], "Journal of Nanoparticle Research", 1200,
         "Anticipatory governance builds societal capacity for foresight, "
         "engagement and integration well before technologies are locked in."),
]
RECENT = [
    work("W4", "Reflexivity in practice: a study of AI developers", 2023,
         ["Ana Silva", "Wei Chen"], "Science Technology and Human Values", 45,
         "Drawing on interviews with developers, we show how reflexivity is "
         "enacted and undermined in everyday engineering work.", doi="10.1177/x"),
    work("W5", "Inclusion beyond consultation", 2024, ["Maria Rossi"],
         "Journal of Responsible Innovation", 30,
         "We distinguish consultation from genuine inclusion and show that "
         "downstream participation rarely changes design decisions."),
    work("W6", "A work with no abstract at all", 2021, ["Ken Watanabe"],
         "Some Journal", 12, ""),
]


class FakeClient(OA.Client):
    """
    覆寫 _fetch：把 URL 對應到假回應。sort 參數決定回傳哪一批，
    這樣 retrieve_corpus 的兩趟檢索邏輯才會真的被走過。
    """

    def __init__(self, *a, **kw):
        self.script = kw.pop("script", None)
        super().__init__(*a, **kw)
        self.urls = []

    def _fetch(self, url):
        self.urls.append(url)
        if self.script:
            return self.script(url)
        if "per-page=1" in url and "publication_year" not in url:
            # 片語探測：只取 meta.count
            n = 5 if "%22responsible+innovation+anticipation%22" in url \
                or "%22responsible%20innovation%20anticipation%22" in url else 9310
            body = {"meta": {"count": n}, "results": []}
        elif "/topics" in url:
            body = {"results": [
                {"id": "https://openalex.org/T10012", "display_name":
                 "Responsible Research and Innovation", "works_count": 8123,
                 "description": "Governance of emerging science and technology",
                 "field": {"display_name": "Social Sciences"}},
                {"id": "https://openalex.org/T99999", "display_name":
                 "Innovation Management", "works_count": 40000,
                 "description": "", "field": {"display_name": "Business"}}]}
        elif "publication_year" in url:
            body = {"meta": {"count": 512}, "results": RECENT}
        else:
            body = {"meta": {"count": 9310}, "results": SEMINAL}
        return json.dumps(body), {"X-RateLimit-Remaining": "99980",
                                  "X-RateLimit-Credits-Used": "10"}


# =====================================================================
print("=" * 70)
print("測試 1：摘要倒排索引還原")
print("=" * 70)
check("還原詞序", OA.reconstruct_abstract(inv("the quick brown fox")),
      "the quick brown fox")
check("空索引", OA.reconstruct_abstract(None), "")
check("空字典", OA.reconstruct_abstract({}), "")
check("非連續位置也照序組回", OA.reconstruct_abstract({"b": [3], "a": [1]}), "a b")
check("重複詞多個位置",
      OA.reconstruct_abstract({"a": [0, 2], "b": [1]}), "a b a")
check_true("非法型別不炸", OA.reconstruct_abstract("not a dict") == "")

print()
print("=" * 70)
print("測試 2：文獻正規化與引文格式")
print("=" * 70)
w1 = OA.normalise_work(SEMINAL[0])
check("OpenAlex ID 去掉網址前綴", w1["openalex_id"], "W1")
check("DOI 去掉網址前綴", w1["doi"], "10.1016/j.respol.2013.05.008")
check("年份", w1["year"], 2013)
check("作者數", len(w1["authors"]), 3)
check("期刊", w1["venue"], "Research Policy")
check("頁碼合併", w1["pages"], "1568-1580")
check_true("摘要已還原", w1["abstract"].startswith("This paper describes four"))
check_true("有摘要旗標", w1["has_abstract"])
check_true("無摘要文獻標記正確",
           not OA.normalise_work(RECENT[2])["has_abstract"])

check("三位作者引文", OA.apa_citation(w1),
      "Stilgoe, J., Owen, R., & Macnaghten, P. (2013). Developing a framework "
      "for responsible innovation. Research Policy, 42(9), 1568-1580. "
      "https://doi.org/10.1016/j.respol.2013.05.008")
check("單一作者引文", OA.apa_citation(OA.normalise_work(SEMINAL[2])),
      "Guston, D. (2010). Anticipatory governance of nanotechnology. "
      "Journal of Nanoparticle Research.")
check("四位以上作者用 et al.",
      OA.apa_citation({"authors": ["A B", "C D", "E F", "G H"], "year": 2020,
                       "title": "T", "venue": ""}),
      "B, A., et al. (2020). T.")
check("無作者不編造", OA.apa_citation({"authors": [], "year": 1999, "title": "T"}),
      "[No author listed] (1999). T.")
check("無年份標 n.d.", OA.apa_citation({"authors": ["X Y"], "title": "T"}),
      "Y, X. (n.d.). T.")
check("中日韓姓名不拆", OA._surname_initials("王小明"), "王小明")

print()
print("=" * 70)
print("測試 3：客戶端額度、快取與錯誤處理")
print("=" * 70)
with tempfile.TemporaryDirectory() as d:
    c = FakeClient(api_key="", cache_dir=d, min_interval=0)
    check("無金鑰額度", c.daily_budget, OA.DAILY_CREDITS_NO_KEY)
    check_true("無金鑰提示含申請網址", OA.API_KEY_URL in c.budget_note("en"))
    check_true("中文提示可用", "金鑰" in c.budget_note("zh"))

    # 把 email 當金鑰填是很常見的誤解：舊的 polite pool 要求提供 email，
    # 該機制已於 2026-02-13 廢除，但多數函式庫仍保留 email 欄位。
    em = FakeClient(api_key="dddsss5419@gmail.com", cache_dir=d, min_interval=0)
    check_true("email 不被當成金鑰", not em.has_key)
    check_true("偵測到填的是 email", em.key_looks_like_email)
    check("填 email 時額度等同無金鑰", em.daily_budget, OA.DAILY_CREDITS_NO_KEY)
    for lg in ("en", "zh"):
        note = em.budget_note(lg)
        check_true(f"{lg} 明說這是 email 不是金鑰",
                   "email" in note.lower() or "email" in note)
        check_true(f"{lg} 說明 polite pool 已廢除",
                   "polite pool" in note.lower())
    em.works(search="responsible innovation via email")
    check_true("email 不會被送進 URL", "@" not in em.urls[0], em.urls[0][:90])
    check_true("一般金鑰不會被誤判為 email",
               not FakeClient(api_key="abc123", cache_dir=d).key_looks_like_email)

    c2 = FakeClient(api_key="KEY123", cache_dir=d, min_interval=0)
    check("有金鑰額度", c2.daily_budget, OA.DAILY_CREDITS_WITH_KEY)
    c2.works(search="responsible innovation", per_page=3)
    check("呼叫一次", c2.calls, 1)
    check("credits 由標頭讀取", c2.credits_used, 10)
    check("剩餘額度已記錄", c2.credits_remaining, 99980)
    check_true("金鑰有出現在實際 URL", "api_key=KEY123" in c2.urls[0])

    c2.works(search="responsible innovation", per_page=3)
    check("第二次命中快取", c2.cache_hits, 1)
    check("命中快取不再呼叫網路", c2.calls, 1)
    check("命中快取不消耗 credits", c2.credits_used, 10)

    # 快取鍵不含金鑰：換一把金鑰仍應命中同一筆快取
    c3 = FakeClient(api_key="DIFFERENT", cache_dir=d, min_interval=0)
    c3.works(search="responsible innovation", per_page=3)
    check("快取鍵不含金鑰（換金鑰仍命中）", c3.calls, 0)

    off = FakeClient(api_key="", cache_dir=d, offline=True, min_interval=0)
    check_true("離線命中快取", bool(off.works(search="responsible innovation",
                                              per_page=3)))
    try:
        off.works(search="something never cached")
        check_true("離線未命中應拋 OfflineMiss", False)
    except OA.OfflineMiss:
        check_true("離線未命中應拋 OfflineMiss", True)


def http_error(code):
    def _f(url):
        raise urllib.error.HTTPError(url, code, "boom", {}, None)
    return _f


with tempfile.TemporaryDirectory() as d:
    for code in (409, 429):
        c = FakeClient(cache_dir=d, min_interval=0, script=http_error(code))
        try:
            c.works(search=f"q{code}")
            check_true(f"HTTP {code} 應拋 QuotaError", False)
        except OA.QuotaError as e:
            check_true(f"HTTP {code} 應拋 QuotaError", True)
            check_true(f"HTTP {code} 訊息說明如何解決",
                       OA.API_KEY_URL in str(e) or "credit" in str(e).lower())
    c = FakeClient(api_key="BAD", cache_dir=d, min_interval=0,
                   script=http_error(401))
    try:
        c.works(search="q401")
        check_true("HTTP 401 應拋 OpenAlexError", False)
    except OA.QuotaError:
        check_true("HTTP 401 不該被當成額度問題", False)
    except OA.OpenAlexError as e:
        check_true("HTTP 401 應拋 OpenAlexError", True)
        check_true("401 訊息提到金鑰", "key" in str(e).lower())
    check("無金鑰時 rate_limit 不浪費呼叫",
          FakeClient(cache_dir=d, min_interval=0).rate_limit()["error"], "no api key")

print()
print("=" * 70)
print("測試 4：檢索策略（兩趟：奠基 + 近年）")
print("=" * 70)
with tempfile.TemporaryDirectory() as d:
    c = FakeClient(api_key="K", cache_dir=d, min_interval=0)
    topics = OA.suggest_topics(c, "responsible innovation")
    check("主題候選數", len(topics), 2)
    check("主題 ID 已去前綴", topics[0]["id"], "T10012")

    works, log = OA.retrieve_corpus(c, "responsible innovation",
                                    n_seminal=3, n_recent=3, topic_id="T10012")
    check("兩趟檢索", len(log["passes"]), 2)
    check("第一趟為奠基", log["passes"][0]["pass"], "seminal")
    check("奠基趟依被引排序", log["passes"][0]["sort"], "cited_by_count:desc")
    check("近年趟有年份篩選",
          "publication_year" in log["passes"][1]["filters"], True)
    check_true("主題篩選有帶入",
               log["passes"][0]["filters"].get("topics.id") == "T10012")
    check("合併後文獻數", len(works), 6)
    check("檢索紀錄的總數與清單一致", log["total_works"], len(works))
    check("有摘要者計數", log["with_abstract"], 5)
    check("每篇都標了來自哪一趟",
          sorted({w["retrieval_pass"] for w in works}), ["recent", "seminal"])
    check_true("有記錄檢索時間", bool(log["retrieved_at"]))
    check_true("有記錄可得總筆數",
               log["passes"][0]["total_available"] == 9310)

    works2, _ = OA.retrieve_corpus(c, "responsible innovation", n_seminal=3,
                                   n_recent=3, topic_id="T10012",
                                   require_abstract=True)
    check("require_abstract 排除無摘要文獻", len(works2), 5)

print()
print("=" * 70)
print("測試 4b：檢索式的精準度（這是把不相干文獻擋在外面的關卡）")
print("=" * 70)
# 要防的失效：查「responsible innovation anticipation」回來的是放射性碳定年
# 校正曲線、鋰電池綜述、DARPA 無人車——全是被引數極高、但只在**全文**
# 某處剛好出現過其中一個詞的論文。原因是用了 search= 參數（比對全文、
# 會做詞幹還原、詞之間非 AND），再加上 sort=cited_by_count:desc
# 把關聯度排序整個蓋掉。
check("整串當片語", OA.phrase_filter("responsible innovation"),
      '"responsible innovation"')
check("多餘空白會正規化", OA.phrase_filter("  responsible   innovation "),
      '"responsible innovation"')
check("使用者自寫的引號原樣保留",
      OA.phrase_filter('"responsible innovation" AND ethics'),
      '"responsible innovation" AND ethics')
check("使用者自寫布林原樣保留", OA.phrase_filter("innovation OR governance"),
      "innovation OR governance")
check("空查詢", OA.phrase_filter("   "), "")
check("AND 退路逐詞加引號", OA.and_filter("responsible innovation anticipation"),
      '"responsible" AND "innovation" AND "anticipation"')
check("AND 退路去掉虛詞", OA.and_filter("the ethics of innovation"),
      '"ethics" AND "innovation"')

with tempfile.TemporaryDirectory() as d:
    c = FakeClient(api_key="K", cache_dir=d, min_interval=0)
    _, lg = OA.retrieve_corpus(c, "responsible innovation", n_seminal=3,
                               n_recent=0)
    joined = " ".join(c.urls)
    check_true("不再使用 search= 參數（那會比對全文）",
               "search=" not in joined.replace("title_and_abstract.search", ""),
               joined[:160])
    check_true("改用 title_and_abstract.search 硬性篩選",
               "title_and_abstract.search" in joined)
    check("片語命中數足夠時不退回 AND", lg.get("fallback_query"), None)
    check("檢索式有記錄下來", lg["search_expr"], '"responsible innovation"')

    c2 = FakeClient(api_key="K", cache_dir=d, min_interval=0)
    _, lg2 = OA.retrieve_corpus(c2, "responsible innovation anticipation",
                                n_seminal=3, n_recent=0)
    check_true("片語太窄時自動放寬為 AND", bool(lg2.get("fallback_query")),
               str(lg2.get("phrase_hits")))
    check("放寬後的檢索式", lg2["search_expr"],
          '"responsible" AND "innovation" AND "anticipation"')
    check_true("放寬的理由有寫進紀錄", "widened" in lg2.get("fallback_reason", ""))

# 事後體檢：檢索結果到底有多少真的談到查詢詞
good = [{"title": "Responsible innovation in practice", "abstract": "..."},
        {"title": "A study", "abstract": "on responsible innovation"}]
junk = [{"title": "IntCal20 Radiocarbon Age Calibration Curve", "abstract": "carbon"},
        {"title": "30 Years of Lithium-Ion Batteries", "abstract": "cells"},
        {"title": "Stanley: the robot that won DARPA", "abstract": "driving"}]
check("全部相關 → 1.0", OA.relevance_of(good, "responsible innovation"), 1.0)
check("全部不相關 → 0.0", OA.relevance_of(junk, "responsible innovation"), 0.0)
check("一半相關", OA.relevance_of(good + junk[:2], "responsible innovation"), 0.5)
check("空結果不除以零", OA.relevance_of([], "x"), 1.0)
check_true("虛詞不列入比對", OA.relevance_of(junk, "the of and") == 1.0)

CORPUS = [OA.normalise_work(w) for w in SEMINAL + RECENT]
for w in CORPUS:
    w["retrieval_pass"] = "seminal"
INDEX = OA.evidence_index(CORPUS)

print()
print("=" * 70)
print("測試 5：證據打包")
print("=" * 70)
check("代號從 W1 起", list(INDEX)[:3], ["W1", "W2", "W3"])
ev = OA.build_evidence(INDEX)
check_true("每篇都有代號", all(f"[W{i}]" in ev for i in range(1, 7)))
check_true("含被引次數", "cited_by=4200" in ev)
check_true("無摘要者明確標示", "(not available)" in ev)
check_true("摘要有進去", "four integrated dimensions" in ev)
short_ev = OA.build_evidence(INDEX, max_abstract_chars=40)
check_true("超長摘要被截斷", "…" in short_ev)


# =====================================================================
def good_draft():
    return json.dumps({
        "framework_name_en": "Responsible Innovation",
        "framework_name_zh": "負責任創新",
        "citation": "Stilgoe et al. (2013)",
        "description_en": "Four dimensions of responsible innovation.",
        "description_zh": "負責任創新的四個維度。",
        "has_polarity": True,
        "coverage_warning": "",
        "dimensions": [
            {"id": "anticipation", "label_en": "Anticipation", "label_zh": "預期",
             "definition_en": "Systematic thinking about plausible futures.",
             "definition_zh": "有系統地設想可能的未來。",
             "indicators_positive_en": ["scenario work"],
             "indicators_positive_zh": ["情境推演"],
             "indicators_negative_en": ["technological determinism"],
             "indicators_negative_zh": ["技術決定論"],
             "polarity_label_positive_en": "Foresight",
             "polarity_label_positive_zh": "前瞻",
             "polarity_label_negative_en": "Determinism",
             "polarity_label_negative_zh": "決定論",
             "grounding_refs": ["W1"], "supporting_refs": ["W3"],
             "grounding_note": "W1 defines anticipation as one of four dimensions."},
            {"id": "reflexivity", "label_en": "Reflexivity", "label_zh": "反思性",
             "definition_en": "Holding a mirror to one's own assumptions.",
             "definition_zh": "檢視自身的預設與知識限度。",
             "indicators_positive_en": ["acknowledging limits"],
             "indicators_positive_zh": ["承認限度"],
             "indicators_negative_en": ["expert hubris"],
             "indicators_negative_zh": ["專家傲慢"],
             "polarity_label_positive_en": "Self-critical",
             "polarity_label_positive_zh": "自我批判",
             "polarity_label_negative_en": "Hubris",
             "polarity_label_negative_zh": "傲慢",
             "grounding_refs": ["W1"], "supporting_refs": ["W4"],
             "grounding_note": "W1 and W4 establish reflexivity."},
        ]})


print()
print("=" * 70)
print("測試 6：草稿解析（正常情況）")
print("=" * 70)
draft, rep = OA.parse_draft(good_draft(), INDEX, "responsible innovation",
                            model_name="test-model")
check("維度數", rep["n_dimensions"], 2)
check("無錯誤", rep["errors"], [])
check("草稿通過框架驗證", F.validate(draft), [])
check("出處標記為草稿", draft[F.PROVENANCE], F.PROV_OPENALEX_DRAFT)
check("framework_id 由名稱轉出", draft[F.FRAMEWORK_ID], "responsible_innovation")
check("短碼自動生成", [d[F.DIM_SHORT] for d in draft[F.DIMENSIONS]],
      ["ANT", "REF"])
check("極性啟用", draft[F.POLARITY][F.POLARITY_ENABLED], True)
lit0 = draft[F.DIMENSIONS][0][F.DIM_LITERATURE]
check("第一維度文獻數（1 grounding + 1 supporting）", len(lit0), 2)
check("grounding 帶了 OpenAlex ID", lit0[0][F.LIT_OPENALEX_ID], "W1")
check("grounding 帶了被引次數", lit0[0][F.LIT_CITED_BY], 4200)
check("角色正確", [l[F.LIT_ROLE] for l in lit0],
      [F.ROLE_GROUNDING, F.ROLE_SUPPORTING])
check_true("未使用的文獻有被提醒",
           any("were not used" in w for w in rep["warnings"]),
           str(rep["warnings"]))
check_true("草稿可載入為 Framework 物件", F.load_dict(draft).id == "responsible_innovation")

print()
print("=" * 70)
print("測試 7：幻覺防護（本模組存在的理由）")
print("=" * 70)
halluc = json.loads(good_draft())
halluc["dimensions"][0]["grounding_refs"] = ["W1", "W99"]
halluc["dimensions"][0]["supporting_refs"] = ["W42"]
d2, r2 = OA.parse_draft(json.dumps(halluc), INDEX, "x")
check_true("捏造的文獻被列為錯誤", any("never retrieved" in e for e in r2["errors"]),
           str(r2["errors"]))
check_true("錯誤訊息指出是哪幾筆",
           any("W99" in e and "W42" in e for e in r2["errors"]))
ids0 = {l[F.LIT_OPENALEX_ID] for l in d2[F.DIMENSIONS][0][F.DIM_LITERATURE]}
check("捏造的文獻沒有進入框架", ids0, {"W1"})

only_fake = json.loads(good_draft())
for dd in only_fake["dimensions"]:
    dd["grounding_refs"] = ["W_MADE_UP"]
    dd["supporting_refs"] = []
try:
    OA.parse_draft(json.dumps(only_fake), INDEX, "x")
    check_true("全部文獻都是捏造時整份草稿失敗", False)
except OA.DraftError as e:
    check_true("全部文獻都是捏造時整份草稿失敗", True, str(e)[:60])

no_ground = json.loads(good_draft())
no_ground["dimensions"][0]["grounding_refs"] = []
d3, r3 = OA.parse_draft(json.dumps(no_ground), INDEX, "x")
check("沒有 grounding 的維度被丟棄", r3["n_dimensions"], 1)
check("丟棄原因有記錄", r3["dropped"][0]["reason"], "no valid grounding reference")
check_true("只剩一個維度時有警告",
           any("single dimension" in w for w in r3["warnings"]))

try:
    OA.parse_draft("模型今天心情不好，沒有輸出 JSON。", INDEX, "x")
    check_true("非 JSON 輸出應拋 DraftError", False)
except OA.DraftError:
    check_true("非 JSON 輸出應拋 DraftError", True)
try:
    OA.parse_draft('{"dimensions": [broken', INDEX, "x")
    check_true("壞掉的 JSON 應拋 DraftError", False)
except OA.DraftError:
    check_true("壞掉的 JSON 應拋 DraftError", True)

print()
print("=" * 70)
print("測試 8：短碼衝突與 id 衝突")
print("=" * 70)
clash = json.loads(good_draft())
clash["dimensions"][1]["label_en"] = "Anticipation"      # 同名 → 短碼會撞
clash["dimensions"][1]["id"] = "anticipation"            # id 也撞
d4, r4 = OA.parse_draft(json.dumps(clash), INDEX, "x")
shorts = [d[F.DIM_SHORT] for d in d4[F.DIMENSIONS]]
ids = [d[F.DIM_ID] for d in d4[F.DIMENSIONS]]
check("短碼不重複", len(set(shorts)), 2)
check("維度 id 不重複", len(set(ids)), 2)
check("衝突處理後仍通過驗證", F.validate(d4), [])
check("保留字 UNC 不會被生成", F.UNASSIGNED_SHORT in shorts, False)
check("_short_code 避開保留字",
      OA._short_code("Unclassified", set()) == F.UNASSIGNED_SHORT, False)
check("_slug 處理奇怪輸入", OA._slug("  Hello, World! 2024 "), "hello_world_2024")
check("_slug 數字開頭補前綴", OA._slug("2024 thing"), "dimension_2024_thing")

print()
print("=" * 70)
print("測試 9：無極性框架")
print("=" * 70)
nopol = json.loads(good_draft())
nopol["has_polarity"] = False
d5, r5 = OA.parse_draft(json.dumps(nopol), INDEX, "x")
check("極性關閉", d5[F.POLARITY][F.POLARITY_ENABLED], False)
check("極性值為空", d5[F.POLARITY][F.POLARITY_VALUES], [])
check("指標改為單組", list(d5[F.DIMENSIONS][0][F.DIM_INDICATORS]), ["all"])
check_true("維度不帶極性標籤", F.POLARITY_LABELS not in d5[F.DIMENSIONS][0])
fw5 = F.load_dict(d5)
check("無極性時編碼即短碼", fw5.codes, ["ANT", "REF"])

print()
print("=" * 70)
print("測試 10：人工核可")
print("=" * 70)
try:
    OA.apply_decisions(draft, {"anticipation": {"decision": "approve"}}, reviewer="")
    check_true("沒有核可者姓名應拒絕", False)
except OA.DraftError:
    check_true("沒有核可者姓名應拒絕", True)

try:
    OA.apply_decisions(draft, {}, reviewer="Hung Chi")
    check_true("完全沒做決定時應拒絕（沉默不等於同意）", False)
except OA.DraftError as e:
    check_true("完全沒做決定時應拒絕（沉默不等於同意）", True, str(e)[:50])

blanks = OA.blank_decisions(draft)
check("預設全部待決", [v["decision"] for v in blanks.values()], [None, None])

fw = OA.apply_decisions(draft, {
    "anticipation": {"decision": OA.DECISION_APPROVE, "note": "與原文一致"},
    "reflexivity": {"decision": OA.DECISION_EDIT,
                    "label_zh": "反身性",
                    "definition_zh": "檢視自身預設、價值與知識限度的能力。",
                    "note": "中文譯名改用學界慣例"},
}, reviewer="Hung Chi", framework_id="ri_from_openalex")
check("核可後為 Framework 物件", isinstance(fw, F.Framework), True)
check("framework_id 已改寫", fw.id, "ri_from_openalex")
check("出處升級為已核可", fw.provenance, F.PROV_OPENALEX_APPROVED)
check("兩個維度都保留", len(fw.dimensions), 2)
check("編輯已生效", fw.label("reflexivity", "zh"), "反身性")
check("未編輯的維度不動", fw.label("anticipation", "zh"), "預期")

pd = OA.provenance_of(fw)
check("核可紀錄兩筆", len(pd[OA.PD_APPROVALS]), 2)
check("核可者已記錄", pd["approved_by"], "Hung Chi")
edit_rec = [a for a in pd[OA.PD_APPROVALS] if a["decision"] == "edit"][0]
check("修改前後都留存", edit_rec["changes"]["label_zh"],
      {"from": "反思性", "to": "反身性"})
check("檢索到的文獻全部留在出處裡", len(pd[OA.PD_WORKS]), 6)

fw2 = OA.apply_decisions(draft, {
    "anticipation": {"decision": OA.DECISION_APPROVE},
    "reflexivity": {"decision": OA.DECISION_REJECT, "note": "與本研究問題無關"},
}, reviewer="Hung Chi")
check("退回的維度不進入框架", fw2.dimensions, ["anticipation"])
check("退回理由有記錄", OA.provenance_of(fw2)[OA.PD_REJECTED][0]["reason"],
      "與本研究問題無關")

fw3 = OA.apply_decisions(draft, {
    "anticipation": {"decision": OA.DECISION_APPROVE},
}, reviewer="Hung Chi")
check("未做決定者視同退回", fw3.dimensions, ["anticipation"])
check("未做決定的理由寫明",
      OA.provenance_of(fw3)[OA.PD_REJECTED][0]["reason"], "no decision recorded")

check_true("核可不會改到原草稿",
           len(draft[F.DIMENSIONS]) == 2 and
           draft[F.DIMENSIONS][1][F.DIM_LABEL]["zh"] == "反思性")

print()
print("=" * 70)
print("測試 11：存檔往返與整條管線接得起來")
print("=" * 70)
with tempfile.TemporaryDirectory() as d:
    import os
    p = F.save(fw, os.path.join(d, "ri_from_openalex.json"))
    back = F.load_file(p)
    check("往返後 ID 相同", back.id, fw.id)
    check("往返後出處保留", OA.provenance_of(back)["approved_by"], "Hung Chi")
    check("往返後文獻保留", len(back.literature("anticipation")), 2)
    check("列得出來", [a[0] for a in F.list_available(d)], ["ri_from_openalex"])

F.set_active(fw)
import tacit_schema as S
import tacit_i18n as I
check("schema 跟著換維度", S.DIMENSIONS, ["anticipation", "reflexivity"])
check("schema 跟著換編碼", S.CODES, ["ANT-P", "ANT-N", "REF-P", "REF-N"])
check("i18n 讀得到新標籤", I.dim("reflexivity", "zh"), "反身性")
check("極性標籤來自框架", fw.polarity_label("anticipation", "P", "en"), "Foresight")
F.reset()

print()
print("=" * 70)
print("測試 12：方法章節數字與參考文獻")
print("=" * 70)
facts = OA.methods_facts(fw)
check("檢索文獻數", facts["n_works_retrieved"], 6)
# 兩個維度共引 W1、各自另引 W3／W4 → 去重後 3 篇（W1 同時支撐兩個維度）
check("實際引用文獻數（去重）", facts["n_works_cited"], 3)
check("維度數", facts["n_dimensions"], 2)
check("原案通過數", facts["n_approved_unchanged"], 1)
check("修改後通過數", facts["n_approved_edited"], 1)
check("退回數", facts["n_rejected"], 0)
check("草擬模型有記錄", facts["drafting_model"], "test-model")

for lang in ("en", "zh"):
    s = OA.methods_sentence(facts, lang)
    check_true(f"{lang} 方法句含檢索數", "6" in s)
    check_true(f"{lang} 方法句含核可者", "Hung Chi" in s)
    check_true(f"{lang} 方法句夠完整", len(s) > 150, f"{len(s)} 字")
check_true("英文方法句說明了幻覺防護",
           "rejected programmatically" in OA.methods_sentence(facts, "en"))
check_true("中文方法句說明了幻覺防護",
           "一律拒絕" in OA.methods_sentence(facts, "zh"))

bib = OA.bibliography(fw)
check("參考文獻筆數（同一篇不重複列出）", len(bib), 3)
check("grounding 排在前面", bib[0]["role"], F.ROLE_GROUNDING)
check_true("引文字串完整", bib[0]["citation"].startswith("Stilgoe, J."))
check_true("保留 DOI 可追溯", any(b["doi"] for b in bib))
w1_row = [b for b in bib if b["openalex_id"] == "W1"][0]
check("奠基文獻標明它支撐哪些維度", w1_row["dimensions"],
      ["anticipation", "reflexivity"])
check("同時為 grounding 與 supporting 時取較強者", w1_row["role"],
      F.ROLE_GROUNDING)

print()
print("=" * 70)
print(f"結果：{'全部通過 ✅' if not FAIL else '失敗項目 ' + str(FAIL)}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
