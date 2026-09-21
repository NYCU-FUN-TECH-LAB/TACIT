"""
_launch_common.py — 啟動器的輔助腳本
=====================================
被 launch_windows.bat / launch_mac.command / launch_linux.sh 呼叫。
把「挑一個沒被佔用的埠」「檢查 Python 版本」「確認相依是否齊全」這些
在批次檔裡很難寫對的判斷，交給 Python 做——批次檔只負責流程。

用法：
  python _launch_common.py check      檢查 Python 版本，不合格回傳 1
  python _launch_common.py deps       相依套件是否齊全，缺少回傳 1 並列出缺項
  python _launch_common.py port       印出一個可用的埠號
  python _launch_common.py credentials 建立 Streamlit 憑證檔，跳過首次 email 詢問
  python _launch_common.py segmenter  安裝中文斷詞器（選配，失敗不影響啟動）
  python _launch_common.py venvcheck  檢查 .venv 是否可用（被複製過來就不可用）
"""

import os
import socket
import sys

MIN_PY = (3, 9)
REQUIRED = [
    ("streamlit", "streamlit"),
    ("docx", "python-docx"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("openpyxl", "openpyxl"),
    # Gemini SDK 是必要相依：不是每個人都有 Ollama，沒有本機模型的人
    # 裝完就要能直接用 Gemini。只裝了舊版 google-generativeai 的既有環境
    # 會被判定缺少，啟動器接著執行 pip install -r requirements.txt 補上新版。
    ("google.genai", "google-genai"),
]

OPTIONAL = [("plotly", "plotly"), ("scipy", "scipy")]

# 中文斷詞器。刻意**不**放進 requirements.txt：
# 它會連帶裝進 PyTorch，下載量約數百 MB，放進主要相依會讓第一次啟動
# 變得又慢又容易因網路中斷而整個失敗。改成獨立的一步，裝失敗也能照常啟動，
# 只是詞庫誘導的品質降級——而詞庫誘導只是輔助頁籤，不影響語意編碼。
SEGMENTER_PKG = "ckip-transformers"
SEGMENTER_MOD = "ckip_transformers"


def _lang():
    """
    啟動器講哪一種語言：系統介面是中文就講中文，其餘一律英文。

    使用者不一定讀中文。雙擊啟動檔之後，黑色視窗裡的每一句話都要讀得懂
    ——尤其是「請不要關閉視窗」與錯誤訊息，那正是最需要讀懂的兩種。

    環境變數 TACIT_LANG=en 或 zh 可以強制指定（拍英文截圖、測試時用）。
    """
    forced = os.environ.get("TACIT_LANG", "").strip().lower()[:2]
    if forced in ("en", "zh"):
        return forced
    try:
        if os.name == "nt":
            import ctypes
            lid = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "zh" if (lid & 0x3FF) == 0x04 else "en"   # 0x04 = Chinese
        import locale
        loc = (os.environ.get("LC_ALL") or os.environ.get("LC_MESSAGES")
               or os.environ.get("LANG") or (locale.getlocale()[0] or ""))
        return "zh" if loc.lower().startswith("zh") else "en"
    except Exception:                                      # noqa: BLE001
        return "en"


LANG = _lang()


def say(en, zh, **kw):
    """依語言印出其中一句。主控台編碼沒切換時退回位元組輸出，不要炸。"""
    text = zh if LANG == "zh" else en
    try:
        print(text, **kw)
    except UnicodeEncodeError:
        stream = kw.get("file", sys.stdout)
        stream.buffer.write(text.encode("utf-8", "replace") + b"\n")


def cmd_segmenter():
    """
    安裝中文斷詞器。裝過就跳過；裝不起來也回傳 0——
    這一步失敗絕不能讓使用者連程式都打不開。
    """
    import importlib.util
    import subprocess
    if importlib.util.find_spec(SEGMENTER_MOD) is not None:
        return 0
    say("\nInstalling the Chinese word segmenter (3-10 minutes, first run only).",
        "\n正在安裝中文斷詞器（首次約 3～10 分鐘，之後不再重覆）。")
    say("If this step fails the program still runs; only the lexicon tab is affected.",
        "這一步失敗不影響使用，只是「詞庫誘導」頁籤的品質會降低。")
    print("------------------------------------------------------")
    try:
        r = subprocess.run([sys.executable, "-m", "pip", "install",
                            SEGMENTER_PKG], timeout=1800)
        if r.returncode == 0:
            print("------------------------------------------------------")
            say("Segmenter installed.", "中文斷詞器安裝完成。")
        else:
            print("------------------------------------------------------")
            say("Segmenter could not be installed; using the built-in statistical "
                "fallback. The program starts as usual.",
                "中文斷詞器安裝失敗，改用內建的統計後備方法，程式照常啟動。")
            say(f"To install it yourself: pip install {SEGMENTER_PKG}",
                f"想自行安裝可執行：pip install {SEGMENTER_PKG}")
    except Exception as e:
        say(f"(segmenter install skipped: {e})", f"（略過斷詞器安裝：{e}）")
    return 0


def cmd_venvcheck():
    """
    檢查 .venv 能不能用。不能用就回傳 1，讓啟動器把它刪掉重建。

    最常見的壞法是**整個資料夾被複製過來**。虛擬環境不可搬移：
    Scripts\\python.exe 只是個小啟動器，標準函式庫的位置在建立當下就寫進
    pyvenv.cfg 了。換一個路徑之後它找不到 stdlib，於是丟出
        Fatal Python error: Failed to import encodings module
    這個訊息完全看不出跟「資料夾搬過」有關，所以這裡主動比對路徑並說清楚。
    """
    venv = sys.argv[2] if len(sys.argv) > 2 else ".venv"
    cfg = os.path.join(venv, "pyvenv.cfg")
    if not os.path.isfile(cfg):
        return 1
    created_at = ""
    try:
        with open(cfg, encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.strip().startswith("command"):
                    part = line.split("-m venv", 1)
                    created_at = part[1].strip() if len(part) > 1 else ""
    except OSError:
        return 1

    here = os.path.abspath(venv)
    if created_at and os.path.normcase(os.path.abspath(created_at)) != \
            os.path.normcase(here):
        say("This environment was copied from another folder:",
            "偵測到執行環境是從別的資料夾複製過來的：")
        say(f"    created at: {created_at}", f"    建立於：{created_at}")
        say(f"    now at:     {here}", f"    現在在：{here}")
        say("A virtual environment cannot be moved. It will be rebuilt; "
            "your research data are not touched.",
            "虛擬環境無法搬移，將自動重建（不會動到你的研究資料）。")
        return 1

    # 就算路徑對，直譯器本身也可能壞掉（例如系統 Python 被移除或升級）
    exe = os.path.join(venv, "Scripts", "python.exe")
    if not os.path.isfile(exe):
        exe = os.path.join(venv, "bin", "python")
    if not os.path.isfile(exe):
        return 1
    try:
        import subprocess
        r = subprocess.run([exe, "-c", "import encodings, sys; print(sys.version)"],
                           capture_output=True, timeout=60)
        if r.returncode != 0:
            say("The environment is broken (its interpreter will not start). "
                "It will be rebuilt.",
                "執行環境已損壞（直譯器無法啟動），將自動重建。")
            return 1
    except Exception:
        say("The environment could not be verified. It will be rebuilt.",
            "執行環境無法驗證，將自動重建。")
        return 1
    return 0


def cmd_check():
    if sys.version_info < MIN_PY:
        _v = f"{sys.version_info.major}.{sys.version_info.minor}"
        say(f"Python {_v} is too old; {MIN_PY[0]}.{MIN_PY[1]} or newer is required.",
            f"Python 版本過舊：目前 {_v}，需要 {MIN_PY[0]}.{MIN_PY[1]} 以上")
        return 1
    print(f"Python {sys.version_info.major}.{sys.version_info.minor}."
          f"{sys.version_info.micro} OK")
    return 0


def cmd_deps():
    import importlib.util
    missing = [pkg for mod, pkg in REQUIRED if importlib.util.find_spec(mod) is None]
    if missing:
        print(" ".join(missing))
        return 1
    opt_missing = [pkg for mod, pkg in OPTIONAL if importlib.util.find_spec(mod) is None]
    if opt_missing:
        say("(optional packages not installed; some features are reduced: "
            + ", ".join(opt_missing) + ")",
            "（選配未安裝，功能會降級但可執行：" + "、".join(opt_missing) + "）",
            file=sys.stderr)
    return 0


def _port_free(port):
    """
    這個埠現在能不能用。

    兩個要避開的坑：

    ① **不要設 SO_REUSEADDR。** 那個旗標的用意是允許重用 TIME_WAIT 狀態的
       位址，但在 Windows 上它更寬鬆——即使有程式正在監聽，bind 仍然會成功。
       於是這裡回報「8501 可用」，Streamlit 隨後卻因為真的被佔用而啟動失敗。

    ② **要綁 0.0.0.0，不是 127.0.0.1。** Streamlit 監聽所有介面；
       只測 loopback 的話，一個綁在其他介面上的程式不會被偵測到。
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def cmd_port():
    """
    從 8501 起找一個沒被佔用的埠。找不到就讓系統隨便給一個。

    8501 被佔用時多半是**上一個視窗還開著**，而不是別的軟體。
    這時換到 8502 雖然能跑，但使用者會同時有兩個程式在跑、
    各自讀寫同一批存檔——所以提醒一句，訊息走 stderr 才不會混進埠號。
    """
    if not _port_free(8501):
        say("Note: port 8501 is in use, most likely by an earlier window.\n"
            "      A different port will be used, but both copies will read and\n"
            "      write the same saved files. Close the old window.",
            "提醒：8501 已被佔用，多半是先前的視窗還開著。\n"
            "      這次會換一個埠啟動，但兩個程式會同時讀寫同一批存檔。\n"
            "      建議關掉舊的視窗，只保留一個。", file=sys.stderr)
    for p in range(8501, 8531):
        if _port_free(p):
            print(p)
            return 0
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 0))
        print(s.getsockname()[1])
    return 0


def cmd_credentials():
    """
    Streamlit 首次執行會在終端機問 email。對非技術使用者這一步很嚇人，
    先寫一個空的憑證檔把它跳過。已存在就不覆寫。
    """
    d = os.path.join(os.path.expanduser("~"), ".streamlit")
    f = os.path.join(d, "credentials.toml")
    try:
        os.makedirs(d, exist_ok=True)
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as fh:
                fh.write('[general]\nemail = ""\n')
            say("Created the Streamlit credentials file (skips the first-run "
                "email prompt).",
                "已建立 Streamlit 憑證檔（跳過首次 email 詢問）")
        return 0
    except Exception as e:
        say(f"(credentials file skipped: {e})", f"（略過憑證檔建立：{e}）",
            file=sys.stderr)
        return 0


MESSAGES = {
    # 每一則都是 (英文, 中文)。shell 啟動器在找到 Python 之後的訊息也走這裡，
    # 三個平台講的是同一套話。
    "banner": (
        "======================================================\n  TACIT\n"
        "  Theory-Anchored Coding with Interpretive Transparency\n======================================================",
        "======================================================\n  TACIT\n"
        "  理論錨定的質性編碼系統\n======================================================"),
    "mkvenv": (
        "\nFirst run: creating an isolated environment (once only, about 1 minute)...",
        "\n首次執行，正在建立獨立的執行環境（只會做這一次，約 1 分鐘）…"),
    "install": (
        "\nInstalling the required packages. The first run takes 3-10 minutes\n"
        "depending on your connection. Please do not close this window.\n------------------------------------------------------",
        "\n正在安裝需要的套件。第一次會比較久，視網路速度約 3～10 分鐘，\n"
        "請不要關閉視窗。\n------------------------------------------------------"),
    "installed": ("------------------------------------------------------\nEnvironment ready.",
                  "------------------------------------------------------\n環境準備完成。"),
    "starting": ("\nStarting. Your browser will open automatically...",
                 "\n正在啟動，瀏覽器會自動開啟…"),
    "keepopen": (
        "\n[When you are done, come back to this window and press Ctrl+C, "
        "or close it]\n======================================================\n",
        "\n【使用完畢請回到這個黑色視窗，按 Ctrl+C 或直接關閉視窗】\n======================================================\n"),
    "err_app": (
        "\n[ERROR] app.py not found.\nKeep this launcher in the same folder as the program.",
        "\n[錯誤] 找不到 app.py。\n請確認這個啟動檔與程式放在同一個資料夾。"),
    "err_venv": (
        "\n[ERROR] Could not create the environment. Check free disk space.",
        "\n[錯誤] 建立執行環境失敗。請確認磁碟空間足夠，或改用完整可攜版。"),
    "err_pip": (
        "\n[ERROR] Package installation failed. Check your connection, close this "
        "window and run the launcher again.",
        "\n[錯誤] 套件安裝失敗。請檢查網路連線後，關閉視窗重新執行一次。"),
    "err_deps": (
        "\n[ERROR] Some packages are still missing; cannot start. "
        "Please report this screen.",
        "\n[錯誤] 仍有套件缺少，無法啟動。請把畫面截圖回報。"),
    "rebuild": (
        "\nRebuilding the environment (the old one cannot be used).\n"
        "Your transcripts, analyses and framework files are not affected.",
        "\n正在重建執行環境（舊的無法使用）。\n"
        "這不會影響你的逐字稿、分析結果與框架檔。"),
    "err_python": (
        "\n[ERROR] No usable Python was found.\n"
        "If you have installed it, the installer option \"Add Python to PATH\" "
        "was probably left unticked.\n"
        "Run the installer again with that option ticked.\n"
        "Python 3.9 or newer: https://www.python.org/downloads/",
        "\n[錯誤] 找不到可用的 Python。\n"
        "若你確定已經安裝過，可能是安裝時沒有勾選 "
        "「Add Python to PATH」。\n"
        "重新執行安裝程式、勾選該選項後再試一次。"),
    "err_pyver": (
        "Python 3.9 or newer is required.",
        "Python 版本不符需求，請安裝 3.9 以上版本。"),
    "url": ("Address: http://localhost:{port}", "網址： http://localhost:{port}"),
    "err_missing": (
        "These packages are still missing: {missing}.",
        "以下套件仍然缺少：{missing}。"),
}


def cmd_msg():
    key = sys.argv[2] if len(sys.argv) > 2 else "banner"
    en, zh = MESSAGES.get(key, ("", ""))
    # 第三個引數起是 name=value，填進訊息裡的 {name}
    fields = dict(a.split("=", 1) for a in sys.argv[3:] if "=" in a)
    try:
        en, zh = en.format(**fields), zh.format(**fields)
    except (KeyError, IndexError):
        pass
    say(en, zh)
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit({
        "check": cmd_check, "deps": cmd_deps, "msg": cmd_msg,
        "port": cmd_port, "credentials": cmd_credentials,
        "segmenter": cmd_segmenter, "venvcheck": cmd_venvcheck,
    }.get(action, cmd_check)())
