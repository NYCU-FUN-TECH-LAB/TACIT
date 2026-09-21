"""
啟動器輔助腳本：_launch_common.py 的每一個子命令。

為什麼需要這一支
----------------
`_launch_common.py` 是三個平台啟動器共用的判斷邏輯——檢查 Python 版本、
確認相依是否齊全、挑一個沒被佔用的埠、建立 Streamlit 憑證檔。**它是使用者
按下去之後第一個執行的東西**，也是任何人拿到程式的第一個接觸點。這一段壞
掉，後面幾千行寫得再好都沒有意義，因為程式根本打不開。

這一支不需要網路、不需要模型服務，也**不會動到使用者家目錄下的任何檔案**
（憑證檔那一項會把 HOME 導到暫存資料夾）。
"""
import io
import os
import socket
import sys
import tempfile
from contextlib import redirect_stdout, redirect_stderr

import _launch_common as LC

FAIL = []


def ok(label, cond, note=""):
    print(("  PASS  " if cond else "  FAIL  ") + label + (f"  ({note})" if note else ""))
    if not cond:
        FAIL.append(label)


def eq(label, got, want):
    ok(label, got == want, f"got={got!r} want={want!r}" if got != want else "")


def run(fn, argv=None):
    """跑一個子命令，回傳 (exit_code, stdout, stderr)。"""
    saved = sys.argv
    if argv is not None:
        sys.argv = argv
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = fn()
    finally:
        sys.argv = saved
    return code, out.getvalue(), err.getvalue()


print("=" * 70)
print("測試 1：check —— Python 版本門檻")
print("=" * 70)
code, out, _ = run(LC.cmd_check)
eq("目前的 Python 通過檢查", code, 0)
ok("有印出實際版本", "Python" in out and "OK" in out, out.strip()[:60])

_saved_min = LC.MIN_PY
try:
    LC.MIN_PY = (99, 0)
    code, out, _ = run(LC.cmd_check)
    eq("版本過舊時回傳 1", code, 1)
    ok("並且說明需要哪一版", "99.0" in out, out.strip()[:80])
finally:
    LC.MIN_PY = _saved_min

print()
print("=" * 70)
print("測試 2：deps —— 必要與選配的分野")
print("=" * 70)
# Gemini SDK 是必要相依：不是每個人都有 Ollama，沒有本機模型的人裝完
# 就要能用 Gemini。所以它必須在 REQUIRED 裡，缺了要讓啟動器去補裝。
code, out, err = run(LC.cmd_deps)
eq("相依齊全時回傳 0", code, 0)
ok("Gemini SDK 列在必要清單", ("google.genai", "google-genai") in LC.REQUIRED,
   str(LC.REQUIRED))
if err:
    ok("選配缺少時的訊息走 stderr（不混進 stdout）", "選配" in err,
       err.strip()[:80])

_saved_req = LC.REQUIRED
try:
    LC.REQUIRED = LC.REQUIRED + [("a_module_that_does_not_exist", "ghost-pkg")]
    code, out, _ = run(LC.cmd_deps)
    eq("缺少必要套件時回傳 1", code, 1)
    ok("並且把缺項印在 stdout 供批次檔安裝", "ghost-pkg" in out, out.strip()[:80])
finally:
    LC.REQUIRED = _saved_req

_saved_opt = LC.OPTIONAL
try:
    LC.OPTIONAL = [("another_ghost_module", "ghost-optional")]
    code, out, err = run(LC.cmd_deps)
    eq("缺少選配套件仍然回傳 0", code, 0)
    ok("選配缺項只提醒，不擋啟動", "ghost-optional" in err, err.strip()[:80])
    ok("選配訊息不會污染 stdout", "ghost-optional" not in out)
finally:
    LC.OPTIONAL = _saved_opt

# 沒裝 Gemini SDK 的環境要被判定缺少，而且缺項要印在 stdout，
# 啟動器才會去跑 pip install -r requirements.txt 補裝。
_saved_req = LC.REQUIRED
try:
    LC.REQUIRED = [r for r in LC.REQUIRED if r[1] != "google-genai"] + [
        ("google_genai_missing_for_test", "google-genai")]
    code, out, _ = run(LC.cmd_deps)
    eq("沒有 Gemini SDK 時回傳 1（讓啟動器補裝）", code, 1)
    ok("缺項印出 google-genai", "google-genai" in out, out.strip()[:80])
finally:
    LC.REQUIRED = _saved_req

print()
print("=" * 70)
print("測試 3：port —— 挑一個真的沒被佔用的埠")
print("=" * 70)
code, out, _ = run(LC.cmd_port)
eq("回傳 0", code, 0)
port = out.strip().splitlines()[-1] if out.strip() else ""
ok("stdout 只有埠號，可以直接餵給批次檔", port.isdigit(), repr(out))
if port.isdigit():
    ok("埠號在合理範圍", 1 <= int(port) <= 65535, port)

