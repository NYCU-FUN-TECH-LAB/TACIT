"""
tacit_llm.py — 語言模型供應者抽象層
=====================================================================
把「呼叫哪一個模型」與「怎麼呼叫」從介面與分析引擎裡拆出來。

支援三種供應者：

    gemini          Google Gemini（雲端，需金鑰）
    ollama          Ollama 本機服務（http://localhost:11434）
    openai_compat   任何 OpenAI 相容端點——LM Studio、llama.cpp server、
                    vLLM、LocalAI、text-generation-webui、OpenRouter…

為什麼要有本機路徑
------------------
訪談逐字稿是人類受試者資料。多數機構的研究倫理審查（IRB）允許把逐字稿
交給雲端服務的前提，是資料處理協議與去識別化程度都寫進了送審文件；
沒寫進去就不能送。地端模型讓「資料完全不離開研究者的電腦」變成可勾選的
選項，而不是只能放棄使用工具。

第二個理由是可重現性。雲端模型會被下架（Gemini 2.5 Flash 就是），
版本號背後的權重也會無聲更動。地端模型有固定的權重檔與雜湊值，
論文寫「llama3.1:70b-instruct-q4_K_M」時，三年後的人還跑得出可比較的結果。

實作限制：只用標準函式庫
------------------------
本機供應者一律走 urllib，不引入 openai / httpx / requests。
理由是相依愈少，別人愈容易把程式跑起來；而 /v1/chat/completions
與 Ollama 的 /api/chat 都只是單純的 POST + JSON，值不上一個新相依。
Gemini 走官方 SDK google-genai，列在 requirements.txt 的必要清單裡：
不是每個人都有 Ollama，沒有本機模型的人裝完就要能直接用 Gemini。
匯入仍然包在 try 裡——手動建的環境少裝了它，程式照樣能開，地端供應者
照樣能用，介面會說缺什麼並提供一鍵安裝。
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

# Gemini SDK 有新舊兩套。
#
# Google 已停止支援 google-generativeai，改推 google-genai，兩者的 API
# 完全不同（前者 configure + GenerativeModel，後者 Client.models）。
# 這裡兩套都支援、優先用新的：只裝了舊套件的既有使用者不該因為升級而
# 壞掉，新使用者也不該被引導去裝一個已經停止維護的套件。
GENAI_NEW = "google-genai"
GENAI_OLD = "google-generativeai"

genai_client = None       # 新版 google.genai
genai = None              # 舊版 google.generativeai
GEMINI_SDK = None

try:
    from google import genai as genai_client      # noqa: F811
    GEMINI_SDK = GENAI_NEW
except Exception:                                    # pragma: no cover
    genai_client = None

if GEMINI_SDK is None:
    try:
        import warnings
        with warnings.catch_warnings():
            # 舊套件在匯入時就印棄用警告。使用者對此無能為力（他們裝的
            # 就是這一套），把警告丟到主控台只是雜訊；真正該講的話由
            # gemini_sdk_note() 在介面上說。
            warnings.simplefilter("ignore")
            import google.generativeai as genai     # noqa: F811
        GEMINI_SDK = GENAI_OLD
    except Exception:                                # pragma: no cover
        genai = None

HAS_GEMINI = GEMINI_SDK is not None


def gemini_sdk_note():
    """介面上要顯示的 SDK 狀態。回傳 (可用嗎, 訊息)。"""
    if GEMINI_SDK == GENAI_NEW:
        return True, ""
    if GEMINI_SDK == GENAI_OLD:
        return True, ("Using the legacy google-generativeai SDK, which Google "
                      "no longer maintains. It still works. To move to the "
                      "supported one: pip install google-genai")
    return False, (f"The Google SDK is missing from this environment, so the "
                   f"Gemini provider cannot run. Install it with: "
                   f"pip install {GENAI_NEW}  (it is listed in requirements.txt; "
                   f"the launchers install it automatically.)")


def install_gemini_sdk(timeout=600):
    """
    把 Gemini SDK 裝進**目前這個直譯器的環境**。回傳 (成功嗎, 輸出)。

    為什麼這個函式必須存在：這個程式是雙擊啟動器打開的，畫面上沒有任何
    地方可以打指令。介面只印一行 `pip install google-genai` 的話，
    對一個不寫程式的研究者而言那是死路——他知道要做什麼，但沒有地方做。

    SDK 是必要相依，啟動器會自動安裝；這個函式留給手動建的環境、
    或是沒有裝到 SDK 的既有虛擬環境。

    用 sys.executable 而不是裸的 `pip`：啟動器建的是專用虛擬環境，
    裸 pip 可能指到系統 Python，裝完之後這支程式仍然找不到。
    """
    import subprocess
    import sys
    try:
        p = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--disable-pip-version-check",
             GENAI_NEW],
            capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (p.stderr or "")
        if p.returncode != 0:
            return False, out
    except Exception as e:                                   # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"
    # 裝完了也**不要**在同一個行程裡宣稱可用：模組層級的偵測是在啟動時
    # 做的，import 快取不會因為 pip 跑完就更新。要求重新啟動才誠實。
    return True, out


# =====================================================================
# 1. 供應者定義
# =====================================================================
GEMINI = "gemini"
OLLAMA = "ollama"
OPENAI_COMPAT = "openai_compat"

PROVIDERS = [GEMINI, OLLAMA, OPENAI_COMPAT]

# 地端供應者：不需要金鑰、資料不離開本機。這份清單被介面用來決定
# 要不要顯示「資料不會離開這台電腦」的提示，不要只靠字串比對。
LOCAL_PROVIDERS = {OLLAMA, OPENAI_COMPAT}

DEFAULT_BASE_URL = {
    GEMINI: "",
    OLLAMA: "http://localhost:11434",
    OPENAI_COMPAT: "http://localhost:1234/v1",       # LM Studio 的預設埠
}

# 常見地端伺服器的預設位址，只作為介面上的提示，不影響邏輯。
KNOWN_ENDPOINTS = [
    ("LM Studio", "http://localhost:1234/v1"),
    ("llama.cpp server", "http://localhost:8080/v1"),
    ("vLLM", "http://localhost:8000/v1"),
    ("LocalAI", "http://localhost:8080/v1"),
    ("Ollama (OpenAI 相容介面)", "http://localhost:11434/v1"),
]

# 寫死的模型清單一定會過期，所以正常路徑一律**跟服務要清單**；
# 這幾份只是拿不到清單時的墊底（沒填金鑰、服務沒開、API 改版）。
FALLBACK_MODELS = {
    GEMINI: ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3-pro"],
    OLLAMA: [],
    OPENAI_COMPAT: [],
}

# 地端模型的輸出上限。Gemini 給 65536 沒問題（它的視窗是百萬級），但一顆
# 8B 的地端模型被要求生 65536 個 token，多數伺服器會直接把 KV cache 開到
# 爆記憶體。
#
# 要防的失效：地端這兩項若寫死 16384、**不隨 num_ctx 縮放**。使用者把
# num_ctx 設成模型實際支援的 20480，room 就變成 20480−16384 = 4096，
# 一份 21306 token 的逐字稿當然送不出去——而錯誤訊息只叫他「加大視窗、
# 切開逐字稿、或換一顆模型」，沒有一項是真正的原因。num_ctx 若設 16384
# 以下，room 直接是 0 或負數，**任何逐字稿都送不出去**。
#
# 實測 24 份參考編碼，模型要吐的 JSON 是 1258–2400 token（中位 1536）。
# 16384 是實際最大需求的 6.8 倍。這個保留額是在保護記憶體，不是在保護
# 輸出完整性，所以它應該跟著視窗縮放，而不是一個絕對值。
DEFAULT_MAX_TOKENS = {
    GEMINI: 65536,
    OLLAMA: 16384,
    OPENAI_COMPAT: 16384,
}

# 地端輸出保留額的下限與上限。下限要放得下最長的那一份編碼結果（實測
# 2400，取 3072 留餘裕）；上限避免在超大視窗上白白鎖住一堆空間。
MIN_OUTPUT_RESERVE = 3072
MAX_OUTPUT_RESERVE = 8192


def default_max_tokens(provider, num_ctx=None):
    """
    這個端點該保留多少輸出額度。

    雲端沿用固定值（服務端自己管視窗）。地端則取視窗的四分之一，夾在
    MIN/MAX 之間——保留額必須跟著視窗走，否則小視窗的模型會被自己的
    保留額鎖死，而那跟模型的能力無關。
    """
    if provider == GEMINI or not num_ctx:
        return DEFAULT_MAX_TOKENS[provider]
    return max(MIN_OUTPUT_RESERVE,
               min(MAX_OUTPUT_RESERVE, int(num_ctx) // 4))

# Ollama 的預設 context window 是 4096——遠小於一份逐字稿。
# 超出的部分會被**無聲截斷**，模型只讀到訪談的後半段，卻照樣回傳
# 格式完整的 JSON。這是本專案在地端最危險的失效模式：結果看起來
# 正常，實際上有一半的資料從來沒被讀過。所以一律明確指定 num_ctx，
# 並在送出前估算長度、超過就擋下來。
DEFAULT_NUM_CTX = 32768


class LLMError(RuntimeError):
    """供應者呼叫失敗的共同基底。"""


class NotConfigured(LLMError):
    """缺金鑰、缺模型名稱、或本機服務沒開。"""


class RateLimited(LLMError):
    """配額或速率上限。呼叫端應該整批停下，而不是繼續重試。"""


class ContextOverflow(LLMError):
    """提示詞長度超過 context window——送出去只會被無聲截斷。"""


class Unavailable(LLMError):
    """
    服務端暫時無法回應（503 滿載、500/502/504）。已自動重試過仍失敗才會拋出。

    跟 RateLimited 分開：配額用完重試幾次都沒用，應該換金鑰或等重置；
    滿載通常幾秒到幾分鐘就過去，值得自動等一下。混在一起的話，要嘛把
    配額錯誤白白重試三輪，要嘛讓使用者被一次尖峰擋下來、以為軟體壞了。
    """


# 暫時性錯誤的重試間隔（秒）。總共最多多等約 19 秒——比使用者手動重按
# 快，又不至於在服務真的掛掉時讓介面卡住太久。
RETRY_DELAYS = (2, 5, 12)
_sleep = time.sleep          # 測試會換掉它，不必真的等


def set_retry_delays(*delays):
    """
    改掉重試間隔。給批次腳本用。

    互動介面不該讓使用者盯著畫面等兩分鐘，所以預設只等約 19 秒。但一支要跑
    一小時的批次腳本剛好相反：為了一次幾分鐘的服務端尖峰就讓整批停下來、
    還要人回來重下指令，比多等兩分鐘糟得多。實測撞到過：雲端模型在尖峰時段
    連續回 503，19 秒內的四次嘗試全部失敗，而幾分鐘後同一個指令就正常。
    """
    global RETRY_DELAYS
    RETRY_DELAYS = tuple(int(d) for d in delays)
    return RETRY_DELAYS

_TRANSIENT = re.compile(
    r"\b(500|502|503|504)\b|unavailable|overloaded|high demand"
    # 連線層的抖動也是暫時性的，而且比服務端滿載更常見。
    #
    # 實測一輪雲端開放編碼，149 個窗口裡有一個掉在
    # "[Errno 11004] getaddrinfo failed"——一次 DNS 查詢失敗，下一秒就好了，
    # 但那個窗口的編碼整份沒了。只認 HTTP 狀態碼的字樣接不到它。
    r"|getaddrinfo|name or service not known|temporary failure in name"
    r"|connection reset|connection aborted|connection refused"
    r"|timed out|timeout|broken pipe|remote end closed", re.I)


def _looks_transient(msg):
    """滿載、閘道錯誤或連線抖動。配額錯誤排除在外（見 Unavailable 的說明）。"""
    return bool(_TRANSIENT.search(msg or "")) and not _looks_rate_limited(msg)


# =====================================================================
# 2. 端點設定
# =====================================================================
class Endpoint:
    """
    一次呼叫需要知道的全部設定。

    刻意做成單純的值物件而不是連線物件：Streamlit 每次互動都會重跑整個
    腳本，任何跨重跑存活的連線都會變成難以追蹤的狀態。每次呼叫重新建立
    連線的成本，對一次要跑幾十秒的生成而言可以忽略。
    """

    def __init__(self, provider=GEMINI, model="", api_key="", base_url="",
                 timeout=900, num_ctx=DEFAULT_NUM_CTX, max_tokens=None):
        if provider not in PROVIDERS:
            raise NotConfigured(f"unknown provider: {provider}")
        self.provider = provider
        self.model = (model or "").strip()
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or DEFAULT_BASE_URL[provider]).strip().rstrip("/")
        self.timeout = int(timeout)
        self.num_ctx = int(num_ctx)
        self.max_tokens = int(max_tokens
                              or default_max_tokens(provider, self.num_ctx))

    def provenance(self, **extra):
        """
        寫進紀錄 _meta 的完整端點描述。describe() 是一行識別字串，方便顯示
        與比對；這個是可以重跑的那一份：context window、輸出上限、地端模型
        的量化等級與 digest、雲端 SDK 名稱、以及呼叫端補上的取樣參數
        （temperature、分窗長度…）。

        為什麼要分開：稿件主張「audit record 記完整端點而非只記模型名」，
        但 describe() 本身就只有 provider/model@url——量化等級、num_ctx、
        temperature 都不在裡面，而那些正是換一個就等於換一次實驗的東西。
        """
        p = {
            "endpoint": self.describe(),
            "provider": self.provider,
            "model": self.model,
            "base_url": self.base_url or None,
            "data_locality": self.data_locality,
            "num_ctx": self.num_ctx if self.is_local else None,
            "max_tokens": self.max_tokens,
            "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if self.provider == GEMINI:
            p["sdk"] = GEMINI_SDK
        elif self.provider == OLLAMA:
            p.update(model_details(self.model, self.base_url))
        p.update({k: v for k, v in extra.items() if v is not None})
        return p

    @property
    def is_local(self):
        return self.provider in LOCAL_PROVIDERS

    @property
    def data_locality(self):
        """
        逐字稿有沒有離開這台機器：'local' 或 'remote'。

        **這件事由位址決定，不由供應者決定。** OpenAI 相容那條路同時涵蓋
        LM Studio（localhost，資料不出機器）與 OpenRouter 之類的代理閘道
        （資料送到別人手上），is_local 只看供應者，兩者都會回 True。
        資料管理聲明要寫的是這個欄位，不是供應者名稱。
        """
        if self.provider == GEMINI:
            return "remote"
        return "local" if _is_loopback(self.base_url) else "remote"

    @property
    def needs_key(self):
        """
        只有 Gemini 一定要金鑰。OpenAI 相容端點分兩種情形：指向
        api.openai.com 或 OpenRouter 要金鑰，指向 localhost 不要——
        所以這裡不能只看供應者，要看位址。
        """
        if self.provider == GEMINI:
            return True
        if self.provider == OPENAI_COMPAT:
            return not _is_loopback(self.base_url)
        return False

    def describe(self):
        """給稽核軌跡與匯出用的一行字串，要能唯一標定這次分析用了什麼。"""
        if self.provider == GEMINI:
            return f"{GEMINI}/{self.model}"
        return f"{self.provider}/{self.model}@{self.base_url}"

    def validate(self):
        if not self.model:
            raise NotConfigured("no model selected")
        if self.needs_key and not self.api_key:
            raise NotConfigured("no API key")


def _is_loopback(url):
    return bool(re.match(r"^https?://(localhost|127\.0\.0\.1|\[::1\]|0\.0\.0\.0)\b",
                         (url or "").strip(), re.I))


# =====================================================================
# 3. 長度估算
# =====================================================================
def estimate_tokens(text):
    """
    粗估 token 數。刻意做成保守（偏高）的估計。

    低估的代價是提示詞被無聲截斷、編碼結果建立在半份逐字稿上，而且
    使用者不會發現；高估的代價只是多跳一個可以略過的警告。兩者不對稱，
    所以往高的估。

    CJK 字元大致 1 字 ≈ 1 token，拉丁字母大致 4 字元 ≈ 1 token。
    """
    if not text:
        return 0
    cjk = sum(1 for ch in text if "㐀" <= ch <= "鿿"
              or "豈" <= ch <= "﫿"
              or "぀" <= ch <= "ヿ")
    other = len(text) - cjk
    return int(cjk + other / 3.5) + 16


def check_context(ep, prompt, system=""):
    """
    送出前擋下必然被截斷的呼叫。

    只對地端供應者檢查：雲端模型的 context window 由服務端管理，
    超過會回傳明確的錯誤，不會無聲截斷。
    """
    if not ep.is_local:
        return
    need = estimate_tokens(prompt) + estimate_tokens(system) + 512
    room = ep.num_ctx - ep.max_tokens
    if room <= 0:
        raise ContextOverflow(
            f"num_ctx ({ep.num_ctx}) must exceed max output tokens "
            f"({ep.max_tokens}); raise the context window or lower the "
            f"output limit.")
    if need > room:
        # 訊息要指向**真正的槓桿**。只寫「加大視窗、切開逐字稿、換模型」的話，
        # 但保留額佔掉視窗一半以上時，那三條沒有一條是原因——使用者會誤以為
        # 地端模型做不到，而其實只是保留額訂得太大。
        share = ep.max_tokens / ep.num_ctx if ep.num_ctx else 0
        hint = (f" The output reservation is {share:.0%} of the window; "
                f"a single coding pass returns about 1,500–2,500 tokens, so "
                f"lowering it to {MIN_OUTPUT_RESERVE} would free "
                f"{ep.max_tokens - MIN_OUTPUT_RESERVE} tokens for the "
                f"transcript."
                if share > 0.3 and ep.max_tokens > MIN_OUTPUT_RESERVE else "")
        # 「加大視窗」不是可行動的建議——使用者不知道要加到多少，也不知道
        # 這顆模型撐不撐得住。所以算出確切的數字，並且去問模型的實際上限。
        want = required_num_ctx(need, ep.provider)
        limit = model_context_limit(ep.model, ep.base_url) if ep.is_local else None
        if want and limit and want > limit:
            advice = (f" This model's context limit is {limit:,}, which is not "
                      f"enough for this transcript — split it, or use a model "
                      f"with a longer context.")
        elif want:
            advice = (f" Set num_ctx to {want:,} or more"
                      + (f" (this model supports up to {limit:,})" if limit else "")
                      + ". Note that a larger window costs proportionally more "
                        "memory on the server.")
        else:
            advice = (" Split the transcript, or use a model with a longer "
                      "context.")
        raise ContextOverflow(
            f"prompt is about {need} tokens but only {room} tokens of "
            f"context remain (num_ctx {ep.num_ctx} minus {ep.max_tokens} "
            f"reserved for output). The server would silently truncate the "
            f"transcript.{hint}{advice}")


# =====================================================================
# 4. HTTP 工具
# =====================================================================
def _post_json(url, payload, timeout, headers=None):
    data = json.dumps(payload).encode("utf-8")
    hdr = {"Content-Type": "application/json"}
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdr, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")[:400]
        except Exception:
            pass
        if e.code == 429:
            raise RateLimited(f"HTTP 429 rate limited: {body}") from e
        raise LLMError(f"HTTP {e.code} from {url}: {body}") from e
    except urllib.error.URLError as e:
        raise NotConfigured(_unreachable_msg(url, e)) from e


def _get_json(url, timeout, headers=None):
    req = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        raise LLMError(f"HTTP {e.code} from {url}") from e
    except urllib.error.URLError as e:
        raise NotConfigured(_unreachable_msg(url, e)) from e


def _unreachable_msg(url, e):
    """
    連不上時給的訊息要能直接指向解法。「Connection refused」對沒開過
    終端機的研究者等於沒有訊息。
    """
    return (f"Cannot reach {url} ({getattr(e, 'reason', e)}). "
            f"Is the local model server running? "
            f"For Ollama, run 'ollama serve' and then 'ollama pull <model>'. "
            f"For LM Studio, start the local server from the Developer tab.")


# =====================================================================
# 5. 模型清單
# =====================================================================
def _gemini_sort_key(name):
    """
    排序：正式版優先 → 版本新的優先 → Flash 優先 → 非 lite 優先。

    preview / exp 一律排到最後，不管版本號多新。預覽版正是最快被下架的
    那一種，而預設選項應該是**明年還會在**的那一個；使用者要嘗鮮，
    清單裡仍然找得到。
    """
    unstable = "preview" in name or "exp" in name
    ver = re.search(r"(\d+(?:\.\d+)?)", name)
    return (unstable,
            -float(ver.group(1)) if ver else 0,
            0 if "flash" in name else 1,
            "lite" in name, name)


def _local_sort_key(name):
    """
    地端模型排序：指令微調版優先，量化程度低的優先，再依名稱。

    base 模型（無 instruct/chat 後綴）幾乎不可能照著我們的提示詞回傳
    JSON，排到最後可以少掉一整類「為什麼都解析失敗」的求助。
    """
    low = name.lower()
    tuned = 0 if any(k in low for k in ("instruct", "chat", "-it")) else 1
    embed = 1 if any(k in low for k in ("embed", "bge", "nomic")) else 0
    return (embed, tuned, low)


def model_context_limit(model, base_url="", timeout=10):
    """
    問 Ollama 這顆模型到底支援多長的 context。查不到就回 None。

    為什麼要問：使用者把 num_ctx 設成 20480 撞牆時，只得到「加大視窗」
    這種建議的話，沒有人告訴他這顆模型其實支援 131072，也沒有人
    告訴他該設多少才夠。要使用者自己去查模型規格再回來填一個數字，
    那不叫提示，那叫把工作丟回去。

    Ollama 的 /api/show 會回 model_info，裡面有 <架構>.context_length。
    欄位名隨架構不同（llama.context_length、qwen2.context_length…），
    所以用後綴比對而不是寫死。
    """
    base_url = (base_url or DEFAULT_BASE_URL[OLLAMA]).rstrip("/")
    try:
        d = _post_json(f"{base_url}/api/show", {"model": model}, timeout)
    except (LLMError, NotConfigured, Exception):
        return None
    info = (d or {}).get("model_info") or {}
    for k, v in info.items():
        if str(k).endswith(".context_length"):
            try:
                n = int(v)
                return n if n > 0 else None
            except (TypeError, ValueError):
                return None
    return None


_DETAILS_CACHE = {}


def model_details(model, base_url="", timeout=10):
    """
    Ollama 這顆模型的身份資訊：量化等級、參數量、家族、原生 context、digest。
    查不到就回空字典，絕不拋錯——這是寫進紀錄的附註，不是能擋住分析的東西。

    為什麼要問：稿件說「llama3.1:8b 在不同人的機器上是不同的量化版本，只寫
    模型名的紀錄無法重現」，所以端點描述子不能只寫模型名。量化
    等級在 /api/show 的 details 裡、digest 在 /api/tags 裡，兩個都是已經
    在打的服務，取得成本為零。結果依 (base_url, model) 快取，一個行程只問
    一次。
    """
    base_url = (base_url or DEFAULT_BASE_URL[OLLAMA]).rstrip("/")
    key = (base_url, model)
    if key in _DETAILS_CACHE:
        return dict(_DETAILS_CACHE[key])
    out = {}
    try:
        d = _post_json(f"{base_url}/api/show", {"model": model}, timeout) or {}
        det = d.get("details") or {}
        for k in ("quantization_level", "parameter_size", "family"):
            if det.get(k):
                out[k] = str(det[k])
        for k, v in (d.get("model_info") or {}).items():
            if str(k).endswith(".context_length"):
                try:
                    out["context_length"] = int(v)
                except (TypeError, ValueError):
                    pass
                break
    except Exception:                                     # noqa: BLE001
        pass
    try:
        tags = _get_json(f"{base_url}/api/tags", timeout) or {}
        for m in tags.get("models") or []:
            if m.get("name") == model or m.get("model") == model:
                if m.get("digest"):
                    out["digest"] = str(m["digest"])
                break
    except Exception:                                     # noqa: BLE001
        pass
    _DETAILS_CACHE[key] = dict(out)
    return out


def required_num_ctx(need_tokens, provider=OLLAMA):
    """
    要送出這麼長的提示詞，num_ctx 至少要設多少。

    保留額本身會隨 num_ctx 縮放（見 default_max_tokens），所以這是個
    互相依賴的式子——直接往上試，比反解乾淨，而且不會因為公式改了就錯。
    """
    for ctx in (8192, 16384, 20480, 24576, 32768, 49152, 65536,
                98304, 131072, 262144, 524288, 1048576):
        if ctx - default_max_tokens(provider, ctx) >= need_tokens:
            return ctx
    return None


def list_models(provider, api_key="", base_url="", timeout=15):
    """
    向服務查詢目前可用的模型。

    回傳 (清單, 提示文字)。提示文字是給使用者看的，說明這份清單
    到底是查來的還是墊底的——研究者需要知道自己選的模型是不是真的存在。
    """
    base_url = (base_url or DEFAULT_BASE_URL.get(provider, "")).rstrip("/")
    try:
        if provider == GEMINI:
            available, note = gemini_sdk_note()
            if not available:
                return [], note
            if not api_key:
                return FALLBACK_MODELS[GEMINI], "Enter an API key to list models."
            names = _gemini_list(api_key)
            names.sort(key=_gemini_sort_key)
            if not names:
                raise LLMError("no usable model returned")
            listed = f"{len(names)} models listed by the API."
            return names, (f"{listed} {note}" if note else listed)

        if provider == OLLAMA:
            d = _get_json(f"{base_url}/api/tags", timeout)
            names = sorted((m.get("name") or m.get("model") or ""
                            for m in d.get("models", []) if m),
                           key=_local_sort_key)
            names = [n for n in names if n]
            if not names:
                return [], ("Ollama is running but has no models. "
                            "Pull one, e.g.: ollama pull llama3.1:8b-instruct-q4_K_M")
            return names, f"{len(names)} models installed locally."

        if provider == OPENAI_COMPAT:
            hdr = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            d = _get_json(f"{base_url}/models", timeout, hdr)
            names = sorted((m.get("id", "") for m in d.get("data", []) if m),
                           key=_local_sort_key)
            names = [n for n in names if n]
            if not names:
                raise LLMError("endpoint returned an empty model list")
            return names, f"{len(names)} models offered by {base_url}."
    except (LLMError, NotConfigured) as e:
        return FALLBACK_MODELS.get(provider, []), str(e)[:200]
    except Exception as e:                            # pragma: no cover
        return FALLBACK_MODELS.get(provider, []), f"Could not list models: {e}"
    return [], ""


def probe(ep, timeout=10):
    """
    連得上嗎？回傳 (bool, 訊息)。介面用它在按下「開始分析」**之前**
    就告訴使用者服務沒開，而不是等跑完第一份逐字稿才失敗。
    """
    try:
        models, note = list_models(ep.provider, ep.api_key, ep.base_url, timeout)
    except Exception as e:                            # pragma: no cover
        return False, str(e)[:200]
    if ep.provider == GEMINI:
        return bool(models), note
    if not models:
        return False, note
    if ep.model and ep.model not in models:
        return False, (f"'{ep.model}' is not available at {ep.base_url}. "
                       f"Installed: {', '.join(models[:5])}")
    return True, note


# =====================================================================
# 6. 生成
# =====================================================================
def _extract_first_json(text):
    """
    從回應裡取出第一個完整的 JSON 物件。

    地端模型比雲端模型更常在 JSON 前後加話（「Here is the JSON:」、
    ```json 圍欄、結尾的解釋）。用括號配對而非貪婪正規式，才不會在
    模型多寫了一段結語時把整個尾巴一起吃進來。
    """
    if not text:
        return ""
    s = text
    fence = re.search(r"```(?:json)?\s*(.+?)```", s, re.DOTALL)
    if fence:
        s = fence.group(1)
    start = s.find("{")
    if start < 0:
        return ""
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return s[start:i + 1]
    return s[start:]        # 截斷的輸出：交給呼叫端的修補與錯誤處理


def _strip_trailing_commas(blob):
    """
    刪掉 `,` 後面只跟著空白就遇到 `}` 或 `]` 的那個逗號。

    字串裡的逗號與括號要跳過，否則像 "he said, }" 這樣的引文會被改壞。
    """
    out, in_str, esc = [], False, False
    for ch in blob:
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            continue
        if ch in "}]":
            # 往回找上一個非空白字元，是逗號就丟掉
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\r\n":
                j -= 1
            if j >= 0 and out[j] == ",":
                del out[j]
        out.append(ch)
    return "".join(out)


def loads_lenient(blob):
    """
    解析模型輸出的 JSON，容忍多餘的逗號。

    為什麼需要它：一個窗口的編碼會因為一個多餘的逗號整份丟掉。實測雲端
    模型跑一份 13 個窗口的聽證會逐字稿，第 6 與第 11 窗各因為
    "Illegal trailing comma before end of object" 與
    "Expecting property name enclosed in double quotes" 失敗——後者也是
    同一件事（`}` 前面多一個逗號）。那是 15% 的逐字稿沒有被編碼，而原因
    與模型的判斷完全無關。

    只修**語法上沒有歧義**的那一種。括號沒合上、引號沒關、鍵名沒引號，
    都不在這裡猜——猜錯會產出一份看起來正常但內容錯的編碼，比失敗更糟。
    """
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass
    repaired = _strip_trailing_commas(blob)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        # 修不掉的話，把出錯位置前後的原文帶進訊息裡。
        #
        # 這些錯誤會被記進 _meta.chunk_errors。只記
        # 「Expecting property name enclosed in double quotes: line 32
        # column 7」——事後沒有任何人查得出模型到底寫了什麼，於是「某個
        # 窗口沒編到」永遠只是一個無法追究的事實。一篇以 provenance 為
        # 題的工具不該自己留這種洞。
        lo = max(0, e.pos - 90)
        snippet = repaired[lo:e.pos + 60].replace("\n", "\\n")
        raise json.JSONDecodeError(
            f"{e.msg} — model wrote: ...{snippet}...", e.doc, e.pos) from None


def _looks_rate_limited(msg):
    m = (msg or "").lower()
    return "429" in m or "quota" in m or "rate limit" in m or "resource_exhausted" in m


def complete(ep, prompt, system="", temperature=0.2, max_tokens=None,
             json_mode=False):
    """
    送出一次生成，回傳純文字。

    json_mode 只在服務支援時才開。Ollama 的 format=json 與 OpenAI 相容
    端點的 response_format 都能大幅降低地端模型輸出雜訊的機率；
    Gemini 這邊維持原本的自由文字加事後擷取，因為既有的提示詞已經
    被調整成搭配擷取邏輯，改動它等於要重新驗證所有既有結果。
    """
    ep.validate()
    max_tokens = int(max_tokens or ep.max_tokens)
    check_context(ep, prompt, system)

    def _once():
        if ep.provider == GEMINI:
            return _complete_gemini(ep, prompt, system, temperature, max_tokens)
        if ep.provider == OLLAMA:
            return _complete_ollama(ep, prompt, system, temperature, max_tokens,
                                    json_mode)
        return _complete_openai(ep, prompt, system, temperature, max_tokens,
                                json_mode)

    # 服務端滿載（503）時自動等一下再試。實測過：雲端模型在尖峰時段會回
    # "This model is currently experiencing high demand"，使用者手動重按
    # 通常就成功——那這件事應該由程式來做，而不是讓人以為軟體壞了。
    for attempt in range(len(RETRY_DELAYS) + 1):
        try:
            return _once()
        except (RateLimited, NotConfigured, ContextOverflow):
            raise
        except LLMError as e:
            if not _looks_transient(str(e)):
                raise
            if attempt == len(RETRY_DELAYS):
                raise Unavailable(
                    f"{ep.describe()} is temporarily unavailable on the provider's "
                    f"side; tried {attempt + 1} times over about "
                    f"{sum(RETRY_DELAYS)} seconds. Wait a few minutes or choose "
                    f"another model. Last error: {str(e)[:300]}") from e
            _sleep(RETRY_DELAYS[attempt])


def _gemini_list(api_key):
    """兩套 SDK 的模型清單。回傳去掉 models/ 前綴、可用於生成的名稱。"""
    names = []
    if GEMINI_SDK == GENAI_NEW:
        client = genai_client.Client(api_key=api_key)
        for m in client.models.list():
            actions = getattr(m, "supported_actions", None) or []
            # 新版 SDK 有些版本不填 supported_actions。填了就據以篩選，
            # 沒填就靠名稱過濾——寧可多列幾個，也不要列出空清單。
            if actions and "generateContent" not in actions:
                continue
            n = str(getattr(m, "name", "")).replace("models/", "")
            if n and "embedding" not in n and "aqa" not in n:
                names.append(n)
    else:
        genai.configure(api_key=api_key)
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" not in methods:
                continue
            n = str(getattr(m, "name", "")).replace("models/", "")
            if n and "embedding" not in n and "aqa" not in n:
                names.append(n)
    return names


def _complete_gemini(ep, prompt, system, temperature, max_tokens):
    available, note = gemini_sdk_note()
    if not available:
        raise NotConfigured(note)
    try:
        if GEMINI_SDK == GENAI_NEW:
            client = genai_client.Client(api_key=ep.api_key)
            cfg = {"temperature": temperature,
                   "max_output_tokens": max_tokens}
            if system:
                cfg["system_instruction"] = system
            r = client.models.generate_content(model=ep.model, contents=prompt,
                                               config=cfg)
            if not r.text:
                # 沒有文字時 r.text 是 None。直接回傳的話，下游只會說「找不到
                # JSON」，看不出是被安全過濾擋下、還是會「思考」的模型把輸出
                # 額度在思考階段就用完了。把 finish reason 帶出來才知道該怎麼辦。
                cands = getattr(r, "candidates", None) or []
                reason = getattr(cands[0], "finish_reason", None) if cands else None
                reason = getattr(reason, "name", reason) or "unknown"
                hint = (" The output limit was reached before any answer text; "
                        "models that think before answering can spend the whole "
                        "budget on thinking. Try another model."
                        if "MAX_TOKENS" in str(reason) else "")
                raise LLMError(f"{ep.model} returned no text "
                               f"(finish reason: {reason}).{hint}")
            return r.text
        genai.configure(api_key=ep.api_key)
        kw = {"model_name": ep.model,
              "generation_config": {"max_output_tokens": max_tokens,
                                    "temperature": temperature}}
        if system:
            kw["system_instruction"] = system
        model = genai.GenerativeModel(**kw)
        return model.generate_content(prompt).text
    except Exception as e:
        if _looks_rate_limited(str(e)):
            raise RateLimited(str(e)) from e
        raise LLMError(str(e)) from e


def _complete_ollama(ep, prompt, system, temperature, max_tokens, json_mode):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    payload = {
        "model": ep.model,
        "messages": msgs,
        "stream": False,
        "options": {
            "temperature": temperature,
            # num_ctx 一定要明確給。Ollama 的預設值遠小於一份逐字稿，
            # 沒給就會無聲截斷——結果看起來完全正常。
            "num_ctx": ep.num_ctx,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"
    d = _post_json(f"{ep.base_url}/api/chat", payload, ep.timeout)
    text = ((d.get("message") or {}).get("content") or "").strip()
    if not text:
        raise LLMError(f"empty response from {ep.model}: {str(d)[:200]}")
    return text


def _complete_openai(ep, prompt, system, temperature, max_tokens, json_mode):
    msgs = ([{"role": "system", "content": system}] if system else []) + \
           [{"role": "user", "content": prompt}]
    payload = {"model": ep.model, "messages": msgs,
               "temperature": temperature, "max_tokens": max_tokens,
               "stream": False}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    hdr = {"Authorization": f"Bearer {ep.api_key}"} if ep.api_key else {}
    try:
        d = _post_json(f"{ep.base_url}/chat/completions", payload, ep.timeout,
                       hdr)
    except LLMError as e:
        # response_format 不是所有地端伺服器都實作。被拒絕就退回自由文字，
        # 事後擷取仍然救得回來——為了一個選配參數讓整趟分析失敗不值得。
        if json_mode and "response_format" in str(e):
            payload.pop("response_format", None)
            d = _post_json(f"{ep.base_url}/chat/completions", payload,
                           ep.timeout, hdr)
        else:
            raise
    choices = d.get("choices") or []
    if not choices:
        raise LLMError(f"no choices returned: {str(d)[:200]}")
    text = ((choices[0].get("message") or {}).get("content") or "").strip()
    if not text:
        raise LLMError(f"empty response from {ep.model}")
    return text


def complete_json(ep, prompt, system="", temperature=0.2, max_tokens=None,
                  retries=2):
    """
    生成並回傳解析後的 dict。

    地端模型解析失敗的機率遠高於雲端，所以重試時會**加碼要求**：
    第二次起把「只輸出 JSON」的指示再說一次，並把溫度降到 0。
    單純原樣重送同一個提示詞，得到的多半是同一個壞掉的輸出。
    """
    last = None
    for attempt in range(retries + 1):
        p = prompt
        temp = temperature
        if attempt:
            temp = 0.0
            p = (prompt + "\n\nReturn a single JSON object and nothing else. "
                          "No prose, no markdown fence, no explanation.")
        raw = complete(ep, p, system, temp, max_tokens, json_mode=True)
        blob = _extract_first_json(raw)
        if blob:
            try:
                return loads_lenient(blob)
            except json.JSONDecodeError as e:
                last = e
        else:
            last = ValueError("no JSON object in response")
        if attempt < retries:
            time.sleep(1)
    raise LLMError(f"could not parse JSON after {retries + 1} attempts: {last}")


def make_callable(ep, temperature=0.2, max_tokens=None):
    """
    包成 `lambda prompt -> text`。

    tacit_themes.induce_themes 與 tacit_openalex.draft_framework 都收這種
    可呼叫物件而不是模型實例——分析引擎因此完全不知道供應者的存在，
    也讓它們可以用假的可呼叫物件離線測試。
    """
    def _call(prompt):
        return complete(ep, prompt, temperature=temperature,
                        max_tokens=max_tokens)
    return _call


# =====================================================================
# 7. 從環境變數帶入
# =====================================================================
def from_env():
    """
    以環境變數建立端點，供批次執行與可重現腳本使用。

        TACIT_PROVIDER   gemini | ollama | openai_compat
        TACIT_MODEL      模型名稱
        TACIT_BASE_URL   地端服務位址
        TACIT_API_KEY    金鑰（Gemini 亦讀 GEMINI_API_KEY / GOOGLE_API_KEY）
        TACIT_NUM_CTX    地端 context window

    回傳 None 表示沒設定，呼叫端應改用介面上的欄位。
    """
    provider = (os.environ.get("TACIT_PROVIDER") or "").strip().lower()
    if provider not in PROVIDERS:
        return None
    key = (os.environ.get("TACIT_API_KEY")
           or os.environ.get("GEMINI_API_KEY")
           or os.environ.get("GOOGLE_API_KEY") or "")
    try:
        return Endpoint(
            provider=provider,
            model=os.environ.get("TACIT_MODEL", ""),
            api_key=key,
            base_url=os.environ.get("TACIT_BASE_URL", ""),
            num_ctx=int(os.environ.get("TACIT_NUM_CTX", DEFAULT_NUM_CTX)),
        )
    except Exception:                                 # pragma: no cover
        return None
