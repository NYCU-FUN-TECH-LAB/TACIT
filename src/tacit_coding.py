"""
分段編碼（windowed coding pass）與產出量檢查。

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
要去重（見 merge_segments）。

【切在哪裡】

只切在換行（read_docx 把每個發言輪次放一行）與句末標點。切在句子中間會
製造出模型必須猜的殘句，而殘句的引文無法逐字對回原文——引文可回溯是這
套工具的核心保證，不能為了切得整齊而破壞它。

【這件事必須記進 provenance】

窗口大小與重疊長度會改變「模型看到什麼」，換一組參數就是換一次實驗。
code_transcript 回傳的 _meta 裡一定帶著這兩個數字與窗口數，否則結果無法
重現。
"""
import re

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
# 低於此值就示警。取人工密度的五分之一——差到這個程度已經不是保守，
# 是漏讀。實測的失效值是 0.86。
LOW_YIELD_PER_10K = 3.0

FLAG_LOW_YIELD = "low_yield"
FLAG_ONE_PER_DIMENSION = "one_per_dimension"
FLAG_MISSING_DIMENSION = "missing_dimension"
FLAG_TRUNCATED = "truncated"

# 句末標點。中英文都要，因為同一份稿件裡兩種都會出現。
_SENT_END = "。！？!?；;"


def split_units(text):
    """
    先切成不可再分的單位：一行一個發言輪次；過長的行再依句末標點切。

    回傳的每一段都以完整句子結尾，串起來會等於原文（含換行）。
    """
    units = []
    for line in (text or "").split("\n"):
        if not line.strip():
            continue
        if len(line) <= DEFAULT_WINDOW_CHARS:
            units.append(line)
            continue
        # 一個發言輪次就超過一個窗口（訪談稿常見：受訪者一講五分鐘）。
        # 依句末標點切開，標點留在前一段——引文要能對回原文。
        buf = ""
        for piece in re.split(f"([{_SENT_END}]+)", line):
            buf += piece
            if piece and piece[0] in _SENT_END and len(buf) >= MIN_CHUNK_CHARS:
                units.append(buf)
                buf = ""
        if buf.strip():
            units.append(buf)
    return units


def split_transcript(text, window=DEFAULT_WINDOW_CHARS,
                     overlap=DEFAULT_OVERLAP_CHARS):
    """
    切成重疊的窗口。回傳 [(start_unit_index, 窗口文字), ...]。

    短於一個窗口的稿件回傳單一窗口——不切，因為切了只是徒增合併誤差。
    """
    text = text or ""
    if len(text) <= window:
        return [(0, text)] if text.strip() else []

    units = split_units(text)
    if not units:
        return []

    chunks, i = [], 0
    while i < len(units):
        cur, j = [], i
        while j < len(units) and (sum(len(u) + 1 for u in cur) + len(units[j])) <= window:
            cur.append(units[j])
            j += 1
        if not cur:                       # 單一單位就超過窗口：整個放進去
            cur, j = [units[i]], i + 1
        chunks.append((i, "\n".join(cur)))
        if j >= len(units):
            break
        # 往回退到「累積長度剛好超過 overlap」的那個單位，作為下一窗口的起點。
        back, acc = j, 0
        while back > i + 1 and acc < overlap:
            back -= 1
            acc += len(units[back]) + 1
        i = back
    return chunks


def _norm(s):
    """比對用的正規化：去掉空白與標點，只留下實際的字。"""
    return re.sub(r"[\s\W_]+", "", str(s or ""), flags=re.UNICODE).lower()


def _codeset(seg):
    return set(S.codes_of(seg))


MERGE_ACTION = "merged_across_excerpts"


