"""
tacit_irr.py — 雙盲編碼與編碼者間信度（Inter-Rater Reliability）
================================================================
對應 Dedoose Training Center 的功能，並修掉一個常見的抽樣瑕疵。

【抽樣設計 — 本模組最重要的一件事】
  若只從「AI 已標記的段落」抽樣給人類複核，人類永遠看不到 AI 忽略的文字，
  結構上就量不到漏標（false negative）。這樣算出來的 κ 只反映 precision，
  不反映 recall，這個數字就站不住。

  因此抽樣框（sampling frame）建立在**原始逐字稿的全部發言單元**上，
  分層包含「AI 標記為各碼者」與「AI 完全未標記者」。未標記層是必要的，
  沒有它就沒有 recall。

【統計量 — 為什麼不能只報 Cohen's κ】
  八個碼在絕大多數單元上都是「無」，屬於高度不平衡的稀有事件標記。
  這種情況下會出現著名的 **kappa paradox**：觀察一致率 95%，κ 卻只有 0.26。
  原因是 κ 的期望一致率 pe 在盛行率極端時被高估。故本模組同時報告
  κ、PABAK（Byrt et al., 1993）、Gwet's AC1（Gwet, 2008）、盛行率與偏誤指數，
  以及可處理多位編碼者與遺漏值的 Krippendorff's α。

【實務考量】
  跨國的共同指導教授不會為了編碼去裝 Streamlit。所以主要交付是**可離線
  填寫的 Excel 編碼表**，填完寄回再匯入。介面內編碼只是備用。
"""

import hashlib
import itertools
import json
import math
import random
import re
from collections import Counter, defaultdict

import tacit_framework as F
import tacit_schema as S


_PUNCT = re.compile(r'[\s，。！？；：、,.!?;:「」『』（）()〈〉《》【】\-—…·"\'　]+')

# 講者標記的三種寫法：【講者】、[Speaker]、以及「講者：」/「Speaker:」。
# 括號式一律視為標記；冒號式只在同一個標籤於整份逐字稿出現兩次以上時
# 才算講者（「案例：」「Source:」這類只出現一次的前言行不是講者）。
_SPEAKER_BRACKET = re.compile(r'^[【\[]\s*([^\]】]{1,40}?)\s*[】\]]\s*(.*)$')
_SPEAKER_COLON = re.compile(
    r'^([A-Za-z][A-Za-z0-9 .\'\-]{0,30}|[一-鿿]{1,10})\s*[:：]\s*(.*)$')
# 訪員一方的標籤。這些發言不是分析對象，不進抽樣框。
_INTERVIEWER = re.compile(
    r'^(?:interviewer|int|i|q|question|moderator|facilitator|researcher|host|'
    r'chair(?:man|woman|person)?|訪員|訪談者|訪問者|主持人|提問者?|問)(?:\s*\d+)?$',
    re.IGNORECASE)
# 講者標籤獨自佔一行的寫法（會議軟體匯出的逐字稿）：「Speaker 2」一行，
# 下一行才是發言；時間戳行（0:12 或 00:01:05）略過。名字獨佔一行也算，
# 但要在整份逐字稿裡出現三次以上，免得把標題當成講者。
_LINE_SPEAKER = re.compile(r"^Speaker\s*\d*$", re.IGNORECASE)
_LINE_NAME = re.compile(r"^[A-Za-z\u4e00-\u9fff][A-Za-z\u4e00-\u9fff .'\-]{0,30}$")
_TIMESTAMP = re.compile(r"^\d{1,2}:\d\d(:\d\d)?(\s*[-–]\s*\d{1,2}:\d\d(:\d\d)?)?$")
ROLE = "role"
ROLE_RESPONDENT = "respondent"
ROLE_INTERVIEWER = "interviewer"
ROLE_HEADER = "header"
# 過長的單元在句末切開；中文句末標點不帶空白，英文句末標點後接空白。
_SENT_SPLIT = re.compile(r"(?<=[。！？])|(?<=[.!?])\s+")

