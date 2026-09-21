"""
tacit_review.py — 人工編碼複核與稽核軌跡
=======================================
這個模組回答的是一個**認識論**問題，不是工程問題。

  「質性詮釋不該外包給機器」——這個反對不能用統計量回應，只能用流程設計回應：
  讓 AI 只做初編碼，研究者逐段複核並保有最終權威。

  補上這一層之後，論文可以誠實地寫：模型執行初編碼，研究者確認、修正或刪除，
  並補入模型漏標的段落；進入分析的每一個編碼皆經研究者複核。
  而且這句話有數字支撐——複核率、修改率、刪除率、新增數皆可報告。

【設計原則：永不銷毀原始資料】
  AI 的原始編碼在第一次複核時被快照保存，之後不論怎麼改都保留。
  刪除的段落移入 deleted_segments 而非真的刪掉。
  每一次修改都寫入編輯紀錄（時間、動作、前後值、複核者）。
  沒有這條軌跡，「人工複核過」就只是一句無法查證的宣稱。

【附帶解決：逐字引文驗證】
  複核時若已載入原始逐字稿，會即時檢查引文是否逐字存在於原文。
  對不上的引文代表模型改寫或幻覺。
"""

import re
from collections import Counter
from datetime import datetime

import tacit_schema as S

_PUNCT = re.compile(r'[\s，。！？；：、,.!?;:「」『』（）()〈〉《》【】\-—…·"\'　]+')

# 編輯紀錄欄位
LOG_TIME = "time"
LOG_ACTION = "action"
LOG_DETAIL = "detail"
LOG_REVIEWER = "reviewer"

# 動作識別碼（顯示文字交給 i18n）
ACTION_CONFIRM = "confirm"
ACTION_UPDATE_CODES = "update_codes"
ACTION_UPDATE_TEXT = "update_text"
ACTION_DELETE = "delete"
ACTION_RESTORE = "restore"
ACTION_ADD = "add"
ALL_ACTIONS = [ACTION_CONFIRM, ACTION_UPDATE_CODES, ACTION_UPDATE_TEXT,
               ACTION_DELETE, ACTION_RESTORE, ACTION_ADD]


def normalize(text):
    return _PUNCT.sub("", text or "")


def codes_of(segment):
    return S.codes_of(segment)


def codes_to_objects(codes, rationales=None):
    rationales = rationales or {}
    out = []
    for c in codes:
        dim, pol = S.split_code(c)
        if dim not in S.DIMENSIONS:
            continue
        # 無極性框架的 split_code 回傳 (dim, None)，而 POLARITIES 是空清單，
        # 於是 `pol in S.POLARITIES` 永遠為假——每一個碼都會被靜默丟掉。
        # fallback 寫成 [P, N] 也一樣（None 不在裡面）；
        # 無極性框架的複核路徑要分開處理。
        if S.HAS_POLARITY:
            if pol not in S.POLARITIES:
                continue
        elif pol is not None:
            continue
        out.append(S.make_code(dim, pol, rationales.get(c, "")))
    return out


# =====================================================================
# 1. 審核欄位初始化
# =====================================================================
def ensure_review(seg, source=S.SOURCE_AI):
    """
    確保段落帶有審核欄位。第一次呼叫時把 AI 的原始編碼快照下來——
    這份快照是整條稽核軌跡的基準，之後永遠不覆寫。
    """
    r = seg.setdefault(S.REVIEW, {})
    r.setdefault(S.STATUS,
                 S.STATUS_PENDING if source == S.SOURCE_AI else S.STATUS_ADDED)
    if S.ORIGINAL_CODES not in r:
        r[S.ORIGINAL_CODES] = codes_of(seg)
        r[S.ORIGINAL_TITLE] = seg.get(S.TITLE, "")
        r[S.ORIGINAL_QUOTE] = seg.get(S.QUOTE, "")
        r[S.SOURCE] = source
    r.setdefault(S.HISTORY, [])
    return seg


def ensure_all(records):
    for rec in records:
        rec.setdefault(S.DELETED_SEGMENTS, [])
        for seg in rec.get(S.SEGMENTS, []):
            ensure_review(seg)
        for seg in rec[S.DELETED_SEGMENTS]:
            ensure_review(seg)
    return records


