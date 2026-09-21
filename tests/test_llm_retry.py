"""
暫時性錯誤的自動重試，與「模型沒回傳文字／輸出被截斷」的錯誤訊息

要防的失效：用框架建構器草擬時，雲端模型在尖峰時段回
"503 UNAVAILABLE — This model is currently experiencing high demand"，
程式直接失敗；換一顆會先思考的模型後，又只看到
"no JSON object found in the model output"，看不出是被截斷、還是根本沒有輸出。
使用者不知道該重試、換模型、還是調高輸出上限。

這支測試確認：
  1. 503 等暫時性錯誤會自動重試，重試成功就照常回傳
  2. 配額錯誤（429）不重試——重試沒用，量測腳本也要靠它停下來換金鑰
  3. 重試用完仍失敗，拋出 Unavailable，訊息說清楚是服務端的問題
  4. Gemini 沒回傳文字時直接說出 finish reason
  5. 框架草稿失敗時分辨：沒有文字、輸出被截斷、用文字而非 JSON 回答

不需要網路、金鑰或模型：供應者呼叫全部換成假的，等待時間也換掉。
"""
import sys
import types

import tacit_llm as LLM
import tacit_openalex as OA

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def eq(label, got, want):
    ok(label, got == want, f"got={got!r} want={want!r}" if got != want else "")


slept = []
LLM._sleep = lambda s: slept.append(s)
ep = LLM.Endpoint(provider=LLM.GEMINI, model="fake-flash", api_key="k")
_real_gemini = LLM._complete_gemini


def scripted(outcomes):
    """依序回傳或拋出 outcomes 裡的東西，並記錄被呼叫幾次。"""
    state = {"n": 0}

    def fn(*a, **k):
        i = state["n"]
        state["n"] += 1
        o = outcomes[min(i, len(outcomes) - 1)]
        if isinstance(o, Exception):
            raise o
        return o
    return fn, state


try:
    print("=" * 70)
    print("測試 1：503 兩次後成功")
    print("=" * 70)
    busy = LLM.LLMError("503 UNAVAILABLE. This model is currently experiencing high demand.")
    fn, st = scripted([busy, busy, "hello"])
    LLM._complete_gemini = fn
    slept.clear()
    out = LLM.complete(ep, "prompt")
    ok("重試後拿到結果", out == "hello", repr(out))
    ok("總共呼叫 3 次", st["n"] == 3, str(st["n"]))
    ok("依序等待 2、5 秒", slept == list(LLM.RETRY_DELAYS[:2]), str(slept))

    print()
    print("=" * 70)
    print("測試 2：配額錯誤不重試")
    print("=" * 70)
    fn, st = scripted([LLM.RateLimited("429 RESOURCE_EXHAUSTED quota exceeded")])
    LLM._complete_gemini = fn
    slept.clear()
    try:
        LLM.complete(ep, "prompt")
        ok("配額錯誤應該拋出", False)
    except LLM.RateLimited:
        ok("配額錯誤原樣拋出 RateLimited", True)
    ok("只呼叫 1 次", st["n"] == 1, str(st["n"]))
    ok("沒有等待", slept == [], str(slept))

    # 訊息裡同時有 503 與 quota 字樣時，以配額為準（不重試）
    fn, st = scripted([LLM.LLMError("503 but quota exceeded for this project")])
    LLM._complete_gemini = fn
    try:
        LLM.complete(ep, "prompt")
    except LLM.LLMError:
        pass
    ok("含 quota 字樣的錯誤不重試", st["n"] == 1, str(st["n"]))

    print()
    print("=" * 70)
    print("測試 3：非暫時性錯誤不重試")
    print("=" * 70)
    fn, st = scripted([LLM.LLMError("400 INVALID_ARGUMENT: unknown model")])
    LLM._complete_gemini = fn
    slept.clear()
    try:
        LLM.complete(ep, "prompt")
        ok("400 應該拋出", False)
    except LLM.Unavailable:
        ok("400 不應被包成 Unavailable", False)
    except LLM.LLMError:
        ok("400 原樣拋出", True)
    ok("400 只呼叫 1 次", st["n"] == 1, str(st["n"]))

    print()
    print("=" * 70)
    print("測試 4：一直 503，重試用完拋出 Unavailable")
    print("=" * 70)
    fn, st = scripted([busy])
    LLM._complete_gemini = fn
    slept.clear()
    try:
        LLM.complete(ep, "prompt")
        ok("應該拋出 Unavailable", False)
    except LLM.Unavailable as e:
        msg = str(e)
        ok("拋出 Unavailable", True)
        ok("Unavailable 仍是 LLMError（既有的 except 接得住）",
           isinstance(e, LLM.LLMError))
        ok("訊息說是服務端的問題", "provider's side" in msg, msg[:90])
        ok("訊息保留最後一次的原始錯誤", "high demand" in msg)
    ok("嘗試次數 = 1 + 重試次數", st["n"] == len(LLM.RETRY_DELAYS) + 1, str(st["n"]))
    ok("每次重試之間都有等待", slept == list(LLM.RETRY_DELAYS), str(slept))

    print()
    print("=" * 70)
    print("測試 5：地端 HTTP 503 走同一套重試")
    print("=" * 70)
    ep_local = LLM.Endpoint(provider=LLM.OLLAMA, model="fake:7b")
    _real_post = LLM._post_json
    fn, st = scripted([LLM.LLMError("HTTP 503 from http://localhost:11434/api/chat: busy"),
                       {"message": {"content": "local ok"}}])
    LLM._post_json = fn
    slept.clear()
    try:
        out = LLM.complete(ep_local, "prompt")
    finally:
        LLM._post_json = _real_post
    ok("地端 503 重試後成功", out == "local ok", repr(out))
    ok("地端呼叫 2 次", st["n"] == 2, str(st["n"]))
