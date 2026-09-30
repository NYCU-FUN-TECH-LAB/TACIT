"""
分段編碼（windowed coding pass）、產出量檢查，與逐字稿讀取。

【這支模組為什麼存在】

最直接的做法是「整份丟進去、要求模型一次回傳所有編碼段落」。實測的
失效是這樣的：一份 46,730 字元的英文訪談稿，qwen2.5:7b 回傳了 **4 個
段落，每個維度剛好一個**，極性也剛好各一種。同一批人工編碼的中文稿
（21,569 字元）用螢光筆標出 30 段（反思 11、預期 7、參與 7、回應 5）。

四段對三十段不是「模型比較保守」，是三件事疊在一起：

  1. 一次要求模型窮舉一份兩萬字文件裡的所有證據，召回率會塌。這是長輸入
     抽取任務的已知行為，不是哪一顆模型的 bug。
  2. 輸出格式範例裡 segments 陣列只寫了**一個**物件。模型會照抄範例的
     形狀——「每個維度一個」正是照抄的簽名。
  3. 提示詞第 3 條寫「Under-code rather than over-code」。那句話的本意是
     限制**單一段落**上的多重編碼，但模型讀成了全域指示。

第 2、3 點由 app.build_system_prompt 處理。這支模組處理第 1 點：把逐字稿
切成重疊的窗口，每個窗口各跑一次，再合併。窗口小到模型有辦法窮舉。

【為什麼要重疊】

一個橫跨切點的段落，在兩邊都只看得到一半，兩邊都會判成「不完整、不編」。
重疊讓它至少完整出現在一個窗口裡。代價是同一段可能被編兩次，所以合併時
要去重（見 merge_segments）——而去重只在相鄰窗口的重疊區裡做，因為只有
那裡才會出現同一段話的兩份判斷。

【切在哪裡】

只切在換行（read_docx_text 把每個發言輪次放一行）與句末標點。切在句子中間
會製造出模型必須猜的殘句，而殘句的引文無法逐字對回原文——引文可回溯是這
套工具的核心保證，不能為了切得整齊而破壞它。

【這件事必須記進 provenance】

窗口大小與重疊長度會改變「模型看到什麼」，換一組參數就是換一次實驗。
code_transcript 回傳的 _meta 裡一定帶著這兩個數字、窗口數、每個窗口的
字元範圍與產出，以及失敗的窗口與原因，否則結果無法重現、也看不出哪裡
不完整。
"""
import os
import re

import tacit_llm as LLM
import tacit_schema as S

# 窗口大小。3,000 字元 ≈ 中文 3,000 字／英文 500-600 詞，大約是一到兩個
# 發言輪次，模型有辦法逐句掃過去。再大就會開始出現「只挑最顯眼的幾段」。
DEFAULT_WINDOW_CHARS = 3000
# 重疊長度。要放得下一個完整的發言片段，300 字元大約是三到四個句子。
DEFAULT_OVERLAP_CHARS = 300
# 短到這個長度以下就不切了：切了反而讓模型失去上下文。
MIN_CHUNK_CHARS = 800

# 人工編碼密度的參考點。來源是一份實際的中文訪談稿：研究者用螢光筆標出
# 30 段 / 21,569 字元 ≈ 每萬字元 13.9 段。這個數字**不是門檻**，不同的
# 框架、不同的訪談風格會差很多；它只用來判斷「低到不可能是真的」。
HUMAN_DENSITY_PER_10K = 13.9
# 低產出量的門檻：每 10,000 字元 3.0 段。低於此值就示警。
# 略高於人工密度的五分之一（13.9 / 5 ≈ 2.8），取整數 3.0——差到這個程度
# 已經不是保守，是漏讀。實測的失效值是 0.86。
LOW_YIELD_PER_10K = 3.0

FLAG_LOW_YIELD = "low_yield"
FLAG_ONE_PER_DIMENSION = "one_per_dimension"
FLAG_MISSING_DIMENSION = "missing_dimension"
FLAG_TRUNCATED = "truncated"

# 合併時「一段引文包含另一段」的最短長度（正規化後的字元數）。太短的引文
# （"a long time"、「很久」）在任何段落裡都找得到，包含關係不代表同一段話；
# 這麼短的只在完全相同時才合併。
MIN_CONTAINMENT_CHARS = 10

