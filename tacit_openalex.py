"""
tacit_openalex.py — 由文獻建構理論編碼框架
=========================================

問題
----
本軟體的編碼框架是可插拔的（見 tacit_framework），但使用者要從哪裡取得一個
新框架的維度與定義？靠語言模型「回想」某個理論有哪幾個維度，是不可接受的：
模型會產出看似合理、實則杜撰的維度與引文，而編碼框架是整份研究的效度根基。

做法：檢索 → 草擬 → 人工核可
-----------------------------
1. **檢索**（本模組，無語言模型）
   以 OpenAlex 檢索該理論的文獻，取「高被引的奠基文獻」與「近年文獻」兩批。
   這一步完全可重現：查詢式、篩選條件、時間戳與回傳的文獻清單都會記錄下來。

2. **草擬**（本模組，呼叫語言模型）
   把檢索到的**摘要原文**交給模型，要求它只依據眼前這批文獻歸納維度。
   解析時強制檢查：模型引用的每一篇文獻都必須存在於檢索集合中，
   任何憑空出現的文獻 ID 一律拒絕（`parse_draft` 會列為 error 而非警告）。
   每個維度至少要有一篇 grounding 文獻，否則該維度不成立。

3. **人工核可**（本模組）
   研究者逐維度核可、修改或退回。未經核可的維度不會進入最終框架。
   核可者、時間、原始草稿、修改內容、退回理由全部記錄在框架檔裡，
   可直接寫進論文方法章節，回答「這個框架怎麼來的」。

模型在這裡的角色是**摘要與草擬**，不是知識來源。文獻是知識來源，
研究者是決定者。這個分工是本模組唯一的設計主張。

OpenAlex API 現況（2026-08 查證）
--------------------------------
* 自 **2026-02-13** 起所有 API 呼叫都需要金鑰，免費申請：
  https://openalex.org/settings/api
* 免費金鑰每日 **100,000 credits**；未帶金鑰每日僅 **100 credits**（僅供試用）。
* 額度以 credits 計：list 端點（如 /works?filter=...）每次 **10 credits**，
  singleton 端點（如 /works/W123）每次 **1 credit**。另有每秒 100 次上限。
* 「polite pool」與 `mailto` 參數已廢除。
* 官方 docs 倉庫中的 rate-limits 文件尚未同步更新（仍寫著「不需要金鑰」），
  以 2026-01-14 的公告為準。
* 底層資料仍為 CC0，可整份下載，不需金鑰。

摘要以 inverted index 形式提供，本模組會還原為原文（`reconstruct_abstract`）。
部分文獻沒有摘要（出版社未授權），這類文獻仍可作為引文，但不進入證據文本。
"""

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import tacit_framework as F

API_BASE = "https://api.openalex.org"
API_KEY_URL = "https://openalex.org/settings/api"
CACHE_DIR = "openalex_cache"

CREDITS_LIST = 10
CREDITS_SINGLETON = 1
DAILY_CREDITS_WITH_KEY = 100_000
DAILY_CREDITS_NO_KEY = 100

USER_AGENT = "TACIT (qualitative coding tool; research use)"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# 出處紀錄的鍵（寫在框架檔的 provenance_detail 之下）
PROV_DETAIL = "provenance_detail"
PD_SOURCE = "source"
PD_THEORY_QUERY = "theory_query"
PD_RETRIEVED_AT = "retrieved_at"
PD_RETRIEVAL = "retrieval"          # 檢索式與筆數，供重現
PD_WORKS = "works"                  # 檢索集合（全部，含未採用者）
PD_MODEL = "drafting_model"
PD_APPROVALS = "approvals"          # 逐維度的核可紀錄
PD_REJECTED = "rejected_dimensions"  # 被研究者退回的草稿維度與理由

DECISION_APPROVE = "approve"
DECISION_EDIT = "edit"
DECISION_REJECT = "reject"
DECISIONS = (DECISION_APPROVE, DECISION_EDIT, DECISION_REJECT)


class OpenAlexError(RuntimeError):
    """檢索層的任何失敗。"""


class QuotaError(OpenAlexError):
    """每日 credits 用盡或超過每秒上限（HTTP 409 / 429）。"""


class OfflineMiss(OpenAlexError):
    """離線模式下快取沒有這一筆。"""


class DraftError(ValueError):
    """草稿無法解析，或違反了防護規則。"""


