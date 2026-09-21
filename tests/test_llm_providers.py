"""
供應者層實跑：把三條「真的送出請求」的路徑對著本機假伺服器走完一次。

為什麼需要這一支
----------------
只測值物件、長度估算與 JSON 擷取的話，tacit_llm 沒被執行到的
正好是 complete()、三個 _complete_*、list_models()、
probe()、complete_json()、make_callable()，也就是**每一行真正跟模型講話的
程式**。論文第 2.4 節整節在講這一層，而任何人拿到程式的第一件事就是裝
Ollama 指一份逐字稿按下去——那正是沒有測試保護的地方。

做法：用標準函式庫起一個本機 HTTP 伺服器假扮 Ollama 與 OpenAI 相容端點，
把每一次請求的路徑、標頭與 JSON 內容都錄下來。因此可以驗證的不只是
「有沒有拿到回覆」，而是**送出去的請求長什麼樣**——num_ctx 有沒有真的寫進
options、金鑰有沒有外洩到不該去的地方、超長提示詞是不是在送出前就被擋下。

不需要網路、不需要金鑰、不需要任何模型服務。Gemini 那條路徑用注入假 SDK
的方式測，因為那個套件是選配的，CI 上不會裝。
"""
import http.server
import json
import os
import sys
import threading
import urllib.error

import tacit_llm as L

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def eq(label, got, want):
    ok(label, got == want, f"got={got!r} want={want!r}" if got != want else "")


MISSING = "<missing>"


def dig(obj, *keys):
    """
    巢狀取值，取不到回 MISSING 而不是拋 KeyError。

    為什麼不直接寫 body["options"]["num_ctx"]：一旦某個欄位在迴歸中消失，
    直接索引會讓整支測試當場崩掉，後面的斷言全部不會執行——於是一個迴歸
    會把其他迴歸藏起來。斷言要能失敗並繼續，測試報告才有診斷價值。
    """
    cur = obj
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        elif isinstance(cur, (list, tuple)) and isinstance(k, int) and \
                -len(cur) <= k < len(cur):
            cur = cur[k]
        else:
            return MISSING
    return cur


