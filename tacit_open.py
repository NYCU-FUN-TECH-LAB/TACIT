"""
tacit_open.py — 開放編碼與會累積的碼簿
======================================

【這支模組要解決什麼】

框架驅動的編碼只做一件事：先有框架，再拿框架去編碼。那涵蓋了主題分析的兩
個取向——編碼信度型（結構化碼簿＋多編碼者＋κ）與碼簿型（template /
framework analysis）——但沒有涵蓋「碼簿本身要從資料裡長出來」的那一半，
也就是開放編碼與紮根理論。

缺的不是主題歸納。`tacit_themes` 的一階→二階→聚合早就在跑，而且二階主題
本來就是歸納出來的。缺的是**開放編碼那一段**，而它缺的具體東西只有一個：

    **碼要會累積。**

如果每一個窗口各自編碼、彼此不知道對方用過什麼碼，一份兩萬字的逐字稿會
產出兩百個互不相同的標籤，沒有任何一個重複出現。那不是編碼，那是逐段下
標題——沒有碼簿，就沒有頻次、沒有共現、沒有信度，什麼都算不了。

所以這支模組做的事是：逐窗編碼時**把已經建立的碼帶進提示詞**，讓模型優先
沿用而不是另起爐灶；沿用與新增都記錄下來；跑完得到一份帶頻次與代表引文的
碼簿。

【為什麼這條路跟現有架構是合的】

    開放編碼產生碼簿 → 碼簿本身就是一個框架 → 存成框架檔
    → 交叉表、共現、信度、主題歸納、匯出全部原封不動地能用

這一步（`codebook_to_framework`）是整個設計的關節。它讓「從資料長出理論」
與「拿理論去編碼」變成同一套機器的兩個方向，而不是兩套工具。也因為如此，
工具名字裡的 Theory-Anchored 仍然成立：錨定的框架可以來自文獻，也可以來自
你自己的資料——紮根理論長出來的東西本來就是理論。

【方法論的界線，必須守住】

Braun 與 Clarke 的三分法裡，這支模組支援的是**開放編碼到碼簿生成**這一段。
它**不是** reflexive TA 的實作，也不宣稱是：反思型 TA 的核心主張是主題由
研究者的詮釋生成而非從資料浮現，並明確拒絕編碼者間信度那一整套；一個由
模型提議碼的工具，在那個立場看來正是它要反對的東西。

同樣地，紮根理論的理論抽樣與持續比較是**跨資料蒐集**的研究者活動，不是一
次批次處理。這支模組給的是開放編碼的機械部分與飽和度的描述性曲線，不是
紮根理論方法本身。

誠實的說法是「支援開放編碼與碼簿生成，詮釋權留在研究者手上」。
不是「支援反思型主題分析」。這兩句話在方法論上差很多。
"""
import json
import re
from datetime import datetime

import tacit_coding as CH
import tacit_framework as F
import tacit_schema as S

# --- 碼簿欄位 ---
CODEBOOK_ID = "codebook_id"
LANGUAGE = "language"
CODES = "codes"
CREATED = "created"
PROVENANCE = "provenance"

CODE_ID = "code_id"
CODE_LABEL = "label"
CODE_DEFINITION = "definition"
CODE_EXAMPLES = "examples"
CODE_COUNT = "count"
CODE_FIRST_SEEN = "first_seen_chunk"
CODE_MERGED_FROM = "merged_from"
CODE_HISTORY = "history"

# --- 開放編碼的紀錄欄位（刻意與 tacit_schema 的欄位分開）---
#
# 開放編碼期間還沒有框架，所以這些紀錄不能走 S.migrate_record——它會把
# 「不在作用中框架維度裡」的碼全部丟掉，而開放編碼的碼依定義就不在任何
# 框架裡。等碼簿定案、轉成框架之後，再用 to_records() 轉成標準格式。
OPEN_SEGMENTS = "open_segments"
OPEN_CODES = "open_codes"

# 一個窗口最多把幾個既有碼放進提示詞。碼簿長到幾百個時全部塞進去會吃掉
# 整個上下文，而且模型對過長的清單本來就讀不完。依出現頻次取前 N 個，
# 因為高頻碼才是真正在用的碼。
MAX_CODES_IN_PROMPT = 60