# =====================================================================
# 1. HTTP 客戶端（帶磁碟快取；快取讓離線重現與測試成為可能）
# =====================================================================
class Client:
    """
    薄薄一層 OpenAlex 客戶端。刻意不用 requests，避免多一個相依套件。

    快取的用意不只是省額度：其他研究者要能在**沒有金鑰、
    沒有網路**的情況下重跑一次框架建構流程，否則「可重現」只是空話。
    快取鍵不含金鑰，所以快取可以連同專案一起流通。
    """

    def __init__(self, api_key=None, cache_dir=CACHE_DIR, timeout=30,
                 offline=False, min_interval=0.15):
        self.api_key = (api_key or os.environ.get("OPENALEX_API_KEY") or "").strip()
        self.cache_dir = cache_dir
        self.timeout = timeout
        self.offline = offline
        self.min_interval = min_interval   # 每秒 100 次上限，實務上遠低於此
        self.credits_used = 0
        self.credits_remaining = None
        self.calls = 0
        self.cache_hits = 0
        self._last_call = 0.0
        if cache_dir:
            os.makedirs(cache_dir, exist_ok=True)

    # --- 額度 ---
    @property
    def has_key(self):
        return bool(self.api_key) and not self.key_looks_like_email

    @property
    def key_looks_like_email(self):
        """
        使用者把 email 當成金鑰填進來的機率不低。

        原因是舊的「polite pool」機制要求提供 email（mailto 參數），
        2026-02-13 起已廢除，但多數函式庫仍保留 email 設定欄位，
        送出去只是被忽略。於是使用者會以為自己有身分、實際上在用
        無金鑰的每日 100 credits，而且因為額度耗盡回的是 409/429，
        腳本若吞掉例外，看起來就只像「今天沒有資料」——靜默失敗。
        """
        return bool(_EMAIL_RE.match(self.api_key or ""))

    @property
    def daily_budget(self):
        return DAILY_CREDITS_WITH_KEY if self.has_key else DAILY_CREDITS_NO_KEY

    def budget_note(self, lang="en"):
        """給介面顯示：目前是哪一種額度、大約還能做幾次檢索。"""
        searches = self.daily_budget // CREDITS_LIST
        if self.key_looks_like_email:
            if lang == "zh":
                return (f"這看起來是 email，不是 API 金鑰。OpenAlex 舊的 "
                        f"polite pool（mailto）機制已於 2026-02-13 廢除，"
                        f"填 email 不再有任何作用，目前等同未設金鑰："
                        f"每日 {DAILY_CREDITS_NO_KEY} credits。"
                        f"請至 {API_KEY_URL} 免費申請金鑰。")
            return (f"That looks like an email address, not an API key. "
                    f"OpenAlex retired the polite pool (the mailto parameter) "
                    f"on 13 Feb 2026, so an email has no effect. You are "
                    f"currently treated as having no key: "
                    f"{DAILY_CREDITS_NO_KEY} credits per day. "
                    f"Get a free key at {API_KEY_URL}")
        if lang == "zh":
            if self.has_key:
                return (f"已設定 API 金鑰：每日 {self.daily_budget:,} credits，"
                        f"約可進行 {searches:,} 次檢索。")
            return (f"未設定 API 金鑰：每日僅 {self.daily_budget} credits，"
                    f"約可進行 {searches} 次檢索（僅供試用）。"
                    f"免費申請：{API_KEY_URL}")
        if self.has_key:
            return (f"API key set: {self.daily_budget:,} credits per day "
                    f"(about {searches:,} searches).")
        return (f"No API key: only {self.daily_budget} credits per day "
                f"(about {searches} searches, for testing only). "
                f"Get a free key at {API_KEY_URL}")

    # --- 快取 ---
    def cache_key_url(self, path, params=None):
        """快取鍵所依據的正規化 URL（不含金鑰，因此快取可以隨專案流通）。"""
        params = dict(params or {})
        params.pop("api_key", None)
        qs = urllib.parse.urlencode(sorted(params.items()), doseq=True)
        return f"{API_BASE}/{path.lstrip('/')}" + (f"?{qs}" if qs else "")

    def prime_cache(self, path, params, payload):
        """手動寫入一筆快取。用於隨軟體附上示範用的檢索結果。"""
        self._cache_write(self.cache_key_url(path, params), payload)

    def _cache_path(self, url_no_key):
        h = hashlib.sha256(url_no_key.encode("utf-8")).hexdigest()[:24]
        return os.path.join(self.cache_dir, f"{h}.json")

    def _cache_read(self, url_no_key):
        if not self.cache_dir:
            return None
        p = self._cache_path(url_no_key)
        if not os.path.exists(p):
            return None
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None   # 壞掉的快取視同沒有，不讓它中斷流程

    def _cache_write(self, url_no_key, payload):
        if not self.cache_dir:
            return
        try:
            with open(self._cache_path(url_no_key), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False)
        except OSError:
            pass

    # --- 請求 ---
    def _fetch(self, url):
        """
        實際的網路呼叫，抽成獨立方法只有一個理由：測試要能覆寫它。
        覆寫這一層而不是覆寫 get()，才會連參數組裝、快取、額度計算
        一起測到。回傳 (raw_text, headers_dict)。
        """
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return resp.read().decode("utf-8"), dict(resp.headers)

    def get(self, path, params=None, cost=CREDITS_LIST, use_cache=True):
        params = dict(params or {})
        params.pop("api_key", None)
        url_no_key = self.cache_key_url(path, params)

        if use_cache:
            cached = self._cache_read(url_no_key)
            if cached is not None:
                self.cache_hits += 1
                return cached
        if self.offline:
            raise OfflineMiss(f"offline mode and not cached: {url_no_key}")

        # 金鑰只加在實際送出的 URL 上，不進快取鍵——快取才能隨專案流通。
        # 用 has_key 而非 api_key：若使用者填的是 email，不要把它送出去。
        if self.has_key:
            params["api_key"] = self.api_key
            qs = urllib.parse.urlencode(sorted(params.items()), doseq=True)
            url = f"{API_BASE}/{path.lstrip('/')}" + (f"?{qs}" if qs else "")
        else:
            url = url_no_key

        gap = time.time() - self._last_call
        if gap < self.min_interval:
            time.sleep(self.min_interval - gap)

        try:
            raw, headers = self._fetch(url)
            rem = headers.get("X-RateLimit-Remaining")
            used = headers.get("X-RateLimit-Credits-Used")
        except urllib.error.HTTPError as e:
            # 公告寫 409、文件寫 429，兩者都可能出現，一律當成額度問題。
            if e.code in (409, 429):
                raise QuotaError(self._quota_message(e.code)) from e
            if e.code in (401, 403):
                raise OpenAlexError(
                    f"HTTP {e.code}: API key rejected. Check the key at "
                    f"{API_KEY_URL}") from e
            raise OpenAlexError(f"HTTP {e.code} from OpenAlex: {e.reason}") from e
        except urllib.error.URLError as e:
            raise OpenAlexError(f"cannot reach OpenAlex: {e.reason}") from e

        self._last_call = time.time()
        self.calls += 1
        self.credits_used += int(used) if (used or "").isdigit() else cost
        if (rem or "").isdigit():
            self.credits_remaining = int(rem)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as e:
            raise OpenAlexError("OpenAlex returned a non-JSON response") from e
        if use_cache:
            self._cache_write(url_no_key, payload)
        return payload

    def _quota_message(self, code):
        if self.has_key:
            return (f"HTTP {code}: daily credit limit reached "
                    f"({DAILY_CREDITS_WITH_KEY:,}/day) or more than 100 requests "
                    f"per second. Credits reset at midnight UTC.")
        return (f"HTTP {code}: without an API key you only get "
                f"{DAILY_CREDITS_NO_KEY} credits per day "
                f"(about {DAILY_CREDITS_NO_KEY // CREDITS_LIST} searches). "
                f"Get a free key at {API_KEY_URL}")

    # --- 端點 ---
    def works(self, search=None, filters=None, per_page=25, sort=None, page=1,
              select=None):
        params = {"per-page": max(1, min(int(per_page), 200)), "page": page}
        if search:
            params["search"] = search
        if filters:
            params["filter"] = ",".join(f"{k}:{v}" for k, v in filters.items())
        if sort:
            params["sort"] = sort
        if select:
            params["select"] = ",".join(select)
        return self.get("works", params, cost=CREDITS_LIST)

    def topics(self, search, per_page=10):
        return self.get("topics", {"search": search, "per-page": per_page},
                        cost=CREDITS_LIST)

    def rate_limit(self):
        """查詢目前額度。需要金鑰；沒有金鑰時直接回報，不浪費一次呼叫。"""
        if not self.has_key:
            return {"error": "no api key", "daily_budget": DAILY_CREDITS_NO_KEY}
        return self.get("rate-limit", {}, cost=CREDITS_SINGLETON, use_cache=False)