def _log(seg, action, detail, reviewer):
    seg[S.REVIEW][S.HISTORY].append({
        LOG_TIME: datetime.now().isoformat(timespec="seconds"),
        LOG_ACTION: action, LOG_DETAIL: detail, LOG_REVIEWER: reviewer,
    })


# =====================================================================
# 2. 編輯操作
# =====================================================================
def confirm(seg, reviewer="researcher"):
    """確認 AI 編碼無誤。狀態為 confirmed，不改動內容。"""
    ensure_review(seg)
    if seg[S.REVIEW][S.STATUS] != S.STATUS_ADDED:
        seg[S.REVIEW][S.STATUS] = S.STATUS_CONFIRMED
    _log(seg, ACTION_CONFIRM, "", reviewer)
    return seg


def update_codes(seg, new_codes, rationales=None, reviewer="researcher"):
    """
    修改段落編碼。回傳 (是否有變動, 新增的碼, 移除的碼)。
    沒有實際變動時視同確認，不會假造一筆修改紀錄。
    """
    ensure_review(seg)
    old = set(codes_of(seg))
    new = {c for c in new_codes if c in S.CODES}
    added, removed = sorted(new - old), sorted(old - new)
    if not added and not removed:
        confirm(seg, reviewer)
        return False, [], []
    keep = {}
    for c in seg.get(S.CODES_F) or []:
        dim, pol = S.norm_dimension(c.get(S.DIMENSION)), S.norm_polarity(c.get(S.POLARITY))
        if dim in S.DIMENSIONS and pol:
            keep[S.code_of(dim, pol)] = c.get(S.RATIONALE, "")
    keep.update(rationales or {})
    seg[S.CODES_F] = codes_to_objects(sorted(new), keep)
    seg[S.REVIEW][S.STATUS] = S.STATUS_MODIFIED
    _log(seg, ACTION_UPDATE_CODES,
         f"+{','.join(added) or '-'} / -{','.join(removed) or '-'}", reviewer)
    return True, added, removed


def update_text(seg, title=None, quote=None, full_text=None, reviewer="researcher"):
    """修改文字欄位。引文被改動時特別記錄——這牽涉逐字性。"""
    ensure_review(seg)
    changes = []
    for field, val in ((S.TITLE, title), (S.QUOTE, quote), (S.FULL_TEXT, full_text)):
        if val is not None and val != seg.get(field, ""):
            changes.append(f"{field}: \"{seg.get(field, '')[:20]}\" -> \"{val[:20]}\"")
            seg[field] = val
    if not changes:
        return False
    if seg[S.REVIEW][S.STATUS] in (S.STATUS_PENDING, S.STATUS_CONFIRMED):
        seg[S.REVIEW][S.STATUS] = S.STATUS_MODIFIED
    _log(seg, ACTION_UPDATE_TEXT, "; ".join(changes), reviewer)
    return True


def delete_segment(rec, seg_id, reason="", reviewer="researcher"):
    """刪除段落——移入 deleted_segments，不是真的丟掉。"""
    rec.setdefault(S.DELETED_SEGMENTS, [])
    for i, seg in enumerate(rec.get(S.SEGMENTS, [])):
        if seg.get(S.SEGMENT_ID) == seg_id:
            ensure_review(seg)
            seg[S.REVIEW][S.STATUS] = S.STATUS_DELETED
            _log(seg, ACTION_DELETE, reason, reviewer)
            rec[S.DELETED_SEGMENTS].append(rec[S.SEGMENTS].pop(i))
            return True
    return False


def restore_segment(rec, seg_id, reviewer="researcher"):
    for i, seg in enumerate(rec.get(S.DELETED_SEGMENTS, [])):
        if seg.get(S.SEGMENT_ID) == seg_id:
            seg[S.REVIEW][S.STATUS] = S.STATUS_MODIFIED
            _log(seg, ACTION_RESTORE, "", reviewer)
            rec.setdefault(S.SEGMENTS, []).append(rec[S.DELETED_SEGMENTS].pop(i))
            return True
    return False


