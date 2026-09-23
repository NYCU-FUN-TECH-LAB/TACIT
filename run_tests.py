"""
run_tests.py — 執行全部測試套件
=====================================================================

    python run_tests.py            全部
    python run_tests.py llm irr    只跑名稱含這些字的套件

測試檔以獨立行程執行，工作目錄固定在專案根目錄。理由有兩個：

  1. 部分套件（test_ui_smoke）用 Streamlit 的 AppTest 實跑 app.py，
     而 app.py 會讀寫相對路徑下的資料夾；工作目錄不對就找不到檔案。
  2. 每個套件都會改動模組層級的狀態（現用框架、介面語言）。同一個
     行程裡連跑，後面的套件會撿到前面留下的框架，失敗訊息會指向
     完全無關的地方。一個套件一個行程，比在每個檔案裡補 teardown
     可靠得多。

全部離線：沒有任何一項需要網路或 API 金鑰。
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(ROOT, "tests")


def main(argv):
    # 本行程自己的輸出同理（下面那一段只管子行程）。
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    if not os.path.isdir(TEST_DIR):
        print(f"no tests directory at {TEST_DIR}")
        return 1
    names = sorted(f for f in os.listdir(TEST_DIR)
                   if f.startswith("test_") and f.endswith(".py"))
    if argv:
        names = [n for n in names if any(a.lower() in n.lower() for a in argv)]
    if not names:
        print("no matching test files")
        return 1

    env = dict(os.environ)
    # 讓 tests/ 底下的檔案 import 得到根目錄的模組，
    # 同時避免任何殘留的環境設定把測試導向真實的模型服務。
    env["PYTHONPATH"] = os.path.join(ROOT, "src") + os.pathsep + env.get("PYTHONPATH", "")
    # 輸出一律 UTF-8。Windows 上把結果導進管道或檔案時，子行程的 stdout
    # 會從主控台的 UTF-8 退回系統地區編碼（cp950），套件結尾印的 ✅／❌
    # 就會 UnicodeEncodeError 當掉，回傳碼非零——於是「全部通過」的套件
    # 被記成全部失敗，而且看不出原因。這一行讓管道與檔案輸出跟直接跑一樣。
    env["PYTHONIOENCODING"] = "utf-8"
    for k in ("TACIT_PROVIDER", "TACIT_MODEL", "TACIT_BASE_URL",
              "TACIT_API_KEY"):
        env.pop(k, None)

    failed = []
    for n in names:
        print("\n" + "=" * 70)
        print(f"  {n}")
        print("=" * 70)
        r = subprocess.run([sys.executable, os.path.join("tests", n)],
                           cwd=ROOT, env=env)
        if r.returncode != 0:
            failed.append(n)

    print("\n" + "=" * 70)
    if failed:
        print(f"  {len(failed)} of {len(names)} suites FAILED")
        for n in failed:
            print(f"    - {n}")
    else:
        print(f"  all {len(names)} suites passed")
    print("=" * 70)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