# 呼叫端不該逐窗吞掉的錯誤：視窗不夠、配額用盡、服務沒開、逾時、重試後仍
# 不可用。這些在第一個窗口出現就會在每個窗口出現，逐窗記成「失敗」再繼續
# 只會把真正的原因埋在六十筆 chunk_errors 底下。
FATAL_ERRORS = LLM.FATAL_ERRORS

# 句末標點。中英文都要，因為同一份稿件裡兩種都會出現。
_SENT_END = "。！？!?；;"


def split_units_with_offsets(text):
    """
    先切成不可再分的單位：一行一個發言輪次；過長的行再依句末標點切。

    回傳 [(在原文裡的起始字元位置, 單位文字), ...]。每一段都以完整句子
    結尾，而且逐字來自原文——引文才對得回去，窗口的字元範圍也才算得出來。
    """
    units = []
    pos = 0
    for line in (text or "").split("\n"):
        start = pos
        pos += len(line) + 1
        if not line.strip():
            continue
        if len(line) <= DEFAULT_WINDOW_CHARS:
            units.append((start, line))
            continue
        # 一個發言輪次就超過一個窗口（訪談稿常見：受訪者一講五分鐘）。
        # 依句末標點切開，標點留在前一段——引文要能對回原文。
        buf, buf_start, off = "", start, start
        for piece in re.split(f"([{_SENT_END}]+)", line):
            if not buf:
                buf_start = off
            buf += piece
            off += len(piece)
            if piece and piece[0] in _SENT_END and len(buf) >= MIN_CHUNK_CHARS:
                units.append((buf_start, buf))
                buf = ""
        if buf.strip():
            units.append((buf_start, buf))
    return units


def split_units(text):
    """同 split_units_with_offsets，只回傳文字。"""
    return [u for _, u in split_units_with_offsets(text)]


def plan_windows(text, window=DEFAULT_WINDOW_CHARS, overlap=DEFAULT_OVERLAP_CHARS):
    """
    規劃重疊的窗口。回傳一個 dict 的清單，每個窗口有：

        chunk          序號
        unit_start     起始單位（含）
        unit_end       結束單位（不含）
        char_start     在原文裡的起始字元位置
        char_end       結束字元位置（不含）
        text           窗口文字
        overlap_text   與前一個窗口共有的文字（第一個窗口為空字串）

    短於一個窗口的稿件回傳單一窗口——不切，因為切了只是徒增合併誤差。
    overlap_text 是合併時判斷「這兩份判斷是不是同一段話」的依據：只有落在
    重疊區的引文，才可能同時被兩個窗口看到。
    """
    text = text or ""
    if len(text) <= window:
        if not text.strip():
            return []
        return [{"chunk": 0, "unit_start": 0, "unit_end": None,
                 "char_start": 0, "char_end": len(text), "text": text,
                 "overlap_text": ""}]

    units = split_units_with_offsets(text)
    if not units:
        return []

    plan, i = [], 0
    while i < len(units):
        cur, j = [], i
        while j < len(units) and (sum(len(u) + 1 for _, u in cur)
                                  + len(units[j][1])) <= window:
            cur.append(units[j])
            j += 1
        if not cur:                       # 單一單位就超過窗口：整個放進去
            cur, j = [units[i]], i + 1
        prev_end = plan[-1]["unit_end"] if plan else 0
        shared = [u for _, u in units[i:prev_end]] if i < prev_end else []
        plan.append({"chunk": len(plan), "unit_start": i, "unit_end": j,
                     "char_start": units[i][0],
                     "char_end": units[j - 1][0] + len(units[j - 1][1]),
                     "text": "\n".join(u for _, u in cur),
                     "overlap_text": "\n".join(shared)})
        if j >= len(units):
            break
        # 往回退到「累積長度剛好超過 overlap」的那個單位，作為下一窗口的起點。
        back, acc = j, 0
        while back > i + 1 and acc < overlap:
            back -= 1
            acc += len(units[back][1]) + 1
        i = back
    return plan


def split_transcript(text, window=DEFAULT_WINDOW_CHARS,
                     overlap=DEFAULT_OVERLAP_CHARS):
    """切成重疊的窗口。回傳 [(start_unit_index, 窗口文字), ...]。"""
    return [(p["unit_start"], p["text"]) for p in plan_windows(text, window, overlap)]