# =====================================================================
# 假伺服器
# =====================================================================
class FakeLLMServer:
    """
    本機假模型服務。

    routes: {path: handler}，handler(body_dict) -> (status, response_dict)
    每一次請求都會被記進 self.seen，測試據此檢查「送出去的東西」而不只是
    「收回來的東西」。
    """

    def __init__(self, routes):
        self.routes = routes
        self.seen = []
        outer = self

        class Handler(http.server.BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _dispatch(self, body):
                path = self.path.split("?")[0]
                outer.seen.append({"path": path, "method": self.command,
                                   "headers": dict(self.headers), "body": body})
                fn = outer.routes.get(path)
                if fn is None:
                    return 404, {"error": f"no route {path}"}
                return fn(body)

            def _respond(self, status, payload):
                raw = payload if isinstance(payload, bytes) else \
                    json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                self._respond(*self._dispatch(None))

            def do_POST(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                try:
                    body = json.loads(raw.decode("utf-8")) if raw else None
                except Exception:
                    body = None
                self._respond(*self._dispatch(body))

            def log_message(self, *a):
                pass

        self._srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self._srv.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self._t = threading.Thread(target=self._srv.serve_forever, daemon=True)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *a):
        self._srv.shutdown()
        self._srv.server_close()

    def posts(self, path):
        return [r for r in self.seen if r["path"] == path and r["method"] == "POST"]


def chat_ok(text="hello"):
    return lambda body: (200, {"message": {"role": "assistant", "content": text}})


def oai_ok(text="hello"):
    return lambda body: (200, {"choices": [{"message": {"role": "assistant",
                                                        "content": text}}]})


# =====================================================================
print("=" * 70)
print("測試 1：Ollama — 模型清單")
print("=" * 70)

with FakeLLMServer({"/api/tags": lambda b: (200, {"models": [
        {"name": "nomic-embed-text"},
        {"name": "llama3.1:8b"},
        {"name": "llama3.1:8b-instruct-q4_K_M"}]})}) as s:
    names, note = L.list_models(L.OLLAMA, base_url=s.base)
    ok("查得到已安裝的模型", len(names) == 3, str(names))
    ok("指令微調版排在 base 之前",
       names.index("llama3.1:8b-instruct-q4_K_M") < names.index("llama3.1:8b"),
       str(names))
    ok("embedding 模型排到最後", names[-1] == "nomic-embed-text", str(names))
    ok("提示文字說明清單來源", "installed locally" in note, note)

with FakeLLMServer({"/api/tags": lambda b: (200, {"models": []})}) as s:
    names, note = L.list_models(L.OLLAMA, base_url=s.base)
    eq("沒有模型時回空清單", names, [])
    ok("沒有模型時給得出具體指令", "ollama pull" in note, note)

# 服務沒開：訊息必須能直接指向解法，不能只回 Connection refused
_dead = "http://127.0.0.1:9"
names, note = L.list_models(L.OLLAMA, base_url=_dead)
eq("連不上時退回墊底清單", names, L.FALLBACK_MODELS[L.OLLAMA])
ok("連不上時的訊息告訴使用者怎麼辦", "ollama serve" in note, note[:120])

print()
print("=" * 70)
print("測試 2：Ollama — 生成請求送出去的內容")
print("=" * 70)

with FakeLLMServer({"/api/chat": chat_ok("coded")}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="llama3.1:8b", base_url=s.base,
                    num_ctx=8192, max_tokens=1024)
    out = L.complete(ep, "prompt text", system="sys text", json_mode=True)
    eq("拿得到生成結果", out, "coded")
    body = s.posts("/api/chat")[0]["body"]
    eq("模型名稱有送出", dig(body,"model"), "llama3.1:8b")
    eq("stream 關閉", dig(body,"stream"), False)
    # 這一條是論文第 2.3 節的核心宣稱：num_ctx 必須明確送出，否則 Ollama
    # 會用 4096 的預設值把逐字稿無聲截斷，而且回傳格式完整的 JSON。
    eq("num_ctx 明確寫進 options（靜默截斷的防線）",
       dig(body,"options","num_ctx"), 8192)
    eq("num_predict 明確寫進 options", dig(body,"options","num_predict"), 1024)
    eq("json_mode 會送出 format=json", body.get("format"), "json")
    eq("system 訊息在第一則", dig(body,"messages",0,"role"), "system")
    eq("system 內容正確", dig(body,"messages",0,"content"), "sys text")
    eq("user 內容正確", dig(body,"messages",1,"content"), "prompt text")

with FakeLLMServer({"/api/chat": chat_ok("x")}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
    L.complete(ep, "p", json_mode=False)
    body = s.posts("/api/chat")[0]["body"]
    ok("沒有 system 時不送空的 system 訊息",
       all(m.get("role") != "system" for m in (dig(body,"messages") or [])))
    ok("非 json_mode 不送 format", dig(body,"format") is MISSING)

# 空回覆要炸掉，不能當成「這份逐字稿沒有可編碼內容」
with FakeLLMServer({"/api/chat": lambda b: (200, {"message": {"content": "  "}})}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
    try:
        L.complete(ep, "p")
        ok("空回覆會拋錯", False)
    except L.LLMError as e:
        ok("空回覆會拋錯", True, str(e)[:60])

# 429 要分辨得出來，介面才能建議稍後再試而不是叫使用者換模型
with FakeLLMServer({"/api/chat": lambda b: (429, {"error": "slow down"})}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
    try:
        L.complete(ep, "p")
        ok("429 會拋 RateLimited", False)
    except L.RateLimited:
        ok("429 會拋 RateLimited", True)
    except L.LLMError as e:
        ok("429 會拋 RateLimited", False, f"拋成了 {type(e).__name__}")

with FakeLLMServer({"/api/chat": lambda b: (500, {"error": "boom detail"})}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
    try:
        L.complete(ep, "p")
        ok("500 會拋 LLMError", False)
    except L.RateLimited:
        ok("500 不該被當成限流", False)
    except L.LLMError as e:
        ok("500 會拋 LLMError", True)
        ok("錯誤訊息帶上伺服器回的內容", "boom detail" in str(e), str(e)[:80])

print()
print("=" * 70)
print("測試 3：超長提示詞必須在送出**之前**被擋下")
print("=" * 70)
# 要防的失效：Ollama 的預設 context window 是 4096，遠小於一份逐字稿。伺服器
# 吃不下就直接截斷，不報錯，而且照樣回傳格式完整的 JSON——編碼看起來完成
# 了，實際上有一半的逐字稿從來沒被讀過。守門必須在送出前，而且要真的沒有
# 任何請求發出去，否則模型仍然會在截斷的輸入上跑完一次。
with FakeLLMServer({"/api/chat": chat_ok("should never get here")}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base,
                    num_ctx=2048, max_tokens=1024)
    try:
        L.complete(ep, "字" * 4000)
        ok("超長提示詞會被擋", False)
    except L.ContextOverflow as e:
        ok("超長提示詞會被擋", True)
        ok("錯誤訊息說明會被無聲截斷", "silently truncate" in str(e), str(e)[:80])
        # 這裡不驗特定措辭，驗「可不可以照做」——訊息要嘛給出確切的
        # num_ctx 數字，要嘛明說這顆模型不夠、請切開或換一顆。
        _m = str(e)
        ok("錯誤訊息給得出可以照做的解法",
           ("Set num_ctx to" in _m) or ("split" in _m.lower()), _m[-110:])
    eq("**沒有任何請求真的送出去**", len(s.posts("/api/chat")), 0)

    # num_ctx 小於等於輸出上限是設定錯誤，也要在送出前擋下
    ep2 = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base,
                     num_ctx=1024, max_tokens=2048)
    try:
        L.complete(ep2, "short")
        ok("num_ctx 小於輸出上限會被擋", False)
    except L.ContextOverflow as e:
        ok("num_ctx 小於輸出上限會被擋", True, str(e)[:60])
    eq("仍然沒有請求送出去", len(s.posts("/api/chat")), 0)

# 雲端不做這個檢查：context window 由服務端管理，超過會回明確的錯誤
_g = L.Endpoint(provider=L.GEMINI, model="m", api_key="k")
try:
    L.check_context(_g, "字" * 100000)
    ok("雲端不做本機長度守門", True)
except L.ContextOverflow:
    ok("雲端不做本機長度守門", False)

print()
print("=" * 70)
print("測試 4：OpenAI 相容端點")
print("=" * 70)

with FakeLLMServer({"/models": lambda b: (200, {"data": [
        {"id": "qwen2.5-7b-instruct"}, {"id": "phi-3"}]})}) as s:
    names, note = L.list_models(L.OPENAI_COMPAT, base_url=s.base)
    ok("查得到模型清單", set(names) == {"qwen2.5-7b-instruct", "phi-3"}, str(names))
    ok("提示文字帶上端點位址", s.base in note, note)

with FakeLLMServer({"/chat/completions": oai_ok("done")}) as s:
    ep = L.Endpoint(provider=L.OPENAI_COMPAT, model="qwen", base_url=s.base,
                    max_tokens=512)
    eq("拿得到生成結果", L.complete(ep, "p", system="s", json_mode=True), "done")
    r = s.posts("/chat/completions")[0]
    eq("json_mode 送出 response_format",
       dig(r,"body","response_format"), {"type": "json_object"})
    eq("max_tokens 有送出", dig(r,"body","max_tokens"), 512)
    # 指向 localhost 時不該有 Authorization 標頭——沒有金鑰就不要偽造一個
    ok("沒有金鑰時不送 Authorization",
       "Authorization" not in {k.title(): v for k, v in r["headers"].items()},
       str(list(r["headers"])))

with FakeLLMServer({"/chat/completions": oai_ok("done")}) as s:
    ep = L.Endpoint(provider=L.OPENAI_COMPAT, model="m", base_url=s.base,
                    api_key="sk-test-123")
    L.complete(ep, "p")
    hdr = {k.title(): v for k, v in s.posts("/chat/completions")[0]["headers"].items()}
    eq("有金鑰時送 Bearer 標頭", hdr.get("Authorization"), "Bearer sk-test-123")

# 不是每個地端伺服器都實作 response_format。被拒絕要退回自由文字重送一次，
# 而不是讓整趟分析失敗——事後的 JSON 擷取本來就救得回來。
_state = {"n": 0}


def _picky(body):
    _state["n"] += 1
    if "response_format" in (body or {}):
        return 400, {"error": {"message": "response_format is not supported"}}
    return 200, {"choices": [{"message": {"content": "recovered"}}]}


with FakeLLMServer({"/chat/completions": _picky}) as s:
    ep = L.Endpoint(provider=L.OPENAI_COMPAT, model="m", base_url=s.base)
    try:
        eq("伺服器不支援 response_format 時會退回重送",
           L.complete(ep, "p", json_mode=True), "recovered")
    except L.LLMError as e:
        ok("伺服器不支援 response_format 時會退回重送", False,
           f"整趟分析被一個選配參數弄失敗了：{str(e)[:70]}")
    posts = s.posts("/chat/completions")
    eq("總共送了兩次", len(posts), 2)
    ok("第一次帶 response_format", dig(posts,0,"body","response_format") is not MISSING)
    ok("第二次拿掉 response_format", dig(posts,1,"body","response_format") is MISSING)

with FakeLLMServer({"/chat/completions": lambda b: (200, {"choices": []})}) as s:
    ep = L.Endpoint(provider=L.OPENAI_COMPAT, model="m", base_url=s.base)
    try:
        L.complete(ep, "p")
        ok("沒有 choices 會拋錯", False)
    except L.LLMError:
        ok("沒有 choices 會拋錯", True)

# 400 若與 response_format 無關，不可被誤判成可退回的情形
with FakeLLMServer({"/chat/completions":
                    lambda b: (400, {"error": "model not found"})}) as s:
    ep = L.Endpoint(provider=L.OPENAI_COMPAT, model="m", base_url=s.base)
    try:
        L.complete(ep, "p", json_mode=True)
        ok("無關的 400 會照實拋出", False)
    except L.LLMError as e:
        ok("無關的 400 會照實拋出", "model not found" in str(e), str(e)[:80])
    eq("無關的 400 不會重送", len(s.posts("/chat/completions")), 1)

print()
print("=" * 70)
print("測試 5：金鑰需求依位址而定")
print("=" * 70)
ok("Gemini 一定要金鑰",
   L.Endpoint(provider=L.GEMINI, model="m", api_key="k").needs_key)
ok("Ollama 不要金鑰",
   not L.Endpoint(provider=L.OLLAMA, model="m").needs_key)
ok("OpenAI 相容指向 localhost 不要金鑰",
   not L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
                  base_url="http://localhost:1234/v1").needs_key)
ok("OpenAI 相容指向遠端要金鑰",
   L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
              base_url="https://api.openai.com/v1").needs_key)
try:
    L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
               base_url="https://api.openai.com/v1").validate()
    ok("遠端缺金鑰時 validate 會擋", False)
except L.NotConfigured:
    ok("遠端缺金鑰時 validate 會擋", True)
try:
    L.Endpoint(provider=L.OLLAMA, model="").validate()
    ok("沒選模型時 validate 會擋", False)
except L.NotConfigured:
    ok("沒選模型時 validate 會擋", True)

# describe() 是寫進稽核軌跡的那一行，必須含端點位址才可重現
_d = L.Endpoint(provider=L.OLLAMA, model="llama3.1:8b-instruct-q4_K_M",
                base_url="http://localhost:11434").describe()
ok("稽核字串含供應者、模型與端點",
   _d == "ollama/llama3.1:8b-instruct-q4_K_M@http://localhost:11434", _d)
ok("稽核字串不含金鑰",
   "sk-secret" not in L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
                                 base_url="https://api.openai.com/v1",
                                 api_key="sk-secret").describe())