def new_codebook(language=S.DEFAULT_ANALYSIS_LANG, codebook_id=None):
    return {
        CODEBOOK_ID: codebook_id or f"cb_{datetime.now():%Y%m%d_%H%M%S}",
        LANGUAGE: language,
        CREATED: datetime.now().isoformat(timespec="seconds"),
        CODES: [],
        PROVENANCE: {},
    }


def _norm(s):
    """比對用的正規化：去掉空白與標點，只留實際的字。"""
    return re.sub(r"[\s\W_]+", "", str(s or ""), flags=re.UNICODE).lower()


_LABEL_COUNT_PREFIX = re.compile(r"^\s*\[\s*\d+\s*x\s*\]\s*", re.I)
# 提示詞的輸出格式裡寫著「if this code is NEW, define it…」，小模型會把那個
# 字眼抄進標籤：實測 llama3:8b 跑 12 份聽證會逐字稿，出現了
# "[NEW CODE] Concerns about AI oversight"（22 次）以及一個**整個就叫
# "NEW CODE" 的碼**（19 次）。
#
# 兩種寫法都要接：帶括號的（[NEW CODE]、(new)）與帶冒號的（NEW CODE:、new:）。
# 括號的字元類別涵蓋全角，但裡面只認英文 new——提示詞是英文的，中文的
# 【新碼】沒有實際觀察到，沒看過的形式不猜。
#
# **不接沒有括號也沒有冒號的裸 "New "**——"New codes of conduct for AI" 與
# "Newly proposed federal guidance" 都是正當的標籤，砍掉開頭就改壞了它們。
_LABEL_NEW_PREFIX = re.compile(
    r"^\s*(?:[\[(（【]\s*new(?:\s+code)?\s*[\])）】]"
    r"|new(?:\s+code)?\s*[:：])\s*", re.I)
# 清乾淨之後只剩下裝飾本身的，不是碼。
_LABEL_ONLY_DECORATION = re.compile(r"^\s*new(\s+code)?s?\s*$", re.I)
_LABEL_DEF_SEP = re.compile(r"\s+(?:—|–|--)\s+")


def clean_label(label):
    """
    把模型從提示詞照抄回來的裝飾拿掉，回傳 (標籤, 夾帶的定義)。

    碼簿在提示詞裡長這樣：`  [9x] Guardrails for AI — 定義文字`。小模型沿用時
    常常整行照抄，於是 "Guardrails for AI"、"[9x] Guardrails for AI — …"、
    "[18x] Guardrails for AI — …" 被當成三個不同的碼，計數一變又多一個。
    實測（llama3:8b，24 份國會聽證會）647 個碼裡有 95 個帶這種裝飾。

    這不是替模型猜意思：`[Nx]` 與 ` — ` 是**這個工具自己**加上去的顯示格式，
    拿掉它們只是還原模型照抄之前的標籤。標籤本身的用字一律不動。
    """
    s = str(label or "")
    s = _LABEL_COUNT_PREFIX.sub("", s)
    s = _LABEL_NEW_PREFIX.sub("", s)
    parts = _LABEL_DEF_SEP.split(s, maxsplit=1)
    head = re.sub(r"\s+", " ", parts[0]).strip(" .:：")
    tail = parts[1].strip() if len(parts) > 1 else ""
    if _LABEL_ONLY_DECORATION.match(head):
        # 標籤整個就是提示詞的字眼，沒有任何內容。回空字串讓 add_code 丟掉它，
        # 不要猜它想說什麼——猜出來的碼會帶著一個沒人寫過的意思。
        return "", tail
    return head, tail


def find_code(cb, label):
    """依標籤找既有的碼（正規化後比對）。找不到回 None。"""
    key = _norm(label)
    if not key:
        return None
    for c in cb[CODES]:
        if _norm(c[CODE_LABEL]) == key:
            return c
    return None


def get_code(cb, code_id):
    return next((c for c in cb[CODES] if c[CODE_ID] == code_id), None)


def _next_code_id(cb):
    """c001、c002…。要符合框架的維度 id 規則 ^[a-z][a-z0-9_]{1,39}$。"""
    n = len(cb[CODES]) + 1
    used = {c[CODE_ID] for c in cb[CODES]}
    while f"c{n:03d}" in used:          # 合併過的碼會留下空號，往後找
        n += 1
    return f"c{n:03d}"