# --- 本模組回傳的欄位名（ASCII） ------------------------------------
N_OBS = "n"
AGREEMENT = "observed_agreement"
KAPPA = "kappa"
PABAK = "pabak"
AC1 = "ac1"
PREVALENCE_INDEX = "prevalence_index"
BIAS_INDEX = "bias_index"
BOTH = "both_coded"
NEITHER = "neither_coded"
ONLY_A = "only_a"
ONLY_B = "only_b"


# =====================================================================
# 1. 抽樣框
# =====================================================================
def normalize(text):
    return _PUNCT.sub("", text or "")


def _colon_labels(lines):
    """冒號式標籤中出現兩次以上的，視為講者。"""
    seen = Counter()
    for line in lines:
        m = _SPEAKER_COLON.match(line)
        if m:
            seen[m.group(1).strip()] += 1
    return {k for k, n in seen.items() if n >= 2}


def speaker_role(speaker, interviewers=None):
    """訪員：標籤符合訪員字樣，或在呼叫端指定的 interviewers 集合裡。"""
    if interviewers and (speaker or "").strip().casefold() in interviewers:
        return ROLE_INTERVIEWER
    return ROLE_INTERVIEWER if _INTERVIEWER.match(speaker or "") else ROLE_RESPONDENT


def _line_labels(lines):
    """獨佔一行的講者標籤：Speaker N 一律算；其他短行要出現三次以上。"""
    seen = Counter()
    for line in lines:
        if _LINE_SPEAKER.match(line):
            seen[line] += 3
        elif _LINE_NAME.match(line) and len(line.split()) <= 4 and not _TIMESTAMP.match(line):
            seen[line] += 1
    return {k for k, n in seen.items() if n >= 3}


def speakers_of(transcript, interviewers=None):
    """每位講者的單元數、字元數與角色，依出現順序。"""
    out = {}
    for u in split_units(transcript, interviewers=interviewers):
        if u[ROLE] == ROLE_HEADER:
            continue
        d = out.setdefault(u[S.SPEAKER], {"units": 0, "chars": 0, "role": u[ROLE]})
        d["units"] += 1
        d["chars"] += len(u[S.TEXT])
    return out


def suggest_interviewers(transcript):
    """
    建議哪些講者是訪員：標籤本身寫明的；若標籤是 Speaker 1、Speaker 2 這種
    看不出身分的，字元數最多的那一位當受訪者，其餘當訪員。呼叫端讓使用者改。
    """
    sp = speakers_of(transcript)
    named = {k.casefold() for k in sp if _INTERVIEWER.match(k or "")}
    if named:
        return named
    generic = [k for k in sp if _LINE_SPEAKER.match(k or "")]
    if len(generic) >= 2:
        top = max(generic, key=lambda k: sp[k]["chars"])
        return {k.casefold() for k in generic if k != top}
    return set()