def add_segment(rec, text, codes, title="", quote=None,
                reviewer="researcher", reason=""):
    """
    人工新增段落——補入模型漏標的內容。
    這是研究者行使詮釋權最直接的形式，也是唯一能改善 recall 的操作。
    """
    existing = ([s.get(S.SEGMENT_ID, "") for s in rec.get(S.SEGMENTS, [])] +
                [s.get(S.SEGMENT_ID, "") for s in rec.get(S.DELETED_SEGMENTS, [])])
    n = 1
    while f"M{n:03d}" in existing:
        n += 1
    seg = {
        S.SEGMENT_ID: f"M{n:03d}",
        S.TITLE: title or (text or "")[:16],
        S.QUOTE: quote if quote is not None else (text or "")[:40],
        S.FULL_TEXT: text or "",
        S.CODES_F: codes_to_objects([c for c in codes if c in S.CODES]),
    }
    ensure_review(seg, source=S.SOURCE_HUMAN)
    seg[S.REVIEW][S.ORIGINAL_CODES] = []       # 人工新增者，AI 原本沒有任何編碼
    _log(seg, ACTION_ADD, reason, reviewer)
    rec.setdefault(S.SEGMENTS, []).append(seg)
    return seg


# =====================================================================
# 3. 逐字引文驗證
# =====================================================================
QUOTE_ISSUE_FULL = "full_text_not_verbatim"
QUOTE_ISSUE_BRIEF = "quote_not_verbatim"


def verify_quote(seg, transcript):
    """檢查引文是否逐字存在於逐字稿（忽略標點與空白）。"""
    if not transcript:
        return {"checkable": False, "quote_ok": None, "full_text_ok": None,
                "quote_within_full": None}
    t = normalize(transcript)
    brief, full = normalize(seg.get(S.QUOTE, "")), normalize(seg.get(S.FULL_TEXT, ""))
    return {
        "checkable": True,
        "quote_ok": (brief in t) if brief else None,
        "full_text_ok": (full in t) if full else None,
        "quote_within_full": (brief in full) if (brief and full) else None,
    }


def verify_all_quotes(records, transcripts):
    """全體引文驗證，回傳 (摘要, 問題清單)。"""
    rows, checked, ok_brief, ok_full = [], 0, 0, 0
    for rec in records:
        t = transcripts.get(rec.get(S.RESPONDENT, ""), "")
        if not t:
            continue
        for seg in rec.get(S.SEGMENTS, []):
            v = verify_quote(seg, t)
            if not v["checkable"]:
                continue
            checked += 1
            ok_brief += 1 if v["quote_ok"] else 0
            ok_full += 1 if v["full_text_ok"] else 0
            if v["quote_ok"] and v["full_text_ok"]:
                continue
            rows.append({
                S.RESPONDENT: rec.get(S.RESPONDENT, ""),
                S.SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                "issue": (QUOTE_ISSUE_FULL if not v["full_text_ok"]
                          else QUOTE_ISSUE_BRIEF),
                S.QUOTE: seg.get(S.QUOTE, ""),
                S.FULL_TEXT: (seg.get(S.FULL_TEXT, "") or "")[:120],
                "codes": codes_of(seg),
                S.STATUS: seg.get(S.REVIEW, {}).get(S.STATUS, S.STATUS_PENDING),
            })
    summary = {
        "checked": checked,
        "quote_verbatim": ok_brief,
        "full_text_verbatim": ok_full,
        "quote_rate": round(ok_brief / checked, 3) if checked else None,
        "full_text_rate": round(ok_full / checked, 3) if checked else None,
        "needs_review": len(rows),
    }
    return summary, rows


# =====================================================================
# 4. 複核統計 —— 這就是要寫進論文的那組數字
# =====================================================================
def review_stats(records):
    ensure_all(records)
    alive = [s for rec in records for s in rec.get(S.SEGMENTS, [])]
    deleted = [s for rec in records for s in rec.get(S.DELETED_SEGMENTS, [])]

    ai_origin = ([s for s in alive if s[S.REVIEW].get(S.SOURCE) != S.SOURCE_HUMAN] +
                 [s for s in deleted if s[S.REVIEW].get(S.SOURCE) != S.SOURCE_HUMAN])
    n_ai = len(ai_origin)
    reviewed = sum(1 for s in ai_origin if s[S.REVIEW][S.STATUS] != S.STATUS_PENDING)
    modified = sum(1 for s in ai_origin if s[S.REVIEW][S.STATUS] == S.STATUS_MODIFIED)
    confirmed = sum(1 for s in ai_origin if s[S.REVIEW][S.STATUS] == S.STATUS_CONFIRMED)
    added = sum(1 for s in alive if s[S.REVIEW].get(S.SOURCE) == S.SOURCE_HUMAN)

    def pct(a, b):
        return round(a / b, 3) if b else None

    return {
        "ai_segments": n_ai,
        "reviewed": reviewed,
        "review_rate": pct(reviewed, n_ai),
        "confirmed": confirmed,
        "confirm_rate": pct(confirmed, n_ai),
        "modified": modified,
        "modify_rate": pct(modified, n_ai),
        "deleted": len(deleted),
        "delete_rate": pct(len(deleted), n_ai),
        "human_added": added,
        "active_segments": len(alive),
        "pending": sum(1 for s in alive if s[S.REVIEW][S.STATUS] == S.STATUS_PENDING),
    }