# 佔用 8501，確認它會換一個，並且提醒走 stderr 而不是混進埠號
_busy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    _busy.bind(("0.0.0.0", 8501))
    _busy.listen(1)
except OSError:
    _busy.close()
    _busy = None
    ok("能佔用 8501 以進行測試", True, "本機已有程式佔用，跳過這一段")

if _busy:
    try:
        ok("_port_free 認得出 8501 被佔用", not LC._port_free(8501))
        code, out, err = run(LC.cmd_port)
        p2 = out.strip().splitlines()[-1]
        ok("被佔用時仍給得出可用的埠", p2.isdigit(), repr(out))
        ok("換掉的埠不是 8501", p2 != "8501", p2)
        # stdout 必須只有埠號：批次檔直接拿它當變數，混進中文提醒會壞掉
        ok("提醒文字走 stderr，沒有混進 stdout",
           "提醒" not in out and "提醒" in err, f"out={out.strip()[:40]!r}")
    finally:
        _busy.close()

print()
print("=" * 70)
print("測試 4：credentials —— 跳過 Streamlit 首次 email 詢問")
print("=" * 70)
# HOME 導到暫存資料夾，絕不碰使用者真正的 ~/.streamlit/credentials.toml
_home_vars = ("HOME", "USERPROFILE")
_saved_home = {k: os.environ.get(k) for k in _home_vars}
_tmp = tempfile.mkdtemp()
try:
    for k in _home_vars:
        os.environ[k] = _tmp
    code, out, _ = run(LC.cmd_credentials)
    eq("回傳 0", code, 0)
    f = os.path.join(_tmp, ".streamlit", "credentials.toml")
    ok("憑證檔有被建立", os.path.isfile(f), f)
    if os.path.isfile(f):
        body = open(f, encoding="utf-8").read()
        ok("內容是空的 email（這才會跳過詢問）", 'email = ""' in body, body.strip())

    # 已存在就不可覆寫——使用者可能已經填過自己的設定
    with open(f, "w", encoding="utf-8") as fh:
        fh.write('[general]\nemail = "me@example.org"\n')
    run(LC.cmd_credentials)
    ok("已存在的憑證檔不會被覆寫",
       "me@example.org" in open(f, encoding="utf-8").read())
finally:
    for k, v in _saved_home.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

print()
print("=" * 70)
print("測試 5：venvcheck —— 被複製過來的虛擬環境要抓得出來")
print("=" * 70)
# 要防的失效：整個資料夾被複製到別台機器後，.venv 裡的直譯器找不到標準函式庫，
# 丟出 "Failed to import encodings module"——那個訊息完全看不出跟「搬過資料夾」
# 有關。所以這裡主動比對建立路徑並說人話。
_tmp2 = tempfile.mkdtemp()
_venv = os.path.join(_tmp2, ".venv")
os.makedirs(_venv)
eq("沒有 pyvenv.cfg 就判定不可用",
   run(LC.cmd_venvcheck, ["x", "venvcheck", _venv])[0], 1)

with open(os.path.join(_venv, "pyvenv.cfg"), "w", encoding="utf-8") as fh:
    fh.write("home = /usr\n"
             "command = /usr/bin/python3 -m venv /somewhere/else/.venv\n")
code, out, _ = run(LC.cmd_venvcheck, ["x", "venvcheck", _venv])
eq("建立路徑不符就判定不可用", code, 1)
ok("並且用人話說明原因（不是 encodings 錯誤）",
   "複製" in out or "無法搬移" in out, out.strip()[:80])
ok("訊息保證不會動到研究資料", "研究資料" in out, out.strip()[:120])

# 路徑對，但直譯器不存在
with open(os.path.join(_venv, "pyvenv.cfg"), "w", encoding="utf-8") as fh:
    fh.write(f"home = /usr\ncommand = /usr/bin/python3 -m venv {_venv}\n")
eq("路徑對但沒有直譯器也判定不可用",
   run(LC.cmd_venvcheck, ["x", "venvcheck", _venv])[0], 1)

print()
print("=" * 70)
print("測試 6：msg —— 啟動器的提示文字")
print("=" * 70)
code, out, _ = run(LC.cmd_msg, ["x", "msg", "banner"])
eq("回傳 0", code, 0)
ok("banner 認得出是 TACIT", "TACIT" in out, out.strip()[:40])
for key in ("mkvenv", "install", "starting", "err_python", "err_deps"):
    c, o, _ = run(LC.cmd_msg, ["x", "msg", key])
    ok(f"訊息 {key} 有內容", c == 0 and o.strip(), o.strip()[:40])
code, out, _ = run(LC.cmd_msg, ["x", "msg", "no_such_key"])
eq("未知的訊息鍵不會炸掉", code, 0)