def _norm(s):
    """比對用的正規化：去掉空白與標點，只留下實際的字。"""
    return re.sub(r"[\s\W_]+", "", str(s or ""), flags=re.UNICODE).lower()


def _codeset(seg):
    return set(S.codes_of(seg))


MERGE_ACTION = "merged_across_excerpts"


def find_duplicate(kept, origins, q, g, overlap_norm, positional):
    """
    在已保留的段落裡找出「與這一段是同一段話」的那一筆；找不到回 None。

    kept / origins 是平行清單：每筆保留段落的正規化引文與它來自哪個窗口。
    q 是新段落的正規化引文，g 是它的窗口序號。

    規則：
      同一窗口       引文完全相同才算重複（模型把同一段回了兩次）。
      前一個窗口     引文相同，或其中一段包含另一段且較短的那段至少
                     MIN_CONTAINMENT_CHARS 個字；positional 為真時，較短的
                     那段還必須落在兩個窗口的重疊區（overlap_norm）裡。
      其他窗口       不合併。同一句話在稿件裡隔了三十個輪次再出現一次，
                     那是兩段不同的話，各有各的脈絡。

    這個函式不碰任何框架相關的函式，開放編碼與框架編碼共用。
    """
    for k, (kq, ko) in enumerate(zip(kept, origins)):
        if ko == g:
            if kq == q:
                return k
            continue
        if ko != g - 1:
            continue
        if kq == q:
            inner = q
        elif q in kq and len(q) >= MIN_CONTAINMENT_CHARS:
            inner = q
        elif kq in q and len(kq) >= MIN_CONTAINMENT_CHARS:
            inner = kq
        else:
            continue
        if positional and (not overlap_norm or inner not in overlap_norm):
            continue
        return k
    return None


def merge_segments(groups, overlaps=None):
    """
    合併各窗口的段落，去掉重疊區產生的重複。

    groups 依窗口順序排列（失敗的窗口放空清單，序號才對得上）。overlaps
    給的是每個窗口與前一個窗口共有的文字（plan_windows 的 overlap_text）；
    給了就只在重疊區裡合併，沒給就退回「相鄰窗口、引文包含」的規則。

    判定重複只看引文：正規化後相同，或其中一段包含另一段。**不要求編碼相同。**

    這一點想了兩輪。同一句話被兩個窗口判成不同維度，看起來像「兩個獨立的
    判斷」，留成兩筆似乎比較保守。但資料模型裡「段落」是一段逐字摘錄，
    留兩筆引文完全相同的段落會造成兩個後果：段落總數被灌水（產出量檢查正是
    讀這個數字），而且共現分析在段落層級會把它算成兩個各自單碼的段落——
    同一段話同時支持兩個維度，那正是共現，卻反而被抹掉了。

    但合併有它的代價：共現關係變成分窗這個動作的產物，而不是模型在單一次
    判斷裡主張的。共現是這套工具的分析輸出之一，不能讓它靜悄悄地被製造
    出來。所以合併時**在該段落的複核歷程留下一筆紀錄**，寫明哪些碼是從
    另一個窗口併進來的。要不要採信這個共現，研究者看得到依據再決定。

    合併只發生在相鄰窗口的重疊區。稿件裡相隔很遠的兩處說了同一句話，
    那是兩段各有脈絡的話，不是同一段的兩份判斷。
    """
    kept, kept_q, origins = [], [], []
    positional = overlaps is not None
    for g, group in enumerate(groups or []):
        ov = _norm(overlaps[g]) if positional and g < len(overlaps) else ""
        for seg in (group or []):
            q = _norm(seg.get(S.QUOTE))
            if not q:
                continue
            k = find_duplicate(kept_q, origins, q, g, ov, positional)
            if k is None:
                kept.append(seg)
                kept_q.append(q)
                origins.append(g)
                continue
            dup = kept[k]
            # 併碼：以 (維度, 極性, 理由) 為準，跟 schema 的去重規則一致
            have = {(c.get(S.DIMENSION), c.get(S.POLARITY),
                     str(c.get(S.RATIONALE) or "").strip())
                    for c in dup.get(S.CODES_F) or []}
            before = _codeset(dup)
            for c in seg.get(S.CODES_F) or []:
                key = (c.get(S.DIMENSION), c.get(S.POLARITY),
                       str(c.get(S.RATIONALE) or "").strip())
                if key not in have:
                    dup.setdefault(S.CODES_F, []).append(c)
                    have.add(key)
            added = sorted(_codeset(dup) - before)
            if added:
                rv = dup.setdefault(S.REVIEW, {})
                rv.setdefault(S.STATUS, S.STATUS_PENDING)
                rv.setdefault(S.SOURCE, S.SOURCE_AI)
                rv.setdefault(S.ORIGINAL_CODES, sorted(before))
                rv.setdefault(S.HISTORY, []).append({
                    "time": "", "reviewer": "", "action": MERGE_ACTION,
                    "detail": "codes from another excerpt: " + ", ".join(added)})
            # 留下比較完整的原文與標題
            if len(str(seg.get(S.FULL_TEXT) or "")) > len(str(dup.get(S.FULL_TEXT) or "")):
                dup[S.FULL_TEXT] = seg[S.FULL_TEXT]
            if len(str(seg.get(S.QUOTE) or "")) > len(str(dup.get(S.QUOTE) or "")):
                dup[S.QUOTE] = seg[S.QUOTE]
                kept_q[k] = _norm(seg[S.QUOTE])
    for n, seg in enumerate(kept, 1):
        seg[S.SEGMENT_ID] = f"S{n:03d}"
    return kept