def code_level_changes(records):
    """
    逐碼的修改情形。移除率高的碼，代表提示詞對該碼的判準需要收緊。
    """
    ensure_all(records)
    orig, final, removed, added = Counter(), Counter(), Counter(), Counter()
    for rec in records:
        for seg in list(rec.get(S.SEGMENTS, [])) + list(rec.get(S.DELETED_SEGMENTS, [])):
            o = set(seg[S.REVIEW].get(S.ORIGINAL_CODES, []))
            f = (set(codes_of(seg))
                 if seg[S.REVIEW][S.STATUS] != S.STATUS_DELETED else set())
            orig.update(o); final.update(f)
            removed.update(o - f); added.update(f - o)
    return [{
        "code": c,
        "ai_original": orig.get(c, 0),
        "kept_after_review": final.get(c, 0),
        "removed_by_researcher": removed.get(c, 0),
        "added_by_researcher": added.get(c, 0),
        "removal_rate": (round(removed.get(c, 0) / orig[c], 3)
                         if orig.get(c) else None),
        "net_change": final.get(c, 0) - orig.get(c, 0),
    } for c in S.CODES]


def audit_trail(records, limit=None):
    """完整編輯紀錄，一列一個動作。這是「人工複核過」這句話的證據。"""
    rows = []
    for rec in records:
        for seg in list(rec.get(S.SEGMENTS, [])) + list(rec.get(S.DELETED_SEGMENTS, [])):
            for e in seg.get(S.REVIEW, {}).get(S.HISTORY, []):
                rows.append({
                    LOG_TIME: e.get(LOG_TIME, ""),
                    S.RESPONDENT: rec.get(S.RESPONDENT, ""),
                    S.SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                    LOG_ACTION: e.get(LOG_ACTION, ""),
                    LOG_DETAIL: e.get(LOG_DETAIL, ""),
                    LOG_REVIEWER: e.get(LOG_REVIEWER, ""),
                    S.STATUS: seg.get(S.REVIEW, {}).get(S.STATUS, ""),
                    S.QUOTE: (seg.get(S.QUOTE, "") or "")[:40],
                })
    rows.sort(key=lambda r: r[LOG_TIME])
    return rows[-limit:] if limit else rows


def changed_segments(records):
    """所有被改動過的段落，前後對照。校準與論文附錄用。"""
    ensure_all(records)
    rows = []
    for rec in records:
        for seg in list(rec.get(S.SEGMENTS, [])) + list(rec.get(S.DELETED_SEGMENTS, [])):
            r = seg[S.REVIEW]
            o, f = set(r.get(S.ORIGINAL_CODES, [])), set(codes_of(seg))
            if r[S.STATUS] in (S.STATUS_PENDING, S.STATUS_CONFIRMED) and o == f:
                continue
            rows.append({
                S.RESPONDENT: rec.get(S.RESPONDENT, ""),
                S.SEGMENT_ID: seg.get(S.SEGMENT_ID, ""),
                S.STATUS: r[S.STATUS],
                "ai_original_codes": sorted(o),
                "codes_after_review": sorted(f),
                "removed": sorted(o - f),
                "added": sorted(f - o),
                S.QUOTE: seg.get(S.QUOTE, ""),
                "edit_count": len(r.get(S.HISTORY, [])),
            })
    return rows


def methods_facts(records):
    """
    產生方法章節句子所需的事實。**不含顯示文字**——組句交給介面層，
    這樣同一組數字可以輸出任何語言的敘述。
    """
    s = review_stats(records)
    return {**s, "has_data": bool(s["ai_segments"])}