# =====================================================================
# 2. 文獻正規化
# =====================================================================
def reconstruct_abstract(inverted_index):
    """
    OpenAlex 以 {詞: [位置, ...]} 的倒排索引提供摘要，需還原為原文。
    位置可能不連續（原文有被移除的詞），以位置排序而非填空，避免產生空洞。
    """
    if not isinstance(inverted_index, dict) or not inverted_index:
        return ""
    slots = []
    for word, positions in inverted_index.items():
        for p in positions or []:
            if isinstance(p, int):
                slots.append((p, word))
    if not slots:
        return ""
    slots.sort()
    return " ".join(w for _, w in slots)


def _surname_initials(display_name):
    """'Jack Stilgoe' → 'Stilgoe, J.'；中日韓姓名不含空格，原樣保留。"""
    name = (display_name or "").strip()
    if not name:
        return ""
    if " " not in name:
        return name
    parts = name.split()
    surname = parts[-1]
    initials = " ".join(f"{p[0]}." for p in parts[:-1] if p)
    return f"{surname}, {initials}".strip()


def normalise_work(raw):
    """把 OpenAlex 的 work 物件收斂成本模組使用的扁平結構（鍵一律 ASCII）。"""
    raw = raw or {}
    oa_id = (raw.get("id") or "").rsplit("/", 1)[-1]
    authorships = raw.get("authorships") or []
    authors = [(a.get("author") or {}).get("display_name", "")
               for a in authorships]
    authors = [a for a in authors if a]

    loc = raw.get("primary_location") or {}
    src = loc.get("source") or {}
    biblio = raw.get("biblio") or {}
    oa = raw.get("open_access") or {}

    abstract = reconstruct_abstract(raw.get("abstract_inverted_index"))
    return {
        "openalex_id": oa_id,
        "doi": (raw.get("doi") or "").replace("https://doi.org/", "") or None,
        "title": raw.get("display_name") or raw.get("title") or "",
        "year": raw.get("publication_year"),
        "authors": authors,
        "venue": src.get("display_name") or "",
        "volume": biblio.get("volume"),
        "issue": biblio.get("issue"),
        "pages": "-".join(x for x in (biblio.get("first_page"),
                                      biblio.get("last_page")) if x) or None,
        "cited_by_count": raw.get("cited_by_count") or 0,
        "type": raw.get("type") or "",
        "abstract": abstract,
        "has_abstract": bool(abstract),
        "oa_url": oa.get("oa_url"),
        "is_oa": bool(oa.get("is_oa")),
    }


def apa_citation(work):
    """組成近似 APA 的引文字串。缺欄位就省略，不要編造。"""
    w = work or {}
    authors = w.get("authors") or []
    if not authors:
        who = "[No author listed]"
    elif len(authors) == 1:
        who = _surname_initials(authors[0])
    elif len(authors) <= 3:
        who = ", ".join(_surname_initials(a) for a in authors[:-1])
        who += f", & {_surname_initials(authors[-1])}"
    else:
        who = f"{_surname_initials(authors[0])}, et al."
    year = w.get("year") or "n.d."
    out = f"{who} ({year}). {(w.get('title') or '').rstrip('.')}."
    if w.get("venue"):
        out += f" {w['venue']}"
        if w.get("volume"):
            out += f", {w['volume']}"
            if w.get("issue"):
                out += f"({w['issue']})"
        if w.get("pages"):
            out += f", {w['pages']}"
        out += "."
    if w.get("doi"):
        out += f" https://doi.org/{w['doi']}"
    return out


# =====================================================================
# 3. 檢索策略
# =====================================================================
def suggest_topics(client, query, n=8):
    """
    先讓使用者確認「你說的是哪個理論」。理論名稱常有歧義
    （responsible innovation / responsible research and innovation），
    直接拿字串去撈文獻會混進不相干的領域。
    """
    data = client.topics(query, per_page=n)
    out = []
    for t in data.get("results") or []:
        out.append({
            "id": (t.get("id") or "").rsplit("/", 1)[-1],
            "name": t.get("display_name") or "",
            "description": t.get("description") or "",
            "works_count": t.get("works_count") or 0,
            "field": ((t.get("field") or {}).get("display_name") or ""),
        })
    return out


_QUERY_STOP = {"the", "a", "an", "of", "and", "or", "in", "on", "for", "to"}


def phrase_filter(query):
    """
    把使用者輸入變成 title_and_abstract.search 的值——整串當成**片語**。

    為什麼不用 `search=` 參數：那個參數會連**全文**一起比對，而且會做詞幹
    還原、去停用詞，多個詞之間預設不是 AND。一旦再加上
    sort=cited_by_count:desc，關聯度排序被覆蓋，浮上來的就是「全文某處剛好
    出現過其中一個詞、而且被引數極高」的論文——放射性碳定年校正曲線、
    鋰電池綜述、DARPA 無人車全部跑出來，正是這樣來的。

    title_and_abstract.search 只比對標題與摘要，是**硬性條件**而非排序訊號，
    因此再依被引次數排序才安全。加上引號則要求詞相鄰，精準度再高一階。
    """
    q = " ".join((query or "").split())
    if not q:
        return ""
    if '"' in q or any(op in q.split() for op in ("AND", "OR", "NOT")):
        return q          # 使用者自己寫了查詢語法，原樣尊重
    return f'"{q}"'