def dedupe_segments(segments):
    """
    單次送出（不分窗）的結果去重：引文完全相同的段落只留一筆，碼取聯集。
    分窗的合併規則套在單一窗口上就是這個。
    """
    return merge_segments([list(segments or [])])


def merge_descriptors(parts):
    """
    合併各窗口讀到的屬性。第一個非 unspecified 的值勝出。

    不做多數決：屬性通常只在稿件的某一處被說出來（多半是開頭的自我介紹），
    只有那一個窗口讀得到，其他窗口照規則會填 unspecified。多數決會讓
    unspecified 贏。
    """
    out = S.blank_descriptors()
    for d in parts:
        for k in S.DESCRIPTOR_KEYS:
            v = (d or {}).get(k)
            if v and v != S.UNSPECIFIED and out.get(k) in (None, S.UNSPECIFIED):
                out[k] = v
        b = str((d or {}).get(S.DESCRIPTOR_BASIS) or "").strip()
        if b and not str(out.get(S.DESCRIPTOR_BASIS) or "").strip():
            out[S.DESCRIPTOR_BASIS] = b
    return out


# 模型「沒有讀到名字」時會填的東西：提示詞裡的佔位字樣被照抄回來、通用的
# 稱謂、或各種寫法的「不明」。這些都不是名字。
_PLACEHOLDER_NAMES = {
    "", "unknown", "unspecified", "unnamed", "none", "n/a", "na", "null",
    "respondent", "the respondent", "interviewee", "the interviewee",
    "speaker", "the speaker", "participant", "the participant",
    "未指定", "不明", "未知", "受訪者", "受訪人", "無",
}


def is_placeholder_name(name):
    """這個「名字」是不是模型交不出名字時的填充物。"""
    s = str(name or "").strip().lower().strip("「」\"'")
    if s in _PLACEHOLDER_NAMES:
        return True
    return ("as named in" in s or s.startswith("the respondent")
            or s.startswith("the person speaking"))


def merge_respondent(names):
    """受訪者名稱取多數決；平手取最早出現的非空值。佔位字樣不算名字。"""
    counts = {}
    for n in names:
        n = str(n or "").strip()
        if n and not is_placeholder_name(n):
            counts[n] = counts.get(n, 0) + 1
    if not counts:
        return "unknown"
    best = max(counts.values())
    for n in names:
        n = str(n or "").strip()
        if counts.get(n) == best:
            return n
    return "unknown"


def respondent_from_filename(name):
    """
    用檔名的主幹當受訪者識別碼。

    名字由模型從文本裡讀，讀不到就填佔位字樣，兩份不同文件會撞成同一個
    識別碼，而紀錄、逐字稿與抽樣框都用這個字串當鍵。檔名是研究者自己取的，
    每份不同，而且不會被提示詞注入改掉。
    """
    stem = os.path.splitext(os.path.basename(str(name or "")))[0].strip()
    return stem or "unknown"


