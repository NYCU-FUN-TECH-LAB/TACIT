#!/usr/bin/env bash
# =====================================================================
# TACIT 啟動器（macOS）
# 使用方式：在檔案總管按右鍵「以程式執行」，或在終端機執行 ./launch_mac.command
# =====================================================================
set -u
cd "$(dirname "$0")" || exit 1

APP="src/app.py"
VENV=".venv"
STAMP="$VENV/.deps_ok"

# 訊息語言：系統語言是中文才顯示中文，其餘一律英文。TACIT_LANG=en|zh 可強制指定。
# 使用者不一定讀中文；雙擊之後看到的每一句話都要讀得懂。
# 找到 Python 之後的訊息改由 src/_launch_common.py msg 輸出，三個平台講同一套話；
# 這裡的 t() 只負責找到 Python **之前**、不得不在 shell 裡說的那幾句。
case "${TACIT_LANG:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
  zh*|ZH*) UI_LANG="zh" ;;
  *)       UI_LANG="en" ;;
esac
export TACIT_LANG="$UI_LANG"

say()  { printf '%s\n' "$*"; }
t()    { if [ "$UI_LANG" = "zh" ]; then printf '%s\n' "$2"; else printf '%s\n' "$1"; fi; }
fail() {
  if [ "$UI_LANG" = "zh" ]; then
    printf '\n[錯誤] %s\n' "$2"; printf '\n按 Enter 關閉視窗…'
  else
    printf '\n[ERROR] %s\n' "$1"; printf '\nPress Enter to close this window...'
  fi
  read -r _; exit 1
}

say "======================================================"
say "  TACIT"
t   "  Theory-Anchored Coding with Interpretive Transparency" "  理論錨定的質性編碼系統"
say "======================================================"
say ""

[ -f "$APP" ] || fail "$APP not found. Keep this launcher in the same folder as the program." \
                       "找不到 $APP。請確認這個啟動檔與程式放在同一個資料夾。"

# --- 1. 找 Python -----------------------------------------------------
PY=""
if [ -x "./python/bin/python3" ]; then
  PY="./python/bin/python3"                      # 完整可攜版內建的 Python
else
  for c in python3 python; do
    if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
  done
fi
[ -n "$PY" ] || fail "Python was not found on this computer. Install Python 3.9 or newer: https://www.python.org/downloads/  (or: brew install python)" \
                     "這台電腦上找不到 Python。請先安裝 Python 3.9 以上：https://www.python.org/downloads/  （macOS 亦可用 brew install python）"

"$PY" src/_launch_common.py check || fail "Python 3.9 or newer is required." \
                                     "Python 版本不符需求，請安裝 3.9 以上版本。"

# --- 2. 虛擬環境（完整可攜版已內建，就不再建立）-----------------------
if [ -x "./python/bin/python3" ]; then
  VPY="./python/bin/python3"
else
  # 從別的資料夾**複製**過來的 venv 一定不能用：標準函式庫的位置在建立當下
  # 就寫進 pyvenv.cfg 了，換路徑之後直譯器找不到 stdlib，會丟出
  # 「Failed to import encodings module」——完全看不出跟搬資料夾有關。
  # 這裡主動偵測並重建，而不是讓使用者對著那個訊息發呆。
  if [ -d "$VENV" ] && ! "$PY" src/_launch_common.py venvcheck "$VENV"; then
    "$PY" src/_launch_common.py msg rebuild
    rm -rf "$VENV" "$STAMP"
  fi
  if [ ! -d "$VENV" ]; then
    "$PY" src/_launch_common.py msg mkvenv
    "$PY" -m venv "$VENV" || fail "Could not create the environment. Check free disk space." \
                                  "建立虛擬環境失敗。請確認磁碟空間足夠"
  fi
  VPY="$VENV/bin/python"
fi

# --- 3. 相依套件（只在缺少時安裝）-------------------------------------
if [ ! -f "$STAMP" ] || [ "requirements.txt" -nt "$STAMP" ]; then
  if ! "$VPY" src/_launch_common.py deps >/dev/null 2>&1; then
    "$PY" src/_launch_common.py msg install
    "$VPY" -m pip install --upgrade pip --quiet
    "$VPY" -m pip install -r requirements.txt || \
      fail "Package installation failed. Check your connection and try again." \
           "套件安裝失敗。請檢查網路連線後重試。"
  fi
  mkdir -p "$(dirname "$STAMP")" 2>/dev/null
  : > "$STAMP"
  "$PY" src/_launch_common.py msg installed
fi

MISSING="$("$VPY" src/_launch_common.py deps 2>/dev/null)" || \
  fail "These packages are still missing: $MISSING. Run: $VPY -m pip install -r requirements.txt" \
       "以下套件仍然缺少：$MISSING。請手動執行：$VPY -m pip install -r requirements.txt"

# --- 4. 啟動 ----------------------------------------------------------
# 中文斷詞器（選配）。會連帶裝 PyTorch，所以獨立成一步；
# 這裡失敗不能讓程式打不開，cmd_segmenter 一律回傳 0。
"$VPY" src/_launch_common.py segmenter

"$VPY" src/_launch_common.py credentials >/dev/null 2>&1
# 埠號走 stdout、警告走 stderr；不要把 stderr 導掉，
# 「舊視窗還開著」的提醒才看得到。
PORT="$("$VPY" src/_launch_common.py port)"
[ -n "$PORT" ] || PORT=8501

"$VPY" src/_launch_common.py msg starting
"$VPY" src/_launch_common.py msg url "port=$PORT"
"$VPY" src/_launch_common.py msg keepopen

# 設 RI_LAUNCH_DRYRUN=1 只印出最終指令而不真的啟動（除錯與自動測試用）
if [ "${RI_LAUNCH_DRYRUN:-0}" = "1" ]; then
  say "DRYRUN: $VPY -m streamlit run $APP --server.port $PORT"
  exit 0
fi

exec "$VPY" -m streamlit run "$APP" \
  --server.port "$PORT" \
  --server.headless false \
  --browser.gatherUsageStats false