def merge_segments(groups):
    """
    合併各窗口的段落，去掉重疊區產生的重複。

    判定重複只看引文：正規化後其中一個是另一個的子字串。**不要求編碼相同。**

    這一點想了兩輪。同一句話被兩個窗口判成不同維度，看起來像「兩個獨立的
    判斷」，留成兩筆似乎比較保守。但資料模型裡「段落」是一段逐字摘錄，
    留兩筆引文完全相同的段落會造成兩個後果：段落總數被灌水（產出量檢查正是
    讀這個數字），而且共現分析在段落層級會把它算成兩個各自單碼的段落——
    同一段話同時支持兩個維度，那正是共現，卻反而被抹掉了。

    但合併有它的代價：共現關係變成分窗這個動作的產物，而不是模型在單一次
    判斷裡主張的。共現是這套工具的分析輸出之一，不能讓它靜悄悄地被製造
    出來。所以合併時**在該段落的複核歷程留下一筆紀錄**，寫明哪些碼是從
    另一個窗口併進來的。要不要採信這個共現，研究者看得到依據再決定。
    """
    kept = []
    for seg in [s for g in groups for s in (g or [])]:
        q = _norm(seg.get(S.QUOTE))
        if not q:
            continue
        dup = next((k for k in kept
                    if q in _norm(k.get(S.QUOTE)) or _norm(k.get(S.QUOTE)) in q),
                   None)
        if dup is None:
            kept.append(seg)
            continue
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
    for n, seg in enumerate(kept, 1):
        seg[S.SEGMENT_ID] = f"S{n:03d}"
    return kept


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


def merge_respondent(names):
    """受訪者名稱取多數決；平手取最早出現的非空值。"""
    counts = {}
    for n in names:
        n = str(n or "").strip()
        if n and n.lower() not in ("unknown", "unspecified", ""):
            counts[n] = counts.get(n, 0) + 1
    if not counts:
        return "unknown"
    best = max(counts.values())
    for n in names:
        n = str(n or "").strip()
        if counts.get(n) == best:
            return n
    return "unknown"


def code_transcript(transcript, code_one, window=DEFAULT_WINDOW_CHARS,
                    overlap=DEFAULT_OVERLAP_CHARS, on_progress=None):
    """
    分窗編碼並合併。

    code_one(chunk_text, index, total) 要回傳一筆已經過 migrate_record 的
    紀錄（或 None 表示這個窗口失敗）。把呼叫模型這件事留在外面，這支函式
    才測得動——測試給它一個假的 code_one 就能驗證切窗與合併的行為，不必
    有模型在場。

    某個窗口失敗不會中斷整輪：一份稿件切成十五個窗口，因為第七個回了壞
    JSON 就把前面六個的結果丟掉，是把小失敗放大成大失敗。失敗的窗口記在
    _meta.chunk_errors 裡，使用者看得到、也知道結果是不完整的。
    """
    chunks = split_transcript(transcript, window, overlap)
    seg_groups, descs, names, summaries, errors = [], [], [], [], []
    for n, (_, text) in enumerate(chunks):
        if on_progress:
            on_progress(n, len(chunks))
        try:
            rec = code_one(text, n, len(chunks))
        except Exception as e:                       # noqa: BLE001
            errors.append({"chunk": n, "error": f"{type(e).__name__}: {e}"})
            continue
        if not rec:
            errors.append({"chunk": n, "error": "empty"})
            continue
        seg_groups.append(rec.get(S.SEGMENTS) or [])
        descs.append(rec.get(S.DESCRIPTORS) or {})
        names.append(rec.get(S.RESPONDENT))
        s = str(rec.get(S.SUMMARY) or "").strip()
        if s:
            summaries.append(s)

    merged = {
        S.RESPONDENT: merge_respondent(names),
        S.DESCRIPTORS: merge_descriptors(descs),
        S.SEGMENTS: merge_segments(seg_groups),
        S.SUMMARY: "",
        S.META: {"chunking": {"window_chars": window, "overlap_chars": overlap,
                              "n_chunks": len(chunks),
                              "n_ok": len(seg_groups)}},
    }
    if errors:
        merged[S.META]["chunk_errors"] = errors
    merged["_chunk_summaries"] = summaries       # 供外層做綜述用，不寫進檔案
    return merged


def yield_report(transcript, segments, dimensions):
    """
    產出量檢查。**只回報，不修改結果。**

    工具沒有辦法知道「正確答案是幾段」——那正是研究者的判斷。但工具有
    辦法認出幾種「幾乎不可能是真的」的形狀。沒有這一層的話，
    使用者拿到 4 段，畫面上沒有任何跡象顯示這不對勁。
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

    return {"chars": chars, "n_segments": n,
            "per_10k": round(per10k, 2),
            "human_reference_per_10k": HUMAN_DENSITY_PER_10K,
            "by_dimension": seen, "missing": missing, "flags": flags}