def _window_error(e, n, total, p):
    """把窗口的位置寫進致命錯誤的訊息，型別不變（呼叫端既有的 except 接得住）。"""
    msg = (f"window {n + 1} of {total} (characters "
           f"{p['char_start']:,}–{p['char_end']:,}): {e}")
    try:
        return type(e)(msg)
    except Exception:                                    # noqa: BLE001
        return LLM.LLMError(msg)


def code_transcript(transcript, code_one, window=DEFAULT_WINDOW_CHARS,
                    overlap=DEFAULT_OVERLAP_CHARS, on_progress=None,
                    respondent=None):
    """
    分窗編碼並合併。

    code_one(chunk_text, index, total) 要回傳一筆已經過 migrate_record 的
    紀錄（或 None 表示這個窗口失敗）。把呼叫模型這件事留在外面，這支函式
    才測得動——測試給它一個假的 code_one 就能驗證切窗與合併的行為，不必
    有模型在場。

    respondent 給了就用它（通常是檔名主幹），不給才用各窗口讀到的名字
    取多數決。

    某個窗口回了壞 JSON 不會中斷整輪：一份稿件切成十五個窗口，因為第七個
    壞了就把前面六個的結果丟掉，是把小失敗放大成大失敗。失敗的窗口記在
    _meta.chunk_errors（序號、字元範圍、原因），_meta.incomplete_windows
    記失敗數，使用者看得到、也知道結果是不完整的。

    但視窗不夠、配額用盡、服務沒開、逾時這幾種是**整批**的問題（見
    FATAL_ERRORS）：直接拋出，訊息前面加上是哪個窗口。
    """
    plan = plan_windows(transcript, window, overlap)
    total = len(plan)
    groups = [[] for _ in plan]
    overlaps = [p["overlap_text"] for p in plan]
    descs, names, summaries, errors, windows = [], [], [], [], []
    n_ok = 0
    for p in plan:
        n = p["chunk"]
        if on_progress:
            on_progress(n, total)
        info = {"chunk": n, "chars": len(p["text"]),
                "start_char": p["char_start"], "end_char": p["char_end"]}
        try:
            rec = code_one(p["text"], n, total)
        except FATAL_ERRORS as e:
            raise _window_error(e, n, total, p) from e
        except Exception as e:                       # noqa: BLE001
            reason = f"{type(e).__name__}: {e}"
            errors.append({**info, "error": reason})
            windows.append({**info, "status": "failed", "segments": 0})
            continue
        if not rec:
            errors.append({**info, "error": "empty"})
            windows.append({**info, "status": "empty", "segments": 0})
            continue
        segs = rec.get(S.SEGMENTS) or []
        groups[n] = segs
        n_ok += 1
        windows.append({**info, "status": "ok" if segs else "no_segments",
                        "segments": len(segs),
                        "per_10k": round(len(segs) / len(p["text"]) * 10000, 2)
                        if p["text"] else 0.0})
        descs.append(rec.get(S.DESCRIPTORS) or {})
        names.append(rec.get(S.RESPONDENT))
        s = str(rec.get(S.SUMMARY) or "").strip()
        if s:
            summaries.append(s)

    merged = {
        S.RESPONDENT: (str(respondent).strip() if respondent
                       else merge_respondent(names)),
        S.DESCRIPTORS: merge_descriptors(descs),
        S.SEGMENTS: merge_segments(groups, overlaps),
        S.SUMMARY: "",
        S.META: {"chunking": {"window_chars": window, "overlap_chars": overlap,
                              "n_chunks": total,
                              "n_ok": n_ok,
                              "n_failed": len(errors),
                              "n_no_segments": sum(
                                  1 for w in windows if w["status"] == "no_segments"),
                              "merge_rule": "adjacent_overlap",
                              "windows": windows}},
    }
    if respondent:
        merged[S.META]["respondent_source"] = "caller"
    if errors:
        merged[S.META]["chunk_errors"] = errors
        merged[S.META]["incomplete_windows"] = len(errors)
    merged["_chunk_summaries"] = summaries       # 供外層做綜述用，不寫進檔案
    return merged