def add_code(cb, label, definition="", chunk=0):
    """新增一個碼。標籤重複時回傳既有的那一個，不會建出兩個同名的碼。"""
    label = str(label or "").strip()
    if not label:
        return None
    existing = find_code(cb, label)
    if existing:
        return existing
    code = {
        CODE_ID: _next_code_id(cb),
        CODE_LABEL: label,
        CODE_DEFINITION: str(definition or "").strip(),
        CODE_EXAMPLES: [],
        CODE_COUNT: 0,
        CODE_FIRST_SEEN: chunk,
        CODE_MERGED_FROM: [],
        CODE_HISTORY: [],
    }
    cb[CODES].append(code)
    return code


def codebook_prompt_block(cb, lang="en", max_codes=MAX_CODES_IN_PROMPT):
    """
    把既有的碼渲染成提示詞的一段。

    這一段就是「碼會累積」這件事真正發生的地方。沒有它，每個窗口都是從零
    開始，產出的是標題不是碼。

    指示的措辭要拿捏：**偏向沿用，但不到強迫**。逼太緊會把真正新的東西硬塞
    進舊碼裡，那等於用一個更隱蔽的方式弄丟資料——比漏編更難察覺，因為畫面
    上看起來碼簿很穩定。
    """
    if not cb[CODES]:
        return ("No codes have been created yet. You are starting the codebook. "
                "Create codes that name what the passage is doing, in the "
                "language of the transcript.")
    # 只列最常用的碼。
    #
    # 試過另一種選法，量測結果比較差，記在這裡免得有人再試一次：
    # 推論是「剛建出來、只出現一次的碼永遠排在名單外，下一段文字看不到它，
    # 於是只好再建一個同義的新碼，單次碼被鎖死成單次碼」，所以改成留四分之一
    # 的位置給最近建立的碼。同一批 24 份聽證會逐字稿、同一顆 llama3:8b：
    #
    #                       只看次數    加上最近建立的
    #   碼數                  352          423
    #   只出現一次            319          369
    #   合併後                323          389
    #   編碼時間             125 分       199 分
    #
    # 每一項都更差。合理的解釋是反過來的：把一串只出現一次的標籤放進提示詞，
    # 等於告訴模型「這個碼簿就是一串一次性標籤」，它就照做；提示詞也變長了。
    # 碼簿在小模型上長不出來，原因不在這個選法。
    top = sorted(cb[CODES], key=lambda c: -c[CODE_COUNT])[:max_codes]
    lines = [
        f"EXISTING CODEBOOK ({len(cb[CODES])} codes so far, "
        f"{len(top)} most used shown).",
        "Reuse an existing code whenever the passage is an instance of it — "
        "reuse is what makes a codebook, and a code that occurs once is not "
        "yet a code. Copy the label EXACTLY as written below when you reuse.",
        "Create a new code when the passage is genuinely about something the "
        "existing codes do not name. Do not force a passage into a nearby code "
        "to keep the list short; a forced fit is harder to detect later than a "
        "duplicate.",
        "",
    ]
    for c in top:
        d = f" — {c[CODE_DEFINITION]}" if c[CODE_DEFINITION] else ""
        lines.append(f"  [{c[CODE_COUNT]}x] {c[CODE_LABEL]}{d}")
    return "\n".join(lines)