print()
print("=" * 70)
print("測試 6：probe — 按下開始分析之前就要知道服務有沒有開")
print("=" * 70)
with FakeLLMServer({"/api/tags": lambda b: (200, {"models": [
        {"name": "llama3.1:8b-instruct-q4_K_M"}]})}) as s:
    good = L.Endpoint(provider=L.OLLAMA, model="llama3.1:8b-instruct-q4_K_M",
                      base_url=s.base)
    okk, note = L.probe(good)
    ok("模型裝了就回 True", okk, note)

    bad = L.Endpoint(provider=L.OLLAMA, model="not-installed", base_url=s.base)
    okk, note = L.probe(bad)
    ok("模型沒裝就回 False", not okk)
    ok("並且列出實際裝了什麼", "llama3.1:8b-instruct-q4_K_M" in note, note[:100])

okk, note = L.probe(L.Endpoint(provider=L.OLLAMA, model="m",
                               base_url="http://127.0.0.1:9"))
ok("服務沒開時 probe 回 False", not okk)
ok("並且說明怎麼啟動", "ollama serve" in note, note[:100])

print()
print("=" * 70)
print("測試 7：complete_json — 地端模型解析失敗時的重試策略")
print("=" * 70)
with FakeLLMServer({"/api/chat": chat_ok('prose... {"a": 1, "b": [2,3]} trailing')}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
    eq("能從夾雜文字的回覆裡挖出 JSON",
       L.complete_json(ep, "p"), {"a": 1, "b": [2, 3]})

_calls = {"n": 0}


def _bad_then_good(body):
    _calls["n"] += 1
    if _calls["n"] == 1:
        return 200, {"message": {"content": "sorry, I cannot do that"}}
    return 200, {"message": {"content": '{"ok": true}'}}


_slept = []
_real_sleep = L.time.sleep
L.time.sleep = lambda s_: _slept.append(s_)
try:
    with FakeLLMServer({"/api/chat": _bad_then_good}) as s:
        ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
        eq("第一次解析失敗會重試並成功", L.complete_json(ep, "p"), {"ok": True})
        posts = s.posts("/api/chat")
        eq("總共送了兩次", len(posts), 2)
        # 原樣重送同一個提示詞，得到的多半是同一個壞掉的輸出。重試必須加碼。
        p2 = dig(posts,1,"body","messages",-1,"content")
        ok("重試時加了「只輸出 JSON」的指示",
           "Return a single JSON object and nothing else" in p2, p2[-60:])
        eq("重試時溫度降到 0", dig(posts,1,"body","options","temperature"), 0.0)

    with FakeLLMServer({"/api/chat": chat_ok("no json at all, ever")}) as s:
        ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
        try:
            L.complete_json(ep, "p", retries=1)
            ok("始終解析不出來就拋錯", False)
        except L.LLMError as e:
            ok("始終解析不出來就拋錯", True)
            ok("錯誤訊息說明試了幾次", "attempts" in str(e), str(e)[:80])
        eq("retries=1 表示總共送兩次", len(s.posts("/api/chat")), 2)
finally:
    L.time.sleep = _real_sleep

print()
print("=" * 70)
print("測試 8：make_callable — 分析引擎看到的介面")
print("=" * 70)
# tacit_themes 與 tacit_openalex 收的是 lambda prompt -> text，因此它們完全
# 不知道供應者的存在，也才能用假的可呼叫物件離線測試。
with FakeLLMServer({"/api/chat": chat_ok("themed")}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
    fn = L.make_callable(ep, temperature=0.0, max_tokens=256)
    eq("可呼叫物件回傳純文字", fn("give me themes"), "themed")
    body = s.posts("/api/chat")[0]["body"]
    eq("溫度有傳下去", dig(body,"options","temperature"), 0.0)
    eq("max_tokens 有傳下去", dig(body,"options","num_predict"), 256)

print()
print("=" * 70)
print("測試 9：Gemini 路徑（注入假 SDK，不需要真的安裝）")
print("=" * 70)


class _FakeModel:
    def __init__(self, name, actions=("generateContent",)):
        self.name = name
        self.supported_actions = list(actions)


class _FakeModels:
    def list(self):
        return [_FakeModel("models/gemini-2.5-flash"),
                _FakeModel("models/gemini-2.5-pro"),
                _FakeModel("models/text-embedding-004"),
                _FakeModel("models/gemini-3.0-flash-preview")]

    def generate_content(self, model=None, contents=None, config=None):
        _sdk_seen.append({"model": model, "contents": contents, "config": config})
        return type("R", (), {"text": "gemini said hi"})()


class _FakeClient:
    def __init__(self, api_key=None):
        _sdk_seen.append({"api_key": api_key})
        self.models = _FakeModels()


_sdk_seen = []
_saved = (L.GEMINI_SDK, L.genai_client)
L.GEMINI_SDK = L.GENAI_NEW
L.genai_client = type("M", (), {"Client": _FakeClient})
try:
    names = L._gemini_list("fake-key")
    ok("排除 embedding 模型", not any("embedding" in n for n in names), str(names))
    ok("去掉 models/ 前綴", all(not n.startswith("models/") for n in names))
    names.sort(key=L._gemini_sort_key)
    # preview 是最快被下架的那一種，預設選項應該是明年還會在的那一個
    ok("preview 排到最後", "preview" in names[-1], str(names))
    ok("正式 flash 排第一", names[0] == "gemini-2.5-flash", str(names))

    listed, note = L.list_models(L.GEMINI, api_key="fake-key")
    ok("list_models 走得通", len(listed) == 3, str(listed))
    ok("提示文字說明是 API 查來的", "listed by the API" in note, note)

    eq("沒有金鑰時回墊底清單而不是空的",
       L.list_models(L.GEMINI, api_key="")[0], L.FALLBACK_MODELS[L.GEMINI])

    _sdk_seen.clear()
    ep = L.Endpoint(provider=L.GEMINI, model="gemini-2.5-flash", api_key="fake-key")
    eq("生成走得通", L.complete(ep, "p", system="s"), "gemini said hi")
    ok("金鑰有傳給 SDK", dig(_sdk_seen,0,"api_key") == "fake-key", str(_sdk_seen[0]))
    cfg = dig(_sdk_seen,1,"config") or {}
    eq("system_instruction 有傳", cfg.get("system_instruction"), "s")
    ok("max_output_tokens 有傳", "max_output_tokens" in cfg, str(cfg))
finally:
    L.GEMINI_SDK, L.genai_client = _saved

# 沒裝 SDK 時要講清楚地端不需要它，而不是丟一個 ImportError
_saved = (L.GEMINI_SDK, L.genai_client, L.genai)
L.GEMINI_SDK, L.genai_client, L.genai = None, None, None
try:
    available, note = L.gemini_sdk_note()
    ok("沒裝 SDK 時回報不可用", not available)
    ok("訊息給得出安裝指令", "pip install" in note, note[:90])
    ok("訊息說明只有 Gemini 需要它", "Gem" in note, note[:90])
    eq("沒裝 SDK 時 list_models 回空清單", L.list_models(L.GEMINI, "k")[0], [])
    try:
        L._complete_gemini(L.Endpoint(provider=L.GEMINI, model="m", api_key="k"),
                           "p", "", 0.2, 100)
        ok("沒裝 SDK 時生成會拋 NotConfigured", False)
    except L.NotConfigured:
        ok("沒裝 SDK 時生成會拋 NotConfigured", True)
finally:
    L.GEMINI_SDK, L.genai_client, L.genai = _saved

print()
print("=" * 70)
print("測試 10：限流字樣辨識與 from_env")
print("=" * 70)
for msg in ["429 Too Many Requests", "RESOURCE_EXHAUSTED", "rate limit exceeded",
            "quota exceeded for this project"]:
    ok(f"辨識得出限流：{msg[:28]}", L._looks_rate_limited(msg))
ok("一般錯誤不會被誤判成限流",
   not L._looks_rate_limited("model not found: llama9"))

_env_keys = ("TACIT_PROVIDER", "TACIT_MODEL", "TACIT_BASE_URL", "TACIT_API_KEY",
             "TACIT_NUM_CTX")
_saved_env = {k: os.environ.get(k) for k in _env_keys}
try:
    for k in _env_keys:
        os.environ.pop(k, None)
    ok("沒設定環境變數時回 None", L.from_env() is None)

    os.environ.update({"TACIT_PROVIDER": "ollama", "TACIT_MODEL": "llama3.1:8b",
                       "TACIT_BASE_URL": "http://localhost:11434",
                       "TACIT_NUM_CTX": "16384"})
    e = L.from_env()
    ok("環境變數建得出端點", e is not None)
    if e:
        eq("供應者正確", e.provider, L.OLLAMA)
        eq("模型正確", e.model, "llama3.1:8b")
        eq("num_ctx 有讀進來", e.num_ctx, 16384)

    os.environ["TACIT_PROVIDER"] = "not_a_provider"
    ok("未知供應者回 None 而不是炸掉", L.from_env() is None)
finally:
    for k, v in _saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

print()
print("=" * 70)
print("測試 11：舊版 Gemini SDK 與其餘錯誤分支")
print("=" * 70)
# google-generativeai 已被 Google 停止支援，但既有使用者裝的就是這一套，
# 升級不該讓他們壞掉。兩套 SDK 的 API 完全不同，所以舊路徑要單獨測。


class _OldModelInfo:
    def __init__(self, name, methods=("generateContent",)):
        self.name = name
        self.supported_generation_methods = list(methods)


class _OldGenAI:
    configured = []

    @staticmethod
    def configure(api_key=None):
        _OldGenAI.configured.append(api_key)

    @staticmethod
    def list_models():
        return [_OldModelInfo("models/gemini-2.5-flash"),
                _OldModelInfo("models/embedding-001"),
                _OldModelInfo("models/gemini-1.5-pro", methods=("countTokens",))]

    class GenerativeModel:
        def __init__(self, **kw):
            _old_seen.append(kw)

        def generate_content(self, prompt):
            _old_seen.append({"prompt": prompt})
            return type("R", (), {"text": "old sdk said hi"})()


_old_seen = []
_saved = (L.GEMINI_SDK, L.genai)
L.GEMINI_SDK, L.genai = L.GENAI_OLD, _OldGenAI
try:
    available, note = L.gemini_sdk_note()
    ok("舊 SDK 仍算可用", available)
    ok("但會提醒它已停止支援",
       "google-genai" in note or "deprecat" in note.lower(), note[:90])

    names = L._gemini_list("old-key")
    eq("舊 SDK 只列得出能生成的模型", names, ["gemini-2.5-flash"])

    _old_seen.clear()
    ep = L.Endpoint(provider=L.GEMINI, model="gemini-2.5-flash", api_key="old-key")
    eq("舊 SDK 生成走得通", L.complete(ep, "p", system="s"), "old sdk said hi")
    ok("舊 SDK 有收到金鑰", "old-key" in _OldGenAI.configured,
       str(_OldGenAI.configured))
    ok("舊 SDK 有帶 system_instruction",
       dig(_old_seen, 0, "system_instruction") == "s", str(_old_seen[:1]))

    # 限流要在 SDK 拋例外時就辨識出來，而不是變成一般錯誤
    class _Boom:
        @staticmethod
        def configure(api_key=None):
            pass

        class GenerativeModel:
            def __init__(self, **kw):
                pass

            def generate_content(self, prompt):
                raise RuntimeError("429 RESOURCE_EXHAUSTED: quota exceeded")

    L.genai = _Boom
    try:
        L.complete(ep, "p")
        ok("SDK 拋限流時轉成 RateLimited", False)
    except L.RateLimited:
        ok("SDK 拋限流時轉成 RateLimited", True)
    except L.LLMError as e:
        ok("SDK 拋限流時轉成 RateLimited", False, f"拋成了 {type(e).__name__}")
finally:
    L.GEMINI_SDK, L.genai = _saved

# 模型清單查詢遇到 HTTP 錯誤：要退回墊底清單並說明，不能讓介面空白
with FakeLLMServer({"/api/tags": lambda b: (503, {"error": "unavailable"})}) as s:
    names, note = L.list_models(L.OLLAMA, base_url=s.base)
    eq("清單查詢 503 時退回墊底清單", names, L.FALLBACK_MODELS[L.OLLAMA])
    ok("並且帶上狀態碼", "503" in note, note[:80])

with FakeLLMServer({"/models": lambda b: (200, {"data": []})}) as s:
    names, note = L.list_models(L.OPENAI_COMPAT, base_url=s.base)
    eq("空清單時退回墊底清單", names, L.FALLBACK_MODELS[L.OPENAI_COMPAT])
    ok("並且說明端點回了空清單", "empty model list" in note, note[:80])

with FakeLLMServer({"/chat/completions":
                    lambda b: (200, {"choices": [{"message": {"content": "   "}}]})}) as s:
    ep = L.Endpoint(provider=L.OPENAI_COMPAT, model="m", base_url=s.base)
    try:
        L.complete(ep, "p")
        ok("OpenAI 相容端點的空回覆會拋錯", False)
    except L.LLMError:
        ok("OpenAI 相容端點的空回覆會拋錯", True)

# 挖得出 JSON 但內容壞掉：要重試，最後才拋，且訊息要指向解析失敗
_slept = []
_real_sleep = L.time.sleep
L.time.sleep = lambda s_: _slept.append(s_)
try:
    with FakeLLMServer({"/api/chat": chat_ok('{"a": 1,,, "b"}')}) as s:
        ep = L.Endpoint(provider=L.OLLAMA, model="m", base_url=s.base)
        try:
            L.complete_json(ep, "p", retries=1)
            ok("壞掉的 JSON 最終會拋錯", False)
        except L.LLMError as e:
            ok("壞掉的 JSON 最終會拋錯", True)
            ok("訊息指向解析失敗而不是連線失敗",
               "parse JSON" in str(e), str(e)[:80])
        eq("壞掉的 JSON 也會重試", len(s.posts("/api/chat")), 2)
finally:
    L.time.sleep = _real_sleep

print()
print("=" * 70)
print("測試 12：輸出保留額必須跟著視窗縮放（否則地端模型被自己鎖死）")
print("=" * 70)
# 要防的失效：地端的 max_tokens 若寫死 16384、不隨 num_ctx 變，使用者把
# num_ctx 設成模型支援的 20480，room 就只剩 20480−16384 = 4096，一份逐字稿
# 當然送不出去；num_ctx 設 16384 以下時 room 直接 ≤ 0，**任何輸入都送不出去**。
# 而錯誤訊息只叫他「加大視窗／切開逐字稿／換模型」，沒有一項是真正的原因，
# 使用者因此以為地端模型做不了長逐字稿。
#
# 實測 24 份參考編碼，模型要吐的 JSON 是 1258–2400 token。16384 是需求的 6.8 倍。
for ctx in (4096, 8192, 16384, 20480, 32768, 131072):
    ep = L.Endpoint(provider=L.OLLAMA, model="m", num_ctx=ctx)
    room = ep.num_ctx - ep.max_tokens
    ok(f"num_ctx {ctx} → room 為正（{room}）", room > 0,
       f"保留 {ep.max_tokens}")
    ok(f"num_ctx {ctx} → 保留額放得下最長的編碼結果（2400）",
       ep.max_tokens >= 2400, str(ep.max_tokens))
    # 4096 是 Ollama 的出廠值，本來就小到放不下一份逐字稿——這個工具存在
    # 的理由之一就是要講出這件事。保留額的下限（放得下一份編碼結果）在這裡
    # 會超過視窗的一半，那是正確的：問題出在視窗太小，不是保留額太大。
    if ctx >= 8192:
        ok(f"num_ctx {ctx} → 保留額不超過視窗的一半",
           ep.max_tokens <= ctx / 2, f"{ep.max_tokens}/{ctx}")
    else:
        ok(f"num_ctx {ctx} → 視窗過小時仍保得住輸出（room 只剩 {room}）",
           room > 0 and ep.max_tokens >= 2400, f"{ep.max_tokens}/{ctx}")

# 明確指定時要照指定的走——這是使用者的決定，不可以被覆寫
eq("明確指定 max_tokens 時不被覆寫",
   L.Endpoint(provider=L.OLLAMA, model="m", num_ctx=32768,
              max_tokens=1234).max_tokens, 1234)
# 雲端不受影響：它的視窗是百萬級，固定值沒有問題
eq("Gemini 維持固定的大額度",
   L.Endpoint(provider=L.GEMINI, model="m", api_key="k").max_tokens,
   L.DEFAULT_MAX_TOKENS[L.GEMINI])

# 這一條是使用者實際撞到的情形：20480 的視窗、約 65,000 字元的逐字稿
_ep = L.Endpoint(provider=L.OLLAMA, model="m", num_ctx=20480)
_room = _ep.num_ctx - _ep.max_tokens
ok("20480 的視窗至少給得出 15,000 token 給逐字稿",
   _room >= 15000, str(_room))

# 真的放不下時，訊息要指向保留額這個真正的槓桿
_ep2 = L.Endpoint(provider=L.OLLAMA, model="m", num_ctx=8192, max_tokens=6000)
try:
    L.check_context(_ep2, "x" * 30000)
    ok("保留額過大時仍會擋下", False)
except L.ContextOverflow as e:
    ok("保留額過大時仍會擋下", True)
    ok("訊息指出保留額佔了視窗多少", "output reservation is" in str(e), str(e)[:90])
    ok("訊息給得出可以降到多少", str(L.MIN_OUTPUT_RESERVE) in str(e), str(e)[-120:])

# 保留額合理時，訊息不該再嘮叨保留額——那會誤導
_ep3 = L.Endpoint(provider=L.OLLAMA, model="m", num_ctx=8192)
try:
    L.check_context(_ep3, "x" * 200000)
    ok("提示詞真的過長時仍會擋下", False)
except L.ContextOverflow as e:
    ok("提示詞真的過長時仍會擋下", True)
    ok("保留額合理時不再提降低保留額（避免誤導）",
       "output reservation is" not in str(e), str(e)[:90])

print()
print("=" * 70)
print("測試 13：擋下來的時候要給得出確切數字，不是叫使用者「加大視窗」")
print("=" * 70)
# 要防的失效：訊息若只寫「Raise the context window, split the transcript, or
# choose a model with a longer context」——三條建議沒有一條說得出「加到多少」，
# 也沒有一條知道這顆模型撐不撐得住。使用者因此得出「地端模型做不了長逐字稿」
# 的結論，而實際上他的模型支援 131072，只是 num_ctx 設在 20480。
def _show_server(limit):
    def _h(body):
        return 200, {"model_info": {"general.architecture": "llama",
                                    "llama.context_length": limit}}
    return _h

eq("21306 token 需要 num_ctx 32768", L.required_num_ctx(21306), 32768)
eq("小提示詞用小視窗就夠", L.required_num_ctx(3000), 8192)
ok("大到沒有視窗放得下時回 None", L.required_num_ctx(9_000_000) is None)

with FakeLLMServer({"/api/show": _show_server(131072)}) as s:
    eq("查得到模型的 context 上限",
       L.model_context_limit("llama3.1:8b", s.base), 131072)
    ep = L.Endpoint(provider=L.OLLAMA, model="llama3.1:8b",
                    base_url=s.base, num_ctx=20480)
    try:
        L.check_context(ep, "x" * int(21306 * 3.5))
        ok("超長時仍會擋下", False)
    except L.ContextOverflow as e:
        msg = str(e)
        ok("超長時仍會擋下", True)
        ok("訊息給出確切該設的數字", "32,768" in msg, msg[-150:])
        ok("訊息說明這顆模型撐得住", "131,072" in msg, msg[-150:])
        ok("訊息提醒加大視窗要付記憶體", "memory" in msg, msg[-90:])
        ok("不再只叫使用者「加大視窗」而不給數字",
           "Raise the context window" not in msg)

# 模型真的撐不住時，就不要叫他去設一個設不到的數字
with FakeLLMServer({"/api/show": _show_server(8192)}) as s:
    ep = L.Endpoint(provider=L.OLLAMA, model="tiny", base_url=s.base,
                    num_ctx=8192)
    try:
        L.check_context(ep, "x" * int(21306 * 3.5))
        ok("模型撐不住時仍會擋下", False)
    except L.ContextOverflow as e:
        msg = str(e)
        ok("模型撐不住時仍會擋下", True)
        ok("如實說這顆模型的上限不夠", "not enough" in msg, msg[-140:])
        ok("改建議切開逐字稿或換模型", "split it" in msg, msg[-140:])
        ok("不會叫他去設一個超過上限的數字",
           "Set num_ctx" not in msg, msg[-140:])

# /api/show 查不到就安靜退回，不可以讓守門本身炸掉
ok("查不到模型資訊時回 None 而不是拋錯",
   L.model_context_limit("m", "http://127.0.0.1:9") is None)
with FakeLLMServer({"/api/show": lambda b: (200, {"model_info": {}})}) as s:
    ok("model_info 沒有 context_length 時回 None",
       L.model_context_limit("m", s.base) is None)

print()
print("=" * 70)
print("測試 N：端點描述子要記下換一個就等於換一次實驗的每一樣東西")
print("=" * 70)
# 稿件主張 audit record 記的是完整端點而非只有模型名——但 describe() 本身
# 就只有 provider/model@url，量化等級、num_ctx、temperature 都不在裡面。
_show = {"details": {"quantization_level": "Q4_K_M", "parameter_size": "8.0B",
                     "family": "llama"},
         "model_info": {"llama.context_length": 8192}}
_tags = {"models": [{"name": "llama3.1:8b", "digest": "abc123def456" + "0" * 52},
                    {"name": "other", "digest": "ffff"}]}
with FakeLLMServer({"/api/show": lambda b: (200, _show),
                    "/api/tags": lambda b: (200, _tags)}) as s:
    L._DETAILS_CACHE.clear()
    ep = L.Endpoint(provider=L.OLLAMA, model="llama3.1:8b", base_url=s.base,
                    num_ctx=32768)
    p = ep.provenance(temperature=0.2, window_chars=3000, overlap_chars=300)
    eq("endpoint 字串與 describe() 一致", p.get("endpoint"), ep.describe())
    eq("量化等級來自 /api/show", p.get("quantization_level"), "Q4_K_M")
    eq("參數量", p.get("parameter_size"), "8.0B")
    eq("原生 context", p.get("context_length"), 8192)
    ok("digest 來自 /api/tags 且對到正確的模型",
       str(p.get("digest", "")).startswith("abc123def456"), str(p.get("digest"))[:20])
    eq("num_ctx 記下來", p.get("num_ctx"), 32768)
    eq("temperature 記下來", p.get("temperature"), 0.2)
    eq("分窗參數記下來", (p.get("window_chars"), p.get("overlap_chars")), (3000, 300))
    ok("有記錄時間", bool(p.get("recorded_at")))
    ok("None 的附加值不會寫進去",
       "seed" not in ep.provenance(seed=None))
    ok("describe() 沒有因此改變（bench 續跑靠它比對）",
       ep.describe() == f"ollama/llama3.1:8b@{s.base}")
    # 快取：第二次不再打服務
    calls_before = len(s.seen)
    ep.provenance()
    eq("同一 (url, model) 只問服務一次", len(s.seen), calls_before)

# 服務不在時不能炸：provenance 是附註，不是能擋住分析的東西
L._DETAILS_CACHE.clear()
ep_down = L.Endpoint(provider=L.OLLAMA, model="m", base_url="http://127.0.0.1:9")
p_down = ep_down.provenance(temperature=0.2)
ok("服務不在時仍回傳基本欄位", p_down.get("endpoint") and p_down.get("temperature") == 0.2)
ok("查不到的欄位就不寫，不寫假值", "quantization_level" not in p_down)

ep_g = L.Endpoint(provider=L.GEMINI, model="gemini-3.6-flash", api_key="k")
p_g = ep_g.provenance(temperature=0.2)
eq("雲端端點記 SDK 名稱", p_g.get("sdk"), L.GEMINI_SDK)
ok("雲端端點的 num_ctx 是 None（服務端自己管視窗）", p_g.get("num_ctx") is None)
ok("金鑰絕不出現在描述子裡", "k" != p_g.get("api_key") and "api_key" not in p_g)

print()
print("=" * 70)
print("測試：多餘的逗號不該讓一整個窗口的編碼掉光")
print("=" * 70)
# 要防的失效：雲端模型開放編碼一份 13 個窗口的聽證會逐字稿，第 6 與第 11 窗
# 各因為 "Illegal trailing comma before end of object" 與 "Expecting property
# name enclosed in double quotes" 失敗（後者也是 `}` 前面多一個逗號）。
# 那是 15% 的逐字稿沒有被編碼，原因與模型的判斷完全無關。
for _label, _blob, _want in [
    ("物件尾逗號", '{"a": 1, "b": 2,}', {"a": 1, "b": 2}),
    ("陣列尾逗號", '{"xs": [1, 2, 3,]}', {"xs": [1, 2, 3]}),
    ("巢狀都有", '{"segs": [{"q": "x", "codes": ["a",],}, {"q": "y",},],}',
     {"segs": [{"q": "x", "codes": ["a"]}, {"q": "y"}]}),
    ("換行加尾逗號", "{\n  \"a\": 1,\n  \"b\": [2,\n  ],\n}",
     {"a": 1, "b": [2]}),
    ("本來就合法的不要動", '{"a": [1, 2], "b": {"c": 3}}',
     {"a": [1, 2], "b": {"c": 3}}),
]:
    try:
        ok(_label, L.loads_lenient(_blob) == _want, repr(L.loads_lenient(_blob)))
    except Exception as _e:                                  # noqa: BLE001
        ok(_label, False, f"{type(_e).__name__}: {_e}")

# 字串裡的逗號與括號不可以被改壞——引文是逐字的，動到就是造假
_tricky = '{"quote": "he said, } and then ,]", "n": 1,}'
ok("修補不會動到字串裡的逗號與括號",
   L.loads_lenient(_tricky)["quote"] == "he said, } and then ,]",
   repr(L.loads_lenient(_tricky).get("quote")))

# 修不掉的時候，錯誤訊息要帶出模型到底寫了什麼。
# 這些錯誤會被記進 _meta.chunk_errors。只記「Expecting property
# name enclosed in double quotes: line 32 column 7」——事後沒有任何人查得
# 出來模型寫了什麼，「某個窗口沒編到」永遠只是一個無法追究的事實。
try:
    L.loads_lenient('{"segments": [{"quote": "ok"}], oops: 1}')
    ok("修不掉的應該拋錯", False)
except Exception as _e:                                      # noqa: BLE001
    _m = str(_e)
    ok("錯誤訊息帶出出錯的原文", "model wrote:" in _m, _m[:110])
    ok("原文片段認得出來", "oops" in _m, _m[:110])
    ok("仍然是 JSONDecodeError（既有的 except 接得住）",
       isinstance(_e, __import__("json").JSONDecodeError))

# 只修語法上沒有歧義的那一種。其他一律照樣失敗——猜錯會產出一份看起來
# 正常但內容錯的編碼，比失敗更糟。
for _bad in ('{"a": }', '{"a" 1}', '{"a": [1,', '{"a": "unterminated'):
    try:
        L.loads_lenient(_bad)
        ok(f"壞掉的不該硬猜：{_bad}", False, "竟然解析成功了")
    except Exception:                                        # noqa: BLE001
        ok(f"壞掉的照樣失敗：{_bad}", True)

print()
print("=" * 70)
print("測試：逐字稿有沒有離開這台機器，由位址決定而不是供應者")
print("=" * 70)
# 稿件主張「兩條地端路徑讓資料留在研究者的機器上」，但 OpenAI 相容那條路
# 同時涵蓋 LM Studio（localhost）與 OpenRouter 之類的代理閘道。
# is_local 只看供應者，兩者都回 True；資料管理聲明要寫的不是那個。
for _ep, _want in [
    (L.Endpoint(provider=L.GEMINI, model="g", api_key="k"), "remote"),
    (L.Endpoint(provider=L.OLLAMA, model="m"), "local"),
    (L.Endpoint(provider=L.OLLAMA, model="m",
                  base_url="http://192.168.1.9:11434"), "remote"),
    (L.Endpoint(provider=L.OPENAI_COMPAT, model="m"), "local"),
    (L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
                  base_url="https://openrouter.ai/api/v1"), "remote"),
    (L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
                  base_url="http://127.0.0.1:8080/v1"), "local"),
]:
    ok(f"{_ep.describe()[:46]} → {_want}",
       _ep.data_locality == _want, _ep.data_locality)

_remote = L.Endpoint(provider=L.OPENAI_COMPAT, model="m",
                       base_url="https://openrouter.ai/api/v1")
ok("同一個端點 is_local 仍為 True（它確實走地端那套協定）", _remote.is_local)
ok("**但 data_locality 說 remote**——這兩件事不是同一件",
   _remote.data_locality == "remote")
ok("data_locality 進得了稽核紀錄",
   _remote.provenance().get("data_locality") == "remote",
   str(_remote.provenance().get("data_locality")))
ok("地端端點的稽核紀錄寫 local",
   L.Endpoint(provider=L.OLLAMA, model="m").provenance()
   .get("data_locality") == "local")

print()
print("=" * 70)
print("結果：全部通過 ✅" if not FAIL else f"結果：{len(FAIL)} 項失敗 ❌")
for f in FAIL:
    print(f"  - {f}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