def split_units(transcript, min_len=15, max_len=400, interviewers=None):
    """
    把逐字稿切成「發言單元」，每個單元帶講者與角色。

    有講者標記的逐字稿：標記行開始一個新輪次，之後沒有標記的行是同一位
    講者的續段；第一個標記之前的行是標題與前言（角色 header）。
    沒有任何標記的文件：逐段切，角色一律 respondent。
    過短的單元併入前一個——但**只在同一位講者之間合併**。
    跨講者合併會把訪員的提問黏進受訪者的發言裡，造成張冠李戴。
    """
    lines = [raw.strip() for raw in (transcript or "").split("\n")]
    lines = [ln for ln in lines if ln and not _TIMESTAMP.match(ln)]
    colon = _colon_labels(lines)
    standalone = _line_labels(lines)
    labelled = any(_SPEAKER_BRACKET.match(ln) for ln in lines) or bool(colon) or bool(standalone)
    interviewers = {str(x).strip().casefold() for x in (interviewers or ())}

    units, buf = [], None
    cur_speaker, seen_label = "", False
    for line in lines:
        if line in standalone:
            cur_speaker, seen_label = line, True
            continue
        m = _SPEAKER_BRACKET.match(line)
        if m:
            speaker, body = m.group(1).strip(), m.group(2).strip()
        else:
            m = _SPEAKER_COLON.match(line)
            if m and m.group(1).strip() in colon:
                speaker, body = m.group(1).strip(), m.group(2).strip()
            else:
                m = None
                body = line
        if m:
            cur_speaker, seen_label = speaker, True
            role = speaker_role(speaker, interviewers)
        elif labelled and not seen_label:
            speaker, role = "", ROLE_HEADER
        else:
            speaker = cur_speaker
            role = speaker_role(speaker, interviewers) if labelled else ROLE_RESPONDENT
        if not body:
            continue
        if (buf and len(normalize(buf[S.TEXT])) < min_len
                and buf[S.SPEAKER] == speaker and buf[ROLE] == role):
            buf[S.TEXT] += body
            continue
        if buf:
            units.append(buf)
        buf = {S.SPEAKER: speaker, S.TEXT: body, ROLE: role}
    if buf:
        units.append(buf)

    out = []
    for u in units:
        t = u[S.TEXT]
        if len(t) <= max_len:
            out.append(u)
            continue
        parts, cur = [], ""
        for piece in _SENT_SPLIT.split(t):
            if not piece:
                continue
            if len(cur) + len(piece) > max_len and cur:
                parts.append(cur); cur = piece
            else:
                cur += (" " if cur and not cur[-1].isspace() and piece[0].isascii() else "") + piece
        if cur:
            parts.append(cur)
        for p in parts:
            out.append({S.SPEAKER: u[S.SPEAKER], S.TEXT: p, ROLE: u[ROLE]})

    merged = []
    for u in out:
        if (merged and len(normalize(u[S.TEXT])) < min_len
                and merged[-1][S.SPEAKER] == u[S.SPEAKER]
                and merged[-1][ROLE] == u[ROLE]):
            merged[-1][S.TEXT] += u[S.TEXT]
        else:
            merged.append(u)
    return [u for u in merged if len(normalize(u[S.TEXT])) >= min_len]


def _overlaps(unit_norm, excerpt_norm, min_chars=10):
    if not excerpt_norm or len(excerpt_norm) < min_chars:
        return False
    if excerpt_norm in unit_norm:
        return True
    return len(unit_norm) >= min_chars and unit_norm in excerpt_norm