def build_open_prompt(cb, analysis_lang, sample="", corpus_term="interview transcript"):
    """
    開放編碼的系統提示詞。

    與框架驅動的提示詞是兩份不同的東西，不共用：那一份的主體是維度定義與
    排除條件，這一份沒有維度，主體是碼簿與開放編碼的規則。硬要共用會讓兩
    邊都長出一堆 if。
    """
    lines = [
        "You are an experienced qualitative researcher performing OPEN CODING "
        f"of a {corpus_term}. There is no pre-existing theoretical framework: "
        "the codes come from the data.",
        "",
        S.analysis_language_instruction(analysis_lang, sample),
        "",
        "=" * 68,
        "1. THE CODEBOOK",
        "=" * 68,
        codebook_prompt_block(cb),
        "",
        "=" * 68,
        "2. CODING RULES",
        "=" * 68,
        "1. Output a FLAT LIST of coded segments.",
        "2. A segment is a contiguous verbatim excerpt expressing one coherent "
        "idea, typically 1-4 sentences.",
        f"3. COVERAGE: work through the {corpus_term} from beginning to end and "
        "code EVERY passage that says something. This is exhaustive coding, "
        "not a selection of highlights. Do not stop early.",
        "4. A code NAMES WHAT THE PASSAGE IS DOING, at a level of abstraction "
        "just above the words used. \"Nurses are overloaded\" is a code; "
        "\"the respondent talks about nurses\" is a topic label, and "
        "\"interesting point\" is nothing at all.",
        "5. Codes are short — a few words. Put the elaboration in the "
        "definition field, not in the label.",
        "6. ABSENCE IS NOT EVIDENCE. Code what the passage says, never what it "
        "fails to say. If the speaker states that something is missing in "
        "their world (\"we have no review process\") that IS codeable; your own "
        "observation that the passage does not show something is not.",
        f"7. Every quote and full_text must be copied VERBATIM from the "
        f"{corpus_term}. quote must be a substring of full_text.",
        "8. JSON: escape all quotes inside strings; never emit literal newline "
        "characters inside JSON string values.",
        "",
        "=" * 68,
        "3. OUTPUT FORMAT — valid JSON only, no text before or after:",
        "=" * 68,
        "{",
        f'  "{S.RESPONDENT}": "the person speaking, as named in the {corpus_term}",',
        f'  "{OPEN_SEGMENTS}": [',
        "    {",
        f'      "{S.TITLE}": "a short label for this particular passage",',
        f'      "{S.QUOTE}": "the most representative 1-2 sentences, verbatim",',
        f'      "{S.FULL_TEXT}": "the fuller passage giving context, verbatim",',
        f'      "{OPEN_CODES}": [',
        "        {",
        f'          "{CODE_LABEL}": "an existing code copied exactly, or a new one",',
        f'          "{CODE_DEFINITION}": "if this code is NEW, define it in one '
        'sentence; if reusing, leave empty",',
        f'          "{S.RATIONALE}": "under 20 words: why this code applies here"',
        "        }",
        "      ]",
        "    },",
        "    { second coded segment, same shape },",
        "    { third coded segment, same shape }",
        "  ]",
        "}",
        "",
        f"The three segment objects show the SHAPE only. Return as many as the "
        f"{corpus_term} warrants — commonly far more than three.",
    ]
    return "\n".join(lines)


def absorb(cb, raw, chunk=0, respondent=""):
    """
    把模型回傳的一個窗口吸收進碼簿，並回傳正規化後的段落清單。

    回傳 (segments, stats)。stats 裡的 reused / created 是**飽和度的原始
    資料**：新碼在第幾個窗口還在出現，是紮根理論談飽和時唯一能拿出來的
    描述性證據。
    """
    segs, reused, created = [], 0, 0
    for i, rs in enumerate(raw.get(OPEN_SEGMENTS) or raw.get(S.SEGMENTS) or []):
        if not isinstance(rs, dict):
            continue
        quote = str(rs.get(S.QUOTE) or "").strip()
        codes = []
        for rc in (rs.get(OPEN_CODES) or rs.get(S.CODES_F) or []):
            if not isinstance(rc, dict):
                continue
            label, carried_def = clean_label(rc.get(CODE_LABEL) or rc.get(S.DIMENSION))
            if not label:
                continue
            if carried_def and not rc.get(CODE_DEFINITION):
                rc = {**rc, CODE_DEFINITION: carried_def}
            existing = find_code(cb, label)
            if existing is None:
                code = add_code(cb, label, rc.get(CODE_DEFINITION), chunk)
                created += 1
            else:
                code = existing
                reused += 1
                # 沿用時模型若補了定義，只在原本沒有定義時採用——
                # 已經寫好的定義不該被後面某一次的即興說法覆蓋掉
                if not code[CODE_DEFINITION] and rc.get(CODE_DEFINITION):
                    code[CODE_DEFINITION] = str(rc[CODE_DEFINITION]).strip()
            if code is None:
                continue
            code[CODE_COUNT] += 1
            if quote and len(code[CODE_EXAMPLES]) < 5:
                code[CODE_EXAMPLES].append(
                    {S.QUOTE: quote, S.RESPONDENT: respondent})
            codes.append({CODE_ID: code[CODE_ID], CODE_LABEL: code[CODE_LABEL],
                          S.RATIONALE: str(rc.get(S.RATIONALE) or "").strip()})
        if not codes:
            continue
        segs.append({
            S.SEGMENT_ID: f"S{i + 1:03d}",
            S.TITLE: str(rs.get(S.TITLE) or "").strip(),
            S.QUOTE: quote,
            S.FULL_TEXT: str(rs.get(S.FULL_TEXT) or quote).strip(),
            OPEN_CODES: codes,
        })
    return segs, {"reused": reused, "created": created, "chunk": chunk}