def yield_report(transcript, segments, dimensions):
    """
    產出量檢查。**只回報，不修改結果。**

    工具沒有辦法知道「正確答案是幾段」——那正是研究者的判斷。但工具有
    辦法認出幾種「幾乎不可能是真的」的形狀。沒有這一層的話，
    使用者拿到 4 段，畫面上沒有任何跡象顯示這不對勁。

    另外數引文對不回原文的段落：那不是產出量的問題，但同樣是研究者在
    複核之前就該知道的數字。
    """
    chars = len(transcript or "")
    n = len(segments or [])
    per10k = (n / chars * 10000) if chars else 0.0

    seen = {}
    for s in segments or []:
        for c in S.codes_of(s):
            d = S.split_code(c)[0] if "-" in str(c) else c
            seen[d] = seen.get(d, 0) + 1

    flags = []
    if chars >= 2000 and per10k < LOW_YIELD_PER_10K:
        flags.append(FLAG_LOW_YIELD)
    # 「每個維度剛好一段」是照抄輸出範例的簽名，不是分析結果。實測值就是
    # 這個形狀：4 個維度、4 段、各一。
    dims = list(dimensions or [])
    if dims and n == len(dims) and n >= 2 and \
            all(seen.get(d) == 1 for d in dims):
        flags.append(FLAG_ONE_PER_DIMENSION)
    missing = [d for d in dims if not seen.get(d)]
    if missing and chars >= 5000:
        flags.append(FLAG_MISSING_DIMENSION)

    tnorm = _norm(transcript) if transcript else ""
    unmatched = sum(1 for s in segments or []
                    if _norm(s.get(S.QUOTE)) and _norm(s.get(S.QUOTE)) not in tnorm)

    return {"chars": chars, "n_segments": n,
            "per_10k": round(per10k, 2),
            "human_reference_per_10k": HUMAN_DENSITY_PER_10K,
            "low_yield_threshold_per_10k": LOW_YIELD_PER_10K,
            "by_dimension": seen, "missing": missing, "flags": flags,
            "n_unmatched_quotes": unmatched}


def summarize_drops(dropped):
    """被丟棄的碼依原因計數，例如 {"unknown_dimension": 3, "duplicate": 1}。"""
    out = {}
    for d in dropped or []:
        r = str((d or {}).get("reason") or "unknown")
        out[r] = out.get(r, 0) + 1
    return out


def attach_yield(rec, transcript, dimensions, dropped=None):
    """
    把產出量診斷與被丟棄的碼寫進紀錄的 _meta，回傳產出量報告。

    要在存檔**之前**呼叫：這些是紀錄的一部分，不是畫面上的一次性提示。
    寫入 _meta.yield（報告）、_meta.low_yield（有沒有觸發低產出量警示）、
    _meta.dropped（逐筆）與 _meta.drop_summary（依原因計數）。
    """
    yr = yield_report(transcript, rec.get(S.SEGMENTS) or [], dimensions)
    meta = rec.setdefault(S.META, {})
    meta["yield"] = yr
    meta["low_yield"] = FLAG_LOW_YIELD in yr["flags"]
    meta["dropped"] = list(dropped or [])
    meta["drop_summary"] = summarize_drops(dropped)
    return yr


# =====================================================================
# 逐字稿讀取
# =====================================================================
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_MC = "{http://schemas.openxmlformats.org/markup-compatibility/2006}"

# 這些元素底下的文字不進逐字稿：追蹤修訂裡被刪掉的字、被搬走的字、
# 相容性標記的備援版本（與正式版本重複）、圖形裡的文字方塊。
_SKIP_TAGS = {_W + "del", _W + "moveFrom", _MC + "Fallback", _W + "txbxContent"}

_SPEAKER_HEADERS = {"講者", "發言人", "說話者", "speaker", "name", "姓名"}
_CONTENT_HEADERS = {"內容", "逐字稿", "發言", "發言內容", "content", "text",
                    "utterance", "transcript", "statement"}