def build_frame(records, transcripts, min_len=15, max_len=400,
                include_interviewer=False, interviewers=None):
    """
    transcripts: {respondent: 逐字稿全文}
    回傳抽樣框：每個單元一列，附上 AI 在該單元標記的編碼集合。
    未被 AI 標記的單元 ai_codes 為空——**這些就是量 recall 的關鍵**。

    只有受訪者的發言進抽樣框。訪員的提問與檔頭的標題行不是編碼對象，
    留在框裡只會灌高「未標記」的數量，讓 PABAK 與 AC1 好看而無意義；
    它們的數量記在 diag 裡。include_interviewer=True 時訪員發言也納入。
    """
    by_resp = defaultdict(list)
    for rec in records:
        resp = rec.get(S.RESPONDENT, "unknown")
        for seg in rec.get(S.SEGMENTS, []):
            txt = seg.get(S.FULL_TEXT) or seg.get(S.QUOTE) or ""
            codes = set(S.codes_of(seg))
            if txt and codes:
                by_resp[resp].append((normalize(txt), codes))

    frame, matched, on_excluded = [], defaultdict(set), defaultdict(set)
    excluded = Counter()
    for resp, text in transcripts.items():
        for k, u in enumerate(split_units(text, min_len, max_len, interviewers)):
            role = u.get(ROLE, ROLE_RESPONDENT)
            un = normalize(u[S.TEXT])
            if role == ROLE_HEADER or (role == ROLE_INTERVIEWER
                                       and not include_interviewer):
                excluded[role] += 1
                # 落在訪員提問或標題行上的編碼不進框，但要記下來：
                # 那是模型（或編碼者）把非分析對象的文字標了碼。
                for j, (ex, cs) in enumerate(by_resp.get(resp, [])):
                    if _overlaps(un, ex):
                        on_excluded[resp].add(j)
                continue
            codes = set()
            for j, (ex, cs) in enumerate(by_resp.get(resp, [])):
                if _overlaps(un, ex):
                    codes |= cs
                    matched[resp].add(j)
            frame.append({
                S.UNIT_ID: f"U{len(frame) + 1:04d}",
                S.RESPONDENT: resp,
                "position": k,
                S.SPEAKER: u[S.SPEAKER],
                ROLE: role,
                S.TEXT: u[S.TEXT],
                S.AI_CODES: sorted(codes),
                S.STRATUM: "+".join(sorted(codes)) if codes else S.STRATUM_UNMARKED,
            })

    only_excluded = {r: len(on_excluded.get(r, set()) - matched.get(r, set()))
                     for r in by_resp}
    unmatched = {r: len(v) - len(matched.get(r, set())) - only_excluded[r]
                 for r, v in by_resp.items()}
    diag = {
        "total_units": len(frame),
        "ai_coded_units": sum(1 for f in frame if f[S.AI_CODES]),
        "uncoded_units": sum(1 for f in frame if not f[S.AI_CODES]),
        "transcripts": len(transcripts),
        "unmatched_quotes": {k: v for k, v in unmatched.items() if v},
        "quotes_on_excluded_units": {k: v for k, v in only_excluded.items() if v},
        "excluded_interviewer_units": excluded[ROLE_INTERVIEWER],
        "excluded_header_units": excluded[ROLE_HEADER],
    }
    return frame, diag


# =====================================================================
# 2. 分層抽樣與雙盲工作階段
# =====================================================================
def stratified_sample(frame, n=100, seed=42, min_per_code=4, unmarked_share=0.35):
    """
    每個 AI 編碼層至少抽 min_per_code 個（保證稀有碼有樣本）；
    未標記層固定佔 unmarked_share（預設 35%），這是 recall 的唯一來源。
    """
    rnd = random.Random(seed)
    marked = [f for f in frame if f[S.AI_CODES]]
    unmarked = [f for f in frame if not f[S.AI_CODES]]

    if not marked:
        # 純人工模式：整個抽樣框都沒有模型編碼（研究者直接上傳逐字稿，
        # 想做的是兩位人類編碼者之間的信度）。這時 unmarked_share 不該再
        # 生效——它的用途是保證「模型沒標的地方」有樣本，而這裡全部都是。
        # 不處理的話，要 100 個單元只會抽到 35 個。
        um = unmarked[:]
        rnd.shuffle(um)
        return um[:n]

    n_unmarked = min(len(unmarked), int(round(n * unmarked_share)))
    n_marked = min(len(marked), n - n_unmarked)

    by_code = defaultdict(list)
    for f in marked:
        for c in f[S.AI_CODES]:
            by_code[c].append(f)

    chosen, seen = [], set()

    def take(pool, k):
        got = 0
        for f in pool:
            if got >= k:
                break
            if f[S.UNIT_ID] in seen:
                continue
            seen.add(f[S.UNIT_ID]); chosen.append(f); got += 1

    for c in S.CODES:
        pool = by_code.get(c, [])[:]
        rnd.shuffle(pool)
        take(pool, min(min_per_code, len(pool)))

    rest = [f for f in marked if f[S.UNIT_ID] not in seen]
    rnd.shuffle(rest)
    take(rest, max(0, n_marked - len(chosen)))

    um = unmarked[:]
    rnd.shuffle(um)
    take(um, n_unmarked)

    rnd.shuffle(chosen)
    return chosen