def merge_open_segments(groups):
    """
    合併各窗口的開放編碼段落，去掉重疊區產生的重複。

    規則與 tacit_coding.merge_segments 相同（引文包含即視為同一段，碼取
    聯集），但**不經過任何框架相關的函式**。

    這一點是刻意的：`S.codes_of()` 會把碼丟給
    `F.active().code_of()`，而開放編碼進行中作用中的框架根本不含這些碼——
    RI 還開著的話，"c001" 會被算成 "c001-None" 這種東西。合併邏輯若依賴
    那個結果，行為就取決於「使用者上一次開的是哪個框架」。開放編碼這一段
    必須完全不依賴框架，因為框架是它的**產物**，不是它的前提。
    """
    kept = []
    for seg in [s for g in groups or [] for s in (g or [])]:
        q = _norm(seg.get(S.QUOTE))
        if not q:
            continue
        dup = next((k for k in kept
                    if q in _norm(k.get(S.QUOTE)) or _norm(k.get(S.QUOTE)) in q),
                   None)
        if dup is None:
            kept.append(dict(seg))
            continue
        have = {c[CODE_ID] for c in dup.get(OPEN_CODES) or []}
        for c in seg.get(OPEN_CODES) or []:
            if c[CODE_ID] not in have:
                dup.setdefault(OPEN_CODES, []).append(c)
                have.add(c[CODE_ID])
        if len(str(seg.get(S.FULL_TEXT) or "")) > len(str(dup.get(S.FULL_TEXT) or "")):
            dup[S.FULL_TEXT] = seg[S.FULL_TEXT]
        if len(str(seg.get(S.QUOTE) or "")) > len(str(dup.get(S.QUOTE) or "")):
            dup[S.QUOTE] = seg[S.QUOTE]
    for n, seg in enumerate(kept, 1):
        seg[S.SEGMENT_ID] = f"S{n:03d}"
    return kept


def open_code_transcript(transcript, code_one, cb, window=CH.DEFAULT_WINDOW_CHARS,
                         overlap=CH.DEFAULT_OVERLAP_CHARS, on_progress=None):
    """
    對一份逐字稿做開放編碼。碼簿 cb 會**就地被修改**——那正是重點：
    下一份逐字稿會帶著這一份建立的碼繼續跑。

    code_one(chunk_text, index, total) 回傳模型的原始 JSON（已 parse 成
    dict）。呼叫模型留在外面，這支函式才測得動。
    """
    chunks = CH.split_transcript(transcript, window, overlap)
    all_segs, per_chunk, errors = [], [], []
    respondent_votes = []
    for n, (_, text) in enumerate(chunks):
        if on_progress:
            on_progress(n, len(chunks))
        try:
            raw = code_one(text, n, len(chunks))
        except Exception as e:                                   # noqa: BLE001
            errors.append({"chunk": n, "error": f"{type(e).__name__}: {e}"})
            continue
        if not raw:
            errors.append({"chunk": n, "error": "empty"})
            continue
        who = str(raw.get(S.RESPONDENT) or "").strip()
        respondent_votes.append(who)
        segs, st = absorb(cb, raw, chunk=n, respondent=who)
        all_segs.append(segs)
        per_chunk.append(st)

    merged = merge_open_segments(all_segs)
    rec = {
        S.RESPONDENT: CH.merge_respondent(respondent_votes),
        S.DESCRIPTORS: S.blank_descriptors(),
        S.SUMMARY: "",
        OPEN_SEGMENTS: merged,
        S.META: {"mode": "open_coding",
                 "codebook_id": cb[CODEBOOK_ID],
                 "chunking": {"window_chars": window, "overlap_chars": overlap,
                              "n_chunks": len(chunks),
                              "n_ok": len(per_chunk)},
                 "codes_per_chunk": per_chunk},
    }
    if errors:
        rec[S.META]["chunk_errors"] = errors
    return rec