def _collect_text(elm, out):
    for ch in elm.iterchildren():
        tag = ch.tag
        if tag in _SKIP_TAGS:
            continue
        if tag == _W + "t":
            out.append(ch.text or "")
        elif tag == _W + "tab":
            out.append("\t")
        elif tag in (_W + "br", _W + "cr"):
            out.append("\n")
        elif tag == _W + "tbl":
            continue
        else:
            _collect_text(ch, out)


def _para_text(p):
    """
    一個段落的文字：一般的字、追蹤修訂裡**新增**的字（w:ins）、超連結裡的
    字都算；刪掉的字不算。
    """
    out = []
    _collect_text(p, out)
    return "".join(out)


def _cell_text(tc):
    paras = [_para_text(p).strip() for p in tc.iterchildren(_W + "p")]
    nested = []
    for sdt in tc.iterchildren(_W + "sdt"):
        for inner in sdt.iterchildren(_W + "sdtContent"):
            paras += [_para_text(p).strip() for p in inner.iterchildren(_W + "p")]
            for tbl in inner.iterchildren(_W + "tbl"):
                nested += _table_lines(tbl)
    for tbl in tc.iterchildren(_W + "tbl"):
        nested += _table_lines(tbl)
    return " ".join(t for t in paras if t), nested


def _table_lines(tbl):
    """
    表格 → 每一列一行。

    儲存格直接讀 w:tc，每一格只出現一次——合併的儲存格在檔案裡本來就只有
    一格，照格線展開才會把同一段文字重複好幾次。巢狀表格的列接在所在列
    的後面。

    表頭同時有「講者」與「內容」兩欄時，當成逐字稿表格，輸出
    【講者】內容；否則每列的非空儲存格以 tab 接起來。
    """
    rows = list(tbl.iterchildren(_W + "tr"))
    if not rows:
        return []
    parsed = []
    for tr in rows:
        cells, nested = [], []
        for tc in tr.iterchildren(_W + "tc"):
            txt, inner = _cell_text(tc)
            cells.append(txt)
            nested += inner
        parsed.append((cells, nested))

    headers = [c.strip().lower() for c in parsed[0][0]]
    si = next((i for i, h in enumerate(headers) if h in _SPEAKER_HEADERS), None)
    ci = next((i for i, h in enumerate(headers) if h in _CONTENT_HEADERS), None)

    lines = []
    if si is not None and ci is not None and si != ci:
        for cells, nested in parsed[1:]:
            sp = cells[si] if si < len(cells) else ""
            tx = cells[ci] if ci < len(cells) else ""
            if tx:
                lines.append(f"【{sp}】{tx}" if sp else tx)
            lines += nested
        return lines
    for cells, nested in parsed:
        vals = [c for c in cells if c]
        if vals:
            lines.append("\t".join(vals))
        lines += nested
    return lines


def _body_lines(container):
    """依文件順序走過段落、表格與內容控制項。"""
    lines = []
    for child in container.iterchildren():
        tag = child.tag
        if tag == _W + "p":
            t = _para_text(child)
            if t.strip():
                lines.append(t)
        elif tag == _W + "tbl":
            lines += _table_lines(child)
        elif tag == _W + "sdt":
            for inner in child.iterchildren(_W + "sdtContent"):
                lines += _body_lines(inner)
    return lines


def read_docx_text(path_or_file):
    """
    把一份 .docx 讀成逐字稿文字：一行一個段落或表格列，依文件順序。

    讀什麼：內文的段落與表格（含巢狀表格與內容控制項裡的），追蹤修訂裡
    新增的文字算進去、刪除的不算。表格每一列輸出一次，儲存格以 tab 接起來；
    表頭同時有講者欄與內容欄（Speaker | Text、講者 | 內容…）的表格輸出
    【講者】內容，這是信度模組認得的發言標記。

    不讀什麼：頁首、頁尾、註腳、章節附註、註解、文字方塊。

    接受檔案路徑或已開啟的檔案物件。不是 .docx 的檔案拋 ValueError，
    訊息說明檔名與原因。
    """
    import docx
    name = getattr(path_or_file, "name", None) or str(path_or_file)
    try:
        doc = docx.Document(path_or_file)
    except Exception as e:                                   # noqa: BLE001
        raise ValueError(f"{os.path.basename(str(name))}: not a readable Word "
                         f"(.docx) document ({type(e).__name__}: {e})") from e
    return "\n".join(_body_lines(doc.element.body))