def create_session(sample, coders, seed=42, note=""):
    """建立雙盲工作階段。AI 編碼保存在 session 內，但不會出現在編碼表上。"""
    payload = json.dumps([s[S.UNIT_ID] for s in sample], ensure_ascii=False)
    sid = hashlib.md5((payload + str(seed)).encode()).hexdigest()[:8]
    return {
        S.SESSION_ID: sid,
        S.SEED: seed,
        S.NOTE: note,
        S.CODERS: list(coders),
        S.UNITS: [{S.UNIT_ID: s[S.UNIT_ID], S.RESPONDENT: s[S.RESPONDENT],
                   S.SPEAKER: s[S.SPEAKER], S.TEXT: s[S.TEXT],
                   S.STRATUM: s[S.STRATUM], S.AI_CODES: s[S.AI_CODES]}
                  for s in sample],
        S.HUMAN_CODINGS: {c: {} for c in coders},
    }


def coding_sheet_rows(session, coder):
    """
    離線編碼表。**刻意不含 AI 編碼與分層資訊**，確保盲測。
    欄位名以 i18n 在匯出時翻譯；此處回傳 ASCII 鍵。
    """
    rows = []
    for u in session[S.UNITS]:
        row = {S.UNIT_ID: u[S.UNIT_ID], "coder": coder, S.TEXT: u[S.TEXT]}
        for c in S.CODES:
            row[c] = ""
        row["comment"] = ""
        rows.append(row)
    return rows


def parse_coding_sheet(rows, valid_ids=None):
    """讀回填好的編碼表。填表的人不會照你想的格式填，所以標記方式要寬鬆。"""
    truthy = {"1", "1.0", "v", "V", "✓", "✔", "x", "X", "y", "Y",
              "yes", "true", "True", "是", "有"}
    out = {}
    for r in rows:
        uid = str(r.get(S.UNIT_ID, r.get("單元ID", ""))).strip()
        if not uid or (valid_ids is not None and uid not in valid_ids):
            continue
        codes = {c for c in S.CODES if str(r.get(c, "")).strip() in truthy}
        out[uid] = sorted(codes)
    return out


# 人工編碼紀錄的來源標記。分析頁籤照樣讀得懂這些紀錄，但要看得出來
# 它們從哪裡來——這一批的每一個碼都是人打的，沒有任何模型參與。
SOURCE_HUMAN_CODING = "human-coding"


def records_from_codings(session, coder, descriptors=None, framework_id=None):
    """
    把一位編碼者交回來的編碼表轉成分析紀錄（一位受訪者一筆）。

    沒有這條路的話，人工編碼表匯進來只算了信度就停住，交叉表、共現、
    跨個案矩陣、詞彙探勘、匯出這些**本來就不需要模型**的引擎讀不到它，
    於是「手邊沒有模型的研究者能做什麼」的答案就只有一個信度係數。
    接起來之後，一份逐字稿加兩位編碼者就能走完整套分析。

    產出的段落 quote 與 full_text 都是該發言單元的原文：人工編碼是在單元
    層級做的，硬要在單元裡再框一段引文等於替編碼者做他沒做的判斷。
    review 狀態記為 confirmed / human，原始編碼留空——沒有模型草稿被覆蓋，
    修正比例在這種紀錄上本來就不該有數字。
    """
    codings = (session.get(S.HUMAN_CODINGS) or {}).get(coder) or {}
    units = {u[S.UNIT_ID]: u for u in session.get(S.UNITS) or []}
    by_resp = defaultdict(list)
    for uid in sorted(codings):
        u = units.get(uid)
        if u is None or not codings[uid]:
            continue
        by_resp[u.get(S.RESPONDENT) or "unknown"].append((uid, u, codings[uid]))

    out = []
    for resp in sorted(by_resp):
        segments = []
        for uid, u, codes in by_resp[resp]:
            parsed = []
            for c in codes:
                dim, pol = S.split_code(c)
                if dim:
                    parsed.append(S.make_code(dim, pol))
            if not parsed:
                continue
            text = u.get(S.TEXT) or ""
            segments.append({
                S.SEGMENT_ID: f"S{len(segments) + 1:03d}",
                S.TITLE: "",
                S.QUOTE: text,
                S.FULL_TEXT: text,
                S.CODES_F: parsed,
                S.REVIEW: {S.STATUS: S.STATUS_CONFIRMED,
                           S.SOURCE: S.SOURCE_HUMAN,
                           S.ORIGINAL_CODES: [],
                           S.HISTORY: [{"by": coder, "unit_id": uid}]},
            })
        if not segments:
            continue
        out.append({
            S.RESPONDENT: resp,
            S.DESCRIPTORS: dict((descriptors or {}).get(resp) or {}),
            S.SEGMENTS: segments,
            S.DELETED_SEGMENTS: [],
            S.SUMMARY: "",
            S.META: {
                "schema_version": S.SCHEMA_VERSION,
                "framework_id": framework_id or F.active().id,
                "source": f"{SOURCE_HUMAN_CODING}/{session.get(S.SESSION_ID, '')}",
                "coder": coder,
                "session_id": session.get(S.SESSION_ID, ""),
                "seed": session.get(S.SEED),
                "endpoint": None,       # 沒有模型參與，這裡刻意留空而不是省略
            },
        })
    return out