# =====================================================================
# 飽和度
# =====================================================================
def saturation_curve(records):
    """
    每個窗口新建了幾個碼、沿用了幾個。

    這是紮根理論談「飽和」時唯一拿得出來的**描述性**證據：新碼的出現速度
    有沒有趨緩。**它不是飽和的判定。** 飽和是研究者對「再收資料還會不會
    有新東西」的判斷，牽涉理論抽樣與研究問題，不是一條曲線能決定的；把
    曲線當判定是把方法論問題偷換成統計問題。

    回傳 [{"n": 累計窗口序, "created": .., "reused": .., "cumulative": ..}]
    """
    out, total = [], 0
    n = 0
    for rec in records:
        for st in ((rec.get(S.META) or {}).get("codes_per_chunk") or []):
            n += 1
            total += st.get("created", 0)
            out.append({"n": n, "created": st.get("created", 0),
                        "reused": st.get("reused", 0), "cumulative": total})
    return out


# =====================================================================
# 合併近義碼
# =====================================================================
def _bigrams(s):
    s = _norm(s)
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)}


def similar_pairs(cb, threshold=0.5, limit=40):
    """
    找出標籤相近的碼，供研究者判斷要不要合併。**只建議，不自動合併。**

    開放編碼一定會產生近義碼（「時間壓力」「工時太長」「排班壓力」），那
    不是缺陷，是開放編碼的正常產物；哪些該合併是分析判斷，不是字串相似度
    能決定的。工具的工作是把候選挑出來讓人看，不是替人決定。

    相似度用 Dice 而不是 Jaccard。碼的標籤很短，中文尤其短，Jaccard 的
    分母把兩邊的獨有字元都算進去，短字串一差一兩個字就掉到門檻以下——
    「時間壓力」對「時間的壓力」只差一個「的」，Jaccard 是 0.40，照 0.5
    的門檻會被判成不相關，而那正是這個功能最該抓到的一種。Dice 對同一組
    字元給 0.57，抓得到；而完全不相干的兩個標籤兩種算法都是 0。

    limit=None 就不截斷。**量測的時候一律用 None。** 預設的 40 是畫面上
    的顯示上限，不是數量：一份 352 個碼的碼簿有 972 對候選，用預設值
    只會拿到 40。把被截斷的筆數當成測量值，「全部接受建議後剩下幾個碼」
    也會跟著錯。
    """
    rows = []
    codes = cb[CODES]
    for i, a in enumerate(codes):
        ga = _bigrams(a[CODE_LABEL])
        for b in codes[i + 1:]:
            gb = _bigrams(b[CODE_LABEL])
            if not (ga or gb):
                continue
            j = 2 * len(ga & gb) / (len(ga) + len(gb))
            if j >= threshold:
                rows.append({"a": a[CODE_ID], "a_label": a[CODE_LABEL],
                             "a_count": a[CODE_COUNT],
                             "b": b[CODE_ID], "b_label": b[CODE_LABEL],
                             "b_count": b[CODE_COUNT],
                             "similarity": round(j, 3)})
    rows.sort(key=lambda r: -r["similarity"])
    return rows if limit is None else rows[:limit]


def merge_codes(cb, keep_id, drop_ids, records=None, reviewer=""):
    """
    把 drop_ids 併進 keep_id。records 給了就一併改寫紀錄裡的碼。

    合併是不可逆的分析決定，所以**留稽核軌跡**：被併掉的標籤記在
    merged_from，動作記在 history。沒有這個，三個月後沒有人記得
    「時間壓力」這個碼原本是三個碼合起來的。
    """
    keep = get_code(cb, keep_id)
    if keep is None:
        raise ValueError(f"unknown code: {keep_id}")
    drop_ids = [d for d in drop_ids if d != keep_id]
    dropped = [get_code(cb, d) for d in drop_ids]
    dropped = [d for d in dropped if d is not None]
    if not dropped:
        return keep

    for d in dropped:
        keep[CODE_COUNT] += d[CODE_COUNT]
        keep[CODE_MERGED_FROM].append(d[CODE_LABEL])
        keep[CODE_MERGED_FROM].extend(d.get(CODE_MERGED_FROM) or [])
        for ex in d[CODE_EXAMPLES]:
            if len(keep[CODE_EXAMPLES]) < 8:
                keep[CODE_EXAMPLES].append(ex)
        if not keep[CODE_DEFINITION] and d[CODE_DEFINITION]:
            keep[CODE_DEFINITION] = d[CODE_DEFINITION]
    keep[CODE_HISTORY].append({
        "time": datetime.now().isoformat(timespec="seconds"),
        "action": "merge",
        "detail": "merged: " + ", ".join(d[CODE_LABEL] for d in dropped),
        "reviewer": reviewer})
    cb[CODES] = [c for c in cb[CODES] if c[CODE_ID] not in drop_ids]

    if records:
        gone = set(drop_ids)
        for rec in records:
            for seg in rec.get(OPEN_SEGMENTS) or []:
                out, seen = [], set()
                for c in seg.get(OPEN_CODES) or []:
                    cid = keep[CODE_ID] if c[CODE_ID] in gone else c[CODE_ID]
                    if cid in seen:          # 合併後同一段落可能出現重複
                        continue
                    seen.add(cid)
                    out.append({**c, CODE_ID: cid,
                                CODE_LABEL: (keep[CODE_LABEL]
                                             if cid == keep[CODE_ID]
                                             else c[CODE_LABEL])})
                seg[OPEN_CODES] = out
    return keep