finally:
    LLM._complete_gemini = _real_gemini

print()
print("=" * 70)
print("測試 5b：批次腳本可以把重試間隔拉長")
print("=" * 70)
# 要防的失效：雲端模型在尖峰時段連續回 503，介面預設的 19 秒四次嘗試全部失敗，
# 一支跑一小時的批次腳本因此整批停下來；幾分鐘後同一個指令就正常。
_saved_delays = LLM.RETRY_DELAYS
try:
    got = LLM.set_retry_delays(5, 15, 40, 90)
    eq("設定後生效", LLM.RETRY_DELAYS, (5, 15, 40, 90))
    eq("回傳設定值", got, (5, 15, 40, 90))
    fn, st = scripted([busy] * 3 + ["ok"])
    LLM._complete_gemini = fn
    slept.clear()
    out = LLM.complete(ep, "prompt")
    eq("撐過三次滿載", out, "ok")
    eq("照新的間隔等待", slept, [5, 15, 40])
    ok("總等待時間比預設長", sum(slept) > sum(_saved_delays), f"{sum(slept)}s")
finally:
    LLM.set_retry_delays(*_saved_delays)
    LLM._complete_gemini = _real_gemini
eq("還原成預設", LLM.RETRY_DELAYS, _saved_delays)

print()
print("=" * 70)
print("測試 5c：連線層的抖動也要重試")
print("=" * 70)
# 要防的失效：一輪雲端開放編碼 149 個窗口，有一個掉在
# "[Errno 11004] getaddrinfo failed"——一次 DNS 查詢失敗，下一秒就好了，
# 但那個窗口的編碼整份沒了。只認 HTTP 狀態碼的字樣接不到它。
for _name, _msg in [
    ("DNS 查詢失敗", "[Errno 11004] getaddrinfo failed"),
    ("連線被重設", "ConnectionResetError: Connection reset by peer"),
    ("逾時", "TimeoutError: timed out"),
    ("對方關閉連線", "RemoteDisconnected: Remote end closed connection"),
]:
    ok(f"{_name}算暫時性", LLM._looks_transient(_msg), _msg[:46])

_fn, _st = scripted([LLM.LLMError("[Errno 11004] getaddrinfo failed"), "recovered"])
LLM._complete_gemini = _fn
slept.clear()
try:
    _out = LLM.complete(ep, "prompt")