# =====================================================================
# 3. 信度統計
# =====================================================================
def binary_agreement(a, b):
    """
    兩位編碼者對「某一個碼」的二元判定一致度。
    同時回傳 κ 與其診斷指標，因為稀有事件下單看 κ 會嚴重誤導。
    """
    keys = (N_OBS, AGREEMENT, KAPPA, PABAK, AC1, PREVALENCE_INDEX, BIAS_INDEX,
            BOTH, NEITHER, ONLY_A, ONLY_B)
    n = len(a)
    if n == 0:
        return {k: None for k in keys}
    both = sum(1 for x, y in zip(a, b) if x and y)
    neither = sum(1 for x, y in zip(a, b) if not x and not y)
    only_a = sum(1 for x, y in zip(a, b) if x and not y)
    only_b = sum(1 for x, y in zip(a, b) if not x and y)

    po = (both + neither) / n
    pa, pb = (both + only_a) / n, (both + only_b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    kappa = None if abs(1 - pe) < 1e-12 else (po - pe) / (1 - pe)
    pi_mean = (pa + pb) / 2
    pe_g = 2 * pi_mean * (1 - pi_mean)
    ac1 = None if abs(1 - pe_g) < 1e-12 else (po - pe_g) / (1 - pe_g)
    r = lambda v: None if v is None else round(v, 3)
    return {N_OBS: n, AGREEMENT: r(po), KAPPA: r(kappa), PABAK: r(2 * po - 1),
            AC1: r(ac1), PREVALENCE_INDEX: r(abs((both - neither) / n)),
            BIAS_INDEX: r(abs((only_a - only_b) / n)),
            BOTH: both, NEITHER: neither, ONLY_A: only_a, ONLY_B: only_b}


def per_code_agreement(coding_a, coding_b, unit_ids):
    rows = []
    for c in S.CODES:
        a = [1 if c in coding_a.get(u, []) else 0 for u in unit_ids]
        b = [1 if c in coding_b.get(u, []) else 0 for u in unit_ids]
        rows.append({"code": c, **binary_agreement(a, b)})
    return rows


def pooled_kappa(coding_a, coding_b, unit_ids):
    """Dedoose 式 pooled kappa：所有碼的 2×2 表加總為單一表再算 κ。"""
    a, b = [], []
    for u in unit_ids:
        sa, sb = set(coding_a.get(u, [])), set(coding_b.get(u, []))
        for c in S.CODES:
            a.append(1 if c in sa else 0)
            b.append(1 if c in sb else 0)
    return binary_agreement(a, b)


def exact_set_agreement(coding_a, coding_b, unit_ids):
    """整組編碼完全相同的單元比例——最嚴格也最直觀的指標。"""
    if not unit_ids:
        return None
    same = sum(1 for u in unit_ids
               if set(coding_a.get(u, [])) == set(coding_b.get(u, [])))
    return round(same / len(unit_ids), 3)


def krippendorff_alpha_nominal(values):
    """
    Krippendorff's α（名目尺度）。可處理任意編碼者數與遺漏值。
    values: {unit: [該單元所有非遺漏的編碼值]}，只計入至少被兩人編碼的單元。

    α = 1 − Do/De
      Do = Σ_{c≠k} o_ck                    觀察到的不一致
      De = Σ_{c≠k} n_c·n_k / (n−1)         期望的不一致
    驗證方式見 test_irr.py：與獨立實作的 Scott's π 交叉比對，另有手算重合矩陣。
    """
    values = {u: vs for u, vs in values.items() if len(vs) >= 2}
    if not values:
        return None
    o = defaultdict(float)
    for vs in values.values():
        m = len(vs)
        for i in range(m):
            for j in range(m):
                if i != j:
                    o[(vs[i], vs[j])] += 1.0 / (m - 1)
    n_c = defaultdict(float)
    for (c1, _c2), v in o.items():
        n_c[c1] += v
    n = sum(n_c.values())
    if n <= 1:
        return None
    Do = sum(v for (c1, c2), v in o.items() if c1 != c2)
    De = sum(n_c[c1] * n_c[c2] for c1 in n_c for c2 in n_c if c1 != c2) / (n - 1)
    if De == 0:
        return None
    return round(1 - Do / De, 3)


def krippendorff_alpha(codings, unit_ids, code):
    """針對單一編碼做「有／無」二元 α。未編碼該單元者視為遺漏值。"""
    values = {}
    for u in unit_ids:
        vs = [1 if code in cd[u] else 0 for cd in codings.values() if u in cd]
        if len(vs) >= 2:
            values[u] = vs
    return krippendorff_alpha_nominal(values)


def dimension_confusion(coding_a, coding_b, unit_ids):
    """維度層次的混淆矩陣（不分極性，含「無」），列＝A、欄＝B。"""
    labels = S.DIMENSIONS + [S.NONE_LABEL]
    mat = {r: {c: 0 for c in labels} for r in labels}
    for u in unit_ids:
        da = {S.split_code(c)[0] for c in coding_a.get(u, [])} or {S.NONE_LABEL}
        db = {S.split_code(c)[0] for c in coding_b.get(u, [])} or {S.NONE_LABEL}
        for x in da:
            for y in db:
                if x in mat and y in mat[x]:
                    mat[x][y] += 1
    return labels, mat


def polarity_confusion(coding_a, coding_b, unit_ids):
    """
    只看雙方都認定屬同一維度的單元，比較極性判定。
    極性分歧比維度分歧更值得討論——代表雙方讀出的評價方向相反。
    """
    rows = []
    for dim in S.DIMENSIONS:
        short = S.DIM_SHORT[dim]
        agree = disagree = 0
        for u in unit_ids:
            pa = {c.split("-")[1] for c in coding_a.get(u, [])
                  if c.startswith(short + "-")}
            pb = {c.split("-")[1] for c in coding_b.get(u, [])
                  if c.startswith(short + "-")}
            if not pa or not pb:
                continue
            if pa == pb:
                agree += 1
            else:
                disagree += 1
        tot = agree + disagree
        rows.append({S.DIMENSION: dim, "both_assigned": tot,
                     "polarity_agree": agree, "polarity_conflict": disagree,
                     "polarity_agreement_rate": round(agree / tot, 3) if tot else None})
    return rows


DISAGREE_POLARITY = "polarity_conflict"
DISAGREE_DIMENSION = "dimension_mismatch"
DISAGREE_PRESENCE = "presence_mismatch"


def disagreement_list(session, codings, name_a, name_b, limit=None):
    """雙方意見分歧的單元清單，供校準會議逐條討論。"""
    text = {u[S.UNIT_ID]: u for u in session[S.UNITS]}
    ca, cb = codings.get(name_a, {}), codings.get(name_b, {})
    rows = []
    for uid in [u[S.UNIT_ID] for u in session[S.UNITS]]:
        sa, sb = set(ca.get(uid, [])), set(cb.get(uid, []))
        if sa == sb:
            continue
        u = text[uid]
        if not sa or not sb:
            kind = DISAGREE_PRESENCE
        elif {c.split("-")[0] for c in sa} == {c.split("-")[0] for c in sb}:
            kind = DISAGREE_POLARITY
        else:
            kind = DISAGREE_DIMENSION
        rows.append({
            S.UNIT_ID: uid, S.RESPONDENT: u[S.RESPONDENT],
            "coder_a": name_a, "coder_b": name_b,
            "codes_a": sorted(sa), "codes_b": sorted(sb),
            "only_a": sorted(sa - sb), "only_b": sorted(sb - sa),
            "disagreement_type": kind,
            S.TEXT: u[S.TEXT],
            S.AI_CODES: list(u.get(S.AI_CODES) or []),
        })
    order = {DISAGREE_POLARITY: 0, DISAGREE_DIMENSION: 1, DISAGREE_PRESENCE: 2}
    rows.sort(key=lambda r: order.get(r["disagreement_type"], 9))
    return rows[:limit] if limit else rows


def recall_estimate(session, coding_human):
    """
    以人工編碼為參照，估計 AI 的 precision / recall / F1。
    因為抽樣框含未標記單元，這裡的 recall 才是有意義的。
    """
    rows = []
    units = session[S.UNITS]
    for c in S.CODES:
        tp = fp = fn = 0
        for u in units:
            ai = c in (u.get(S.AI_CODES) or [])
            hu = c in coding_human.get(u[S.UNIT_ID], [])
            if ai and hu:
                tp += 1
            elif ai and not hu:
                fp += 1
            elif hu and not ai:
                fn += 1
        prec = tp / (tp + fp) if tp + fp else None
        rec = tp / (tp + fn) if tp + fn else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else None
        rows.append({"code": c, "human_count": tp + fn, "ai_count": tp + fp,
                     "tp": tp, "fp_ai_extra": fp, "fn_ai_missed": fn,
                     "precision": None if prec is None else round(prec, 3),
                     "recall": None if rec is None else round(rec, 3),
                     "f1": None if f1 is None else round(f1, 3)})
    return rows


# =====================================================================
# 4. 解讀
# =====================================================================
BAND_ALMOST_PERFECT = "almost_perfect"
BAND_SUBSTANTIAL = "substantial"
BAND_MODERATE = "moderate"
BAND_FAIR = "fair"
BAND_SLIGHT = "slight"
BAND_NA = "not_available"


def kappa_band(v):
    """Landis & Koch (1977) 的慣用門檻。回傳識別碼，顯示文字交給 i18n。"""
    if v is None:
        return BAND_NA
    if v > .80:
        return BAND_ALMOST_PERFECT
    if v > .60:
        return BAND_SUBSTANTIAL
    if v > .40:
        return BAND_MODERATE
    if v > .20:
        return BAND_FAIR
    return BAND_SLIGHT


def interpret(kappa, pabak, ac1, prevalence_index):
    """
    回傳結構化判讀結果（不含顯示文字），由介面依語言組句。
    is_paradox 為真時，代表 κ 偏低是盛行率造成的，不是編碼者不一致。
    """
    paradox = (kappa is not None and prevalence_index is not None
               and prevalence_index > 0.6 and (pabak or 0) - kappa > 0.2)
    return {KAPPA: kappa, PABAK: pabak, AC1: ac1,
            PREVALENCE_INDEX: prevalence_index,
            "band": kappa_band(kappa), "is_paradox": bool(paradox)}