def drop_rare_codes(cb, min_count=2, records=None):
    """
    移除只出現過一次的碼。**預設不做，要研究者明確呼叫。**

    只出現一次的碼在編碼信度與共現分析裡是雜訊，但在紮根理論裡可能正是
    最有價值的那一個（負面案例、極端個案）。所以這件事不能自動做，也不能
    做成預設值——工具沒有立場替研究者決定哪個罕見碼是雜訊。

    回傳被移除的碼清單。
    """
    rare = [c for c in cb[CODES] if c[CODE_COUNT] < min_count]
    ids = {c[CODE_ID] for c in rare}
    cb[CODES] = [c for c in cb[CODES] if c[CODE_ID] not in ids]
    if records:
        for rec in records:
            for seg in rec.get(OPEN_SEGMENTS) or []:
                seg[OPEN_CODES] = [c for c in (seg.get(OPEN_CODES) or [])
                                   if c[CODE_ID] not in ids]
    return rare


# =====================================================================
# 碼簿 → 框架：整個設計的關節
# =====================================================================
def _short_for(code, used):
    """框架要求 2-6 個大寫英數且不重複。從碼 id 生成最穩，且天然唯一。"""
    base = re.sub(r"[^A-Za-z0-9]", "", code[CODE_ID]).upper()[:6]
    if len(base) < 2:
        base = f"C{len(used) + 1:02d}"
    s, n = base, 1
    while s in used or s == F.UNASSIGNED_SHORT:
        suffix = str(n)
        s = (base[:6 - len(suffix)] + suffix).upper()
        n += 1
    used.add(s)
    return s


def codebook_to_framework(cb, framework_id, name_en, name_zh=None,
                          description_en="", description_zh="",
                          min_count=1):
    """
    把碼簿轉成一個框架。**這一步是整個設計的關節。**

    轉成框架之後，交叉表、共現、信度、主題歸納、匯出全部原封不動地能用——
    因為那些模組讀的是作用中框架，而它們並不在意這個框架是從文獻來的還是
    從資料長出來的。

    這一步在方法論上也是一個明確的時刻：**碼簿在此定案**。開放編碼階段碼
    還在長，任何頻次統計都是暫時的；定案之後才談得上編碼信度與共現。介面
    上要把這個先後講清楚。

    每個碼的代表引文寫進 indicators——那是「這個碼長什麼樣子」的證據，
    也是之後拿這個框架重新編碼時模型會看到的東西。
    """
    keep = [c for c in cb[CODES] if c[CODE_COUNT] >= min_count]
    if not keep:
        raise ValueError("no codes meet min_count; nothing to build a framework from")

    used_short = set()
    dims = []
    for c in keep:
        quotes = [e[S.QUOTE] for e in (c[CODE_EXAMPLES] or []) if e.get(S.QUOTE)]
        dims.append({
            F.DIM_ID: c[CODE_ID],
            F.DIM_SHORT: _short_for(c, used_short),
            F.DIM_LABEL: {"en": c[CODE_LABEL], "zh": c[CODE_LABEL]},
            F.DIM_DEFINITION: {"en": c[CODE_DEFINITION], "zh": c[CODE_DEFINITION]},
            # 無極性：開放編碼產生的碼沒有正負兩極。要做障礙／助力那種
            # 兩極編碼，是在這個框架上另外宣告 polarity，不是預設。
            F.DIM_INDICATORS: {"all": {"en": quotes, "zh": quotes}},
            F.DIM_EXCLUSIONS: {"en": [], "zh": []},
            F.DIM_LITERATURE: [],
        })

    data = {
        F.FRAMEWORK_ID: framework_id,
        F.VERSION: "1.0",
        # 出處是資料，不是文獻也不是手寫——這一點必須在框架檔裡看得出來，
        # 否則三個月後沒有人分得出哪個框架是讀出來的、哪個是跑出來的。
        F.PROVENANCE: F.PROV_INDUCED,
        F.NAME: {"en": name_en, "zh": name_zh or name_en},
        F.CITATION: (f"Codebook induced from the corpus by open coding "
                     f"(codebook {cb[CODEBOOK_ID]}, "
                     f"{len(keep)} codes, created {cb.get(CREATED, '')}). "
                     f"Not derived from published literature."),
        F.DESCRIPTION: {
            "en": description_en or
            (f"{len(keep)} codes developed inductively from the corpus. "
             f"Each dimension's indicators are verbatim examples of that code "
             f"as it occurred in the data, not criteria written in advance."),
            "zh": description_zh or
            (f"由語料歸納出的 {len(keep)} 個碼。每個維度的指標是該碼在資料裡"
             f"實際出現的逐字例子，不是事先寫好的判準。")},
        F.POLARITY: {F.POLARITY_ENABLED: False, F.POLARITY_VALUES: [],
                     F.POLARITY_LABELS: {}, F.POLARITY_CITATION: ""},
        F.DIMENSIONS: dims,
    }
    return F.load_dict(data)