def and_filter(query):
    """
    片語找不到東西時的退路：把各詞以 AND 相連，仍限定在標題與摘要。

    「responsible innovation anticipation」不會有論文標題剛好是這一整串，
    但「responsible innovation」AND「anticipation」同時出現在摘要裡的，
    正是使用者要找的那一批。
    """
    words = [w for w in (query or "").split() if w.lower() not in _QUERY_STOP]
    return " AND ".join(f'"{w}"' for w in words) if words else ""


def relevance_of(works, query):
    """
    檢索結果有多少比例真的提到查詢詞——用來當「檢索是否可信」的體檢指標。

    這是事後的健全性檢查，不是過濾器：低分不代表個別文獻沒用，
    而是代表這一次檢索式本身有問題，應該讓使用者知道並重下條件。
    """
    terms = [w.lower() for w in (query or "").split()
             if w.lower() not in _QUERY_STOP and len(w) > 2]
    if not works or not terms:
        return 1.0
    hit = 0
    for w in works:
        blob = f"{w.get('title', '')} {w.get('abstract', '')}".lower()
        if any(t in blob for t in terms):
            hit += 1
    return round(hit / len(works), 3)


def retrieve_corpus(client, query, n_seminal=15, n_recent=10, recent_years=6,
                    topic_id=None, min_citations=0, require_abstract=False,
                    min_hits=25):
    """
    兩批檢索：
      * 奠基文獻——依被引次數排序。理論的維度定義來自這裡。
      * 近年文獻——確認該理論的當代用法與延伸，避免框架停留在原始論文。
    兩批合併去重，並回傳完整的檢索紀錄（查詢式、篩選、筆數、時間）。

    回傳 (works, retrieval_log)
    """
    filters_common = {}
    if topic_id:
        filters_common["topics.id"] = topic_id
    if min_citations:
        filters_common["cited_by_count"] = f">{int(min_citations)}"

    log = {"query": query, "topic_id": topic_id,
           "retrieved_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "passes": []}
    seen, works = set(), []

    # 先確定要用哪一種查詢式：整串片語太窄時退回 AND 連接。
    # 兩次嘗試都寫進紀錄，方法章節才能說明檢索式是怎麼定下來的。
    q_phrase, q_and = phrase_filter(query), and_filter(query)
    search_expr, probe = q_phrase, None
    if q_phrase:
        f_probe = dict(filters_common)
        f_probe["title_and_abstract.search"] = q_phrase
        probe = (client.works(filters=f_probe, per_page=1).get("meta")
                 or {}).get("count", 0)
        log["phrase_query"] = q_phrase
        log["phrase_hits"] = probe
        if probe is not None and probe < min_hits and q_and and q_and != q_phrase:
            search_expr = q_and
            log["fallback_query"] = q_and
            log["fallback_reason"] = (
                f"phrase matched only {probe} works (< {min_hits}); "
                f"widened to AND of the individual terms")
    log["search_expr"] = search_expr

    def _run(label, filters, sort, per_page):
        f = dict(filters or {})
        if search_expr:
            f["title_and_abstract.search"] = search_expr
        data = client.works(filters=f or None, sort=sort, per_page=per_page)
        got = data.get("results") or []
        added = 0
        for raw in got:
            w = normalise_work(raw)
            if not w["openalex_id"] or w["openalex_id"] in seen:
                continue
            if require_abstract and not w["has_abstract"]:
                continue
            seen.add(w["openalex_id"])
            w["retrieval_pass"] = label
            works.append(w)
            added += 1
        log["passes"].append({
            "pass": label, "sort": sort, "filters": f,
            "requested": per_page,
            "total_available": (data.get("meta") or {}).get("count"),
            "returned": len(got), "added_after_dedup": added,
        })

    f_sem = dict(filters_common)
    f_sem.setdefault("type", "article")
    _run("seminal", f_sem, "cited_by_count:desc", n_seminal)

    if n_recent:
        this_year = datetime.now(timezone.utc).year
        f_rec = dict(filters_common)
        f_rec["type"] = "article"
        f_rec["publication_year"] = f">{this_year - recent_years}"
        _run("recent", f_rec, "cited_by_count:desc", n_recent)

    log["total_works"] = len(works)
    log["with_abstract"] = sum(1 for w in works if w["has_abstract"])
    log["relevance"] = relevance_of(works, query)
    if log["relevance"] < 0.6:
        log["relevance_warning"] = (
            "Fewer than 60% of the retrieved works mention the query terms in "
            "their title or abstract. Treat this retrieval as unreliable: "
            "narrow the query, or pick a topic to filter on.")
    return works, log


# =====================================================================
# 4. 證據打包（不含語言模型）
# =====================================================================
def evidence_index(works):
    """給每篇文獻一個穩定的短代號 W1、W2…，模型只准引用這些代號。"""
    return {f"W{i}": w for i, w in enumerate(works, 1)}


def build_evidence(index, max_abstract_chars=1100):
    """把文獻整理成模型看得懂、又能被逐條追溯的文字。沒有摘要的文獻仍列出。"""
    blocks = []
    for ref, w in index.items():
        head = (f"[{ref}] {apa_citation(w)}\n"
                f"      cited_by={w['cited_by_count']}  "
                f"pass={w.get('retrieval_pass', '?')}")
        if w["has_abstract"]:
            ab = w["abstract"]
            if len(ab) > max_abstract_chars:
                ab = ab[:max_abstract_chars].rsplit(" ", 1)[0] + " …"
            blocks.append(f"{head}\n      ABSTRACT: {ab}")
        else:
            blocks.append(f"{head}\n      ABSTRACT: (not available)")
    return "\n\n".join(blocks)


# =====================================================================
# 5. 草擬（呼叫語言模型）
# =====================================================================
DRAFT_PROMPT = """\
You are helping a qualitative researcher build a THEORY-DRIVEN CODING FRAMEWORK.

The researcher wants to code interview transcripts using the theoretical
construct named below. Your task is to propose the dimensions of that
construct, based STRICTLY AND ONLY on the literature provided.

THEORETICAL CONSTRUCT: {theory}

=== LITERATURE (this is your ONLY source) ===
{evidence}
=== END OF LITERATURE ===

HARD RULES
1. Every claim you make must be traceable to the abstracts above. If the
   literature provided does not establish a dimension clearly, DO NOT invent it.
2. You may ONLY cite the reference tags that appear above ({ref_list}).
   Never write a reference tag that is not in that list. Never cite an author,
   year or title that does not appear above.
3. Each dimension needs at least one "grounding" reference: a work that
   actually defines or establishes that dimension, not one that merely uses it.
4. If the literature is insufficient to define a proper framework, say so in
   "coverage_warning" and propose only the dimensions you can actually ground.
5. Propose between 2 and 8 dimensions. Prefer fewer, well-grounded dimensions
   over many speculative ones.

POLARITY
{polarity_instruction}

OUTPUT
Return ONE JSON object and nothing else:

{{
  "framework_name_en": "short name of the framework in English",
  "framework_name_zh": "short name in Traditional Chinese",
  "citation": "the single work most standardly cited for this framework, in APA",
  "description_en": "2-3 sentences on what this framework is for",
  "description_zh": "same in Traditional Chinese",
  "has_polarity": true or false,
  "coverage_warning": "any concern about whether the retrieved literature is
                       adequate; empty string if none",
  "dimensions": [
    {{
      "id": "lowercase_ascii_identifier",
      "label_en": "Dimension name",
      "label_zh": "維度名稱（繁體中文）",
      "definition_en": "2-4 sentences defining the dimension, as the literature
                        defines it. Write it so a coder can apply it.",
      "definition_zh": "same in Traditional Chinese",
      "indicators_positive_en": ["observable marker in an interview", "..."],
      "indicators_positive_zh": ["...", "..."],
      "indicators_negative_en": ["...", "..."],
      "indicators_negative_zh": ["...", "..."],
      "polarity_label_positive_en": "what the positive pole is called",
      "polarity_label_positive_zh": "...",
      "polarity_label_negative_en": "what the negative pole is called",
      "polarity_label_negative_zh": "...",
      "grounding_refs": ["W1"],
      "supporting_refs": ["W4"],
      "grounding_note": "one sentence: what exactly W1 contributes to this
                         dimension"
    }}
  ]
}}

If has_polarity is false, still provide indicators under
"indicators_positive_*" (treat them as general indicators) and leave the
negative and polarity-label fields as empty lists or empty strings.
"""

POLARITY_ON = """\
This framework SHOULD use a two-pole model: each dimension can be expressed in
an affirming way or an undermining way, and the coder marks which. Give both
poles a name that is specific to the dimension (not just "positive"/"negative").
Only choose this if the literature actually supports a bidirectional reading.
"""

POLARITY_OFF = """\
This framework should NOT use a polarity model. Dimensions are simply present
or absent. Set "has_polarity" to false.
"""

POLARITY_AUTO = """\
Decide for yourself whether a two-pole model fits. Use one only if the
literature actually treats each dimension as something that can be enacted well
or poorly. If the dimensions are simply thematic categories, set
"has_polarity" to false. Do not add polarity just because it seems richer.
"""


def draft_prompt(theory, index, has_polarity=None, extra=""):
    pol = {True: POLARITY_ON, False: POLARITY_OFF, None: POLARITY_AUTO}[has_polarity]
    prompt = DRAFT_PROMPT.format(
        theory=theory,
        evidence=build_evidence(index),
        ref_list=", ".join(index.keys()),
        polarity_instruction=pol,
    )
    return prompt + (f"\n\nADDITIONAL INSTRUCTION FROM THE RESEARCHER:\n{extra}\n"
                     if extra.strip() else "")


def draft_framework(theory, index, llm_fn, has_polarity=None, extra="",
                    model_name=""):
    """
    llm_fn: callable(prompt: str) -> str（回傳模型原始輸出）
    抽成參數是為了讓本模組不綁定任何特定廠商，也讓測試不需要網路。
    回傳 (draft_dict, report)
    """
    raw = llm_fn(draft_prompt(theory, index, has_polarity, extra))
    return parse_draft(raw, index, theory, model_name=model_name)


_JSON_RE = re.compile(r"\{.*\}", re.S)


def _unbalanced(s):
    """
    從第一個 { 起算，括號到結尾都沒有合上——輸出在 JSON 結束前被切斷。

    不能只看有沒有 }：被截斷的草稿裡面通常已經有合上的內層物件，
    貪婪比對會抓到一段合法開頭、非法結尾的文字，錯誤訊息就變成誤導人的
    「not valid JSON」，而真正的原因是輸出上限。
    """
    depth, in_str, esc = 0, False, False
    for ch in s:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return False
    return True


def _slug(text, fallback="dimension"):
    s = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    s = re.sub(r"_+", "_", s)
    if not s or not s[0].isalpha():
        s = f"{fallback}_{s}".strip("_")
    return s[:40] if len(s) >= 2 else f"{fallback}_x"


def _short_code(label, taken):
    """由標籤生成 2-6 碼大寫短碼，避開保留字與已用過的碼。"""
    words = re.findall(r"[A-Za-z][A-Za-z0-9]*", label or "")
    cands = []
    if len(words) >= 2:
        cands.append("".join(w[0] for w in words[:6]).upper())
    if words:
        cands.append(words[0][:3].upper())
        cands.append(words[0][:4].upper())
    cands.append("DIM")
    for c in cands:
        c = re.sub(r"[^A-Z0-9]", "", c)[:6]
        if len(c) >= 2 and c not in taken and c != F.UNASSIGNED_SHORT:
            return c
    base = re.sub(r"[^A-Z0-9]", "", (cands[0] or "DIM"))[:4] or "DIM"
    for i in range(1, 100):
        c = f"{base[:max(1, 5 - len(str(i)))]}{i}"
        if len(c) >= 2 and c not in taken and c != F.UNASSIGNED_SHORT:
            return c
    raise DraftError("cannot generate a unique short code")


def parse_draft(raw_text, index, theory, model_name=""):
    """
    解析模型輸出並套用防護規則。

    回傳 (draft_dict, report)，report 含：
        errors    — 讓維度被丟棄或整份草稿失效的問題
        warnings  — 值得研究者注意，但不阻擋
        dropped   — 被丟棄的維度與原因

    最關鍵的一條：模型引用的每一個 ref 都必須在 index 裡。這是唯一能防止
    「憑空生出一篇看似合理的文獻」的機制，因此不可降級為警告。
    """
    errors, warnings, dropped = [], [], []
    # 失敗要分清楚是哪一種，因為解法不同。三種情況都回同一句
    # 「no JSON object found」的話，使用者看不出該換模型、調高輸出上限、還是重試。
    text = raw_text or ""
    if not text.strip():
        raise DraftError("the model returned no text. Try again, or choose "
                         "another model.")
    m = _JSON_RE.search(text)
    try:
        if not m:
            raise json.JSONDecodeError("no closing brace", text, len(text))
        data = json.loads(m.group(0))
    except json.JSONDecodeError as e:
        head = re.sub(r"\s+", " ", text.strip())[:160]
        if "{" in text and _unbalanced(text[text.index("{"):]):
            raise DraftError(
                "the model's output was cut off before the JSON was complete. "
                "A framework draft is long; choose a model with a larger output "
                "limit, or ask for fewer dimensions in the additional instruction. "
                f"Output began: “{head}”") from e
        if "{" not in text:
            raise DraftError("the model answered in prose instead of JSON. "
                             f"Output began: “{head}”") from e
        raise DraftError(f"model output is not valid JSON: {e}. "
                         f"Output began: “{head}”") from e

    valid_refs = set(index)
    has_pol = bool(data.get("has_polarity", True))

    dims, seen_id, seen_short = [], set(), set()
    for i, d in enumerate(data.get("dimensions") or []):
        if not isinstance(d, dict):
            dropped.append({"index": i, "reason": "not an object"})
            continue
        label_en = (d.get("label_en") or "").strip()
        if not label_en:
            dropped.append({"index": i, "reason": "missing label_en"})
            continue

        ground = [r for r in (d.get("grounding_refs") or []) if isinstance(r, str)]
        support = [r for r in (d.get("supporting_refs") or []) if isinstance(r, str)]
        bad = [r for r in ground + support if r not in valid_refs]
        if bad:
            errors.append(f"dimension {label_en!r} cites references that were "
                          f"never retrieved: {', '.join(sorted(set(bad)))}")
            ground = [r for r in ground if r in valid_refs]
            support = [r for r in support if r in valid_refs]
        if not ground:
            dropped.append({"index": i, "label": label_en,
                            "reason": "no valid grounding reference"})
            continue

        did = _slug(d.get("id") or label_en)
        if did in seen_id or did == F.UNASSIGNED:
            did = f"{did}_{i}"[:40]
        short = _short_code(label_en, seen_short)
        seen_id.add(did)
        seen_short.add(short)

        lit = []
        for ref in ground:
            w = index[ref]
            lit.append(_lit_from_work(w, F.ROLE_GROUNDING,
                                      (d.get("grounding_note") or "").strip()))
        for ref in support:
            if ref in ground:
                continue
            lit.append(_lit_from_work(index[ref], F.ROLE_SUPPORTING, ""))

        def _list(key):
            v = d.get(key) or []
            return [str(x).strip() for x in v if str(x).strip()] \
                if isinstance(v, list) else []

        if has_pol:
            indicators = {
                "P": {"en": _list("indicators_positive_en"),
                      "zh": _list("indicators_positive_zh")},
                "N": {"en": _list("indicators_negative_en"),
                      "zh": _list("indicators_negative_zh")},
            }
            pol_labels = {
                "P": {"en": (d.get("polarity_label_positive_en") or "Positive"),
                      "zh": (d.get("polarity_label_positive_zh") or "正向")},
                "N": {"en": (d.get("polarity_label_negative_en") or "Negative"),
                      "zh": (d.get("polarity_label_negative_zh") or "負向")},
            }
        else:
            indicators = {"all": {"en": _list("indicators_positive_en"),
                                  "zh": _list("indicators_positive_zh")}}
            pol_labels = {}

        if not (d.get("definition_en") or "").strip():
            warnings.append(f"dimension {label_en!r} has no English definition")

        dim = {
            F.DIM_ID: did, F.DIM_SHORT: short,
            F.DIM_LABEL: {"en": label_en,
                          "zh": (d.get("label_zh") or label_en).strip()},
            F.DIM_DEFINITION: {"en": (d.get("definition_en") or "").strip(),
                               "zh": (d.get("definition_zh") or "").strip()},
            F.DIM_INDICATORS: indicators,
            F.DIM_LITERATURE: lit,
        }
        if pol_labels:
            dim[F.POLARITY_LABELS] = pol_labels
        dims.append(dim)

    if not dims:
        raise DraftError("no dimension survived validation; "
                         + ("; ".join(errors) if errors else "the draft was empty"))
    if len(dims) < 2:
        warnings.append("only one dimension was grounded; a coding framework "
                        "with a single dimension is rarely usable")

    fid = _slug(data.get("framework_name_en") or theory, "framework")
    draft = {
        F.FRAMEWORK_ID: fid,
        F.VERSION: "1.0",
        F.PROVENANCE: F.PROV_OPENALEX_DRAFT,
        F.NAME: {"en": (data.get("framework_name_en") or theory).strip(),
                 "zh": (data.get("framework_name_zh")
                        or data.get("framework_name_en") or theory).strip()},
        F.CITATION: (data.get("citation") or "").strip(),
        F.DESCRIPTION: {"en": (data.get("description_en") or "").strip(),
                        "zh": (data.get("description_zh") or "").strip()},
        F.POLARITY: {
            F.POLARITY_ENABLED: has_pol,
            F.POLARITY_VALUES: ["P", "N"] if has_pol else [],
            F.POLARITY_LABELS: {"P": {"en": "Affirming", "zh": "彰顯"},
                                "N": {"en": "Undermining", "zh": "削弱"}},
            F.POLARITY_CITATION: "",
        },
        F.DIMENSIONS: dims,
        PROV_DETAIL: {
            PD_SOURCE: "openalex",
            PD_THEORY_QUERY: theory,
            PD_MODEL: model_name,
            PD_RETRIEVED_AT: datetime.now(timezone.utc).isoformat(timespec="seconds"),
            PD_WORKS: [dict(w) for w in index.values()],
            PD_APPROVALS: [],
            PD_REJECTED: [],
        },
    }

    problems = F.validate(draft)
    if problems:
        errors.extend(problems)

    cw = (data.get("coverage_warning") or "").strip()
    if cw:
        warnings.append(f"model's own coverage warning: {cw}")
    unused = sorted(valid_refs - {r for d in dims
                                  for r in _refs_of(d, index)})
    if unused:
        warnings.append(f"{len(unused)} of {len(valid_refs)} retrieved works "
                        f"were not used by any dimension")

    report = {"errors": errors, "warnings": warnings, "dropped": dropped,
              "n_dimensions": len(dims), "has_polarity": has_pol,
              "n_works": len(index), "usable": not problems}
    return draft, report


def _lit_from_work(w, role, note):
    return {F.LIT_CITATION: apa_citation(w), F.LIT_ROLE: role,
            F.LIT_YEAR: w.get("year"), F.LIT_INCLUDED: True, F.LIT_NOTE: note,
            F.LIT_OPENALEX_ID: w.get("openalex_id"), F.LIT_DOI: w.get("doi"),
            F.LIT_CITED_BY: w.get("cited_by_count")}


def _refs_of(dim, index):
    ids = {l.get(F.LIT_OPENALEX_ID) for l in dim.get(F.DIM_LITERATURE) or []}
    return {ref for ref, w in index.items() if w.get("openalex_id") in ids}


# =====================================================================
# 6. 人工核可
# =====================================================================
def review_rows(draft, lang="en"):
    """草稿攤平成逐維度的表格，供介面顯示與研究者判斷。"""
    rows = []
    for d in draft.get(F.DIMENSIONS) or []:
        lit = d.get(F.DIM_LITERATURE) or []
        ground = [l for l in lit if l.get(F.LIT_ROLE) == F.ROLE_GROUNDING]
        rows.append({
            "dimension_id": d[F.DIM_ID],
            "short": d[F.DIM_SHORT],
            "label": (d.get(F.DIM_LABEL) or {}).get(lang, ""),
            "definition": (d.get(F.DIM_DEFINITION) or {}).get(lang, ""),
            "n_grounding": len(ground),
            "n_supporting": len(lit) - len(ground),
            "grounding_citations": [l.get(F.LIT_CITATION, "") for l in ground],
            "grounding_note": next((l.get(F.LIT_NOTE) for l in ground
                                    if l.get(F.LIT_NOTE)), ""),
        })
    return rows


def blank_decisions(draft):
    """預設全部待決。刻意不預設為核可——核可必須是主動的動作。"""
    return {d[F.DIM_ID]: {"decision": None, "note": ""}
            for d in draft.get(F.DIMENSIONS) or []}


def apply_decisions(draft, decisions, reviewer, framework_id=None, note=""):
    """
    套用研究者的逐維度決定，產出可用的 Framework。

    decisions: {dimension_id: {
        "decision": "approve" | "edit" | "reject",
        "note": "退回理由或修改說明",
        # decision == "edit" 時可覆寫下列任一欄位：
        "label_en", "label_zh", "definition_en", "definition_zh", "short",
    }}

    未做決定的維度視同退回：沉默不等於同意。
    """
    if not reviewer or not str(reviewer).strip():
        raise DraftError("a reviewer name is required; approval must be attributable")

    data = json.loads(json.dumps(draft))   # 深拷貝，不動到原草稿
    kept, approvals, rejected = [], [], []
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    for d in data.get(F.DIMENSIONS) or []:
        did = d[F.DIM_ID]
        dec = dict(decisions.get(did) or {})
        choice = dec.get("decision")
        if choice not in DECISIONS:
            rejected.append({"dimension_id": did, "reason": "no decision recorded",
                             "label": (d.get(F.DIM_LABEL) or {}).get("en", "")})
            continue
        if choice == DECISION_REJECT:
            rejected.append({"dimension_id": did,
                             "label": (d.get(F.DIM_LABEL) or {}).get("en", ""),
                             "reason": dec.get("note", "") or "rejected by the researcher"})
            continue

        changes = {}
        if choice == DECISION_EDIT:
            for key, (holder, sub) in {
                "label_en": (F.DIM_LABEL, "en"), "label_zh": (F.DIM_LABEL, "zh"),
                "definition_en": (F.DIM_DEFINITION, "en"),
                "definition_zh": (F.DIM_DEFINITION, "zh"),
            }.items():
                new = dec.get(key)
                if new is not None and str(new).strip() != d.get(holder, {}).get(sub, ""):
                    changes[key] = {"from": d.get(holder, {}).get(sub, ""),
                                    "to": str(new).strip()}
                    d.setdefault(holder, {})[sub] = str(new).strip()
            new_short = (dec.get("short") or "").strip().upper()
            if new_short and new_short != d[F.DIM_SHORT]:
                changes["short"] = {"from": d[F.DIM_SHORT], "to": new_short}
                d[F.DIM_SHORT] = new_short

        kept.append(d)
        approvals.append({"dimension_id": did, "decision": choice,
                          "reviewer": str(reviewer).strip(), "at": now,
                          "note": dec.get("note", ""), "changes": changes})

    if not kept:
        raise DraftError("no dimension was approved; a framework needs at least one")

    data[F.DIMENSIONS] = kept
    data[F.PROVENANCE] = F.PROV_OPENALEX_APPROVED
    if framework_id:
        data[F.FRAMEWORK_ID] = _slug(framework_id, "framework")
    pd = data.setdefault(PROV_DETAIL, {})
    pd[PD_APPROVALS] = approvals
    pd[PD_REJECTED] = rejected
    pd["approved_by"] = str(reviewer).strip()
    pd["approved_at"] = now
    pd["approval_note"] = note

    problems = F.validate(data)
    if problems:
        raise DraftError("approved framework failed validation: " + "; ".join(problems))
    return F.load_dict(data)


# =====================================================================
# 7. 出處報告（給方法章節用）
# =====================================================================
def provenance_of(fw):
    data = fw.data if isinstance(fw, F.Framework) else (fw or {})
    return data.get(PROV_DETAIL) or {}


def methods_facts(fw):
    """把框架的建構過程整理成可寫進方法章節的數字。"""
    data = fw.data if isinstance(fw, F.Framework) else (fw or {})
    pd = provenance_of(data)
    dims = data.get(F.DIMENSIONS) or []
    approvals = pd.get(PD_APPROVALS) or []
    lit_ids = {l.get(F.LIT_OPENALEX_ID)
               for d in dims for l in (d.get(F.DIM_LITERATURE) or [])
               if l.get(F.LIT_OPENALEX_ID)}
    return {
        "framework_id": data.get(F.FRAMEWORK_ID, ""),
        "framework_name": (data.get(F.NAME) or {}).get("en", ""),
        "provenance": data.get(F.PROVENANCE, ""),
        "theory_query": pd.get(PD_THEORY_QUERY, ""),
        "retrieved_at": pd.get(PD_RETRIEVED_AT, ""),
        "drafting_model": pd.get(PD_MODEL, ""),
        "n_works_retrieved": len(pd.get(PD_WORKS) or []),
        "n_works_cited": len(lit_ids),
        "n_dimensions": len(dims),
        "n_approved_unchanged": sum(1 for a in approvals
                                    if a["decision"] == DECISION_APPROVE),
        "n_approved_edited": sum(1 for a in approvals
                                 if a["decision"] == DECISION_EDIT),
        "n_rejected": len(pd.get(PD_REJECTED) or []),
        "approved_by": pd.get("approved_by", ""),
        "approved_at": pd.get("approved_at", ""),
        "has_polarity": bool((data.get(F.POLARITY) or {}).get(F.POLARITY_ENABLED)),
    }


def methods_sentence(facts, lang="en"):
    """
    產出可貼進方法章節的句子。數字全部來自 methods_facts，不另行推論。
    """
    f = facts
    if lang == "zh":
        s = (f"本研究的編碼框架以「{f['theory_query']}」為題，"
             f"於 {f['retrieved_at'][:10]} 檢索 OpenAlex，取得 "
             f"{f['n_works_retrieved']} 篇文獻；"
             f"由語言模型（{f['drafting_model'] or '未指定'}）依據上述文獻摘要草擬維度，"
             f"模型僅得引用該檢索集合內的文獻，任何集合外的引用一律拒絕。")
        s += (f"草稿由 {f['approved_by']} 於 {f['approved_at'][:10]} 逐維度審定："
              f"{f['n_approved_unchanged']} 個維度原案通過、"
              f"{f['n_approved_edited']} 個修改後通過、"
              f"{f['n_rejected']} 個退回。")
        s += (f"最終框架含 {f['n_dimensions']} 個維度，"
              f"引用 {f['n_works_cited']} 篇文獻作為定義依據"
              + ("，並採用雙極性編碼模型。" if f["has_polarity"] else "。"))
        return s
    s = (f"The coding framework was built from literature retrieved from "
         f"OpenAlex on {f['retrieved_at'][:10]} using the query "
         f"“{f['theory_query']}”, which returned "
         f"{f['n_works_retrieved']} works. A language model "
         f"({f['drafting_model'] or 'unspecified'}) drafted candidate dimensions "
         f"from the abstracts of those works only; citations outside the "
         f"retrieved set were rejected programmatically. ")
    s += (f"{f['approved_by']} reviewed every drafted dimension on "
          f"{f['approved_at'][:10]}: {f['n_approved_unchanged']} were approved "
          f"as drafted, {f['n_approved_edited']} were approved after editing, "
          f"and {f['n_rejected']} were rejected. ")
    s += (f"The final framework contains {f['n_dimensions']} dimensions grounded "
          f"in {f['n_works_cited']} works"
          + (", coded with a two-pole model." if f["has_polarity"] else "."))
    return s


def bibliography(fw):
    """
    框架實際引用的文獻清單，依角色與年份排序，可貼進參考文獻。

    一篇文獻可能同時支撐多個維度（奠基性論文通常如此），
    清單中只列一次，但 dimensions 欄位會列出它支撐的所有維度；
    role 取最強的角色（grounding 優於 supporting）。
    """
    data = fw.data if isinstance(fw, F.Framework) else (fw or {})
    by_key, order = {}, []
    for d in data.get(F.DIMENSIONS) or []:
        for l in d.get(F.DIM_LITERATURE) or []:
            key = l.get(F.LIT_OPENALEX_ID) or l.get(F.LIT_CITATION)
            if key not in by_key:
                by_key[key] = {"citation": l.get(F.LIT_CITATION, ""),
                               "role": l.get(F.LIT_ROLE, ""),
                               "year": l.get(F.LIT_YEAR),
                               "doi": l.get(F.LIT_DOI),
                               "openalex_id": l.get(F.LIT_OPENALEX_ID),
                               "cited_by_count": l.get(F.LIT_CITED_BY),
                               "dimensions": []}
                order.append(key)
            entry = by_key[key]
            if d[F.DIM_ID] not in entry["dimensions"]:
                entry["dimensions"].append(d[F.DIM_ID])
            if l.get(F.LIT_ROLE) == F.ROLE_GROUNDING:
                entry["role"] = F.ROLE_GROUNDING
    out = [by_key[k] for k in order]
    out.sort(key=lambda r: (r["role"] != F.ROLE_GROUNDING, -(r["year"] or 0)))
    return out