finally:
    LLM._complete_gemini = _real_gemini
eq("DNS 失敗重試後成功", _out, "recovered")
eq("呼叫了兩次", _st["n"], 2)

# 配額錯誤即使提到 timeout 也不重試——重試沒用，該做的是換專案或等重設
ok("配額錯誤不會因為提到 timeout 而被認成暫時性",
   not LLM._looks_transient("429 quota exceeded, request timed out"))
ok("JSON 錯誤不是暫時性（重傳同一份提示詞沒用）",
   not LLM._looks_transient("JSONDecodeError: Expecting property name"))

print()
print("=" * 70)
print("測試 6：Gemini 沒有回傳文字")
print("=" * 70)
_saved = (LLM.GEMINI_SDK, LLM.genai_client)


class _Resp:
    text = None
    candidates = [types.SimpleNamespace(finish_reason=types.SimpleNamespace(name="MAX_TOKENS"))]


class _Client:
    def __init__(self, api_key=None):
        self.models = types.SimpleNamespace(generate_content=lambda **k: _Resp())


LLM.GEMINI_SDK = LLM.GENAI_NEW
LLM.genai_client = types.SimpleNamespace(Client=_Client)
try:
    LLM.complete(ep, "prompt")
    ok("空白回應應該拋錯", False)
except LLM.Unavailable:
    ok("空白回應不是暫時性錯誤，不該重試", False)
except LLM.LLMError as e:
    msg = str(e)
    ok("空白回應拋出 LLMError", True)
    ok("訊息帶出 finish reason", "MAX_TOKENS" in msg, msg[:90])
    ok("MAX_TOKENS 時提示思考型模型可能用完額度", "thinking" in msg)
finally:
    LLM.GEMINI_SDK, LLM.genai_client = _saved

print()
print("=" * 70)
print("測試 7：框架草稿失敗時分清楚原因")
print("=" * 70)
INDEX = {"W1": {"title": "t"}}


def draft_error(raw):
    try:
        OA.parse_draft(raw, INDEX, "x")
    except OA.DraftError as e:
        return str(e)
    return ""


m_empty = draft_error("")
ok("沒有文字：說沒有回傳", "returned no text" in m_empty, m_empty[:80])
m_none = draft_error(None)
ok("None 也當成沒有文字", "returned no text" in m_none, m_none[:80])

m_prose = draft_error("I'm sorry, I cannot produce that framework today.")
ok("用文字回答：說不是 JSON", "prose" in m_prose, m_prose[:80])
ok("用文字回答：附上開頭", "I'm sorry" in m_prose)

# 被截斷，而且裡面沒有任何 }（不可以只回 "no JSON object found"）
m_cut1 = draft_error('{"framework_name_en": "RI", "dimensions": [{"id": "anticipation", "label_en": "Antic')
ok("截斷（無右括號）：說被切斷", "cut off" in m_cut1, m_cut1[:80])

# 被截斷，但內層已有合上的物件（不可以回誤導人的 "not valid JSON"）
m_cut2 = draft_error('{"dimensions": [{"id": "a", "label_en": "A"}, {"id": "b", "label_en": "B"')
ok("截斷（內層已合上）：仍說被切斷", "cut off" in m_cut2, m_cut2[:80])
ok("截斷訊息建議換模型或減少維度", "fewer dimensions" in m_cut2)

# 括號合上了但內容不合法：維持 not valid JSON
m_bad = draft_error('{"dimensions": [1, 2,]}')
ok("括號完整但格式錯：說不是合法 JSON", "not valid JSON" in m_bad, m_bad[:80])

# 括號計算要跳過字串裡的括號
ok("字串裡的 } 不算合上", OA._unbalanced('{"a": "}"') is True)
ok("完整物件判定為已合上", OA._unbalanced('{"a": {"b": 1}} trailing') is False)

print()
print("=" * 70)
print("結果：全部通過 ✅" if not FAIL else f"結果：{len(FAIL)} 項失敗 ❌")
for f in FAIL:
    print(f"  - {f}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