def to_records(open_records, cb=None):
    """
    把開放編碼的紀錄轉成標準格式，讓既有的分析管線讀得到。

    **要先啟用由碼簿轉出來的框架再呼叫**——migrate_record 會丟掉不在作用中
    框架維度裡的碼，而開放編碼的碼在框架建立之前不在任何框架裡。順序錯了
    就會得到一批空紀錄，而且不會有人告訴你。這裡直接擋下來。
    """
    active = set(F.active().dimensions)
    out = []
    for rec in open_records:
        segs = []
        for seg in rec.get(OPEN_SEGMENTS) or []:
            codes = [{S.DIMENSION: c[CODE_ID], S.POLARITY: None,
                      S.RATIONALE: c.get(S.RATIONALE, "")}
                     for c in (seg.get(OPEN_CODES) or [])
                     if c[CODE_ID] in active]
            if not codes:
                continue
            segs.append({S.SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                         S.TITLE: seg.get(S.TITLE, ""),
                         S.QUOTE: seg.get(S.QUOTE, ""),
                         S.FULL_TEXT: seg.get(S.FULL_TEXT, ""),
                         S.CODES_F: codes})
        if not segs and (rec.get(OPEN_SEGMENTS) or []):
            raise ValueError(
                "every open code was dropped: the active framework does not "
                "contain the codebook's codes. Build a framework with "
                "codebook_to_framework() and activate it before converting.")
        new = S.migrate_record({
            S.RESPONDENT: rec.get(S.RESPONDENT, "unknown"),
            S.DESCRIPTORS: rec.get(S.DESCRIPTORS) or S.blank_descriptors(),
            S.SUMMARY: rec.get(S.SUMMARY, ""),
            S.SEGMENTS: segs})
        meta = dict(rec.get(S.META) or {})
        meta["framework_id"] = F.active().id
        new[S.META] = {**(new.get(S.META) or {}), **meta}
        for k in (S.TRANSCRIPT, S.TRANSCRIPT_FILE):
            if rec.get(k):
                new[k] = rec[k]
        out.append(new)
    return out


# =====================================================================
# 存檔
# =====================================================================
def save_codebook(cb, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cb, f, ensure_ascii=False, indent=2)
    return path


def load_codebook(path):
    with open(path, "r", encoding="utf-8") as f:
        cb = json.load(f)
    cb.setdefault(CODES, [])
    for c in cb[CODES]:
        c.setdefault(CODE_EXAMPLES, [])
        c.setdefault(CODE_COUNT, 0)
        c.setdefault(CODE_MERGED_FROM, [])
        c.setdefault(CODE_HISTORY, [])
        c.setdefault(CODE_DEFINITION, "")
    return cb


def codebook_stats(cb):
    codes = cb[CODES]
    counts = [c[CODE_COUNT] for c in codes]
    return {
        "codes": len(codes),
        "applications": sum(counts),
        "singletons": sum(1 for n in counts if n == 1),
        "max_count": max(counts) if counts else 0,
        "undefined": sum(1 for c in codes if not c[CODE_DEFINITION]),
    }