print()
print("=" * 70)
print("測試 7：segmenter —— 裝不起來也絕不能擋住啟動")
print("=" * 70)
# 中文斷詞器會連帶裝進 PyTorch，數百 MB。網路中斷、磁碟不足、平台不支援
# 都可能失敗——但它只是輔助頁籤的功能，失敗絕不能讓使用者連程式都打不開。
_saved_pkg = LC.SEGMENTER_PKG
try:
    LC.SEGMENTER_PKG = "a-package-that-does-not-exist-on-pypi-tacit-test"
    LC.SEGMENTER_MOD = "a_module_that_does_not_exist_tacit_test"
    code, _, _ = run(LC.cmd_segmenter)
    eq("安裝失敗仍然回傳 0", code, 0)
finally:
    LC.SEGMENTER_PKG = _saved_pkg
    LC.SEGMENTER_MOD = "ckip_transformers"

print()
print("=" * 70)
print("測試 8：三個平台啟動器都指得到共用腳本")
print("=" * 70)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for fn in ("launch_windows.bat", "launch_mac.command", "launch_linux.sh"):
    p = os.path.join(ROOT, fn)
    ok(f"{fn} 存在", os.path.isfile(p))
    if os.path.isfile(p):
        body = open(p, encoding="utf-8", errors="replace").read()
        ok(f"{fn} 有呼叫 _launch_common", "_launch_common" in body)
        ok(f"{fn} 有啟動 app.py", "app.py" in body)

print()
print("=" * 70)
print("測試：啟動器講什麼語言")
print("=" * 70)
# 使用者不一定讀中文。雙擊之後黑色視窗裡的每一句話都要讀得懂——包括
# 「請不要關閉視窗」與錯誤訊息，正是最需要讀懂的兩種。預設英文，系統介面
# 是中文才講中文。
import re as _re                                                 # noqa: E402
import subprocess as _sp                                         # noqa: E402

_CJK = _re.compile(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]")


def _run_launcher(lang, *args):
    env = dict(os.environ, TACIT_LANG=lang, PYTHONIOENCODING="utf-8")
    r = _sp.run([sys.executable, os.path.join(ROOT, "_launch_common.py"), *args],
                capture_output=True, env=env, cwd=ROOT, timeout=120)
    return (r.stdout + r.stderr).decode("utf-8", "replace")


ok("每一則訊息都有英文與中文兩個版本",
   all(isinstance(v, tuple) and len(v) == 2 and all(v) for v in LC.MESSAGES.values()),
   str([k for k, v in LC.MESSAGES.items() if not (isinstance(v, tuple) and len(v) == 2)]))
ok("英文版裡一個中文字都沒有",
   not any(_CJK.search(v[0]) for v in LC.MESSAGES.values()),
   str([k for k, v in LC.MESSAGES.items() if _CJK.search(v[0])]))

for _key in LC.MESSAGES:
    _out = _run_launcher("en", "msg", _key, "port=8501", "missing=pandas")
    ok(f"TACIT_LANG=en 時 {_key} 是英文", not _CJK.search(_out), _out.strip()[:60])
_zh = _run_launcher("zh", "msg", "install")
ok("TACIT_LANG=zh 時講中文", bool(_CJK.search(_zh)), _zh.strip()[:40])
ok("訊息裡的欄位會被填進去",
   "8501" in _run_launcher("en", "msg", "url", "port=8501"))

# 不是走 MESSAGES 的那幾句（版本檢查、相依檢查、埠號提醒）也要是英文
ok("版本檢查的輸出在英文模式下沒有中文",
   not _CJK.search(_run_launcher("en", "check")))
ok("相依檢查的輸出在英文模式下沒有中文",
   not _CJK.search(_run_launcher("en", "deps")))

# 兩支 shell 啟動器：找到 Python 之前的訊息只能在 shell 裡講，必須成對出現
for _sh in ("launch_linux.sh", "launch_mac.command"):
    _src = open(os.path.join(ROOT, _sh), encoding="utf-8").read()
    ok(f"{_sh} 會判斷語言", "UI_LANG" in _src and "TACIT_LANG" in _src)
    _fails = _re.findall(r'fail "([^"]*)"', _src)
    ok(f"{_sh} 的每一個 fail 第一個引數都是英文",
       _fails and not any(_CJK.search(f) for f in _fails),
       str([f[:30] for f in _fails if _CJK.search(f)]))
    ok(f"{_sh} 沒有 CRLF（否則 bash 直接不認得）", "\r" not in _src)

_bat = open(os.path.join(ROOT, "launch_windows.bat"), encoding="utf-8",
            errors="replace").read()
_echo = [l for l in _bat.splitlines() if l.strip().lower().startswith("echo ")]
ok("launch_windows.bat 自己印的字沒有中文",
   not any(_CJK.search(l) for l in _echo),
   str([l.strip()[:40] for l in _echo if _CJK.search(l)]))

print()
print("=" * 70)
print("結果：全部通過 ✅" if not FAIL else f"結果：{len(FAIL)} 項失敗 ❌")
for f in FAIL:
    print(f"  - {f}")
print("=" * 70)
sys.exit(1 if FAIL else 0)
